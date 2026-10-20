# Rencana Implementasi (Implementation Plan)

Proyek: **Sistem Informasi Peminjaman, Penyerahan, dan Pengembalian Barang**  
Platform: Django 5.2 / Python 3.14  
Dokumen Acuan: `PRD_Sistem_Peminjaman_Penyerahan_Barang_Django.txt`  
Tanggal: 2026-10-20  

---

## 1. Struktur Modul & Bobot Progres

Progres dihitung berdasarkan pencapaian tugas terverifikasi (Verified Code & Passed Tests) dengan pembobotan berikut:

| Tahap | Modul & Fokus Utama | Bobot | Target Luaran |
|---|---|:---:|---|
| **Tahap 0** | Pemeriksaan, Perencanaan & Dokumen Desain | 5% | Analisis PRD, Dokumen Rencana, TDR, Setup Struktur |
| **Tahap 1** | Fondasi Proyek, Konfigurasi & Autentikasi | 10% | Django Project, CustomUser Model, Roles, Base Templates, Auth Views |
| **Tahap 2** | Master Data Barang, Kategori, Lokasi & Pegawai | 12% | CRUD Master, Validasi Tipe LOANABLE vs CONSUMABLE, Saldo Stok Awal |
| **Tahap 3** | Transaksi Peminjaman (Pengajuan, Persetujuan, Serah Terima) | 15% | Pengajuan Pegawai, Approval/Rejection Admin, Serah Terima Fisik, Stok Keluar |
| **Tahap 4** | Transaksi Pengembalian (Sebagian/Penuh & Kondisi Barang) | 15% | Return Form, Pemeriksaan Fisik, Penanganan Rusak/Hilang, Stok Kembali |
| **Tahap 5** | Penyerahan Barang Habis Pakai (CONSUMABLE) | 12% | Penyerahan ATK, Pengurangan Stok, Slip Penyerahan, Validasi Non-Returnable |
| **Tahap 6** | Dashboard Analitik & Modul Laporan | 13% | Dashboard Real-time Admin & Pegawai, Filter Laporan, Cetak PDF/Excel/CSV |
| **Tahap 7** | Audit Log, Pengaturan Instansi & Penguatan Keamanan | 10% | Audit Trail, Institution Profile, Error Pages (403, 404, 500), Permission Test |
| **Tahap 8** | Verifikasi Akhir, Pengujian Menyeluruh (E2E) & Laporan Akhir | 8% | Run Full Test Suite, Smoke Testing, Verifikasi 20 Acceptance Criteria |
| **Total** | | **100%** | |

---

## 2. Rincian Checklist Pekerjaan per Tahap

### Tahap 0 — Pemeriksaan dan Perencanaan (Bobot: 5%)
- [x] Periksa lingkungan Python, virtual environment, dan dependensi (Python 3.14, Django 5.2).
- [x] Baca dan pahami seluruh isi `PRD_Sistem_Peminjaman_Penyerahan_Barang_Django.txt`.
- [x] Susun dokumen arsitektur dan keputusan teknis (`docs/TECHNICAL_DECISIONS.md`).
- [x] Buat dokumen rencana kerja dan pembobotan (`docs/IMPLEMENTATION_PLAN.md`).
- [x] Siapkan file pelacakan progres (`PROGRESS.md`), riwayat perubahan (`CHANGELOG.md`), dan laporan pengujian (`docs/TEST_REPORT.md`).

### Tahap 1 — Fondasi Proyek, Konfigurasi & Autentikasi (Bobot: 10%)
- [x] Inisialisasi Django project (`config`) dan struktur apps (`accounts`, `inventory`, `loans`, `consumables`, `reports`, `audit`).
- [x] Buat file konfigurasi `.env` dan `.env.example`.
- [x] Konfigurasi `settings.py` (Custom User Model, Localization id-ID, Static/Media dirs, Messages tags).
- [x] Implementasikan `CustomUser` model di aplikasi `accounts` dengan role `ADMIN` dan `EMPLOYEE`.
- [x] Buat migrasi awal untuk aplikasi `accounts` dan terapkan ke database.
- [x] Buat view & template login, logout, profil, dan ganti kata sandi.
- [x] Buat base templates responsif (`base.html`, `navbar.html`, `sidebar.html`, `alerts.html`).
- [x] Tulis unit test untuk model `CustomUser` dan autentikasi login/logout/permission check.

### Tahap 2 — Master Data Barang, Kategori, Lokasi & Pegawai (Bobot: 12%)
- [x] Model `Category`, `Location`, `Item`, `AssetUnit`, `StockMovement` di aplikasi `inventory`.
- [x] Validasi tipe barang (`LOANABLE` vs `CONSUMABLE`), kode barang unik, dan aturan saldo stok.
- [x] Views & Forms CRUD Kategori, Lokasi, dan Barang dengan permission admin.
- [x] View Manajemen Akun/Data Pegawai bagi Admin.
- [x] Implementasi fitur pencarian, filter kategori/tipe, dan pagination pada tabel master data.
- [x] Tulis unit test untuk validasi model master data, isolasi tipe barang, dan batasan integritas data.

