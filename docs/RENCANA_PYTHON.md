# Rencana: model jago Python tanpa kehilangan kemampuan coding lain

Dokumen ini adalah rencana kerja untuk adapter berikutnya (v4) di atas Qwen3.5-4B. Target v4: menulis Python dengan teliti, membaca error dan memperbaikinya, serta menjelaskan dalam bahasa Indonesia. Kemampuan membuat website one-shot dan perbaikan bug web tidak boleh turun.

Ringkasnya: **ukur dulu, latih dengan data yang terverifikasi, dan terima adapter hanya jika lolos gerbang uji.**

---

## 1. Titik awal

| Model | HumanEval | HumanEval+ | Catatan |
|---|---|---|---|
| Model dasar Qwen3.5-4B (4-bit, greedy) | 82,3% | 73,8% | pembanding utama |
| v3 (dataset own, website) | belum diukur | belum diukur | Langkah 5 PROSEDUR |
| bench-lanjut (v3 + 164 soal HumanEval) | 78,0% | 72,0% | terkontaminasi, tidak dipakai lagi |

**Pelajaran dari bench-lanjut:**
1. **Model 4B ini sudah kuat di Python.** Fine-tuning kecil hampir tidak bisa menaikkan skornya. Risiko terbesarnya justru menurunkan skor. Jadi target pertama adalah *tidak turun*. Target kedua adalah *naik di hal yang memang diajarkan*.
2. **Model meniru gaya jawaban latihan lebih cepat daripada isinya.** Jawaban latihan yang ringkas membuat model kehilangan ketelitiannya. Contohnya `split(" ")` dan nilai awal `-1`. Jadi gaya jawaban di data harus gaya yang kita inginkan: teliti, menyebut kasus tepi, dan disertai tes.
3. **Loss training menyesatkan.** Sebagian besar token jawaban hanya salinan signature dan docstring, jadi loss rendah walaupun isi fungsinya belum dikuasai. Keputusan diambil dari hasil uji, bukan dari loss.
4. **Selisih kecil belum tentu nyata.** Selisih −7 soal ternyata tidak signifikan (McNemar p = 0,34), karena ±40 soal berpindah status ke dua arah. Setiap klaim naik atau turun harus diuji statistik.

## 2. Arti "jago": papan skor dan gerbang

Adapter v4 **diterima** hanya jika lolos semua gerbang di bawah. Pembandingnya model dasar, dan untuk kemampuan web pembandingnya v3.

| Gerbang | Ukuran | Syarat lolos |
|---|---|---|
| G1. Python umum tidak turun | HumanEval+ dan MBPP+ (EvalPlus, 164 + 378 soal) | tidak ada penurunan signifikan (McNemar p ≥ 0,05 untuk arah turun) dan selisih gabungan ≥ −1,5 poin |
| G2. Python yang diajarkan naik | **IndoPy-test**: 40 soal Python berbahasa Indonesia dengan tes tersembunyi, tidak pernah dilatih | naik signifikan dari model dasar (McNemar p < 0,05) |
| G3. Website tidak turun | **Web-eval**: 10 prompt website baru, dinilai otomatis dengan Playwright | jumlah website yang lolos ≥ v3 |
| G4. Perbaikan bug | 10 bug Python dan 10 bug web baru | patch diterapkan ≥ 90%, tes lolos setelah patch ≥ model dasar |

**Kenapa harus ada soal buatan sendiri (IndoPy)?** HumanEval dan MBPP hanya mengukur fungsi pendek berbahasa Inggris. Yang ingin diajarkan lebih luas dari itu:
- konteks Indonesia, seperti rupiah, tanggal WIB, NIK, PPN, dan terbilang;
- program utuh;
- membaca traceback;
- penjelasan berbahasa Indonesia.

Tanpa soal sendiri, kenaikan di hal-hal itu tidak akan terlihat.

**Disiplin data uji:**
- IndoPy dibagi dua. **dev** (20 soal) boleh dilihat untuk analisis kegagalan. **test** (40 soal) dikunci dan hanya dijalankan saat penilaian akhir.
- Soal uji tidak boleh dijadikan sampel latihan, termasuk versi yang hanya diubah sedikit. Kalau dilanggar, kita mengulang kesalahan bench-lanjut.

