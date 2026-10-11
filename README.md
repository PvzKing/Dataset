# Dataset Instruct Bahasa Indonesia untuk Qwen3.5-4B

Dataset instruksi berbahasa Indonesia untuk fine-tuning **Qwen3.5-4B** dalam mode non-thinking. Dataset ini juga bisa dipakai untuk Qwen2.5-Coder-7B-Instruct. Fokus utamanya adalah **pembuatan website one-shot**: dari satu permintaan, model langsung menghasilkan satu file HTML lengkap yang berjalan di browser, lalu menjelaskan fiturnya.

## Isi

| Kelompok | Sampel | Rata-rata token | Topik |
|---|---|---|---|
| Website one-shot (`web_oneshot`) | 24 | ±4.500 | landing page, portfolio, dashboard, toko online, game, kalkulator, sistem kasir, form, undangan, dan lainnya |
| Perbaikan bug website (`web_debug`) | 12 | ±3.650 | XSS, urutan operasi, timer di tab latar, `localStorage` rusak, overflow di HP, acak tidak aman, dan lainnya |
| Teknologi & pemrograman | 22 | ±700 | algoritma, struktur data, database, keamanan, sistem terdistribusi, Git, testing, AI |
| Matematika & logika | 11 | ±800 | kalkulus, pembuktian, probabilitas, statistik, aljabar, teka-teki logika |
| Sains | 10 | ±850 | fisika, biologi, kimia, ilmu bumi |
| **Total** | **79** | | ±184 ribu token, sampel terpanjang ±6.200 token |

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

## Mencampur dengan dataset umum

Melatih model hanya dengan 79 sampel berisiko membuat model "terlalu fokus", misalnya selalu menjawab dengan file HTML walaupun pertanyaannya bukan soal website. Selain itu, kemampuan umumnya bisa menurun. Karena itu, config training memakai data campuran yang dibuat oleh `scripts/mix_general.py`:

| Sumber | Jumlah bawaan | Isi |
|---|---|---|
| Dataset ini (`data/train.jsonl`) | 79 | semua sampel, tanpa dikurangi |
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
- **Ringkasan:** jumlah sampel dan perkiraan porsi token setiap sumber dicetak di akhir. Sampel web di dataset ini panjang (±4.200 token), jadi meskipun jumlah sampelnya kecil, porsi tokennya tetap besar. Targetkan porsi dataset sendiri sekitar 20–30% dari total token, dan ubah jumlah per sumber jika perlu.
- **Skema dicek saat dijalankan:** jika pengelola dataset sumber mengubah nama kolom, script berhenti dan menampilkan kolom yang tersedia. Sesuaikan entri `SOURCES` di dalam script.

`data/train_mix.jsonl` tidak di-commit (ada di `.gitignore`) karena isinya data pihak ketiga. Buat ulang file itu di mesin training.

### Catatan lisensi dan hukum

- **Aya Dataset** ditulis oleh kontributor manusia, bukan dihasilkan model, dan dirilis dengan lisensi terbuka. Lisensi terbuka seperti Apache 2.0 umumnya mewajibkan atribusi dan menyertakan teks lisensi saat data didistribusikan ulang.
- **Magicoder-Evol-Instruct** dan **UltraChat** dibuat dengan bantuan model OpenAI. Syarat penggunaan OpenAI melarang penggunanya memakai output untuk mengembangkan model yang bersaing dengan OpenAI. Apakah ketentuan kontraktual itu juga mengikat pihak ketiga yang hanya mengunduh datasetnya masih diperdebatkan. Untuk eksperimen pribadi atau riset risikonya kecil, tetapi jika model hasil fine-tuning akan dipakai atau dijual secara komersial, pertimbangkan untuk mengganti kedua sumber ini dengan data yang ditulis manusia atau berlisensi jelas.
- **Model dasar** Qwen3.5-4B dan Qwen2.5-Coder-7B-Instruct berlisensi Apache 2.0. Adapter atau model gabungan hasil fine-tuning boleh didistribusikan dan dipakai secara komersial, dengan syarat menyertakan salinan lisensi, mempertahankan pemberitahuan hak cipta, dan menandai bahwa model telah diubah (Pasal 4 Apache License 2.0). Tidak semua model Qwen berlisensi Apache 2.0: misalnya Qwen2.5-Coder-3B memakai lisensi riset non-komersial. Periksa lisensi setiap model sebelum mengganti model dasar.
- Periksa kartu dataset (dataset card) masing-masing sumber untuk lisensi terbaru sebelum mendistribusikan dataset campuran atau model hasil training.

