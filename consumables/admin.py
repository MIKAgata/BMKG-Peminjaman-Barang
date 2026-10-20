from django.contrib import admin
from .models import ConsumableHandover, ConsumableHandoverItem


class ConsumableHandoverItemInline(admin.TabularInline):
    model = ConsumableHandoverItem
    extra = 0


@admin.register(ConsumableHandover)
class ConsumableHandoverAdmin(admin.ModelAdmin):
    list_display = ('handover_number', 'recipient', 'department', 'handover_date', 'status', 'created_by')
    list_filter = ('status', 'handover_date')
    search_fields = ('handover_number', 'recipient__username', 'recipient__first_name', 'department', 'purpose')
    inlines = [ConsumableHandoverItemInline]
