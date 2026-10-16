"""Uji sel-sel docs/PANDUAN_V6_A100.md tanpa GPU dan tanpa Colab.

GPU, google.colab, train_unsloth.py, dan script uji diganti tiruan yang menulis file hasil dengan struktur yang sama.
Yang diuji adalah alur panduan: pilih cabang, unduh data bench-support, cek data, training 10 epoch, uji epoch 10 dan
epoch kandidat, pilih epoch, ekspor, laporan, melanjutkan setelah terputus, VRAM habis saat uji, dan training gagal.

Simulasi menulis ke /content (path Colab yang dipakai panduan), jadi jalankan hanya di container sekali pakai:
    python tests/simulasi_v6/cek.py
"""
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
HASIL = Path("/content/drive/MyDrive/finetune-id/V6")
gagal = []


def jalan(mode, **env):
    return subprocess.run([sys.executable, str(HERE / "jalankan.py"), mode], capture_output=True, text=True,
                          env={**os.environ, "HOME": HOME, **env}).stdout


def harus(syarat, pesan):
    print(("ok    " if syarat else "GAGAL ") + pesan)
    if not syarat:
        gagal.append(pesan)


HOME = tempfile.mkdtemp()
shutil.rmtree(HASIL, ignore_errors=True)
o = jalan("semua", SIM_BONUS="5:0.05,7:0.005")
harus("cabang claude/" in o, "Sel 1 memakai cabang yang sudah mendukung V6")
harus("1256 sampel (seharusnya 1256), 0 dibuang, terpanjang 6231 token, 3140 step" in o,
      "cek data: 1256 sampel (own + HumanEval + MBPP+ + MBPP), 3140 step untuk 10 epoch")
harus("epoch kandidat 3, 5, 7" in o and "terkontaminasi" in o, "Sel 1 menampilkan resep dan peringatan kontaminasi")
harus(all(f"Uji epoch {n} · 2/2: Web-eval" in o for n in (3, 5, 7)) and "Uji epoch 10 · 4/4" in o,
      "epoch 10 diuji lengkap, epoch 3/5/7 hanya dengan uji bersih")
harus("V6 memakai adapter epoch 5" in o, "epoch kandidat dipakai hanya jika unggul ≥ 1 poin (epoch 5 +5, epoch 7 +0,5)")
harus("dipakai adapter: {'epoch': 5}" in o, "ekspor GGUF memakai adapter epoch terpilih")
harus((HASIL / "qwen3.5-4b-V6/gguf/qwen3.5-4b-V6.Q4_K_M.gguf").is_file(), "file GGUF memuat nama V6")
laporan = (HASIL / "laporan-V6.txt").read_text() if (HASIL / "laporan-V6.txt").is_file() else ""
harus("MBPP+ (terkontaminasi)" in laporan and "HumanEval+ (terkontaminasi)" in laporan and "V6 ep 10" in laporan,
      "laporan ditulis ke Drive dengan tanda terkontaminasi")
harus("runtime.unassign" not in o, "Sel 3 tidak mematikan runtime")

o = jalan("semua")
harus(o.count("sudah selesai") >= 12 and "[sim] " not in o, "jalankan ulang: semua langkah dilewati")
o = jalan("langkah")
harus("⬜" not in o and o.count("✅") >= 25, "sel cek progres: semua langkah ✅")

shutil.rmtree(HASIL)
o = jalan("oom", SIM_OOM="1")
harus("VRAM habis: Web-eval diulang dengan batch 2" in o and "V6 memakai adapter epoch 10" in o,
      "VRAM habis saat uji: batch turun otomatis; epoch 10 dipakai saat kandidat tidak unggul")

shutil.rmtree(HASIL)
o = jalan("tanpa-pilih", SIM_BONUS="5:0.2")
harus("Uji epoch 5" not in o and "V6 memakai adapter epoch 10" in o,
      "PILIH_EPOCH_TERBAIK = False: epoch kandidat tidak diuji, epoch 10 dipakai")

shutil.rmtree(HASIL)
o = jalan("semua", SIM_FAIL_TRAIN="1")
harus("Training gagal" in o and "runtime.unassign" not in o, "training gagal: pesan tampil, runtime tetap menyala")

shutil.rmtree(HASIL, ignore_errors=True)
shutil.rmtree(HOME)
print(f"\n{len(gagal)} gagal" if gagal else "\nsemua skenario lolos")
sys.exit(1 if gagal else 0)
