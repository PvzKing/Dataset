# Rencana: model jago Python sekaligus jago membuat website

Dokumen ini adalah rencana kerja untuk adapter berikutnya (v4) di atas Qwen3.5-4B. Ada dua target yang harus tercapai bersamaan:

1. **Python:** menulis kode yang teliti, membaca error lalu memperbaikinya, menulis tes, dan menjelaskan dalam bahasa Indonesia.
2. **Website:** tetap kuat membuat website one-shot dan memperbaiki bug web, lalu naik lewat data yang diarahkan oleh hasil uji. Kedua kemampuan juga dijembatani lewat sampel Python untuk web (backend, generator HTML).

Ringkasnya: **ukur dulu, latih dengan data yang terverifikasi, dan terima adapter hanya jika lolos gerbang uji.**

Bagian 5 mencatat apa yang sudah dikerjakan di repo. Langkah yang butuh GPU ada di [`PROSEDUR_V4.md`](PROSEDUR_V4.md) (T4, v4-pilot dengan resep v3) dan [`PROSEDUR_V4_A100.md`](PROSEDUR_V4_A100.md) (A100: v4 dari model dasar, LoRA 16-bit, konteks 16.384).

---

## 1. Titik awal

| Model | HumanEval | HumanEval+ | Catatan |
|---|---|---|---|
| Model dasar Qwen3.5-4B (4-bit, greedy) | 82,3% | 73,8% | pembanding utama |
| v3 (dataset own, website) | belum diukur | belum diukur | Bagian C di PROSEDUR_V4 |
| bench-lanjut (v3 + 164 soal HumanEval) | 78,0% | 72,0% | terkontaminasi, tidak dipakai lagi |

Kemampuan website v3 sejauh ini hanya dinilai dari dua website uji setelah training. Belum ada angka terukur yang bisa dibandingkan, dan itu yang diperbaiki oleh Web-eval.

**Pelajaran dari bench-lanjut:**
1. **Model 4B ini sudah kuat di Python.** Fine-tuning kecil hampir tidak bisa menaikkan skor benchmark umum, dan risiko terbesarnya justru menurunkan skor. Jadi untuk Python umum targetnya *tidak turun*, sedangkan *naik* diukur pada hal yang memang diajarkan.
2. **Model meniru gaya jawaban latihan lebih cepat daripada isinya.** Jawaban latihan yang ringkas membuat model kehilangan ketelitiannya, misalnya `split(" ")` dan nilai awal `-1`. Gaya jawaban di data harus gaya yang kita inginkan: teliti, menyebut kasus tepi, dan disertai tes.
3. **Loss training menyesatkan.** Sebagian besar token jawaban hanya salinan signature dan docstring, jadi loss tetap rendah walaupun isi fungsinya belum dikuasai. Keputusan diambil dari hasil uji, bukan dari loss.
4. **Selisih kecil belum tentu nyata.** Selisih −7 soal ternyata tidak signifikan (McNemar p = 0,34), karena ±40 soal berpindah status ke dua arah. Setiap klaim naik atau turun harus diuji statistik.

## 2. Arti "jago": papan skor dan gerbang

Adapter **diterima** hanya jika lolos semua gerbang yang sudah bisa diukur. `eval-suite/papan_skor.py` menghitung semuanya dari folder hasil uji.

| Gerbang | Ukuran | Syarat lolos |
|---|---|---|
| G1. Python umum tidak turun | HumanEval+ dan MBPP+ (EvalPlus, 164 + 378 soal) | tidak ada penurunan nyata (McNemar p ≥ 0,05 untuk arah turun) dan selisih gabungan ≥ −1,5 poin |
| G2. Python yang diajarkan naik | **IndoPy-test**: 40 soal Python berbahasa Indonesia dengan tes tersembunyi, tidak pernah dilatih | naik nyata dari model dasar (McNemar p < 0,05) |
| G3. Website tidak turun | **Web-eval**: 10 prompt website baru, dinilai otomatis di Chromium | jumlah website yang lolos ≥ v3 |
| G4. Perbaikan bug | 10 bug Python dan 10 bug web baru | patch diterapkan ≥ 90%, tes lolos setelah patch ≥ model dasar. Set ujinya dibuat di Fase 3 |

