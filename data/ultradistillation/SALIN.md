# Pertanyaan ultradistillation yang belum dijawab (16 dari 50)

Salin satu blok ke **percakapan baru** di AI-nya. Setelah AI menjawab, salin jawabannya dengan tombol salin (supaya format Markdown dan blok kodenya ikut), lalu kirim ke chat dengan baris pertama `<id> · <nama AI dan versinya>`.

## ud-035 · web

````text
Jawab pertanyaan di bawah garis dalam bahasa Indonesia yang baku tapi luwes. Langsung ke jawabannya: jangan membuka dengan basa-basi, jangan menyebut dirimu AI atau model bahasa, dan jangan menampilkan proses berpikir.

Format jawaban: satu kalimat pembuka, lalu satu dokumen HTML lengkap dalam satu blok ```html. CSS dan JavaScript ada di dalam file itu, tanpa library, font, gambar, atau file dari luar. Halaman harus responsif sampai lebar 375 px, tanpa error JavaScript, dan akses localStorage dibungkus try/catch. Setelah kode, tulis bagian **Cek kebutuhan** berupa daftar `- **<hal yang diminta>** → <bagian kode yang memenuhinya>` untuk setiap permintaan, lalu **Catatan teknis** singkat.

---

Buatkan spreadsheet mini dalam satu file HTML: grid kolom A–J dan baris 1–20 yang bisa diedit. Sel boleh berisi angka, teks, atau rumus yang diawali `=`, misalnya `=A1+B2*2`, `=SUM(A1:A5)`, `=AVERAGE(B1:B3)`, `=MIN(...)`, dan `=MAX(...)`. Hasil rumus ikut diperbarui saat sel yang dirujuk berubah, rumus yang saling merujuk secara melingkar menampilkan `#SIKLUS`, dan rumus yang salah menampilkan `#ERROR`. Jangan memakai `eval` atau `Function`. Isi sel tersimpan di localStorage.
````

## ud-036 · web

````text
Jawab pertanyaan di bawah garis dalam bahasa Indonesia yang baku tapi luwes. Langsung ke jawabannya: jangan membuka dengan basa-basi, jangan menyebut dirimu AI atau model bahasa, dan jangan menampilkan proses berpikir.

Format jawaban: satu kalimat pembuka, lalu satu dokumen HTML lengkap dalam satu blok ```html. CSS dan JavaScript ada di dalam file itu, tanpa library, font, gambar, atau file dari luar. Halaman harus responsif sampai lebar 375 px, tanpa error JavaScript, dan akses localStorage dibungkus try/catch. Setelah kode, tulis bagian **Cek kebutuhan** berupa daftar `- **<hal yang diminta>** → <bagian kode yang memenuhinya>` untuk setiap permintaan, lalu **Catatan teknis** singkat.

---

Buatkan pembuat invoice untuk usaha jasa dalam satu file HTML. Isiannya: data penjual dan pembeli, nomor invoice otomatis berformat INV/tahun/bulan/urut, tanggal dan jatuh tempo, daftar item (deskripsi, jumlah, harga satuan), diskon, dan persentase pajak yang bisa diubah. Hitung subtotal, pajak, dan total dalam format rupiah, tampilkan total dalam huruf (terbilang), dan sediakan tampilan cetak yang rapi di kertas A4 lewat `window.print()`. Riwayat invoice tersimpan di localStorage dan bisa dibuka kembali.
````

## ud-037 · web

````text
Jawab pertanyaan di bawah garis dalam bahasa Indonesia yang baku tapi luwes. Langsung ke jawabannya: jangan membuka dengan basa-basi, jangan menyebut dirimu AI atau model bahasa, dan jangan menampilkan proses berpikir.

Format jawaban: satu kalimat pembuka, lalu satu dokumen HTML lengkap dalam satu blok ```html. CSS dan JavaScript ada di dalam file itu, tanpa library, font, gambar, atau file dari luar. Halaman harus responsif sampai lebar 375 px, tanpa error JavaScript, dan akses localStorage dibungkus try/catch. Setelah kode, tulis bagian **Cek kebutuhan** berupa daftar `- **<hal yang diminta>** → <bagian kode yang memenuhinya>` untuk setiap permintaan, lalu **Catatan teknis** singkat.

