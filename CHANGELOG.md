# Changelog

Semua perubahan pada proyek **Sistem Informasi Peminjaman, Penyerahan, dan Pengembalian Barang** dicatat dalam file ini.

Format changelog mengacu pada [Keep a Changelog](https://keepachangelog.com/id/1.0.0/).

## [1.0.0] - 2026-10-20

### Ditambahkan
- **Inisialisasi & Fondasi Proyek (Tahap 1)**:
  - Custom User model `CustomUser` dengan peran `ADMIN` dan `EMPLOYEE`.
  - Sistem otentikasi (login, logout, profil pengguna, perubahan password).
  - Base template antarmuka responsif dengan Bootstrap modern.
- **Master Data Inventaris (Tahap 2)**:
  - Model `Category`, `Location`, `Item`, `AssetUnit`, dan `StockMovement`.
  - Pemisahan ketat barang `LOANABLE` dan `CONSUMABLE`.
  - Formulir dan halaman CRUD master data dengan pencarian dan filter.
- **Modul Peminjaman Barang (Tahap 3)**:
  - Pengajuan peminjaman multi-barang oleh pegawai.
  - Alur persetujuan admin (`APPROVED` / `REJECTED`).
  - Serah-terima fisik terpisah (`LoanHandover`) yang memotong stok tersedia.
  - Penomoran dokumen transaksi terstruktur otomatis (`PINJ-YYYYMM-XXXX`, `SRH-YYYYMM-XXXX`).
- **Modul Pengembalian & Kondisi Fisik (Tahap 4)**:
  - Pencatatan pengembalian penuh atau parsial (`PARTIALLY_RETURNED`).
  - Evaluasi kondisi fisik barang: Layak (`USABLE`), Rusak (`DAMAGED`), atau Hilang (`LOST`).
  - Proteksi stok rusak/hilang agar tidak langsung menambah saldo tersedia.
- **Modul Penyerahan Barang Habis Pakai (Tahap 5)**:
  - Pencatatan penyerahan ATK operasional unit tanpa kewajiban kembali (`CONFIRMED`).
  - Pembatalan transaksi dengan jurnal pembalik stok otomatis.
- **Modul Laporan & Dashboard (Tahap 6)**:
  - Dashboard analitik real-time terpisah untuk Administrator dan Pegawai.
  - Laporan peminjaman, pengembalian, penyerahan habis pakai, dan saldo stok.
  - Ekspor data laporan multi-format: CSV, Microsoft Excel (`.xlsx`), dan PDF.
  - Cetak slip bukti transaksi resmi standar A4.
- **Keamanan, Audit Log & Pengaturan Instansi (Tahap 7)**:
  - Jejak audit komprehensif pada `AuditLog`.
  - Pencegahan pemalsuan identitas peminjam dan proteksi IDOR.
  - Konfigurasi kop surat dan data pejabat pada `InstitutionSetting`.
  - Halaman error kustom 403, 404, dan 500.
- **Seeder Data & Verifikasi Menyeluruh (Tahap 8)**:
  - Command seeder `python manage.py init_data` untuk instan demo master & transaksi.
  - Rangkaian pengujian otomatis 55 test case (termasuk 20 acceptance criteria PRD) lulus 100%.

### Tahap 0 — Perencanaan & Desain Arsitektur (2026-10-20)
- Memeriksa lingkungan sistem (Python 3.14, virtualenv, Django 5.2, openpyxl, reportlab).
- Mempelajari dan menganalisis 100% persyaratan dalam `PRD_Sistem_Peminjaman_Penyerahan_Barang_Django.txt`.
- Menyusun arsitektur sistem, aturan saldo stok, penomoran dokumen, dan kontrol peran pada `docs/TECHNICAL_DECISIONS.md`.
- Menyusun rencana kerja bertahap dengan bobot progres terukur pada `docs/IMPLEMENTATION_PLAN.md`.
- Menginisialisasi sistem pelacakan progres `PROGRESS.md` dan pelaporan pengujian `docs/TEST_REPORT.md`.
