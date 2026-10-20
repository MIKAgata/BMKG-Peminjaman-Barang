from django.contrib import admin
from .models import AuditLog, InstitutionSetting


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'user', 'action', 'entity_type', 'entity_id', 'ip_address')
    list_filter = ('action', 'entity_type', 'created_at')
    search_fields = ('user__username', 'entity_type', 'entity_id', 'details')
    readonly_fields = ('user', 'action', 'entity_type', 'entity_id', 'details', 'ip_address', 'created_at')

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(InstitutionSetting)
class InstitutionSettingAdmin(admin.ModelAdmin):
    list_display = ('institution_name', 'unit_name', 'phone', 'email', 'updated_at')