---

bikin visualisasi algoritma pencarian jalur satu file html. grid kira-kira 25x15, klik atau drag buat gambar dinding, titik awal dan tujuan bisa dipindah. pilihan algoritmanya BFS, Dijkstra (ada petak lumpur yang biayanya 5), dan A*. animasikan petak yang sedang dijelajahi lalu jalur akhirnya, tampilkan jumlah petak yang dijelajahi dan panjang atau biaya jalurnya, plus tombol bikin labirin acak.
````

## ud-038 · web

````text
Jawab pertanyaan di bawah garis dalam bahasa Indonesia yang baku tapi luwes. Langsung ke jawabannya: jangan membuka dengan basa-basi, jangan menyebut dirimu AI atau model bahasa, dan jangan menampilkan proses berpikir.

Format jawaban: satu kalimat pembuka, lalu satu dokumen HTML lengkap dalam satu blok ```html. CSS dan JavaScript ada di dalam file itu, tanpa library, font, gambar, atau file dari luar. Halaman harus responsif sampai lebar 375 px, tanpa error JavaScript, dan akses localStorage dibungkus try/catch. Setelah kode, tulis bagian **Cek kebutuhan** berupa daftar `- **<hal yang diminta>** → <bagian kode yang memenuhinya>` untuk setiap permintaan, lalu **Catatan teknis** singkat.

---

Buatkan generator surat kuasa khusus untuk perkara perdata dalam satu file HTML, untuk dipakai kantor advokat. Formnya berisi data pemberi kuasa (nama, NIK, alamat), satu atau beberapa penerima kuasa (nama advokat, nomor kartu tanda anggota advokat, alamat kantor), pihak lawan, pengadilan negeri, pokok perkara, dan pilihan hak substitusi. Pratinjau surat berubah langsung saat form diisi, tanggal ditulis dalam format Indonesia, ada tempat tanda tangan dan meterai, dan tampilan cetaknya rapi di kertas A4. Profil kantor advokat tersimpan di localStorage supaya tidak perlu diisi ulang.
````

## ud-039 · web

````text
Jawab pertanyaan di bawah garis dalam bahasa Indonesia yang baku tapi luwes. Langsung ke jawabannya: jangan membuka dengan basa-basi, jangan menyebut dirimu AI atau model bahasa, dan jangan menampilkan proses berpikir.

Format jawaban: satu kalimat pembuka, lalu satu dokumen HTML lengkap dalam satu blok ```html. CSS dan JavaScript ada di dalam file itu, tanpa library, font, gambar, atau file dari luar. Halaman harus responsif sampai lebar 375 px, tanpa error JavaScript, dan akses localStorage dibungkus try/catch. Setelah kode, tulis bagian **Cek kebutuhan** berupa daftar `- **<hal yang diminta>** → <bagian kode yang memenuhinya>` untuk setiap permintaan, lalu **Catatan teknis** singkat.

---

Buat simulasi tata surya beranimasi dalam satu file HTML pakai canvas: matahari dan 8 planet mengorbit dengan kecepatan relatif sesuai periode orbitnya (skala jarak boleh tidak nyata, tetapi urutannya benar), bulan yang mengitari bumi, dan cincin Saturnus. Sediakan slider kecepatan waktu, tombol jeda, zoom dengan scroll atau pinch, dan klik planet untuk menampilkan info singkatnya: diameter, jarak rata-rata ke matahari, dan periode orbit.
````

## ud-040 · web

