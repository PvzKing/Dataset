# Panduan Colab v4 di A100: training dari awal dengan konteks panjang

<!-- colab-gpu: A100 -->

Panduan ini melatih **v4** dari model dasar Qwen3.5-4B di GPU A100, dengan konteks training 16.384 token, lalu mengukur v4 dengan semua uji di [`eval-suite/`](../eval-suite/README.md). **Tanpa pembanding:** v3 dan model dasar tidak dilatih ulang atau diuji, jadi hasilnya berupa skor v4 apa adanya. Panduan ini tidak butuh hasil lama di Google Drive, jadi bisa dimulai dari akun Google yang baru. Ikuti berurutan. Setiap sel menjelaskan tujuannya, kode yang harus dijalankan, output yang seharusnya muncul, dan apa yang dilakukan kalau gagal.

<!-- hanya-md -->
## Cara termudah: panel interaktif

Buka **[panel interaktif A100](https://colab.research.google.com/github/PvzKing/Dataset/blob/main/notebooks/v4_a100_interaktif.ipynb)**. Notebook ini hanya punya 4 sel berbentuk formulir, tanpa perintah yang perlu disalin:

| Sel | Fungsi |
|---|---|
| 1️⃣ Siapkan | cek GPU (harus A100), pasang paket yang belum ada, hubungkan Google Drive, dan unduh script terbaru. Konteks training dipilih di sini (16384, atau 12288 jika kehabisan VRAM) |
| 2️⃣ Jalankan | pilihan **Otomatis** menjalankan semua langkah yang belum selesai secara berurutan: latih v4, lalu uji v4. Centang `sertakan_indopy_test` untuk menjalankan set uji akhir. Bisa juga memilih satu langkah saja |
| 3️⃣ Lihat progres | tabel ✅/▶️/⏳ untuk setiap langkah, dengan perkiraan sisa waktu GPU |
| 4️⃣ Laporan | skor v4 di setiap uji, website dan soal yang gagal, serta ringkasan training, siap disalin ke chat. Laporan juga disimpan ke Drive (`finetune-id/laporan-v4-a100.txt`) |

Panel menjalankan perintah yang sama persis dengan bagian manual di bawah, dengan tambahan berikut:
- **Melanjutkan sendiri setelah Colab terputus.** Jalankan sel 1 dan sel 2 lagi. Training dilanjutkan dari checkpoint terakhir, dan jawaban uji yang sudah tersimpan tidak diulang.
- **Menurunkan batch uji sendiri saat VRAM habis**, lalu mengulang uji itu tanpa kehilangan jawaban yang sudah tersimpan.
- **Memberi peringatan** kalau training tidak memakai 103 sampel atau ada sampel yang dibuang.

Bagian di bawah ini adalah **cara manual**, sel demi sel. Gunanya untuk memahami apa yang dikerjakan panel atau menjalankan uji dengan opsi lain. Versi notebook-nya: [notebook manual A100](https://colab.research.google.com/github/PvzKing/Dataset/blob/main/notebooks/v4_a100_colab.ipynb). Panduan untuk T4 gratis ada di [`PROSEDUR_V4.md`](PROSEDUR_V4.md).
<!-- /hanya-md -->

## Gambaran

### Bedanya dengan v4-pilot di T4

| | v4-pilot (T4) | **v4 (panduan ini, A100)** |
|---|---|---|
| Titik awal | model dasar | model dasar. **Bukan** lanjutan adapter lain (`--init-adapter` tidak dipakai) |
| Presisi training | QLoRA 4-bit, dihitung dalam float32 | **LoRA 16-bit (bf16)**, yaitu cara yang disarankan Unsloth untuk Qwen3.5 |
| Konteks training (`max_seq_len`) | 6.144 token | **16.384 token** |
| Batas jawaban website uji (`max_new_tokens`) | 6.000 token | **12.000 token** |
| Data | `data/train.jsonl` terbaru (103 sampel) | sama |
| Resep lain | 3 epoch, lr 1e-4, LoRA r16/alpha 32, batch efektif 8, seed 42 | sama |
| Pembanding | v3 dan model dasar ikut diuji | **tidak ada**. Hanya v4 yang diuji (`--no-vs-base`) |
| Folder hasil uji | `finetune-id/eval-*` | **`finetune-id/a100/eval-*`**, terpisah dari hasil uji 4-bit di T4 |

### Tanpa pembanding: apa artinya

Setiap uji di repo ini secara bawaan juga menjawab soal dengan model dasar, lalu membandingkannya. Di panduan ini perbandingan itu dimatikan dengan `--no-vs-base`, dan tidak ada adapter lain yang dilatih. Akibatnya:

- **waktu GPU kira-kira separuh**, karena setiap soal hanya dijawab sekali;
- laporan berisi **skor v4 saja**, misalnya `HumanEval+ 120/164`. Angka itu tidak menunjukkan apakah v4 lebih baik atau lebih buruk dari model dasar atau v3;
- **gerbang G1–G3 di [`RENCANA_PYTHON.md`](RENCANA_PYTHON.md) tidak dinilai**, karena ketiganya berupa perbandingan. `papan_skor.py` tidak dipakai.

Kalau nanti perbandingan dibutuhkan, model dasar bisa diuji kapan saja dengan perintah di Lampiran 3. Adapter v4 tidak perlu dilatih ulang.

### Arti "konteks lebih panjang", supaya ekspektasinya tepat

Ada tiga angka yang sering tertukar:

1. **Konteks training (`max_seq_len` 16.384).** Ini panjang maksimum satu sampel latihan. Sampel yang lebih panjang **dibuang**, tidak dipotong. Sampel terpanjang di dataset sekarang ±6.200 token, jadi di 16.384 ke-103 sampel tetap ikut seluruhnya, sama seperti di T4. **Isi pelajarannya baru berubah kalau dataset ditambah sampel panjang**, misalnya proyek multi-file, website besar, atau percakapan perbaikan bug yang panjang. Sampel seperti itu akan terbuang di T4 tapi terpakai di sini. Pengaturan ini menyiapkan jalannya.
2. **Batas jawaban (`max_new_tokens` 12.000).** Ini dipakai saat model menjawab: website uji setelah training dan Web-eval. Dengan batas lebih tinggi, website panjang tidak terpotong di tengah.
3. **Jendela konteks model saat dipakai.** Ini bawaan Qwen3.5-4B, yang menurut model card-nya jauh di atas 16.384 token. LoRA tidak memperkecilnya. Yang menentukan mutu jawaban panjang adalah apakah model pernah dilatih dengan contoh panjang (poin 1).

### Urutan dan perkiraan waktu

Semuanya muat dalam **satu sesi A100**. Angka A100 di bawah masih perkiraan, karena belum pernah diukur di repo ini. ETA di setiap progress bar menunjukkan waktu yang sebenarnya.

| Bagian | Isi | Perkiraan |
|---|---|---|
| A | persiapan dan pasang paket | ±10 menit |
| B | cek data tanpa training | ±2 menit |
| C | training v4, lalu 2 website uji | ±15–40 menit, ditambah ±10 menit website uji |
| D | uji v4: HumanEval+, MBPP+, IndoPy-dev, Web-eval | ±40–60 menit |
| E | opsional: IndoPy-test, set uji akhir | ±5 menit |
| F | kumpulkan skor dan kirim hasil | ±5 menit |

A100 di Colab memakai **compute unit** (Colab Pro atau Pay As You Go). Sebelum mulai, cek sisa unit di **Runtime → View resources**. Semua hasil disimpan di Google Drive, dan setiap langkah bisa dilanjutkan kalau sesi terputus.

---

## Bagian A. Persiapan

### A1. Buka notebook dan pilih GPU

1. Buka notebook ini di Colab dengan **akun Google yang menyimpan folder `finetune-id`** di Drive-nya. Kalau kamu memakai lebih dari satu akun Gmail, pastikan yang dipakai akun yang benar.
2. Pilih **File → Save a copy in Drive**.
3. Pilih **Runtime → Change runtime type**. Di **Hardware accelerator**, pilih **A100 GPU**. Aktifkan **High-RAM** jika pilihannya ada, lalu **Save**.
4. Pastikan isi Drive-mu:

   | Yang dibutuhkan | Lokasi di Drive | Kalau tidak ada |
   |---|---|---|
   | hasil lama | tidak dibutuhkan | folder `MyDrive/finetune-id` dibuat otomatis. Akun Google yang baru tidak masalah |
   | ruang kosong | | sediakan ±3 GB. Adapter 16-bit dan checkpoint-nya lebih besar dari versi 4-bit |

### A2. Sel 1: cek GPU dan pasang paket

Jalankan **sekali di setiap runtime baru**.

```python
!nvidia-smi --query-gpu=name,memory.total --format=csv
!pip install --upgrade unsloth "evalplus @ git+https://github.com/evalplus/evalplus@26d6d00bb1fd0fa37f39c99d5290da67891d1c5e"
!pip install -q playwright && playwright install --with-deps chromium
```

- **Output yang benar:** baris pertama memuat `A100`, misalnya `NVIDIA A100-SXM4-40GB, 40960 MiB`. Setelah itu muncul log instalasi yang panjang.
- **Waktu:** ±4–6 menit.
- **Kalau muncul tombol Restart session:** klik tombolnya, lalu lanjut ke Sel 2. Paket yang sudah terpasang tidak hilang.
- **Kalau yang muncul `Tesla T4` atau `L4`:** A100 sedang tidak tersedia atau belum dipilih. Ulangi A1 langkah 3. Jangan lanjut di T4: training 16-bit dengan konteks 16.384 tidak muat di sana. Untuk T4, pakai [`PROSEDUR_V4.md`](PROSEDUR_V4.md).

### A3. Sel 2: mount Drive, unduh script, dan atur path

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

ROOT = "/content/drive/MyDrive/finetune-id"
HASIL = f"{ROOT}/a100"                                 # semua hasil uji A100
V4 = f"{ROOT}/v4/qwen3.5-4b-own/lora-adapter"          # dibuat oleh Bagian C
KONTEKS = 16384
LATIH = f"--out {ROOT}/v4 --no-load-in-4bit --max-seq-len {KONTEKS}"   # dipakai semua perintah train_unsloth.py
UJI = "--no-load-in-4bit --no-vs-base"                 # 16-bit, v4 saja tanpa model dasar
import subprocess
GPU = subprocess.run(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"], capture_output=True, text=True).stdout
assert "A100" in GPU or "H100" in GPU, f"GPU sekarang: {GPU.strip() or 'tidak ada'}. Pilih A100 (lihat A1)."
```

- **Pertama kali**, muncul jendela izin akses Google Drive. Pilih akun yang sama dengan A1.
- **Output yang benar:** `Mounted at /content/drive`, tanpa error.
- **Kalau sel berhenti dengan `GPU sekarang: Tesla T4...`:** runtime-nya bukan A100. Pengaturan di panduan ini tidak muat di T4, jadi sel sengaja dihentikan. Ulangi A1 langkah 3.
- **`LATIH` harus sama persis di semua perintah `train_unsloth.py`** (training, uji ulang, GGUF), karena folder hasil dan checkpoint ditentukan dari pengaturan itu.

---

## Bagian B. Cek data tanpa training

Sel ini memuat tokenizer saja, tanpa model, dan menghitung panjang setiap sampel dengan pengaturan v4.

```python
!python /content/train_unsloth.py prepare {LATIH}
```

| Baris yang muncul | Arti |
|---|---|
| `folder hasil: /content/drive/MyDrive/finetune-id/v4/qwen3.5-4b-own` | tanpa akhiran `-4bit`, jadi 16-bit. Folder lain tidak tersentuh |
| `data valid: 103 sampel dari ...` | **wajib 103.** Angka lain berarti `train.jsonl` lama terpakai (lihat Bagian H) |
| `sampel terpanjang: ... (6,2xx)` | sampel terpanjang saat ini |
| `103 sampel dipakai, 0 dibuang karena > 16384 token []` | semua sampel ikut dilatih |
| `3 epoch = 39 step, ±... token dilatih` | 103 sampel ÷ 8 per step, dibulatkan ke atas = 13 step per epoch, dikali 3 epoch |
| `perkiraan waktu (300–900 token/detik): ...` | perkiraan kasar untuk GPU ber-bf16, sekitar 15–40 menit |

Kalau ada sampel yang dibuang, catat id-nya dan kirim ke chat sebelum lanjut.

---

## Bagian C. Training v4

### C1. Latih dari model dasar

```python
!python /content/train_unsloth.py train {LATIH} --max-new-tokens 12000
```

Output penting, berurutan:

| Baris | Arti |
|---|---|
| `folder hasil: .../finetune-id/v4/qwen3.5-4b-own` | folder baru untuk v4 |
| banner Unsloth memuat `A100` dan `Bfloat16 = TRUE` | training berjalan di A100 dalam bf16 |
| **tidak ada** baris `melanjutkan dari ...` | training dimulai dari model dasar, bukan dari adapter lain |
| `data valid: 103 sampel` dan `103 sampel dipakai, 0 dibuang` | sama dengan Bagian B |
| `cek masking: ... token sampel pertama ikut dilatih` | hanya jawaban asisten yang dilatih, bukan prompt |
| progress bar sampai `39/39` dengan loss berkala | training berjalan |
| `[status] trained: adapter tersimpan` | adapter v4 sudah ada di Drive |
| dua jawaban website uji mengalir di layar, lalu `[status] done: selesai` | website uji dibuat dengan batas 12.000 token |

- **Kalau sesi terputus di tengah training**, jalankan perintah yang sama lagi. Checkpoint disimpan setiap 10 step, dan training melanjutkan dari checkpoint terakhir selama data dan pengaturannya sama.
- **Kalau muncul `CUDA out of memory`:** jalankan ulang dengan konteks `12288`, yang masih di atas sampel terpanjang:
  ```
  !python /content/train_unsloth.py train --out /content/drive/MyDrive/finetune-id/v4 --no-load-in-4bit --max-seq-len 12288 --max-new-tokens 12000
  ```
  Setelah itu ganti juga `KONTEKS = 12288` di Sel 2. Karena pengaturannya berubah, checkpoint lama otomatis dipindahkan ke `arsip/` dan training dimulai dari awal.
- **Website uji** disimpan di `MyDrive/finetune-id/v4/qwen3.5-4b-own/contoh-*.html`. Kolom `finished: True` di ringkasannya berarti jawaban selesai sebelum batas 12.000 token.

### C2. Cek adapter

```python
!ls {V4}
!cat {ROOT}/v4/qwen3.5-4b-own/status.json | head -30
```

`ls` harus menampilkan `adapter_config.json` dan `adapter_model.safetensors`. Di `status.json`, cari `train_loss` dan `train_runtime_min`, lalu catat keduanya untuk laporan. Training berjalan sebagai proses terpisah, jadi memori GPU langsung dilepas dan uji bisa langsung dijalankan.

---

## Bagian D. Mengukur v4

Setiap uji hanya menjawab soal dengan v4 (`--no-vs-base` di `UJI`). Hasilnya berupa skor dan daftar soal yang gagal, tanpa tabel perbandingan.

### D1. HumanEval+ (±5–8 menit)

```python
%run /content/eval_humaneval.py --adapter {V4} --results {HASIL}/eval-humaneval {UJI} --batch-size 32
```

Output-nya berupa progres `[v4-qwen3.5-4b-own] 64/164 soal ...`, lalu skor HumanEval dan HumanEval+.

### D2. MBPP+ (±15–20 menit)

```python
%run /content/eval_humaneval.py --dataset mbpp --adapter {V4} --results {HASIL}/eval-mbpp {UJI} --batch-size 32
```

### D3. IndoPy-dev (±3–5 menit)

```python
%run /content/indopy_eval.py --split dev --adapter {V4} --results {HASIL}/eval-indopy-dev {UJI} --batch-size 8
```

### D4. Web-eval dengan batas jawaban 12.000 token (±20–30 menit)

```python
%run /content/web_eval.py --adapter {V4} --results {HASIL}/eval-web {UJI} --max-seq-len {KONTEKS} --max-new-tokens 12000 --batch-size 2
```

- Website yang dibuat disimpan di `a100/eval-web/v4-qwen3.5-4b-own/situs/`.

**Kalau muncul `CUDA out of memory` di uji mana pun:** turunkan `--batch-size` (misalnya 32 → 16, atau 8 → 4), lalu jalankan perintah yang sama. Jawaban yang sudah tersimpan dilewati.

---

## Bagian E. Opsional: IndoPy-test, set uji akhir

Set test berisi 40 soal yang **dikunci**, untuk menilai Python berbahasa Indonesia dengan soal yang belum pernah dilihat saat menulis sampel.

```python
%run /content/indopy_eval.py --split test --adapter {V4} --results {HASIL}/eval-indopy-test {UJI} --batch-size 8
```

- **Jalankan sekali saja untuk v4 ini.** Jangan membaca soal atau jawaban yang gagal untuk menulis sampel latihan baru. Kalau itu dilakukan, set test bocor dan tidak bisa lagi dipakai sebagai ukuran yang jujur.
- Kalau ingin menunda penilaian akhir sampai data Fase 3 selesai, lewati bagian ini.

---

## Bagian F. Kumpulkan skor dan kirim hasil

### F1. Sel cek progres

Sel ini tidak memuat model, jadi bisa dijalankan kapan saja untuk melihat uji yang sudah selesai.

```python
import json
from pathlib import Path

H = Path(HASIL)
RUN = "v4-qwen3.5-4b-own"
print("adapter v4:", "sudah ada" if Path(V4, "adapter_config.json").exists() else "belum dilatih")
for folder in ["eval-humaneval", "eval-mbpp", "eval-indopy-dev", "eval-web", "eval-indopy-test"]:
    print(f"{folder:<18}", "selesai" if (H / folder / RUN / "ringkasan.json").exists() else "-")
```

Di akhir, semua baris harus `selesai`, kecuali `eval-indopy-test` kalau Bagian E dilewati.

### F2. Sel kumpulkan hasil

Sel ini mencetak skor v4 di setiap uji, website dan soal IndoPy-dev yang gagal, serta ringkasan training dalam satu output.

```python
def ringkasan(folder):
    f = H / folder / RUN / "ringkasan.json"
    return json.loads(f.read_text()) if f.exists() else None


print(f"=== Skor {RUN} ===")
for folder, kunci in [("eval-humaneval", ["humaneval_pass@1", "humaneval+_pass@1"]),
                      ("eval-mbpp", ["mbpp_pass@1", "mbpp+_pass@1"]), ("eval-indopy-dev", ["indopy_pass@1"]),
                      ("eval-indopy-test", ["indopy_pass@1"]), ("eval-web", ["web_lolos"])]:
    r = ringkasan(folder)
    print(f"{folder:<18}", ", ".join(f"{x.split('_')[0]} {round(r[x] * r['soal'])}/{r['soal']} ({r[x]:.1%})"
                                     for x in kunci) if r else "belum diuji")
if r := ringkasan("eval-web"):
    print(f"\n=== Web-eval: website yang gagal (format Cek kebutuhan {r['format_cek_kebutuhan']}/{r['soal']}) ===")
    for situs, alasan in r["gagal"].items():
        print(f"   {situs}: {alasan[:150]}")
if r := ringkasan("eval-indopy-dev"):
    print(f"\n=== IndoPy-dev: soal yang gagal (per tingkat {r['per_tingkat']}) ===")
    for soal, alasan in r["gagal"].items():
        print(f"   {soal.rsplit('/', 1)[1]}: {alasan[:150]}")
status = json.loads(Path(ROOT, "v4/qwen3.5-4b-own/status.json").read_text())
print("\n=== Training v4 ===")
print({k: status.get(k) for k in ("data", "result", "tests")})
```

Sel ini memakai `H` dan `RUN` dari Sel cek progres, jadi jalankan sel itu dulu.

### F3. Kirim ke chat

Salin dan kirim:
1. output sel kumpulkan hasil (F2);
2. baris `sampel terpanjang` dan `sampel dipakai` dari log training.

Untuk IndoPy-test, kirim **skornya saja**, tanpa soal atau jawaban yang gagal.

---

## Bagian G. Opsional: ekspor GGUF

Untuk memakai v4 di Ollama atau llama.cpp:

```python
!python /content/train_unsloth.py gguf {LATIH}
```

Hasilnya ada di `MyDrive/finetune-id/v4/qwen3.5-4b-own/gguf/`. `LATIH` harus sama dengan saat training. Kalau berbeda, script mencari adapter di folder lain.

---

## Bagian H. Mengatasi masalah

| Gejala | Penyebab | Solusi |
|---|---|---|
| Baris pertama Sel 1 bukan A100 | A100 penuh atau belum dipilih | Runtime → Change runtime type → A100 GPU. Kalau tetap tidak tersedia, coba lagi nanti atau pakai [`PROSEDUR_V4.md`](PROSEDUR_V4.md) di T4 |
| `Cannot connect to GPU backend` | compute unit habis atau A100 penuh | cek Runtime → View resources. Semua hasil aman di Drive |
| Sel 2 berhenti dengan `GPU sekarang: ...` | runtime bukan A100 | pilih A100 (A1 langkah 3), lalu jalankan Sel 1 dan Sel 2 lagi |
| `CUDA out of memory` saat training | konteks 16.384 tidak muat di A100 40 GB | ulangi dengan `--max-seq-len 12288` (lihat C1) |
| `CUDA out of memory` saat uji | batch terlalu besar | turunkan `--batch-size`, lalu ulangi perintah yang sama |
| `data valid: 82 sampel` atau angka lain selain 103 | `train.jsonl` lama terpakai | hapus `MyDrive/finetune-id/v4/train.jsonl`, lalu ulangi Bagian B dan C |
| `data atau pengaturan berubah: hasil lama dipindah ke .../arsip/...` | pengaturan training berbeda dari run sebelumnya | wajar. Training dimulai dari awal, dan hasil lama tetap tersimpan di `arsip/` |
| `adapter tidak ditemukan` | adapter belum dilatih, atau Drive belum di-mount | jalankan Sel 2. Uji v4 butuh Bagian C |
| `evalplus yang terpasang (0.3.1 dari PyPI)...` | EvalPlus versi PyPI terpasang | jalankan perintah `pip install --force-reinstall --no-deps ...` yang ditampilkan, Restart session, lalu Sel 2 |
| `No module named 'playwright'` atau `Executable doesn't exist` | Playwright belum terpasang di runtime ini | jalankan baris terakhir Sel 1 |
| Skor v4 janggal setelah dilatih ulang | jawaban uji adapter lama dipakai ulang | hapus subfolder `v4-qwen3.5-4b-own` di setiap folder `a100/eval-*`, lalu ulangi Bagian D |

---

## Lampiran 1. Hasil di Google Drive

```
MyDrive/finetune-id/
├── v4/
│   ├── train.jsonl                         data yang dipakai training v4
│   └── qwen3.5-4b-own/
│       ├── lora-adapter/                   adapter v4 (16-bit, konteks 16.384)
│       ├── checkpoints/                    untuk melanjutkan training yang terputus
│       ├── status.json                     loss, lama training, hasil website uji
│       └── contoh-*.html                   website uji (batas 12.000 token)
└── a100/
    ├── eval-humaneval/   v4-qwen3.5-4b-own/ (jawaban, ringkasan.json)
    ├── eval-mbpp/        (susunan sama)
    ├── eval-indopy-dev/  (susunan sama)
    ├── eval-indopy-test/ (susunan sama, jika Bagian E dijalankan)
    └── eval-web/         (susunan sama; situs/ berisi website yang dibuat)
```

## Lampiran 2. Semua perintah sekaligus

```
Sel 1   pasang paket (sekali per runtime)
Sel 2   mount Drive, unduh script, ROOT/HASIL/V4/KONTEKS/LATIH/UJI (setiap sesi)
cek     !python /content/train_unsloth.py prepare {LATIH}
latih   !python /content/train_unsloth.py train {LATIH} --max-new-tokens 12000
v4      %run /content/eval_humaneval.py --adapter {V4} --results {HASIL}/eval-humaneval {UJI} --batch-size 32
        %run /content/eval_humaneval.py --dataset mbpp --adapter {V4} --results {HASIL}/eval-mbpp {UJI} --batch-size 32
        %run /content/indopy_eval.py --split dev --adapter {V4} --results {HASIL}/eval-indopy-dev {UJI} --batch-size 8
        %run /content/web_eval.py --adapter {V4} --results {HASIL}/eval-web {UJI} --max-seq-len {KONTEKS} --max-new-tokens 12000 --batch-size 2
akhir   %run /content/indopy_eval.py --split test --adapter {V4} --results {HASIL}/eval-indopy-test {UJI} --batch-size 8
skor    sel cek progres (F1) dan sel kumpulkan hasil (F2)
```

## Lampiran 3. Kalau nanti butuh pembanding model dasar

Jawaban v4 yang sudah tersimpan dipakai ulang, jadi hanya model dasar yang dijawab. Hapus `--no-vs-base` dari `UJI`, lalu jalankan lagi perintah uji di Bagian D:

```
UJI = "--no-load-in-4bit"
%run /content/eval_humaneval.py --adapter {V4} --results {HASIL}/eval-humaneval {UJI} --batch-size 32
(begitu juga MBPP+, IndoPy-dev, Web-eval)
%run /content/papan_skor.py --root {HASIL} --tag v4-qwen3.5-4b-own
```

Papan skor lalu menilai G1 dan G2 (dengan IndoPy-test). G3 tetap butuh adapter pembanding untuk Web-eval.

## Lampiran 4. Menambah sampel panjang nanti

Konteks 16.384 baru berguna kalau ada sampel yang lebih panjang dari ±6.200 token. Saat menambahkannya:
- periksa panjangnya dengan `python scripts/validate.py --tokenizer Qwen/Qwen3.5-4B --max-len 16384`;
- ingat bahwa sampel di atas 6.144 token **terbuang kalau dilatih di T4**. Jadi model yang dilatih di T4 dan di A100 tidak lagi belajar dari data yang sama;
- sampel Python tetap ditulis di `data/python-src/<id>/`, lalu dibangun dengan `scripts/build_python_samples.py` dan diperiksa dengan `scripts/decontaminate.py`.

## Catatan hukum

- **Klaim mutu.** Angka dari prosedur ini adalah uji internal. Kalau model ditawarkan sebagai produk atau jasa:
  - sebutkan kondisi ujinya (greedy, pass@1, versi EvalPlus, 16-bit di A100);
  - sebut IndoPy dan Web-eval sebagai uji buatan sendiri;
  - karena prosedur ini tidak membandingkan v4 dengan model dasar atau versi lain, **jangan klaim v4 "lebih baik" atau "meningkat"**. Yang bisa dinyatakan hanya skor v4 apa adanya beserta kondisi ujinya.

  Klaim yang melebihkan mutu berisiko melanggar Pasal 9 ayat (1) huruf a dan Pasal 10 huruf b UU No. 8 Tahun 1999 tentang Perlindungan Konsumen.
- **Membagikan GGUF atau adapter.** Qwen3.5-4B dirilis dengan lisensi Apache 2.0. Pastikan lagi di model card saat membagikan. Kalau berlaku, Pasal 4 lisensi itu mewajibkan:
  - salinan lisensi ikut disertakan;
  - pemberitahuan bahwa file sudah diubah (fine-tuning);
  - pemberitahuan hak cipta dan atribusi dari karya asal dipertahankan.
