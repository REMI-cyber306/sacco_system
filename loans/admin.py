from django.contrib import admin

from .models import Loan, LoanCollateral, LoanGuarantor, LoanRateTier


class LoanCollateralInline(admin.TabularInline):
    model = LoanCollateral
    extra = 0


class LoanGuarantorInline(admin.TabularInline):
    model = LoanGuarantor
    extra = 0
    fields = ('guarantor', 'relationship', 'has_signed', 'signed_at')


@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = (
        'member',
        'amount',
        'interest_rate',
        'duration_months',
        'requested_disbursement_date',
        'repayment_start_date',
        'status',
        'outstanding_balance',
        'created_at',
    )
    list_filter = ('status', 'requested_disbursement_date', 'repayment_start_date', 'created_at')
    search_fields = ('member__username', 'member__phone', 'purpose')
    list_editable = ('status',)
    inlines = (LoanCollateralInline, LoanGuarantorInline)


@admin.register(LoanRateTier)
class LoanRateTierAdmin(admin.ModelAdmin):
    list_display = ('name', 'min_amount', 'max_amount', 'interest_rate', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name',)


@admin.register(LoanCollateral)
class LoanCollateralAdmin(admin.ModelAdmin):
    list_display = ('loan', 'property_name', 'estimated_value', 'confiscated', 'created_at')
    list_filter = ('confiscated', 'created_at')
    search_fields = ('loan__member__username', 'property_name', 'description')


@admin.register(LoanGuarantor)
class LoanGuarantorAdmin(admin.ModelAdmin):
    list_display = ('loan', 'guarantor', 'relationship', 'has_signed', 'signed_at')
    list_filter = ('has_signed', 'created_at')
    search_fields = ('loan__member__username', 'guarantor__username')
    list_editable = ('has_signed',)
