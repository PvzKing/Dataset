Halaman statis seperti ini aman dan cepat, karena bisa di-hosting gratis tanpa server, misalnya di GitHub Pages atau Netlify. Ada tiga hal yang perlu ditangani dengan teliti:

- **Escape HTML untuk semua teks dari data.** Nama seperti `Kopi & Teh Celup <isi 20>` harus menjadi `&amp;` dan `&lt;`. Kalau tidak, browser membaca `<isi 20>` sebagai tag dan teksnya hilang. Tanda kutip juga di-escape (`&quot;`), supaya nama produk tidak bisa "keluar" dari atribut HTML.
- **Link WhatsApp perlu dua lapis encoding.** Teks pesan di-encode untuk URL dengan `quote()`. Tanpa itu, `&` di nama produk dianggap pemisah parameter dan pesannya terpotong. URL lengkapnya lalu di-escape lagi untuk HTML, karena diletakkan di atribut `href`.
- **Data diperiksa sebelum halaman dibuat.** Semua masalah dikumpulkan sekaligus, misalnya harga negatif, harga berkoma, atau nama kosong. Pemilik toko bisa memperbaiki semuanya dalam sekali jalan, dan halaman yang setengah benar tidak pernah tertulis.

Produk dengan stok 0 tetap tampil, tapi tombolnya diganti tulisan "Stok habis". Produk tanpa kategori masuk ke kategori "Lainnya".

```python
{{file katalog.py}}
```

Hasil menjalankan pada `produk.json` milikmu:

```
{{run python katalog.py produk.json}}
```

Untuk mengecek escaping, saya tampilkan judul produk dan link pesan untuk produk yang namanya berisi `&`:

```python
{{file lihat.py}}
```

```
{{run python lihat.py}}
{{run python katalog.py --tes}}
```

**Cek kebutuhan**
- **Satu file HTML statis** → `situs/index.html` dengan CSS di dalamnya, tanpa JavaScript dan tanpa file lain.
- **Dikelompokkan per kategori** → `per_kategori`, diurutkan menurut nama kategori lalu nama produk. Tes `test_stok_habis_dan_urutan` memeriksanya.
- **Harga format Rupiah** → `rupiah()`, misalnya `Rp145.000`.
- **Tombol pesan via WhatsApp** → link `wa.me` berisi nama dan harga produk. Nomor `0812-3456-7890` diubah ke format internasional `6281234567890`.
- **Bagus di HP** → meta viewport dan grid `auto-fill` dengan lebar minimal 220 px, jadi tampil satu kolom di HP dan beberapa kolom di laptop. Nama produk yang panjang dipatahkan (`overflow-wrap`) supaya tidak melebar keluar layar.
- **Tanda kutip dan & tidak merusak halaman** → `escape()` untuk teks dan atribut, `quote()` untuk URL. Tes `test_escape_teks_dan_atribut` dan `test_link_whatsapp` memeriksanya.

Jalankan ulang script setiap kali `produk.json` berubah, lalu unggah folder `situs`.