**Soal buatan sendiri:**
- **IndoPy** dibutuhkan karena HumanEval dan MBPP hanya mengukur fungsi pendek berbahasa Inggris. Yang ingin diajarkan lebih luas: konteks Indonesia (rupiah, tanggal, zona waktu WIB/WITA/WIT, format administrasi), spesifikasi yang harus dibaca teliti, dan penjelasan berbahasa Indonesia.
- **Web-eval** dibutuhkan karena website tidak bisa dinilai dari teks jawaban. Website harus dibuka dan dipakai: misalnya 100 °C harus menjadi 212 °F, data harus tetap ada setelah reload, dan jam WIB harus benar walaupun server memakai UTC.

**Disiplin data uji:**
- IndoPy dibagi dua. **dev** (20 soal) boleh dilihat untuk analisis kegagalan. **test** (40 soal) dikunci dan hanya dijalankan saat penilaian akhir.
- Soal uji, prompt Web-eval, dan website rujukannya tidak boleh dijadikan sampel latihan, termasuk versi yang hanya diubah sedikit. `scripts/decontaminate.py` memeriksanya sebelum setiap training.
- Soal IndoPy dan website rujukan Web-eval ditulis oleh agen terpisah dari penulis sampel latihan, supaya data latihan tidak tanpa sadar disesuaikan dengan soal uji.

**Batas Web-eval:** 10 website terlalu sedikit untuk uji statistik. Karena itu G3 dinilai dari jumlah website yang lolos, dan Web-eval diperbesar menjadi 20 prompt di Fase 3.

## 3. Prinsip data

1. **Setiap kode dijalankan.** Sampel Python dibangun dari file sumber di `data/python-src/` oleh `scripts/build_python_samples.py`. Kode dan output di jawaban diisi dari file dan eksekusi sungguhan, dan patch `SEARCH/REPLACE` dibuktikan menghasilkan file perbaikan. Website diuji di browser.
2. **Proses sebelum kode.** Jawaban memetakan aturan dan kasus tepi dulu, baru menulis kode, menampilkan hasil menjalankan, lalu menutup dengan **Cek kebutuhan** untuk program yang lebih besar.
3. **Panjang jawaban sesuai permintaan.** Soal fungsi pendek dijawab pendek tapi tetap teliti.
4. **Bahasa mengikuti prompt.** Sekitar 80% prompt berbahasa Indonesia dan 20% berbahasa Inggris, dijawab dalam bahasa yang sama.
5. **Bersih dari benchmark.** `scripts/decontaminate.py` memeriksa 13-gram terhadap HumanEval+, MBPP+, IndoPy, dan prompt Web-eval.
6. **Website tetap ikut di setiap run.** Data web dilatih ulang bersama data Python, dan adapter tidak disambung dari adapter sebelumnya. Penyambungan itulah yang membuat bench-lanjut mengacak hasil v3.
7. **Web diperkuat lewat data yang diarahkan hasil uji.** Kegagalan Web-eval dianalisis per *jenis* kesalahan, misalnya zona waktu, persistensi, atau validasi form. Sampel web baru ditulis untuk jenis itu, tidak pernah untuk prompt ujinya.

## 4. Komposisi data