## 3. Prinsip data

1. **Setiap kode dijalankan.** Output yang ditulis di jawaban harus hasil eksekusi sungguhan. Tes dan validator memastikannya.
2. **Proses sebelum kode.** Jawaban yang panjang mengikuti pola `tech-023`:
   1. petakan aturan dan kasus tepi;
   2. tulis kode;
   3. tampilkan hasil menjalankan;
   4. tutup dengan **Cek kebutuhan**.
3. **Panjang jawaban sesuai permintaan.** Soal fungsi pendek dijawab pendek tapi tetap teliti. Kalau semua sampel panjang, model akan menulis esai untuk soal yang cukup dijawab 10 baris.
4. **Bahasa mengikuti prompt.** Sekitar 75% prompt berbahasa Indonesia dan 25% berbahasa Inggris, dijawab dalam bahasa yang sama. Benchmark dan dokumentasi library sebagian besar berbahasa Inggris.
5. **Bersih dari benchmark.** Semua sampel dicek tumpang tindihnya dengan HumanEval dan MBPP: 13-gram dan nama fungsi. Sampel yang terlalu mirip dibuang.
6. **Website tetap ikut di setiap run.** Data web dilatih ulang bersama data Python. Adapter tidak lagi disambung dari adapter sebelumnya, karena itu yang membuat bench-lanjut mengacak hasil v3.

## 4. Komposisi data v4

| Kategori | Sampel | Rata-rata token | Isi |
|---|---|---|---|
| `py_fungsi` | 35 | ±700 | soal fungsi baru yang mirip gaya benchmark (string, list, angka, rekursi, DP kecil), dengan kasus tepi. Jawaban ringkas, ditutup daftar kasus tepi |
| `py_program` | 25 | ±3.000 | program lengkap dengan tes, seperti `tech-023`: terbilang, hitung PPN, validasi NIK fiktif, jadwal WIB, CLI `argparse` |
| `py_debug` | 20 | ±1.800 | traceback atau tes gagal di prompt, lalu penyebab dan patch `SEARCH/REPLACE`. Sama seperti `web_debug`, kode ber-bug hanya ada di pesan user |
| `py_data` | 15 | ±2.000 | CSV/JSON, `datetime` dan zona waktu, regex, `sqlite3`, pengolahan file, semuanya hanya dengan library standar |
| `py_tes` | 10 | ±1.500 | menulis tes `unittest`/`pytest` untuk kode yang diberikan, termasuk menemukan bug lewat tes |
| `py_agentic` | 10 | ±2.500 | multi-turn: model menulis kode, user mengirim output tes yang gagal, model memperbaiki sampai lolos. Format sama dengan agen di `agent_gradio.py` |
| `py_review` | 5 | ±1.500 | review dan refactor kode dengan alasan yang jelas |
| **Python baru** | **120** | | **±210 ribu token** |
| Dataset own sekarang (web + teknologi + MIPA) | 82 | | ±199 ribu token |
| **Total v4** | **202** | | **±410 ribu token per epoch, porsi Python ±50%** |

**Opsional, sangat dianjurkan: data swa-distilasi terverifikasi (±200 sampel, ±120 ribu token).**
1. Saya menulis 200 soal Python baru beserta tes tersembunyinya.
2. Model dasar menjawab setiap soal 4 kali.
3. Hanya jawaban yang lolos tes yang disimpan.

Data ini memakai gaya model itu sendiri, jadi melatihnya hampir tidak menggeser distribusi model. Cara ini dikenal mengurangi *forgetting* (self-distillation fine-tuning). Data ini juga menjadi "jangkar" yang menjaga ketelitian model dasar, sementara sampel buatan tangan mengajarkan hal baru. Generate-nya ±2 jam di T4 dan bisa dilanjutkan jika Colab terputus.

**Pengganti data campuran `code`:** `mix_general.py` sekarang mengambil Magicoder-Evol-Instruct. Jawaban di dataset itu dibuat GPT-4 dan tidak dijalankan. Kalau data campuran dipakai, ganti dengan dataset yang lolos uji eksekusi, misalnya `bigcode/self-oss-instruct-sc2-exec-filter-50k`. Cek dulu lisensi dan keterangan dekontaminasinya di kartu dataset.

## 5. Resep training v4

