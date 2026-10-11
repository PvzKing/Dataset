Untuk puluhan ribu file dan video besar, menghitung hash seluruh isi setiap file terlalu lambat. Jadi script ini menyaring bertahap, dari pemeriksaan yang paling murah:

1. **Ukuran file.** File dengan ukuran berbeda pasti berbeda isinya. Tahap ini hanya membaca metadata, tanpa membuka file.
2. **Hash 64 KB pertama**, hanya untuk file yang ukurannya sama. Kebanyakan file berbeda sudah terpisah di tahap ini.
3. **Hash SHA-256 seluruh isi**, hanya untuk yang masih tersisa. File dibaca per blok 1 MB, jadi video 10 GB tidak dimuat sekaligus ke memori.

Ada beberapa jebakan yang perlu ditangani supaya laporannya tidak menyesatkan:

- **Hard link** adalah satu file yang punya dua nama. Menghapus salah satunya tidak menghemat ruang sama sekali, jadi file dengan inode yang sama hanya dihitung sekali.
- **Symlink** dilewati. Kalau diikuti, file yang sama terhitung dua kali, dan symlink yang menunjuk ke folder induk bisa membuat pemindaian berputar.
- **File kosong** semuanya "identik" tapi tidak memakan ruang, jadi bawaannya diabaikan (`--min-ukuran 1`).
- **File yang tidak bisa dibaca** karena izin ditolak, atau terhapus di tengah pemindaian, dicatat sebagai peringatan. Script tidak berhenti.

```python
{{file duplikat.py}}
```

Hasil menjalankan pada folder contoh dan tesnya:

```
{{run python duplikat.py contoh}}
{{run python duplikat.py --tes}}
```

**Cek kebutuhan**
- **Isi sama walaupun nama beda** → kelompok ditentukan oleh hash SHA-256 isi file, bukan nama. Di contoh, `pantai.jpg` dan `IMG_0001.jpg` masuk satu kelompok.
- **Termasuk subfolder** → `os.walk` menelusuri seluruh pohon folder. Tes `test_duplikat_di_subfolder` memeriksanya.
- **Kelompok duplikat dan ruang yang bisa dihemat** → setiap kelompok dicetak, diurutkan dari ruang terbuang terbesar. Ruang yang bisa dihemat = ukuran × (jumlah file − 1), karena satu salinan tetap disimpan.
- **Tidak menghapus apa pun** → pemindaian hanya membaca file. Satu-satunya yang dihapus adalah folder sementara yang dibuat tes sendiri (`TemporaryDirectory`).
- **Puluhan ribu file dan video besar** → penyaringan tiga tahap dan pembacaan per blok 1 MB.

`laporan.txt` dan `laporan-revisi.txt` berukuran sama tapi isinya berbeda satu kata, jadi tidak dilaporkan. Sebelum menghapus file dari laporan ini, buka dulu kedua file atau pastikan salinannya memang tidak dipakai program lain.
