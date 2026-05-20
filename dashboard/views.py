from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.contrib import messages
from django.db.models import Q
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from loans.forms import LoanApplicationForm
from loans.models import Loan, LoanRateTier
from notifications.models import Notification
from notifications.services import notify_user, notify_users
from repayments.forms import RepaymentForm
from repayments.models import Repayment
from users.models import User
from banking.models import BankTransaction, VirtualBankAccount


def index(request):
    if request.user.is_authenticated:
        return redirect('redirect_user')
    return render(request, 'index.html')


@login_required
def redirect_user(request):
    if is_admin_user(request.user):
        return redirect('admin_dashboard')
    return redirect('member_dashboard')


def is_admin_user(user):
    return user.is_authenticated and user.is_sacco_admin


def is_member_user(user):
    return user.is_authenticated and user.is_sacco_member


def admin_required(view_func):
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not is_admin_user(request.user):
            raise PermissionDenied
        return view_func(request, *args, **kwargs)

    return wrapper


def member_required(view_func):
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not is_member_user(request.user):
            raise PermissionDenied
        return view_func(request, *args, **kwargs)

    return wrapper


def notify_admins(message):
    admins = User.objects.filter(Q(role=User.ADMIN) | Q(is_superuser=True) | Q(is_staff=True)).distinct()
    notify_users(admins, 'SACCO admin notification', message)


def notify_loan_guarantors(loan):
    guarantors = [guarantor.guarantor for guarantor in loan.guarantors.select_related('guarantor')]
    if guarantors:
        notify_users(
            guarantors,
            'You were added as a SACCO loan guarantor',
            (
                f'{loan.member.username} added you as a guarantor for loan application '
                f'#{loan.id} of {loan.amount}. Please contact SACCO administration if this is incorrect.'
            ),
        )


@admin_required
def admin_dashboard(request):
    today = timezone.localdate()
    virtual_bank = VirtualBankAccount.primary()
    context = {
        'virtual_bank': virtual_bank,
        'recent_bank_transactions': BankTransaction.objects.select_related('loan', 'repayment').order_by('-created_at')[:5],
        'total_members': User.objects.filter(role=User.MEMBER, is_staff=False).count(),
        'total_loans': Loan.objects.count(),
        'pending_loans': Loan.objects.filter(status=Loan.PENDING).count(),
        'repayments_today': Repayment.objects.filter(payment_date__date=today).aggregate(total=Sum('amount_paid'))['total'] or 0,
        'unread_notifications': Notification.objects.filter(member=request.user, is_read=False).count(),
        'recent_notifications': Notification.objects.filter(member=request.user).order_by('-created_at')[:5],
        'pending_applications': Loan.objects.select_related('member').filter(status=Loan.PENDING).order_by('-created_at')[:10],
        'recent_loans': Loan.objects.select_related('member').order_by('-created_at')[:5],
        'recent_payments': Repayment.objects.select_related('loan', 'loan__member').order_by('-payment_date')[:5],
        'recent_members': User.objects.filter(role=User.MEMBER, is_staff=False).order_by('-created_at')[:5],
    }
    return render(request, 'admin/dashboard.html', context)


@member_required
def member_dashboard(request):
    loans = Loan.objects.filter(member=request.user)
    context = {
        'total_loans': loans.count(),
        'loan_balance': loans.aggregate(total=Sum('outstanding_balance'))['total'] or 0,
        'monthly_payment': loans.exclude(status=Loan.COMPLETED).aggregate(total=Sum('monthly_payment'))['total'] or 0,
        'notifications_count': Notification.objects.filter(member=request.user, is_read=False).count(),
        'recent_loans': loans.order_by('-created_at')[:5],
    }
    return render(request, 'member/dashboard.html', context)


@admin_required
def approve_loan(request, loan_id):
    loan = get_object_or_404(Loan, pk=loan_id)
    if request.method == 'POST':
        if loan.status != Loan.PENDING:
            messages.error(request, f'Loan #{loan.id} is already {loan.get_status_display().lower()}.')
            return redirect('admin_dashboard')
        try:
            BankTransaction.record_loan_disbursement(loan)
        except Exception as exc:
            messages.error(request, f'Loan could not be approved: {exc}')
            return redirect('admin_dashboard')
        loan.status = Loan.APPROVED
        loan.save(update_fields=('status',))
        messages.success(request, f'Loan #{loan.id} approved and disbursed from the virtual bank.')
        notify_user(
            loan.member,
            'Your SACCO loan has been approved',
            f'Your loan application #{loan.id} for {loan.amount} has been approved.',
        )
    return redirect('admin_dashboard')


@admin_required
def reject_loan(request, loan_id):
    loan = get_object_or_404(Loan, pk=loan_id)
    if request.method == 'POST':
        loan.status = Loan.REJECTED
        loan.save(update_fields=('status',))
        notify_user(
            loan.member,
            'Your SACCO loan has been rejected',
            f'Your loan application #{loan.id} for {loan.amount} has been rejected.',
        )
    return redirect('admin_dashboard')


@member_required
def apply_loan(request):
    form = LoanApplicationForm(request.POST or None, user=request.user)
    if request.method == 'POST' and form.is_valid():
        loan = form.save_application(request.user)
        notify_user(
            request.user,
            'Your SACCO loan application was received',
            (
                f'Your loan application for {loan.amount} was submitted at '
                f'{loan.interest_rate}% interest. Estimated total repayment is '
                f'{loan.total_repayment}, with monthly payment of {loan.monthly_payment}.'
            ),
        )
        notify_admins(
            f'{request.user.username} submitted loan application #{loan.id} for {loan.amount}. '
            'Review it for approval.'
        )
        notify_loan_guarantors(loan)
        return redirect('member_dashboard')
    loan_rates = LoanRateTier.objects.filter(is_active=True).order_by('min_amount')
    loan_rate_data = [
        {
            'name': tier.name,
            'min_amount': float(tier.min_amount),
            'max_amount': float(tier.max_amount),
            'interest_rate': float(tier.interest_rate),
        }
        for tier in loan_rates
    ]
    return render(
        request,
        'member/apply_loan.html',
        {'form': form, 'loan_rates': loan_rates, 'loan_rate_data': loan_rate_data},
    )


@member_required
def make_payment(request):
    form = RepaymentForm(request.POST or None, user=request.user)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('member_dashboard')
    return render(request, 'member/make_payment.html', {'form': form})
