"""Bangun notebooks/v4_pilot_interaktif.ipynb: panel Colab berbentuk formulir untuk scripts/panel_v4.py.

Pemakaian:
    python scripts/build_panel_notebook.py
"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "notebooks" / "v4_pilot_interaktif.ipynb"

PANEL = "https://raw.githubusercontent.com/PvzKing/Dataset/main/scripts/panel_v4.py"
LANGKAH = ["Otomatis: semua yang belum selesai", "HumanEval+ v3", "IndoPy-dev v3", "Web-eval v3", "Latih v4-pilot",
           "HumanEval+ v4", "IndoPy-dev v4", "Web-eval v4", "MBPP+ v4", "MBPP+ v3"]

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
nb = {"cells": cells, "metadata": {"accelerator": "GPU", "colab": {"gpuType": "T4", "provenance": []},
      "kernelspec": {"display_name": "Python 3", "name": "python3"}, "language_info": {"name": "python"}},
      "nbformat": 4, "nbformat_minor": 0}
OUT.write_text(json.dumps(nb, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(f"ditulis {OUT.name}: {len(cells)} sel")
