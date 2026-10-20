from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Nama Kategori")
    description = models.TextField(blank=True, verbose_name="Keterangan")
    is_active = models.BooleanField(default=True, verbose_name="Aktif")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Dibuat Pada")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Diperbarui Pada")

    class Meta:
        verbose_name = "Kategori Barang"
        verbose_name_plural = "Daftar Kategori Barang"
        ordering = ['name']

    def __str__(self):
        return self.name


class Location(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Nama Lokasi / Ruang")
    description = models.TextField(blank=True, verbose_name="Keterangan / Posisi")
    is_active = models.BooleanField(default=True, verbose_name="Aktif")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Dibuat Pada")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Diperbarui Pada")

    class Meta:
        verbose_name = "Lokasi Penyimpanan"
        verbose_name_plural = "Daftar Lokasi Penyimpanan"
        ordering = ['name']

    def __str__(self):
        return self.name


class Item(models.Model):
    class ItemType(models.TextChoices):
        LOANABLE = 'LOANABLE', 'Barang Pinjaman (Wajib Kembali)'
        CONSUMABLE = 'CONSUMABLE', 'Barang Habis Pakai (Non-Kembali)'

    code = models.CharField(max_length=50, unique=True, verbose_name="Kode Barang")
    name = models.CharField(max_length=200, verbose_name="Nama Barang")
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='items', verbose_name="Kategori")
    item_type = models.CharField(max_length=20, choices=ItemType.choices, verbose_name="Tipe Barang")
    unit = models.CharField(max_length=30, default="Unit", verbose_name="Satuan (Unit, Rim, Buah, dll.)")
    location = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True, blank=True, related_name='items', verbose_name="Lokasi Penyimpanan")
    brand = models.CharField(max_length=100, blank=True, verbose_name="Merek / Model")
    description = models.TextField(blank=True, verbose_name="Deskripsi / Spesifikasi")

    # Stock Saldo Fields
    stock_available = models.IntegerField(default=0, verbose_name="Stok Tersedia (Gudang)")
    stock_loaned = models.IntegerField(default=0, verbose_name="Stok Sedang Dipinjam")
    stock_damaged = models.IntegerField(default=0, verbose_name="Stok Rusak / Perbaikan")
    stock_lost = models.IntegerField(default=0, verbose_name="Stok Hilang")
    minimum_stock = models.IntegerField(default=0, verbose_name="Batas Minimum Stok")

    is_active = models.BooleanField(default=True, verbose_name="Status Aktif")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Dibuat Pada")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Diperbarui Pada")

    class Meta:
        verbose_name = "Barang"
        verbose_name_plural = "Daftar Barang"
        ordering = ['name']

    def __str__(self):
        return f"{self.code} - {self.name} [{self.get_item_type_display()}]"

    def clean(self):
        super().clean()
        if self.stock_available < 0:
            raise ValidationError({'stock_available': "Stok tersedia tidak boleh bernilai negatif."})
        if self.stock_loaned < 0:
            raise ValidationError({'stock_loaned': "Stok dipinjam tidak boleh bernilai negatif."})
        if self.stock_damaged < 0:
            raise ValidationError({'stock_damaged': "Stok rusak tidak boleh bernilai negatif."})
        if self.stock_lost < 0:
            raise ValidationError({'stock_lost': "Stok hilang tidak boleh bernilai negatif."})
        if self.minimum_stock < 0:
            raise ValidationError({'minimum_stock': "Batas minimum stok tidak boleh negatif."})

        # CONSUMABLE items cannot have loaned, damaged, or lost balances
        if self.item_type == self.ItemType.CONSUMABLE:
            if self.stock_loaned > 0:
                raise ValidationError({'stock_loaned': "Barang habis pakai tidak boleh memiliki status pinjam."})
            if self.stock_damaged > 0:
                raise ValidationError({'stock_damaged': "Barang habis pakai tidak menggunakan status stok rusak."})
            if self.stock_lost > 0:
                raise ValidationError({'stock_lost': "Barang habis pakai tidak menggunakan status stok hilang."})

    @property
    def total_stock(self):
        return self.stock_available + self.stock_loaned + self.stock_damaged + self.stock_lost

    @property
    def is_loanable(self):
        return self.item_type == self.ItemType.LOANABLE

    @property
    def is_consumable(self):
        return self.item_type == self.ItemType.CONSUMABLE

    @property
    def is_low_stock(self):
        return self.stock_available <= self.minimum_stock


