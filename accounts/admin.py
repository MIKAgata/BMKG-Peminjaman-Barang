from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Informasi Kepegawaian & Peran', {
            'fields': ('role', 'employee_number', 'department', 'phone_number'),
        }),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Informasi Kepegawaian & Peran', {
            'fields': ('role', 'employee_number', 'department', 'phone_number'),
        }),
    )
    list_display = ('username', 'employee_number', 'first_name', 'last_name', 'role', 'department', 'is_active', 'is_staff')
    list_filter = ('role', 'is_active', 'department')
    search_fields = ('username', 'employee_number', 'first_name', 'last_name', 'department')