````text
Jawab pertanyaan di bawah garis dalam bahasa Indonesia yang baku tapi luwes. Langsung ke jawabannya: jangan membuka dengan basa-basi, jangan menyebut dirimu AI atau model bahasa, dan jangan menampilkan proses berpikir.

Format jawaban: satu kalimat pembuka, lalu satu dokumen HTML lengkap dalam satu blok ```html. CSS dan JavaScript ada di dalam file itu, tanpa library, font, gambar, atau file dari luar. Halaman harus responsif sampai lebar 375 px, tanpa error JavaScript, dan akses localStorage dibungkus try/catch. Setelah kode, tulis bagian **Cek kebutuhan** berupa daftar `- **<hal yang diminta>** → <bagian kode yang memenuhinya>` untuk setiap permintaan, lalu **Catatan teknis** singkat.

---

Buatkan aplikasi peta pikiran (mind map) dalam satu file HTML. Mulai dari satu ide utama di tengah; pengguna bisa menambah cabang dan anak cabang, mengubah teks dengan klik dua kali, menghapus cabang beserta anak-anaknya, menggeser simpul dengan drag (garis penghubungnya ikut bergerak), memberi warna per cabang, serta zoom dan menggeser kanvas. Sediakan tombol ekspor ke gambar PNG dan ke teks kerangka bertingkat. Data tersimpan di localStorage.
````

## ud-041 · hukum

````text
Jawab pertanyaan di bawah garis dalam bahasa Indonesia yang baku tapi luwes. Langsung ke jawabannya: jangan membuka dengan basa-basi, jangan menyebut dirimu AI atau model bahasa, dan jangan menampilkan proses berpikir.

Format jawaban: pisahkan fakta, isu hukum, dasar hukum, analisis, dan langkah yang bisa diambil. Sebut nama peraturan, pasal, dan ayat hanya jika yakin; jika tidak yakin nomornya, katakan demikian. Akhiri dengan satu kalimat bahwa ini informasi umum, bukan nasihat hukum untuk kasus konkret.

---

Ayah saya meninggal dan meninggalkan sebidang tanah bersertifikat atas namanya. Ahli warisnya ibu dan kami empat bersaudara, semuanya beragama Islam. Kakak sulung diam-diam menjual tanah itu ke orang lain tanpa tanda tangan kami, dengan alasan dia anak tertua dan yang menyimpan sertifikat. Apakah penjualan itu sah, dan apa yang bisa kami lakukan?
````

## ud-042 · hukum

````text
Jawab pertanyaan di bawah garis dalam bahasa Indonesia yang baku tapi luwes. Langsung ke jawabannya: jangan membuka dengan basa-basi, jangan menyebut dirimu AI atau model bahasa, dan jangan menampilkan proses berpikir.

Format jawaban: pisahkan fakta, isu hukum, dasar hukum, analisis, dan langkah yang bisa diambil. Sebut nama peraturan, pasal, dan ayat hanya jika yakin; jika tidak yakin nomornya, katakan demikian. Akhiri dengan satu kalimat bahwa ini informasi umum, bukan nasihat hukum untuk kasus konkret.

---

Tahun 2015 saya membeli tanah dari Pak Darto seharga Rp150 juta, tetapi hanya dengan kuitansi bermeterai dan surat jual beli di bawah tangan, tanpa akta PPAT. Sertifikatnya masih atas nama Pak Darto. Sekarang beliau sudah meninggal, dan anak-anaknya menolak membantu balik nama, bahkan mengklaim tanah itu sebagai warisan. Bagaimana posisi hukum saya, dan langkah apa yang harus saya tempuh?
````

## ud-043 · hukum

````text
Jawab pertanyaan di bawah garis dalam bahasa Indonesia yang baku tapi luwes. Langsung ke jawabannya: jangan membuka dengan basa-basi, jangan menyebut dirimu AI atau model bahasa, dan jangan menampilkan proses berpikir.

Format jawaban: pisahkan fakta, isu hukum, dasar hukum, analisis, dan langkah yang bisa diambil. Sebut nama peraturan, pasal, dan ayat hanya jika yakin; jika tidak yakin nomornya, katakan demikian. Akhiri dengan satu kalimat bahwa ini informasi umum, bukan nasihat hukum untuk kasus konkret.

---

Tetangga membangun pagar tembok permanen yang menurut sertifikat saya masuk sekitar 1 meter ke tanah saya sepanjang 10 meter. Waktu saya tegur, dia bilang batasnya sudah begitu sejak zaman orang tuanya. Apa yang bisa saya lakukan secara hukum, dan apakah perlu pengukuran ulang dari kantor pertanahan?
````

## ud-044 · hukum

````text
Jawab pertanyaan di bawah garis dalam bahasa Indonesia yang baku tapi luwes. Langsung ke jawabannya: jangan membuka dengan basa-basi, jangan menyebut dirimu AI atau model bahasa, dan jangan menampilkan proses berpikir.

Format jawaban: pisahkan fakta, isu hukum, dasar hukum, analisis, dan langkah yang bisa diambil. Sebut nama peraturan, pasal, dan ayat hanya jika yakin; jika tidak yakin nomornya, katakan demikian. Akhiri dengan satu kalimat bahwa ini informasi umum, bukan nasihat hukum untuk kasus konkret.

---

Saya dan suami beragama Islam dan akan bercerai. Anak kami berumur 5 dan 13 tahun. Siapa yang berhak mengasuh anak-anak, dan apakah suami wajib memberi nafkah anak serta nafkah untuk saya setelah cerai? Bagaimana kalau nanti dia tidak membayar?
````

## ud-045 · hukum

````text
Jawab pertanyaan di bawah garis dalam bahasa Indonesia yang baku tapi luwes. Langsung ke jawabannya: jangan membuka dengan basa-basi, jangan menyebut dirimu AI atau model bahasa, dan jangan menampilkan proses berpikir.

Format jawaban: pisahkan fakta, isu hukum, dasar hukum, analisis, dan langkah yang bisa diambil. Sebut nama peraturan, pasal, dan ayat hanya jika yakin; jika tidak yakin nomornya, katakan demikian. Akhiri dengan satu kalimat bahwa ini informasi umum, bukan nasihat hukum untuk kasus konkret.

---

Kami sudah menikah 4 tahun tanpa perjanjian pranikah. Sekarang kami ingin memisahkan harta karena suami akan memulai usaha yang berisiko utang. Apakah perjanjian pisah harta masih bisa dibuat setelah menikah? Bagaimana caranya supaya berlaku juga terhadap pihak ketiga seperti bank, dan apa akibatnya terhadap harta yang sudah kami miliki?
````

## ud-046 · hukum

````text
Jawab pertanyaan di bawah garis dalam bahasa Indonesia yang baku tapi luwes. Langsung ke jawabannya: jangan membuka dengan basa-basi, jangan menyebut dirimu AI atau model bahasa, dan jangan menampilkan proses berpikir.

Format jawaban: pisahkan fakta, isu hukum, dasar hukum, analisis, dan langkah yang bisa diambil. Sebut nama peraturan, pasal, dan ayat hanya jika yakin; jika tidak yakin nomornya, katakan demikian. Akhiri dengan satu kalimat bahwa ini informasi umum, bukan nasihat hukum untuk kasus konkret.

---

Seorang pembeli grosir membayar barang dagangan saya senilai Rp85 juta dengan bilyet giro. Saat jatuh tempo, giro itu ditolak bank karena saldonya tidak cukup, dan pembeli sekarang sulit dihubungi. Apakah ini bisa dipidanakan atau hanya urusan perdata? Langkah apa saja yang bisa saya ambil?
````

## ud-047 · hukum

````text
Jawab pertanyaan di bawah garis dalam bahasa Indonesia yang baku tapi luwes. Langsung ke jawabannya: jangan membuka dengan basa-basi, jangan menyebut dirimu AI atau model bahasa, dan jangan menampilkan proses berpikir.

Format jawaban: pisahkan fakta, isu hukum, dasar hukum, analisis, dan langkah yang bisa diambil. Sebut nama peraturan, pasal, dan ayat hanya jika yakin; jika tidak yakin nomornya, katakan demikian. Akhiri dengan satu kalimat bahwa ini informasi umum, bukan nasihat hukum untuk kasus konkret.

---

Saya membeli HP bekas lewat media sosial dan sudah mentransfer Rp4,5 juta ke rekening penjual, tetapi barangnya tidak pernah dikirim dan akun penjual menghilang. Ke mana saya harus melapor, pasal apa yang bisa dipakai, dan apakah uang saya bisa kembali?
````

## ud-048 · hukum

````text
Jawab pertanyaan di bawah garis dalam bahasa Indonesia yang baku tapi luwes. Langsung ke jawabannya: jangan membuka dengan basa-basi, jangan menyebut dirimu AI atau model bahasa, dan jangan menampilkan proses berpikir.

Format jawaban: pisahkan fakta, isu hukum, dasar hukum, analisis, dan langkah yang bisa diambil. Sebut nama peraturan, pasal, dan ayat hanya jika yakin; jika tidak yakin nomornya, katakan demikian. Akhiri dengan satu kalimat bahwa ini informasi umum, bukan nasihat hukum untuk kasus konkret.

---

Motor saya ditabrak mobil dari belakang saat berhenti di lampu merah. Kaki saya patah dan motor rusak berat. Pengemudinya kabur, tetapi pelat nomornya terekam kamera pengawas. Apa ancaman hukum bagi pengemudi itu, bagaimana cara menuntut biaya pengobatan dan perbaikan motor, dan apakah saya bisa mengklaim santunan Jasa Raharja?
````

## ud-049 · hukum

````text
Jawab pertanyaan di bawah garis dalam bahasa Indonesia yang baku tapi luwes. Langsung ke jawabannya: jangan membuka dengan basa-basi, jangan menyebut dirimu AI atau model bahasa, dan jangan menampilkan proses berpikir.

Format jawaban: pisahkan fakta, isu hukum, dasar hukum, analisis, dan langkah yang bisa diambil. Sebut nama peraturan, pasal, dan ayat hanya jika yakin; jika tidak yakin nomornya, katakan demikian. Akhiri dengan satu kalimat bahwa ini informasi umum, bukan nasihat hukum untuk kasus konkret.

---

Saya karyawan tetap dan sedang hamil 7 bulan. HRD tiba-tiba memberi surat PHK dengan alasan efisiensi, padahal saya merasa ini karena kehamilan saya. Apakah PHK ini sah? Berapa lama hak cuti melahirkan saya, dan apa yang harus saya lakukan?
````

## ud-050 · hukum

````text
Jawab pertanyaan di bawah garis dalam bahasa Indonesia yang baku tapi luwes. Langsung ke jawabannya: jangan membuka dengan basa-basi, jangan menyebut dirimu AI atau model bahasa, dan jangan menampilkan proses berpikir.

Format jawaban: pisahkan fakta, isu hukum, dasar hukum, analisis, dan langkah yang bisa diambil. Sebut nama peraturan, pasal, dan ayat hanya jika yakin; jika tidak yakin nomornya, katakan demikian. Akhiri dengan satu kalimat bahwa ini informasi umum, bukan nasihat hukum untuk kasus konkret.

---

Saya punya usaha keripik dengan merek "Renyah Mbok Sri" sejak 2018, tetapi belum pernah mendaftarkan mereknya. Ternyata ada orang lain yang mendaftarkan merek yang sama di DJKI tahun lalu, dan sekarang dia mengirim somasi agar saya berhenti memakai nama itu. Apakah saya harus berhenti? Upaya hukum apa yang bisa saya tempuh?
````
