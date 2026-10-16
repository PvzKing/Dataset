Ini soal *subset sum*: memilih sebagian faktur yang jumlahnya tepat sama dengan nominal transfer. Soal ini NP-complete, jadi tidak ada cara cepat untuk semua ukuran. Yang bisa dilakukan adalah memilih cara yang cukup cepat untuk ukuran datamu, yaitu sampai 40 faktur:

- **Mencoba semua kombinasi** tidak mungkin: 40 faktur berarti 2^40, sekitar 1,1 triliun kombinasi.
- **Pemrograman dinamis per nominal**, yaitu tabel "jumlah berapa saja yang bisa dibentuk", hanya cocok untuk angka kecil. Nominal di sini puluhan juta rupiah, jadi tabelnya puluhan juta sel untuk setiap faktur. Nota retur yang negatif juga membuat rentang tabel harus digeser.
- **Meet in the middle** yang saya pakai. Faktur dibagi dua kelompok berisi 20. Semua jumlah subset tiap kelompok dihitung (2 × 2^20, sekitar 2,1 juta), jumlah kelompok kiri disimpan di dict, lalu untuk setiap jumlah `s` di kelompok kanan dicari `transfer - s` di dict itu. Waktunya bergantung pada 2^(n/2), tidak pada besar nominal, dan nilai negatif tidak jadi masalah.

Bagian yang paling penting justru bukan kecepatannya, tapi **jawabannya bisa lebih dari satu**. Contoh paling sederhana adalah dua faktur dengan nominal sama. Kalau fungsi mengembalikan kombinasi pertama yang ditemukan lalu hasilnya langsung dipakai menandai lunas, faktur yang salah bisa tercatat lunas sementara faktur yang benar terus ditagih. Karena itu fungsi ini mencari sampai dua kombinasi:

- tidak ada kombinasi: transfer tidak cocok dengan faktur mana pun;
- tepat satu: aman ditandai lunas otomatis;
- dua: ambigu, jangan ditandai otomatis dan serahkan ke petugas.

Supaya memori tidak membengkak saat banyak subset punya jumlah yang sama, dict hanya menyimpan paling banyak `maks` subset untuk setiap jumlah. Batas ini tidak membuat kombinasi terlewat. Ambil sembarang kombinasi yang benar, terdiri dari bagian kiri `a` dan bagian kanan `b`. Kalau `a` tersimpan, kombinasi itu ditemukan. Kalau `a` tidak disimpan, berarti sudah ada `maks` subset kiri lain dengan jumlah yang sama, dan masing-masing juga sah bila dipasangkan dengan `b`. Jadi fungsi selalu menemukan sebanyak `maks` kombinasi, atau semuanya kalau jumlahnya lebih sedikit.

Nominal harus bilangan bulat rupiah. Nilai `float` ditolak karena penjumlahan desimal biner bisa meleset sedikit, dan selisih sekecil apa pun membuat pencocokan "tepat sama" gagal diam-diam.

```python
{{file rekonsiliasi.py}}
```

```
{{run python rekonsiliasi.py}}
```

Cara membaca hasilnya:

- **4.205.000 ambigu** karena INV-0415 dan INV-0423 sama-sama 3.480.000. Inilah kasus yang tidak boleh ditandai lunas otomatis.
- **1.070.000 dan 1.795.000** cocok pasti, masing-masing memakai nota retur −180.000.
- **Cek silang** membandingkan fungsi ini dengan cara lambat yang mencoba semua kombinasi pada 3.000 kasus acak sampai 12 faktur, termasuk nota retur. Jumlah kombinasi yang ditemukan dan kebenaran setiap kombinasi diperiksa.
- **Kasus terberat 40 faktur** adalah ketika tidak ada yang cocok, karena semua subset harus diperiksa. Di mesin uji, kasus ini selesai sekitar 1 detik dengan memori sekitar 120 MB.

Hasil terakhir, **40 faktur dengan 2 kombinasi**, bukan kebetulan. Faktur di contoh itu bernilai Rp100 ribu sampai Rp9 juta dalam kelipatan seribu, jadi jumlah semua faktur paling banyak Rp360 juta. Artinya hanya ada sekitar 360 ribu kemungkinan total, sedangkan subsetnya 1,1 triliun, atau rata-rata jutaan kombinasi untuk setiap total. Dengan nominal persis sampai satuan rupiah pun, 360 juta kemungkinan total dibagi 1,1 triliun subset masih rata-rata ribuan kombinasi per total.

Kesimpulannya, makin banyak faktur, pencocokan yang hanya berdasarkan nominal makin pasti ambigu, jauh sebelum batas 40 faktur tercapai. Jadi sempitkan kandidatnya dulu sebelum memanggil fungsi ini:

- hanya faktur milik pelanggan pengirim;
- hanya yang belum lunas;
- hanya yang terbit sebelum tanggal transfer.

Kalau memungkinkan, minta pelanggan mencantumkan nomor faktur di berita transfer atau pakai nomor virtual account per faktur. Untuk kasus yang diputuskan petugas, simpan siapa yang memilih dan kombinasi apa yang dipilih, supaya status lunas setiap faktur bisa ditelusuri lagi.
