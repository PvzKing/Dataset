Kode ini memang berjalan, tapi belum aman untuk aplikasi yang menyimpan data pasien. Temuannya saya urutkan dari yang paling berbahaya.

**1. Kritis: SQL injection di `login` dan `daftar`.**
Username dimasukkan ke query dengan f-string, jadi isi username ikut dijalankan sebagai SQL. Penyerang bisa menulis query sendiri lewat kolom username, misalnya menambahkan `UNION SELECT` yang mengembalikan hash password pilihannya sendiri. Dengan cara itu ia lolos login tanpa tahu password siapa pun. Ini saya buktikan pada kodemu:

```python
{{file uji_lama.py}}
```

```
{{run python uji_lama.py}}
```

Perbaikannya: selalu pakai parameter `?`. Dengan parameter, isi username dikirim sebagai data, tidak pernah sebagai SQL.

**2. Tinggi: MD5 tanpa salt untuk password.**
- MD5 dirancang supaya cepat. Kartu grafis biasa bisa mencoba miliaran tebakan per detik, jadi kalau database bocor, sebagian besar password bisa ditebak dalam hitungan jam.
- Tanpa salt, pengguna dengan password yang sama punya hash yang sama, dan hash password umum bisa langsung dicari di tabel yang sudah tersedia di internet.

Gunakan fungsi yang memang dirancang lambat dan bersalt. `hashlib.scrypt` sudah ada di library standar Python. Alternatifnya Argon2id lewat paket `argon2-cffi`.

**3. Sedang: pesan gagal yang berbeda.** "username tidak ditemukan" dan "password salah" memberi tahu penyerang username mana yang terdaftar. Dari situ ia tinggal fokus menebak password akun yang sudah pasti ada. Kembalikan hasil gagal yang sama untuk keduanya, dan tetap hitung hash meski username tidak ada, supaya lama prosesnya juga tidak membedakan.

**4. Sedang: `!=` untuk membandingkan hash.** Pembandingan string biasa berhenti di karakter pertama yang berbeda. Pakai `hmac.compare_digest`, yang waktunya tidak bergantung pada isi.

**5. Rendah:**
- koneksi database dibuat saat modul di-import, dengan path relatif yang bergantung pada folder saat program dijalankan;
- `commit` tidak dijalankan kalau query error;
- tidak ada batas panjang minimal password.

Versi perbaikan dengan library standar saja:

```python
{{file akun.py}}
```

Skenario yang sama pada versi baru:

{{copy akun.py akun.py}}
```python
{{file uji_baru.py}}
```

```
{{run python uji_baru.py}}
```

Masih ada yang perlu ditambahkan di level aplikasi: **batasi percobaan login** (misalnya kunci sementara setelah 5 kali gagal) dan jalankan aplikasi hanya lewat **HTTPS**. Password yang sudah tersimpan sebagai MD5 tidak bisa diubah langsung ke scrypt karena password aslinya tidak diketahui. Saat pengguna berhasil login berikutnya, cocokkan dengan MD5 lama, lalu simpan ulang dengan `hash_password` dan hapus hash MD5-nya.

**Catatan hukum.**
- Data kesehatan pasien termasuk data pribadi yang bersifat spesifik menurut Pasal 4 ayat (2) UU No. 27 Tahun 2022 tentang Pelindungan Data Pribadi.
- Pasal 35 undang-undang itu mewajibkan pengendali data melindungi dan memastikan keamanan data yang diprosesnya, termasuk dengan langkah teknis.
- Kalau terjadi kegagalan pelindungan, misalnya database bocor lewat celah seperti SQL injection di atas, Pasal 46 ayat (1) mewajibkan pemberitahuan tertulis kepada pasien dan lembaga paling lambat 3 × 24 jam.

Jadi perbaikan nomor 1 dan 2 sebaiknya selesai sebelum aplikasi menerima data pasien sungguhan.
