from django.db import models
from django.conf import settings


class AuditLog(models.Model):
    class Action(models.TextChoices):
        LOGIN = 'LOGIN', 'Masuk Sistem'
        LOGOUT = 'LOGOUT', 'Keluar Sistem'
        CREATE = 'CREATE', 'Tambah Data'
        UPDATE = 'UPDATE', 'Ubah Data'
        DELETE = 'DELETE', 'Hapus Data / Nonaktif'
        APPROVE = 'APPROVE', 'Persetujuan'
        REJECT = 'REJECT', 'Penolakan'
        HANDOVER = 'HANDOVER', 'Serah Terima Fisik'
        RETURN = 'RETURN', 'Pengembalian'
        CONSUMABLE_ISSUE = 'CONSUMABLE_ISSUE', 'Penyerahan Habis Pakai'
        CANCEL = 'CANCEL', 'Pembatalan Transaksi'
        STOCK_ADJUSTMENT = 'STOCK_ADJUSTMENT', 'Penyesuaian Stok'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
        verbose_name="Pengguna"
    )
    action = models.CharField(max_length=50, choices=Action.choices, verbose_name="Aksi")
    entity_type = models.CharField(max_length=100, verbose_name="Tipe Objek")
    entity_id = models.CharField(max_length=100, blank=True, verbose_name="ID Objek")
    details = models.JSONField(default=dict, blank=True, verbose_name="Rincian / Perubahan")
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name="Alamat IP")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Waktu Aksi")

    class Meta:
        verbose_name = "Audit Log"
        verbose_name_plural = "Daftar Audit Log"
        ordering = ['-created_at']

    def __str__(self):
        user_str = self.user.username if self.user else "Sistem"
        return f"[{self.created_at:%Y-%m-%d %H:%M}] {user_str} - {self.get_action_display()} ({self.entity_type})"


class InstitutionSetting(models.Model):
    institution_name = models.CharField(
        max_length=200,
        default="Badan Meteorologi, Klimatologi, dan Geofisika (BMKG)",
        verbose_name="Nama Instansi / Kantor"
    )
    unit_name = models.CharField(
        max_length=200,
        default="Bagian Umum dan Tata Usaha",
        blank=True,
        verbose_name="Nama Sub-Unit / Bagian"
    )
    address = models.TextField(
        blank=True,
        default="Jl. Angkasa I No.2, Kemayoran, Jakarta Pusat",
        verbose_name="Alamat Kantor"
    )
    phone = models.CharField(
        max_length=50,
        blank=True,
        default="(021) 4246321",
        verbose_name="Nomor Telepon"
    )
    email = models.EmailField(
        blank=True,
        default="inventaris@bmkg.go.id",
        verbose_name="Email Resmi"
    )
    head_officer_name = models.CharField(
        max_length=150,
        blank=True,
        default="Kepala Bagian Umum",
        verbose_name="Nama Pejabat Berwenang"
    )
    head_officer_nip = models.CharField(
        max_length=50,
        blank=True,
        default="19800101 200501 1 001",
        verbose_name="NIP Pejabat Berwenang"
    )
    warehouse_officer_name = models.CharField(
        max_length=150,
        blank=True,
        default="Petugas Pengelola Barang Milik Negara",
        verbose_name="Nama Petugas Pengelola Barang"
    )
    warehouse_officer_nip = models.CharField(
        max_length=50,
        blank=True,
        default="19850512 201001 1 002",
        verbose_name="NIP Petugas Pengelola Barang"
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Terakhir Diperbarui")

    class Meta:
        verbose_name = "Pengaturan Instansi"
        verbose_name_plural = "Pengaturan Instansi"

    def __str__(self):
        return self.institution_name
