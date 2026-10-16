"""Uji sel-sel docs/PANDUAN_V7_A100.md tanpa GPU dan tanpa Colab, lalu uji scripts/sulingan.py dalam mode demo.

Bagian 1 (alur panduan): GPU, google.colab, git clone, sulingan.py, train_unsloth.py, dan script uji diganti tiruan
yang menulis file hasil dengan struktur yang sama. Yang diuji: pilih cabang, sulingan, OOM saat sulingan, gabung, cek
data, training 2 epoch, uji setiap epoch, gerbang melawan model dasar (adapter menang atau model dasar menang), ekspor,
laporan, melanjutkan setelah terputus, dan training gagal.

Bagian 2 (sulingan.py asli, --demo): soal MBPP dibungkus permintaan berbahasa Indonesia, jawaban diperiksa dengan assert,
yang gagal dibuang, gabung menulis data training, dan hasilnya sama persis jika dijalankan ulang. Pemeriksa website
ikut diuji jika Playwright dan Chromium tersedia (CHROMIUM=<path> jika bukan bawaan Playwright).

Bagian 1 menulis ke /content (path Colab yang dipakai panduan), jadi jalankan hanya di container sekali pakai:
    python tests/simulasi_v7/cek.py
"""
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
HASIL = Path("/content/drive/MyDrive/finetune-id/V7")
gagal = []


def jalan(mode, **env):
    return subprocess.run([sys.executable, str(HERE / "jalankan.py"), mode], capture_output=True, text=True,
                          env={**os.environ, "HOME": HOME, **env}).stdout


def harus(syarat, pesan):
    print(("ok    " if syarat else "GAGAL ") + pesan)
    if not syarat:
        gagal.append(pesan)


def baca(path):
    return Path(path).read_text() if Path(path).is_file() else ""


# ---------------------------------------------------------------- bagian 1: alur panduan

HOME = tempfile.mkdtemp()
own = sum(1 for baris in open(REPO / "data/train.jsonl") if baris.strip())
total = own + 30 + 300
shutil.rmtree(HASIL, ignore_errors=True)
o = jalan("semua", SIM_BONUS="1:0.05", SIM_16BIT="1")
harus("[sim] clone claude/youthful-mayer-lvf8r6" in o and "✅ Repo" in o and "40 prompt website sulingan" in o,
      "Sel 1 pindah ke cabang yang sudah punya sulingan.py")
harus("sulingan python k=4 batch 8: 589 soal" in o and "sulingan web k=2 batch 2: 40 soal" in o,
      "sulingan Python (4 kandidat) dan website (2 kandidat) berjalan")
harus(f"✅ {total} sampel, 0 dibuang" in o, f"cek data: own {own} + 30 web + 300 python = {total} sampel")
harus(all(f"Uji epoch {n} · 4/4: HumanEval+" in o for n in (1, 2)), "setiap epoch diuji dengan keempat uji bersih")
harus("V7 memakai adapter epoch 1" in o and "model dasar 65.0%" in o, "gerbang: epoch terbaik (1) mengalahkan model dasar")
harus("dipakai adapter: {'epoch': 1}" in o, "ekspor GGUF memakai adapter epoch terpilih")
harus((HASIL / "qwen3.5-4b-V7/gguf/qwen3.5-4b-V7.Q4_K_M.gguf").is_file()
      and (HASIL / "qwen3.5-4b-V7/qwen3.5-4b-V7-merged-16bit/config.json").is_file(), "GGUF dan 16-bit memuat nama V7")
laporan = baca(HASIL / "laporan-V7.txt")
harus(all(k in laporan for k in ("IndoPy-dev", "MBPP+", "HumanEval+", "format Cek kebutuhan", "=== Sulingan ===",
                                 "V7 ep 2", "dibuang karena tumpang tindih dengan soal uji: 1")),
      "laporan memuat empat uji, format, sulingan, dan setiap epoch")
harus("terkontaminasi" not in laporan, "laporan V7 tidak menandai uji mana pun sebagai terkontaminasi")
harus("runtime.unassign" not in o, "Sel 3 tidak mematikan runtime")

o = jalan("semua")
harus(o.count("sudah selesai") >= 10 and "[sim] " not in o.replace("[sim] clone", ""),
      "jalankan ulang: semua langkah dilewati, tidak ada yang diulang")
o = jalan("langkah")
harus("⬜" not in o and o.count("✅") >= 15, "sel cek progres: semua langkah ✅")

shutil.rmtree(HASIL)
o = jalan("semua", SIM_DASAR="0.9")
harus("V7 TIDAK dipakai: model dasar lebih baik" in o and "Ekspor dilewati" in o
      and not (HASIL / "qwen3.5-4b-V7/gguf").exists(), "gerbang: model dasar menang, ekspor dilewati")
