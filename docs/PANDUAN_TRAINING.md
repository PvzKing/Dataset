# Panduan Training Qwen3.5-4B di Google Colab

Panduan ini membawa Anda dari nol sampai punya model hasil fine-tuning yang bisa membuat website dari satu permintaan.
Tidak perlu memasang apa pun di komputer. Semua berjalan di browser.

## Daftar isi

1. [Gambaran singkat](#1-gambaran-singkat)
2. [Yang perlu disiapkan](#2-yang-perlu-disiapkan)
3. [Langkah persiapan (wajib)](#3-langkah-persiapan-wajib)
4. [Mode A: jalankan sendiri](#4-mode-a-jalankan-sendiri)
5. [Mode B: Claude yang mengontrol](#5-mode-b-claude-yang-mengontrol)
6. [Memantau progres](#6-memantau-progres)
7. [Jika sesi Colab putus](#7-jika-sesi-colab-putus)
8. [Menilai hasil](#8-menilai-hasil)
9. [Memakai model hasil training](#9-memakai-model-hasil-training)
10. [Mengatasi masalah](#10-mengatasi-masalah)
11. [Catatan hukum dan kebijakan](#11-catatan-hukum-dan-kebijakan)

---

## 1. Gambaran singkat

```
Buka notebook di Colab ─► pilih GPU ─► jalankan sel 1–4 (persiapan)
                                          │
                     ┌────────────────────┴────────────────────┐
                     ▼                                         ▼
            Mode A: jalankan sendiri                Mode B: Claude mengontrol
            satu sel, tunggu sampai selesai          Claude menjalankan, memantau,
                                                    memperbaiki, dan melapor
                     └────────────────────┬────────────────────┘
                                          ▼
                      Hasil di Google Drive: adapter LoRA + 2 contoh website
                                          ▼
                       (opsional) ekspor GGUF ─► dipakai di Ollama
```

| | Mode A | Mode B |
|---|---|---|
| Kesulitan | Paling mudah | Mudah, ada langkah login Claude |
| Perlu akun Claude berbayar | Tidak | Ya (Pro, Max, Team, Enterprise, atau API) |
| Jika ada error | Anda membaca pesannya sendiri | Claude menganalisis dan memperbaikinya |
| Cocok untuk | Percobaan pertama | Training lama (`mix`) atau jika ingin ditemani |

**Perkiraan waktu Qwen3.5-4B**, belum termasuk persiapan sekitar 10–15 menit:

| GPU | Data `own` (disarankan) | Data `mix` |
|---|---|---|
| T4 (gratis) | ±30–90 menit | ±2–5 jam |
| L4 (Colab berbayar) | ±10–20 menit | ±40–80 menit |

T4 lebih lambat karena tidak mendukung bf16. Qwen3.5 menghasilkan error numerik (NaN) pada fp16, jadi Unsloth otomatis
melatihnya dalam float32.

## 2. Yang perlu disiapkan

- [ ] **Akun Google** untuk Colab dan Google Drive.
- [ ] **Ruang kosong di Google Drive minimal 2 GB**, atau minimal 6 GB jika ingin ekspor GGUF.
- [ ] **Browser di laptop atau PC.** Tab Colab harus tetap terbuka selama training, dan HP tidak disarankan.
- [ ] **Khusus mode B:** akun Claude Pro, Max, Team, atau Enterprise.
- [ ] **Khusus repo privat:** token GitHub. Cara membuatnya ada di langkah 3.4.

## 3. Langkah persiapan (wajib)

### 3.1 Buka notebook

1. Buka <https://colab.research.google.com>.
2. Pilih menu **File → Open notebook**, lalu tab **GitHub**.
3. Ketik `PvzKing/Dataset`, tekan Enter, lalu pilih `notebooks/train_colab.ipynb`.
   - Jika repo privat, centang *Include private repos* dan izinkan akses GitHub.
4. Supaya perubahan Anda tersimpan, pilih **File → Save a copy in Drive**. Langkah ini opsional.

### 3.2 Pilih GPU

1. Pilih menu **Runtime → Change runtime type**.
2. Pada *Hardware accelerator*, pilih **T4 GPU** (gratis) atau **L4 GPU** (berbayar, lebih cepat), lalu **Save**.

### 3.3 Jalankan sel 1–3

Klik tombol ▶ di kiri setiap sel, dan tunggu sampai selesai sebelum lanjut ke sel berikutnya.

- **Sel 1 (Cek GPU)** harus menampilkan `Tesla T4` atau `NVIDIA L4`. Jika muncul error, ulangi langkah 3.2.
- **Sel 2 (Instal Unsloth)** butuh 2–4 menit dan tidak menampilkan output. Jika muncul tombol **Restart session**, klik tombolnya lalu lanjut ke sel 3 tanpa mengulang sel 2.
- **Sel 3 (Konfigurasi)** biarkan apa adanya untuk percobaan pertama.

### 3.4 Jalankan sel 4 (Drive dan repo)

1. Muncul jendela izin Google Drive. Klik **Connect to Google Drive**, pilih akun, lalu **Allow**.
2. **Khusus repo privat**, lakukan ini sebelum menjalankan sel:
   1. Buka GitHub, lalu **Settings → Developer settings → Personal access tokens → Fine-grained tokens → Generate new token**.
   2. Pada *Repository access*, pilih **Only select repositories → PvzKing/Dataset**.
   3. Pada *Permissions*, set **Contents: Read-only**, lalu **Generate token** dan salin token-nya.
   4. Di Colab, klik ikon 🔑 (*Secrets*) di panel kiri, lalu **Add new secret** dengan nama `GITHUB_TOKEN`. Tempel token di kolom value dan aktifkan **Notebook access**.
3. Hasil yang diharapkan: `repo siap, commit ...` dan `hasil akan disimpan di /content/drive/MyDrive/finetune-id/qwen3.5-4b-own`.

Persiapan selesai. Lanjut ke **mode A** atau **mode B**.

## 4. Mode A: jalankan sendiri

1. Jalankan sel **Mode A** (`!python scripts/train_unsloth.py train ...`). Output yang akan muncul berurutan:
   - `OK, semua sampel valid.`: data lolos validasi.
   - Ringkasan data: jumlah sampel, jumlah step, dan perkiraan waktu.
   - `cek masking: ...`: bagian yang dilatih harus diawali jawaban, bukan pertanyaan.
   - Progress bar training dengan ETA (sisa waktu). Baris `loss` muncul setiap step.
   - Setelah training, model menulis dua website uji. Teksnya muncul bertahap, dan ini butuh beberapa menit.
2. Jalankan sel **Lihat hasil** untuk melihat status, loss akhir, dan kedua website langsung di notebook.

## 5. Mode B: Claude yang mengontrol

Claude Code berjalan **di terminal VM Colab**, dan seluruh kendali dilakukan lewat terminal itu. Anda memberi
perintah dan membaca laporan Claude di terminal yang sama, di dalam tab Colab.

Claude akan:
- menjalankan training di latar belakang;
- membaca log dan `status.json`;
- memantau GPU;
- menangani masalah umum: kehabisan memori, paket bermasalah, proses mati;
- memeriksa website hasil uji;
- melapor kepada Anda.

Aturan kerjanya ada di [`RUNBOOK_CLAUDE.md`](RUNBOOK_CLAUDE.md). Claude akan bertanya dulu sebelum mengambil keputusan
penting, misalnya mengganti data atau menghapus checkpoint.

### 5.1 Buka terminal dan jalankan Claude

1. **Jalankan sel Mode B.** Sel ini memasang Claude Code dan membuka jendela terminal hitam di bawahnya.
2. **Klik di dalam terminal**, ketik perintah berikut, lalu tekan Enter:
   ```
   cd /content/Dataset && export PATH="$HOME/.local/bin:$PATH" && claude
   ```
3. **Login.** Ini hanya perlu dilakukan sekali per sesi Colab.
   1. Ikuti pertanyaan awal (misalnya pilihan tema), lalu pilih login dengan **akun Claude** (langganan).
   2. Muncul link panjang. Salin, buka di tab baru, login, lalu klik **Authorize**.
   3. Salin kode yang muncul, kembali ke terminal, dan tempel dengan **Ctrl+Shift+V** atau klik kanan → Paste. Tekan Enter.
   4. Jika ditanya *Do you trust the files in this folder?*, pilih **Yes**.

### 5.2 Beri tugas dan izin

1. **Beri tugas.** Ketik atau tempel kalimat ini di terminal, lalu tekan Enter:
   ```
   Latih model sesuai run_config.json mengikuti docs/RUNBOOK_CLAUDE.md, pantau sampai selesai, lalu laporkan hasilnya.
   ```
2. **Izinkan perintah.** Setiap kali Claude ingin menjalankan perintah, terminal menampilkan pilihan.
   - Untuk perintah aman seperti `python scripts/train_unsloth.py`, `cat`, `tail`, `nvidia-smi`, dan `sleep`, pilih **Yes, and don't ask again** dengan tombol panah, lalu Enter. Setelah itu Claude bisa memantau sendiri tanpa bertanya lagi.
   - Untuk perintah yang terlihat tidak biasa, baca dulu sebelum menyetujui. Jika ragu, pilih **No** dan tanyakan alasannya ke Claude.
3. **Tunggu.** Biarkan tab Colab tetap terbuka. Claude melapor di terminal saat training mulai, kira-kira setiap 25% progres, saat ada error, dan saat selesai.
4. **Selesai.** Claude akan melaporkan:
   - loss akhir dan lama training;
   - lokasi adapter;
   - penilaian kedua website uji;
   - saran langkah berikutnya.

### 5.3 Berinteraksi dengan Claude di terminal

| Ingin | Ketik / tekan |
|---|---|
| Menanyakan progres | `gimana progresnya?` |
| Menanyakan sesuatu | `kenapa loss-nya naik?`, `berapa lama lagi?` |
| Menghentikan training | `stop training` (Claude menghentikan prosesnya; checkpoint tetap aman) |
| Menyela Claude yang sedang bekerja | **Esc** |
| Keluar dari Claude | `/exit`, atau **Ctrl+C** dua kali |
| Membuka lagi percakapan terakhir | `claude --continue` (di folder `/content/Dataset`) |
| Menjalankan langkah berikutnya | `uji ulang adapter`, `ekspor GGUF`, `latih juga model qwen2.5-coder-7b untuk pembanding` |

Catatan:
- **Training tetap berjalan meski Claude berhenti.** Training berjalan di latar belakang, jadi tetap jalan walaupun Anda keluar dari Claude, terminal tertutup, atau output sel terhapus. Untuk melanjutkan pemantauan, jalankan ulang sel Mode B, lalu `claude --continue`.
- **Proses tidak tampil di layar.** Terminal hanya menampilkan percakapan dengan Claude, bukan progress bar. Untuk melihat angka mentahnya, minta `tampilkan status.json` atau buka `status.json` di Google Drive.

## 6. Memantau progres

Semua hasil ada di Google Drive, di folder `finetune-id/<model>-<dataset>/`:

| File/folder | Isi |
|---|---|
| `status.json` | Kondisi terkini. Buka dari Google Drive di HP untuk mengecek tanpa membuka Colab. |
| `train.log` | Log lengkap (mode B) |
| `checkpoints/` | Titik simpan otomatis setiap 10 step |
| `lora-adapter/` | Adapter hasil training |
| `contoh-bengkel.html`, `contoh-absensi.html` | Website buatan model. Unduh lalu buka di browser. |
| `contoh-*.md` | Jawaban lengkap model, termasuk penjelasannya |

Arti isi `status.json`:

| Kolom | Arti |
|---|---|
| `stage` | `loading` → `prepared` → `training` → `saving` → `trained` → `testing` → `done`. Nilainya `error` jika gagal. |
| `step`, `max_steps` | Progres training, misalnya step 12 dari 24 |
| `loss` | Nilai error model. Seharusnya turun, misalnya dari ±1,5 ke di bawah 1. |
| `eta_min` | Perkiraan sisa menit |
| `hint` | Saran perbaikan jika `stage` bernilai `error` |

## 7. Jika sesi Colab putus

Checkpoint tersimpan di Drive, jadi progres tidak hilang. Paling banyak 10 step terakhir yang perlu diulang.

1. Klik **Reconnect** atau buka ulang notebook, lalu pilih GPU lagi.
2. Jalankan ulang sel **1–4**. Sel 2 tetap perlu dijalankan karena VM-nya baru.
3. Jalankan mode yang sama:
   - **Mode A:** jalankan ulang sel training.
   - **Mode B:** jalankan ulang sel Mode B, lalu di terminal jalankan `cd /content/Dataset && export PATH="$HOME/.local/bin:$PATH" && claude` dan login lagi (VM-nya baru). Setelah itu ketik `lanjutkan training yang terputus`.
4. Di output akan muncul `mulai dari .../checkpoint-XX`. Itu tanda training dilanjutkan dari checkpoint terakhir.

Tips supaya sesi tidak cepat putus:
- **Tab dan layar:** tetap buka tab Colab, dan jangan biarkan laptop sleep.
- **Batas tier gratis:** sesi tier gratis maksimal sekitar 12 jam, dan GPU kadang tidak tersedia di jam sibuk. Jika muncul *Cannot connect to GPU backend*, coba lagi beberapa jam kemudian.
- **Data `mix` di T4:** kemungkinan butuh 2 sesi. Itu normal karena training dilanjutkan dari checkpoint.

## 8. Menilai hasil

Unduh `contoh-bengkel.html` dan `contoh-absensi.html` dari Drive, buka di browser, lalu cek:

- [ ] Halaman tampil utuh, tidak terpotong di tengah. Jika terpotong, `status.json` menunjukkan `finished: false`.
- [ ] Tombol dan form berfungsi. Validasi form muncul, dan data absensi tersimpan setelah halaman di-refresh.
- [ ] Tampilan rapi di layar HP. Di Chrome, tekan F12 lalu ikon HP, dan pilih lebar 375 px.
- [ ] Tidak ada error di Console (F12 → Console).
- [ ] Bahasa Indonesia natural, dan penjelasan setelah kode ringkas.

**Membandingkan dengan model lain.**
1. Di sel 3, ganti `MODEL = "qwen2.5-coder-7b"`.
2. Jalankan ulang sel 3–4 dan mode yang sama.
3. Hasilnya tersimpan di folder terpisah, dengan prompt uji yang sama, jadi bisa dibandingkan langsung.

**Kapan beralih ke data `mix`.** Coba tanyakan hal umum ke model, misalnya "jelaskan fotosintesis" atau "apa itu inflasi". Beralih ke `mix` jika:
- model selalu menjawab dengan HTML;
- jawaban umumnya memburuk.

Dengan Claude, cukup katakan `latih ulang dengan data mix`, dan Claude akan mengingatkan catatan lisensinya.

## 9. Memakai model hasil training

### Di Ollama (laptop/PC)

1. Di notebook, jalankan sel **Ekspor GGUF**. Butuh ±15–40 menit.
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

Untuk menguji ulang adapter dengan prompt uji, tambahkan sel baru setelah sel 4 berisi:

```
!python scripts/train_unsloth.py test {ARGS}
```

Untuk prompt sendiri, ubah `TEST_PROMPTS` di `scripts/train_unsloth.py`, atau minta Claude melakukannya.

## 10. Mengatasi masalah

| Pesan / gejala | Penyebab | Solusi |
|---|---|---|
| `CUDA out of memory` | VRAM tidak cukup untuk sampel terpanjang | Di sel 3 set `MAX_SEQ_LEN = 6144`, lalu jalankan ulang sel 3–4 dan training. 2 sampel web terpanjang akan dibuang. |
| `Cannot connect to GPU backend` | Kuota GPU gratis habis atau sedang penuh | Coba lagi beberapa jam kemudian, atau pakai Colab berbayar |
| `loss` bernilai `nan` | Masalah presisi | Jalankan ulang sel 2 untuk memasang Unsloth terbaru, lalu ulangi training. Untuk Qwen3.5 di T4, log harus berisi `Switching to float32`. |
| `ModuleNotFoundError: unsloth` | Sel 2 belum dijalankan setelah sesi baru | Jalankan sel 2 |
| `does not support Qwen3.5` | Versi transformers terlalu lama | Jalankan ulang sel 2, lalu *Runtime → Restart session* |
| `perintah gagal: git clone` | Repo privat tanpa token, atau token salah | Ulangi langkah 3.4 bagian repo privat |
| Mount Drive gagal | Izin tidak diberikan | Jalankan ulang sel 4 dan pilih **Allow** |
| Download model lambat atau error 429 | Batas unduhan Hugging Face | Tunggu lalu ulangi. Bisa juga buat token di huggingface.co (Settings → Access Tokens) dan simpan sebagai secret `HF_TOKEN`. |
| Terminal mode B kosong atau hilang | Output sel terhapus | Jalankan ulang sel Mode B. Training yang sudah berjalan di latar belakang tidak berhenti. |
| Claude: `command not found` | PATH belum diatur | Jalankan `export PATH="$HOME/.local/bin:$PATH"` |
| Website hasil uji terpotong | Jawaban melebihi `--max-new-tokens` | Normal jika jarang terjadi. Uji ulang dengan `--max-new-tokens 8000`. |

## 11. Catatan hukum dan kebijakan

- **Kebijakan Google Colab.**
  - Menurut [FAQ Colab](https://research.google.com/colaboratory/faq.html), tier gratis membatasi *remote control* (SSH, remote desktop), bekerja terutama lewat web UI di luar notebook, dan worker komputasi terdistribusi. Runtime yang melakukannya bisa dihentikan tanpa peringatan.
  - Mode B berjalan lewat terminal di dalam tab notebook, jadi tetap bekerja di dalam UI notebook. Jangan menambahkan SSH, tunnel (ngrok dan sejenisnya), atau akses jarak jauh lain ke VM Colab.
  - Proxy, file hosting, dan penambangan kripto dilarang di semua tier.
- **Claude Code** memakai akun Claude Anda dan tunduk pada ketentuan layanan Anthropic. Isi repo dan log yang dibaca Claude dikirim ke Anthropic untuk diproses. Jangan menaruh data rahasia di repo atau Drive yang dibaca Claude.
- **Kerahasiaan klien dan data pribadi.** Jika Anda menambah sampel dari pekerjaan nyata, misalnya dokumen perkara atau korespondensi klien:
  - Advokat wajib merahasiakan segala sesuatu yang diketahui atau diperoleh dari kliennya karena hubungan profesinya (Pasal 19 ayat (1) UU No. 18 Tahun 2003 tentang Advokat).
  - Data pribadi tunduk pada UU No. 27 Tahun 2022 tentang Pelindungan Data Pribadi. Pemrosesan butuh dasar yang sah (Pasal 20), dan pengendali data wajib menjaga kerahasiaan serta keamanannya (Pasal 35–36).
  - Mengunggah data seperti itu ke Colab, Hugging Face, atau Claude, atau memasukkannya ke dataset yang dibagikan, berisiko melanggar kedua ketentuan tersebut.
  - Anonimkan secara menyeluruh atau buat contoh fiktif. Sampel di dataset ini seluruhnya fiktif.
- **Lisensi model.**
  - Qwen3.5-4B dan Qwen2.5-Coder-7B-Instruct berlisensi Apache 2.0.
  - Adapter dan GGUF hasil training boleh dipakai dan dibagikan, termasuk untuk komersial, dengan syarat menyertakan teks lisensi, mempertahankan pemberitahuan hak cipta, dan menandai bahwa model telah diubah (Pasal 4 Apache License 2.0).
- **Data `mix`.** Sebagian sumbernya (Magicoder dan UltraChat) dibuat dengan model OpenAI. Untuk pemakaian komersial, pakai `own` saja, atau jalankan `python scripts/mix_general.py --code 0 --chat 0` agar hanya memakai Aya yang ditulis manusia. Penjelasan lengkapnya ada di README.
