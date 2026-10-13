"""Uji sel-sel docs/PANDUAN_V5_A100.md tanpa GPU dan tanpa Colab.

GPU, google.colab, train_unsloth.py, dan script uji diganti tiruan yang menulis file hasil dengan struktur yang sama.
Yang diuji adalah alur panduan: pilih cabang, cek data, training, uji, pilih epoch, ekspor, laporan, matikan runtime,
melanjutkan setelah terputus, VRAM habis saat uji, dan training yang gagal.

Simulasi menulis ke /content (path Colab yang dipakai panduan), jadi jalankan hanya di container sekali pakai:
    python tests/simulasi_v5/cek.py
"""
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
HASIL = Path("/content/drive/MyDrive/finetune-id/V5")
gagal = []


def jalan(mode, **env):
    out = subprocess.run([sys.executable, str(HERE / "jalankan.py"), mode], capture_output=True, text=True,
                         env={**os.environ, "HOME": HOME, **env}).stdout
    return out


def harus(syarat, pesan):
    print(("ok    " if syarat else "GAGAL ") + pesan)
    if not syarat:
        gagal.append(pesan)


HOME = tempfile.mkdtemp()
shutil.rmtree(HASIL, ignore_errors=True)
o = jalan("semua", SIM_EPOCH2_BONUS="0.05")
harus("cabang claude/" in o, "Sel 1 memakai cabang yang sudah mendukung V5")
harus("281 sampel (seharusnya 281), 0 dibuang, terpanjang 6231 token, 213 step" in o,
      "cek data: 281 sampel, tidak ada yang dibuang, 213 step (lr 2e-4, grad-accum 4)")
harus("V5 memakai adapter epoch 2" in o, "epoch 2 dipilih saat skornya unggul ≥ 1 poin")
harus("dipakai adapter: {'epoch': 2}" in o, "ekspor GGUF memakai adapter epoch terpilih")
harus((HASIL / "qwen3.5-4b-V5/gguf/qwen3.5-4b-V5.Q4_K_M.gguf").is_file(), "file GGUF memuat nama V5")
harus((HASIL / "laporan-V5.txt").is_file() and "HumanEval+ (terkontaminasi)" in o, "laporan ditulis ke Drive")
harus("runtime.unassign" in o, "runtime dimatikan setelah selesai")

o = jalan("semua")
harus(o.count("sudah selesai") >= 10 and "[sim] eval" not in o, "jalankan ulang: semua langkah dilewati")
o = jalan("langkah")
harus("⬜" not in o and o.count("✅") >= 12, "sel cek progres: semua langkah ✅")

shutil.rmtree(HASIL)
o = jalan("oom", SIM_OOM="1")
harus("VRAM habis: Web-eval diulang dengan batch 2" in o and "V5 memakai adapter epoch 3" in o,
      "VRAM habis saat uji: batch turun otomatis; epoch 3 dipakai saat epoch 2 tidak unggul")

shutil.rmtree(HASIL)
o = jalan("semua", SIM_FAIL_TRAIN="1")
harus(o.find("Training gagal") < o.find("runtime.unassign") and (HASIL / "GAGAL-V5.txt").is_file(),
      "training gagal: pesan dicetak dan disimpan sebelum runtime dimatikan")

shutil.rmtree(HASIL, ignore_errors=True)
shutil.rmtree(HOME)
print(f"\n{len(gagal)} gagal" if gagal else "\nsemua skenario lolos")
sys.exit(1 if gagal else 0)
