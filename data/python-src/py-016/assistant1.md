Aturan yang saya terapkan:

- **Seluruh teks harus terbaca.** Parser membaca pasangan angka dan satuan dari kiri ke kanan. Kalau ada sisa yang tidak cocok, seperti `abc` di `"1j abc"`, hasilnya error, bukan diabaikan diam-diam.
- **Spasi bebas dan huruf besar/kecil tidak dibedakan:** `"1j30m"`, `"2 jam 5 menit"`, dan `"45D"` semuanya diterima.
- **Satuan yang sama tidak boleh muncul dua kali.** `"1j 2j"` kemungkinan besar salah ketik, jadi ditolak.
- **Hanya bilangan bulat non-negatif.** `"1.5j"` dan `"-5m"` ditolak. Kalau nanti perlu desimal, aturannya bisa ditambah dengan sengaja.

```python
{{file modern/durasi.py}}
```

```
{{run python durasi.py 1j 30m 15d}}
{{run python durasi.py --tes}}
```
