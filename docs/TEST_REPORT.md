# Laporan Pengujian (Test Report)

Proyek: **Sistem Informasi Peminjaman, Penyerahan, dan Pengembalian Barang**  
Platform: Django 5.2 / Python 3.14  
Terakhir Diperbarui: 2026-10-20  

---

## 1. Ringkasan Eksekutif Pengujian

| Metrik | Nilai |
|---|---|
| Total Kasus Uji | 55 |
| Berhasil (Passed) | 55 |
| Gagal (Failed) | 0 |
| Error | 0 |
| Dilewati (Skipped) | 0 |
| Durasi Eksekusi | ~25.5 detik |
| Status Rangkaian Uji | **PASSED (100% OK)** |

---

## 2. Rincian Pengujian Skenario Wajib PRD (20 Skenario Kriteria Penerimaan)

Seluruh 20 skenario wajib PRD diimplementasikan pada `config/tests_mandatory_scenarios.py` dan terverifikasi berhasil:

| No | Skenario Uji Wajib | Status | Catatan / Hasil Verifikasi |
|:---:|---|:---:|---|
| 1 | Admin dapat login dan mengelola barang | **PASSED** | Admin berhasil login dan mengkases modul inventaris |
| 2 | Pegawai dapat login dan melihat katalog | **PASSED** | Pegawai melihat barang LOANABLE; barang CONSUMABLE tidak muncul di katalog pinjaman |
| 3 | Pegawai tidak dapat mengakses halaman admin tanpa izin | **PASSED** | Mengembalikan HTTP 403 Forbidden pada akses menu admin |
| 4 | Pegawai tidak dapat melihat transaksi pegawai lain | **PASSED** | Proteksi IDOR aktif, pegawai lain diblokir dengan HTTP 403 |
| 5 | Barang CONSUMABLE tidak dapat dipinjam | **PASSED** | `ValidationError` dipicu jika barang bertipe CONSUMABLE diajukan pinjam |
| 6 | Barang LOANABLE tidak dapat diproses penyerahan habis pakai | **PASSED** | `ValidationError` dipicu jika barang LOANABLE dimasukkan ke penyerahan habis pakai |
| 7 | Pengajuan peminjaman tidak mengurangi stok sebelum serah terima | **PASSED** | Saldo stok fisik dan dipinjam tetap utuh saat pengajuan dibuat |
| 8 | Persetujuan tanpa serah terima tidak dianggap sebagai barang keluar | **PASSED** | Persetujuan admin (`APPROVED`) tidak mengurangi stok fisik |
| 9 | Stok berkurang ketika barang benar-benar diserahkan | **PASSED** | Stok tersedia berkurang dan stok dipinjam bertambah saat `LoanHandover` dikonfirmasi |
| 10 | Pengembalian sebagian memperbarui saldo dengan benar | **PASSED** | Stok dipinjam berkurang sesuai jumlah parsial, stok tersedia bertambah |
| 11 | Pengembalian melebihi jumlah yang dipinjam ditolak | **PASSED** | Validasi server menolak pengembalian di atas kuota pinjaman aktif |
| 12 | Barang rusak tidak langsung menjadi stok tersedia | **PASSED** | Masuk ke saldo `stock_damaged`, saldo `stock_available` tidak bertambah |
| 13 | Penyerahan habis pakai mengurangi stok satu kali | **PASSED** | Saldo berkurang tepat sekali dan dicatat pada StockMovement |
| 14 | Stok tidak boleh negatif | **PASSED** | Transaksi yang meminta kuota melebihi saldo ditolak dengan `ValidationError` |
| 15 | Pemrosesan ganda tidak menggandakan perubahan stok | **PASSED** | Idempotensi mencegah persetujuan/penolakan berulang mengubah status berulang |
| 16 | Pembatalan transaksi memiliki jejak audit | **PASSED** | Pembatalan penyerahan dicatat ke `AuditLog` dengan aksi `CANCEL` |
| 17 | Nomor transaksi tidak duplikat | **PASSED** | Format nomor transaksi terurut unik berurutan per bulan |
| 18 | Laporan sesuai dengan data transaksi | **PASSED** | Agregasi dashboard admin dan rekap laporan cocok dengan data transaksi sumber |
| 19 | Pengguna tidak dapat memalsukan identitas peminjam melalui request | **PASSED** | Server memaksakan peminjam adalah `request.user` terautentikasi |
| 20 | Dokumen transaksi dapat dibuat dari data yang benar | **PASSED** | Slip cetak resmi merender nomor, penerima, rincian barang, dan data instansi dengan benar |

---

## 3. Rincian Pengujian per Modul Aplikasi

| Modul | File Test | Jumlah Test | Status |
|---|---|:---:|:---:|
| `config` | `config/tests_mandatory_scenarios.py` | 20 | **PASSED** |
| `accounts` | `accounts/tests.py` | 5 | **PASSED** |
| `inventory` | `inventory/tests.py` | 6 | **PASSED** |
| `loans` | `loans/tests.py` | 11 | **PASSED** |
| `consumables` | `consumables/tests.py` | 4 | **PASSED** |
| `reports` | `reports/tests.py` | 6 | **PASSED** |
| `audit` | `audit/tests.py` | 3 | **PASSED** |
| **Total** | | **55** | **PASSED (100%)** |

---

## 4. Log Eksekusi Pengujian Otomatis

```text
Found 55 test(s).
Creating test database for alias 'default'...
System check identified no issues (0 silenced).
.......................................................
----------------------------------------------------------------------
Ran 55 tests in 25.552s

OK
Destroying test database for alias 'default'...
```
