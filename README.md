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

## Training dengan LLaMA-Factory

1. Pasang [LLaMA-Factory](https://github.com/hiyouga/LLaMA-Factory):
   ```bash
   git clone --depth 1 https://github.com/hiyouga/LLaMA-Factory.git
   cd LLaMA-Factory && pip install -e ".[torch,metrics]"
   ```
2. Dari root repo ini, jalankan:
   ```bash
   llamafactory-cli train train/qwen2.5-coder-7b-lora.yaml
   ```
   Dataset sudah terdaftar di `data/dataset_info.json` dengan nama `instruct_id`.
3. Coba hasilnya:
   ```bash
   llamafactory-cli chat --model_name_or_path Qwen/Qwen2.5-Coder-7B-Instruct \
     --adapter_name_or_path saves/qwen2.5-coder-7b-instruct-id/lora/sft \
     --template qwen --finetuning_type lora
   ```

Ringkasan konfigurasi di `train/qwen2.5-coder-7b-lora.yaml`:

- LoRA rank 16 di semua layer linear, learning rate `1e-4`, 3 epoch, scheduler cosine, dan batch efektif 8.
- `template: qwen` dan `cutoff_len: 8192`, sehingga tidak ada sampel yang terpotong.
- Loss hanya dihitung pada jawaban assistant. Ini perilaku bawaan LLaMA-Factory.
- Perkiraan VRAM untuk LoRA bf16 adalah sekitar 24 GB. Untuk GPU yang lebih kecil, aktifkan `quantization_bit: 4` (QLoRA).

Framework lain seperti TRL (`SFTTrainer`), Axolotl (`type: chat_template`), dan Unsloth juga bisa membaca format `messages` ini. Pastikan memakai chat template bawaan tokenizer Qwen2.5, dan loss hanya dihitung pada bagian assistant.

## Validasi

```bash
python scripts/validate.py
# opsional, hitung token dengan tokenizer asli (butuh transformers):
python scripts/validate.py --tokenizer Qwen/Qwen2.5-Coder-7B-Instruct --max-len 8192
```

Script ini memeriksa struktur JSON, urutan role, ID dan prompt duplikat, kelengkapan blok HTML pada sampel web, serta panjang token terhadap `cutoff_len`.

## Catatan penting

- **Ukuran dataset kecil.** Fine-tuning dengan 62 sampel terutama membentuk gaya dan format jawaban, misalnya kebiasaan menghasilkan satu file HTML lengkap dengan penjelasan berbahasa Indonesia. Pengetahuan baru tidak banyak bertambah. Untuk hasil yang lebih stabil, tambah sampel atau campur dengan dataset instruksi umum agar kemampuan dasar model tidak menurun.
- **Hindari overfitting.** Pantau training loss. Dengan data sekecil ini, terlalu banyak epoch membuat model sekadar menghafal jawaban.

## Menambah sampel

1. Tambahkan satu baris JSON ke `data/train.jsonl` dengan `id` unik.
2. Untuk sampel web, uji dulu HTML-nya di browser, lalu letakkan di dalam tepat satu blok ```` ```html ````.
3. Jalankan `python scripts/validate.py`.

## Struktur repo

```
data/train.jsonl                      dataset (format messages)
data/dataset_info.json                registrasi dataset untuk LLaMA-Factory
train/qwen2.5-coder-7b-lora.yaml      konfigurasi fine-tuning LoRA
scripts/validate.py                   validasi dataset
```
