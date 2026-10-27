from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ValidationError
from inventory.models import Item


def generate_loan_number():
    """Format: PINJ-YYYYMM-XXXX"""
    now = timezone.now()
    prefix = f"PINJ-{now:%Y%m}-"
    last = LoanRequest.objects.filter(loan_number__startswith=prefix).order_by('-loan_number').first()
    if last:
        try:
            seq = int(last.loan_number.split('-')[-1]) + 1
        except (ValueError, IndexError):
            seq = 1
    else:
        seq = 1
    return f"{prefix}{seq:04d}"


def generate_handover_number():
    """Format: SRH-YYYYMM-XXXX"""
    now = timezone.now()
    prefix = f"SRH-{now:%Y%m}-"
    last = LoanHandover.objects.filter(handover_number__startswith=prefix).order_by('-handover_number').first()
    if last:
        try:
            seq = int(last.handover_number.split('-')[-1]) + 1
        except (ValueError, IndexError):
            seq = 1
    else:
        seq = 1
    return f"{prefix}{seq:04d}"


def generate_return_number():
    """Format: KMB-YYYYMM-XXXX"""
    now = timezone.now()
    prefix = f"KMB-{now:%Y%m}-"
    last = ReturnRecord.objects.filter(return_number__startswith=prefix).order_by('-return_number').first()
    if last:
        try:
            seq = int(last.return_number.split('-')[-1]) + 1
        except (ValueError, IndexError):
            seq = 1
    else:
        seq = 1
    return f"{prefix}{seq:04d}"


class LoanRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Menunggu Persetujuan'
        APPROVED = 'APPROVED', 'Disetujui (Menunggu Penyerahan Fisik)'
        REJECTED = 'REJECTED', 'Ditolak'
        ACTIVE = 'ACTIVE', 'Aktif (Barang Sedang Dipinjam)'
        PARTIALLY_RETURNED = 'PARTIALLY_RETURNED', 'Kembali Sebagian'
        COMPLETED = 'COMPLETED', 'Selesai (Semua Telah Kembali)'
        CANCELLED = 'CANCELLED', 'Dibatalkan'

    loan_number = models.CharField(max_length=50, unique=True, default=generate_loan_number, verbose_name="Nomor Peminjaman")
    borrower = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='loans', verbose_name="Peminjam / Pegawai")
    start_date = models.DateField(verbose_name="Tanggal Rencana Pinjam")
    due_date = models.DateField(verbose_name="Batas Waktu Pengembalian (Jatuh Tempo)")
    purpose = models.TextField(verbose_name="Tujuan / Keperluan Peminjaman")
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.PENDING, verbose_name="Status Peminjaman")

    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='reviewed_loans', verbose_name="Ditinjau Oleh")
    reviewed_at = models.DateTimeField(null=True, blank=True, verbose_name="Waktu Peninjauan")
    rejection_reason = models.TextField(blank=True, verbose_name="Alasan Penolakan")
    cancellation_reason = models.TextField(blank=True, verbose_name="Alasan Pembatalan")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Waktu Pengajuan")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Terakhir Diperbarui")

    class Meta:
        verbose_name = "Pengajuan Peminjaman"
        verbose_name_plural = "Daftar Pengajuan Peminjaman"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.loan_number} - {self.borrower.display_name} ({self.get_status_display()})"

    def clean(self):
        super().clean()
        if self.start_date and self.due_date and self.due_date < self.start_date:
            raise ValidationError({'due_date': "Tanggal jatuh tempo tidak boleh lebih awal dari tanggal pinjam."})

    @property
    def is_overdue(self):
        if self.status in [self.Status.ACTIVE, self.Status.PARTIALLY_RETURNED]:
            return timezone.now().date() > self.due_date
        return False

    @property
    def total_items_requested(self):
        return sum(item.quantity_requested for item in self.items.all())

    @property
    def total_items_handed_over(self):
        return sum(item.quantity_handed_over for item in self.items.all())

    @property
    def total_items_returned(self):
        return sum(
            item.quantity_returned_usable + item.quantity_returned_damaged + item.quantity_returned_lost
            for item in self.items.all()
        )

    @property
    def total_items_pending_return(self):
        return self.total_items_handed_over - self.total_items_returned


