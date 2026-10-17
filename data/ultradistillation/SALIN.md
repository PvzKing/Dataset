# Pertanyaan ultradistillation yang belum dijawab (13 dari 20)

Salin satu blok ke **percakapan baru** di AI-nya. Setelah AI menjawab, salin jawabannya dengan tombol salin (supaya format Markdown dan blok kodenya ikut), lalu kirim ke chat dengan baris pertama `<id> · <nama AI dan versinya>`.

## ud-008 · python

````text
Jawab pertanyaan di bawah garis dalam bahasa Indonesia yang baku tapi luwes. Langsung ke jawabannya: jangan membuka dengan basa-basi, jangan menyebut dirimu AI atau model bahasa, dan jangan menampilkan proses berpikir.

Format jawaban: jelaskan pendekatannya dalam beberapa kalimat, lalu tulis solusi lengkap dalam satu blok ```python dengan nama fungsi persis seperti yang diminta, tanpa input() dan tanpa print di luar fungsi. Setelah itu beri contoh pemakaian singkat dan kasus khusus yang ditangani.

---

Tulis fungsi `normalisasi_npwp(teks: str) -> str | None` di Python. NPWP lama punya 15 digit dan harus dikembalikan dalam format `99.999.999.9-999.999`. NPWP 16 digit (berbasis NIK) dikembalikan sebagai 16 digit tanpa pemisah. Masukan boleh memakai titik, tanda minus, dan spasi sebagai pemisah, di posisi mana pun. Jika ada karakter lain, atau jumlah digitnya bukan 15 atau 16, kembalikan `None`.
````

## ud-009 · python

````text
Jawab pertanyaan di bawah garis dalam bahasa Indonesia yang baku tapi luwes. Langsung ke jawabannya: jangan membuka dengan basa-basi, jangan menyebut dirimu AI atau model bahasa, dan jangan menampilkan proses berpikir.

Format jawaban: jelaskan pendekatannya dalam beberapa kalimat, lalu tulis solusi lengkap dalam satu blok ```python dengan nama fungsi persis seperti yang diminta, tanpa input() dan tanpa print di luar fungsi. Setelah itu beri contoh pemakaian singkat dan kasus khusus yang ditangani.

---

Saya butuh fungsi Python `pecah_tagihan(total: int, porsi: dict[str, float]) -> dict[str, int]` untuk membagi tagihan dalam rupiah secara proporsional. Contohnya `porsi = {"Budi": 2, "Ani": 1}` berarti Budi menanggung dua kali bagian Ani. Hasilnya bilangan bulat dan jumlahnya harus tepat sama dengan `total`. Caranya: bulatkan ke bawah dulu, lalu sisa rupiahnya dibagikan satu per satu ke orang dengan pecahan desimal terbesar; jika pecahannya sama, urutkan menurut nama. Lempar `ValueError` jika total negatif, `porsi` kosong, atau ada porsi yang ≤ 0.
````

## ud-010 · python

````text
Jawab pertanyaan di bawah garis dalam bahasa Indonesia yang baku tapi luwes. Langsung ke jawabannya: jangan membuka dengan basa-basi, jangan menyebut dirimu AI atau model bahasa, dan jangan menampilkan proses berpikir.

Format jawaban: jelaskan pendekatannya dalam beberapa kalimat, lalu tulis solusi lengkap dalam satu blok ```python dengan nama fungsi persis seperti yang diminta, tanpa input() dan tanpa print di luar fungsi. Setelah itu beri contoh pemakaian singkat dan kasus khusus yang ditangani.

---

Buatkan fungsi Python `rekap_bulanan(transaksi: list[dict]) -> dict[str, dict[str, int]]`. Setiap transaksi berisi `tanggal` (format `YYYY-MM-DD`), `kategori`, dan `nominal`. Hasilnya dikelompokkan per bulan (`"2026-01"`) lalu per kategori, berisi jumlah nominalnya. Urutan kunci bulan harus naik, dan kategori di dalam setiap bulan diurutkan menurut abjad. Lempar `ValueError` jika tanggalnya tidak valid atau formatnya bukan `YYYY-MM-DD`, atau jika nominalnya negatif.
````

## ud-011 · python_debug

````text
Jawab pertanyaan di bawah garis dalam bahasa Indonesia yang baku tapi luwes. Langsung ke jawabannya: jangan membuka dengan basa-basi, jangan menyebut dirimu AI atau model bahasa, dan jangan menampilkan proses berpikir.

Format jawaban: jelaskan pendekatannya dalam beberapa kalimat, lalu tulis solusi lengkap dalam satu blok ```python dengan nama fungsi persis seperti yang diminta, tanpa input() dan tanpa print di luar fungsi. Setelah itu beri contoh pemakaian singkat dan kasus khusus yang ditangani.

