from django.contrib import admin
from .models import LoanRequest, LoanItem, LoanHandover, LoanHandoverItem, ReturnRecord, ReturnItem


class LoanItemInline(admin.TabularInline):
    model = LoanItem
    extra = 0


@admin.register(LoanRequest)
class LoanRequestAdmin(admin.ModelAdmin):
    list_display = ('loan_number', 'borrower', 'start_date', 'due_date', 'status', 'created_at')
    list_filter = ('status', 'start_date', 'due_date')
    search_fields = ('loan_number', 'borrower__username', 'borrower__first_name', 'purpose')
    inlines = [LoanItemInline]


class LoanHandoverItemInline(admin.TabularInline):
    model = LoanHandoverItem
    extra = 0


@admin.register(LoanHandover)
class LoanHandoverAdmin(admin.ModelAdmin):
    list_display = ('handover_number', 'loan', 'handed_over_by', 'recipient', 'handover_date')
    search_fields = ('handover_number', 'loan__loan_number', 'recipient__username')
    inlines = [LoanHandoverItemInline]


class ReturnItemInline(admin.TabularInline):
    model = ReturnItem
    extra = 0


@admin.register(ReturnRecord)
class ReturnRecordAdmin(admin.ModelAdmin):
    list_display = ('return_number', 'loan', 'received_by', 'return_date')
    search_fields = ('return_number', 'loan__loan_number', 'received_by__username')
    inlines = [ReturnItemInline]