class LoanItem(models.Model):
    loan = models.ForeignKey(LoanRequest, on_delete=models.CASCADE, related_name='items', verbose_name="Surat Peminjaman")
    item = models.ForeignKey(Item, on_delete=models.PROTECT, related_name='loan_items', verbose_name="Barang Pinjaman")
    quantity_requested = models.IntegerField(verbose_name="Jumlah Diminta")
    quantity_handed_over = models.IntegerField(default=0, verbose_name="Jumlah Telah Diserahkan")
    quantity_returned_usable = models.IntegerField(default=0, verbose_name="Jumlah Kembali Layak")
    quantity_returned_damaged = models.IntegerField(default=0, verbose_name="Jumlah Kembali Rusak")
    quantity_returned_lost = models.IntegerField(default=0, verbose_name="Jumlah Hilang")
    notes = models.CharField(max_length=200, blank=True, verbose_name="Catatan")

    class Meta:
        verbose_name = "Item Pinjaman"
        verbose_name_plural = "Item Pinjaman"
        unique_together = ('loan', 'item')

    def __str__(self):
        return f"{self.item.name} ({self.quantity_requested} {self.item.unit})"

    def clean(self):
        super().clean()

        # Jangan validasi jika barang belum dipilih
        if not self.item_id:
            return

        # Barang yang dipinjam harus bertipe LOANABLE
        if self.item.item_type != Item.ItemType.LOANABLE:
            raise ValidationError({
                'item': (
                    f"Barang '{self.item.name}' bertipe HABIS PAKAI "
                    "dan tidak boleh dipinjam."
                )
            })

        # Jumlah yang diminta harus lebih dari nol
        if (
            self.quantity_requested is not None
            and self.quantity_requested <= 0
        ):
            raise ValidationError({
                'quantity_requested': "Jumlah yang diminta harus lebih dari 0."
            })
    
    @property
    def quantity_remaining_to_handover(self):
        return max(0, self.quantity_requested - self.quantity_handed_over)

    @property
    def total_returned(self):
        return self.quantity_returned_usable + self.quantity_returned_damaged + self.quantity_returned_lost

    @property
    def quantity_remaining_to_return(self):
        return max(0, self.quantity_handed_over - self.total_returned)

    @property
    def is_fully_returned(self):
        return self.quantity_handed_over > 0 and self.quantity_remaining_to_return == 0


class LoanHandover(models.Model):
    handover_number = models.CharField(max_length=50, unique=True, default=generate_handover_number, verbose_name="Nomor Bukti Serah Terima")
    loan = models.ForeignKey(LoanRequest, on_delete=models.PROTECT, related_name='handovers', verbose_name="Peminjaman Terkait")
    handover_date = models.DateTimeField(default=timezone.now, verbose_name="Waktu Serah Terima")
    handed_over_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='handed_over_records', verbose_name="Petugas Penyerah")
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='received_handover_records', verbose_name="Pegawai Penerima")
    notes = models.TextField(blank=True, verbose_name="Catatan Serah Terima")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Bukti Serah Terima Pinjaman"
        verbose_name_plural = "Daftar Bukti Serah Terima Pinjaman"
        ordering = ['-handover_date']

    def __str__(self):
        return f"{self.handover_number} - {self.loan.loan_number}"


class LoanHandoverItem(models.Model):
    handover = models.ForeignKey(LoanHandover, on_delete=models.CASCADE, related_name='items')
    loan_item = models.ForeignKey(LoanItem, on_delete=models.PROTECT, related_name='handover_items')
    quantity = models.IntegerField(verbose_name="Jumlah Diserahkan")
    initial_condition = models.CharField(max_length=50, default="Baik / Layak Pakai", verbose_name="Kondisi Saat Keluar")
    notes = models.CharField(max_length=200, blank=True)

    class Meta:
        verbose_name = "Rincian Barang Serah Terima"
        verbose_name_plural = "Rincian Barang Serah Terima"

    def __str__(self):
        return f"{self.loan_item.item.name} ({self.quantity})"


class ReturnRecord(models.Model):
    return_number = models.CharField(max_length=50, unique=True, default=generate_return_number, verbose_name="Nomor Bukti Pengembalian")
    loan = models.ForeignKey(LoanRequest, on_delete=models.PROTECT, related_name='returns', verbose_name="Peminjaman Terkait")
    return_date = models.DateTimeField(default=timezone.now, verbose_name="Waktu Pengembalian")
    received_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='received_return_records', verbose_name="Petugas Penerima")
    notes = models.TextField(blank=True, verbose_name="Catatan Pengembalian")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Bukti Pengembalian Barang"
        verbose_name_plural = "Daftar Bukti Pengembalian Barang"
        ordering = ['-return_date']

    def __str__(self):
        return f"{self.return_number} - {self.loan.loan_number}"


class ReturnItem(models.Model):
    return_record = models.ForeignKey(ReturnRecord, on_delete=models.CASCADE, related_name='items')
    loan_item = models.ForeignKey(LoanItem, on_delete=models.PROTECT, related_name='return_items')
    quantity_usable = models.IntegerField(default=0, verbose_name="Kembali Kondisi Layak")
    quantity_damaged = models.IntegerField(default=0, verbose_name="Kembali Kondisi Rusak")
    quantity_lost = models.IntegerField(default=0, verbose_name="Dilaporkan Hilang")
    damage_notes = models.TextField(blank=True, verbose_name="Keterangan Kerusakan / Kehilangan")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Rincian Pengembalian Barang"
        verbose_name_plural = "Rincian Pengembalian Barang"

    def __str__(self):
        return f"{self.loan_item.item.name} (Kembali: {self.total_returned})"

    @property
    def total_returned(self):
        return self.quantity_usable + self.quantity_damaged + self.quantity_lost
