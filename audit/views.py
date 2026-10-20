from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q

from accounts.permissions import admin_required
from .models import AuditLog, InstitutionSetting
from .forms import InstitutionSettingForm
from .utils import log_action


@login_required
@admin_required
def audit_log_list_view(request):
    action_filter = request.GET.get('action', '').strip()
    query = request.GET.get('q', '').strip()

    logs = AuditLog.objects.select_related('user').all()

    if action_filter:
        logs = logs.filter(action=action_filter)
    if query:
        logs = logs.filter(
            Q(user__username__icontains=query) |
            Q(user__first_name__icontains=query) |
            Q(user__last_name__icontains=query) |
            Q(entity_type__icontains=query) |
            Q(entity_id__icontains=query)
        )

    paginator = Paginator(logs, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'audit/log_list.html', {
        'page_obj': page_obj,
        'action_filter': action_filter,
        'query': query,
        'actions': AuditLog.Action.choices,
    })


@login_required
@admin_required
def setting_view(request):
    setting = InstitutionSetting.objects.first()
    if not setting:
        setting = InstitutionSetting.objects.create()

    if request.method == 'POST':
        form = InstitutionSettingForm(request.POST, instance=setting)
        if form.is_valid():
            form.save()
            log_action(
                request.user,
                AuditLog.Action.UPDATE,
                'InstitutionSetting',
                setting.id,
                {'detail': 'Pembaruan identitas dan kop surat instansi'},
                request=request
            )
            messages.success(request, "Pengaturan instansi berhasil disimpan.")
            return redirect('audit:setting_view')
    else:
        form = InstitutionSettingForm(instance=setting)

    return render(request, 'audit/setting_form.html', {'form': form})
