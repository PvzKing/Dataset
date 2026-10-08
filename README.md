# Dataset Instruct Bahasa Indonesia untuk Qwen2.5-Coder

Dataset instruksi berbahasa Indonesia untuk fine-tuning **Qwen2.5-Coder-7B-Instruct**. Fokus utamanya adalah **pembuatan website one-shot**: dari satu permintaan, model langsung menghasilkan satu file HTML lengkap yang berjalan di browser, lalu menjelaskan fiturnya.

## Isi

| Kelompok | Sampel | Rata-rata token | Topik |
|---|---|---|---|
| Website one-shot (`web_oneshot`) | 20 | ±4.200 | landing page, portfolio, dashboard, toko online, game, kalkulator, form, undangan, dan lainnya |
| Teknologi & pemrograman | 22 | ±700 | algoritma, struktur data, database, keamanan, sistem terdistribusi, Git, testing, AI |
| Matematika | 10 | ±690 | kalkulus, pembuktian, probabilitas, statistik, aljabar |
| Sains | 10 | ±850 | fisika, biologi, kimia, ilmu bumi |
| **Total** | **62** | | ±115 ribu token, sampel terpanjang ±6.600 token |

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

## Format

`data/train.jsonl` berisi satu sampel per baris:

```json
{
  "id": "web-003",
  "category": "web_oneshot",
  "messages": [
    {"role": "user", "content": "bikin aplikasi to-do list dalam satu file html ..."},
    {"role": "assistant", "content": "Berikut aplikasi to-do list ...\n\n```html\n<!DOCTYPE html>...</html>\n```\n\n**Fitur** ..."}
  ]
}
```

- `messages` memakai format percakapan standar (`role`/`content`) yang dipetakan ke chat template ChatML milik Qwen2.5.
- Sebagian besar sampel **tidak memakai system message**. Saat training, chat template Qwen2.5 otomatis menyisipkan system prompt bawaannya. Kondisi ini sama dengan pemakaian model sehari-hari di Ollama, LM Studio, atau vLLM.
- Dua sampel web (`web-012`, `web-019`) memakai system prompt khusus, misalnya batas maksimal 3 poin penjelasan, supaya model tetap patuh pada instruksi system.

## Standar kualitas sampel website

- Satu file HTML lengkap (HTML, CSS, JavaScript) tanpa library maupun request eksternal, sehingga langsung jalan saat dibuka.
- Setiap website diuji otomatis di Chromium (Playwright) pada lebar 1280px dan 375px. Kriterianya: tanpa error JavaScript, tanpa scroll horizontal (juga dicek di 320px), dan lolos skenario interaksi khusus. Contohnya, kalkulator harus menghasilkan `2 + 3 × 4 = 14`, minimax tic-tac-toe tidak pernah kalah, dan editor markdown kebal terhadap `<img onerror>` serta link `javascript:`.
- Responsif dan aksesibel: HTML semantik, label form, atribut `aria-*`, fokus keyboard yang terlihat, dan dukungan `prefers-reduced-motion`.
- Aman: data dari pengguna dipasang dengan `textContent`, tanpa `eval()`, dan akses `localStorage` dibungkus `try/catch`.
- Konteks Indonesia yang akurat: format Rupiah dengan `Intl.NumberFormat('id-ID')`, nomor HP Indonesia, zona waktu WIB, dan untuk website kantor hukum penyesuaian dengan Kode Etik Advokat Indonesia, UU No. 18 Tahun 2003 tentang Advokat, serta UU No. 27 Tahun 2022 tentang Pelindungan Data Pribadi.

Contoh kode Python di sampel teknologi juga sudah dijalankan, sehingga output yang tertulis di jawaban sesuai dengan hasil eksekusi sebenarnya.

## Mencampur dengan dataset umum

Melatih model hanya dengan 62 sampel berisiko membuat model "terlalu fokus", misalnya selalu menjawab dengan file HTML walaupun pertanyaannya bukan soal website. Selain itu, kemampuan umumnya bisa menurun. Karena itu, config training memakai data campuran yang dibuat oleh `scripts/mix_general.py`:

| Sumber | Jumlah bawaan | Isi |
|---|---|---|
| Dataset ini (`data/train.jsonl`) | 62 | semua sampel, tanpa dikurangi |
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
- **Model dasar** Qwen2.5-Coder-7B-Instruct berlisensi Apache 2.0. Adapter atau model gabungan hasil fine-tuning boleh didistribusikan dan dipakai secara komersial, dengan syarat menyertakan salinan lisensi, mempertahankan pemberitahuan hak cipta, dan menandai bahwa model telah diubah (Pasal 4 Apache License 2.0). Ukuran lain dalam keluarga yang sama, misalnya 3B, memakai lisensi yang berbeda.
- Periksa kartu dataset (dataset card) masing-masing sumber untuk lisensi terbaru sebelum mendistribusikan dataset campuran atau model hasil training.

## Training dengan LLaMA-Factory

1. Pasang [LLaMA-Factory](https://github.com/hiyouga/LLaMA-Factory):
   ```bash
   git clone --depth 1 https://github.com/hiyouga/LLaMA-Factory.git
   cd LLaMA-Factory && pip install -e ".[torch,metrics]"
   ```
2. Buat data campuran (lihat bagian sebelumnya):
   ```bash
   python scripts/mix_general.py
   ```
3. Dari root repo ini, jalankan:
   ```bash
   llamafactory-cli train train/qwen2.5-coder-7b-lora.yaml
   ```
   Dataset sudah terdaftar di `data/dataset_info.json` sebagai `instruct_id_mix` (campuran) dan `instruct_id` (hanya dataset ini).
4. Coba hasilnya:
   ```bash
   llamafactory-cli chat --model_name_or_path Qwen/Qwen2.5-Coder-7B-Instruct \
     --adapter_name_or_path saves/qwen2.5-coder-7b-instruct-id/lora/sft \
     --template qwen --finetuning_type lora
   ```

Ringkasan konfigurasi di `train/qwen2.5-coder-7b-lora.yaml`:

- LoRA rank 16 di semua layer linear, learning rate `1e-4`, 2 epoch, scheduler cosine, dan batch efektif 8. Jika melatih dengan `instruct_id` saja (tanpa campuran), naikkan ke 3 epoch.
- `template: qwen` dan `cutoff_len: 8192`, sehingga tidak ada sampel yang terpotong.
- Loss hanya dihitung pada jawaban assistant. Ini perilaku bawaan LLaMA-Factory.
- Perkiraan VRAM untuk LoRA bf16 adalah sekitar 24 GB. Untuk GPU yang lebih kecil, aktifkan `quantization_bit: 4` (QLoRA).

Framework lain seperti TRL (`SFTTrainer`), Axolotl (`type: chat_template`), dan Unsloth juga bisa membaca format `messages` ini. Pastikan memakai chat template bawaan tokenizer Qwen2.5, dan loss hanya dihitung pada bagian assistant.

## Training di Google Colab (GPU T4 gratis)

Buka [`notebooks/train_colab_t4.ipynb`](notebooks/train_colab_t4.ipynb) di Colab (*File → Open notebook → GitHub*), pilih runtime **T4 GPU**, atur sel *Konfigurasi*, lalu jalankan semua sel. Notebook ini memakai [Unsloth](https://github.com/unslothai/unsloth) untuk QLoRA 4-bit karena:

- **Memori:** T4 hanya punya 16 GB VRAM. Sampel web sampai ±6.600 token butuh penghematan memori dari Unsloth agar muat pada `max_seq_length` 8192.
- **Presisi:** T4 tidak mendukung bf16, jadi notebook otomatis memakai fp16.
- **Sampel terlalu panjang dibuang, bukan dipotong.** Jika `MAX_SEQ_LEN` diturunkan (misalnya ke 6144 saat kehabisan memori), sampel yang terlalu panjang dibuang supaya model tidak belajar dari HTML yang terpotong. Notebook menampilkan sampel mana saja yang dibuang.
- **Loss hanya pada jawaban assistant**, memakai `train_on_responses_only`. Notebook mencetak contoh token yang dilatih untuk memastikan masking-nya benar.
- **Tahan sesi putus:** data campuran dan checkpoint disimpan ke Google Drive setiap 20 step. Jika sesi putus, jalankan ulang semua sel dan training dilanjutkan dari checkpoint terakhir.
- **Hasil:** adapter LoRA (±160 MB) di Drive, contoh website yang dibuat model, dan opsional file GGUF q4_k_m untuk Ollama/llama.cpp.

Perkiraan waktu training di T4, belum termasuk instalasi dan unduh model (±10–15 menit):

| Data | Token dilatih | Waktu |
|---|---|---|
| `own` (62 sampel, 3 epoch) | ±350 ribu | ±15–50 menit |
| `mix` (±960 sampel, 2 epoch) | ±1 juta | ±1–2,5 jam |

Angka ini perkiraan dengan asumsi 120–400 token/detik dan belum diukur. ETA di progress bar saat training adalah angka yang sebenarnya. Colab gratis membatasi lama sesi dan ketersediaan GPU, jadi data `mix` mungkin butuh lebih dari satu sesi.

Untuk LLaMA-Factory di GPU 16 GB tanpa bf16, gunakan `train/qwen2.5-coder-7b-qlora-t4.yaml` (QLoRA 4-bit, fp16, Unsloth, checkpoint tiap 20 step).

## Validasi

```bash
python scripts/validate.py
# opsional, hitung token dengan tokenizer asli (butuh transformers):
python scripts/validate.py --tokenizer Qwen/Qwen2.5-Coder-7B-Instruct --max-len 8192
```

Script ini memeriksa struktur JSON, urutan role, ID dan prompt duplikat, kelengkapan blok HTML pada sampel web, serta panjang token terhadap `cutoff_len`.

## Catatan penting

- **Ukuran dataset kecil.** Fine-tuning dengan 62 sampel terutama membentuk gaya dan format jawaban, misalnya kebiasaan menghasilkan satu file HTML lengkap dengan penjelasan berbahasa Indonesia. Pengetahuan baru tidak banyak bertambah. Karena itu, config bawaan memakai data campuran dengan dataset umum (lihat bagian *Mencampur dengan dataset umum*).
- **Hindari overfitting.** Pantau training loss. Dengan data sekecil ini, terlalu banyak epoch membuat model sekadar menghafal jawaban.

## Melihat dan menguji website

Ke-20 website juga tersedia sebagai file terpisah di `examples/web/`, isinya identik dengan yang ada di `data/train.jsonl`. Buka saja file `.html`-nya di browser untuk melihat hasilnya.

Untuk menjalankan ulang tes otomatis (Chromium, desktop 1280px dan HP 375px):

```bash
cd tests
npm install
npx playwright install chromium
node test_web.mjs              # semua website
node test_web.mjs 04-          # satu website saja
```

Tes gagal jika ada error JavaScript, request ke luar, scroll horizontal, atau skenario interaksi di `tests/interactions.mjs` yang tidak terpenuhi. Screenshot disimpan di `tests/screenshots/`.

## Menambah sampel

1. Tambahkan satu baris JSON ke `data/train.jsonl` dengan `id` unik.
2. Untuk sampel web, uji dulu HTML-nya di browser, lalu letakkan di dalam tepat satu blok ```` ```html ````.
3. Jalankan `python scripts/validate.py`.

## Struktur repo

```
data/train.jsonl                      dataset (format messages)
data/train_mix.jsonl                  hasil scripts/mix_general.py (tidak di-commit)
data/dataset_info.json                registrasi dataset untuk LLaMA-Factory
train/qwen2.5-coder-7b-lora.yaml      konfigurasi fine-tuning LoRA
train/qwen2.5-coder-7b-qlora-t4.yaml  konfigurasi QLoRA untuk GPU 16 GB tanpa bf16 (T4)
notebooks/train_colab_t4.ipynb        notebook training di Google Colab T4 (Unsloth)
scripts/mix_general.py                pencampur dengan dataset umum dari Hugging Face
scripts/validate.py                   validasi dataset
examples/web/*.html                   20 website dari sampel web, siap dibuka di browser
tests/test_web.mjs                    tes otomatis website dengan Playwright
tests/interactions.mjs                skenario interaksi per website
```