---

Fungsi ini seharusnya menghitung rata-rata tertimbang, tapi `rata_rata_tertimbang([80, 90], [1, 3])` menghasilkan 135, padahal seharusnya 87.5.

```python
def rata_rata_tertimbang(nilai, bobot):
    total = 0
    for i in range(1, len(nilai)):
        total += nilai[i] * bobot[i]
    return total / len(bobot)
```

Tolong cari semua kesalahannya, jelaskan, lalu berikan versi yang benar. Fungsi juga harus melempar `ValueError` jika panjang `nilai` dan `bobot` berbeda, daftarnya kosong, atau total bobotnya 0.
````

## ud-012 · hukum

````text
Jawab pertanyaan di bawah garis dalam bahasa Indonesia yang baku tapi luwes. Langsung ke jawabannya: jangan membuka dengan basa-basi, jangan menyebut dirimu AI atau model bahasa, dan jangan menampilkan proses berpikir.

Format jawaban: pisahkan fakta, isu hukum, dasar hukum, analisis, dan langkah yang bisa diambil. Sebut nama peraturan, pasal, dan ayat hanya jika yakin; jika tidak yakin nomornya, katakan demikian. Akhiri dengan satu kalimat bahwa ini informasi umum, bukan nasihat hukum untuk kasus konkret.

---

Saya menyewakan ruko. Penyewa sudah 3 bulan tidak bayar sewa, padahal di perjanjian tertulis sewa dibayar tiap tanggal 5. Saya kesal dan ingin langsung mengganti gembok ruko dan mengeluarkan barang-barangnya. Boleh tidak secara hukum? Kalau tidak, langkah apa yang benar?
````

## ud-013 · hukum

````text
Jawab pertanyaan di bawah garis dalam bahasa Indonesia yang baku tapi luwes. Langsung ke jawabannya: jangan membuka dengan basa-basi, jangan menyebut dirimu AI atau model bahasa, dan jangan menampilkan proses berpikir.

Format jawaban: pisahkan fakta, isu hukum, dasar hukum, analisis, dan langkah yang bisa diambil. Sebut nama peraturan, pasal, dan ayat hanya jika yakin; jika tidak yakin nomornya, katakan demikian. Akhiri dengan satu kalimat bahwa ini informasi umum, bukan nasihat hukum untuk kasus konkret.

---

Saya beli HP di toko online. Begitu dibuka, layarnya bergaris. Penjual menolak retur dengan alasan di deskripsi tokonya tertulis "barang yang sudah dibeli tidak dapat ditukar atau dikembalikan". Apakah aturan toko itu sah? Apa hak saya dan bagaimana cara menuntutnya?
````

## ud-014 · hukum

````text
Jawab pertanyaan di bawah garis dalam bahasa Indonesia yang baku tapi luwes. Langsung ke jawabannya: jangan membuka dengan basa-basi, jangan menyebut dirimu AI atau model bahasa, dan jangan menampilkan proses berpikir.

Format jawaban: pisahkan fakta, isu hukum, dasar hukum, analisis, dan langkah yang bisa diambil. Sebut nama peraturan, pasal, dan ayat hanya jika yakin; jika tidak yakin nomornya, katakan demikian. Akhiri dengan satu kalimat bahwa ini informasi umum, bukan nasihat hukum untuk kasus konkret.

---

Aplikasi pinjaman online menagih utang adik saya dengan cara mengirim pesan ke semua kontak di HP-nya, termasuk atasan di kantornya, disertai kata-kata yang mempermalukan. Pelanggaran apa saja yang terjadi, dan ke mana kami bisa melapor?
````

## ud-015 · hukum

````text
Jawab pertanyaan di bawah garis dalam bahasa Indonesia yang baku tapi luwes. Langsung ke jawabannya: jangan membuka dengan basa-basi, jangan menyebut dirimu AI atau model bahasa, dan jangan menampilkan proses berpikir.

Format jawaban: pisahkan fakta, isu hukum, dasar hukum, analisis, dan langkah yang bisa diambil. Sebut nama peraturan, pasal, dan ayat hanya jika yakin; jika tidak yakin nomornya, katakan demikian. Akhiri dengan satu kalimat bahwa ini informasi umum, bukan nasihat hukum untuk kasus konkret.

---

