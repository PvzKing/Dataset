# Panduan Menjalankan Crawler Dataset di Laptop

Panduan ini menjelaskan cara menjalankan [`scripts/find_datasets.py`](../scripts/find_datasets.py) di laptop sendiri (Windows, macOS, atau Linux), dari memasang Python sampai menonton laba-labanya merayap di browser.

## Daftar isi

1. [Gambaran singkat](#1-gambaran-singkat)
2. [Yang perlu disiapkan](#2-yang-perlu-disiapkan)
3. [Instalasi](#3-instalasi)
4. [Token Hugging Face (opsional)](#4-token-hugging-face-opsional)
5. [Menjalankan pertama kali](#5-menjalankan-pertama-kali)
6. [Pilihan perintah lain](#6-pilihan-perintah-lain)
7. [Membaca hasil](#7-membaca-hasil)
8. [Menjalankan lagi lain kali](#8-menjalankan-lagi-lain-kali)
9. [Mengatasi masalah](#9-mengatasi-masalah)
10. [Catatan hukum](#10-catatan-hukum)

---

## 1. Gambaran singkat

Crawler ini mencari kandidat dataset di katalog [Hugging Face Hub](https://huggingface.co/datasets), lalu:

- membaca dataset card tiap kandidat dan menandai risikonya;
- menilai lisensi (permisif, share-alike, nonkomersial, dan seterusnya);
- untuk preset coding, memberi skor kualitas 0–100;
- mengambil beberapa baris contoh lewat dataset viewer resmi Hugging Face supaya isinya bisa dilihat;
- menulis laporan `.md`, `.json`, dan `.html` di folder `runs/`.

Semua data diambil lewat API resmi Hugging Face. Dataset tidak diunduh utuh dan halaman web tidak di-scrape.

Dengan opsi `--live`, script menjalankan server kecil di laptop dan membuka browser. Jaringnya tumbuh dan laba-labanya merayap selama crawl berjalan.

## 2. Yang perlu disiapkan

| Kebutuhan | Keterangan |
|---|---|
| Python 3.9 atau lebih baru | Cek dengan `python --version` (Windows: `py --version`) |
| Git | Untuk mengambil repo. Bisa juga diganti dengan unduh ZIP dari GitHub |
| Browser modern | Chrome, Edge, Firefox, atau Safari versi terbaru |
| Internet | Laptop harus bisa membuka `huggingface.co` dan `datasets-server.huggingface.co` |
| Akun Hugging Face | Opsional, hanya untuk token (lihat [bagian 4](#4-token-hugging-face-opsional)) |

Tidak perlu GPU. Crawler hanya mengirim request HTTP, jadi laptop biasa sudah cukup.

## 3. Instalasi

### 3.1 Pasang Python dan Git

**Windows**
1. Unduh Python dari [python.org/downloads](https://www.python.org/downloads/). Saat memasang, **centang "Add python.exe to PATH"**.
2. Unduh Git dari [git-scm.com](https://git-scm.com/download/win), lalu pasang dengan pilihan bawaan.
3. Buka **PowerShell**, lalu cek: `py --version` dan `git --version`.

**macOS**
1. Buka **Terminal**, lalu jalankan `xcode-select --install`. Perintah ini memasang Git.
2. Pasang Python dari [python.org/downloads](https://www.python.org/downloads/) atau dengan Homebrew: `brew install python`.
3. Cek: `python3 --version` dan `git --version`.

**Linux (Ubuntu/Debian)**
```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git
```

> Di bawah ini perintah ditulis `python`. Di Windows ganti dengan `py`. Di macOS dan Linux ganti dengan `python3` jika `python` tidak dikenali.

### 3.2 Ambil repo

```bash
git clone https://github.com/PvzKing/Dataset.git
cd Dataset
```

Selama fitur crawler belum di-merge ke `main`, pindah dulu ke branch-nya:

```bash
git checkout claude/ecstatic-brahmagupta-e0m0hw
```

Setelah PR-nya di-merge, langkah ini tidak perlu lagi.

### 3.3 Buat virtual environment dan pasang paket

Virtual environment menjaga paket untuk proyek ini terpisah dari Python sistem.

**Windows (PowerShell)**
```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install requests
```
Jika PowerShell menolak menjalankan `Activate.ps1`, jalankan dulu `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, lalu ulangi.

**macOS / Linux**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install requests
```

Jika berhasil, awal baris terminal menampilkan `(.venv)`. Crawler hanya butuh paket `requests`. Sisanya sudah tersedia di Python.

## 4. Token Hugging Face (opsional)

Tanpa token, crawler tetap jalan. Token berguna kalau Anda sering dibatasi server (HTTP 429), karena batas request untuk akun lebih longgar.

1. Masuk ke [huggingface.co](https://huggingface.co), lalu buka **Settings → Access Tokens**.
2. Buat token baru dengan jenis **Read**. Crawler tidak butuh izin menulis.
3. Pasang token sebagai variabel lingkungan di terminal yang sama dengan tempat crawler akan dijalankan:

| Sistem | Perintah |
|---|---|
| Windows PowerShell | `$env:HF_TOKEN = "hf_xxx"` |
| Windows Command Prompt | `set HF_TOKEN=hf_xxx` |
| macOS / Linux | `export HF_TOKEN=hf_xxx` |

Token hanya berlaku selama jendela terminal itu terbuka. **Jangan menulis token ke file di dalam repo** dan jangan meng-commit-nya.

## 5. Menjalankan pertama kali

Pastikan virtual environment aktif (`(.venv)` tampil), lalu jalankan:

```bash
python scripts/find_datasets.py --preset coding --live
```

Yang terjadi:

1. **Server dimulai.** Terminal menampilkan `visualisasi live: http://127.0.0.1:8765/` dan browser terbuka otomatis. Kalau browser tidak terbuka, salin alamat itu ke browser.
2. **Mencari.** Laba-laba berangkat dari "katalog" ke setiap kata kunci (`code`, `coding`, `program`, `python`, `javascript`, `sql`, dan tag `code`), lalu memintal benang ke dataset yang ditemukan. Dataset yang tergeser dari daftar teratas memudar.
3. **Membaca dataset card.** Laba-laba mendatangi tiap dataset. Titiknya berdenyut, lalu mendapat cincin dan skor.
4. **Mengintip isi data.** Laba-laba mengambil 3 baris contoh tiap dataset. Titik yang isinya bisa dilihat diberi lubang kecil di tengah.
5. **Selesai.** Status berubah menjadi "Selesai" dan laporan tersimpan di `runs/`.

Dengan pengaturan bawaan, satu crawl preset coding memakan waktu sekitar **4–6 menit**, karena jeda 1 detik antar-request disengaja supaya tidak membebani server.

Halaman tetap bisa dibuka atau dimuat ulang setelah crawl selesai. Untuk menghentikan server, kembali ke terminal dan tekan **Ctrl+C**.

### Cara memakai halaman

- **Klik titik atau nama dataset** untuk melihat detail di panel kanan: lisensi, skor, sinyal kualitas, dan catatan risiko.
- **Lihat isi data:** klik **Lihat isi data** di panel, atau **Lihat** di tabel bawah. Percakapan ditampilkan per giliran (user/assistant), sedangkan kolom lain sebagai teks apa adanya.
- **Klik kata kunci** (misalnya `"python"`) untuk melihat dataset yang ditemukan lewat pencarian itu.
- **Klik legenda warna** untuk menyembunyikan atau menampilkan status lisensi tertentu.
- **Tombol Jeda, Ulangi, dan Lewati animasi**, serta pengatur kecepatan.
- **Tabel "Daftar kandidat"** di bawah jaring berisi semua kandidat dan bisa dipakai dengan keyboard.

## 6. Pilihan perintah lain

```bash
# Dataset berbahasa Indonesia (preset bawaan), tanpa live
python scripts/find_datasets.py

# Cari dengan kata kunci dan tugas tertentu
python scripts/find_datasets.py --search instruct --task text-generation

# Hanya lisensi permisif, 30 kandidat teratas
python scripts/find_datasets.py --preset coding --only-permissive --top 30 --live

# Lebih cepat: tanpa membaca card dan tanpa contoh isi
python scripts/find_datasets.py --preset coding --no-cards --preview 0
```

| Opsi | Bawaan | Fungsi |
|---|---|---|
| `--preset umum\|coding` | `umum` | `umum`: dataset berbahasa Indonesia. `coding`: dataset kode semua bahasa, diurutkan menurut skor |
| `--live` | mati | Tonton crawl langsung di browser |
| `--port` | `8765` | Port server lokal untuk `--live` |
| `--no-browser` | mati | Dengan `--live`: jangan buka browser otomatis |
| `--search` | - | Kata kunci pada nama dataset |
| `--task` | - | Kategori tugas, misalnya `text-generation` |
| `--language` | `id` (umum), semua (coding) | Kode bahasa di metadata Hugging Face |
| `--top` | `50` | Jumlah kandidat di laporan |
| `--scan` | `500` | Jumlah maksimal dataset yang dipindai per pencarian |
| `--min-downloads` | `0` | Buang dataset dengan unduhan lebih sedikit dari ini |
| `--only-permissive` | mati | Hanya tampilkan lisensi permisif |
| `--no-cards` | mati | Jangan baca dataset card (lebih cepat, catatan risiko lebih sedikit) |
| `--preview` | `3` | Jumlah baris contoh per kandidat. `0` = tidak mengambil |
| `--delay` | `1.0` | Jeda minimal antar-request, dalam detik. Jangan diturunkan di bawah 1 |
| `--out` | `runs/kandidat_*` | Awalan nama file laporan |

## 7. Membaca hasil

Setelah selesai, folder `runs/` berisi tiga file (preset coding memakai nama `kandidat_coding`, preset umum memakai `kandidat_dataset`):

| File | Isi |
|---|---|
| `kandidat_coding.md` | Tabel kandidat, arti status lisensi, dan checklist sebelum memakai data. Bisa dibuka di editor teks atau VS Code |
| `kandidat_coding.json` | Data mentah lengkap, termasuk baris contoh, untuk diolah script lain |
| `kandidat_coding.html` | Visualisasi laba-laba yang memutar ulang crawl. Klik dua kali untuk membuka di browser, tanpa server dan tanpa internet |

Folder `runs/` tidak ikut di-commit (ada di `.gitignore`), karena isinya data pihak ketiga.

**Cara menilai kandidat:**
1. Mulai dari skor tertinggi dengan status **permisif**.
2. Buka **Lihat isi data**: apakah bentuknya cocok (instruksi/percakapan), jawabannya benar, dan bahasanya rapi?
3. Baca **catatan risiko**. Perhatikan terutama output model lain, data media sosial, benchmark, dan korpus kode mentah.
4. Buka dataset card asli lewat tautan **Buka di Hugging Face** dan pastikan lisensinya sama dengan metadata.
5. Kalau sudah yakin, tambahkan dataset itu ke `SOURCES` di [`scripts/mix_general.py`](../scripts/mix_general.py).

## 8. Menjalankan lagi lain kali

```bash
cd Dataset
git pull                                   # ambil versi terbaru
source .venv/bin/activate                  # Windows: .venv\Scripts\Activate.ps1
python scripts/find_datasets.py --preset coding --live
```

Laporan lama di `runs/` akan ditimpa. Pakai `--out runs/coding-2026-10-11` kalau ingin menyimpan beberapa hasil.

## 9. Mengatasi masalah

| Gejala | Penyebab dan solusi |
|---|---|
| `python` tidak dikenali | Windows: pakai `py`. macOS/Linux: pakai `python3`. Kalau masih gagal, Python belum masuk PATH; pasang ulang dan centang "Add python.exe to PATH" |
| `ModuleNotFoundError: No module named 'requests'` | Virtual environment belum aktif atau paket belum dipasang. Aktifkan `.venv`, lalu `pip install requests` |
| `tidak bisa membuka port 8765` | Port sedang dipakai, mungkin oleh crawler yang masih jalan di terminal lain. Tutup terminal itu, atau pakai `--port 8800` |
| Browser tidak terbuka otomatis | Salin alamat `http://127.0.0.1:8765/` dari terminal ke browser |
| Halaman menampilkan data lama | Muat ulang paksa: Ctrl+F5 (Windows/Linux) atau Cmd+Shift+R (macOS) |
| `dibatasi server (429), menunggu ...` | Normal: crawler menunggu sesuai permintaan server, lalu lanjut sendiri. Kalau sering terjadi, pasang token ([bagian 4](#4-token-hugging-face-opsional)) |
| `Crawl gagal: ... HTTP 401/403` | Token salah atau kedaluwarsa. Hapus atau perbarui `HF_TOKEN` |
| `Crawl gagal: ... HTTP 5xx` | Server Hugging Face sedang bermasalah. Coba lagi beberapa menit kemudian |
| Error koneksi atau SSL | Internet terputus, atau jaringan kantor/kampus memblokir Hugging Face. Coba jaringan lain. Kalau memakai proxy, isi `HTTPS_PROXY` |
| "dataset viewer tidak tersedia" | Dataset viewer tidak aktif untuk dataset itu (format tidak didukung atau dataset terlalu besar). Lihat isinya langsung di Hugging Face |
| "dataset gated: ..." | Pemilik mewajibkan persetujuan syarat. Buka halaman dataset, setujui syaratnya kalau memang mau memakainya, lalu jalankan lagi dengan token akun yang sama |
| Laba-laba tertinggal dari crawl | Normal. Ia otomatis mempercepat langkah, atau tekan **Lewati animasi** |

## 10. Catatan hukum

- **Akses sah.** Crawler hanya memakai API resmi Hugging Face, memberi jeda antar-request, dan mematuhi `Retry-After`. Tidak ada login atau pengamanan yang diterobos, jadi tidak masuk ranah akses tanpa hak (dahulu Pasal 30 UU ITE, kini diatur dalam KUHP baru) atau mengganggu sistem elektronik (Pasal 33 UU ITE).
- **Dataset gated tidak diakali.** Isinya baru diambil setelah Anda sendiri menyetujui syarat pemiliknya. Syarat itu berlaku sebagai perjanjian (Pasal 1320 dan 1338 KUHPerdata).
- **Baris contoh hanya untuk menilai.** Baris contoh adalah salinan kecil untuk menilai kualitas dan disimpan lokal di `runs/`. Menyebarkan ulang isi dataset tetap tunduk pada lisensinya dan hak ekonomi pencipta (Pasal 9 UU No. 28 Tahun 2014 tentang Hak Cipta).
- **Data pribadi.** Baris contoh bisa memuat data pribadi, terutama dataset dari media sosial atau ulasan. Jangan bagikan file di `runs/` sembarangan, dan saring data pribadi sebelum memakai dataset untuk training (UU No. 27 Tahun 2022 tentang Pelindungan Data Pribadi).
- **Status lisensi hanya petunjuk awal.** Status lisensi di laporan dibaca dari metadata yang diisi pemilik dataset dan bisa keliru. Laporan adalah daftar untuk direview, bukan izin memakai data.
