from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models


class VirtualBankAccount(models.Model):
    name = models.CharField(max_length=100, default='SACCO Virtual Bank')
    balance = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('name',)

    def __str__(self):
        return f'{self.name} - {self.balance}'

    @classmethod
    def primary(cls):
        account, _ = cls.objects.get_or_create(
            name='SACCO Virtual Bank',
            defaults={'balance': Decimal('0.00'), 'is_active': True},
        )
        return account


class BankTransaction(models.Model):
    DEPOSIT = 'deposit'
    LOAN_DISBURSEMENT = 'loan_disbursement'
    REPAYMENT = 'repayment'
    ADJUSTMENT = 'adjustment'

    TRANSACTION_TYPES = (
        (DEPOSIT, 'Deposit'),
        (LOAN_DISBURSEMENT, 'Loan Disbursement'),
        (REPAYMENT, 'Repayment'),
        (ADJUSTMENT, 'Adjustment'),
    )

    account = models.ForeignKey(VirtualBankAccount, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=30, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    loan = models.ForeignKey('loans.Loan', on_delete=models.SET_NULL, blank=True, null=True)
    repayment = models.ForeignKey('repayments.Repayment', on_delete=models.SET_NULL, blank=True, null=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-created_at',)

    def clean(self):
        if self.amount <= 0:
            raise ValidationError('Transaction amount must be greater than zero.')
        if self.transaction_type == self.LOAN_DISBURSEMENT and self.account.balance < self.amount:
            raise ValidationError('Virtual bank has insufficient funds for this loan disbursement.')

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        self.full_clean()
        super().save(*args, **kwargs)
        if is_new:
            self.apply_to_balance()

    def apply_to_balance(self):
        if self.transaction_type == self.LOAN_DISBURSEMENT:
            self.account.balance -= self.amount
        else:
            self.account.balance += self.amount
        self.account.save(update_fields=('balance', 'updated_at'))

    @classmethod
    def record_loan_disbursement(cls, loan):
        account = VirtualBankAccount.primary()
        return cls.objects.create(
            account=account,
            transaction_type=cls.LOAN_DISBURSEMENT,
            amount=loan.amount,
            loan=loan,
            description=f'Loan #{loan.id} disbursed to {loan.member.username}.',
        )

    @classmethod
    def record_repayment(cls, repayment):
        account = VirtualBankAccount.primary()
        return cls.objects.create(
            account=account,
            transaction_type=cls.REPAYMENT,
            amount=repayment.amount_paid,
            loan=repayment.loan,
            repayment=repayment,
            description=f'Repayment for loan #{repayment.loan.id} by {repayment.loan.member.username}.',
        )

    def __str__(self):
        return f'{self.get_transaction_type_display()} - {self.amount}'