## Kelompok `bench-support` (HumanEval)

Folder `data/bench-support/` berisi sampel latihan dari benchmark kode, terpisah dari dataset `own`. Saat ini isinya 164 soal HumanEval dengan format prompt instruct EvalPlus. Solusinya diambil dari HumanEval+, kecuali satu soal yang ditulis ulang.

Setiap solusi diverifikasi oleh `scripts/build_bench_support.py` dengan dua cara: tes resmi HumanEval, dan pemeriksaan silang dengan solusi asli HumanEval pada 111 ribu input tambahan HumanEval+. Lewat pemeriksaan ini ditemukan 15 solusi asli HumanEval yang keliru dan satu soal yang kedua solusi referensinya gagal. Rinciannya ada di `data/bench-support/README.md`.

Pakai dengan `--dataset bench`, yaitu `own` ditambah `bench-support`, total 243 sampel:

```bash
python scripts/train_unsloth.py train --dataset bench
python scripts/build_bench_support.py      # membuat ulang dan memverifikasi data/bench-support/humaneval.jsonl
```

Dua hal yang perlu diingat:
- **Skor HumanEval tidak lagi bersih.** Model yang dilatih dengan kelompok ini sudah melihat soal dan jawabannya.
- **Lisensi wajib disertakan.** HumanEval berlisensi MIT (OpenAI) dan HumanEval+ berlisensi Apache 2.0 (EvalPlus). Jika data atau model didistribusikan, sertakan kedua teks lisensinya yang ada di folder tersebut.

## Pilihan data: `own` atau `mix`

- **`own`**: hanya `data/train.jsonl`, 79 sampel, 3 epoch, ±540 ribu token diproses.
- **`mix`**: dataset ini ditambah ±900 sampel umum dari `scripts/mix_general.py`, 2 epoch, ±1 juta token dilatih.

Mulailah dengan **`own`**, lalu beralih ke `mix` jika hasilnya menunjukkan gejala lupa kemampuan umum.

- **Alasan memulai dengan `own`:**
  - Qwen3.5-4B sudah dilatih dengan data umum dalam jumlah sangat besar. 79 sampel dengan LoRA rank 16 hanya mengubah sedikit bobot, jadi risiko model melupakan kemampuan umumnya kecil.
  - Sekitar 80% token di dataset ini adalah sampel website, baik one-shot maupun perbaikan bug. Itu memang kemampuan utama yang ingin diajarkan.
  - Training di T4 butuh ±30–90 menit, tidak berjam-jam, jadi cepat untuk iterasi.
- **Kapan beralih ke `mix`.** Jika setelah training dengan `own` muncul salah satu gejala berikut:
  - Setiap pertanyaan dijawab dengan HTML.
  - Pertanyaan umum dijawab dengan buruk.
  - Bahasa jawaban menjadi aneh.
- **Risiko `mix`.** Sebagian data umumnya (Magicoder dan UltraChat) dibuat dengan model OpenAI. Lihat catatan hukum di atas jika model akan dipakai secara komersial. Jalankan `mix_general.py --code 0 --chat 0` untuk memakai Aya saja, yang ditulis manusia.

## Training di Google Colab

**Panduan langkah demi langkah: [`docs/PANDUAN_TRAINING.md`](docs/PANDUAN_TRAINING.md).**

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

| GPU | `own` (±540 ribu token) | `mix` (±1 juta token) |
|---|---|---|
| T4 gratis (QLoRA 4-bit, float32, konteks 6144) | ±35 menit (23 menit terukur saat masih 62 sampel) | ±1,5–3 jam |
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

