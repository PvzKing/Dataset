"""Bangun panel Colab berbentuk formulir untuk scripts/panel_v4.py:
  notebooks/v4_pilot_interaktif.ipynb  mode pilot (T4): ukur v3, latih v4-pilot, ukur v4-pilot
  notebooks/v4_a100_interaktif.ipynb   mode a100: latih v4 dari model dasar (konteks 16.384), ukur tanpa pembanding

Pemakaian:
    python scripts/build_panel_notebook.py
"""
import json
from pathlib import Path

NOTEBOOKS = Path(__file__).resolve().parent.parent / "notebooks"
OUT = NOTEBOOKS / "v4_pilot_interaktif.ipynb"
OUT_A100 = NOTEBOOKS / "v4_a100_interaktif.ipynb"

PANEL = "https://raw.githubusercontent.com/PvzKing/Dataset/main/scripts/panel_v4.py"
LANGKAH = ["Otomatis: semua yang belum selesai", "HumanEval+ v3", "IndoPy-dev v3", "Web-eval v3", "Latih v4-pilot",
           "HumanEval+ v4", "IndoPy-dev v4", "Web-eval v4", "MBPP+ v4", "MBPP+ v3"]
LANGKAH_A100 = ["Otomatis: semua yang belum selesai", "Latih v4", "HumanEval+ v4", "MBPP+ v4", "IndoPy-dev v4",
                "Web-eval v4", "IndoPy-test v4"]

def md(text):
    return {"cell_type": "markdown", "metadata": {}, "source": text.strip("\n").splitlines(True)}

def form(text):
    return {"cell_type": "code", "execution_count": None, "metadata": {"cellView": "form"}, "outputs": [],
            "source": text.strip("\n").splitlines(True)}

IMPORT = '''import sys
sys.path.insert(0, "/content")
try:
    import panel_v4
except ImportError:
    raise SystemExit("Jalankan sel 1 (Siapkan) dulu.")'''

