# Panduan Training Qwen3.5-4B di Google Colab

Panduan ini membawa Anda dari nol sampai punya model hasil fine-tuning yang bisa membuat website dari satu permintaan.
Tidak perlu memasang apa pun di komputer, dan Colab **tidak perlu dihubungkan ke GitHub**. Semua berjalan di browser.

## Daftar isi

1. [Gambaran singkat](#1-gambaran-singkat)
2. [Yang perlu disiapkan](#2-yang-perlu-disiapkan)
3. [Cara 1: upload notebook (disarankan)](#3-cara-1-upload-notebook-disarankan)
4. [Cara 2: dua sel saja](#4-cara-2-dua-sel-saja)
5. [Mode A: jalankan sendiri](#5-mode-a-jalankan-sendiri)
6. [Mode B: Claude yang mengontrol lewat terminal](#6-mode-b-claude-yang-mengontrol-lewat-terminal)
7. [Memantau progres](#7-memantau-progres)
8. [Jika sesi Colab putus](#8-jika-sesi-colab-putus)
9. [Menilai hasil](#9-menilai-hasil)
10. [Memakai model hasil training](#10-memakai-model-hasil-training)
11. [Mengatasi masalah](#11-mengatasi-masalah)
12. [Catatan hukum dan kebijakan](#12-catatan-hukum-dan-kebijakan)

---

## 1. Gambaran singkat

Seluruh proses training ada di **satu file**, [`scripts/train_unsloth.py`](../scripts/train_unsloth.py):
- membaca dan memeriksa data;
- melatih LoRA;
- menyimpan adapter;
- membuat dua website uji;
- ekspor GGUF (opsional).

Pengaturannya ada di blok `CONFIG` di awal file. Dataset `own` diunduh otomatis dari repo publik, atau dibaca dari
`train.jsonl` yang Anda upload sendiri.

Ada dua cara memakainya:

| | Cara 1: upload notebook | Cara 2: dua sel |
|---|---|---|
| Yang dilakukan | Upload `train_colab.ipynb` ke Colab, lalu jalankan selnya | Sel 1: instalasi. Sel 2: tempel seluruh script. |
| Mode A (jalankan sendiri) | Ya | Ya |
| Mode B (Claude mengontrol lewat terminal) | Ya | Tidak |
| Cocok untuk | Hampir semua kebutuhan | Cara tercepat untuk mencoba |

```
Cara 1 atau Cara 2 ─► pilih GPU ─► instalasi ─► jalankan training (Mode A atau Mode B)
                                                        │
                                                        ▼
                         Hasil di Google Drive: adapter LoRA + 2 contoh website
                                                        ▼
                                  (opsional) ekspor GGUF ─► dipakai di Ollama
```

**Perkiraan waktu training Qwen3.5-4B**, belum termasuk instalasi dan unduh model sekitar 10–15 menit:

| GPU | Data `own` (disarankan) | Data `mix` |
|---|---|---|
| T4 (gratis) | **±23 menit (terukur)** | ±1,5–3 jam |
| L4 (Colab berbayar) | ±10–20 menit | ±40–80 menit |

T4 lebih lambat karena tidak mendukung bf16. Qwen3.5 menghasilkan error numerik (NaN) pada fp16, jadi Unsloth otomatis
melatihnya dalam float32. Supaya muat di 16 GB VRAM T4, script otomatis memakai **QLoRA 4-bit** dan **`max_seq_len` 6144**.
Semua sampel dataset dijaga di bawah batas 6144, jadi seharusnya tidak ada yang terbuang. Output training menampilkan jumlah sampel yang dibuang, dan seharusnya 0. Akurasi 4-bit sedikit di bawah 16-bit.
GPU L4 tidak butuh kompromi ini.

## 2. Yang perlu disiapkan

- [ ] **Akun Google** untuk Colab dan Google Drive.
- [ ] **Ruang kosong di Google Drive minimal 2 GB**, atau minimal 6 GB jika ingin ekspor GGUF.
- [ ] **Browser di laptop atau PC.** Tab Colab harus tetap terbuka selama training, dan HP tidak disarankan.
- [ ] **Khusus mode B:** akun Claude Pro, Max, Team, atau Enterprise.
- [ ] **Salah satu file berikut,** sesuai cara yang dipilih. Unduh dari GitHub dengan membuka file, lalu klik ikon **Download raw file** (⤓) di kanan atas:
  - Cara 1: [`notebooks/train_colab.ipynb`](../notebooks/train_colab.ipynb)
  - Cara 2: [`scripts/train_unsloth.py`](../scripts/train_unsloth.py). Bisa juga dibuka sebagai teks di <https://raw.githubusercontent.com/PvzKing/Dataset/main/scripts/train_unsloth.py>, lalu salin semua isinya (Ctrl+A, Ctrl+C).
- [ ] **Opsional:** [`data/train.jsonl`](../data/train.jsonl). Tidak wajib, karena script mengunduhnya otomatis. Upload sendiri hanya jika unduhan otomatis gagal, atau jika Anda memakai versi dataset yang sudah diubah.

## 3. Cara 1: upload notebook (disarankan)

### 3.1 Upload notebook

1. Buka <https://colab.research.google.com>.
2. Di jendela yang muncul, pilih tab **Upload**. Jika jendelanya tidak muncul, pilih **File → Upload notebook**.
3. Pilih file `train_colab.ipynb` yang sudah diunduh. Notebook otomatis tersimpan di Drive Anda, di folder *Colab Notebooks*.

### 3.2 Pilih GPU

1. Pilih menu **Runtime → Change runtime type**.
2. Pada *Hardware accelerator*, pilih **T4 GPU** (gratis) atau **L4 GPU** (berbayar, lebih cepat), lalu **Save**.

### 3.3 Jalankan sel 1–4

Klik tombol ▶ di kiri setiap sel, dan tunggu sampai selesai sebelum lanjut ke sel berikutnya.

- **Sel 1 (Cek GPU)** harus menampilkan `Tesla T4` atau `NVIDIA L4`. Jika muncul error, ulangi langkah 3.2.
- **Sel 2 (Instalasi)** butuh 2–4 menit dan tidak menampilkan output. Jika muncul tombol **Restart session**, klik tombolnya lalu lanjut ke sel 3 tanpa mengulang sel 2.
- **Sel 3 (Mount Google Drive):** klik **Connect to Google Drive**, pilih akun, lalu **Allow**. Hasilnya `Mounted at /content/drive`.
- **Sel 4 (Script training)** hanya menyimpan script ke `/content/train_unsloth.py`, belum menjalankan training. Untuk percobaan pertama, biarkan `CONFIG` apa adanya. Hasilnya `Writing /content/train_unsloth.py`.

Persiapan selesai. Lanjut ke [mode A](#5-mode-a-jalankan-sendiri) atau [mode B](#6-mode-b-claude-yang-mengontrol-lewat-terminal).

## 4. Cara 2: dua sel saja

Cara ini hanya mendukung mode A.

1. Buka <https://colab.research.google.com>, lalu klik **New notebook**.
2. Pilih GPU seperti di langkah 3.2.
3. **Sel 1, instalasi.** Tempel kode berikut lalu jalankan. Jika diminta *Restart session*, klik tombolnya.
   ```
   !pip install --upgrade unsloth
   ```
4. **Sel 2, training.** Klik **+ Code** untuk membuat sel baru, lalu tempel **seluruh isi** `train_unsloth.py`.
   - Ubah `CONFIG` di bagian atas jika perlu.
   - Jalankan sel. Colab meminta izin Google Drive: pilih **Connect to Google Drive → Allow**.
   - Training lalu berjalan sampai selesai di sel yang sama. Output-nya sama seperti mode A di bagian 5.
5. **Tahap lain:** untuk uji ulang adapter atau ekspor GGUF, ubah `"command": "train"` di `CONFIG` menjadi `"test"` atau `"gguf"`, lalu jalankan sel 2 lagi.

## 5. Mode A: jalankan sendiri

1. **Jalankan training.** Di Cara 1, jalankan sel **Mode A** (`!python /content/train_unsloth.py train`). Di Cara 2, cukup jalankan sel 2. Output yang akan muncul berurutan:
   - Di T4: `GPU kecil tanpa bf16 terdeteksi ... (load_in_4bit=True, max_seq_len=6144)`. Ini pengaturan hemat memori otomatis.
   - `folder hasil: /content/drive/MyDrive/finetune-id/qwen3.5-4b-own-4bit`. Di GPU yang mendukung bf16, nama foldernya tanpa `-4bit`.
   - `data valid: 62 sampel`. Jika belum ada `train.jsonl`, akan muncul `mengunduh ...` dulu.
   - Ringkasan data: jumlah sampel, jumlah step, dan perkiraan waktu.
   - `cek masking: ...`: bagian yang dilatih harus diawali jawaban, bukan pertanyaan.
   - Progress bar training dengan ETA (sisa waktu). Baris `loss` muncul setiap step.
   - Setelah training, model menulis dua website uji. Teksnya muncul bertahap, dan ini butuh beberapa menit.
2. **Lihat hasil.** Khusus Cara 1, jalankan sel **Lihat hasil** untuk menampilkan status, loss akhir, dan kedua website langsung di notebook. Di Cara 2, buka file hasilnya di Google Drive (lihat bagian 7).

## 6. Mode B: Claude yang mengontrol lewat terminal

Mode ini hanya tersedia di Cara 1. Claude Code berjalan **di terminal VM Colab**, dan seluruh kendali dilakukan lewat
terminal itu. Anda memberi perintah dan membaca laporan Claude di terminal yang sama, di dalam tab Colab.

Claude akan:
- menjalankan training di latar belakang;
- membaca log dan `status.json`;
- memantau GPU;
- menangani masalah umum: kehabisan memori, paket bermasalah, proses mati;
- memeriksa website hasil uji;
- melapor kepada Anda.

Aturan kerjanya ada di [`RUNBOOK_CLAUDE.md`](RUNBOOK_CLAUDE.md). Sel B1 menyalinnya ke `/content/CLAUDE.md` supaya
dibaca Claude secara otomatis. Claude akan bertanya dulu sebelum mengambil keputusan penting, misalnya mengganti data
atau menghapus checkpoint.

### 6.1 Siapkan dan buka terminal

1. Pastikan sel 1–4 sudah dijalankan.
2. **Jalankan sel B1.** Sel ini menyimpan aturan kerja Claude ke `/content/CLAUDE.md`.
3. **Jalankan sel B2.** Sel ini memasang Claude Code dan membuka jendela terminal hitam di bawahnya.
4. **Klik di dalam terminal**, ketik perintah berikut, lalu tekan Enter:
   ```
   cd /content && export PATH="$HOME/.local/bin:$PATH" && claude
   ```
5. **Login.** Ini hanya perlu dilakukan sekali per sesi Colab.
   1. Ikuti pertanyaan awal (misalnya pilihan tema), lalu pilih login dengan **akun Claude** (langganan).
   2. Muncul link panjang. Salin, buka di tab baru, login, lalu klik **Authorize**.
   3. Salin kode yang muncul, kembali ke terminal, dan tempel dengan **Ctrl+Shift+V** atau klik kanan → Paste. Tekan Enter.
   4. Jika ditanya *Do you trust the files in this folder?*, pilih **Yes**.

### 6.2 Beri tugas dan izin

1. **Beri tugas.** Ketik atau tempel kalimat ini di terminal, lalu tekan Enter:
   ```
   Latih model sesuai CONFIG di train_unsloth.py mengikuti CLAUDE.md, pantau sampai selesai, lalu laporkan hasilnya.
   ```
2. **Izinkan perintah.** Setiap kali Claude ingin menjalankan perintah, terminal menampilkan pilihan.
   - Untuk perintah aman seperti `python /content/train_unsloth.py`, `cat`, `tail`, `nvidia-smi`, dan `sleep`, pilih **Yes, and don't ask again** dengan tombol panah, lalu Enter. Setelah itu Claude bisa memantau sendiri tanpa bertanya lagi.
   - Untuk perintah yang terlihat tidak biasa, baca dulu sebelum menyetujui. Jika ragu, pilih **No** dan tanyakan alasannya ke Claude.
3. **Tunggu.** Biarkan tab Colab tetap terbuka. Claude melapor di terminal saat training mulai, kira-kira setiap 25% progres, saat ada error, dan saat selesai.
4. **Selesai.** Claude akan melaporkan:
   - loss akhir dan lama training;
   - lokasi adapter;
   - penilaian kedua website uji;
   - saran langkah berikutnya.

### 6.3 Berinteraksi dengan Claude di terminal

| Ingin | Ketik / tekan |
|---|---|
| Menanyakan progres | `gimana progresnya?` |
| Menanyakan sesuatu | `kenapa loss-nya naik?`, `berapa lama lagi?` |
| Menghentikan training | `stop training` (Claude menghentikan prosesnya; checkpoint tetap aman) |
| Menyela Claude yang sedang bekerja | **Esc** |
| Keluar dari Claude | `/exit`, atau **Ctrl+C** dua kali |
| Membuka lagi percakapan terakhir | `cd /content && claude --continue` |
| Menjalankan langkah berikutnya | `uji ulang adapter`, `ekspor GGUF`, `latih juga model qwen2.5-coder-7b untuk pembanding` |

Catatan:
- **Training tetap berjalan meski Claude berhenti.** Training berjalan di latar belakang, jadi tetap jalan walaupun Anda keluar dari Claude, terminal tertutup, atau output sel terhapus. Untuk kembali memantau, jalankan ulang sel B2, lalu `claude --continue`.
- **Proses tidak tampil di layar.** Terminal hanya menampilkan percakapan dengan Claude, bukan progress bar. Untuk melihat angka mentahnya, minta `tampilkan status.json` atau buka `status.json` di Google Drive.

## 7. Memantau progres

Semua hasil ada di Google Drive, di folder `finetune-id/<model>-<dataset>/`, misalnya `finetune-id/qwen3.5-4b-own-4bit/` di T4:

| File/folder | Isi |
|---|---|
| `status.json` | Kondisi terkini. Bisa dibuka dari Google Drive di HP untuk mengecek tanpa membuka Colab. |
| `checkpoints/` | Titik simpan otomatis setiap 10 step |
| `arsip/<tanggal-jam>/` | Hasil training sebelumnya, dipindahkan otomatis saat dataset atau pengaturan berubah |
| `lora-adapter/` | Adapter hasil training |
| `contoh-bengkel.html`, `contoh-absensi.html` | Website buatan model. Unduh lalu buka di browser. |
| `contoh-*.md` | Jawaban lengkap model, termasuk penjelasannya |

Jika tidak ada `train.jsonl` di `/content`, versi terbaru diunduh ulang ke `finetune-id/` setiap kali training dijalankan. Di mode B, log lengkap ada di `/content/train.log`.

Arti isi `status.json`:

| Kolom | Arti |
|---|---|
| `stage` | `loading` → `prepared` → `training` → `saving` → `trained` → `testing` → `done`. Nilainya `error` jika gagal. |
| `step`, `max_steps` | Progres training, misalnya step 12 dari 24 |
| `loss` | Nilai error model. Seharusnya turun, misalnya dari ±1,5 ke di bawah 1. |
| `eta_min` | Perkiraan sisa menit |
| `hint` | Saran perbaikan jika `stage` bernilai `error` |

## 8. Jika sesi Colab putus

Checkpoint tersimpan di Drive, jadi progres tidak hilang. Paling banyak 10 step terakhir yang perlu diulang.

1. Klik **Reconnect** atau buka ulang notebook dari Drive (folder *Colab Notebooks*), lalu pilih GPU lagi.
2. Ulangi persiapannya. VM-nya baru, jadi instalasi tetap perlu diulang:
   - **Cara 1:** jalankan ulang sel 1–4.
   - **Cara 2:** jalankan ulang sel 1, lalu lanjut ke langkah 3.
3. Jalankan training yang sama:
   - **Mode A atau Cara 2:** jalankan ulang sel training.
   - **Mode B:** jalankan ulang sel B1 dan B2, lalu di terminal jalankan `cd /content && export PATH="$HOME/.local/bin:$PATH" && claude` dan login lagi. Setelah itu ketik `lanjutkan training yang terputus`.
4. Di output akan muncul `mulai dari .../checkpoint-XX`. Itu tanda training dilanjutkan dari checkpoint terakhir.

Tips supaya sesi tidak cepat putus:
- **Tab dan layar:** tetap buka tab Colab, dan jangan biarkan laptop sleep.
- **Batas tier gratis:** sesi tier gratis maksimal sekitar 12 jam, dan GPU kadang tidak tersedia di jam sibuk. Jika muncul *Cannot connect to GPU backend*, coba lagi beberapa jam kemudian.
- **Data `mix` di T4:** kemungkinan butuh 2 sesi. Itu normal karena training dilanjutkan dari checkpoint.

**Training ulang setelah dataset diperbarui.** Jalankan perintah training yang sama. Checkpoint hanya dilanjutkan jika isi dataset dan pengaturannya persis sama. Jika berbeda, hasil lama (checkpoint, adapter, dan website uji) dipindah ke `arsip/<tanggal-jam>/`, lalu training dimulai dari awal. Output menampilkan `hasil lama dipindah ke ...` dan `mulai dari awal`. Website uji lama tetap ada di arsip, jadi bisa dibandingkan dengan hasil baru.

## 9. Menilai hasil

Unduh `contoh-bengkel.html` dan `contoh-absensi.html` dari Drive, buka di browser, lalu cek:

- [ ] Halaman tampil utuh, tidak terpotong di tengah. Jika terpotong, `status.json` menunjukkan `finished: false`.
- [ ] Tombol dan form berfungsi. Validasi form muncul, dan data absensi tersimpan setelah halaman di-refresh.
- [ ] Tampilan rapi di layar HP. Di Chrome, tekan F12 lalu ikon HP, dan pilih lebar 375 px.
- [ ] Tidak ada error di Console (F12 → Console).
- [ ] Bahasa Indonesia natural, dan penjelasan setelah kode ringkas.

**Membandingkan dengan model lain.**
1. Di `CONFIG`, ganti `"model": "qwen2.5-coder-7b"`.
2. Jalankan ulang sel script dan training.
3. Hasilnya tersimpan di folder terpisah (`qwen2.5-coder-7b-own`), dengan prompt uji yang sama, jadi bisa dibandingkan langsung.

**Kapan beralih ke data `mix`.** Coba tanyakan hal umum ke model, misalnya "jelaskan fotosintesis" atau "apa itu inflasi". Beralih ke `mix` jika:
- model selalu menjawab dengan HTML;
- jawaban umumnya memburuk.

Caranya, ganti `"dataset": "mix"` di `CONFIG`. Script akan mengunduh `mix_general.py` dari repo lalu membuat data campuran. Dengan Claude, cukup katakan `latih ulang dengan data mix`, dan Claude akan mengingatkan catatan lisensinya.

## 10. Memakai model hasil training

### Di Ollama (laptop/PC)

1. **Buat file GGUF.** Butuh ±15–40 menit.
   - **Cara 1:** jalankan sel **Ekspor GGUF**.
   - **Cara 2:** ganti `"command": "gguf"` di `CONFIG`, lalu jalankan sel 2 lagi.
2. Unduh folder `gguf/` dari Drive. Di dalamnya ada file `.gguf`, sekitar 2,5–3 GB untuk 4B.
3. Pasang [Ollama](https://ollama.com). Pastikan versi terbaru, karena Qwen3.5 butuh versi baru.
4. Jika di folder `gguf/` sudah ada `Modelfile`, pakai file itu. Jika tidak, buat file bernama `Modelfile` di folder yang sama:
   ```
   FROM ./nama-file.gguf
   PARAMETER temperature 0.7
   PARAMETER top_p 0.8
   PARAMETER top_k 20
   ```
5. Jalankan:
   ```bash
   ollama create web-id -f Modelfile
   ollama run web-id "Buatkan landing page satu file HTML untuk toko roti"
   ```

### Di Colab lagi (tanpa GGUF)

Untuk menguji ulang adapter dengan prompt uji:
- **Cara 1:** tambahkan sel baru berisi `!python /content/train_unsloth.py test`.
- **Cara 2:** ganti `"command": "test"` di `CONFIG`.

Untuk prompt sendiri, ubah `TEST_PROMPTS` di script, atau minta Claude melakukannya.

## 11. Mengatasi masalah

| Pesan / gejala | Penyebab | Solusi |
|---|---|---|
| `CUDA out of memory` | VRAM T4 tidak cukup: Qwen3.5 dilatih dalam float32 di T4 | Di T4, script otomatis memakai QLoRA 4-bit dan `max_seq_len` 6144. Kombinasi ini sudah terbukti jalan. Jika Anda mengubah pengaturan itu dan error muncul, kembalikan `"load_in_4bit"` dan `"max_seq_len"` ke `None`, atau jalankan dengan `--load-in-4bit --max-seq-len 6144`. **Tanpa kompromi:** pakai GPU L4 (Colab berbayar), yang bisa memakai 16-bit dengan konteks 8192. |
| `Cannot connect to GPU backend` | Kuota GPU gratis habis atau sedang penuh | Coba lagi beberapa jam kemudian, atau pakai Colab berbayar |
| `loss` bernilai `nan` | Masalah presisi | Jalankan ulang sel instalasi untuk memasang Unsloth terbaru, lalu ulangi training. Untuk Qwen3.5 di T4, log harus berisi `Switching to float32`. |
| `ModuleNotFoundError: unsloth` | Sel instalasi belum dijalankan setelah sesi baru | Jalankan sel instalasi |
| `does not support Qwen3.5` | Versi transformers terlalu lama | Jalankan ulang sel instalasi, lalu *Runtime → Restart session* |
| `Google Drive belum ter-mount` | Sel mount Drive belum dijalankan | Cara 1: jalankan sel 3. Cara 2: jalankan ulang sel 2 dan pilih **Allow**. |
| Gagal mengunduh `train.jsonl` | Jaringan atau GitHub sedang bermasalah | Unduh `data/train.jsonl` dari GitHub, lalu upload lewat panel 📁 *Files* di kiri (ke `/content`). Ulangi training. |
| `masalah di ... train.jsonl` | Isi dataset tidak valid | Baca daftar masalah yang ditampilkan dan perbaiki barisnya. Jika memakai file dari repo, unduh ulang. |
| Download model lambat atau error 429 | Batas unduhan Hugging Face | Tunggu lalu ulangi. Bisa juga buat token di huggingface.co (Settings → Access Tokens) dan simpan sebagai secret `HF_TOKEN` di panel 🔑 Colab. |
| Terminal mode B kosong atau hilang | Output sel terhapus | Jalankan ulang sel B2. Training yang sudah berjalan di latar belakang tidak berhenti. |
| Claude: `command not found` | PATH belum diatur | Jalankan `export PATH="$HOME/.local/bin:$PATH"` |
| Website hasil uji terpotong | Jawaban melebihi `max_new_tokens` | Normal jika jarang terjadi. Set `"max_new_tokens": 8000` lalu uji ulang. |

## 12. Catatan hukum dan kebijakan

- **Kebijakan Google Colab.**
  - Menurut [FAQ Colab](https://research.google.com/colaboratory/faq.html), tier gratis membatasi *remote control* (SSH, remote desktop), bekerja terutama lewat web UI di luar notebook, dan worker komputasi terdistribusi. Runtime yang melakukannya bisa dihentikan tanpa peringatan.
  - Mode B berjalan lewat terminal di dalam tab notebook, jadi tetap bekerja di dalam UI notebook. Jangan menambahkan SSH, tunnel (ngrok dan sejenisnya), atau akses jarak jauh lain ke VM Colab.
  - Proxy, file hosting, dan penambangan kripto dilarang di semua tier.
- **Claude Code** memakai akun Claude Anda dan tunduk pada ketentuan layanan Anthropic. File dan log yang dibaca Claude dikirim ke Anthropic untuk diproses. Jangan menaruh data rahasia di folder yang dibaca Claude.
- **Kerahasiaan klien dan data pribadi.** Jika Anda menambah sampel dari pekerjaan nyata, misalnya dokumen perkara atau korespondensi klien:
  - Advokat wajib merahasiakan segala sesuatu yang diketahui atau diperoleh dari kliennya karena hubungan profesinya (Pasal 19 ayat (1) UU No. 18 Tahun 2003 tentang Advokat).
  - Data pribadi tunduk pada UU No. 27 Tahun 2022 tentang Pelindungan Data Pribadi. Pemrosesan butuh dasar yang sah (Pasal 20), dan pengendali data wajib menjaga kerahasiaan serta keamanannya (Pasal 35–36).
  - Mengunggah data seperti itu ke Colab, Hugging Face, atau Claude, atau memasukkannya ke dataset yang dibagikan, berisiko melanggar kedua ketentuan tersebut.
  - Anonimkan secara menyeluruh atau buat contoh fiktif. Sampel di dataset ini seluruhnya fiktif.
- **Lisensi model.**
  - Qwen3.5-4B dan Qwen2.5-Coder-7B-Instruct berlisensi Apache 2.0.
  - Adapter dan GGUF hasil training boleh dipakai dan dibagikan, termasuk untuk komersial, dengan syarat menyertakan teks lisensi, mempertahankan pemberitahuan hak cipta, dan menandai bahwa model telah diubah (Pasal 4 Apache License 2.0).
- **Data `mix`.** Sebagian sumbernya (Magicoder dan UltraChat) dibuat dengan model OpenAI. Untuk pemakaian komersial, pakai `own` saja, atau buat data campuran yang hanya berisi Aya (ditulis manusia) dengan `"mix_args": "--code 0 --chat 0"` di `CONFIG`. Penjelasan lengkapnya ada di README.
