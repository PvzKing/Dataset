Bagian tersulit di sini adalah syarat terakhir. Kalau file JSON langsung ditimpa dengan `open(path, "w")`, isinya terhapus saat file dibuka. Jika program mati sebelum penulisan selesai, yang tersisa hanya file kosong atau JSON setengah jadi. Jadi penyimpanan memakai pola **tulis-lalu-ganti**:

1. Tulis data ke file sementara **di folder yang sama**. `os.replace` hanya atomik dalam satu filesystem, jadi file sementara tidak boleh ditaruh di `/tmp`.
2. `flush()` lalu `os.fsync()`, supaya isinya benar-benar sudah di disk sebelum diganti, bukan masih di cache sistem operasi. Ini yang melindungi dari mati listrik.
3. `os.replace(tmp, path)`. Penggantian ini terjadi dalam satu langkah, jadi file selalu berisi versi lama yang utuh atau versi baru yang utuh.
4. Di Linux dan macOS, folder juga di-`fsync`, supaya penggantian nama itu sendiri tercatat di disk.
5. Jika gagal di tengah jalan, termasuk karena Ctrl+C, file sementara dihapus dan file lama tidak tersentuh.

Ada dua keputusan lain yang juga melindungi data:

- **File yang gagal dibaca tidak pernah ditimpa.** Banyak aplikasi menganggap JSON rusak sebagai "data kosong" lalu menyimpan daftar baru di atasnya. Akibatnya data lama hilang permanen. Di sini program berhenti dengan pesan error dan file dibiarkan apa adanya.
- **ID tidak dipakai ulang setelah dihapus.** Kalau tugas #2 dihapus lalu tugas baru diberi ID 2, perintah `selesai 2` yang diketik dari ingatan bisa salah sasaran.

```python
{{file todo.py}}
```

Hasil menjalankan:

```
{{run python todo.py --file tugas.json tambah "Bayar tagihan listrik"}}
{{run python todo.py --file tugas.json tambah "Siapkan berkas rapat Senin"}}
{{run python todo.py --file tugas.json tambah "Telepon bengkel"}}
{{run python todo.py --file tugas.json selesai 1}}
{{run python todo.py --file tugas.json hapus 3}}
{{run python todo.py --file tugas.json tambah "Beli tinta printer"}}
{{run python todo.py --file tugas.json daftar}}
{{run python todo.py --file tugas.json daftar --semua}}
{{run python todo.py --file tugas.json selesai 9}}
{{run python todo.py --tes}}
```

**Cek kebutuhan**
- **Tambah, lihat, selesai, hapus** → subperintah `tambah`, `daftar` (dengan `--semua` untuk melihat yang sudah selesai), `selesai`, dan `hapus`.
- **Disimpan ke file JSON** → bawaannya `~/.todo.json`, atau file lain dengan `--file`. JSON ditulis dengan `ensure_ascii=False`, jadi teks berbahasa Indonesia tetap terbaca kalau file dibuka manual.
- **Tidak rusak saat program atau listrik mati** → `simpan()` memakai file sementara, `fsync`, dan `os.replace`. Tes `test_mati_saat_menyimpan_tidak_merusak_file` mensimulasikan program terhenti di tengah `json.dump`, lalu memastikan file lama utuh dan tidak ada file sementara yang tertinggal.
- **Data rusak tidak memperparah keadaan** → `DataRusak` menghentikan program tanpa menimpa file. Tes `test_file_rusak_tidak_ditimpa` memeriksanya.

Kalau aplikasi ini dijalankan di dua terminal sekaligus, perubahan yang disimpan belakangan menimpa yang lebih dulu. Untuk pemakaian pribadi hal ini wajar. Kalau datanya dipakai bersama, gunakan SQLite, yang sudah menangani penguncian.
