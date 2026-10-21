# Pertanyaan ultradistillation yang belum dijawab (23 dari 50)

Salin satu blok ke **percakapan baru** di AI-nya. Setelah AI menjawab, salin jawabannya dengan tombol salin (supaya format Markdown dan blok kodenya ikut), lalu kirim ke chat dengan baris pertama `<id> · <nama AI dan versinya>`.

## ud-028 · python

````text
Jawab pertanyaan di bawah garis dalam bahasa Indonesia yang baku tapi luwes. Langsung ke jawabannya: jangan membuka dengan basa-basi, jangan menyebut dirimu AI atau model bahasa, dan jangan menampilkan proses berpikir.

Format jawaban: jelaskan pendekatannya dalam beberapa kalimat, lalu tulis solusi lengkap dalam satu blok ```python dengan nama fungsi persis seperti yang diminta, tanpa input() dan tanpa print di luar fungsi. Setelah itu beri contoh pemakaian singkat dan kasus khusus yang ditangani.

---

Tulis fungsi `stasiun_terdekat(lokasi: tuple[float, float], stasiun: dict[str, tuple[float, float]], k: int) -> list[tuple[str, float]]` untuk mencari `k` stasiun KRL terdekat dari posisi pengguna. Koordinat berupa (lintang, bujur) dalam derajat. Hitung jarak dengan rumus haversine dan jari-jari bumi 6.371 km, bulatkan ke 2 angka desimal, lalu urutkan dari yang terdekat; jika jaraknya sama, urutkan menurut nama. Jika `k` lebih besar dari jumlah stasiun, kembalikan semuanya. Lempar `ValueError` jika `k` kurang dari 1.
````

## ud-029 · python

````text
Jawab pertanyaan di bawah garis dalam bahasa Indonesia yang baku tapi luwes. Langsung ke jawabannya: jangan membuka dengan basa-basi, jangan menyebut dirimu AI atau model bahasa, dan jangan menampilkan proses berpikir.

Format jawaban: jelaskan pendekatannya dalam beberapa kalimat, lalu tulis solusi lengkap dalam satu blok ```python dengan nama fungsi persis seperti yang diminta, tanpa input() dan tanpa print di luar fungsi. Setelah itu beri contoh pemakaian singkat dan kasus khusus yang ditangani.

---

Guru matematika butuh fungsi `distribusi_frekuensi(data: list[int], k: int) -> list[tuple[int, int, int]]` untuk membuat tabel distribusi frekuensi nilai ulangan. Lebar kelas adalah `(maks − min + 1) / k` yang dibulatkan ke atas. Kelas pertama dimulai dari nilai minimum, setiap kelas mencakup batas bawah sampai batas atasnya (inklusif), dan selalu ada tepat `k` kelas meskipun kelas terakhir melewati nilai maksimum. Kembalikan daftar `(batas_bawah, batas_atas, frekuensi)`. Lempar `ValueError` jika `data` kosong atau `k` kurang dari 1.
````

## ud-030 · python

````text
Jawab pertanyaan di bawah garis dalam bahasa Indonesia yang baku tapi luwes. Langsung ke jawabannya: jangan membuka dengan basa-basi, jangan menyebut dirimu AI atau model bahasa, dan jangan menampilkan proses berpikir.

Format jawaban: jelaskan pendekatannya dalam beberapa kalimat, lalu tulis solusi lengkap dalam satu blok ```python dengan nama fungsi persis seperti yang diminta, tanpa input() dan tanpa print di luar fungsi. Setelah itu beri contoh pemakaian singkat dan kasus khusus yang ditangani.

---

Untuk pelajaran olahraga, tulis fungsi `bagi_tim_seimbang(pemain: dict[str, int]) -> tuple[list[str], list[str]]` yang membagi pemain menjadi dua tim berdasarkan skor kemampuannya. Jumlah anggota kedua tim boleh berbeda paling banyak satu, dan selisih total skor kedua tim harus sekecil mungkin. Nama di dalam setiap tim diurutkan menurut abjad, dan tim yang memuat nama pertama menurut abjad ditulis lebih dulu. Jumlah pemain paling banyak 20. Lempar `ValueError` jika pemain kurang dari 2.
````

## ud-031 · web

````text
Jawab pertanyaan di bawah garis dalam bahasa Indonesia yang baku tapi luwes. Langsung ke jawabannya: jangan membuka dengan basa-basi, jangan menyebut dirimu AI atau model bahasa, dan jangan menampilkan proses berpikir.

Format jawaban: satu kalimat pembuka, lalu satu dokumen HTML lengkap dalam satu blok ```html. CSS dan JavaScript ada di dalam file itu, tanpa library, font, gambar, atau file dari luar. Halaman harus responsif sampai lebar 375 px, tanpa error JavaScript, dan akses localStorage dibungkus try/catch. Setelah kode, tulis bagian **Cek kebutuhan** berupa daftar `- **<hal yang diminta>** → <bagian kode yang memenuhinya>` untuk setiap permintaan, lalu **Catatan teknis** singkat.

