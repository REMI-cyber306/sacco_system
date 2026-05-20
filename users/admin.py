from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('SACCO Profile', {'fields': ('role', 'phone', 'position', 'savings_balance')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('SACCO Profile', {'fields': ('role', 'phone', 'position', 'savings_balance')}),
    )
    list_display = ('username', 'email', 'role', 'phone', 'savings_balance', 'is_staff')
    list_filter = ('role', 'is_staff', 'is_active')
    search_fields = ('username', 'email', 'phone')

