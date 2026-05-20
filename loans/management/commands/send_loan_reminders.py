from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from loans.models import Loan
from notifications.services import notify_user, notify_users
from penalties.models import Penalty


class Command(BaseCommand):
    help = 'Email members with overdue loans and record daily penalties.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show overdue loans without creating penalties or sending messages.',
        )

    def handle(self, *args, **options):
        today = timezone.localdate()
        overdue_loans = Loan.objects.select_related('member').filter(
            status=Loan.APPROVED,
            repayment_start_date__lt=today,
            outstanding_balance__gt=0,
        )
        sent_count = 0
        dry_run = options['dry_run']

        for loan in overdue_loans:
            months_due = self.months_due(loan.repayment_start_date, today)
            expected_paid = min(loan.monthly_payment * months_due, loan.total_repayment)
            actual_paid = loan.total_repayment - loan.outstanding_balance

            if actual_paid >= expected_paid:
                continue

            shortfall = expected_paid - actual_paid
            penalty, created = self.get_or_create_daily_penalty(loan, today, dry_run)
            subject = 'SACCO overdue loan payment reminder'
            message = (
                f'Dear {loan.member.username}, your loan #{loan.id} has a delayed payment. '
                f'Expected paid by {today}: {expected_paid}. Amount paid: {actual_paid}. '
                f'Outstanding balance: {loan.outstanding_balance}. Current shortfall: {shortfall}. '
                f'Penalty for today: {penalty.amount if penalty else self.penalty_amount(loan)}.'
            )

            if dry_run:
                self.stdout.write(f'OVERDUE loan #{loan.id}: {loan.member.username} - {message}')
                sent_count += 1
                continue

            notify_user(loan.member, subject, message)
            self.notify_admins(loan, message)
            sent_count += 1

            status = 'created' if created else 'already existed'
            self.stdout.write(f'Notified {loan.member.username}; penalty {status} for loan #{loan.id}.')

        self.stdout.write(self.style.SUCCESS(f'Overdue reminder check complete. Loans notified: {sent_count}.'))

    def months_due(self, start_date, today):
        months = (today.year - start_date.year) * 12 + today.month - start_date.month
        if today.day >= start_date.day:
            months += 1
        return max(months, 1)

    def penalty_amount(self, loan):
        rate = Decimal(settings.SACCO_PENALTY_RATE)
        base_amount = loan.monthly_payment or loan.amount
        return (base_amount * rate).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    def get_or_create_daily_penalty(self, loan, today, dry_run):
        reason = f'Overdue payment penalty for {today}'
        existing_penalty = Penalty.objects.filter(loan=loan, reason=reason).first()
        if existing_penalty:
            return existing_penalty, False
        if dry_run:
            return None, False
        return Penalty.objects.create(
            loan=loan,
            amount=self.penalty_amount(loan),
            reason=reason,
        ), True

    def notify_admins(self, loan, member_message):
        User = get_user_model()
        admins = User.objects.filter(Q(role=User.ADMIN) | Q(is_superuser=True) | Q(is_staff=True)).distinct()
        notify_users(
            admins,
            'SACCO overdue loan alert',
            f'{loan.member.username} has an overdue loan. {member_message}',
        )