Saya bekerja sebagai karyawan kontrak (PKWT) di perusahaan yang sama selama 6 tahun. Kontraknya diperpanjang terus setiap tahun dengan jenis pekerjaan yang sama. Sekarang perusahaan mau mengakhiri kontrak tanpa pesangon. Bagaimana status saya menurut hukum, dan apa yang bisa saya tuntut?
````

## ud-016 · hukum

````text
Jawab pertanyaan di bawah garis dalam bahasa Indonesia yang baku tapi luwes. Langsung ke jawabannya: jangan membuka dengan basa-basi, jangan menyebut dirimu AI atau model bahasa, dan jangan menampilkan proses berpikir.

Format jawaban: pisahkan fakta, isu hukum, dasar hukum, analisis, dan langkah yang bisa diambil. Sebut nama peraturan, pasal, dan ayat hanya jika yakin; jika tidak yakin nomornya, katakan demikian. Akhiri dengan satu kalimat bahwa ini informasi umum, bukan nasihat hukum untuk kasus konkret.

---

Buatkan draf surat somasi pertama dari kuasa hukum kepada kontraktor renovasi rumah yang berhenti bekerja setelah menerima uang muka 50% (Rp60.000.000) dan tidak bisa dihubungi selama 5 minggu. Ada perjanjian tertulis yang menyebut pekerjaan selesai dalam 3 bulan. Pakai nama dan alamat fiktif, dan beri tenggat 7 hari.
````

## ud-017 · matematika

````text
Jawab pertanyaan di bawah garis dalam bahasa Indonesia yang baku tapi luwes. Langsung ke jawabannya: jangan membuka dengan basa-basi, jangan menyebut dirimu AI atau model bahasa, dan jangan menampilkan proses berpikir.

Format jawaban: jelaskan runtut dengan contoh, dan tunjukkan langkah perhitungannya.

---

Berapa peluang minimal dua orang di sebuah kelas berisi 30 siswa berulang tahun di hari yang sama (anggap satu tahun 365 hari dan setiap hari sama mungkinnya)? Jelaskan cara menghitungnya langkah demi langkah, lalu cari berapa orang minimal supaya peluangnya lebih dari 50%. Kenapa hasilnya terasa tidak masuk akal bagi kebanyakan orang?
````

## ud-018 · machine_learning

````text
Jawab pertanyaan di bawah garis dalam bahasa Indonesia yang baku tapi luwes. Langsung ke jawabannya: jangan membuka dengan basa-basi, jangan menyebut dirimu AI atau model bahasa, dan jangan menampilkan proses berpikir.

Format jawaban: jelaskan runtut dengan contoh, dan tunjukkan langkah perhitungannya.

---

Kenapa fine-tuning model bahasa kecil dengan data sedikit dan jumlah epoch banyak (misalnya 10 epoch) bisa membuat model menghafal data latihan dan malah lebih buruk di pertanyaan baru? Jelaskan dengan bahasa sederhana, beri tanda-tanda yang bisa dilihat dari angka loss dan hasil uji, dan cara mencegahnya.
````

## ud-019 · python_konsep

````text
Jawab pertanyaan di bawah garis dalam bahasa Indonesia yang baku tapi luwes. Langsung ke jawabannya: jangan membuka dengan basa-basi, jangan menyebut dirimu AI atau model bahasa, dan jangan menampilkan proses berpikir.

Format jawaban: jelaskan runtut dengan contoh, dan tunjukkan langkah perhitungannya.

---

Jelaskan cara kerja manajemen memori di Python: reference counting, garbage collector generasional, dan kapan memory leak tetap bisa terjadi walaupun ada garbage collector. Sertakan contoh kode singkat untuk menunjukkan referensi melingkar dan cara memeriksanya dengan modul `gc` dan `weakref`.
````

## ud-020 · database

````text
Jawab pertanyaan di bawah garis dalam bahasa Indonesia yang baku tapi luwes. Langsung ke jawabannya: jangan membuka dengan basa-basi, jangan menyebut dirimu AI atau model bahasa, dan jangan menampilkan proses berpikir.

Format jawaban: jelaskan runtut dengan contoh, dan tunjukkan langkah perhitungannya.

---

Rancang skema database PostgreSQL untuk sistem peminjaman buku perpustakaan sekolah: buku dan eksemplarnya, anggota (siswa dan guru dengan batas pinjam berbeda), peminjaman, pengembalian, dan denda keterlambatan Rp1.000 per hari. Berikan DDL lengkap dengan constraint, lalu query untuk daftar peminjaman yang terlambat beserta dendanya per hari ini.
````