| Kategori | Pilot (sudah ada) | Target v4 | Isi |
|---|---|---|---|
| `py_fungsi` | 6 | 35 | fungsi ringkas dengan kasus tepi: nomor HP, interval, hari kerja, kata terbanyak, kembalian (DP), urutan dependensi |
| `py_program` | 3 + `tech-023` | 25 | program lengkap dengan tes: terbilang, angsuran anuitas, file duplikat, to-do dengan penyimpanan atomik |
| `py_debug` | 3 | 20 | bug di pesan user, lalu penyebab dan patch: argumen default mutable, pembulatan bankir, datetime tanpa zona |
| `py_data` | 2 | 15 | CSV ekspor Excel (titik koma, BOM, format Indonesia), log nginx |
| `py_tes` | 1 | 10 | menulis tes yang menemukan bug, lalu memperbaikinya |
| `py_agentic` | 2 | 10 | multi-giliran: server Python 3.8, kebutuhan berubah karena data spreadsheet |
| `py_review` | 1 | 5 | review keamanan login (SQL injection, hash password) |
| `py_web` | 2 | 10 | Python untuk web: buku tamu Flask + SQLite yang aman XSS, generator katalog HTML statis |
| **Python** | **21 (±42 ribu token)** | **±130 (±230 ribu token)** | |
| Web (`web_oneshot`, `web_debug`) | 38 (±163 ribu token) | 38 + sampel dari analisis Web-eval | |
| Teknologi, matematika, sains | 43 (±33 ribu token) | tetap | |

Saat pilot, porsi Python sekitar 18% token. Pada v4 penuh targetnya sekitar 50%.

**Opsional, sangat dianjurkan: data swa-distilasi terverifikasi (±200 sampel).**
1. Ditulis 200 soal Python baru beserta tes tersembunyinya.
2. Model dasar menjawab setiap soal 4 kali.
3. Hanya jawaban yang lolos tes yang disimpan.

Data ini memakai gaya model itu sendiri, jadi menjaga ketelitian model dasar dan mengurangi *forgetting*. Langkah ini wajib jika v3 ternyata sudah di bawah model dasar (keputusan Fase 0).

**Pengganti data campuran `code`:** `mix_general.py` sekarang mengambil Magicoder-Evol-Instruct, yang jawabannya dibuat GPT-4 dan tidak dijalankan. Kalau data campuran dipakai, ganti dengan dataset yang lolos uji eksekusi, misalnya `bigcode/self-oss-instruct-sc2-exec-filter-50k`, setelah lisensi dan dekontaminasinya dicek di kartu dataset.

## 5. Status eksekusi

**Sudah dikerjakan di repo** (diuji tanpa GPU):

| Bagian | File | Bukti |
|---|---|---|
| MBPP+ dan uji McNemar | `humaneval-bench-script/eval_humaneval.py --dataset mbpp` | demo 378 soal berjalan. Hasil demo HumanEval sama persis dengan versi sebelumnya |
| IndoPy | `eval-suite/indopy_eval.py`, `eval-suite/indopy/{dev,test}.jsonl` | setiap solusi rujukan lolos tesnya, dan setiap solusi salah ditolak |
| Web-eval | `eval-suite/web_eval.py`, `eval-suite/web/` | `uji_pemeriksa.py`: 10 website rujukan lolos, 10 versi rusaknya (satu bug per website) ditolak |
| Papan skor | `eval-suite/papan_skor.py` | diuji dengan hasil demo |
| Pembangun sampel | `scripts/build_python_samples.py` | `--check` memastikan train.jsonl sama dengan hasil eksekusi ulang |
| Dekontaminasi | `scripts/decontaminate.py` | 0 tumpang tindih 13-gram |
| Data pilot | `data/python-src/py-001` … `py-020` | 20 sampel. Patch di sampel debug terbukti; Flask dan HTML diuji di Chromium |

**Belum dikerjakan:**
- Semua yang butuh GPU: uji baseline, training v4-pilot atau v4, dan uji setelahnya. Prosedurnya di [`PROSEDUR_V4.md`](PROSEDUR_V4.md) dan [`PROSEDUR_V4_A100.md`](PROSEDUR_V4_A100.md).
- Sampel panjang (di atas ±6.200 token) yang memanfaatkan konteks 16.384 di A100.
- Set uji G4 (perbaikan bug).
- Web-eval 20 prompt.
- Data penuh dan swa-distilasi.

## 6. Resep training

