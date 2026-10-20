from .models import AuditLog


def log_action(user, action, entity_type, entity_id='', details=None, request=None):
    """
    Helper untuk mencatat audit trail secara konsisten.
    """
    ip_address = None
    if request:
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip_address = x_forwarded_for.split(',')[0].strip()
        else:
            ip_address = request.META.get('REMOTE_ADDR')

    AuditLog.objects.create(
        user=user if user and user.is_authenticated else None,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        details=details or {},
        ip_address=ip_address
    )