| Pengaturan | Nilai | Alasan |
|---|---|---|
| Titik awal | model dasar, bukan v3 atau bench-lanjut | hasilnya bisa diulang dan tidak mewarisi pergeseran adapter lama |
| Data | own (82) + Python baru (120) + swa-distilasi (opsional) | web tetap ikut dilatih |
| Epoch | 2, dengan checkpoint tiap epoch | data lebih besar. Checkpoint dipilih dari hasil uji |
| LoRA | r 16, alpha 32, lr 1e-4 cosine | sama dengan v3, supaya perbedaan hasil berasal dari data. r 32 hanya dicoba jika uji menunjukkan underfit |
| Validasi | 10% sampel Python ditahan sebagai eval loss | memantau overfit. Tetap bukan dasar keputusan akhir |
| Panjang | `max_seq_len` 6144 (T4), semua sampel ≤ ±5.900 token | tidak ada sampel yang terbuang |

**Pemilihan checkpoint.** Uji cepat setiap checkpoint dengan HumanEval+ dan IndoPy-dev (±30 menit per checkpoint). Checkpoint terbaik baru diuji lengkap dengan semua gerbang.

## 6. Tahapan

| Fase | Kerja | Pelaksana | Waktu Colab T4 | Hasil |
|---|---|---|---|---|
| 0. Diagnosis | Langkah 5 PROSEDUR: v3 vs model dasar | kamu | ±20 menit | tahu apakah dataset web sudah menggeser Python |
| 1. Alat ukur | dukungan MBPP+ di script eval, IndoPy (60 soal + runner), Web-eval otomatis, validator yang menjalankan kode sampel, script dekontaminasi | saya | ±2–3 jam untuk baseline model dasar dan v3 | papan skor siap; skor awal tercatat |
| 2. Pilot | 20 sampel Python dari semua kategori, latih v4-pilot (own + 20) | saya → kamu | ±1 jam training + ±1,5 jam uji | gaya sampel terbukti membantu atau tidak sebelum dibuat 120 |
| 3. Data penuh | 120 sampel + dekontaminasi + review kamu untuk catatan hukumnya | saya + kamu | – | dataset v4 |
| 4. Swa-distilasi (opsional) | 200 soal + tes, generate dengan model dasar, saring dengan tes | saya → kamu | ±2 jam | ±200 sampel jangkar |
| 5. Training v4 | latih, pilih checkpoint, uji semua gerbang | kamu | ±1,5–2 jam training + ±3 jam uji | keputusan terima atau tolak |
| 6. Iterasi | analisis kegagalan di IndoPy-dev → sampel baru untuk **jenis** kesalahannya, bukan untuk soalnya | saya | sesuai kebutuhan | v4.1 dan seterusnya |
| 7. Lanjutan (eksperimen) | DPO dengan pasangan jawaban lolos dan gagal dari Fase 4 | saya → kamu | perlu diuji muat di T4 | ketelitian naik tanpa data baru |

**Keputusan setelah Fase 0:**
- **v3 ≈ model dasar:** dataset web aman. Lanjutkan rencana apa adanya.
- **v3 jelas di bawah model dasar:** dataset web sudah menggeser kemampuan Python. Data swa-distilasi di Fase 4 menjadi wajib, bukan opsional.
- **v3 di atas model dasar:** bagus. Tetap jalankan rencana. Gerbang G1 dibandingkan dengan v3 juga.

**Keputusan setelah Fase 2:**
- **IndoPy-dev naik dan HumanEval+ tidak turun:** lanjut ke 120 sampel.
- **IndoPy-dev tidak naik:** periksa gaya sampel sebelum menambah jumlah. Menambah data dengan gaya yang salah hanya memperbesar masalah.

## 7. Anggaran waktu di T4

Angka training dikalibrasi dari v3, yaitu ±13 ribu token per menit. Angka uji berasal dari run HumanEval kemarin.

| Pekerjaan | Perkiraan |
|---|---|
| Training v4 (±410 ribu token × 2 epoch) | ±65–80 menit |
| Training v4 + swa-distilasi (±530 ribu × 2) | ±85–100 menit |
| HumanEval+ satu model | 17–23 menit |
| MBPP+ satu model (378 soal) | ±40–55 menit (perkiraan) |
| IndoPy 60 soal | ±10–15 menit |
| Web-eval 10 website | ±45–60 menit (generate satu per satu) |

