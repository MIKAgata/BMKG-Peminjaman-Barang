# Technical Decisions Record (TDR)

Proyek: **Sistem Informasi Peminjaman, Penyerahan, dan Pengembalian Barang**  
Platform: Python 3.14 / Django 5.2 / SQLite (dev/test) & PostgreSQL compatible  
Tanggal Dokumen: 2026-10-20  

---

## 1. Arsitektur Aplikasi Django

Untuk menjaga separation of concerns dan kemudahan pengujian, proyek dibagi menjadi beberapa aplikasi (apps) terfokus:

1. **`accounts`**:
   - Model `CustomUser` turunan `AbstractUser`.
   - Field tambahan: `role` (ADMIN, EMPLOYEE), `employee_number` (NIP), `department` (Unit Kerja/Bagian), `phone_number`.
   - Autentikasi berbasis session, login/logout, update profil, pergantian kata sandi.
   - Mixin & Decorator: `AdminRequiredMixin`, `EmployeeRequiredMixin`, `RoleRequiredMixin`.

2. **`inventory`**:
   - Master data: `Category`, `Location`, `Item`, `AssetUnit` (opsional untuk nomor seri/tag aset).
   - Tipe barang tegas: `LOANABLE` (Barang Pinjaman) vs `CONSUMABLE` (Barang Habis Pakai).
   - Aturan saldo stok & `StockMovement` (ledger perubahan stok).
   - Layanan stok atomik: `InventoryService`.

3. **`loans`**:
   - Transaksi barang pinjaman (`LOANABLE` only).
   - Model `LoanRequest` (header pengajuan), `LoanItem` (rincian barang & jumlah diminta).
   - Model `LoanHandover` (pencatatan serah-terima fisik aktual saat barang benar-benar keluar).
   - Model `ReturnRecord` & `ReturnItem` (pengembalian sebagian/penuh, pemeriksaan kondisi layak/rusak/hilang).
   - Validasi status transisi tegas: `PENDING` -> `APPROVED` / `REJECTED` -> `ACTIVE` -> `PARTIALLY_RETURNED` -> `COMPLETED` / `CANCELLED`.

4. **`consumables`**:
   - Transaksi penyerahan barang habis pakai (`CONSUMABLE` only).
   - Model `ConsumableHandover` & `ConsumableHandoverItem`.
   - Validasi stok tersedia secara atomik, pencatatan penerima dan tujuan dinas.
   - Perubahan status: `CONFIRMED`, `CANCELLED` (dengan reversing stock movement jika dibatalkan oleh admin berwenang).

5. **`reports`**:
   - Dashboard analitik berbasis query agregasi ORM nyata.
   - Laporan peminjaman, pengembalian, penyerahan habis pakai, stok di bawah minimum, barang rusak/hilang, rekapitulasi per unit kerja.
   - Ekspor data: CSV, Excel (`openpyxl`), dan PDF (`reportlab`).
   - Format cetak slip bukti transaksi resmi instansi (Printable A4 CSS).

6. **`audit`**:
   - Model `AuditLog` untuk merekam jejak aksi pengguna (create, update, approve, handover, return, cancel, adjustment).
   - Model `InstitutionSetting` (Nama kantor, alamat, logo, kepala instansi, NIP pimpinan untuk kop surat transaksi).

---

## 2. Model Akuntansi Stok (Stock Ledger & Balances)

Untuk memenuhi PRD bagian 5 & 6 tanpa inkonsistensi:
- Pada model `Item`:
  - `stock_available`: Stok fisik di gudang yang siap dipinjam/diserahkan.
  - `stock_loaned`: Unit yang sedang aktif dipinjam oleh pegawai.
  - `stock_damaged`: Unit yang rusak atau dalam perbaikan (tidak boleh dipinjam).
  - `stock_lost`: Unit yang dilaporkan hilang.
  - Total aset fisik = `stock_available + stock_loaned + stock_damaged + stock_lost`.
  - Untuk `CONSUMABLE`: `stock_loaned = 0`, `stock_damaged = 0`, `stock_lost = 0`.
- Aturan Mutasi:
  - **Pengajuan Peminjaman (`LoanRequest`)**: Status `PENDING` / `APPROVED` **TIDAK** mengubah stok.
  - **Serah-Terima Fisik (`LoanHandover`)**: Mengurangi `stock_available`, menambah `stock_loaned`.
  - **Pengembalian (`ReturnRecord`)**:
    - Kondisi Baik (`USABLE`): Mengurangi `stock_loaned`, menambah `stock_available`.
    - Kondisi Rusak (`DAMAGED`): Mengurangi `stock_loaned`, menambah `stock_damaged` (stok tersedia TIDAK bertambah).
    - Kondisi Hilang (`LOST`): Mengurangi `stock_loaned`, menambah `stock_lost`.
  - **Penyerahan Habis Pakai (`ConsumableHandover`)**: Mengurangi `stock_available`.
  - **Semua mutasi** wajib memanggil `record_movement()` yang mencatat row pada `StockMovement` dalam blok `transaction.atomic()`.

---

## 3. Format Penomoran Dokumen Transaksi Unik

Format nomor dokumen terstandar instansi:
- Peminjaman: `PINJ-YYYYMM-XXXX` (contoh: `PINJ-202610-0001`)
- Bukti Serah Terima: `SRH-YYYYMM-XXXX` (contoh: `SRH-202610-0001`)
- Bukti Pengembalian: `KMB-YYYYMM-XXXX` (contoh: `KMB-202610-0001`)
- Penyerahan Habis Pakai: `HPK-YYYYMM-XXXX` (contoh: `HPK-202610-0001`)
- Koreksi/Penyesuaian Stok: `ADJ-YYYYMM-XXXX` (contoh: `ADJ-202610-0001`)

---

## 4. Keamanan dan Kontrol Akses

- Password disimpan menggunakan hashing Django PBKDF2/Argon2.
- Semua view diproteksi oleh decorator/mixin izin (`login_required`, `admin_required`, atau filter berbasis `request.user`).
- Pegawai **hanya** dapat melihat riwayat pengajuan dan peminjamannya sendiri (`request.user == loan.borrower`).
- Admin memiliki hak penuh verifikasi, approval, serah-terima, pengembalian, dan penyerahan habis pakai.
- Penolakan dan pembatalan mewajibkan pengisian alasan.
- Transaksi yang sudah memiliki relasi data tidak boleh di-hard-delete, melainkan menggunakan soft-delete / status `CANCELLED` / `is_active=False`.

---

## 5. UI/UX dan Template

- Antarmuka Bahasa Indonesia formal ramah kantor pemerintahan.
- Bootstrap 5 via CDN/local vendor assets, FontAwesome / Bootstrap Icons.
- Layout responsive dengan Sidebar navigasi dinamis sesuai peran (Admin vs Pegawai).
- Notifikasi flash messages Django (`messages.success`, `messages.warning`, `messages.error`).
- Halaman error kustom: `403.html`, `404.html`, `500.html`.
