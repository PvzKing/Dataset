Rancangannya: Flask hanya menyediakan API JSON dan satu halaman HTML statis, lalu halaman itu yang mengambil dan menampilkan data. Dengan begitu, perlindungan XSS cukup ditangani di satu tempat yang jelas. Keputusan penting lainnya:

- **XSS dicegah saat menampilkan, bukan saat menyimpan.** Pesan disimpan apa adanya, lalu ditampilkan dengan `textContent`. Browser memperlakukan `textContent` sebagai teks biasa, jadi `<img onerror=...>` tampil sebagai tulisan, tidak dijalankan. Membersihkan HTML saat menyimpan mudah ditembus dan merusak pesan yang memang berisi `<` atau `>`.
- **SQL selalu memakai parameter `?`**, jadi isi pesan tidak pernah dijalankan sebagai SQL.
- **Validasi di server.** Atribut `maxlength` dan `required` di form hanya untuk kenyamanan, karena request bisa dikirim langsung tanpa lewat halaman. Server memeriksa tipe data, membuang spasi di awal dan akhir, mewajibkan isi, dan membatasi panjang. Galat dikembalikan per kolom dengan status 400.
- **Satu koneksi SQLite per request** lewat `flask.g`, ditutup di `teardown_appcontext`.
- **Waktu disimpan dalam UTC** (ISO 8601) dan baru diubah ke WIB di browser. Server di zona waktu mana pun hasilnya sama.
- **`limit` dibatasi 1–100**, supaya satu request tidak bisa meminta seluruh tabel.

```python
{{file app.py}}
```

```
{{run python app.py --tes}}
```

**Cek kebutuhan**
- **Flask dan SQLite** → `create_app()` membuat aplikasi dan tabel `pesan`. Path database jadi parameter, sehingga tes memakai database sementara.
- **Form nama dan pesan, daftar pesan terbaru** → halaman di `/`. Daftar diurutkan dari yang terbaru (`ORDER BY id DESC`) dan dimuat ulang setelah mengirim.
- **API JSON** → `GET /api/pesan?limit=N` dan `POST /api/pesan` dengan body `{"nama": ..., "pesan": ...}`, yang mengembalikan 201 berisi pesan yang tersimpan.
- **Tidak bisa disusupi script** → `textContent` di `tampilkan()`. Tes `test_xss_tetap_teks` memastikan payload tersimpan utuh dan halaman tidak memasukkan data lewat `innerHTML`, `insertAdjacentHTML`, atau `document.write`.
- **Input divalidasi** → `kirim()`. Tes `test_validasi` mencakup kolom kosong, hanya spasi, terlalu panjang, bukan teks, dan body yang bukan JSON.

Untuk dipakai publik, jalankan dengan server produksi seperti `gunicorn "app:create_app('tamu.db')"`, bukan server bawaan Flask, dan tambahkan pembatasan jumlah request per IP supaya buku tamu tidak dibanjiri spam. Isi buku tamu yang dipublikasikan bisa memuat nama orang, jadi sediakan juga cara menghapus pesan atas permintaan penulisnya.
