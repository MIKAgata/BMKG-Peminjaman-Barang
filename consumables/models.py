from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ValidationError
from inventory.models import Item


def generate_consumable_number():
    """Format: HPK-YYYYMM-XXXX"""
    now = timezone.now()
    prefix = f"HPK-{now:%Y%m}-"
    last = ConsumableHandover.objects.filter(handover_number__startswith=prefix).order_by('-handover_number').first()
    if last:
        try:
            seq = int(last.handover_number.split('-')[-1]) + 1
        except (ValueError, IndexError):
            seq = 1
    else:
        seq = 1
    return f"{prefix}{seq:04d}"


class ConsumableHandover(models.Model):
    class Status(models.TextChoices):
        CONFIRMED = 'CONFIRMED', 'Dikonfirmasi (Stok Berkurang)'
        CANCELLED = 'CANCELLED', 'Dibatalkan (Stok Dikembalikan)'

    handover_number = models.CharField(max_length=50, unique=True, default=generate_consumable_number, verbose_name="Nomor Bukti Penyerahan")
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='consumable_receipts', verbose_name="Pegawai Penerima")
    department = models.CharField(max_length=100, blank=True, verbose_name="Unit Kerja / Bidang")
    handover_date = models.DateTimeField(default=timezone.now, verbose_name="Waktu Penyerahan")
    purpose = models.TextField(verbose_name="Tujuan / Keperluan Dinas")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.CONFIRMED, verbose_name="Status Transaksi")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='created_consumables', verbose_name="Petugas Penyerah")
    cancellation_reason = models.TextField(blank=True, verbose_name="Alasan Pembatalan")
    notes = models.TextField(blank=True, verbose_name="Catatan")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Penyerahan Barang Habis Pakai"
        verbose_name_plural = "Daftar Penyerahan Barang Habis Pakai"
        ordering = ['-handover_date']

    def __str__(self):
        return f"{self.handover_number} - {self.recipient.display_name} ({self.get_status_display()})"

    @property
    def total_quantity(self):
        return sum(item.quantity for item in self.items.all())


class ConsumableHandoverItem(models.Model):
    handover = models.ForeignKey(ConsumableHandover, on_delete=models.CASCADE, related_name='items')
    item = models.ForeignKey(Item, on_delete=models.PROTECT, related_name='consumable_items', verbose_name="Barang Habis Pakai")
    quantity = models.IntegerField(verbose_name="Jumlah Diserahkan")
    notes = models.CharField(max_length=200, blank=True, verbose_name="Catatan")

    class Meta:
        verbose_name = "Rincian Barang Habis Pakai"
        verbose_name_plural = "Rincian Barang Habis Pakai"
        unique_together = ('handover', 'item')

    def __str__(self):
        return f"{self.item.name} ({self.quantity} {self.item.unit})"

    def clean(self):
        super().clean()
        if self.item.item_type != Item.ItemType.CONSUMABLE:
            raise ValidationError({'item': f"Barang '{self.item.name}' adalah BARANG PINJAMAN, bukan habis pakai."})
        if self.quantity <= 0:
            raise ValidationError({'quantity': "Jumlah penyerahan harus lebih dari 0."})
