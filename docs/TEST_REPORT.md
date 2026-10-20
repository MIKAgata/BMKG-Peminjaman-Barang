# Laporan Pengujian (Test Report)

Proyek: **Sistem Informasi Peminjaman, Penyerahan, dan Pengembalian Barang**  
Platform: Django 5.2 / Python 3.14  
Terakhir Diperbarui: 2026-10-20  

---

## 1. Ringkasan Eksekutif Pengujian

| Metrik | Nilai |
|---|---|
| Total Kasus Uji | 0 |
| Berhasil (Passed) | 0 |
| Gagal (Failed) | 0 |
| Error | 0 |
| Dilewati (Skipped) | 0 |
| Status Rangkaian Uji | NOT STARTED |

---

## 2. Rincian Pengujian Skenario Wajib PRD (20 Skenario)

| No | Skenario Uji Wajib | Status | Catatan / Hasil |
|:---:|---|:---:|---|
| 1 | Admin dapat login dan mengelola barang | PENDING | Menunggu Tahap 1 & 2 |
| 2 | Pegawai dapat login dan melihat katalog | PENDING | Menunggu Tahap 1 & 2 |
| 3 | Pegawai tidak dapat mengakses halaman admin tanpa izin | PENDING | Menunggu Tahap 1 & 7 |
| 4 | Pegawai tidak dapat melihat transaksi pegawai lain | PENDING | Menunggu Tahap 3 & 7 |
| 5 | Barang CONSUMABLE tidak dapat dipinjam | PENDING | Menunggu Tahap 3 |
| 6 | Barang LOANABLE tidak dapat diproses melalui penyerahan habis pakai | PENDING | Menunggu Tahap 5 |
| 7 | Pengajuan peminjaman tidak mengurangi stok sebelum serah terima | PENDING | Menunggu Tahap 3 |
| 8 | Persetujuan tanpa serah terima tidak dianggap sebagai barang keluar | PENDING | Menunggu Tahap 3 |
| 9 | Stok berkurang ketika barang benar-benar diserahkan | PENDING | Menunggu Tahap 3 |
| 10 | Pengembalian sebagian memperbarui saldo dengan benar | PENDING | Menunggu Tahap 4 |
| 11 | Pengembalian melebihi jumlah yang dipinjam ditolak | PENDING | Menunggu Tahap 4 |
| 12 | Barang rusak tidak langsung menjadi stok tersedia | PENDING | Menunggu Tahap 4 |
| 13 | Penyerahan habis pakai mengurangi stok satu kali | PENDING | Menunggu Tahap 5 |
| 14 | Stok tidak boleh negatif | PENDING | Menunggu Tahap 2, 3, 5 |
| 15 | Pemrosesan ganda tidak menggandakan perubahan stok | PENDING | Menunggu Tahap 3, 4, 5 |
| 16 | Pembatalan transaksi memiliki jejak audit | PENDING | Menunggu Tahap 5 & 7 |
| 17 | Nomor transaksi tidak duplikat | PENDING | Menunggu Tahap 3, 4, 5 |
| 18 | Laporan sesuai dengan data transaksi | PENDING | Menunggu Tahap 6 |
| 19 | Pengguna tidak dapat memalsukan identitas peminjam melalui request | PENDING | Menunggu Tahap 3 & 7 |
| 20 | Dokumen transaksi dapat dibuat dari data yang benar | PENDING | Menunggu Tahap 6 |

---

## 3. Log Eksekusi Pengujian Otomatis

*(Akan diperbarui setiap kali perintah pengujian dieksekusi)*
