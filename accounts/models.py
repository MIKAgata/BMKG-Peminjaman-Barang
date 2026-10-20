from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = 'ADMIN', 'Admin / Petugas Gudang'
        EMPLOYEE = 'EMPLOYEE', 'Pegawai / Pengguna'

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.EMPLOYEE,
        verbose_name="Peran Pengguna"
    )
    employee_number = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        unique=True,
        verbose_name="Nomor Pegawai / NIP"
    )
    department = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Unit Kerja / Bagian"
    )
    phone_number = models.CharField(
        max_length=30,
        blank=True,
        verbose_name="Nomor Kontak / Telepon"
    )

    class Meta:
        verbose_name = "Pengguna"
        verbose_name_plural = "Daftar Pengguna"
        ordering = ['username']

    def __str__(self):
        name = self.get_full_name() or self.username
        if self.employee_number:
            return f"{name} (NIP: {self.employee_number})"
        return f"{name} [{self.get_role_display()}]"

    @property
    def is_admin_role(self):
        return self.role == self.Role.ADMIN or self.is_superuser

    @property
    def is_employee_role(self):
        return self.role == self.Role.EMPLOYEE

    @property
    def display_name(self):
        return self.get_full_name() or self.username
