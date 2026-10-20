# Sistem Informasi Peminjaman, Penyerahan, dan Pengembalian Barang

Aplikasi web profesional berbasis Django untuk manajemen inventaris kantor dan instansi pemerintahan. Sistem ini memisahkan secara ketat alur operasional antara **Barang Pinjaman (Loanable)** dan **Barang Habis Pakai (Consumable)** sesuai standar tata kelola aset pemerintah.

---

## Fitur Utama

1. **Autentikasi & Otorisasi Berbasis Peran**:
   - Peran **Admin / Petugas Gudang**: Manajemen master data, persetujuan peminjaman, serah terima fisik, pengembalian, penyerahan barang habis pakai, audit log, dan laporan menyeluruh.
   - Peran **Pegawai / Pemohon**: Akses katalog barang pinjaman, pengajuan peminjaman daring, pemantauan status persetujuan, jatuh tempo pengembalian, dan riwayat transaksi pribadi.
2. **Pemisahan Tipe Barang Tegas**:
   - **LOANABLE**: Kamera, laptop, proyektor, monitor, dll. Wajib dikembalikan, mendukung pengembalian sebagian, inspeksi kondisi fisik (layak, rusak, hilang).
   - **CONSUMABLE**: Kertas, pulpen, tinta, map, ATK. Diserahkan untuk operasional unit, langsung mengurangi stok, tanpa kewajiban pengembalian.
3. **Pencatatan Stok & Stock Ledger Atomik**:
   - Saldo terpisah: Stok Tersedia, Stok Sedang Dipinjam, Stok Rusak/Perbaikan, dan Stok Hilang.
   - Pengajuan peminjaman **tidak** memotong stok sampai serah terima fisik benar-benar dikonfirmasi.
   - Semua mutasi tercatat pada tabel mutasi stok (`StockMovement`) dengan jaminan `transaction.atomic()`.
4. **Dokumen & Bukti Transaksi Resmi**:
   - Format penomoran dokumen unik (`PINJ-`, `SRH-`, `KMB-`, `HPK-`).
   - Tampilan cetak A4 ramah printer, ekspor CSV, Excel (`openpyxl`), dan PDF (`reportlab`).
5. **Audit Trail & Keamanan**:
   - Pencatatan seluruh aksi perubahan data penting pada `AuditLog`.
   - Validasi ketat di sisi server untuk mencegah manipulasi ID pemohon (IDOR), stok minus, atau pengembalian melebihi pinjaman.

---

## Persyaratan Sistem

- Python 3.11 s/d 3.14
- Django 5.2+
- SQLite (Pengembangan & Pengujian) / PostgreSQL (Produksi)

---

## Instalasi dan Menjalankan Aplikasi

1. **Aktifkan Virtual Environment**:
   ```bash
   source venv/bin/activate
   ```

2. **Instal Dependensi**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Migrasi Database & Inisialisasi Data Demo**:
   ```bash
   python manage.py migrate
   python manage.py init_data
   ```

   *Perintah `init_data` secara otomatis mengisi pengaturan instansi BMKG, akun pengguna (admin & pegawai), master barang & kategori, saldo awal stok, serta contoh transaksi aktif.*

4. **Kredensial Pengujian (Demo)**:
   - **Administrator**: `admin` / `admin123`
   - **Petugas Gudang**: `petugas` / `petugas123`
   - **Pegawai 1**: `pegawai_andi` / `pegawai123`
   - **Pegawai 2**: `pegawai_budi` / `pegawai123`
   - **Pegawai 3**: `pegawai_citra` / `pegawai123`

5. **Jalankan Pengujian Otomatis**:
   ```bash
   python manage.py test
   ```

6. **Jalankan Server Pengembangan**:
   ```bash
   python manage.py runserver
   ```

---

## Dokumentasi Proyek

- [PRD Acuan](PRD_Sistem_Peminjaman_Penyerahan_Barang_Django.txt)
- [Keputusan Teknis](docs/TECHNICAL_DECISIONS.md)
- [Rencana Implementasi](docs/IMPLEMENTATION_PLAN.md)
- [Pelacakan Progres](PROGRESS.md)
- [Laporan Pengujian](docs/TEST_REPORT.md)
- [Catatan Rilis](CHANGELOG.md)
