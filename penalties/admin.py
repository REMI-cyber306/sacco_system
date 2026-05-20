from django.contrib import admin

from .models import Penalty


@admin.register(Penalty)
class PenaltyAdmin(admin.ModelAdmin):
    list_display = ('loan', 'amount', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('loan__member__username', 'reason')

