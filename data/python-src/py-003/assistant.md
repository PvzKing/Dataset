Karena rentangnya bisa bertahun-tahun, saya tidak menghitung hari satu per satu. Setiap 7 hari berturut-turut pasti berisi tepat 5 hari kerja, jadi minggu penuh cukup dikalikan 5, dan hanya sisa hari (maksimal 6) yang dicek satu per satu. Libur lalu dikurangkan dengan tiga syarat:

- libur yang jatuh di Sabtu atau Minggu tidak dikurangi, karena hari itu memang tidak dihitung;
- libur di luar rentang diabaikan;
- libur yang tercantum dua kali hanya dikurangi sekali (dikumpulkan dalam `set`).

Tanggal awal yang lebih besar dari tanggal akhir memicu `ValueError`. Objek `datetime` ditolak dengan `TypeError`, karena `datetime` adalah turunan `date` dan membandingkan keduanya memicu error yang membingungkan. Ubah dulu dengan `.date()`.

```python
{{file hari_kerja.py}}
```

```
{{run python hari_kerja.py}}
```

Bagian cek silang membandingkan fungsi cepat dengan cara lambat hari per hari pada 2.000 rentang acak. Ini cara murah untuk memastikan rumus minggu penuh tidak meleset satu hari di tepi rentang.

Daftar libur sengaja diterima sebagai parameter, bukan ditulis di dalam fungsi. Hari libur nasional dan cuti bersama di Indonesia ditetapkan setiap tahun lewat Surat Keputusan Bersama Menteri Agama, Menteri Ketenagakerjaan, dan Menteri PANRB, dan tanggalnya bisa berubah, jadi simpan sebagai data yang diperbarui tiap tahun.
