"""Pekerja simulasi: jalankan sel Python dari docs/PANDUAN_V6_A100.md dengan GPU, Colab, training, dan uji tiruan.

Dipanggil oleh cek.py, satu skenario per proses: python jalankan.py <semua|langkah|oom|tanpa-pilih>.
Modul tiruan google.colab, unsloth, evalplus, dan playwright dipakai bersama dengan tests/simulasi_v5/stubs.
"""
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
cells = re.findall(r"^```python\n(.*?)^```", (REPO / "docs/PANDUAN_V6_A100.md").read_text(), re.S | re.M)
sel1, sel2, sel3, progres = cells[0], cells[1], cells[2], cells[8]

sys.path.insert(0, str(HERE.parent / "simulasi_v5" / "stubs"))
(Path(os.environ["HOME"]) / ".cache/ms-playwright/chromium-sim").mkdir(parents=True, exist_ok=True)
Path("/content/drive/MyDrive").mkdir(parents=True, exist_ok=True)


def nvidia_smi(argv, *a, **k):
    if argv[0] == "nvidia-smi":
        return subprocess.CompletedProcess(argv, 0, stdout="NVIDIA A100-SXM4-40GB, 40960 MiB\n", stderr="")
    raise AssertionError(f"perintah tak terduga: {argv}")


def unduh(url, dest):
    ref_path = url.split("PvzKing/Dataset/", 1)[1]
    name = ref_path.rsplit("/", 1)[1]
    if ref_path.startswith("main/scripts/train_unsloth.py"):  # main dianggap belum mendukung V6: Sel 1 harus pindah cabang
        Path(dest).write_text("# script lama dengan own+bench saja\n")
        return
    if "/data/bench-support/" in ref_path:
        shutil.copy(REPO / "data/bench-support" / name, dest)
        return
    src = {"train_unsloth.py": HERE / "fake/train_unsloth.py", "train.jsonl": REPO / "data/train.jsonl"}
    shutil.copy(src.get(name, HERE / "fake/eval_tiruan.py"), dest)


subprocess.run = nvidia_smi
urllib.request.urlretrieve = unduh
time.sleep = lambda s: None
mode = sys.argv[1]
ns = {}
s1 = sel1 if mode == "oom" else sel1.replace("EKSPOR_16BIT = False", "EKSPOR_16BIT = True")
if mode == "tanpa-pilih":
    s1 = s1.replace("PILIH_EPOCH_TERBAIK = True", "PILIH_EPOCH_TERBAIK = False")
kode = [s1, sel2, progres] if mode == "langkah" else [s1, sel2, sel3]
try:
    for k in kode:
        exec(compile(k, "<sel>", "exec"), ns)
except SystemExit as e:
    print("SystemExit:", e)
