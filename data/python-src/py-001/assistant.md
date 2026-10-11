Sebelum menulis kode, ini aturan yang saya pakai:

- **Awalan yang diterima:** `0`, `62`, atau `+62`. Setelah awalan dibuang, sisanya harus diawali `8` dengan total 9–12 digit. Itu rentang nomor seluler Indonesia, dari nomor lama 0811-234-567 sampai 0812-3456-78901.
- **Pemisah dibuang:** spasi, tanda hubung, titik, dan kurung.
- **`+62 0812...` diterima.** Nol setelah kode negara sering ditulis orang, dan maksudnya jelas.
- **Nomor tanpa awalan seperti `812345678` ditolak.** Tanpa awalan, kita tidak bisa membedakan nomor yang sengaja ditulis begitu dari nomor yang terpotong.
- **Pakai `[0-9]`, bukan `\d`.** Di Python, `\d` juga cocok dengan angka Unicode lain, misalnya angka Arab `٠٨١٢`. Kalau memakai `\d`, angka itu ikut lolos ke database.

```python
{{file hp.py}}
```

```
{{run python hp.py}}
```

Nomor telepon rumah seperti `021...` ditolak karena tidak diawali 8. Kalau sistemmu juga perlu menerima telepon rumah, aturannya harus dipisah, karena panjang nomornya bergantung pada kode wilayah.