cells = [
    md("""
# Panel v4-pilot

Notebook ini mengukur v3, melatih v4-pilot, mengukurnya, lalu membuat laporan. Semua langkah dijalankan dari tombol di bawah, tanpa perlu menyalin perintah.

**Cara pakai**
1. Pilih **Runtime → Change runtime type → T4 GPU → Save**.
2. Jalankan **sel 1 (Siapkan)** dengan tombol ▶ di kiri sel. Saat diminta, izinkan akses Google Drive dengan **akun yang menyimpan folder `finetune-id`**. Tunggu sampai semua baris bertanda ✅.
3. Jalankan **sel 2 (Jalankan)** dengan pilihan *Otomatis*. Panel menjalankan semua langkah yang belum selesai secara berurutan, sambil menampilkan output dan perkiraan waktunya. Biarkan tab tetap terbuka.
4. **Kalau Colab terputus atau kuota GPU habis:** buka notebook ini lagi, lalu jalankan sel 1 dan sel 2. Panel melanjutkan dari langkah yang belum selesai, dan hasil yang sudah tersimpan di Drive tidak diulang.
5. Setelah semua langkah ✅, jalankan **sel 4** dan kirim teksnya ke chat.

Total pekerjaan sekitar 6–8 jam GPU, jadi di Colab gratis biasanya selesai dalam 2–3 sesi. Sel 3 menampilkan progres kapan saja.

Rincian setiap langkah, arti output-nya, dan cara mengatasi masalah ada di panduan manual [`docs/PROSEDUR_V4.md`](https://github.com/PvzKing/Dataset/blob/main/docs/PROSEDUR_V4.md).
"""),
    form(f'''
#@title 1️⃣ Siapkan (jalankan di awal setiap sesi)
#@markdown Sel ini mengecek GPU, memasang paket yang belum ada (pertama kali ±5–8 menit), menghubungkan Google Drive, mengunduh script terbaru, dan memeriksa adapter v3.
#@markdown
#@markdown **Path adapter v3** di Google Drive. Biarkan apa adanya jika foldernya mengikuti panduan.
adapter_v3 = "/content/drive/MyDrive/finetune-id/v3/qwen3.5-4b-own-4bit/lora-adapter"  #@param {{type:"string"}}
import importlib, sys, urllib.request
urllib.request.urlretrieve("{PANEL}", "/content/panel_v4.py")
sys.path.insert(0, "/content")
import panel_v4
importlib.reload(panel_v4)
panel_v4.siapkan(adapter_v3)
'''),
    form(f'''
#@title 2️⃣ Jalankan
#@markdown **Otomatis** menjalankan semua langkah yang belum selesai secara berurutan. Atau pilih satu langkah untuk menjalankan langkah itu saja.
langkah = "{LANGKAH[0]}"  #@param {json.dumps(LANGKAH, ensure_ascii=False)}
#@markdown Centang untuk ikut menjalankan **MBPP+ v3**. Opsional, ±50 menit; menunjukkan apakah v3 sudah menggeser kemampuan Python umum.
sertakan_mbpp_v3 = False  #@param {{type:"boolean"}}
{IMPORT}
panel_v4.jalankan(langkah, sertakan_mbpp_v3)
'''),
    form(f'''
#@title 3️⃣ Lihat progres
#@markdown Tidak memuat model, jadi aman dijalankan kapan saja, termasuk saat membuka sesi baru.
sertakan_mbpp_v3 = False  #@param {{type:"boolean"}}
{IMPORT}
panel_v4.progres(sertakan_mbpp_v3)
'''),
    form(f'''
#@title 4️⃣ Papan skor dan laporan untuk dikirim
#@markdown Menampilkan papan skor v3 dan v4-pilot, website dan soal yang gagal, serta ringkasan training. Teksnya juga disimpan ke `finetune-id/laporan-v4-pilot.txt` di Drive.
{IMPORT}
panel_v4.laporan()
'''),
    md("""
## Kalau ada masalah

Saat langkah gagal, panel menampilkan saran perbaikannya. Yang paling sering:

| Gejala | Yang dilakukan |
|---|---|
| Sel 1 menampilkan ❌ GPU | Runtime → Change runtime type → T4 GPU, lalu jalankan sel 1 lagi |
| `Cannot connect to GPU backend` | kuota GPU gratis harian habis. Coba lagi nanti; semua hasil aman di Drive |
| ❌ Adapter v3 | sel 1 menampilkan daftar adapter yang ada di Drive. Salin path yang benar ke kolom `adapter_v3`, lalu jalankan sel 1 lagi |
| `CUDA out of memory` | jalankan sel 2 lagi. Jika berulang, pilih Runtime → Restart session, lalu sel 1 dan sel 2 |
| Ingin menghentikan langkah yang sedang berjalan | klik ■ di sel 2. Jawaban yang sudah tersimpan tidak hilang, dan langkah itu dilanjutkan saat sel 2 dijalankan lagi |

Output setiap langkah juga disimpan di `finetune-id/panel-log/` di Drive.
"""),
]
cells_a100 = [
    md("""
# Panel v4 di A100: training dari awal dengan konteks panjang

Notebook ini melatih **v4 dari model dasar** Qwen3.5-4B, mengukurnya, lalu membuat laporan. **Tanpa pembanding:** v3 dan model dasar tidak dilatih ulang atau diuji, jadi laporannya berisi skor v4 apa adanya. Semua langkah dijalankan dari tombol di bawah. **Tidak butuh hasil lama di Drive**, jadi bisa dimulai dari akun Google yang baru.

| | v4 |
|---|---|
| Data | `data/train.jsonl` terbaru (125 sampel) |
| Titik awal | model dasar (bukan lanjutan adapter lain) |
| Resep | LoRA 16-bit (bf16), konteks 16.384, batas jawaban 12.000 token, 3 epoch, lr 1e-4, r16 |
| Uji | HumanEval+, MBPP+, IndoPy-dev, Web-eval; IndoPy-test opsional. Hasil di `finetune-id/a100/` |

**Cara pakai**
1. Pilih **Runtime → Change runtime type → A100 GPU**. Aktifkan **High-RAM** jika ada, lalu **Save**. A100 memakai compute unit; cek sisanya di **Runtime → View resources**.
2. Jalankan **sel 1 (Siapkan)** dengan tombol ▶. Saat diminta, izinkan akses Google Drive dengan **akun yang menyimpan folder `finetune-id`**. Tunggu sampai semua baris bertanda ✅.
3. Jalankan **sel 2 (Jalankan)** dengan pilihan *Otomatis*. Panel melatih v4, lalu menjalankan keempat uji. Biarkan tab tetap terbuka.
4. **Kalau Colab terputus:** buka notebook ini lagi, lalu jalankan sel 1 dan sel 2. Training dilanjutkan dari checkpoint terakhir, dan jawaban uji yang sudah tersimpan tidak diulang.
5. Setelah semua langkah ✅, jalankan **sel 4** dan kirim teksnya ke chat.

Perkiraan kasarnya sekitar 1,5 jam GPU (belum pernah diukur di A100), jadi biasanya selesai dalam satu sesi. Sel 3 menampilkan progres kapan saja.

**Tentang konteks 16.384:** sampel terpanjang di dataset sekarang ±6.200 token, jadi semua sampel sudah ikut dilatih, sama seperti di T4. Konteks panjang baru mengubah isi pelajaran setelah dataset ditambah sampel yang lebih panjang. Yang langsung terasa adalah batas jawaban 12.000 token, sehingga website panjang tidak terpotong.

Rincian setiap langkah dan arti output-nya ada di panduan [`docs/PROSEDUR_V4_A100.md`](https://github.com/PvzKing/Dataset/blob/main/docs/PROSEDUR_V4_A100.md).
"""),
    form(f'''
#@title 1️⃣ Siapkan (jalankan di awal setiap sesi)
#@markdown Sel ini mengecek GPU (harus A100), memasang paket yang belum ada (pertama kali ±5–8 menit), menghubungkan Google Drive, dan mengunduh script terbaru. Folder `finetune-id` dibuat otomatis jika belum ada.
#@markdown
#@markdown **Konteks training** (`max_seq_len`). Pilih 12288 hanya jika training kehabisan VRAM. Mengubah nilai ini setelah training dimulai akan mengulang training dari awal.
konteks_training = 16384  #@param [16384, 12288] {{type:"raw"}}
import importlib, sys, urllib.request
urllib.request.urlretrieve("{PANEL}", "/content/panel_v4.py")
sys.path.insert(0, "/content")
import panel_v4
importlib.reload(panel_v4)
panel_v4.siapkan(mode="a100", konteks=konteks_training)
'''),
    form(f'''
#@title 2️⃣ Jalankan
#@markdown **Otomatis** menjalankan semua langkah yang belum selesai secara berurutan: latih v4, lalu uji v4. Atau pilih satu langkah untuk menjalankan langkah itu saja.
langkah = "{LANGKAH_A100[0]}"  #@param {json.dumps(LANGKAH_A100, ensure_ascii=False)}
#@markdown Centang untuk ikut menjalankan **IndoPy-test**, yaitu set uji akhir (40 soal yang dikunci, ±5 menit). Jalankan **sekali saja** untuk v4 ini, dan jangan pakai soal atau jawabannya untuk menulis sampel latihan.
sertakan_indopy_test = False  #@param {{type:"boolean"}}
{IMPORT}
panel_v4.jalankan(langkah, sertakan_indopy_test)
'''),
    form(f'''
#@title 3️⃣ Lihat progres
#@markdown Tidak memuat model, jadi aman dijalankan kapan saja, termasuk saat membuka sesi baru.
sertakan_indopy_test = False  #@param {{type:"boolean"}}
{IMPORT}
panel_v4.progres(sertakan_indopy_test)
'''),
    form(f'''
#@title 4️⃣ Papan skor dan laporan untuk dikirim
#@markdown Menampilkan skor v4 di setiap uji, website dan soal IndoPy-dev yang gagal, serta ringkasan training. Teksnya juga disimpan ke `finetune-id/laporan-v4-a100.txt` di Drive.
{IMPORT}
panel_v4.laporan()
'''),
    md("""
## Kalau ada masalah

Saat langkah gagal, panel menampilkan saran perbaikannya. Yang paling sering:

| Gejala | Yang dilakukan |
|---|---|
| Sel 1 menampilkan ❌ GPU | runtime-nya bukan A100. Runtime → Change runtime type → A100 GPU, lalu jalankan sel 1 lagi. Untuk T4, pakai notebook `v4_pilot_interaktif` |
| `Cannot connect to GPU backend` | A100 sedang penuh atau compute unit habis. Coba lagi nanti; semua hasil aman di Drive |
| `⚠️ VRAM habis ... diulang dengan batch ...` | tidak perlu tindakan. Panel mengulang uji itu dengan batch lebih kecil, dan jawaban yang sudah tersimpan tidak hilang |
| VRAM habis saat training | pilih `konteks_training` 12288 di sel 1, jalankan sel 1, lalu sel 2 |
| Ingin menghentikan langkah yang sedang berjalan | klik ■ di sel 2. Langkah itu dilanjutkan saat sel 2 dijalankan lagi |

Output setiap langkah juga disimpan di `finetune-id/panel-log/` di Drive.
"""),
]


def tulis(path, isi, gpu):
    colab = {"gpuType": gpu, "provenance": []}
    if gpu == "A100":
        colab["machine_shape"] = "hm"  # High-RAM
    nb = {"cells": isi, "metadata": {"accelerator": "GPU", "colab": colab,
          "kernelspec": {"display_name": "Python 3", "name": "python3"}, "language_info": {"name": "python"}},
          "nbformat": 4, "nbformat_minor": 0}
    path.write_text(json.dumps(nb, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"ditulis {path.name}: {len(isi)} sel")


tulis(OUT, cells, "T4")
tulis(OUT_A100, cells_a100, "A100")
