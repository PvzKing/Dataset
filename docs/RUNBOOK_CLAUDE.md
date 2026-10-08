# Runbook: Claude menjalankan training di Google Colab

Dokumen ini ditujukan untuk Claude Code yang berjalan di terminal VM Google Colab. Tugasmu: menjalankan dan memantau
fine-tuning sampai selesai, memperbaiki masalah yang aman diperbaiki sendiri, dan melaporkan hasilnya ke pengguna dalam
bahasa Indonesia yang singkat.
Pengguna berinteraksi denganmu hanya lewat terminal ini, jadi tulis setiap laporan sebagai jawaban di terminal.

## Konteks

- Repo ada di `/content/Dataset`. Google Drive ada di `/content/drive/MyDrive`. Semua yang tidak disimpan di Drive
  hilang saat runtime Colab di-reset.
- `run_config.json` di root repo ditulis oleh notebook dan berisi `model`, `dataset`, `out`, dan `max_seq_len`. Pakai
  nilai itu kecuali pengguna meminta yang lain.
- Semua pekerjaan berat lewat `scripts/train_unsloth.py`. Hasilnya ada di `<out>/<model>-<dataset>/`:

  | File | Isi |
  |---|---|
  | `status.json` | `stage`, `message`, `step`/`max_steps`, `loss`, `eta_min`, `result`, `tests`; saat error juga `hint` dan `traceback` |
  | `train.log` | seluruh output proses training |
  | `checkpoints/` | checkpoint; perintah `train` otomatis melanjutkan dari checkpoint terakhir |
  | `lora-adapter/` | adapter hasil training |
  | `contoh-*.md`, `contoh-*.html` | jawaban model untuk prompt uji dan HTML yang diekstrak darinya |

  Nilai `stage` berurutan: `starting` → `loading` → `prepared` → `training` → `saving` → `trained` → `testing` → `done`.
  Jika gagal, nilainya `error`.

## Langkah

1. **Cek lingkungan**, lalu laporkan hasilnya dalam satu atau dua kalimat:
   ```bash
   cat run_config.json; nvidia-smi --query-gpu=name,memory.total --format=csv
   ls /content/drive/MyDrive >/dev/null && echo "drive OK"; python -c "import unsloth" && echo "unsloth OK"
   ```
   - **Drive belum ter-mount:** minta pengguna menjalankan sel *Hubungkan Google Drive* di notebook. Mount butuh login lewat UI, jadi tidak bisa dilakukan dari terminal.
   - **Unsloth belum terpasang:** jalankan `pip install --upgrade unsloth`.
2. **Cek data tanpa GPU:**
   ```bash
   python scripts/train_unsloth.py prepare --model M --dataset D --out OUT --max-seq-len L
   ```
   Pastikan:
   - validasi `OK`;
   - jumlah sampel yang dibuang sesuai harapan (untuk `own` dengan 8192 seharusnya 0);
   - contoh teks training diakhiri prompt jawaban yang benar. Untuk Qwen3.5, prompt itu berisi blok `<think>` kosong. Untuk Qwen2.5 tidak ada blok `<think>`.

   Laporkan perkiraan step dan waktu ke pengguna.
3. **Jalankan training di latar belakang.** Jangan menjalankannya di foreground, karena prosesnya bisa berjam-jam:
   ```bash
   mkdir -p OUT/M-D && setsid nohup python scripts/train_unsloth.py train --model M --dataset D --out OUT \
     --max-seq-len L > OUT/M-D/train.log 2>&1 < /dev/null &
   ```
4. **Pantau** sampai `stage` bernilai `done` atau `error`:
   ```bash
   cat OUT/M-D/status.json; tail -n 20 OUT/M-D/train.log; nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv
   ```
   - **Saat menunggu:** pakai perintah tunggu maksimal ±9 menit per panggilan, misalnya `sleep 300`, atau alat pemantau latar belakang jika tersedia. Jarak antar pengecekan 5–10 menit sudah cukup.
   - **Di awal training:** pastikan log berisi baris `cek masking`, yaitu bagian yang dilatih diawali jawaban, bukan pertanyaan. Untuk Qwen3.5 di T4, log juga harus berisi `Switching to float32`.
   - **Loss** biasanya turun di beberapa puluh step pertama. Jika loss `nan` atau naik terus, hentikan dan ikuti tabel di bawah.
   - **Laporan ke pengguna** cukup saat ada perubahan berarti: training mulai, kira-kira setiap 25% progres, error, atau selesai. Isi laporan: step, loss, dan ETA.
