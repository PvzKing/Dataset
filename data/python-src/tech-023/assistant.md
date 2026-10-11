Di kwitansi dan akta, satu kata yang salah membuat angka dan huruf tidak cocok, jadi sumber kesalahannya saya petakan dulu sebelum menulis kode.

**Aturan bahasa**
- Awalan *se-* menggantikan "satu" pada sepuluh, sebelas, seratus, dan seribu. Untuk skala yang lebih besar tetap "satu juta", "satu miliar".
- "seribu" hanya jika kelompok ribuannya tepat 1. Jadi 101.000 adalah "seratus satu ribu", dan 21.000 "dua puluh satu ribu".
- 12–19 memakai "belas"; 11 khusus "sebelas".
- Kelompok tiga angka yang bernilai nol dilewati: 1.000.001 adalah "satu juta satu". Kata "nol" hanya untuk nilai 0.

**Bentuk input**
- Format Indonesia memakai titik untuk ribuan dan koma untuk desimal. Teks format Inggris seperti `1,250,000.50` ditolak, bukan ditebak, karena tebakan yang salah mengubah nominal.
- `float` tidak tepat untuk uang (`0.1 + 0.2` menghasilkan `0.30000000000000004`), jadi nilai disimpan sebagai `Decimal`.
- Sen lebih dari 2 angka tidak dibulatkan diam-diam. Pembulatan uang harus keputusan pemanggil.
- Di Python, `True` juga bertipe `int`, jadi harus ditolak secara eksplisit.

```python
{{file terbilang.py}}
```

Hasil menjalankan:

```
{{run python terbilang.py 1.250.000,50}}
{{run python terbilang.py Rp 75.000.000}}
{{run python terbilang.py 1,250,000.50}}
{{run python terbilang.py --tes}}
```

**Cek kebutuhan**
- **Tanpa library eksternal** → hanya `re`, `sys`, `unittest`, dan `decimal` dari library standar.
- **Angka dan huruf seperti di kwitansi** → `kwitansi()` mengembalikan `Rp1.250.000,50 (… rupiah lima puluh sen)`. Angka dan hurufnya dibuat dari satu nilai `Decimal` yang sama, jadi keduanya tidak mungkin berbeda.
- **Input angka** → `int` dan `Decimal` diterima. `float` dan `bool` ditolak dengan `TypeError` beserta alasannya.
- **Input teks format Indonesia** → `POLA_RUPIAH` menerima awalan `Rp`/`Rp.`, titik ribuan yang selalu per 3 angka, dan koma dengan 1–2 angka sen. Teks lain menghasilkan `ValueError` yang menyebut contoh format yang benar.
- **Kasus tepi** → nol, belasan, awalan *se-*, kelompok nol, nominal di bawah Rp1 (`Rp0,75 (tujuh puluh lima sen)`), batas 999 triliun, negatif, `NaN`, dan sen lebih dari 2 angka.
- **Tes** → `python terbilang.py --tes` menjalankan 45 kasus. Kasus dalam tabel memakai `subTest`, jadi kasus yang gagal dilaporkan satu per satu, bukan berhenti di kegagalan pertama.

**Catatan desain**
- `terbilang()` menerima bilangan negatif ("minus empat puluh lima") karena berguna di luar konteks uang. `kwitansi()` menolaknya, karena nominal negatif di kwitansi hampir pasti salah input.
- `BATAS` dihitung dari `SKALA`. Jika perlu "kuadriliun", tambahkan ke daftar itu dan batasnya ikut naik.
- Hasil memakai huruf kecil seperti kebiasaan kwitansi. Untuk gaya Huruf Kapital Tiap Kata, pakai `.title()`.

**Catatan hukum**
- Pasal 42 ayat (3) UU No. 30 Tahun 2004 tentang Jabatan Notaris mewajibkan bilangan yang menyatakan jumlah dalam akta ditulis dengan huruf. Dalam praktik, huruf itu didahului angka, persis seperti keluaran `kwitansi()`.
- Satuan sen punya dasar hukum: Pasal 3 ayat (2) UU No. 7 Tahun 2011 tentang Mata Uang menetapkan satu rupiah sama dengan 100 sen.
- Kwitansi penerimaan uang dengan nominal lebih dari Rp5.000.000 adalah objek bea meterai Rp10.000 (Pasal 3 ayat (2) huruf g dan Pasal 5 UU No. 10 Tahun 2020 tentang Bea Meterai). Program ini hanya menulis nominal; ia tidak memeriksa kewajiban meterai.
