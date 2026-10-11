Unit test yang baik menguji **batas-batas aturannya**, bukan hanya satu contoh "normal". Dari aturan itu, kasus yang perlu diuji:

| Kasus | Contoh | Harapan |
|---|---|---|
| Masih dalam masa pinjam | hari ke-6 dan ke-7 | Rp0 |
| Hari pertama terlambat | hari ke-8 | Rp1.000 |
| Kembali lebih cepat | hari ke-0 sampai ke-3 | Rp0 |
| Tepat di batas maksimal | hari ke-57 (50 hari terlambat) | Rp50.000 |
| Satu hari sebelum batas | hari ke-56 | Rp49.000 |
| Jauh melewati batas | hari ke-58 dan ke-400 | Rp50.000 |
| Melewati akhir Februari tahun kabisat | 25 Feb – 5 Mar 2028 | Rp2.000 |
| Tanggal kembali sebelum tanggal pinjam | salah input | `ValueError` |

Kasus di dalam satu aturan dikelompokkan dengan `subTest`, jadi kalau beberapa gagal, semuanya dilaporkan sekaligus, bukan berhenti di yang pertama.

```python
{{file test_denda.py}}
```

Saya jalankan tes ini pada fungsimu apa adanya:

```
{{run python -m unittest test_denda}}
```

Tesnya menemukan dua bug:

1. **Kembali sebelum hari ke-7 menghasilkan denda negatif.** Pinjam hari ini lalu kembali hari ini juga menghasilkan `0 - 7 = -7` hari terlambat, jadi dendanya −Rp7.000. Hari ke-6 pun menghasilkan −Rp1.000. Kalau angka ini dijumlahkan ke kas atau ditampilkan ke siswa, hasilnya kacau.
2. **Tanggal kembali sebelum tanggal pinjam diterima begitu saja.** Ini hampir pasti salah ketik, dan sekarang ikut "dihitung" sebagai denda negatif.

Perbaikannya:

```
<<<<<<< SEARCH
    terlambat = (tgl_kembali - tgl_pinjam).days - lama_pinjam
=======
    if tgl_kembali < tgl_pinjam:
        raise ValueError(f"tanggal kembali ({tgl_kembali}) sebelum tanggal pinjam ({tgl_pinjam})")
    terlambat = max(0, (tgl_kembali - tgl_pinjam).days - lama_pinjam)
>>>>>>> REPLACE
```

{{copy denda.py denda.py}}
Setelah diperbaiki:

```
{{run python -m unittest -v test_denda}}
```

Semua tes lolos. Simpan `test_denda.py` di samping `denda.py` dan jalankan `python -m unittest` setiap kali aturan denda diubah, misalnya kalau masa pinjam diganti menjadi 14 hari.
