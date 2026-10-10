# Runbook: Claude menjalankan training di Google Colab

Dokumen ini ditujukan untuk Claude Code yang berjalan di terminal VM Google Colab. Notebook menyalinnya ke
`/content/CLAUDE.md`. Tugasmu: menjalankan dan memantau fine-tuning sampai selesai, memperbaiki masalah yang aman
diperbaiki sendiri, dan melaporkan hasilnya ke pengguna dalam bahasa Indonesia yang singkat. Pengguna berinteraksi
denganmu hanya lewat terminal ini, jadi tulis setiap laporan sebagai jawaban di terminal.

## Konteks

- **Script training:** `/content/train_unsloth.py`, ditulis oleh notebook. Script ini mandiri, tidak butuh repo.
  - Konfigurasi ada di blok `CONFIG` di awal file. Argumen seperti `--max-seq-len 6144` menimpa nilai `CONFIG` hanya untuk perintah itu.
  - Jangan mengubah file ini tanpa izin pengguna.
- **Google Drive:** ada di `/content/drive/MyDrive`. Semua yang tidak disimpan di Drive hilang saat runtime Colab di-reset.
- **Data `own`:** `train.jsonl` di `/content` dipakai lebih dulu. Jika tidak ada, versi terbaru diunduh ulang dari repo GitHub publik `PvzKing/Dataset` ke folder hasil setiap kali perintah dijalankan.
- **Lokasi hasil:** `python /content/train_unsloth.py info` menampilkan konfigurasi dan folder hasil `RUN_DIR`. Isi `RUN_DIR`:

  | File | Isi |
  |---|---|
  | `status.json` | `stage`, `message`, `step`/`max_steps`, `loss`, `eta_min`, `result`, `tests`; saat error juga `hint` dan `traceback` |
  | `checkpoints/` | checkpoint; perintah `train` melanjutkan dari checkpoint terakhir jika data dan pengaturannya sama |
  | `arsip/<waktu>/` | hasil lama yang dipindahkan otomatis karena data atau pengaturan berubah; training lalu dimulai dari awal. Ini normal, bukan error. |
  | folder `...-lanjut` | hasil training lanjutan (`--init-adapter <folder lora-adapter>`); adapter asal tidak diubah |
  | `lora-adapter/` | adapter hasil training |
  | `contoh-*.md`, `contoh-*.html` | jawaban model untuk prompt uji dan HTML yang diekstrak darinya |

  Nilai `stage` berurutan: `starting` → `loading` → `prepared` → `training` → `saving` → `trained` → `testing` → `done`.
  Jika gagal, nilainya `error`.

## Langkah

1. **Cek lingkungan**, lalu laporkan hasilnya dalam satu atau dua kalimat:
   ```bash
   python /content/train_unsloth.py info; nvidia-smi --query-gpu=name,memory.total --format=csv
   ls /content/drive/MyDrive >/dev/null && echo "drive OK"; python -c "import unsloth" && echo "unsloth OK"
   ```
   - **Drive belum ter-mount:** minta pengguna menjalankan sel *Mount Google Drive* di notebook. Mount butuh login lewat UI, jadi tidak bisa dilakukan dari terminal.
   - **Unsloth belum terpasang:** jalankan `pip install --upgrade unsloth`.
2. **Cek data tanpa GPU:**
   ```bash
   python /content/train_unsloth.py prepare
   ```
   Pastikan:
   - output berisi `data valid`;
   - jumlah sampel yang dibuang sesuai harapan (untuk `own` dengan 8192 seharusnya 0);
   - contoh teks training diakhiri prompt jawaban yang benar. Untuk Qwen3.5, prompt itu berisi blok `<think>` kosong. Untuk Qwen2.5 tidak ada blok `<think>`.

   Laporkan perkiraan step dan waktu ke pengguna.
3. **Jalankan training di latar belakang.** Jangan menjalankannya di foreground, karena prosesnya bisa berjam-jam:
   ```bash
   setsid nohup python /content/train_unsloth.py train > /content/train.log 2>&1 < /dev/null &
   ```
4. **Pantau** sampai `stage` bernilai `done` atau `error` (`RUN_DIR` dari langkah 1):
   ```bash
   cat RUN_DIR/status.json; tail -n 20 /content/train.log; nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv
   ```
   - **Saat menunggu:** pakai perintah tunggu maksimal ±9 menit per panggilan, misalnya `sleep 300`, atau alat pemantau latar belakang jika tersedia. Jarak antar pengecekan 5–10 menit sudah cukup.
   - **Di awal training:** pastikan log berisi baris `cek masking`, yaitu bagian yang dilatih diawali jawaban, bukan pertanyaan. Untuk Qwen3.5 di T4, log juga harus berisi `Switching to float32`.
   - **Loss** biasanya turun di beberapa puluh step pertama. Jika loss `nan` atau naik terus, hentikan dan ikuti tabel di bawah.
   - **Laporan ke pengguna** cukup saat ada perubahan berarti: training mulai, kira-kira setiap 25% progres, error, atau selesai. Isi laporan: step, loss, dan ETA.
