from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q

from .models import CustomUser
from .forms import (
    LoginForm,
    ProfileUpdateForm,
    UserCreateAdminForm,
    UserUpdateAdminForm,
    BootstrapPasswordChangeForm,
)
from .permissions import admin_required
from audit.utils import log_action
from audit.models import AuditLog


def login_view(request):
    if request.user.is_authenticated:
        return redirect('reports:dashboard')

    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            log_action(user, AuditLog.Action.LOGIN, 'CustomUser', user.id, {'detail': 'User login berhasil'}, request=request)
            messages.success(request, f"Selamat datang, {user.display_name}!")
            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)
            return redirect('reports:dashboard')
        else:
            errors = form.non_field_errors()
            if any('dinonaktifkan' in str(e).lower() for e in errors):
                messages.error(request, "Akun Anda telah dinonaktifkan. Silakan hubungi Administrator.")
            else:
                messages.error(request, "Nama pengguna atau kata sandi tidak valid.")
    else:
        form = LoginForm(request)

    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    if request.user.is_authenticated:
        log_action(request.user, AuditLog.Action.LOGOUT, 'CustomUser', request.user.id, {'detail': 'User logout'}, request=request)
        logout(request)
        messages.info(request, "Anda telah berhasil keluar dari sistem.")
    return redirect('accounts:login')


@login_required
def profile_view(request):
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            log_action(request.user, AuditLog.Action.UPDATE, 'CustomUser', request.user.id, {'detail': 'Perbaruan profil mandiri'}, request=request)
            messages.success(request, "Profil Anda berhasil diperbarui.")
            return redirect('accounts:profile')
    else:
        form = ProfileUpdateForm(instance=request.user)

    return render(request, 'accounts/profile.html', {'form': form})


@login_required
def password_change_view(request):
    if request.method == 'POST':
        form = BootstrapPasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            log_action(request.user, AuditLog.Action.UPDATE, 'CustomUser', user.id, {'detail': 'Penggantian kata sandi mandiri'}, request=request)
            messages.success(request, "Kata sandi Anda berhasil diperbarui.")
            return redirect('accounts:profile')
    else:
        form = BootstrapPasswordChangeForm(user=request.user)

    return render(request, 'accounts/password_change.html', {'form': form})


# --- Admin User Management ---

@login_required
@admin_required
def user_list_view(request):
    query = request.GET.get('q', '').strip()
    role_filter = request.GET.get('role', '').strip()
    status_filter = request.GET.get('status', '').strip()

    users = CustomUser.objects.all().order_by('username')

    if query:
        users = users.filter(
            Q(username__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(employee_number__icontains=query) |
            Q(department__icontains=query)
        )
    if role_filter:
        users = users.filter(role=role_filter)
    if status_filter != '':
        users = users.filter(is_active=(status_filter == '1'))

    paginator = Paginator(users, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'accounts/user_list.html', {
        'page_obj': page_obj,
        'query': query,
        'role_filter': role_filter,
        'status_filter': status_filter,
        'roles': CustomUser.Role.choices,
    })


@login_required
@admin_required
def user_create_view(request):
    if request.method == 'POST':
        form = UserCreateAdminForm(request.POST)
        if form.is_valid():
            user = form.save()
            log_action(
                request.user,
                AuditLog.Action.CREATE,
                'CustomUser',
                user.id,
                {'username': user.username, 'role': user.role, 'employee_number': user.employee_number},
                request=request
            )
            messages.success(request, f"Akun pengguna '{user.username}' berhasil dibuat.")
            return redirect('accounts:user_list')
    else:
        form = UserCreateAdminForm()

    return render(request, 'accounts/user_form.html', {
        'form': form,
        'title': 'Tambah Pengguna / Pegawai Baru',
    })


@login_required
@admin_required
def user_edit_view(request, pk):
    user_obj = get_object_or_404(CustomUser, pk=pk)
    if request.method == 'POST':
        form = UserUpdateAdminForm(request.POST, instance=user_obj)
        if form.is_valid():
            form.save()
            log_action(
                request.user,
                AuditLog.Action.UPDATE,
                'CustomUser',
                user_obj.id,
                {'username': user_obj.username, 'role': user_obj.role, 'is_active': user_obj.is_active},
                request=request
            )
            messages.success(request, f"Data pengguna '{user_obj.username}' berhasil diperbarui.")
            return redirect('accounts:user_list')
    else:
        form = UserUpdateAdminForm(instance=user_obj)

    return render(request, 'accounts/user_form.html', {
        'form': form,
        'user_obj': user_obj,
        'title': f'Ubah Pengguna: {user_obj.username}',
    })


@login_required
@admin_required
def user_toggle_active_view(request, pk):
    user_obj = get_object_or_404(CustomUser, pk=pk)
    if user_obj == request.user:
        messages.error(request, "Anda tidak dapat menonaktifkan akun Anda sendiri!")
        return redirect('accounts:user_list')

    user_obj.is_active = not user_obj.is_active
    user_obj.save()
    status_str = "diaktifkan" if user_obj.is_active else "dinonaktifkan"
    log_action(
        request.user,
        AuditLog.Action.UPDATE,
        'CustomUser',
        user_obj.id,
        {'action': 'toggle_active', 'is_active': user_obj.is_active},
        request=request
    )
    messages.success(request, f"Akun '{user_obj.username}' berhasil {status_str}.")
    return redirect('accounts:user_list')
