File CSV dari Excel versi Indonesia punya beberapa ciri yang perlu ditangani satu per satu. Semua penanganannya hanya memakai library standar Python:

- **Pemisah titik koma.** Excel memakai `;` jika pengaturan regional memakai koma sebagai pemisah desimal. Pemisah ditebak dari baris judul dengan `csv.Sniffer`, jadi file berpemisah koma juga tetap terbaca.
- **BOM di awal file.** Ekspor "CSV UTF-8" dari Excel menambahkan karakter tak terlihat di awal file. Tanpa `utf-8-sig`, judul kolom pertama terbaca sebagai `﻿Tanggal` dan kolom tanggal "tidak ditemukan". Ekspor CSV biasa yang memakai encoding Windows dibaca dengan `cp1252` sebagai cadangan.
- **Nominal format Indonesia.** `1.250.000` dibaca sebagai satu juta lebih, bukan 1,25. Titik harus berupa pemisah ribuan per 3 angka, dan koma desimal paling banyak 2 angka. Teks lain seperti `12.50` ditolak, bukan ditebak.
- **Tanggal** diterima dalam format `03/01/2026`, `2026-01-03`, atau `03-01-2026`. Tanggal mustahil seperti 31/02/2026 dianggap salah.
- **Kategori yang beda tulisan**, misalnya `transportasi ` dengan spasi di belakang dan huruf kecil, disatukan dengan `Transportasi`.
- **Baris yang salah** dicatat beserta nomornya, dengan penomoran seperti di Excel (baris 1 adalah judul kolom), lalu dilewati. Script tetap berjalan.

```python
{{file rekap.py}}
```

Hasil menjalankan pada file contoh (berpemisah `;`, dengan BOM, dan dua baris yang salah):

```
{{run python rekap.py transaksi.csv}}
{{run python rekap.py --tes}}
```

**Cek kebutuhan**
- **Rekap per bulan dan per kategori** → `rekap()` menjumlahkan dengan `Decimal` per `YYYY-MM` dan per kategori. Kategori diurutkan dari total terbesar.
- **Pemisah titik koma** → `csv.Sniffer` dengan pilihan `;`, `,`, dan tab. Tes `test_koma_dan_kolom_hilang` memeriksa file berpemisah koma.
- **Format 1.250.000** → `baca_nominal()`, termasuk awalan `Rp`, sen, dan angka negatif untuk refund.
- **Baris salah tidak menghentikan script dan dilaporkan** → `salah` berisi nomor baris dan alasannya. Di contoh, baris 8 (31 Februari) dan baris 9 (nominal kosong) dilewati.

Kolom `Keterangan` tidak dipakai untuk rekap, tapi tetap terbaca, jadi mudah ditambahkan kalau nanti perlu, misalnya untuk mencari transaksi tertentu.