class AssetUnit(models.Model):
    class Condition(models.TextChoices):
        USABLE = 'USABLE', 'Baik / Layak Pakai'
        DAMAGED = 'DAMAGED', 'Rusak / Perlu Perbaikan'
        LOST = 'LOST', 'Hilang'

    class Status(models.TextChoices):
        AVAILABLE = 'AVAILABLE', 'Tersedia di Gudang'
        LOANED = 'LOANED', 'Sedang Dipinjam'
        UNDER_REPAIR = 'UNDER_REPAIR', 'Dalam Perbaikan'
        DISPOSED = 'DISPOSED', 'Dihapuskan / Afkir'

    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='asset_units', verbose_name="Barang Induk")
    asset_code = models.CharField(max_length=100, unique=True, verbose_name="Nomor Barcode / Kode Aset NUP")
    serial_number = models.CharField(max_length=100, blank=True, verbose_name="Nomor Seri Pabrik (S/N)")
    condition = models.CharField(max_length=20, choices=Condition.choices, default=Condition.USABLE, verbose_name="Kondisi Fisik")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.AVAILABLE, verbose_name="Status Unit")
    location = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Lokasi Unit")
    notes = models.TextField(blank=True, verbose_name="Catatan")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Unit Aset Serial"
        verbose_name_plural = "Daftar Unit Aset Serial"
        ordering = ['asset_code']

    def __str__(self):
        return f"{self.asset_code} ({self.item.name})"


class StockMovement(models.Model):
    class MovementType(models.TextChoices):
        INITIAL = 'INITIAL', 'Saldo Awal'
        HANDOVER_LOAN = 'HANDOVER_LOAN', 'Penyerahan Pinjaman'
        RETURN_USABLE = 'RETURN_USABLE', 'Pengembalian Layak'
        RETURN_DAMAGED = 'RETURN_DAMAGED', 'Pengembalian Rusak'
        RETURN_LOST = 'RETURN_LOST', 'Pengembalian Hilang'
        CONSUMABLE_ISSUE = 'CONSUMABLE_ISSUE', 'Penyerahan Habis Pakai'
        ADJUSTMENT = 'ADJUSTMENT', 'Penyesuaian Manual Admin'
        CANCELLATION = 'CANCELLATION', 'Pembatalan Transaksi'

    item = models.ForeignKey(Item, on_delete=models.PROTECT, related_name='movements', verbose_name="Barang")
    movement_type = models.CharField(max_length=30, choices=MovementType.choices, verbose_name="Jenis Mutasi")
    quantity = models.IntegerField(verbose_name="Jumlah Unit")
    stock_available_before = models.IntegerField(verbose_name="Stok Tersedia Sebelum")
    stock_available_after = models.IntegerField(verbose_name="Stok Tersedia Sesudah")
    stock_loaned_before = models.IntegerField(default=0, verbose_name="Stok Dipinjam Sebelum")
    stock_loaned_after = models.IntegerField(default=0, verbose_name="Stok Dipinjam Sesudah")
    reference_number = models.CharField(max_length=100, blank=True, verbose_name="Nomor Referensi Transaksi")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Dicatat Oleh")
    reason = models.TextField(verbose_name="Alasan / Keterangan Mutasi")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Waktu Mutasi")

    class Meta:
        verbose_name = "Buku Mutasi Stok"
        verbose_name_plural = "Buku Mutasi Stok"
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.created_at:%Y-%m-%d %H:%M}] {self.item.name} - {self.get_movement_type_display()} ({self.quantity} unit)"