| Pengaturan | v4-pilot | v4 penuh | Alasan |
|---|---|---|---|
| Titik awal | model dasar | model dasar | hasil bisa diulang, tidak mewarisi pergeseran adapter lama |
| Data | own sekarang (102 sampel) | own + Python penuh + swa-distilasi | web selalu ikut |
| Epoch | 3 (sama dengan v3) | 2, dengan checkpoint tiap epoch | pilot memakai resep v3 persis, supaya perbedaan hasil pasti berasal dari data |
| LoRA | r 16, alpha 32, lr 1e-4 cosine | sama | r 32 hanya dicoba jika uji menunjukkan underfit |
| Panjang | `max_seq_len` 6144 (T4) | sama | semua sampel ≤ ±6.200 token |

**Pemilihan checkpoint di v4 penuh:** uji cepat setiap checkpoint dengan HumanEval+ dan IndoPy-dev (±30 menit per checkpoint). Checkpoint terbaik baru diuji lengkap.

## 7. Tahapan

| Fase | Kerja | Status | Hasil |
|---|---|---|---|
| 0. Diagnosis | v3 vs model dasar di HumanEval+, MBPP+, IndoPy-dev, Web-eval | menunggu Colab | tahu apakah dataset web sudah menggeser Python, dan angka web v3 |
| 1. Alat ukur | MBPP+, IndoPy, Web-eval, papan skor, dekontaminasi, pembangun sampel | **selesai** | papan skor siap |
| 2. Pilot | 20 sampel Python, latih v4-pilot, uji | data **selesai**, training menunggu Colab | tahu apakah gaya sampel membantu sebelum dibuat 130 |
| 3. Perluasan | set uji G4, Web-eval 20 prompt, data Python penuh, sampel web dari analisis kegagalan | setelah Fase 2 | dataset v4 |
| 4. Swa-distilasi | 200 soal + tes, generate dengan model dasar, saring dengan tes | setelah Fase 0 | ±200 sampel jangkar |
| 5. Training v4 | latih, pilih checkpoint, uji semua gerbang | – | keputusan terima atau tolak |
| 6. Iterasi | analisis kegagalan di IndoPy-dev dan Web-eval → sampel baru untuk jenis kesalahannya | – | v4.1 dan seterusnya |
| 7. Lanjutan | DPO dengan pasangan jawaban lolos dan gagal dari Fase 4 | eksperimen | ketelitian naik tanpa data baru |

**Keputusan setelah Fase 0:**
- **v3 ≈ model dasar di Python:** dataset web aman. Lanjutkan rencana apa adanya.
- **v3 jelas di bawah model dasar:** swa-distilasi di Fase 4 menjadi wajib.
- **v3 di atas model dasar:** tetap jalankan rencana. G1 dibandingkan juga dengan v3.

**Keputusan setelah Fase 2 (v4-pilot vs v3):**
- **IndoPy-dev naik, G1 lolos, dan Web-eval ≥ v3:** gaya sampel terbukti. Lanjut ke Fase 3.
- **IndoPy-dev tidak naik:** periksa jawaban di `eval-indopy-dev/<run>/hasil.jsonl` sebelum menambah data. Menambah data dengan gaya yang salah hanya memperbesar masalah.
- **Web-eval turun:** cek apakah kegagalannya baru (regresi) atau sama dengan v3, sebelum menambah porsi Python.

## 8. Anggaran waktu di T4

Angka training dikalibrasi dari v3 (±13 ribu token per menit). Angka uji berasal dari run HumanEval sebelumnya.

| Pekerjaan | Perkiraan |
|---|---|
| Training v4-pilot (±238 ribu token × 3 epoch) | ±55–65 menit |
| Training v4 penuh (±430 ribu token × 2 epoch) | ±70–85 menit |
| HumanEval+ satu model | 17–23 menit |
| MBPP+ satu model (378 soal) | ±40–55 menit (perkiraan) |
| IndoPy-dev 20 soal / test 40 soal | ±5–10 / ±10–15 menit |
| Web-eval 10 website | ±30–45 menit (generate panjang, batch 2) |

Jawaban model dasar disimpan dan dipakai ulang, jadi model dasar cukup diuji sekali per benchmark.

## 9. Risiko dan penanganannya

