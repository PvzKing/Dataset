# Dataset Instruct Bahasa Indonesia untuk Qwen3.5-4B

Dataset instruksi berbahasa Indonesia untuk fine-tuning **Qwen3.5-4B** dalam mode non-thinking. Dataset ini juga bisa dipakai untuk Qwen2.5-Coder-7B-Instruct. Fokus utamanya adalah **pembuatan website one-shot**: dari satu permintaan, model langsung menghasilkan satu file HTML lengkap yang berjalan di browser, lalu menjelaskan fiturnya.

## Isi

| Kelompok | Sampel | Rata-rata token | Topik |
|---|---|---|---|
| Website one-shot (`web_oneshot`) | 43 | ±5.000 | landing page, portfolio, dashboard, toko online, game (termasuk game 3D WebGL), kalkulator, sistem kasir, form, undangan, aplikasi web, alat bantu hukum, dan lainnya |
| Perbaikan bug website (`web_debug`) | 12 | ±3.650 | XSS, urutan operasi, timer di tab latar, `localStorage` rusak, overflow di HP, acak tidak aman, dan lainnya |
| Python terverifikasi (`py_*`, `tech-023`) | 22 | ±2.000 | fungsi dengan kasus tepi, program lengkap dengan tes, debug dari traceback, olah data CSV/log, menulis tes, multi-giliran (Python 3.8, kebutuhan berubah), review keamanan, Python untuk web (Flask, generator HTML) |
| Teknologi & pemrograman | 22 | ±700 | algoritma, struktur data, database, keamanan, sistem terdistribusi, Git, testing, AI |
| Matematika & logika | 15 | ±800 | kalkulus, pembuktian, probabilitas, statistik, aljabar, teka-teki logika, dan 4 sampel `matematika-*` dengan `<think>` |
| Hukum | 1 | belum diukur | sengketa utang piutang, wanprestasi dan penipuan |
| Sains | 10 | ±850 | fisika, biologi, kimia, ilmu bumi |
| **Total** | **125** | | ±329 ribu token, sampel terpanjang ±6.200 token |

Jumlah token dihitung dengan tokenizer Qwen2.5 setelah chat template diterapkan.

### Sampel website

| ID | Website | Yang diuji |
|---|---|---|
| web-001 | Landing page kedai kopi | menu bertab, status buka/tutup, menu mobile |
| web-002 | Portfolio developer | dark mode tersimpan, filter proyek, validasi form |
| web-003 | To-do list | tambah/edit/hapus, filter, `localStorage` |
| web-004 | Kalkulator tanpa `eval()` | urutan operasi, galat floating point, keyboard |
| web-005 | Dashboard admin penjualan | grafik SVG, tabel cari & urut, sidebar mobile |
| web-006 | Kuis pengetahuan Indonesia | timer per soal, skor, pembahasan |
| web-007 | Game Snake (canvas) | keyboard, swipe, jeda, skor tertinggi |
| web-008 | Tic-tac-toe vs komputer | minimax tidak pernah kalah |
| web-009 | Pomodoro timer | siklus otomatis, timer akurat di tab nonaktif |
| web-010 | Halaman pricing SaaS | toggle tahunan diskon 20%, FAQ |
| web-011 | Toko batik online | keranjang tersimpan, checkout WhatsApp |
| web-012 | Simulasi KPR | rumus anuitas, tabel angsuran |
| web-013 | Template artikel blog | progress baca, daftar isi otomatis |
| web-014 | Form pendaftaran multi-step | validasi per langkah, ringkasan |
| web-015 | Undangan pernikahan digital | nama tamu dari URL, countdown, file `.ics` |
| web-016 | Editor markdown | live preview, aman dari XSS |
| web-017 | Papan kanban | drag-and-drop, alternatif tombol untuk mobile |
| web-018 | Website kantor hukum | sesuai kode etik advokat dan UU PDP |
| web-019 | Password generator | `crypto.getRandomValues`, entropi |
| web-020 | Tes kecepatan mengetik | WPM, akurasi, highlight per huruf |
| web-021 | Kalkulator ilmiah | parser tanpa `eval()`, derajat/radian, riwayat yang bisa diklik |
| web-022 | Kalkulator patungan | menu dibagi rata, diskon proporsional, pembulatan tanpa selisih |
| web-023 | Kasir toko kelontong (POS) | stok, kode barang/scanner, kembalian, struk, rekap harian, opsi PPN |
| web-024 | Kasir kafe | dine-in/take away, PBJT dan service, tunai/QRIS/debit, antrean dapur |
| web-025 | Portofolio bergaya surat perjanjian | pasal dan ayat, filter karya, tanda tangan di kanvas untuk membuka kontak, mode gelap |
| web-026 | Game blok 3D "Dunia Kubus" (mirip Minecraft) | WebGL murni, dunia prosedural, tabrakan, gali dan pasang blok, kontrol sentuh |
| web-027 | Landing page agensi kreatif | filter portofolio, angka beranimasi saat di-scroll, testimoni bergilir berlabel contoh, validasi form |
| web-028 | Aplikasi cuaca (data simulasi) | combobox kota dengan keyboard, grafik SVG 24 jam, prakiraan 7 hari, °C/°F, WIB/WITA/WIT |
| web-029 | Pemutar musik Web Audio | lagu disusun dari tangga nada slendro/pelog, penjadwalan *lookahead*, visualizer, pintasan keyboard |
| web-030 | Situs resep Nusantara | cari bahan, takaran ikut porsi (pecahan dapur), favorit, timer di dalam `<dialog>` |
| web-031 | Perencana liburan | filter pulau dan anggaran, rencana tersimpan, estimasi biaya per orang |
| web-032 | Game 2048 bertema rempah | animasi geser/gabung, geser layar, undo, skor terbaik |
| web-033 | Klinik gigi + reservasi | wizard 4 langkah, jadwal dokter, validasi nomor WA, sesuai Permenkes 1787/2010 dan UU PDP |
| web-034 | Kalkulator pesangon | 18 alasan PHK menurut PP 35/2021, UPMK, UPH, kompensasi PKWT, PPh 21 final PP 68/2009 |
| web-035 | Habit tracker | streak, rekor, heatmap ala GitHub, tanggal lokal tanpa geser zona waktu |
| web-036 | Sudoku | generator dengan solusi tunggal, catatan pensil, petunjuk, undo |
| web-037 | Landing page SaaS absensi & payroll | tab ARIA, kalkulator penghematan, harga tahunan diskon 20%, contoh PPh 21 TER |
| web-038 | CV online | dwibahasa, mode gelap, filter pengalaman, siap cetak A4 |
| web-039 | Aplikasi menggambar | pena bertekanan, spidol, bentuk, ember cat, undo/redo, latar berpola, simpan PNG |
| web-040 | UI chat | balasan otomatis, indikator mengetik, centang dibaca, emoji, reaksi |
| web-041 | Game pecah bata | 4 level, bata berlapis, 4 power-up, suara Web Audio, kontrol sentuh |

## Format

`data/train.jsonl` berisi satu sampel per baris:

```json
{
  "id": "web-003",
  "category": "web_oneshot",
  "messages": [
    {"role": "user", "content": "bikin aplikasi to-do list dalam satu file html ..."},
    {"role": "assistant", "content": "Berikut aplikasi to-do list ...\n\n```html\n<!DOCTYPE html>...</html>\n```\n\n**Cek kebutuhan**\n- **Tambah** → form `#new-todo`.\n..."}
  ]
}
```

- `messages` memakai format percakapan standar (`role`/`content`) yang dipetakan ke chat template bawaan model (ChatML untuk keluarga Qwen).
- Sebagian besar sampel **tidak memakai system message**. Saat training, chat template model yang menentukan system prompt bawaannya (Qwen2.5 menyisipkan "You are Qwen..."). Kondisi ini sama dengan pemakaian model sehari-hari di Ollama, LM Studio, atau vLLM.
- **Qwen3.5 dilatih dalam mode non-thinking** (`enable_thinking=False`). Dataset ini tidak berisi jejak penalaran, jadi model diajari langsung menjawab. Notebook menempelkan jawaban tepat setelah prompt inferensi, termasuk blok `<think>` kosong jika template menambahkannya, supaya format training sama dengan saat dipakai.
- Dua sampel web (`web-012`, `web-019`) memakai system prompt khusus, misalnya batas maksimal 3 poin penjelasan, supaya model tetap patuh pada instruksi system.
- **Sampel perbaikan bug (`web_debug`)** berisi satu website dari `examples/web` yang sengaja diberi satu bug realistis. Di prompt, user menempelkan kode itu bersama pesan error atau gejalanya. Jawabannya menjelaskan penyebab, lalu memperbaiki hanya bagian yang rusak dengan blok `<<<<<<< SEARCH` / `=======` / `>>>>>>> REPLACE`, bukan menulis ulang seluruh file. Kode ber-bug hanya ada di pesan user, yang tidak ikut dilatih, jadi model tidak belajar menulis bug. Format ini juga bisa dipakai apa adanya oleh script cek-dan-perbaiki otomatis.
- Jawaban web terdiri dari: pengantar singkat, tepat satu blok ```` ```html ````, lalu bagian **Cek kebutuhan**. Bagian itu memetakan setiap permintaan di prompt ke kode yang mengerjakannya, dengan format `- **permintaan** → fungsi/elemen dan cara kerjanya`. Tujuannya melatih model memeriksa sendiri bahwa tidak ada fitur yang terlewat, kelemahan yang terlihat pada uji model hasil fine-tuning pertama. Setelahnya boleh ada catatan teknis dan cara menyesuaikan. `scripts/validate.py` menolak sampel web tanpa pemetaan ini.

## Standar kualitas sampel website

- Satu file HTML lengkap (HTML, CSS, JavaScript) tanpa library maupun request eksternal, sehingga langsung jalan saat dibuka.
- Setiap website diuji otomatis di Chromium (Playwright) pada lebar 1280px dan 375px. Kriterianya: tanpa error JavaScript, tanpa scroll horizontal (juga dicek di 320px), dan lolos skenario interaksi khusus. Contohnya, kalkulator harus menghasilkan `2 + 3 × 4 = 14`, minimax tic-tac-toe tidak pernah kalah, dan editor markdown kebal terhadap `<img onerror>` serta link `javascript:`.
- Responsif dan aksesibel: HTML semantik, label form, atribut `aria-*`, fokus keyboard yang terlihat, dan dukungan `prefers-reduced-motion`.
- Aman: data dari pengguna dipasang dengan `textContent`, tanpa `eval()`, dan akses `localStorage` dibungkus `try/catch`.
- Panjang maksimal sekitar 6.200 token, supaya semua sampel tetap ikut dilatih di T4 dengan `max_seq_len` 6144.
- Tanpa data karangan yang bisa menyesatkan: tidak ada testimoni fiktif yang tampil seperti ulasan asli, dan data contoh seperti alamat diberi tanda bahwa itu contoh.
- Konteks Indonesia yang akurat: format Rupiah dengan `Intl.NumberFormat('id-ID')`, nomor HP Indonesia, zona waktu WIB, dan untuk website kantor hukum penyesuaian dengan Kode Etik Advokat Indonesia, UU No. 18 Tahun 2003 tentang Advokat, serta UU No. 27 Tahun 2022 tentang Pelindungan Data Pribadi. Sampel kasir dan patungan mengikuti aturan pajak yang berlaku: PPN 12% × DPP nilai lain 11/12 untuk toko PKP (PMK 131 Tahun 2024), dan pajak restoran berupa PBJT paling tinggi 10% (UU No. 1 Tahun 2022), bukan PPN.

Contoh kode Python di sampel teknologi juga sudah dijalankan, sehingga output yang tertulis di jawaban sesuai dengan hasil eksekusi sebenarnya.

### Sampel Python terverifikasi

Sampel Python (`py-001`–`py-021` dan `tech-023`) tidak ditulis langsung di `train.jsonl`. Sumbernya ada di `data/python-src/<id>/`: teks tiap giliran, file kode, dan file data. `scripts/build_python_samples.py` lalu membangun sampelnya:

- **Kode** di jawaban diambil dari file sumbernya.
- **Output** diisi dari hasil menjalankan perintah sungguhan, termasuk traceback, hasil tes, dan untuk sampel kompatibilitas, Python 3.8.
- **Patch `SEARCH/REPLACE`** di sampel debug dibuktikan menghasilkan file perbaikan.

Jadi output yang tertulis di jawaban tidak mungkin dikarang. Gaya jawabannya mengikuti pelajaran dari uji HumanEval:
- aturan dan kasus tepi dipetakan sebelum menulis kode;
- kode ditutup dengan tes atau hasil menjalankan;
- program yang lebih besar ditutup dengan **Cek kebutuhan**.

Sampel Flask dan generator HTML juga diuji di Chromium. Rencana lengkapnya ada di [`docs/RENCANA_PYTHON.md`](docs/RENCANA_PYTHON.md).

```bash
python scripts/build_python_samples.py           # bangun ulang sampel Python ke data/train.jsonl (butuh Flask dan uv untuk Python 3.8)
python scripts/build_python_samples.py --check   # pastikan train.jsonl sama dengan hasil eksekusi ulang
python scripts/decontaminate.py                  # pastikan tidak ada tumpang tindih dengan soal uji
```

## Mode penalaran

Dataset ini sekarang punya dua jenis jawaban:

- **Tanpa penalaran** (sebagian besar): jawaban langsung, seperti sebelumnya.
- **Dengan penalaran**: jawaban diawali blok `<think>…</think>`, lalu baris kosong, lalu jawaban yang dibaca pengguna. Contoh:

  ```
  <think>
  Harga awal Rp250.000. Diskon 20% ... sisa 200.000. Diskon 10% dari 200.000 ... 180.000.
  </think>

  Harga akhirnya **Rp180.000**. ...
  ```

Pemisahan dibuat di `data/kelompok/`:

