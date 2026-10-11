Cara yang paling sering dipakai adalah **serakah**: ambil pecahan terbesar sebanyak mungkin, lalu lanjut ke pecahan berikutnya. Untuk pecahan Rupiah standar cara ini memang benar. Tapi karena daftar pecahannya bisa diatur, serakah bisa salah. Contohnya nominal 6 dengan pecahan [1, 3, 4]: serakah menghasilkan 4 + 1 + 1 (3 keping), padahal 3 + 3 hanya 2 keping.

Jadi saya pakai **dynamic programming**. `keping[i]` menyimpan jumlah keping minimal untuk nominal `i`, dihitung dari nominal yang lebih kecil, lalu kombinasinya direkonstruksi dari pecahan terakhir yang dipakai. Ada beberapa hal lain yang ditangani:

- **Ukuran tabel.** Tabel sepanjang nominal bisa besar untuk jutaan rupiah. Karena semua pecahan Rupiah kelipatan 100, nominal dan pecahan dibagi dulu dengan FPB-nya, sehingga tabelnya 100 kali lebih kecil.
- **Nominal yang tidak bisa dibentuk** mengembalikan `None`, misalnya Rp150 dengan pecahan terkecil Rp100.
- **Input `float` ditolak.** Uang dihitung dalam bilangan bulat rupiah, supaya tidak ada sisa pembagian seperti 0,30000000000000004.

```python
{{file kembalian.py}}
```

```
{{run python kembalian.py}}
```

Kompleksitasnya O(N × P), dengan N = nominal ÷ FPB dan P = banyaknya jenis pecahan. Untuk Rp9.999.900 dengan 10 pecahan Rupiah, tabelnya hanya sekitar 100 ribu baris, bukan 10 juta. Fungsi `gcd` dengan lebih dari dua argumen butuh Python 3.9 ke atas.
