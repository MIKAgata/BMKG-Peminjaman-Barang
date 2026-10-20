from functools import wraps
from django.contrib.auth.mixins import AccessMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.contrib import messages


def admin_required(view_func):
    """
    Decorator untuk memastikan user yang login memiliki role ADMIN atau superuser.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        if not (request.user.role == 'ADMIN' or request.user.is_superuser):
            messages.error(request, "Akses ditolak! Anda tidak memiliki izin Administrator/Petugas.")
            raise PermissionDenied("Hanya Admin/Petugas yang diizinkan mengakses halaman ini.")
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def employee_required(view_func):
    """
    Decorator untuk memastikan user yang login adalah pegawai atau admin.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


class AdminRequiredMixin(AccessMixin):
    """
    CBV mixin untuk membatasi akses hanya kepada ADMIN atau superuser.
    """
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not (request.user.role == 'ADMIN' or request.user.is_superuser):
            messages.error(request, "Akses ditolak! Halaman ini khusus untuk Administrator/Petugas Gudang.")
            raise PermissionDenied("Hanya Admin/Petugas yang diizinkan mengakses halaman ini.")
        return super().dispatch(request, *args, **kwargs)


class EmployeeRequiredMixin(AccessMixin):
    """
    CBV mixin untuk memverifikasi autentikasi user.
    """
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)