---

Buatkan aplikasi pencatat iuran warga RT dalam satu file HTML. Bendahara bisa menambah, mengubah, dan menghapus data warga (nama kepala keluarga dan nomor rumah), menetapkan besar iuran bulanan, lalu mencentang status lunas setiap warga per bulan dalam tabel Januari–Desember untuk tahun yang dipilih. Tampilkan total kas masuk per bulan, daftar warga yang menunggak beserta jumlah tunggakannya sampai bulan berjalan, dan tombol ekspor CSV. Data tersimpan di localStorage. Pakai data contoh fiktif.
````

## ud-032 · web

````text
Jawab pertanyaan di bawah garis dalam bahasa Indonesia yang baku tapi luwes. Langsung ke jawabannya: jangan membuka dengan basa-basi, jangan menyebut dirimu AI atau model bahasa, dan jangan menampilkan proses berpikir.

Format jawaban: satu kalimat pembuka, lalu satu dokumen HTML lengkap dalam satu blok ```html. CSS dan JavaScript ada di dalam file itu, tanpa library, font, gambar, atau file dari luar. Halaman harus responsif sampai lebar 375 px, tanpa error JavaScript, dan akses localStorage dibungkus try/catch. Setelah kode, tulis bagian **Cek kebutuhan** berupa daftar `- **<hal yang diminta>** → <bagian kode yang memenuhinya>` untuk setiap permintaan, lalu **Catatan teknis** singkat.

---

bikin game tetris satu file html pakai canvas. 7 bentuk balok standar, bisa diputar, geser kiri kanan, turun cepat, dan hard drop pakai keyboard, plus tombol layar sentuh buat hp. ada preview balok berikutnya, skor, level yang makin cepat tiap 10 baris, tombol jeda, dan skor tertinggi disimpan di localStorage.
````

## ud-033 · web

````text
Jawab pertanyaan di bawah garis dalam bahasa Indonesia yang baku tapi luwes. Langsung ke jawabannya: jangan membuka dengan basa-basi, jangan menyebut dirimu AI atau model bahasa, dan jangan menampilkan proses berpikir.

Format jawaban: satu kalimat pembuka, lalu satu dokumen HTML lengkap dalam satu blok ```html. CSS dan JavaScript ada di dalam file itu, tanpa library, font, gambar, atau file dari luar. Halaman harus responsif sampai lebar 375 px, tanpa error JavaScript, dan akses localStorage dibungkus try/catch. Setelah kode, tulis bagian **Cek kebutuhan** berupa daftar `- **<hal yang diminta>** → <bagian kode yang memenuhinya>` untuk setiap permintaan, lalu **Catatan teknis** singkat.

---

Buatkan aplikasi jadwal proyek berbentuk Gantt chart dalam satu file HTML. Setiap tugas punya nama, penanggung jawab, tanggal mulai, durasi dalam hari, persentase progres, dan boleh bergantung pada tugas lain (tugas itu baru boleh mulai setelah tugas yang ditunggunya selesai). Tampilkan batang setiap tugas pada skala hari beserta garis hari ini, warnai tugas yang terlambat, dan tolak ketergantungan yang melingkar. Data tersimpan di localStorage, dan sertakan data contoh proyek renovasi kantor.
````

## ud-034 · web

````text
Jawab pertanyaan di bawah garis dalam bahasa Indonesia yang baku tapi luwes. Langsung ke jawabannya: jangan membuka dengan basa-basi, jangan menyebut dirimu AI atau model bahasa, dan jangan menampilkan proses berpikir.

Format jawaban: satu kalimat pembuka, lalu satu dokumen HTML lengkap dalam satu blok ```html. CSS dan JavaScript ada di dalam file itu, tanpa library, font, gambar, atau file dari luar. Halaman harus responsif sampai lebar 375 px, tanpa error JavaScript, dan akses localStorage dibungkus try/catch. Setelah kode, tulis bagian **Cek kebutuhan** berupa daftar `- **<hal yang diminta>** → <bagian kode yang memenuhinya>` untuk setiap permintaan, lalu **Catatan teknis** singkat.

---

Buat permainan catur untuk dua pemain di satu perangkat dalam satu file HTML, tanpa library. Langkah setiap bidak harus divalidasi, termasuk rokade, en passant, dan promosi pion. Tandai petak tujuan yang sah saat bidak dipilih, tolak langkah yang membuat raja sendiri terkena skak, lalu deteksi skak, skakmat, dan remis karena pat. Tampilkan riwayat langkah dalam notasi aljabar dan tombol untuk membatalkan langkah.
````

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
