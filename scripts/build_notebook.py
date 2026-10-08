"""Bangun notebooks/train_colab.ipynb dari scripts/train_unsloth.py dan docs/RUNBOOK_CLAUDE.md.

Notebook ini mandiri: isi script training dan runbook disisipkan ke sel `%%writefile`, sehingga notebook cukup
di-upload ke Colab tanpa clone repo. Jalankan ulang setelah mengubah salah satu file sumber:

    python scripts/build_notebook.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GUIDE = "https://github.com/PvzKing/Dataset/blob/main/docs/PANDUAN_TRAINING.md"
cells = []


def md(src):
    cells.append({"cell_type": "markdown", "metadata": {}, "source": src.strip("\n")})


def code(src):
    cells.append({"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": src.strip("\n")})


md(f"""
# Fine-tuning Qwen3.5-4B di Google Colab

Notebook ini mandiri: tidak perlu menghubungkan Colab ke GitHub. Panduan lengkapnya ada di [PANDUAN_TRAINING.md]({GUIDE}).

1. Pilih GPU di menu *Runtime → Change runtime type*. T4 tersedia gratis.
2. Jalankan sel **1–4** berurutan. Konfigurasi ada di blok `CONFIG` di sel 4.
3. Pilih salah satu cara:
   - **Mode A:** jalankan sendiri dengan satu sel.
   - **Mode B:** biarkan **Claude** yang menjalankan, memantau, dan memperbaiki masalah lewat terminal.

Data `own` diunduh otomatis dari repo publik. Bisa juga upload `train.jsonl` ke panel *Files* (`/content`).
Semua hasil disimpan ke Google Drive. Jika sesi putus, jalankan ulang sel 1–4 lalu mode yang sama, dan training
**dilanjutkan dari checkpoint terakhir**.
""")

md("## 1. Cek GPU")
code("!nvidia-smi --query-gpu=name,memory.total --format=csv")

md("""
## 2. Instalasi
Butuh ±2–4 menit. Jika Colab meminta *Restart session*, klik tombolnya lalu lanjut ke sel 3. Sel ini tidak perlu diulang.
""")
code("""
%%capture
!pip install --upgrade unsloth
""")

md("""
## 3. Mount Google Drive
Pilih akun Google Anda, lalu izinkan akses. Hasil training disimpan di `MyDrive/finetune-id`.
""")
code("""
from google.colab import drive
drive.mount("/content/drive")
""")

md("""
## 4. Script training
Sel ini **hanya menyimpan** script ke `/content/train_unsloth.py`; training belum berjalan. Ubah blok `CONFIG` jika
perlu, lalu jalankan sel ini. Jika `CONFIG` diubah lagi nanti, jalankan ulang sel ini.
""")
code("%%writefile /content/train_unsloth.py\n" + (ROOT / "scripts/train_unsloth.py").read_text(encoding="utf-8"))

md("""
---
## Mode A: jalankan sendiri

Satu sel ini menjalankan seluruh proses:
1. cek data;
2. training;
3. simpan adapter;
4. buat dua website uji.

Progress dan ETA tampil di bawah sel. Biarkan tab browser tetap terbuka.
""")
code("!python /content/train_unsloth.py train")

md("### Lihat hasil")
code("""
import html
import json
import os
import subprocess
from IPython.display import HTML, display

info = json.loads(subprocess.check_output(["python", "/content/train_unsloth.py", "info"]))
RUN_DIR = info["run_dir"]
status = json.load(open(f"{RUN_DIR}/status.json"))
print(json.dumps({k: status.get(k) for k in ("stage", "message", "result", "tests", "hint")}, indent=1, ensure_ascii=False))
for name in sorted(os.listdir(RUN_DIR)):
    if name.endswith(".html"):
        page = open(f"{RUN_DIR}/{name}", encoding="utf-8").read()
        display(HTML(f'<h3>{name}</h3><iframe srcdoc="{html.escape(page)}" '
                     'style="width:100%;height:600px;border:1px solid #ccc"></iframe>'))
""")

md("""
---
## Mode B: Claude yang mengontrol lewat terminal

Claude Code berjalan di terminal VM Colab ini, dan seluruh kendali dilakukan lewat terminal tersebut. Claude bisa:
- menjalankan training di latar belakang;
- memantau log, `status.json`, dan GPU;
- menangani error umum: kehabisan memori, paket bermasalah, proses mati;
- memeriksa website hasil uji, lalu melaporkan semuanya ke Anda.

**Syarat:** akun Claude Pro, Max, Team, atau Enterprise (atau akun API Console).

### B1. Simpan aturan kerja Claude
Sel ini menyimpan aturan kerja Claude ke `/content/CLAUDE.md`. Claude Code membaca file itu otomatis saat dijalankan
di folder `/content`.
""")
code("%%writefile /content/CLAUDE.md\n" + (ROOT / "docs/RUNBOOK_CLAUDE.md").read_text(encoding="utf-8"))

md("### B2. Pasang Claude Code dan buka terminal")
code("""
!curl -fsSL https://claude.ai/install.sh | bash
!pip install -q colab-xterm
%load_ext colabxterm
%xterm
""")

md("""
### B3. Di terminal

1. Ketik perintah ini lalu Enter:
   ```
   cd /content && export PATH="$HOME/.local/bin:$PATH" && claude
   ```
2. **Login:**
   - Pilih login dengan akun Claude. Buka link yang muncul di tab baru, login, lalu salin kode yang diberikan.
   - Tempel kode itu di terminal (Ctrl+Shift+V atau klik kanan → Paste).
   - Jika muncul pertanyaan *trust this folder*, pilih **Yes**.
3. Ketik perintah untuk Claude:
   ```
   Latih model sesuai CONFIG di train_unsloth.py mengikuti CLAUDE.md, pantau sampai selesai, lalu laporkan hasilnya.
   ```
4. **Izin:** saat Claude meminta izin menjalankan perintah, pilih **Yes, and don't ask again** untuk perintah yang aman
   seperti `python /content/train_unsloth.py`, `tail`, `cat`, `nvidia-smi`, dan `sleep`.
5. Biarkan tab Colab tetap terbuka. Anda bisa bertanya kapan saja, misalnya `gimana progresnya?`, atau meminta
   `stop training`.

Training berjalan di latar belakang, jadi tetap jalan walaupun Anda keluar dari Claude atau terminal tertutup. Untuk
kembali memantau, jalankan ulang sel B2, lalu `cd /content && claude --continue`.
""")

md("""
---
## Opsional: ekspor GGUF untuk Ollama / llama.cpp
Jalankan setelah training selesai. Butuh ±15–40 menit dan ±3 GB ruang di Drive (untuk 4B).
""")
code("!python /content/train_unsloth.py gguf")

nb = {
    "cells": cells,
    "metadata": {
        "accelerator": "GPU",
        "colab": {"gpuType": "T4", "provenance": []},
        "kernelspec": {"display_name": "Python 3", "name": "python3"},
        "language_info": {"name": "python"},
    },
    "nbformat": 4,
    "nbformat_minor": 0,
}
for c in cells:  # nbformat menyimpan source sebagai daftar baris
    lines = c["source"].split("\n")
    c["source"] = [line + "\n" for line in lines[:-1]] + [lines[-1]]

out = ROOT / "notebooks/train_colab.ipynb"
with open(out, "w", encoding="utf-8", newline="\n") as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)
    f.write("\n")
print(f"ditulis: {out.relative_to(ROOT)} ({len(cells)} sel)")
