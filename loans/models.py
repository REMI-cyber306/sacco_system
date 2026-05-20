from decimal import Decimal

from django.conf import settings
from django.db import models


class Loan(models.Model):
    PENDING = 'pending'
    APPROVED = 'approved'
    REJECTED = 'rejected'
    COMPLETED = 'completed'

    STATUS_CHOICES = (
        (PENDING, 'Pending'),
        (APPROVED, 'Approved'),
        (REJECTED, 'Rejected'),
        (COMPLETED, 'Completed'),
    )

    member = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2)
    duration_months = models.IntegerField()
    requested_disbursement_date = models.DateField(blank=True, null=True)
    repayment_start_date = models.DateField(blank=True, null=True)
    purpose = models.TextField()
    total_repayment = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    monthly_payment = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    outstanding_balance = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.total_repayment:
            interest = self.amount * (self.interest_rate / Decimal('100'))
            self.total_repayment = self.amount + interest
        if not self.monthly_payment and self.duration_months:
            self.monthly_payment = self.total_repayment / self.duration_months
        if not self.outstanding_balance:
            self.outstanding_balance = self.total_repayment
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.member.username} - {self.amount}'


class LoanRateTier(models.Model):
    name = models.CharField(max_length=100)
    min_amount = models.DecimalField(max_digits=18, decimal_places=2)
    max_amount = models.DecimalField(max_digits=18, decimal_places=2)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ('min_amount',)

    def __str__(self):
        return f'{self.name}: {self.min_amount} - {self.max_amount} at {self.interest_rate}%'

    @classmethod
    def for_amount(cls, amount):
        return cls.objects.filter(
            is_active=True,
            min_amount__lte=amount,
            max_amount__gte=amount,
        ).order_by('min_amount').first()


class LoanCollateral(models.Model):
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name='collaterals')
    property_name = models.CharField(max_length=100)
    estimated_value = models.DecimalField(max_digits=18, decimal_places=2)
    description = models.TextField()
    confiscated = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.property_name} - {self.estimated_value}'


class LoanGuarantor(models.Model):
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name='guarantors')
    guarantor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='guaranteed_loans')
    relationship = models.CharField(max_length=50, blank=True)
    has_signed = models.BooleanField(default=False)
    signed_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=('loan', 'guarantor'), name='unique_guarantor_per_loan'),
        ]

    def __str__(self):
        return f'{self.guarantor.username} signs for {self.loan}'