- `penalaran.jsonl`: 6 sampel dengan `<think>` (`matematika-001` sampai `matematika-004`, `web-042`, dan `web-043`).
- `tanpa-penalaran.jsonl`: 119 sampel lainnya.

`data/train.jsonl` tetap berisi semua 125 sampel, sehingga pengaturan training dan `mix_general.py` tidak berubah.

Catatan untuk training:
- `scripts/train_unsloth.py` merender jawaban yang diawali `<think>` dalam mode thinking (`enable_thinking=True`). Jawaban lainnya tetap memakai blok kosong seperti sebelumnya.
- Jalur LLaMA-Factory (`dataset_info.json` dan file yaml) memakai `train.jsonl` penuh, sehingga 6 sampel ber-`<think>` ikut dilatih lewat template `qwen3_5_nothink`. Cara template itu menangani teks `<think>` di jawaban belum diuji. Sampai diuji, gunakan `train_unsloth.py` untuk data dengan penalaran.
- Untuk `qwen2.5-coder-7b` (`train_unsloth.py`), sampel `<think>` dilatih sebagai teks biasa, karena template-nya tidak punya opsi thinking.
- Enam sampel belum cukup untuk membuat model belajar mode thinking secara andal. Kelompok `penalaran.jsonl` perlu diperbesar dulu.
- Angka token di tabel *Isi* belum dihitung ulang setelah penambahan sampel baru.

## Mencampur dengan dataset umum

Melatih model hanya dengan 125 sampel berisiko membuat model "terlalu fokus", misalnya selalu menjawab dengan file HTML walaupun pertanyaannya bukan soal website. Selain itu, kemampuan umumnya bisa menurun. Karena itu, config training memakai data campuran yang dibuat oleh `scripts/mix_general.py`:

| Sumber | Jumlah bawaan | Isi |
|---|---|---|
| Dataset ini (`data/train.jsonl`) | 125 | semua sampel, tanpa dikurangi |
| [`CohereForAI/aya_dataset`](https://huggingface.co/datasets/CohereForAI/aya_dataset), bagian bahasa Indonesia | 600 | tanya-jawab umum yang ditulis manusia |
| [`ise-uiuc/Magicoder-Evol-Instruct-110K`](https://huggingface.co/datasets/ise-uiuc/Magicoder-Evol-Instruct-110K) | 200 | instruksi pemrograman (bahasa Inggris) |
| [`HuggingFaceH4/ultrachat_200k`](https://huggingface.co/datasets/HuggingFaceH4/ultrachat_200k), split `train_sft` | 100 | percakapan umum multi-turn (bahasa Inggris) |

```bash
pip install datasets
python scripts/mix_general.py                              # menulis data/train_mix.jsonl
python scripts/mix_general.py --aya-id 800 --code 300 --chat 150 --seed 7   # ubah komposisi
python scripts/validate.py data/train_mix.jsonl
```

Hal-hal yang dilakukan script:

- **Streaming:** data diambil secara streaming, jadi dataset besar tidak diunduh penuh. Pengambilannya acak, dengan `--seed` agar hasilnya bisa diulang.
- **Filter:**
  - Aya hanya diambil bagian bahasa Indonesianya.
  - Jawaban yang terlalu pendek (di bawah 15 karakter) dibuang.
  - Sampel yang melebihi sekitar 7.000 token dibuang, supaya tetap di bawah `cutoff_len`.
  - Percakapan dengan urutan giliran yang rusak dibuang.
  - Jawaban yang menyebut identitas model lain ("ChatGPT", "OpenAI", "sebagai model bahasa AI") dibuang, supaya tidak bertentangan dengan identitas Qwen.
- **Deduplikasi:** prompt yang sama, termasuk yang sudah ada di dataset ini, hanya diambil sekali.
- **Ringkasan:** jumlah sampel dan perkiraan porsi token setiap sumber dicetak di akhir. Sampel web di dataset ini panjang (±5.000 token), jadi meskipun jumlah sampelnya kecil, porsi tokennya tetap besar. Targetkan porsi dataset sendiri sekitar 20–30% dari total token, dan ubah jumlah per sumber jika perlu.
- **Skema dicek saat dijalankan:** jika pengelola dataset sumber mengubah nama kolom, script berhenti dan menampilkan kolom yang tersedia. Sesuaikan entri `SOURCES` di dalam script.

`data/train_mix.jsonl` tidak di-commit (ada di `.gitignore`) karena isinya data pihak ketiga. Buat ulang file itu di mesin training.

### Catatan lisensi dan hukum

- **Aya Dataset** ditulis oleh kontributor manusia, bukan dihasilkan model, dan dirilis dengan lisensi terbuka. Lisensi terbuka seperti Apache 2.0 umumnya mewajibkan atribusi dan menyertakan teks lisensi saat data didistribusikan ulang.
- **Magicoder-Evol-Instruct** dan **UltraChat** dibuat dengan bantuan model OpenAI. Syarat penggunaan OpenAI melarang penggunanya memakai output untuk mengembangkan model yang bersaing dengan OpenAI. Apakah ketentuan kontraktual itu juga mengikat pihak ketiga yang hanya mengunduh datasetnya masih diperdebatkan. Untuk eksperimen pribadi atau riset risikonya kecil, tetapi jika model hasil fine-tuning akan dipakai atau dijual secara komersial, pertimbangkan untuk mengganti kedua sumber ini dengan data yang ditulis manusia atau berlisensi jelas.
- **Model dasar** Qwen3.5-4B dan Qwen2.5-Coder-7B-Instruct berlisensi Apache 2.0. Adapter atau model gabungan hasil fine-tuning boleh didistribusikan dan dipakai secara komersial, dengan syarat menyertakan salinan lisensi, mempertahankan pemberitahuan hak cipta, dan menandai bahwa model telah diubah (Pasal 4 Apache License 2.0). Tidak semua model Qwen berlisensi Apache 2.0: misalnya Qwen2.5-Coder-3B memakai lisensi riset non-komersial. Periksa lisensi setiap model sebelum mengganti model dasar.
- Periksa kartu dataset (dataset card) masing-masing sumber untuk lisensi terbaru sebelum mendistribusikan dataset campuran atau model hasil training.

## Kelompok `bench-support` (HumanEval dan MBPP)

Folder `data/bench-support/` berisi sampel latihan dari benchmark kode, terpisah dari dataset `own`. Semuanya memakai format prompt instruct EvalPlus:

| File | Sampel | Sumber |
|---|---|---|
| `humaneval.jsonl` | 164 | HumanEval, solusi dari HumanEval+ (satu soal ditulis ulang) |
| `mbppplus.jsonl` | 378 | MBPP+ v0.2.0, solusi kanonis EvalPlus |
| `mbpp-sisa.jsonl` | 589 | soal MBPP asli yang tidak masuk MBPP+ |

Setiap solusi HumanEval diverifikasi oleh `scripts/build_bench_support.py` dengan dua cara: tes resmi HumanEval, dan pemeriksaan silang dengan solusi asli HumanEval pada 111 ribu input tambahan HumanEval+. Lewat pemeriksaan ini ditemukan 15 solusi asli HumanEval yang keliru dan satu soal yang kedua solusi referensinya gagal. Solusi MBPP+ dan MBPP harus lolos assert resmi MBPP. Rinciannya ada di `data/bench-support/README.md`.

Ada tiga cara memakai kelompok ini:

- **Dicampur dengan `own` dalam satu run dari model dasar (`--dataset own+bench`, dipakai V5).** Panduannya ada di [`docs/PANDUAN_V5_A100.md`](docs/PANDUAN_V5_A100.md). Adapter epoch 2 dan 3 disimpan, lalu yang dipakai dipilih dari uji yang bersih: MBPP+, IndoPy-dev, dan Web-eval.
- **Seluruh EvalPlus dan MBPP dicampur dengan `own`, 10 epoch (`--dataset own+evalplus`, dipakai V6).** Panduannya ada di [`docs/PANDUAN_V6_A100.md`](docs/PANDUAN_V6_A100.md). Kontaminasinya disengaja: skor HumanEval+ dan MBPP+ V6 tidak bersih, jadi epoch dipilih hanya dari IndoPy-dev dan Web-eval.
- **Tidak dipakai sama sekali (V7).** V6 menghafal sampel latihan dan kalah dari model dasar di permintaan baru, jadi V7 melatih `own` + jawaban model dasar sendiri yang lolos pemeriksaan otomatis (lihat bagian V7 di bawah). Keempat uji, termasuk HumanEval+ dan MBPP+, kembali bersih.
- **Dilatih sendiri, tanpa `own`**, sebagai training lanjutan di atas adapter yang sudah dilatih dengan `own` (misalnya v3). Cara ini dipakai percobaan bench-lanjut, yang skornya turun (lihat `data/bench-support/README.md`):

```bash
python scripts/train_unsloth.py train --dataset bench \
  --init-adapter /content/drive/MyDrive/finetune-id/v3/qwen3.5-4b-own-4bit/lora-adapter
python scripts/build_bench_support.py      # membuat ulang dan memverifikasi data/bench-support/humaneval.jsonl
```

Dengan 164 sampel dan 3 epoch, training di T4 diperkirakan memakan ±19–27 menit. Angka ini dikalibrasi dari run v3 dan dicetak script di baris `perkiraan T4`. Hasilnya disimpan di folder `qwen3.5-4b-bench-4bit-lanjut`, jadi adapter v3 tidak berubah. Website uji tetap dibuat setelah training. Bandingkan website itu dengan hasil v3 untuk memastikan kemampuan membuat website tidak menurun, karena data lanjutan ini hanya berisi soal Python.

Dua hal yang perlu diingat:
- **Skor HumanEval tidak lagi bersih.** Model yang dilatih dengan kelompok ini sudah melihat soal dan jawabannya.
- **Lisensi wajib disertakan.** HumanEval berlisensi MIT (OpenAI) dan HumanEval+ berlisensi Apache 2.0 (EvalPlus). Jika data atau model didistribusikan, sertakan kedua teks lisensinya yang ada di folder tersebut.

## Pilihan data: `own` atau `mix`

- **`own`**: hanya `data/train.jsonl`, 125 sampel, 3 epoch, ±980 ribu token diproses.
- **`mix`**: dataset ini ditambah ±900 sampel umum dari `scripts/mix_general.py`, 2 epoch, ±1 juta token dilatih.

Mulailah dengan **`own`**, lalu beralih ke `mix` jika hasilnya menunjukkan gejala lupa kemampuan umum.

- **Alasan memulai dengan `own`:**
  - Qwen3.5-4B sudah dilatih dengan data umum dalam jumlah sangat besar. 125 sampel dengan LoRA rank 16 hanya mengubah sedikit bobot, jadi risiko model melupakan kemampuan umumnya kecil.
  - Sekitar 77% token di dataset ini adalah sampel website, baik one-shot maupun perbaikan bug, dan 13% sampel Python terverifikasi. Keduanya memang kemampuan utama yang ingin diajarkan.
  - Training di T4 butuh ±30–90 menit, tidak berjam-jam, jadi cepat untuk iterasi.
- **Kapan beralih ke `mix`.** Jika setelah training dengan `own` muncul salah satu gejala berikut:
  - Setiap pertanyaan dijawab dengan HTML.
  - Pertanyaan umum dijawab dengan buruk.
  - Bahasa jawaban menjadi aneh.
- **Risiko `mix`.** Sebagian data umumnya (Magicoder dan UltraChat) dibuat dengan model OpenAI. Lihat catatan hukum di atas jika model akan dipakai secara komersial. Jalankan `mix_general.py --code 0 --chat 0` untuk memakai Aya saja, yang ditulis manusia.

## Training di Google Colab

**Panduan langkah demi langkah: [`docs/PANDUAN_TRAINING.md`](docs/PANDUAN_TRAINING.md).** Untuk GPU A100 dengan data own + HumanEval, checkpoint dan hasil di Google Drive, serta model bernama V5, pakai [`docs/PANDUAN_V5_A100.md`](docs/PANDUAN_V5_A100.md) atau [notebook-nya](notebooks/v5_a100_colab.ipynb). Untuk V6 (ditambah MBPP+ dan MBPP, 10 epoch, skor benchmark sengaja terkontaminasi), pakai [`docs/PANDUAN_V6_A100.md`](docs/PANDUAN_V6_A100.md) atau [notebook-nya](notebooks/v6_a100_colab.ipynb). Untuk V7, perbaikan V6 yang mencegah hafalan, pakai [`docs/PANDUAN_V7_A100.md`](docs/PANDUAN_V7_A100.md) atau [notebook-nya](notebooks/v7_a100_colab.ipynb).

### V7: data sulingan model dasar dan gerbang melawan model dasar

V6 (Codexia2) dilatih 10 epoch dengan 1.131 jawaban benchmark pendek. Hasilnya, epoch 9 menyalin sampel web-003 kata per kata, tetapi gagal total di permintaan baru (antrean puskesmas). V7 mengubah empat hal:

1. **Tanpa jawaban benchmark**, jadi IndoPy-dev, Web-eval, MBPP+, dan HumanEval+ semuanya bersih.
2. **Data sulingan** dari `scripts/sulingan.py`. Model dasar menjawab 589 soal MBPP di luar MBPP+ (dibungkus permintaan berbahasa Indonesia) dan 40 prompt website baru (`data/sulingan/prompt-web.jsonl`) beberapa kali. Hanya jawaban yang lolos pemeriksaan otomatis yang dipakai: assert resmi MBPP untuk Python; untuk website, Chromium tanpa error saat semua input diisi dan tombol diklik, halaman berubah setelah dipakai, responsif di 375 px, localStorage jika diminta, dan bagian **Cek kebutuhan**. Instruksi gaya hanya ada di system prompt saat membuat jawaban dan tidak ikut dilatih. Sampel yang punya 13-gram sama dengan soal uji dibuang.
3. **Dosis kecil**: 2 epoch, lr 1e-4, batch efektif 8.
4. **Gerbang**: adapter dipakai hanya jika rata-rata keempat uji bersih minimal sama dengan model dasar. Kalau tidak, laporan menyarankan model dasar dan ekspor dilewati.

```bash
python scripts/sulingan.py python --out /tmp/sulingan --demo --limit 20   # uji alur tanpa GPU
python scripts/sulingan.py gabung --out /tmp/sulingan --demo
python tests/simulasi_v7/cek.py     # simulasi sel panduan V7 (menulis ke /content: container sekali pakai saja)
```

Seluruh proses training ada di satu file mandiri, [`scripts/train_unsloth.py`](scripts/train_unsloth.py), dengan pengaturan di blok `CONFIG`. File ini tidak butuh clone repo: jika `train.jsonl` tidak ditemukan, file itu diunduh dari repo publik ini. Ada dua cara memakainya, dan keduanya tidak perlu menghubungkan Colab ke GitHub:

- **Cara 1, upload notebook** [`notebooks/train_colab.ipynb`](notebooks/train_colab.ipynb) ke Colab (*File → Upload notebook*). Notebook menyimpan script ke `/content/train_unsloth.py`, lalu menyediakan dua mode:
  - **Mode A: jalankan sendiri.** Satu sel menjalankan training, menyimpan adapter, dan membuat dua website uji.
  - **Mode B: Claude yang mengontrol lewat terminal.** Claude Code berjalan di terminal VM Colab. Claude menjalankan training di latar belakang, memantau `status.json` dan log, menangani error umum, lalu melaporkan hasilnya. Aturan kerjanya ([`docs/RUNBOOK_CLAUDE.md`](docs/RUNBOOK_CLAUDE.md)) disalin ke `/content/CLAUDE.md`.
- **Cara 2, dua sel:** sel 1 berisi `!pip install --upgrade unsloth`, dan sel 2 berisi seluruh isi `train_unsloth.py`.

Notebook dibangun dari script dan runbook dengan `python scripts/build_notebook.py`. Jalankan ulang perintah itu setiap kali salah satu file sumbernya diubah.

Script ini memakai [Unsloth](https://github.com/unslothai/unsloth):

- **Model:** `"model": "qwen3.5-4b"` (bawaan) melatih LoRA 16-bit, karena Unsloth tidak menyarankan QLoRA 4-bit untuk Qwen3.5. `"model": "qwen2.5-coder-7b"` melatih QLoRA 4-bit sebagai pembanding. Hasil setiap model dan pilihan data disimpan di folder Drive terpisah.
- **Presisi di T4:** T4 tidak mendukung bf16, dan Qwen3.5 menghasilkan NaN pada fp16. Unsloth otomatis melatih dalam float32, yang benar tetapi lebih lambat. GPU L4 (Colab berbayar) mendukung bf16 dan jauh lebih cepat.
- **Sampel terlalu panjang dibuang, bukan dipotong.** Jika `max_seq_len` diturunkan (misalnya ke 6144 saat kehabisan memori), sampel yang terlalu panjang dibuang supaya model tidak belajar dari HTML yang terpotong. Script menampilkan sampel mana saja yang dibuang.
- **Loss hanya pada jawaban assistant**, memakai `train_on_responses_only`. Script mencetak contoh token yang dilatih untuk memastikan masking-nya benar.
- **Tahan sesi putus:** data campuran dan checkpoint disimpan ke Google Drive setiap 10 step. Jika sesi putus, jalankan ulang instalasi dan training yang sama, dan training dilanjutkan dari checkpoint terakhir.
- **Mudah dipantau:** `status.json` di folder hasil selalu berisi tahap, step, loss, dan ETA terbaru. Saat error, file ini juga berisi saran perbaikan.
- **Hasil:**
  - adapter LoRA di Drive;
  - dua website yang dibuat model dari prompt uji yang sama untuk setiap model, supaya mudah dibandingkan;
  - opsional, file GGUF q4_k_m untuk Ollama atau llama.cpp.

Perkiraan waktu training Qwen3.5-4B, belum termasuk instalasi dan unduh model (±10–15 menit):

| GPU | `own` (±980 ribu token) | `mix` (±1 juta token) |
|---|---|---|
| T4 gratis (QLoRA 4-bit, float32, konteks 6144) | ±60–70 menit (v3 dengan 78 sampel terukur 42,7 menit) | ±1,5–3 jam |
| L4 (bf16) | ±10–20 menit | ±40–80 menit |

Angka T4 untuk `own` diukur langsung di Colab. Angka lainnya masih perkiraan, dan ETA di progress bar menunjukkan waktu yang sebenarnya. Di T4, script otomatis memakai QLoRA 4-bit dan `max_seq_len` 6144, karena 16-bit maupun 4-bit dengan konteks 8192 kehabisan memori di sana. Semua sampel dijaga di bawah batas itu, jadi tidak ada yang terbuang. Colab gratis membatasi lama sesi dan ketersediaan GPU, jadi data `mix` di T4 kemungkinan butuh lebih dari satu sesi.

## Training dengan LLaMA-Factory

Cara ini untuk GPU yang mendukung bf16 (L4, A10, A100, RTX 30xx/40xx). LLaMA-Factory tidak punya jalur float32 otomatis seperti Unsloth, jadi untuk T4 gunakan notebook di atas.

1. Pasang [LLaMA-Factory](https://github.com/hiyouga/LLaMA-Factory):
   ```bash
   git clone --depth 1 https://github.com/hiyouga/LLaMA-Factory.git
   cd LLaMA-Factory && pip install -e ".[torch,metrics]"
   ```
2. Opsional, buat data campuran:
   ```bash
   python scripts/mix_general.py
   ```
3. Dari root repo ini, jalankan:
   ```bash
   llamafactory-cli train train/qwen3.5-4b-lora.yaml
   ```
   Dataset sudah terdaftar di `data/dataset_info.json` sebagai `instruct_id` (hanya dataset ini) dan `instruct_id_mix` (campuran).
4. Coba hasilnya:
   ```bash
   llamafactory-cli chat --model_name_or_path Qwen/Qwen3.5-4B \
     --adapter_name_or_path saves/qwen3.5-4b-id/lora/sft \
     --template qwen3_5_nothink --finetuning_type lora
   ```

Ringkasan konfigurasi di `train/qwen3.5-4b-lora.yaml`:

- LoRA rank 16 di semua layer linear, dengan vision tower dibekukan.
- Learning rate `1e-4`, 3 epoch untuk `instruct_id`, scheduler cosine, dan batch efektif 8.
- `template: qwen3_5_nothink` dan `cutoff_len: 8192`, sehingga tidak ada sampel yang terpotong.
- Loss hanya dihitung pada jawaban assistant. Ini perilaku bawaan LLaMA-Factory.

Template `qwen3_5_nothink` di LLaMA-Factory tidak menyisipkan blok `<think>` kosong. Karena itu, pakai template yang sama saat inferensi (`llamafactory-cli chat` atau API LLaMA-Factory). Notebook Colab memakai chat template resmi model, sehingga cocok untuk transformers, vLLM, dan Ollama.

Konfigurasi lama untuk Qwen2.5-Coder-7B-Instruct masih tersedia di `train/qwen2.5-coder-7b-lora.yaml` (`template: qwen`, butuh ±24 GB VRAM atau `quantization_bit: 4`).

Framework lain seperti TRL (`SFTTrainer`) dan Axolotl (`type: chat_template`) juga bisa membaca format `messages` ini. Pastikan memakai chat template bawaan tokenizer model, dan loss hanya dihitung pada bagian assistant.

## Validasi

```bash
python scripts/validate.py
# opsional, hitung token dengan tokenizer asli (butuh transformers):
python scripts/validate.py --tokenizer Qwen/Qwen3.5-4B --max-len 8192
```

Script ini memeriksa struktur JSON, urutan role, ID dan prompt duplikat, kelengkapan blok HTML pada sampel web, serta panjang token terhadap `cutoff_len`.

## Catatan penting

- **Ukuran dataset kecil.** Fine-tuning dengan 125 sampel terutama membentuk gaya dan format jawaban, misalnya kebiasaan menghasilkan satu file HTML lengkap dengan penjelasan berbahasa Indonesia. Pengetahuan baru tidak banyak bertambah. Karena itu, config bawaan memakai data campuran dengan dataset umum (lihat bagian *Mencampur dengan dataset umum*).
- **Hindari overfitting.** Pantau training loss. Dengan data sekecil ini, terlalu banyak epoch membuat model sekadar menghafal jawaban.

## Melihat dan menguji website

Ke-41 website juga tersedia sebagai file terpisah di `examples/web/`, isinya identik dengan yang ada di `data/train.jsonl`. Buka saja file `.html`-nya di browser untuk melihat hasilnya.

Untuk menjalankan ulang tes otomatis (Chromium, desktop 1280px dan HP 375px):

```bash
cd tests
npm install
npx playwright install chromium
node test_web.mjs              # semua website
node test_web.mjs 04-          # satu website saja
```

Tes gagal jika ada error JavaScript, request ke luar, scroll horizontal, atau skenario interaksi di `tests/interactions.mjs` yang tidak terpenuhi. Screenshot disimpan di `tests/screenshots/`.

### Koleksi tambahan: `examples/web-pilihan/`

Folder ini berisi 20 website single-file untuk etalase. Tidak ada CDN atau gambar dari luar. Satu-satunya sumber luar adalah Google Fonts; tanpa internet, website tetap berjalan dengan font sistem.

**Yang masuk dataset.** 15 website sudah dijadikan sampel `web-027`–`web-041`. Versi datanya ada di `examples/web/27-`…`41-`, dan berbeda dari versi etalase dalam tiga hal:
- Google Fonts dibuang, karena sampel latihan tidak boleh membuat request eksternal.
- Website yang terlalu panjang dipadatkan sampai ±5.500 token HTML, supaya tetap muat di batas 6144 token T4.
- Bagian khusus pratinjau iframe dihapus.

Perubahan pada file di folder ini **tidak** otomatis masuk dataset.

**Yang sengaja tidak dimasukkan.** Lima website tidak dijadikan sampel karena jenis tugasnya sama dengan soal Web-eval, sehingga skor Web-eval tidak lagi bersih:

| Website etalase | Soal Web-eval yang tumpang tindih |
|---|---|
| `p06` | `pengeluaran` |
| `p07` | `memori` |
| `p13` | `galeri` |
| `p18` | `seminar` |
| `p19` | `konversi-satuan` |

| File | Jenis | Fitur utama |
|---|---|---|
| `p01-agensi-kreatif` | Landing page agensi | filter portofolio, animasi angka, testimoni bergilir, validasi form |
| `p02-cuaca` | Aplikasi cuaca | cari kota (keyboard), grafik 24 jam SVG, prakiraan 7 hari, °C/°F |
| `p03-pemutar-musik` | Pemutar musik | lagu disintesis Web Audio, visualizer, acak/ulang, pintasan keyboard |
| `p04-resep-nusantara` | Situs resep | cari bahan, takaran ikut jumlah porsi, favorit, timer memasak |
| `p05-wisata-nusantara` | Perencana liburan | filter pulau & anggaran, rencana perjalanan, estimasi biaya |
| `p06-catatan-keuangan` | Pencatat keuangan | grafik donat, batas anggaran, per bulan, ekspor CSV, mode gelap |
| `p07-memori-satwa` | Game kartu memori | 3 tingkat, rekor, fakta satwa endemik |
| `p08-2048` | Game 2048 | animasi ubin, geser layar, urungkan, skor terbaik |
| `p09-klinik-gigi` | Situs klinik + reservasi | wizard 4 langkah, jadwal dokter, validasi nomor WA |
| `p10-kalkulator-pesangon` | Kalkulator hukum | pesangon/UPMK/UPH per alasan PHK (PP 35/2021), kompensasi PKWT, PPh 21 final |
| `p11-pelacak-kebiasaan` | Habit tracker | streak, heatmap hingga setahun, progres harian |
| `p12-sudoku` | Game sudoku | generator dengan solusi tunggal, catatan, petunjuk, urungkan |
| `p13-galeri-seni` | Galeri | karya generatif canvas, lightbox keyboard/geser, unduh PNG |
| `p14-landing-saas` | Landing page SaaS | tab fitur, kalkulator penghematan, harga bulanan/tahunan |
| `p15-cv-online` | CV / resume | dwibahasa, mode gelap, siap cetak A4 |
| `p16-papan-gambar` | Aplikasi gambar | pena, spidol, bentuk, ember cat, undo/redo, simpan PNG |
| `p17-aplikasi-chat` | UI chat | balasan otomatis, indikator mengetik, emoji, reaksi |
| `p18-konferensi-teknologi` | Situs acara | hitung mundur, agenda pribadi, deteksi bentrok, tiket + promo |
| `p19-konverter-satuan` | Konverter | 8 kategori termasuk tumbak/bata/ubin, dua arah, riwayat |
| `p20-pecah-bata` | Game arkade | 4 level, power-up, efek suara, kontrol sentuh |

Kalkulator pesangon hanya memberi estimasi hak minimal, bukan nasihat hukum. Dasar hukumnya dicantumkan per baris perhitungan.

Tesnya memakai runner yang sama, dengan skenario interaksi di `tests/interactions_pilihan.mjs`:

```bash
cd tests
WEB_DIR=web-pilihan node test_web.mjs        # ke-20 website
WEB_DIR=web-pilihan node test_web.mjs p10    # satu website
```

Sampel perbaikan bug diuji dengan `node test_debug.mjs`. Untuk setiap sampel, tes memeriksa tiga hal:
1. Blok SEARCH/REPLACE di jawaban, bila diterapkan ke kode di prompt, menghasilkan website asli di `examples/web` persis sama.
2. Versi ber-bug benar-benar gagal di browser.
3. Pemeriksaan khusus bug tersebut lolos di versi asli.

## Agen coding (`scripts/agent_gradio.py`)

`scripts/agent_gradio.py` adalah tampilan Gradio bergaya Claude Code untuk model hasil fine-tuning (bawaan: adapter terbaru `qwen3.5-4b-bench-4bit-lanjut`, atau v3 jika belum ada). Model tidak hanya menjawab, tetapi bekerja dalam loop:

1. **Write.** Model menulis `index.html`. Jika jawaban terpotong di batas token, agen menyambungnya otomatis dari titik terakhir (prefill), bukan mengulang dari awal.
2. **Bash.** Halaman dibuka di Chromium headless pada lebar 1280px dan 375px, lalu setiap tombol diklik. Error JavaScript, `console.error`, dan scroll horizontal dicatat beserta lokasinya, misalnya `index.html:190:43`.
3. **Update.** Kode dan daftar error dikirim ke model dengan format yang sama seperti sampel `web_debug`. Blok SEARCH/REPLACE di jawabannya diterapkan ke file dan ditampilkan sebagai diff, lalu agen kembali ke langkah 2, maksimal 3 putaran.

Panel kanan berisi:
- editor kode bernomor baris yang bisa diubah langsung;
- pratinjau website;
- daftar masalah;
- tombol Uji, Perbaiki, Undo, Stop, dan Unduh.

Jika editor sudah berisi kode, pesan biasa diperlakukan sebagai permintaan perubahan pada file itu. Perintah yang tersedia: `/baru`, `/cek`, `/perbaiki [keluhan]`, `/undo`, `/reset`, `/bantuan`.

```python
# Colab, GPU T4
!pip install --upgrade unsloth "gradio>=6.30,<7" playwright
!playwright install --with-deps chromium
from google.colab import drive; drive.mount("/content/drive")
BR = "https://raw.githubusercontent.com/PvzKing/Dataset/main/scripts"
!wget -q -O /content/agent_gradio.py {BR}/agent_gradio.py
!wget -q -O /content/chat_gradio.py {BR}/chat_gradio.py
%run /content/agent_gradio.py            # --adapter <folder> untuk adapter lain, --demo tanpa GPU
```

Batasan yang perlu diketahui:
- **Uji browser hanya menangkap error yang terlihat mesin.** Contohnya error JavaScript, error setelah tombol diklik, dan tampilan yang meluber. Bug logika seperti hasil hitung yang salah tidak terdeteksi, jadi jelaskan lewat `/perbaiki <keluhan>`.
- **Kode, daftar error, dan jawaban harus muat di konteks** (bawaan 8.192 token). File di atas ±6.000 token sebaiknya diperbaiki manual.
- **Model 4B bisa gagal menyalin teks SEARCH persis.**
  - Agen sudah mencoba pencocokan yang mengabaikan indentasi.
  - Blok yang tetap tidak cocok dilaporkan dan dilewati, tidak diterapkan sembarangan.
  - Setiap versi disimpan di `<workdir>/.versi/`, dan perubahan bisa dibatalkan dengan `/undo`.

## Codexia Studio (`scripts/codexia_studio.py`)

Tampilan Gradio bergaya Claude Code untuk memakai **Codexia2** (hasil `docs/PANDUAN_V6_A100.md`) tanpa kuantisasi. Model dimuat bf16, atau float32 dengan `--dtype float32`; tidak pernah 4-bit atau 8-bit. Karena itu butuh GPU dengan bf16 asli seperti A100, L4, atau H100.

- **Editor Monaco** (editor VS Code). Kode baru dari model mengalir langsung ke editor saat ditulis.
- **Edit beberapa baris, tanpa menulis ulang.** Jika editor sudah berisi kode, permintaan dikirim dengan format sampel debug di data training: keluhan, lalu kode lengkap, lalu output atau error. Jawaban model diawali blok `SEARCH/REPLACE`, dan setiap blok diterapkan ke baris yang sama. Baris yang berubah disorot di editor dan tampil sebagai diff di transkrip. Blok yang tidak cocok dikirim balik ke model satu kali.
- **Jalankan dan perbaiki.** Python, JavaScript (jika ada `node`), dan Bash dijalankan di subprocess dengan batas waktu. HTML tampil di tab Pratinjau. `/perbaiki` tanpa keterangan mengirim traceback terakhir ke model, lalu menjalankan ulang file untuk membuktikan perbaikannya.
- **Pengaturan lengkap:** sampling terpisah untuk menulis dan mengedit, mode patch atau bebas, mode berpikir, seed, batas konteks 16.384 token, undo, dan riwayat versi di folder kerja.

```bash
!pip install -q --upgrade unsloth "gradio>=5.40,<7"
%run /content/codexia_studio.py                      # adapter Codexia2 final dari Google Drive
%run /content/codexia_studio.py --adapter .../epoch-5/qwen3.5-4b-Codexia2-lora   # epoch lain
%run /content/codexia_studio.py --adapter none       # model dasar Qwen3.5-4B tanpa adapter, untuk pembanding
%run /content/codexia_studio.py --demo               # coba tampilan tanpa GPU
```

Monaco diunduh sekali dari registry npm lalu disajikan oleh Gradio. Jika gagal, Monaco dimuat dari CDN jsDelivr, dan jika itu juga gagal, editor diganti kotak teks biasa. Kode yang dijalankan adalah kode tulisan model, jadi jalankan di runtime Colab, bukan di komputer yang berisi data penting.

## Menulis isi `<think>` sendiri (`scripts/editor_think.py`)

Isi tag `<think>` untuk sampel dataset own ditulis manusia lewat editor ini. **Cara termudah:** buka [notebook editor di Colab](https://colab.research.google.com/github/PvzKing/Dataset/blob/main/notebooks/editor_think_colab.ipynb), isi nama, email, dan sandi, lalu jalankan satu sel. Langkah membuat token GitHub ada di notebook itu. Editor tidak membuat atau menyarankan isi apa pun.

- **Isi editor.** Setiap sampel ditampilkan dengan prompt dan jawabannya, ditambah kotak untuk menulis isi `<think>`. Sampel multi-giliran punya satu kotak per jawaban.
- **Saat Simpan:**
  1. Teks ditulis ke `data/think/<id>-<n>.md`, yaitu isi `<think>` untuk jawaban assistant ke-n.
  2. `scripts/think_tags.py` memasangnya ke `data/train.jsonl` sebagai `<think>\n...\n</think>\n\n` di awal jawaban.
  3. `scripts/validate.py` dijalankan.
  4. Jika kotak **Commit & push** dicentang, perubahan di-commit lalu di-push ke GitHub.
- **Menghapus.** Kosongkan teks lalu Simpan untuk menghapus `<think>` dari sampel itu.
- **Aman saat build ulang.** `build_python_samples.py` ikut memasang isi `data/think/`, jadi membangun ulang sampel Python tidak menghapusnya.

Di Colab (CPU saja cukup), simpan token GitHub fine-grained dengan izin *Contents: Read and write* untuk repo ini di **Secrets** dengan nama `GITHUB_TOKEN`, lalu jalankan:

```python
import os
from google.colab import userdata
os.environ["GITHUB_TOKEN"] = userdata.get("GITHUB_TOKEN")
!git clone -q https://github.com/PvzKing/Dataset.git /content/Dataset
!pip install -q "gradio>=5"
!git -C /content/Dataset config user.name "Nama Anda" && git -C /content/Dataset config user.email "email@contoh.com"
%run /content/Dataset/scripts/editor_think.py --share --auth penulis:ganti-sandi
```

Di laptop: `python scripts/editor_think.py` dari clone repo, lalu buka `http://127.0.0.1:7861`. Push ke `main` adalah bawaan; pakai `--branch <nama>` untuk cabang lain, atau `--no-push` untuk menyimpan saja. Token tidak disimpan ke git config dan tidak ditampilkan di layar.

**Dampaknya ke training.**
- Sampel yang berisi `<think>` dilatih dengan isi itu: blok `<think>` kosong dari template mode non-thinking dibuang, jadi model belajar menulis penalarannya sendiri sebelum menjawab.
- Saat dipakai dengan `enable_thinking=False`, template menyisipkan `<think>` kosong, sehingga model langsung menjawab. Untuk memakai penalaran yang dipelajari, jalankan inferensi dengan `enable_thinking=True`.
- Sampel tanpa `<think>` tetap dilatih seperti sebelumnya.

## Menambah sampel

1. Tambahkan satu baris JSON ke `data/train.jsonl` dengan `id` unik. Untuk sampel Python, buat folder di `data/python-src/` lalu jalankan `python scripts/build_python_samples.py`.
2. Untuk sampel web, uji dulu HTML-nya di browser, lalu letakkan di dalam tepat satu blok ```` ```html ````.
3. Jalankan `python scripts/validate.py` dan `python scripts/decontaminate.py`.

## Struktur repo

```
data/train.jsonl                      dataset (format messages), semua sampel
data/kelompok/penalaran.jsonl         sampel dengan blok <think> (mode thinking)
data/kelompok/tanpa-penalaran.jsonl   sampel tanpa blok <think>
data/train_mix.jsonl                  hasil scripts/mix_general.py (tidak di-commit)
data/dataset_info.json                registrasi dataset untuk LLaMA-Factory
train/qwen3.5-4b-lora.yaml            konfigurasi LoRA Qwen3.5-4B untuk LLaMA-Factory
train/qwen2.5-coder-7b-lora.yaml      konfigurasi LoRA Qwen2.5-Coder-7B (pembanding)
notebooks/train_colab.ipynb           notebook Colab mandiri untuk di-upload (mode A dan mode B)
scripts/train_unsloth.py              script training mandiri (Unsloth): info/prepare/train/test/gguf, menulis status.json
scripts/chat_gradio.py                chatbot Gradio untuk mencoba adapter (streaming, pengaturan lengkap, pratinjau HTML)
scripts/agent_gradio.py               agen coding bergaya Claude Code: tulis → uji di browser → perbaiki (SEARCH/REPLACE)
scripts/codexia_studio.py             Codexia2 tanpa kuantisasi: UI bergaya Claude Code, editor Monaco, edit baris lewat SEARCH/REPLACE
scripts/build_notebook.py             membangun notebooks/train_colab.ipynb dari script dan runbook
docs/PANDUAN_TRAINING.md              panduan training lengkap untuk pengguna
docs/RUNBOOK_CLAUDE.md                aturan kerja Claude saat mengontrol training di Colab
docs/RENCANA_PYTHON.md                rencana adapter v4: jago Python sekaligus jago membuat website
docs/PROSEDUR_V4.md                   panduan Colab langkah demi langkah: ukur v3, latih v4-pilot, papan skor
docs/PANDUAN_V5_A100.md               panduan Colab A100 untuk V5: own + HumanEval, checkpoint di Drive, pilih epoch, ekspor GGUF
notebooks/v5_a100_colab.ipynb         notebook Colab V5 (dibangun dari PANDUAN_V5_A100.md)
docs/PANDUAN_V6_A100.md               panduan Colab A100 untuk V6: own + HumanEval+ + MBPP+ + MBPP, 10 epoch (terkontaminasi)
notebooks/v6_a100_colab.ipynb         notebook Colab V6 (dibangun dari PANDUAN_V6_A100.md)
docs/PANDUAN_V7_A100.md               panduan Colab A100 untuk V7: own + sulingan model dasar, 2 epoch, gerbang melawan model dasar
notebooks/v7_a100_colab.ipynb         notebook Colab V7 (dibangun dari PANDUAN_V7_A100.md)
scripts/sulingan.py                   jawaban model dasar yang lolos pemeriksaan otomatis (Python: assert MBPP, website: Chromium)
data/sulingan/prompt-web.jsonl        40 prompt website untuk sulingan V7 (bukan soal Web-eval)
tests/simulasi_v7/                    simulasi sel panduan V7 tanpa GPU, plus uji sulingan.py mode demo
notebooks/v4_pilot_interaktif.ipynb   panel Colab interaktif v4-pilot: siapkan, jalankan otomatis, progres, laporan
scripts/panel_v4.py                   logika panel (mode pilot dan a100): langkah, status dari Drive, saran saat gagal
scripts/build_panel_notebook.py       membangun notebook panel interaktif
notebooks/v4_pilot_colab.ipynb        panduan manual dalam bentuk notebook (dibangun dari PROSEDUR_V4.md)
docs/PROSEDUR_V4_A100.md              panduan Colab A100: latih v4 dari model dasar, LoRA 16-bit, konteks 16.384
notebooks/v4_a100_colab.ipynb         panduan A100 dalam bentuk notebook (dibangun dari PROSEDUR_V4_A100.md)
notebooks/v4_a100_interaktif.ipynb    panel Colab interaktif untuk panduan A100 (mode a100 di panel_v4.py)
scripts/md_to_notebook.py             membangun notebook Colab dari panduan Markdown
CLAUDE.md                             catatan singkat untuk Claude Code di repo ini
scripts/mix_general.py                pencampur dengan dataset umum dari Hugging Face
scripts/validate.py                   validasi dataset
scripts/build_bench_support.py        membuat dan memverifikasi kelompok bench-support (HumanEval, MBPP+, MBPP)
scripts/build_python_samples.py       membangun sampel Python dari data/python-src/ dengan output hasil eksekusi
scripts/decontaminate.py              cek tumpang tindih 13-gram data latihan dengan HumanEval+, MBPP+, IndoPy, Web-eval
data/python-src/                      sumber sampel Python: teks giliran, kode, dan data
data/bench-support/                   kelompok dataset bench-support, lisensi, dan catatan perubahannya
humaneval-bench-script/               script uji skor HumanEval+ dan MBPP+ (harness resmi EvalPlus, uji McNemar)
eval-suite/                           IndoPy (60 soal Python berbahasa Indonesia), Web-eval (10 website), papan skor
examples/web/*.html                   41 website dari sampel web, siap dibuka di browser
examples/web-pilihan/*.html           20 website etalase; 15 di antaranya punya versi dataset di examples/web/27–41
tests/test_web.mjs                    tes otomatis website dengan Playwright
tests/interactions.mjs                skenario interaksi per website
tests/interactions_pilihan.mjs        skenario interaksi untuk examples/web-pilihan
tests/test_debug.mjs                  tes sampel perbaikan bug (web_debug)
```