Jawaban model dasar disimpan dan dipakai ulang, jadi model dasar cukup diuji sekali per benchmark.

## 8. Risiko dan penanganannya

| Risiko | Tanda | Penanganan |
|---|---|---|
| Kemampuan web turun | Web-eval < v3 | naikkan porsi web atau kurangi epoch. Data web selalu ikut dilatih |
| Python umum turun | G1 gagal | tambah data swa-distilasi, turunkan lr ke 5e-5, pilih checkpoint lebih awal |
| Model jadi bertele-tele | jawaban `py_fungsi` atau HumanEval memanjang, kode terpotong | perbanyak sampel ringkas. Cek panjang jawaban di laporan uji |
| Kontaminasi tak sengaja | sampel mirip soal benchmark | script dekontaminasi wajib dijalankan sebelum training |
| Overfit ke IndoPy | dev naik, test tidak | soal test dikunci. Sampel baru hanya ditulis untuk jenis kesalahan |
| Output di jawaban tidak sesuai eksekusi | validator gagal | sampel tidak boleh masuk sebelum validator lolos |
| Colab terputus | – | semua script generate dan uji bisa dilanjutkan dari titik terakhir |

## 9. Analisis hukum

1. **Hak cipta kode.** Program komputer adalah ciptaan yang dilindungi (Pasal 40 ayat (1) huruf s UU No. 28 Tahun 2014 tentang Hak Cipta).
   - Kode dari repositori publik, forum, atau StackOverflow tidak boleh disalin ke dataset kecuali lisensinya mengizinkan dan syaratnya dipenuhi. Konten StackOverflow berlisensi CC BY-SA, yang mewajibkan atribusi dan lisensi serupa untuk turunannya.
   - Sampel ditulis baru. Dataset terbuka hanya dipakai jika lisensinya jelas, dan berkas lisensi serta catatan perubahannya disertakan seperti di `data/bench-support/`.
2. **Ketentuan layanan penyedia model.** Dataset yang dibuat model berbayar, misalnya Magicoder-Evol (GPT-4), dan sampel yang ditulis asisten AI dapat terikat ketentuan layanan penyedianya. Ketentuan itu bisa membatasi pemakaian output untuk mengembangkan model yang bersaing.
   - Ini soal perjanjian, bukan hak cipta. Status hak cipta output AI di Indonesia belum jelas, karena pencipta didefinisikan sebagai orang (Pasal 1 angka 2 UU Hak Cipta).
   - Perjanjian tetap mengikat para pihak (Pasal 1338 KUHPerdata), dan pelanggarannya bisa digugat sebagai wanprestasi (Pasal 1243 KUHPerdata).
   - Cek ketentuan yang berlaku untuk jenis akun yang dipakai, terutama sebelum model didistribusikan atau dikomersialkan.
   - Data swa-distilasi dari Qwen sendiri lebih bersih dari sisi ini. Lisensi Qwen3.5 tetap perlu dicek di kartu modelnya.
3. **Data pribadi.** Sampel seperti validasi NIK hanya memakai data fiktif yang jelas fiktif. Data pribadi orang sungguhan tidak boleh masuk dataset, karena pemrosesannya membutuhkan dasar yang sah menurut UU No. 27 Tahun 2022 tentang Pelindungan Data Pribadi.
4. **Klaim skor.** Skor v4 hanya boleh dipublikasikan jika:
   - lolos dekontaminasi;
   - disertai kondisi ujinya (greedy, pass@1, versi EvalPlus, 4-bit);
   - dibandingkan dengan model dasar.

   Klaim yang melebihkan mutu berisiko melanggar Pasal 9 ayat (1) huruf a dan Pasal 10 huruf b UU No. 8 Tahun 1999 tentang Perlindungan Konsumen.

## 10. Langkah pertama

1. **Kamu:** jalankan Langkah 5 PROSEDUR (v3 vs model dasar), lalu kirim tabel perbandingannya.
2. **Saya:** mulai Fase 1, dimulai dari IndoPy dan dukungan MBPP+. Dengan alat ukur ini, setiap sampel berikutnya bisa dinilai dampaknya.
