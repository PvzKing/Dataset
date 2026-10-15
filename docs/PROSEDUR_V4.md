# Panduan Colab v4-pilot, langkah demi langkah

Panduan ini menjalankan bagian [`RENCANA_PYTHON.md`](RENCANA_PYTHON.md) yang butuh GPU, dari membuka Colab sampai mengirim hasilnya. Ikuti berurutan. Setiap sel menjelaskan tujuannya, kode yang harus dijalankan, output yang seharusnya muncul, lama waktunya, dan apa yang dilakukan kalau gagal.

<!-- hanya-md -->
## Cara termudah: panel interaktif

Buka **[notebook panel interaktif](https://colab.research.google.com/github/PvzKing/Dataset/blob/main/notebooks/v4_pilot_interaktif.ipynb)**. Notebook ini hanya punya 4 sel berbentuk formulir, tanpa perintah yang perlu disalin:

| Sel | Fungsi |
|---|---|
| 1️⃣ Siapkan | cek GPU, pasang paket yang belum ada, hubungkan Google Drive, unduh script terbaru, dan periksa adapter v3. Hasilnya berupa daftar ✅/❌ |
| 2️⃣ Jalankan | pilihan **Otomatis** menjalankan semua langkah yang belum selesai secara berurutan: ukur v3, latih v4-pilot, ukur v4-pilot, lalu MBPP+. Bisa juga memilih satu langkah saja |
| 3️⃣ Lihat progres | tabel ✅/▶️/⏳ untuk setiap langkah, dengan perkiraan sisa waktu GPU |
| 4️⃣ Laporan | papan skor v3 dan v4-pilot, website dan soal yang gagal, serta ringkasan training, siap disalin ke chat. Laporan juga disimpan ke Drive |

**Kalau Colab terputus atau kuota GPU habis**, buka notebook itu lagi, lalu jalankan sel 1 dan sel 2. Panel membaca hasil yang sudah ada di Drive dan melanjutkan dari langkah yang belum selesai.

Setiap langkah berjalan sebagai proses terpisah, jadi memori GPU selalu bersih dan sesi tidak perlu di-restart. Kalau sebuah langkah gagal, panel berhenti dan menampilkan saran perbaikannya. Output setiap langkah juga disimpan di `finetune-id/panel-log/`.

**Punya akses A100, atau memakai akun Google baru yang belum menyimpan adapter v3?** Ikuti [`PROSEDUR_V4_A100.md`](PROSEDUR_V4_A100.md). Panduan itu melatih v4 dan pembandingnya (v3-ulang) dari model dasar dengan LoRA 16-bit dan konteks 16.384, lalu mengukur semua model di A100. Panduan T4 di bawah butuh adapter v3 yang sudah ada di Drive.

Bagian di bawah ini adalah **cara manual**, sel demi sel. Gunanya untuk memahami apa yang dikerjakan panel, membaca arti output setiap langkah, atau menjalankan satu uji dengan opsi lain. Versi notebook-nya: [notebook manual](https://colab.research.google.com/github/PvzKing/Dataset/blob/main/notebooks/v4_pilot_colab.ipynb).
<!-- /hanya-md -->

## Gambaran

Yang akan dikerjakan:
1. **Mengukur v3 dan model dasar** dengan empat uji: HumanEval+, IndoPy-dev, Web-eval, dan MBPP+.
2. **Melatih v4-pilot**, yaitu adapter baru dengan dataset own terbaru (124 sampel, termasuk 20 sampel Python dan 15 sampel website baru). Resepnya sama persis dengan v3, jadi perbedaan hasilnya berasal dari data.
3. **Mengukur v4-pilot** dengan empat uji yang sama.
4. **Membaca papan skor**: apakah v4-pilot lolos gerbang G1 (Python umum tidak turun) dan G3 (website tidak kalah dari v3).

Total waktu GPU sekitar 6–8 jam, terlalu panjang untuk satu sesi Colab gratis. Jadi pekerjaannya dibagi menjadi tiga sesi. Semua hasil disimpan di Google Drive, dan setiap uji bisa dilanjutkan kalau Colab terputus.

| Sesi | Isi | Perkiraan waktu |
|---|---|---|
| 1 | Persiapan, lalu mengukur v3: HumanEval+, IndoPy-dev, Web-eval | ±2–2,5 jam |
| 2 | Melatih v4-pilot, lalu mengukurnya: HumanEval+, IndoPy-dev | ±1,5–2 jam |
| 3 | Web-eval v4-pilot, MBPP+ untuk model dasar, v4-pilot, dan v3 (opsional), papan skor, kirim hasil | ±2,5–3,5 jam |

Urutan ini tidak wajib. Kalau sesi terputus, buka sesi baru, jalankan Bagian A2 dan **Sel cek progres** (Bagian B), lalu lanjutkan uji yang belum selesai.

---

## Bagian A. Persiapan

### A1. Buka notebook dan pilih GPU

1. Buka notebook ini di Colab. Login dengan **akun Google yang menyimpan folder `finetune-id`** di Drive-nya. Kalau kamu memakai lebih dari satu akun Gmail, pastikan yang dipakai akun yang benar.
2. Pilih **File → Save a copy in Drive**, supaya catatan dan output tersimpan di Drive-mu.
3. Pilih **Runtime → Change runtime type**. Di **Hardware accelerator**, pilih **T4 GPU**, lalu **Save**.
4. Pastikan isi Drive-mu:

   | Yang dibutuhkan | Lokasi di Drive | Kalau tidak ada |
   |---|---|---|
   | adapter v3 | `MyDrive/finetune-id/v3/qwen3.5-4b-own-4bit/lora-adapter` (berisi `adapter_config.json`) | wajib ada. Periksa path-nya |
   | jawaban model dasar HumanEval+ dari uji sebelumnya | `MyDrive/finetune-id/eval-humaneval/model-dasar` | tidak masalah. Model dasar akan dijawab ulang (±23 menit) |
   | ruang kosong | | sediakan ±2 GB untuk adapter, checkpoint, dan hasil uji |

### A2. Sel 1: cek GPU dan pasang paket

Jalankan **sekali di setiap runtime baru**, yaitu saat pertama membuka atau setelah terputus lama. Tidak perlu diulang kalau kamu hanya memilih **Runtime → Restart session**.

```python
!nvidia-smi --query-gpu=name,memory.total --format=csv
!pip install --upgrade unsloth "evalplus @ git+https://github.com/evalplus/evalplus@26d6d00bb1fd0fa37f39c99d5290da67891d1c5e"
!pip install -q playwright && playwright install --with-deps chromium
```

- **Output yang benar:** baris pertama menampilkan `Tesla T4, 15360 MiB`. Setelah itu muncul log instalasi yang panjang.
- **Waktu:** ±4–6 menit.
- **Kalau muncul peringatan "You must restart the runtime" atau tombol Restart session:** klik tombolnya, lalu lanjut ke Sel 2. Paket yang sudah terpasang tidak hilang.
- **Kalau baris pertama bukan T4** atau muncul `NVIDIA-SMI has failed`: GPU belum dipilih. Ulangi A1 langkah 3.

Paket yang dipasang:
- `unsloth` untuk memuat model;
- `evalplus` dari commit yang sudah diperbaiki. Jangan pakai versi PyPI 0.3.1, yang selalu salah menilai HumanEval/32;
- Playwright dan Chromium, browser yang dipakai Web-eval untuk membuka dan mencoba website.

### A3. Sel 2: mount Drive dan unduh script

Jalankan **di awal setiap sesi**, termasuk setelah Restart session.

```python
from google.colab import drive; drive.mount("/content/drive")
REPO = "https://raw.githubusercontent.com/PvzKing/Dataset/main"
!wget -q -O /content/eval_humaneval.py {REPO}/humaneval-bench-script/eval_humaneval.py
!wget -q -O /content/chat_gradio.py {REPO}/scripts/chat_gradio.py
!wget -q -O /content/indopy_eval.py {REPO}/eval-suite/indopy_eval.py
!wget -q -O /content/web_eval.py {REPO}/eval-suite/web_eval.py
!wget -q -O /content/papan_skor.py {REPO}/eval-suite/papan_skor.py
!wget -q -O /content/train_unsloth.py {REPO}/scripts/train_unsloth.py
V3 = "/content/drive/MyDrive/finetune-id/v3/qwen3.5-4b-own-4bit/lora-adapter"
V4 = "/content/drive/MyDrive/finetune-id/v4-pilot/qwen3.5-4b-own-4bit/lora-adapter"
!ls {V3}
```

- **Pertama kali**, muncul jendela izin akses Google Drive. Pilih akun yang sama dengan A1, lalu izinkan.
- **Output yang benar:** `Mounted at /content/drive`, lalu daftar file adapter yang berisi `adapter_config.json` dan `adapter_model.safetensors`.
- **Kalau muncul `No such file or directory`:** path adapter v3 berbeda. Cari foldernya di panel **Files** di kiri (ikon folder → `drive/MyDrive/...`), klik kanan folder `lora-adapter`, pilih **Copy path**, lalu ganti nilai `V3`. Lokasi lain yang umum adalah `MyDrive/finetune-id/qwen3.5-4b-own-4bit/lora-adapter`.
- **Kalau Drive-nya baru dan tidak ada adapter v3 sama sekali:** panduan ini tidak bisa dipakai. Ikuti [`PROSEDUR_V4_A100.md`](PROSEDUR_V4_A100.md), yang melatih ulang pembandingnya dari awal.

---

## Bagian B. Sel cek progres

Sel ini tidak memuat model. Jalankan kapan saja, terutama di awal sesi kedua dan ketiga, untuk melihat uji mana yang sudah selesai.

```python
import json
from pathlib import Path

ROOT = Path("/content/drive/MyDrive/finetune-id")
RUN = {"dasar": "model-dasar", "v3": "v3-qwen3.5-4b-own-4bit", "v4": "v4-pilot-qwen3.5-4b-own-4bit"}
print(f"{'uji':<16}" + "".join(f"{k:>8}" for k in RUN))
for folder in ["eval-humaneval", "eval-indopy-dev", "eval-web", "eval-mbpp"]:
    print(f"{folder:<16}" + "".join(f"{'selesai' if (ROOT / folder / run / 'ringkasan.json').exists() else '-':>8}"
                                     for run in RUN.values()))
v4 = ROOT / "v4-pilot/qwen3.5-4b-own-4bit/lora-adapter/adapter_config.json"
print("adapter v4-pilot:", "sudah ada" if v4.exists() else "belum dilatih")
```

Contoh output di awal Sesi 1, kalau jawaban model dasar HumanEval+ dari uji sebelumnya masih ada:

```
uji                dasar      v3      v4
eval-humaneval   selesai       -       -
eval-indopy-dev        -       -       -
eval-web               -       -       -
eval-mbpp              -       -       -
adapter v4-pilot: belum dilatih
```

---

## Bagian C. Sesi 1: mengukur v3

Setiap uji berikut menjawab soal dengan adapter v3, lalu dengan **model dasar**, yaitu adapter yang sama dimatikan sementara. Setelah itu kedua model dibandingkan. Jawaban model dasar disimpan dan dipakai ulang, jadi model dasar cukup dijawab sekali untuk setiap uji.

Selama uji berjalan, biarkan tab Colab tetap terbuka. Output setiap uji juga disimpan di Drive, jadi tidak perlu disalin manual.

### C1. HumanEval+ v3 (±20 menit)

```python
%run /content/eval_humaneval.py --adapter {V3}
```

Output yang seharusnya muncul, berurutan:
1. `##### run: v3-qwen3.5-4b-own-4bit (...)` dan `folder hasil: .../eval-humaneval/v3-qwen3.5-4b-own-4bit`.
2. Banner Unsloth saat model dimuat (±1 menit).
3. Baris progres seperti `[v3-qwen3.5-4b-own-4bit] 48/164 soal, 3.0 menit, ±7.2 menit lagi, 32 token/detik`.
4. Penilaian EvalPlus (±1–3 menit), lalu ringkasan `===== v3-qwen3.5-4b-own-4bit: 164 soal =====` dengan skor HumanEval dan HumanEval+.
5. Run `model-dasar`. Kalau jawabannya sudah ada, muncul `164 soal sudah dijawab sebelumnya, dilewati`, lalu hanya penilaiannya yang diulang.
6. Tabel perbandingan, dengan baris seperti `HumanEval+: selisih -2 soal (-1.2 poin persen), McNemar p = 0.687: belum nyata, bisa kebetulan`.

Cara membaca baris terakhir: **p < 0,05 berarti selisihnya nyata**. Kalau p ≥ 0,05, selisih itu bisa saja kebetulan, jadi jangan disimpulkan sebagai naik atau turun.

### C2. IndoPy-dev v3 (±10–15 menit)

```python
%run /content/indopy_eval.py --split dev --adapter {V3}
```

- **Isinya:** 20 soal Python berbahasa Indonesia dengan tes tersembunyi. Model menjawab seperti saat dipakai sungguhan, lalu kodenya dijalankan bersama tes.
- **Output:** baris progres `[v3-...] 8/20 soal, ...`, lalu `===== v3-qwen3.5-4b-own-4bit: IndoPy-dev, 20 soal =====` dengan skor `pass@1`, skor per tingkat (mudah/sedang/sulit), dan daftar `gagal NN: <alasan>`. Setelah itu run model dasar dan tabel perbandingan.
- **Jangan jalankan `--split test`.** Set test dikunci untuk penilaian akhir v4 penuh.

### C3. Web-eval v3 (±60–90 menit)

```python
%run /content/web_eval.py --adapter {V3}
```

- **Isinya:** model membuat 10 website dari prompt baru. Setiap website dibuka di Chromium tanpa internet lalu dicoba. Contohnya: 100 °C harus menjadi 212 °F, data pengeluaran harus tetap ada setelah reload, dan jam WIB harus benar.
- **Output:** progres `[v3-...] 2/10 website, ...`. Generate website panjang, jadi setiap batch berisi 2 website dan butuh beberapa menit. Setelah itu muncul tabel:
  ```
  | website          | html | tanpa error | responsif | fitur | alasan
  | konversi-satuan  | ya   | ya          | ya        | ya    |
  | jam-dunia        | ya   | ya          | ya        | TIDAK | jam Asia/Jakarta tidak sesuai (...)
  ```
- **Website yang dibuat** disimpan di `MyDrive/finetune-id/eval-web/<run>/situs/`. Unduh dan buka di browser kalau ingin melihatnya.
- **Kalau muncul `No module named 'playwright'` atau `Executable doesn't exist`:** jalankan ulang baris terakhir Sel 1, lalu ulangi perintah ini. Website yang sudah dibuat tidak dibuat ulang.

### C4. Papan skor sementara v3

```python
%run /content/papan_skor.py --tag v3-qwen3.5-4b-own-4bit
```

Uji yang belum dijalankan tercatat `belum diuji` atau `BELUM DIUKUR`, dan itu wajar. Simpan output ini. Kalau Sesi 1 selesai di sini, tutup tab saja: semua hasil sudah ada di Drive.

---

## Bagian D. Sesi 2: melatih v4-pilot

Mulai sesi baru: jalankan Sel 1 jika runtime-nya baru, lalu Sel 2 dan Sel cek progres.

### D1. Training (±75–90 menit, ditambah ±10 menit untuk website uji)

```python
!python /content/train_unsloth.py train --out /content/drive/MyDrive/finetune-id/v4-pilot
```

Output penting yang perlu dicek, berurutan:

| Baris | Arti |
|---|---|
| `folder hasil: /content/drive/MyDrive/finetune-id/v4-pilot/qwen3.5-4b-own-4bit` | hasil masuk ke folder baru, jadi v3 tidak tersentuh |
| `GPU kecil tanpa bf16 terdeteksi (misalnya T4): ...` | QLoRA 4-bit dan konteks 6144 dipakai otomatis, sama dengan v3 |
| `data valid: 124 sampel dari ...` | **wajib 124.** Angka lain berarti `train.jsonl` yang terunduh bukan versi terbaru (lihat Bagian H) |
| `124 sampel dipakai, 0 dibuang karena > 6144 token []` | semua sampel ikut dilatih |
| `token per epoch: ...` dan `3 epoch = 48 step` | 124 sampel ÷ 8 per step = 16 step per epoch (dibulatkan ke atas) |
| `perkiraan T4 (kalibrasi dari run v3): ...` | perkiraan lama training |
| progress bar sampai `39/39` | training berjalan. Loss dicetak berkala |
| `[status] trained: adapter tersimpan` | adapter v4-pilot sudah tersimpan di Drive |
| `[status] done: selesai` | dua website uji (`contoh-*.html`) juga sudah dibuat |

- **Kalau Colab terputus di tengah training**, jalankan perintah yang sama lagi. Checkpoint disimpan setiap 10 step, dan training melanjutkan dari checkpoint terakhir selama data dan pengaturannya sama.
- **Website uji** ada di `MyDrive/finetune-id/v4-pilot/qwen3.5-4b-own-4bit/contoh-*.html`. Bandingkan dengan hasil v3 kalau ingin melihat sekilas.

### D2. Cek adapter v4-pilot

```python
!ls {V4}
```

Harus berisi `adapter_config.json` dan `adapter_model.safetensors`. Training berjalan sebagai proses terpisah (`!python`), jadi memori GPU-nya langsung dilepas saat selesai. Uji v4-pilot bisa langsung dijalankan tanpa restart.

---

## Bagian E. Mengukur v4-pilot

Semua jawaban model dasar dipakai ulang dari Bagian C, jadi hanya v4-pilot yang dijawab. Waktunya sekitar separuh Bagian C.

```python
%run /content/eval_humaneval.py --adapter {V4}                 # ±20 menit
```
```python
%run /content/indopy_eval.py --split dev --adapter {V4}        # ±5–10 menit
```

Kalau Sesi 2 masih punya waktu, lanjutkan dengan Web-eval. Kalau tidak, jalankan di Sesi 3:

```python
%run /content/web_eval.py --adapter {V4}                       # ±30–45 menit
```

---

## Bagian F. Sesi 3: MBPP+

MBPP+ berisi 378 soal Python umum. Uji pertama juga menjawab model dasar, jadi jalankan v4-pilot dulu:

```python
%run /content/eval_humaneval.py --dataset mbpp --adapter {V4}  # ±80–110 menit (v4-pilot + model dasar)
```

MBPP+ untuk v3 **opsional** (±40–55 menit). Uji ini menunjukkan apakah dataset website v3 sudah menggeser kemampuan Python umum. Jalankan kalau masih ada waktu:

```python
%run /content/eval_humaneval.py --dataset mbpp --adapter {V3}  # opsional
```

Setiap uji melepas memori GPU saat selesai, jadi beberapa uji bisa dijalankan berurutan dalam satu sesi. Kalau tetap muncul `CUDA out of memory`, pilih **Runtime → Restart session**, jalankan Sel 2, lalu ulangi perintah yang sama. Jawaban yang sudah tersimpan dilewati.

---

## Bagian G. Papan skor, keputusan, dan kirim hasil

### G1. Papan skor

```python
%run /content/papan_skor.py --tag v3-qwen3.5-4b-own-4bit
```
```python
%run /content/papan_skor.py --tag v4-pilot-qwen3.5-4b-own-4bit --pembanding v3-qwen3.5-4b-own-4bit
```

Papan skor v4-pilot berisi tabel ukuran (adapter, pembanding, selisih, p) dan status gerbang:

| Gerbang | Lolos jika |
|---|---|
| G1 Python umum | HumanEval+ dan MBPP+ v4-pilot tidak turun nyata dari model dasar, dan selisih gabungannya ≥ −1,5 poin |
| G2 IndoPy-test | tercatat `BELUM DIUKUR`, dan memang begitu untuk pilot. Set test baru dijalankan pada v4 penuh. Untuk pilot, lihat baris IndoPy-dev sebagai petunjuk |
| G3 Website | jumlah website Web-eval v4-pilot yang lolos ≥ v3 |

Baris `Keputusan: BELUM DITERIMA` wajar untuk pilot, karena G2 dan G4 memang belum diukur. Yang menentukan langkah berikutnya adalah tabel ini:

| Hasil | Langkah berikutnya |
|---|---|
| G1 lolos, G3 lolos, IndoPy-dev v4-pilot > v3 | gaya sampel terbukti membantu. Lanjut ke Fase 3: data penuh dan set uji perbaikan bug |
| IndoPy-dev tidak naik | jangan tambah data dulu. Jawaban yang gagal perlu dianalisis |
| G3 gagal | bandingkan kolom alasan Web-eval v3 dan v4-pilot: kegagalan baru (regresi) atau sama |
| G1 gagal | cek soal regresi di `perbandingan-*.json`, lalu pertimbangkan swa-distilasi (Fase 4) |

### G2. Sel kumpulkan hasil

Sel ini mencetak website dan soal IndoPy-dev yang gagal untuk model dasar, v3, dan v4-pilot, dalam satu output yang mudah disalin:

```python
import json
from pathlib import Path

ROOT = Path("/content/drive/MyDrive/finetune-id")
RUN = {"dasar": "model-dasar", "v3": "v3-qwen3.5-4b-own-4bit", "v4": "v4-pilot-qwen3.5-4b-own-4bit"}


def ringkasan(folder, run):
    f = ROOT / folder / run / "ringkasan.json"
    return json.loads(f.read_text()) if f.exists() else None


print("=== Web-eval: website yang gagal ===")
for nama, run in RUN.items():
    if r := ringkasan("eval-web", run):
        print(f"{nama}: lolos {round(r['web_lolos'] * r['soal'])}/{r['soal']}, "
              f"format Cek kebutuhan {r['format_cek_kebutuhan']}/{r['soal']}")
        for situs, alasan in r["gagal"].items():
            print(f"   {situs}: {alasan[:150]}")
print("\n=== IndoPy-dev: soal yang gagal ===")
for nama, run in RUN.items():
    if r := ringkasan("eval-indopy-dev", run):
        print(f"{nama}: {r['indopy_pass@1']:.0%}, per tingkat {r['per_tingkat']}")
        for soal, alasan in r["gagal"].items():
            print(f"   {soal.rsplit('/', 1)[1]}: {alasan[:150]}")
```

### G3. Kirim ke chat

Salin dan kirim:
1. output kedua papan skor (G1);
2. output sel kumpulkan hasil (G2);
3. potongan log training yang memuat baris `data valid`, `sampel dipakai`, dan loss terakhir.

Dari situ saya menganalisis jenis kesalahannya dan menyusun sampel Fase 3.

---

## Bagian H. Mengatasi masalah

| Gejala | Penyebab | Solusi |
|---|---|---|
| Baris pertama Sel 1 bukan `Tesla T4`, atau `NVIDIA-SMI has failed` | runtime tanpa GPU | Runtime → Change runtime type → T4 GPU, lalu jalankan Sel 1 lagi |
| `Cannot connect to GPU backend` atau `You cannot currently connect to a GPU` | kuota GPU gratis harian habis | coba lagi beberapa jam kemudian. Semua hasil aman di Drive |
| `adapter tidak ditemukan` | Drive belum di-mount atau path salah | jalankan Sel 2 dan periksa output `ls`. Pastikan akun Google-nya benar |
| `evalplus yang terpasang (0.3.1 dari PyPI)...` | EvalPlus versi PyPI terpasang | jalankan perintah `pip install --force-reinstall --no-deps ...` yang ditampilkan, Restart session, lalu Sel 2 |
| `No module named 'playwright'` atau `Executable doesn't exist` | Playwright/Chromium belum terpasang di runtime ini | jalankan baris terakhir Sel 1 |
| `CUDA out of memory` | memori dari uji atau training sebelumnya | Restart session, Sel 2, lalu ulangi perintah yang sama |
| Colab terputus di tengah uji | sesi habis atau idle | sesi baru: Sel 1 (jika runtime baru), Sel 2, lalu perintah yang sama. Jawaban yang tersimpan dilewati |
| Colab terputus di tengah training | sesi habis | jalankan D1 lagi. Training dilanjutkan dari checkpoint terakhir |
| `data valid: N sampel` dengan N selain 124 | `train.jsonl` lama dipakai | hapus `MyDrive/finetune-id/v4-pilot/train.jsonl`, lalu ulangi D1 |
| `data atau pengaturan berubah: hasil lama dipindah ke .../arsip/...` | training ulang dengan data atau pengaturan berbeda | wajar. Hasil lama diarsipkan, dan training dimulai dari awal |
| `stop_strings tidak didukung ...` | versi transformers | tidak perlu tindakan. Generate tetap jalan, hanya sedikit lebih lambat |
| Skor v4-pilot janggal setelah dilatih ulang | jawaban uji dari adapter lama dipakai ulang | hapus subfolder `v4-pilot-qwen3.5-4b-own-4bit` di setiap folder `eval-*`, lalu ulangi Bagian E dan F |

---

## Lampiran 1. Hasil di Google Drive

```
MyDrive/finetune-id/
├── v3/qwen3.5-4b-own-4bit/lora-adapter/        adapter v3 (tidak diubah)
├── v4-pilot/
│   ├── train.jsonl                              data yang dipakai training v4-pilot
│   └── qwen3.5-4b-own-4bit/
│       ├── lora-adapter/                        adapter v4-pilot
│       ├── checkpoints/                         untuk melanjutkan training yang terputus
│       └── contoh-*.html                        website uji setelah training
├── eval-humaneval/   model-dasar/, v3-.../, v4-pilot-.../, perbandingan-*.json
├── eval-mbpp/        (susunan sama)
├── eval-indopy-dev/  (susunan sama; hasil.jsonl berisi kode dan alasan gagal per soal)
└── eval-web/         (susunan sama; situs/ berisi website yang dibuat)
```

Setiap folder run berisi:
- `jawaban.jsonl`: jawaban mentah model;
- `ringkasan.json`: skor dan daftar yang gagal.

## Lampiran 2. Semua perintah sekaligus

```
Sel 1   pasang paket (sekali per runtime)
Sel 2   mount Drive, unduh script, V3 dan V4 (setiap sesi)
v3      %run /content/eval_humaneval.py --adapter {V3}
        %run /content/indopy_eval.py --split dev --adapter {V3}
        %run /content/web_eval.py --adapter {V3}
latih   !python /content/train_unsloth.py train --out /content/drive/MyDrive/finetune-id/v4-pilot
v4      %run /content/eval_humaneval.py --adapter {V4}
        %run /content/indopy_eval.py --split dev --adapter {V4}
        %run /content/web_eval.py --adapter {V4}
        %run /content/eval_humaneval.py --dataset mbpp --adapter {V4}
        %run /content/eval_humaneval.py --dataset mbpp --adapter {V3}      (opsional)
skor    %run /content/papan_skor.py --tag v4-pilot-qwen3.5-4b-own-4bit --pembanding v3-qwen3.5-4b-own-4bit
```

## Catatan sebelum mempublikasikan skor

Angka dari prosedur ini adalah **uji internal**. Kalau nanti model ditawarkan sebagai produk atau jasa:
- sebutkan kondisi ujinya (greedy, pass@1, versi EvalPlus, 4-bit);
- bandingkan dengan model dasarnya;
- jangan sebut skor model dasar sebagai hasil fine-tuning;
- sebut IndoPy dan Web-eval sebagai uji buatan sendiri.

Klaim yang melebihkan mutu berisiko melanggar Pasal 9 ayat (1) huruf a dan Pasal 10 huruf b UU No. 8 Tahun 1999 tentang Perlindungan Konsumen.
