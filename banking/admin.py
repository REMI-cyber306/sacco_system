from django.contrib import admin

from .models import BankTransaction, VirtualBankAccount


class BankTransactionInline(admin.TabularInline):
    model = BankTransaction
    extra = 0
    readonly_fields = ('created_at',)
    fields = ('transaction_type', 'amount', 'loan', 'repayment', 'description', 'created_at')


@admin.register(VirtualBankAccount)
class VirtualBankAccountAdmin(admin.ModelAdmin):
    list_display = ('name', 'balance', 'is_active', 'updated_at')
    list_filter = ('is_active',)
    search_fields = ('name',)
    inlines = (BankTransactionInline,)


@admin.register(BankTransaction)
class BankTransactionAdmin(admin.ModelAdmin):
    list_display = ('transaction_type', 'amount', 'account', 'loan', 'repayment', 'created_at')
    list_filter = ('transaction_type', 'created_at')
    search_fields = ('description', 'loan__member__username')

