Rumus anuitas sendiri sederhana. Yang sering salah justru pembulatannya, jadi itu saya rancang dulu:

- **Angsuran** dihitung dengan rumus A = P × r / (1 − (1 + r)^−n), dengan r = bunga tahunan ÷ 12 ÷ 100, lalu dibulatkan ke rupiah terdekat (*half up*).
- **Bunga tiap bulan** = sisa pokok × r, juga dibulatkan ke rupiah. Pokok yang dibayar = angsuran − bunga.
- **Sisa pembulatan masuk ke bulan terakhir.** Kalau semua bulan memakai angsuran yang sama, pembulatan menumpuk dan total pokok meleset beberapa rupiah. Karena itu bulan terakhir membayar persis sisa pokok, dan angsuran terakhir bisa berbeda sedikit.
- **Bunga 0%** tidak bisa memakai rumus itu karena terjadi pembagian dengan nol. Kasus ini ditangani terpisah: pokok ÷ tenor.
- **Semua hitungan memakai `Decimal`**, bukan `float`, supaya hasilnya sama persis dengan hitungan tangan.

```python
{{file angsuran.py}}
```

Hasil menjalankan:

```
{{run python angsuran.py 100000000 12 12}}
{{run python angsuran.py 250000000 7.25 240}}
{{run python angsuran.py 1000000 0 3}}
{{run python angsuran.py --tes}}
```

**Cek kebutuhan**
- **Metode anuitas** → rumus anuitas di `jadwal()`, diuji terhadap nilai hitungan tangan (8.884.878,79 dibulatkan menjadi Rp8.884.879).
- **Tabel amortisasi** → `cetak()` menampilkan angsuran, bunga, pokok, dan sisa per bulan. Tenor panjang diringkas menjadi 3 bulan pertama dan 3 bulan terakhir.
- **Dibulatkan ke rupiah** → setiap angsuran dan bunga dibulatkan dengan `ROUND_HALF_UP`.
- **Total pokok tepat sama dengan pinjaman** → bulan terakhir melunasi sisa pokok. Tes `test_total_pokok_tepat` memeriksanya untuk 4 kombinasi, termasuk tenor 240 bulan.
- **Tes** → `python angsuran.py --tes`: total pokok, nilai rumus, bunga 0%, dan input yang salah.

Program ini memakai bunga efektif (anuitas). Penawaran kredit kadang memakai **bunga flat**, yaitu bunga dihitung dari pokok awal sepanjang tenor. Untuk persentase yang sama, total bunga flat jauh lebih besar, jadi saat membandingkan penawaran, pastikan metode bunganya sama.
