from django.db import models

from loans.models import Loan


class Repayment(models.Model):
    PAYMENT_METHODS = (
        ('cash', 'Cash'),
        ('mobile', 'Mobile Money'),
        ('bank', 'Bank'),
    )

    loan = models.ForeignKey(Loan, on_delete=models.CASCADE)
    amount_paid = models.DecimalField(max_digits=18, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    payment_date = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        was_completed = self.loan.status == Loan.COMPLETED
        super().save(*args, **kwargs)
        if is_new:
            self.loan.outstanding_balance = max(self.loan.outstanding_balance - self.amount_paid, 0)
            self.record_virtual_bank_repayment()
            if self.loan.outstanding_balance == 0:
                self.loan.status = Loan.COMPLETED
            self.loan.save(update_fields=('outstanding_balance', 'status'))
            if self.loan.status == Loan.COMPLETED and not was_completed:
                self.notify_admins_about_completion()

    def record_virtual_bank_repayment(self):
        from banking.models import BankTransaction

        BankTransaction.record_repayment(self)

    def notify_admins_about_completion(self):
        from django.contrib.auth import get_user_model
        from django.db.models import Q
        from notifications.services import notify_users

        User = get_user_model()
        admins = User.objects.filter(Q(role=User.ADMIN) | Q(is_superuser=True) | Q(is_staff=True)).distinct()
        message = (
            f'{self.loan.member.username} has completed loan #{self.loan.id}. '
            f'Total repayment: {self.loan.total_repayment}.'
        )
        notify_users(admins, 'SACCO loan completed', message)

    def __str__(self):
        return str(self.loan)