- **Ukuran dataset kecil.** Fine-tuning dengan 79 sampel terutama membentuk gaya dan format jawaban, misalnya kebiasaan menghasilkan satu file HTML lengkap dengan penjelasan berbahasa Indonesia. Pengetahuan baru tidak banyak bertambah. Karena itu, config bawaan memakai data campuran dengan dataset umum (lihat bagian *Mencampur dengan dataset umum*).
- **Hindari overfitting.** Pantau training loss. Dengan data sekecil ini, terlalu banyak epoch membuat model sekadar menghafal jawaban.

## Melihat dan menguji website

Ke-24 website juga tersedia sebagai file terpisah di `examples/web/`, isinya identik dengan yang ada di `data/train.jsonl`. Buka saja file `.html`-nya di browser untuk melihat hasilnya.

Untuk menjalankan ulang tes otomatis (Chromium, desktop 1280px dan HP 375px):

```bash
cd tests
npm install
npx playwright install chromium
node test_web.mjs              # semua website
node test_web.mjs 04-          # satu website saja
```

Tes gagal jika ada error JavaScript, request ke luar, scroll horizontal, atau skenario interaksi di `tests/interactions.mjs` yang tidak terpenuhi. Screenshot disimpan di `tests/screenshots/`.

Sampel perbaikan bug diuji dengan `node test_debug.mjs`. Untuk setiap sampel, tes memeriksa tiga hal:
1. Blok SEARCH/REPLACE di jawaban, bila diterapkan ke kode di prompt, menghasilkan website asli di `examples/web` persis sama.
2. Versi ber-bug benar-benar gagal di browser.
3. Pemeriksaan khusus bug tersebut lolos di versi asli.

## Agen coding (`scripts/agent_gradio.py`)

`scripts/agent_gradio.py` adalah tampilan Gradio bergaya Claude Code untuk model hasil fine-tuning (bawaan: adapter v3). Model tidak hanya menjawab, tetapi bekerja dalam loop:

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

## Menambah sampel

1. Tambahkan satu baris JSON ke `data/train.jsonl` dengan `id` unik.
2. Untuk sampel web, uji dulu HTML-nya di browser, lalu letakkan di dalam tepat satu blok ```` ```html ````.
3. Jalankan `python scripts/validate.py`.

## Struktur repo

```
data/train.jsonl                      dataset (format messages)
data/train_mix.jsonl                  hasil scripts/mix_general.py (tidak di-commit)
data/dataset_info.json                registrasi dataset untuk LLaMA-Factory
train/qwen3.5-4b-lora.yaml            konfigurasi LoRA Qwen3.5-4B untuk LLaMA-Factory
train/qwen2.5-coder-7b-lora.yaml      konfigurasi LoRA Qwen2.5-Coder-7B (pembanding)
notebooks/train_colab.ipynb           notebook Colab mandiri untuk di-upload (mode A dan mode B)
scripts/train_unsloth.py              script training mandiri (Unsloth): info/prepare/train/test/gguf, menulis status.json
scripts/chat_gradio.py                chatbot Gradio untuk mencoba adapter (streaming, pengaturan lengkap, pratinjau HTML)
scripts/agent_gradio.py               agen coding bergaya Claude Code: tulis → uji di browser → perbaiki (SEARCH/REPLACE)
scripts/build_notebook.py             membangun notebooks/train_colab.ipynb dari script dan runbook
docs/PANDUAN_TRAINING.md              panduan training lengkap untuk pengguna
docs/RUNBOOK_CLAUDE.md                aturan kerja Claude saat mengontrol training di Colab
CLAUDE.md                             catatan singkat untuk Claude Code di repo ini
scripts/mix_general.py                pencampur dengan dataset umum dari Hugging Face
scripts/validate.py                   validasi dataset
scripts/build_bench_support.py        membuat dan memverifikasi kelompok bench-support (HumanEval)
data/bench-support/                   kelompok dataset bench-support, lisensi, dan catatan perubahannya
examples/web/*.html                   24 website dari sampel web, siap dibuka di browser
tests/test_web.mjs                    tes otomatis website dengan Playwright
tests/interactions.mjs                skenario interaksi per website
tests/test_debug.mjs                  tes sampel perbaikan bug (web_debug)
```