harus("V7 TIDAK dipakai" in baca(HASIL / "laporan-V7.txt"), "laporan menyebut model dasar yang dipakai")

shutil.rmtree(HASIL)
o = jalan("semua", SIM_OOM_SUL="1")
harus("VRAM habis: sulingan web diulang dengan batch 1" in o and "V7 memakai adapter epoch 2" in o,
      "VRAM habis saat sulingan: batch turun otomatis; seri dipecahkan ke epoch terakhir")

shutil.rmtree(HASIL)
o = jalan("semua", SIM_FAIL_TRAIN="1")
harus("Training gagal" in o and "runtime.unassign" not in o, "training gagal: pesan tampil, runtime tetap menyala")
shutil.rmtree(HASIL, ignore_errors=True)
shutil.rmtree(HOME)

# ---------------------------------------------------------------- bagian 2: sulingan.py asli (demo)

tmp = Path(tempfile.mkdtemp())
sul = [sys.executable, str(REPO / "scripts/sulingan.py")]
r = subprocess.run(sul + ["python", "--out", str(tmp), "--demo", "--limit", "24"], capture_output=True, text=True)
rows = [json.loads(b) for b in baca(tmp / "kandidat-python.jsonl").splitlines()]
kand = [c for row in rows for c in row["kandidat"]]
harus(r.returncode == 0 and len(rows) == 24 and len(kand) == 96, "sulingan python demo: 24 soal × 4 kandidat")
harus(any(c["lolos"] for c in kand) and any(not c["lolos"] for c in kand), "jawaban benar lolos, jawaban rusak dibuang")
harus(all("fungsi" in row["user"].lower() and "`" in row["user"] for row in rows),
      "soal dibungkus permintaan berbahasa Indonesia yang menyebut nama fungsi")
sys.path.insert(0, str(REPO / "scripts"))
import sulingan  # noqa: E402

task = next(t for t in sulingan.python_tasks(sulingan.parse_args(["python", "--demo", "--limit", "1"])))
benar = {"text": f"Fungsi ini memakai pendekatan langsung.\n\n```python\n{task['solusi']}\n```\n\nSelesai, tanpa kasus khusus.",
         "selesai": True}
rusak = {"text": benar["text"].replace("```python\n", f"```python\ndef {task['entry']}(*a):\n    return None\n#", 1),
         "selesai": True}
harus(sulingan.check_python(task, benar, 10)[0] and not sulingan.check_python(task, rusak, 10)[0]
      and not sulingan.check_python(task, {**benar, "selesai": False}, 10)[0],
      "pemeriksa Python: solusi rujukan lolos, solusi salah dan jawaban terpotong ditolak")

ada_chromium = importlib.util.find_spec("playwright") is not None
if ada_chromium:
    extra = ["--chromium", os.environ["CHROMIUM"]] if os.environ.get("CHROMIUM") else []
    r = subprocess.run(sul + ["web", "--out", str(tmp), "--demo", "--limit", "4", *extra], capture_output=True, text=True)
    web = [c for row in map(json.loads, baca(tmp / "kandidat-web.jsonl").splitlines()) for c in row["kandidat"]]
    harus(r.returncode == 0 and len(web) == 8 and any(c["lolos"] for c in web)
          and any("belumAda" in c["alasan"] for c in web), "sulingan web demo: halaman dengan error JavaScript dibuang")
else:
    print("lewati  pemeriksa website: Playwright tidak terpasang")
r = subprocess.run(sul + ["gabung", "--out", str(tmp), "--demo", "--hasil", str(tmp / "train.jsonl")],
                   capture_output=True, text=True)
pertama = baca(tmp / "train.jsonl")
ringkas = json.loads(baca(tmp / "ringkasan-sulingan.json") or "{}")
data = [json.loads(b) for b in pertama.splitlines()]
harus(r.returncode == 0 and ringkas.get("total") == len(data) == own + ringkas["sulingan_python"]["dipakai"]
      + ringkas["sulingan_web"]["dipakai"], "gabung: own + sulingan, jumlahnya sesuai ringkasan")
harus(all(m["role"] != "system" for s in data if s["id"].startswith("sul-") for m in s["messages"]),
      "sampel sulingan tanpa system prompt (instruksi gaya tidak ikut dilatih)")
subprocess.run(sul + ["gabung", "--out", str(tmp), "--demo", "--hasil", str(tmp / "train.jsonl")], capture_output=True)
harus(baca(tmp / "train.jsonl") == pertama, "gabung deterministik: checkpoint training tetap bisa dilanjutkan")
shutil.rmtree(tmp)

print(f"\n{len(gagal)} gagal" if gagal else "\nsemua skenario lolos")
sys.exit(1 if gagal else 0)