5. **Setelah selesai**, baca `status.json` bagian `result` dan `tests`, lalu periksa setiap `contoh-*.html`:
   - **File lengkap:** diakhiri `</html>`, dan `finished: true` berarti jawaban tidak terpotong batas token.
   - **Tidak ada library eksternal:** cek dengan `grep -c "<script src=\|<link .*href=\"http" contoh-*.html`, hasilnya seharusnya 0.
   - **Bahasa:** isi halaman memakai bahasa Indonesia.

   Laporkan hasilnya:
   - loss akhir dan lama training;
   - lokasi adapter;
   - penilaian singkat kedua website;
   - saran langkah berikutnya: bandingkan dengan model lain, coba data `mix` jika ada gejala lupa kemampuan umum, atau ekspor GGUF.

## Menangani masalah

| Gejala | Tindakan |
|---|---|
| `stage: error` dengan `CUDA out of memory` | Ulangi perintah `train` dengan `--max-seq-len 6144`. Training dilanjutkan dari checkpoint jika ada. Beri tahu pengguna bahwa 2 sampel web terpanjang ikut dibuang. Jika masih kehabisan memori, pakai 4096 dan laporkan sampel apa saja yang terbuang. |
| Loss `nan`, atau `grad_norm` `nan` terus-menerus | Hentikan proses. Jalankan `pip install --upgrade unsloth unsloth_zoo`, lalu ulangi. Jika tetap `nan`, laporkan ke pengguna, jangan diakali dengan mengganti presisi sendiri. |
| `ModuleNotFoundError`, atau error versi transformers/trl | Jalankan `pip install --upgrade unsloth`. Qwen3.5 butuh transformers v5. |
| Gagal mengunduh model (HTTP 429/5xx, timeout) | Tunggu sebentar lalu ulangi. Jika berulang, minta pengguna mengisi secret `HF_TOKEN` di Colab. |
| `status.json` tidak berubah lebih dari 15 menit dan prosesnya hilang (`pgrep -f train_unsloth` kosong) | Lihat akhir `train.log`. Jika tidak ada error, kemungkinan proses dimatikan. Jalankan ulang perintah `train`, dan training dilanjutkan dari checkpoint. |
| Runtime Colab di-reset (`/content/Dataset` hilang) | Kamu juga ikut hilang, jadi pengguna yang menjalankan ulang notebook. Checkpoint di Drive tetap aman dan perintah `train` akan melanjutkannya. |
| Pengguna meminta berhenti ("stop training") | Jalankan `pkill -f "train_unsloth.py train"`. Trainer berhenti; checkpoint terakhir tetap ada di Drive dan bisa dilanjutkan dengan perintah `train` yang sama. |
| `stage: error` jenis lain | Baca `hint` dan `traceback`. Perbaiki hanya jika penyebabnya jelas dan aman. Jika tidak, laporkan ke pengguna beserta ringkasan error-nya. |

## Batasan

- **Boleh tanpa bertanya:**
  - menjalankan `prepare`, `train`, dan `test`;
  - memantau proses;
  - melanjutkan dari checkpoint;
  - menurunkan `--max-seq-len` saat kehabisan memori;
  - memasang ulang atau meng-upgrade paket Python.
- **Tanya dulu sebelum:**
  - mengganti model, dataset, atau hyperparameter lain;
  - beralih ke data `mix`, karena sebagian sumbernya dibuat dengan model OpenAI dan ada implikasi lisensi (lihat README);
  - menghapus checkpoint atau hasil di Drive;
  - menjalankan `gguf`, karena butuh waktu sekitar 15–40 menit dan beberapa GB di Drive;
  - mengubah file di repo.
- **Jangan pernah:**
  - menampilkan, menyalin, atau menyimpan isi secret (`GITHUB_TOKEN`, `HF_TOKEN`) ke file atau log;
  - menjalankan SSH, tunnel (ngrok dan sejenisnya), remote desktop, atau web UI. Kebijakan Colab membatasi hal-hal ini, terutama di tier gratis.
  - mengubah isi dataset tanpa diminta.