### Tahap 3 — Transaksi Peminjaman (LOANABLE) (Bobot: 15%)
- [x] Model `LoanRequest`, `LoanItem`, `LoanHandover`, `LoanHandoverItem` di aplikasi `loans`.
- [x] Formulir pengajuan peminjaman barang LOANABLE oleh pegawai.
- [x] Validasi stok tersedia dan penolakan peminjaman barang CONSUMABLE pada form pengajuan.
- [x] Antarmuka admin untuk verifikasi pengajuan: Persetujuan (`APPROVED`) atau Penolakan (`REJECTED`) dengan catatan/alasan.
- [x] Antarmuka serah-terima fisik (`LoanHandover`): Mencatat tanggal serah terima, kondisi awal keluar, dan petugas penyerah.
- [x] Mutasi stok otomatis: Stok tersedia berkurang, stok dipinjam bertambah, catat `StockMovement`.
- [x] Tulis unit test untuk alur peminjaman, proteksi stok saat pengajuan vs serah-terima, dan nomor transaksi unik.

### Tahap 4 — Transaksi Pengembalian & Kondisi Barang (Bobot: 15%)
- [x] Model `ReturnRecord` dan `ReturnItem` di aplikasi `loans`.
- [x] Antarmuka pengembalian barang pinjaman aktif untuk admin/petugas.
- [x] Dukungan pengembalian penuh atau pengembalian sebagian (`PARTIALLY_RETURNED`).
- [x] Validasi: Jumlah yang dikembalikan tidak boleh melebihi sisa pinjaman aktif.
- [x] Pemeriksaan kondisi saat kembali: Layak Pakai (`USABLE`), Rusak (`DAMAGED`), atau Hilang (`LOST`).
- [x] Mutasi stok yang akurat: Barang layak menambah stok tersedia; barang rusak masuk stok rusak (TIDAK menambah stok tersedia).
- [x] Pembaruan status peminjaman menjadi `COMPLETED` jika semua item telah diselesaikan.
- [x] Tulis unit test untuk validasi pengembalian berlebih, pembaruan stok sesuai kondisi, dan transisi status.

### Tahap 5 — Penyerahan Barang Habis Pakai (CONSUMABLE) (Bobot: 12%)
- [x] Model `ConsumableHandover` dan `ConsumableHandoverItem` di aplikasi `consumables`.
- [x] Formulir penyerahan ATK/barang habis pakai oleh admin/petugas (penerima, unit kerja, tujuan dinas).
- [x] Validasi ketat: Hanya barang tipe `CONSUMABLE` yang dapat dipilih, stok tersedia harus mencukupi.
- [x] Konfirmasi transaksi secara atomik (`transaction.atomic()`): Pengurangan stok tersedia dan pencatatan `StockMovement`.
- [x] Fasilitas pembatalan transaksi dengan jejak audit dan reversing stock movement.
- [x] Tulis unit test untuk isolasi barang habis pakai, penolakan stok minus, dan konsistensi ledger.

### Tahap 6 — Dashboard Analitik & Modul Laporan (Bobot: 13%)
- [x] Dashboard Admin: Ringkasan stok, barang dipinjam, pengajuan pending, peminjaman jatuh tempo/terlambat, transaksi terbaru.
- [x] Dashboard Pegawai: Ringkasan pengajuan pribadi, peminjaman aktif milik sendiri, tanggal jatuh tempo, riwayat transaksi.
- [x] Laporan terintegrasi: Filter tanggal, jenis transaksi, kategori, status, dan unit kerja.
- [x] Ekspor data ke format CSV, format Excel (`openpyxl`), dan format PDF (`reportlab`).
- [x] Halaman cetak slip bukti resmi (Bukti Peminjaman, Serah Terima, Pengembalian, Penyerahan Habis Pakai).
- [x] Tulis unit test untuk akurasi agregasi data dashboard dan validitas file ekspor laporan.

### Tahap 7 — Audit Log, Pengaturan Instansi & Keamanan (Bobot: 10%)
- [x] Model `AuditLog` dan service pencatat aktivitas sistem (peminjaman, serah terima, pengembalian, penyerahan, koreksi stok).
- [x] Halaman penampil Audit Log khusus admin dengan filter pengguna, aksi, dan rentang waktu.
- [x] Model dan halaman `InstitutionSetting` (Nama kantor/instansi, alamat, nomor kontak, nama & NIP pimpinan/petugas).
- [x] Halaman error kustom responsif: 403 Forbidden, 404 Not Found, 500 Server Error.
- [x] Pemeriksaan menyeluruh permission semua view: Uji proteksi IDOR (pegawai tidak bisa membuka transaksi orang lain).
- [x] Tulis unit test untuk audit trail, isolasi multi-user, dan penanganan error.

### Tahap 8 — Verifikasi Akhir & Pengujian Menyeluruh (Bobot: 8%)
- [x] Eksekusi `python manage.py check`.
- [x] Eksekusi `python manage.py makemigrations --check --dry-run`.
- [x] Eksekusi rangkaian lengkap `python manage.py test`.
- [x] Verifikasi ke-20 kriteria penerimaan (Acceptance Criteria) PRD.
- [x] Pembuatan data awal / seeder demonstrasi jika diperlukan untuk pengujian langsung (`init_data` command).
- [x] Dokumentasi lengkap instruksi instalasi dan penggunaan pada `README.md`.
- [x] Pembaruan akhir `PROGRESS.md`, `TEST_REPORT.md`, dan `CHANGELOG.md`.