| Risiko | Tanda | Penanganan |
|---|---|---|
| Kemampuan web turun | Web-eval < v3 | naikkan porsi web atau kurangi epoch. Data web selalu ikut dilatih |
| Python umum turun | G1 gagal | tambah data swa-distilasi, turunkan lr ke 5e-5, pilih checkpoint lebih awal |
| Model jadi bertele-tele | jawaban `py_fungsi` atau HumanEval memanjang, kode terpotong | perbanyak sampel ringkas. Cek panjang jawaban di laporan uji |
| Kontaminasi tak sengaja | sampel mirip soal uji | `scripts/decontaminate.py` wajib dijalankan sebelum training |
| Overfit ke IndoPy atau Web-eval | dev naik, test tidak | soal test dikunci. Sampel baru hanya untuk jenis kesalahan |
| Output di jawaban tidak sesuai eksekusi | `build_python_samples.py --check` gagal | sampel tidak boleh masuk sebelum lolos |
| Pemeriksaan Web-eval terlalu longgar atau terlalu ketat | website bagus ditolak, atau website rusak lolos | `eval-suite/web/uji_pemeriksa.py` dijalankan setiap kali pemeriksaan diubah |
| Colab terputus | – | semua script generate dan uji bisa dilanjutkan dari titik terakhir |

## 10. Analisis hukum

1. **Hak cipta kode.** Program komputer adalah ciptaan yang dilindungi (Pasal 40 ayat (1) huruf s UU No. 28 Tahun 2014 tentang Hak Cipta).
   - Kode dari repositori publik, forum, atau StackOverflow tidak boleh disalin ke dataset kecuali lisensinya mengizinkan dan syaratnya dipenuhi. Konten StackOverflow berlisensi CC BY-SA, yang mewajibkan atribusi dan lisensi serupa untuk turunannya.
   - Sampel pilot ditulis baru.
   - MBPP+ dan HumanEval+ hanya dipakai sebagai alat uji, tidak dilatih.
2. **Ketentuan layanan penyedia model.** Dataset yang dibuat model berbayar, misalnya Magicoder-Evol (GPT-4), dan sampel yang ditulis asisten AI dapat terikat ketentuan layanan penyedianya. Ketentuan itu bisa membatasi pemakaian output untuk mengembangkan model yang bersaing.
   - Ini soal perjanjian, bukan hak cipta. Status hak cipta output AI di Indonesia belum jelas, karena pencipta didefinisikan sebagai orang (Pasal 1 angka 2 UU Hak Cipta).
   - Perjanjian tetap mengikat para pihak (Pasal 1338 KUHPerdata), dan pelanggarannya bisa digugat sebagai wanprestasi (Pasal 1243 KUHPerdata).
   - Cek ketentuan yang berlaku untuk jenis akun yang dipakai, terutama sebelum model didistribusikan atau dikomersialkan.
   - Data swa-distilasi dari Qwen sendiri lebih bersih dari sisi ini. Lisensi Qwen3.5 tetap perlu dicek di kartu modelnya.
3. **Data pribadi.** Sampel hanya memakai data fiktif: nomor HP contoh, nama umum, dan toko rekaan. Rencana sampel validasi NIK dibatalkan, karena NIK rekaan dengan kode wilayah asli bisa kebetulan sama dengan NIK orang sungguhan. Data pribadi orang sungguhan tidak boleh masuk dataset, karena pemrosesannya membutuhkan dasar yang sah menurut UU No. 27 Tahun 2022 tentang Pelindungan Data Pribadi.
4. **Klaim skor.** Skor v4 hanya boleh dipublikasikan jika:
   - lolos dekontaminasi;
   - disertai kondisi ujinya (greedy, pass@1, versi EvalPlus, 4-bit);
   - dibandingkan dengan model dasar.

   Klaim yang melebihkan mutu berisiko melanggar Pasal 9 ayat (1) huruf a dan Pasal 10 huruf b UU No. 8 Tahun 1999 tentang Perlindungan Konsumen. Skor IndoPy dan Web-eval adalah uji internal dan harus disebut begitu.
