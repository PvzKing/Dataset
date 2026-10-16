"""Pekerja simulasi: jalankan sel Python dari docs/PANDUAN_V7_A100.md dengan GPU, Colab, git, sulingan, training, dan
uji tiruan.

Dipanggil oleh cek.py, satu skenario per proses: python jalankan.py <semua|langkah>.
Modul tiruan google.colab, unsloth, evalplus, dan playwright dipakai bersama dengan tests/simulasi_v5/stubs.
"""
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
cells = re.findall(r"^```python\n(.*?)^```", (REPO / "docs/PANDUAN_V7_A100.md").read_text(), re.S | re.M)
sel1, sel2, sel3, progres = cells[0], cells[1], cells[2], cells[7]
assert progres.startswith("def baris_jsonl"), "urutan sel di panduan berubah: perbarui indeks di jalankan.py"

sys.path.insert(0, str(HERE.parent / "simulasi_v5" / "stubs"))
(Path(os.environ["HOME"]) / ".cache/ms-playwright/chromium-sim").mkdir(parents=True, exist_ok=True)
Path("/content/drive/MyDrive").mkdir(parents=True, exist_ok=True)


def palsu(argv, *a, **k):
    if argv[0] == "nvidia-smi":
        return subprocess.CompletedProcess(argv, 0, stdout="NVIDIA A100-SXM4-40GB, 40960 MiB\n", stderr="")
    if argv[:2] == ["git", "clone"]:
        ref, dest = argv[argv.index("--branch") + 1], Path(argv[-1])
        shutil.copytree(REPO, dest, ignore=shutil.ignore_patterns(".git", "node_modules", "__pycache__"))
        for nama in ("eval-suite/indopy_eval.py", "eval-suite/web_eval.py", "humaneval-bench-script/eval_humaneval.py"):
            shutil.copy(HERE / "fake/eval_tiruan.py", dest / nama)
        shutil.copy(HERE / "fake/train_unsloth.py", dest / "scripts/train_unsloth.py")
        shutil.copy(HERE / "fake/sulingan.py", dest / "scripts/sulingan.py")
        if ref == "main":  # main dianggap belum punya V7: Sel 1 harus pindah ke cabang berikutnya
            (dest / "scripts/sulingan.py").unlink()
        print(f"[sim] clone {ref}")
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")
    if argv[:2] == ["git", "-C"]:
        return subprocess.CompletedProcess(argv, 0, stdout="abc1234\n", stderr="")
    raise AssertionError(f"perintah tak terduga: {argv}")


subprocess.run = palsu
time.sleep = lambda s: None
mode = sys.argv[1]
s1 = sel1.replace("EKSPOR_16BIT = False", "EKSPOR_16BIT = True") if os.environ.get("SIM_16BIT") else sel1
kode = [s1, sel2, progres] if mode == "langkah" else [s1, sel2, sel3]
ns = {}
try:
    for k in kode:
        exec(compile(k, "<sel>", "exec"), ns)
except SystemExit as e:
    print("SystemExit:", e)