5. **Setelah selesai**, baca `status.json` bagian `result` dan `tests`, lalu periksa setiap `contoh-*.html`:
   - **File lengkap:** diakhiri `</html>`, dan `finished: true` berarti jawaban tidak terpotong batas token.
   - **Tidak ada library eksternal:** cek dengan `grep -c "<script src=\|<link .*href=\"http" RUN_DIR/contoh-*.html`, hasilnya seharusnya 0.
   - **Bahasa:** isi halaman memakai bahasa Indonesia.

   Laporkan hasilnya:
   - loss akhir dan lama training;
   - lokasi adapter;
   - penilaian singkat kedua website;
   - saran langkah berikutnya: bandingkan dengan `--model qwen2.5-coder-7b`, coba `--dataset mix` jika ada gejala lupa kemampuan umum, atau ekspor GGUF dengan perintah `gguf`.

## Menangani masalah

| Gejala | Tindakan |
|---|---|
| `stage: error` dengan `CUDA out of memory` | Di T4, script otomatis memakai `--load-in-4bit --max-seq-len 6144`. Kombinasi ini sudah terbukti jalan. Semua sampel dataset dijaga di bawah 6144 token, jadi jumlah yang dibuang seharusnya 0; laporkan jika tidak. Jika error terjadi dengan pengaturan lain, ulangi dengan `--load-in-4bit --max-seq-len 6144` dan beri tahu pengguna bahwa akurasi Qwen3.5 sedikit turun dengan 4-bit. Hasilnya disimpan di folder `...-4bit`. Untuk batas di bawah 6144, tanya pengguna dulu, karena sebagian besar sampel web akan terbuang. |
| Loss `nan`, atau `grad_norm` `nan` terus-menerus | Hentikan proses. Jalankan `pip install --upgrade unsloth unsloth_zoo`, lalu ulangi. Jika tetap `nan`, laporkan ke pengguna, jangan diakali dengan mengganti presisi sendiri. |
| `ModuleNotFoundError`, atau error versi transformers/trl | Jalankan `pip install --upgrade unsloth`. Qwen3.5 butuh transformers v5. |
| Gagal mengunduh model atau data (HTTP 429/5xx, timeout) | Tunggu sebentar lalu ulangi. Jika berulang, minta pengguna mengisi secret `HF_TOKEN` di Colab, atau meng-upload `train.jsonl` ke `/content`. |
| `Google Drive belum ter-mount` | Minta pengguna menjalankan sel *Mount Google Drive*. |
| `status.json` tidak berubah lebih dari 15 menit dan prosesnya hilang (`pgrep -f train_unsloth` kosong) | Lihat akhir `/content/train.log`. Jika tidak ada error, kemungkinan proses dimatikan. Jalankan ulang perintah `train`, dan training dilanjutkan dari checkpoint. |
| Pengguna meminta berhenti ("stop training") | Jalankan `pkill -f "train_unsloth.py train"`. Checkpoint terakhir tetap ada di Drive dan bisa dilanjutkan dengan perintah `train` yang sama. |
| Runtime Colab di-reset (`/content/train_unsloth.py` hilang) | Kamu juga ikut hilang, jadi pengguna yang menjalankan ulang notebook. Checkpoint di Drive tetap aman dan perintah `train` akan melanjutkannya. |
| `stage: error` jenis lain | Baca `hint` dan `traceback`. Perbaiki hanya jika penyebabnya jelas dan aman. Jika tidak, laporkan ke pengguna beserta ringkasan error-nya. |

## Batasan

- **Boleh tanpa bertanya:**
  - menjalankan `info`, `prepare`, `train`, dan `test`;
  - memantau proses;
  - melanjutkan dari checkpoint;
  - beralih ke `--load-in-4bit` atau menurunkan `--max-seq-len` sampai 6144 saat kehabisan memori;
  - memasang ulang atau meng-upgrade paket Python;
  - menghentikan training jika pengguna memintanya.
- **Tanya dulu sebelum:**
  - mengganti model, dataset, atau hyperparameter lain;
  - beralih ke `--dataset mix`, karena sebagian sumbernya dibuat dengan model OpenAI dan ada implikasi lisensi (lihat README repo);
  - menghapus checkpoint atau hasil di Drive;
  - menjalankan `gguf`, karena butuh waktu sekitar 15–40 menit dan beberapa GB di Drive;
  - mengubah `/content/train_unsloth.py` atau file data.
- **Jangan pernah:**
  - menampilkan, menyalin, atau menyimpan isi secret (`HF_TOKEN` dan sejenisnya) ke file atau log;
  - menjalankan SSH, tunnel (ngrok dan sejenisnya), remote desktop, atau web UI. Kebijakan Colab membatasi hal-hal ini, terutama di tier gratis.
