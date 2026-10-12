"""Panel interaktif v4 untuk Google Colab: siapkan, jalankan langkah yang belum selesai, progres, laporan.

Dua mode, masing-masing dengan notebook sendiri:
  pilot  notebooks/v4_pilot_interaktif.ipynb (T4): ukur v3, latih v4-pilot dengan resep v3, ukur v4-pilot
         (docs/PROSEDUR_V4.md)
  a100   notebooks/v4_a100_interaktif.ipynb (A100): latih v4 dan v3-ulang dari model dasar dengan LoRA 16-bit dan
         konteks 16.384, lalu ukur keduanya dan model dasar di folder finetune-id/a100 (docs/PROSEDUR_V4_A100.md).
         Tidak butuh hasil lama di Drive, jadi bisa dimulai dari akun Google yang baru.

Cara kerjanya:
  - setiap langkah (uji atau training) dijalankan sebagai proses terpisah, jadi memori GPU selalu bersih di awal
    langkah berikutnya dan sesi Colab tidak perlu di-restart;
  - status setiap langkah dibaca dari hasilnya di Google Drive, jadi kalau Colab terputus, jalankan sel yang sama
    lagi dan panel melanjutkan dari langkah yang belum selesai;
  - output setiap langkah juga disimpan di Drive (finetune-id/panel-log/), dan laporan akhir ditulis ke
    finetune-id/laporan-v4-pilot.txt atau finetune-id/laporan-v4-a100.txt.

Mode demo (tanpa GPU dan tanpa Colab) menguji alurnya dengan jawaban tiruan:
    python scripts/panel_v4.py --demo /tmp/panel-demo
    python scripts/panel_v4.py --demo /tmp/panel-demo-a100 --a100
"""
import codecs
import importlib.metadata
import importlib.util
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from argparse import Namespace
from dataclasses import dataclass, field
from pathlib import Path

REPO = "https://raw.githubusercontent.com/PvzKing/Dataset/main"
ROOT_REPO = Path(__file__).resolve().parent.parent if "__file__" in globals() else Path.cwd()
KERJA = Path("/content")
OUT = Path("/content/drive/MyDrive/finetune-id")
V3_BAWAAN = str(OUT / "v3" / "qwen3.5-4b-own-4bit" / "lora-adapter")
EVALPLUS = "evalplus @ git+https://github.com/evalplus/evalplus@26d6d00bb1fd0fa37f39c99d5290da67891d1c5e"
SCRIPTS = {
    "eval_humaneval.py": "humaneval-bench-script/eval_humaneval.py",
    "chat_gradio.py": "scripts/chat_gradio.py",
    "indopy_eval.py": "eval-suite/indopy_eval.py",
    "web_eval.py": "eval-suite/web_eval.py",
    "papan_skor.py": "eval-suite/papan_skor.py",
    "train_unsloth.py": "scripts/train_unsloth.py",
}
OTOMATIS = "Otomatis: semua yang belum selesai"
CONFIG_FILE = KERJA / "panel_v4.json"

# Mode A100 (docs/PROSEDUR_V4_A100.md). Batch uji bisa diturunkan otomatis saat VRAM habis.
A100_BATCH = {"humaneval": 32, "mbpp": 32, "indopy": 16, "indopy-test": 16, "web": 5}
A100_JAWABAN = 12000  # batas jawaban website uji dan Web-eval
A100_UJI = {  # kunci: (folder hasil, script, argumen tambahan, label)
    "humaneval": ("eval-humaneval", "eval_humaneval.py", [], "HumanEval+"),
    "mbpp": ("eval-mbpp", "eval_humaneval.py", ["--dataset", "mbpp"], "MBPP+"),
    "indopy": ("eval-indopy-dev", "indopy_eval.py", ["--split", "dev"], "IndoPy-dev"),
    "web": ("eval-web", "web_eval.py", [], "Web-eval"),
    "indopy-test": ("eval-indopy-test", "indopy_eval.py", ["--split", "test"], "IndoPy-test"),
}
POLA_OOM = r"CUDA out of memory|OutOfMemoryError"
# v3-ulang: pembanding gerbang G3 yang dilatih ulang dengan resep yang sama dengan v4. Datanya train.jsonl terakhir
# sebelum sampel Python ditambahkan (79 sampel web, tech, debug, math, sci). v4 = data ini + 23 sampel baru.
V3_ULANG_COMMIT = "3ed189ddcb387fe6609968ccb426c5603d7f5690"
V3_ULANG_SAMPEL = 79

# Saran untuk pesan error yang sudah dikenal, dicocokkan dengan output langkah yang gagal.
SARAN = [
    (r"CUDA out of memory|OutOfMemoryError", "VRAM habis. Jalankan sel 2 lagi: langkah ini dilanjutkan dari jawaban "
                                             "yang sudah tersimpan. Jika berulang, pilih Runtime → Restart session, "
                                             "lalu jalankan sel 1 dan sel 2."),
    (r"adapter tidak ditemukan|bukan folder adapter", "Folder adapter tidak ditemukan. Periksa path adapter v3 di sel 1."),
    (r"No module named 'playwright'|Executable doesn't exist|playwright install",
     "Playwright/Chromium belum terpasang di runtime ini. Jalankan sel 1, lalu sel 2."),
    (r"evalplus yang terpasang|evalplus belum terpasang", "Versi EvalPlus salah. Jalankan sel 1 (memasang versi yang benar)."),
    (r"Google Drive belum ter-mount|Drive belum", "Google Drive belum ter-mount. Jalankan sel 1."),
    (r"No CUDA GPUs|CUDA driver|Found no NVIDIA driver|torch.cuda.is_available\(\) is False",
     "Runtime tidak punya GPU. Pilih Runtime → Change runtime type → T4 GPU, lalu jalankan sel 1."),
]


@dataclass
class Konfig:
    v3: str = V3_BAWAAN
    out: Path = OUT
    kerja: Path = KERJA
    demo: bool = False
    limit: int = 0  # khusus demo: jumlah soal per uji supaya cepat
    mode: str = "pilot"  # "pilot" (T4) atau "a100"
    konteks: int = 16384  # khusus a100: max_seq_len training
    batch: dict = field(default_factory=dict)  # khusus a100: batch uji yang diturunkan setelah VRAM habis
    log: list = field(default_factory=list)

    @property
    def hasil(self):
        """Folder induk eval-*. Mode A100 memakai folder sendiri supaya model dasar diukur ulang dalam 16-bit."""
        return self.out if self.mode == "pilot" else self.out / "a100"

    @property
    def folder_v4(self):
        return self.out / ("v4-pilot" if self.mode == "pilot" else "v4")

    @property
    def data_v3(self):
        return self.out / "v3-ulang" / "train_v3.jsonl"


def v3_ulang(out):
    return str(Path(out) / "v3-ulang" / "qwen3.5-4b-own" / "lora-adapter")


def adapter_ada(path):
    return (Path(path) / "adapter_config.json").is_file()


KONFIG = None


# ---------------------------------------------------------------- bantuan umum

def judul(teks):
    print(f"\n{'=' * 78}\n{teks}\n{'=' * 78}", flush=True)


def jalankan_proses(argv, cwd, log_path=None):
    """Jalankan perintah, alirkan outputnya apa adanya (termasuk progress bar), kembalikan (exit code, ekor output)."""
    env = dict(os.environ, PYTHONUNBUFFERED="1")
    p = subprocess.Popen(argv, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env)
    decoder, ekor = codecs.getincrementaldecoder("utf-8")("replace"), ""
    log = open(log_path, "a", encoding="utf-8") if log_path else None
    try:
        while chunk := p.stdout.read1(65536):
            teks = decoder.decode(chunk)
            sys.stdout.write(teks)
            sys.stdout.flush()
            ekor = (ekor + teks)[-20000:]
            if log:
                log.write(teks)
        return p.wait(), ekor
    except KeyboardInterrupt:
        p.terminate()
        raise
    finally:
        if log:
            log.close()


def pip(*args):
    return subprocess.run([sys.executable, "-m", "pip", "install", "-q", *args]).returncode == 0


def script(k, nama):
    return str((ROOT_REPO / SCRIPTS[nama]) if k.demo else (k.kerja / nama))


def eval_humaneval(k):
    """Modul eval_humaneval, untuk menghitung nama run dengan aturan yang sama persis dengan script uji."""
    path = script(k, "eval_humaneval.py")
    spec = importlib.util.spec_from_file_location("eval_humaneval_panel", path)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


def adapter_v4(k):
    if k.mode == "a100":  # hanya hasil 16-bit; folder -4bit di bawah v4/ bukan hasil panduan A100
        found = (k.folder_v4 / "qwen3.5-4b-own" / "lora-adapter" / "adapter_config.json").is_file()
        return str(k.folder_v4 / "qwen3.5-4b-own" / "lora-adapter") if found else None
    found = sorted((k.out / "v4-pilot").glob("*/lora-adapter/adapter_config.json"))
    return str(found[-1].parent) if found else None


def nama_run(k, adapter, cadangan):
    if k.demo:
        return cadangan
    return eval_humaneval(k).run_tag(Namespace(tag=None, demo=False, adapter=adapter, out=str(k.out)))


def nama_dasar(k, run):
    # Script uji memberi model dasar folder sendiri jika --tag dipakai (demo); run sungguhan memakai "model-dasar".
    return f"{run}-model-dasar" if k.demo else "model-dasar"


def ringkasan_ada(k, folder, run):
    return (k.hasil / folder / run / "ringkasan.json").is_file()


# ---------------------------------------------------------------- daftar langkah

def langkah_langkah(k, opsional=False):
    """Daftar langkah sesuai mode. `opsional` menyertakan langkah opsional: MBPP+ v3 (pilot) atau IndoPy-test (a100)."""
    if k.mode == "a100":
        return langkah_a100(k, opsional)
    mbpp_v3 = opsional
    v4 = adapter_v4(k)
    run_v3 = nama_run(k, k.v3, "v3-demo")
    run_v4 = nama_run(k, v4, "v4-demo") if v4 else None
    uji = [
        ("humaneval", "eval-humaneval", "eval_humaneval.py", [], "HumanEval+"),
        ("indopy", "eval-indopy-dev", "indopy_eval.py", ["--split", "dev"], "IndoPy-dev"),
        ("web", "eval-web", "web_eval.py", [], "Web-eval"),
        ("mbpp", "eval-mbpp", "eval_humaneval.py", ["--dataset", "mbpp"], "MBPP+"),
    ]
    menit = {("humaneval", "v3"): 20, ("indopy", "v3"): 15, ("web", "v3"): 80, ("mbpp", "v3"): 50,
             ("humaneval", "v4"): 20, ("indopy", "v4"): 8, ("web", "v4"): 40, ("mbpp", "v4"): 100}

    def langkah_uji(kunci, folder, nama, extra, label, versi, adapter, run):
        argv = [script(k, nama), "--adapter", adapter or "-", "--results", str(k.out / folder), *extra]
        if k.demo:
            argv = [script(k, nama), "--demo", "--tag", run, "--results", str(k.out / folder), *extra]
            argv += ["--limit", str(k.limit)] if k.limit and kunci != "web" else []
        return {"kunci": f"{kunci}-{versi}", "judul": f"{label} {versi}", "menit": menit[(kunci, versi)],
                "argv": argv, "butuh_v4": versi == "v4", "opsional": kunci == "mbpp" and versi == "v3",
                "selesai": bool(run) and ringkasan_ada(k, folder, run) and ringkasan_ada(k, folder, nama_dasar(k, run))}

    daftar = [langkah_uji(*u[:2], u[2], u[3], u[4], "v3", k.v3, run_v3) for u in uji[:3]]
    daftar.append({"kunci": "latih-v4", "judul": "Latih v4-pilot", "menit": 70, "butuh_v4": False, "opsional": False,
                   "argv": [script(k, "train_unsloth.py"), "train", "--out", str(k.out / "v4-pilot")],
                   "selesai": v4 is not None})
    daftar += [langkah_uji(*u[:2], u[2], u[3], u[4], "v4", v4, run_v4) for u in uji]
    daftar.append(langkah_uji(*uji[3][:2], uji[3][2], uji[3][3], uji[3][4], "v3", k.v3, run_v3))
    for d in daftar:
        d["dilewati"] = d["opsional"] and not mbpp_v3
    return daftar


def langkah_a100(k, indopy_test=False):
    """Urutan docs/PROSEDUR_V4_A100.md: latih v4, ukur v4, latih v3-ulang, ukur v3-ulang (Web-eval dulu karena
    dibutuhkan G3), lalu IndoPy-test opsional. Semua uji 16-bit dengan folder hasil finetune-id/a100."""
    v4 = adapter_v4(k)
    run_v3 = nama_run(k, k.v3, "v3-demo")
    run_v4 = nama_run(k, v4, "v4-demo") if v4 else None
    menit = {("humaneval", "v4"): 15, ("mbpp", "v4"): 35, ("indopy", "v4"): 8, ("web", "v4"): 30,
             ("web", "v3-ulang"): 20, ("humaneval", "v3-ulang"): 6, ("mbpp", "v3-ulang"): 15,
             ("indopy", "v3-ulang"): 4, ("indopy-test", "v4"): 10}

    def langkah_uji(kunci, versi, adapter, run, opsional=False):
        folder, nama, extra, label = A100_UJI[kunci]
        batch = k.batch.get(kunci, A100_BATCH[kunci])
        if kunci == "web":
            extra = [*extra, "--max-seq-len", str(k.konteks), "--max-new-tokens", str(A100_JAWABAN)]
        hasil = str(k.hasil / folder)
        if k.demo:
            argv = [script(k, nama), "--demo", "--tag", run, "--results", hasil, "--batch-size", str(batch), *extra]
            argv += ["--limit", str(k.limit)] if k.limit and kunci != "web" else []
        else:
            argv = [script(k, nama), "--adapter", adapter or "-", "--results", hasil, "--no-load-in-4bit",
                    "--batch-size", str(batch), *extra]
        return {"kunci": f"{kunci}-{versi}", "judul": f"{label} {versi}", "menit": menit[(kunci, versi)],
                "argv": argv, "jenis": kunci, "batch": batch, "butuh_v4": versi == "v4",
                "butuh_v3": versi == "v3-ulang", "opsional": opsional,
                "selesai": bool(run) and ringkasan_ada(k, folder, run) and ringkasan_ada(k, folder, nama_dasar(k, run))}

    daftar = [{"kunci": "latih-v4", "judul": "Latih v4", "menit": 45, "butuh_v4": False, "opsional": False,
               "argv": [script(k, "train_unsloth.py"), "train", "--out", str(k.folder_v4), "--no-load-in-4bit",
                        "--max-seq-len", str(k.konteks), "--max-new-tokens", str(A100_JAWABAN)],
               "selesai": v4 is not None}]
    daftar += [langkah_uji(u, "v4", v4, run_v4) for u in ("humaneval", "mbpp", "indopy", "web")]
    daftar.append({"kunci": "latih-v3", "judul": "Latih v3-ulang", "menit": 35, "butuh_v4": False, "opsional": False,
                   "argv": [script(k, "train_unsloth.py"), "train", "--out", str(k.out / "v3-ulang"),
                            "--data", str(k.data_v3), "--no-load-in-4bit", "--max-seq-len", str(k.konteks),
                            "--no-test"],
                   "selesai": adapter_ada(k.v3)})
    daftar += [langkah_uji(u, "v3-ulang", k.v3, run_v3) for u in ("web", "humaneval", "mbpp", "indopy")]
    daftar.append(langkah_uji("indopy-test", "v4", v4, run_v4, opsional=True))
    for d in daftar:
        d["dilewati"] = d["opsional"] and not indopy_test
    return daftar


# ---------------------------------------------------------------- sel 1: siapkan

def siapkan(adapter_v3=V3_BAWAAN, demo_out=None, mode="pilot", konteks=16384):
    """Cek GPU, pasang paket yang belum ada, mount Drive, unduh script terbaru, dan periksa adapter v3."""
    global KONFIG
    k = Konfig(v3=adapter_v3.strip(), mode=mode, konteks=int(konteks)) if demo_out is None else Konfig(
        v3="demo", out=Path(demo_out), kerja=ROOT_REPO, demo=True, limit=12, mode=mode, konteks=int(konteks))
    if mode == "a100":
        k.v3 = v3_ulang(k.out)  # dilatih ulang oleh panel, jadi adapter v3 lama tidak dibutuhkan
    cek = []
    judul("Persiapan")
    if not k.demo:
        gpu = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
                             capture_output=True, text=True)
        if gpu.returncode != 0:
            cek.append(("GPU", False, "tidak ada GPU. Pilih Runtime → Change runtime type → T4 GPU, lalu jalankan "
                                      "sel ini lagi"))
            return laporkan_cek(cek)
        nama_gpu = gpu.stdout.strip()
        if mode == "a100" and not re.search(r"A100|H100", nama_gpu):
            cek.append(("GPU", False, f"{nama_gpu}. Panel ini butuh A100 (LoRA 16-bit, konteks {k.konteks}). Pilih "
                                      "Runtime → Change runtime type → A100 GPU, lalu jalankan sel ini lagi. "
                                      "Untuk T4, pakai notebook v4_pilot_interaktif"))
            return laporkan_cek(cek)
        cek.append(("GPU", True, nama_gpu))

        print("memeriksa paket ...", flush=True)
        if importlib.util.find_spec("unsloth") is None:
            print("memasang unsloth (±3–5 menit) ...", flush=True)
            pip("--upgrade", "unsloth")
        versi = importlib.metadata.version("evalplus") if importlib.util.find_spec("evalplus") else None
        if versi is None:
            print("memasang evalplus ...", flush=True)
            pip(EVALPLUS)
        elif versi.startswith("0.3"):
            print(f"mengganti evalplus {versi} (PyPI, salah menilai HumanEval/32) ...", flush=True)
            pip("--force-reinstall", "--no-deps", EVALPLUS)
        if importlib.util.find_spec("playwright") is None:
            print("memasang playwright ...", flush=True)
            pip("playwright")
        if not list(Path.home().glob(".cache/ms-playwright/chromium-*")):
            print("memasang Chromium untuk Web-eval (±1–2 menit) ...", flush=True)
            subprocess.run([sys.executable, "-m", "playwright", "install", "--with-deps", "chromium"],
                           stdout=subprocess.DEVNULL)
        importlib.invalidate_caches()
        terpasang = {p: importlib.util.find_spec(p) is not None for p in ("unsloth", "evalplus", "playwright")}
        terpasang["chromium"] = bool(list(Path.home().glob(".cache/ms-playwright/chromium-*")))
        cek.append(("Paket", all(terpasang.values()), ", ".join(f"{p} {'ok' if v else 'GAGAL'}"
                                                                for p, v in terpasang.items())))

        if not Path("/content/drive/MyDrive").is_dir():
            from google.colab import drive
            drive.mount("/content/drive")
        cek.append(("Google Drive", Path("/content/drive/MyDrive").is_dir(), "/content/drive/MyDrive"))

        gagal_unduh = []
        for nama, path in SCRIPTS.items():
            try:
                urllib.request.urlretrieve(f"{REPO}/{path}", k.kerja / nama)
            except OSError as e:
                gagal_unduh.append(f"{nama} ({e})")
        cek.append(("Script terbaru", not gagal_unduh, "6 script di /content" if not gagal_unduh else
                    "gagal: " + ", ".join(gagal_unduh)))

        if k.mode == "a100":
            cek.append(("Data v3-ulang", *siapkan_data_v3(k)))
        else:
            ada_v3 = adapter_ada(k.v3)
            info = k.v3
            if not ada_v3:
                calon = sorted(str(p.parent) for pola in ("lora-adapter", "*/lora-adapter", "*/*/lora-adapter")
                               for p in k.out.glob(pola + "/adapter_config.json"))
                info = f"tidak ditemukan: {k.v3}" + (
                    "\n      adapter yang ada di Drive:\n      " + "\n      ".join(calon) if calon else
                    "\n      belum ada adapter sama sekali di Drive ini (akun baru?). Pakai notebook "
                    "v4_a100_interaktif, yang melatih ulang v3 dan v4 dari awal")
            cek.append(("Adapter v3", ada_v3, info))
    else:
        k.out.mkdir(parents=True, exist_ok=True)
        cek.append(("Mode demo", True, f"hasil di {k.out}"))
        if k.mode == "a100":
            k.data_v3.parent.mkdir(parents=True, exist_ok=True)
            k.data_v3.write_text(subprocess.run(["git", "-C", str(ROOT_REPO), "show",
                                                 f"{V3_ULANG_COMMIT}:data/train.jsonl"],
                                                capture_output=True, text=True, check=True).stdout)

    KONFIG = k
    if all(ok for _, ok, _ in cek) and not k.demo:
        # supaya sel 2–4 tetap jalan setelah Restart session
        CONFIG_FILE.write_text(json.dumps({"v3": k.v3, "mode": k.mode, "konteks": k.konteks}))
    laporkan_cek(cek)
    if all(ok for _, ok, _ in cek):
        progres()


def siapkan_data_v3(k):
    """Unduh data v3-ulang dari commit yang dipatok, sekali saja. Kembalikan (ok, info) untuk daftar cek."""
    if not k.data_v3.is_file():
        k.data_v3.parent.mkdir(parents=True, exist_ok=True)
        try:
            tmp = k.data_v3.with_suffix(".part")
            urllib.request.urlretrieve(
                f"https://raw.githubusercontent.com/PvzKing/Dataset/{V3_ULANG_COMMIT}/data/train.jsonl", tmp)
            tmp.replace(k.data_v3)
        except OSError as e:
            return False, f"gagal mengunduh data v3-ulang ({e})"
    n = sum(1 for b in k.data_v3.read_text(encoding="utf-8").splitlines() if b.strip())
    ok = n == V3_ULANG_SAMPEL
    return ok, (f"{n} sampel dari commit {V3_ULANG_COMMIT[:7]}" if ok else
                f"{n} sampel, seharusnya {V3_ULANG_SAMPEL}. Hapus {k.data_v3} lalu jalankan sel ini lagi")


def laporkan_cek(cek):
    print()
    for nama, ok, info in cek:
        print(f"{'✅' if ok else '❌'} {nama:<15} {info}")
    if all(ok for _, ok, _ in cek):
        print("\nSiap. Lanjut ke sel 2.")
    else:
        print("\nPerbaiki yang bertanda ❌, lalu jalankan sel ini lagi.")


def konfig():
    """Konfigurasi sesi ini; dimuat ulang dari file jika kernel baru di-restart."""
    global KONFIG
    if KONFIG is None and CONFIG_FILE.is_file() and Path("/content/drive/MyDrive").is_dir():
        c = json.loads(CONFIG_FILE.read_text())
        KONFIG = Konfig(v3=c["v3"], mode=c.get("mode", "pilot"), konteks=c.get("konteks", 16384))
        if KONFIG.mode == "a100":
            KONFIG.v3 = v3_ulang(KONFIG.out)
    if KONFIG is None:
        raise SystemExit("Jalankan sel 1 (Siapkan) dulu.")
    return KONFIG


# ---------------------------------------------------------------- sel 3: progres

def progres(opsional=False):
    k = konfig()
    daftar = langkah_langkah(k, opsional)
    ada_v4 = adapter_v4(k) is not None
    berikut = next((d for d in daftar if not d["selesai"] and not d["dilewati"]), None)
    if k.mode == "a100":
        print(f"\nMode A100: v4 dan v3-ulang dari model dasar, LoRA 16-bit, konteks {k.konteks}; "
              f"hasil uji di {k.hasil}")
    print(f"\n{'':2} {'langkah':<22} {'perkiraan':>10}   status")
    sisa = 0
    for i, d in enumerate(daftar, 1):
        if d["selesai"]:
            ikon, status = "✅", "selesai"
        elif d["dilewati"]:
            ikon, status = "➖", ("opsional, dilewati (centang sertakan_mbpp_v3 untuk menjalankan)" if k.mode == "pilot"
                                else "opsional, dilewati (centang sertakan_indopy_test untuk penilaian akhir)")
        elif d is berikut:
            ikon, status = "▶️", "berikutnya"
        elif d["butuh_v4"] and not ada_v4:
            ikon, status = "⏳", "menunggu training v4-pilot" if k.mode == "pilot" else "menunggu training v4"
        elif d.get("butuh_v3") and not adapter_ada(k.v3):
            ikon, status = "⏳", "menunggu training v3-ulang"
        else:
            ikon, status = "⬜", "belum"
        if not d["selesai"] and not d["dilewati"]:
            sisa += d["menit"]
        print(f"{ikon} {i:>2}. {d['judul']:<20} {'±' + str(d['menit']) + ' mnt':>10}   {status}")
    if berikut:
        print(f"\nPerkiraan sisa waktu GPU: ±{sisa / 60:.1f} jam. Jalankan sel 2 untuk melanjutkan.")
    else:
        print("\nSemua langkah selesai. Jalankan sel 4 untuk papan skor dan laporan.")
    return daftar


# ---------------------------------------------------------------- sel 2: jalankan

def jalankan(pilihan=OTOMATIS, opsional=False):
    k = konfig()
    mbpp_v3 = opsional
    log_dir = k.out / "panel-log"
    log_dir.mkdir(parents=True, exist_ok=True)
    while True:
        daftar = langkah_langkah(k, mbpp_v3)
        if pilihan == OTOMATIS:
            d = next((d for d in daftar if not d["selesai"] and not d["dilewati"]), None)
            if d is None:
                progres(mbpp_v3)
                return
        else:
            d = next((d for d in daftar if d["judul"] == pilihan), None)
            if d is None:
                raise SystemExit(f"langkah tidak dikenal: {pilihan}")
            if d["selesai"]:
                print(f"{d['judul']} sudah selesai. Untuk mengulang, hapus folder hasilnya di Drive dulu.")
                return
        if d["butuh_v4"] and adapter_v4(k) is None:
            latih = next(x["judul"] for x in daftar if x["kunci"] == "latih-v4")
            raise SystemExit(f"{d['judul']} butuh adapter v4. Jalankan langkah '{latih}' dulu.")
        if d.get("butuh_v3") and not adapter_ada(k.v3):
            raise SystemExit(f"{d['judul']} butuh adapter v3-ulang. Jalankan langkah 'Latih v3-ulang' dulu.")
        nomor = daftar.index(d) + 1
        judul(f"▶️ Langkah {nomor}/{len(daftar)}: {d['judul']} (±{d['menit']} menit)  ·  mulai {time.strftime('%H:%M')}")
        if k.demo and d["kunci"].startswith("latih-"):
            kode, ekor = latih_demo(k, d["kunci"])
        else:
            kode, ekor = jalankan_proses([sys.executable, "-u", *d["argv"]], cwd=str(k.kerja),
                                         log_path=log_dir / f"{d['kunci']}.log")
        if kode != 0 and (d.get("batch") or 0) > 1 and re.search(POLA_OOM, ekor):
            # Jawaban tersimpan per batch, jadi uji yang sama diulang dengan batch lebih kecil tanpa kehilangan hasil.
            k.batch[d["jenis"]] = d["batch"] // 2
            judul(f"⚠️ VRAM habis di {d['judul']}: diulang dengan batch {d['batch'] // 2} (sebelumnya {d['batch']})")
            continue
        if kode != 0:
            judul(f"❌ {d['judul']} gagal (exit code {kode})")
            saran = [s for pola, s in SARAN if re.search(pola, ekor)]
            if k.mode == "a100" and d["kunci"].startswith("latih-") and re.search(POLA_OOM, ekor):
                saran.insert(0, "VRAM habis saat training. Pilih konteks_training 12288 di sel 1, jalankan sel 1, "
                                "lalu sel 2. Checkpoint lama dipindah ke arsip/ dan training dimulai dari awal.")
            print("\n".join(saran) if saran else
                  "Lihat pesan error di atas. Jalankan sel 2 lagi untuk mencoba ulang; hasil yang sudah tersimpan "
                  f"tidak hilang. Log lengkap: {log_dir / (d['kunci'] + '.log')}")
            return
        if d["kunci"].startswith("latih-"):
            ringkas_training(k, ekor, d["kunci"])
        judul(f"✅ {d['judul']} selesai  ·  {time.strftime('%H:%M')}")
        if pilihan != OTOMATIS:
            progres(mbpp_v3)
            return
        progres(mbpp_v3)


def ringkas_training(k, ekor, kunci="latih-v4"):
    baris = [b for b in ekor.splitlines()
             if re.search(r"data valid:|sampel dipakai|sampel terpanjang|train_loss|\[status\] trained", b)]
    if baris:
        print("\nRingkasan training:\n  " + "\n  ".join(b.strip() for b in baris[-6:]))
    if kunci == "latih-v3":
        m = re.search(r"data valid: (\d+) sampel", ekor)
        if m and int(m[1]) != V3_ULANG_SAMPEL:
            print(f"\n⚠️ Training v3-ulang memakai {m[1]} sampel, bukan {V3_ULANG_SAMPEL}. Hapus folder "
                  "finetune-id/v3-ulang di Drive, jalankan sel 1, lalu sel 2.")
        return
    folder, run, latih = (("v4-pilot", "qwen3.5-4b-own-4bit", "Latih v4-pilot") if k.mode == "pilot"
                          else ("v4", "qwen3.5-4b-own", "Latih v4"))
    m = re.search(r"data valid: (\d+) sampel", ekor)
    if m and int(m[1]) != 102:
        print(f"\n⚠️ Training memakai {m[1]} sampel, bukan 102. Hapus finetune-id/{folder}/train.jsonl di Drive, "
              f"hapus folder {folder}/{run}, lalu jalankan langkah '{latih}' lagi.")
    m = re.search(r"(\d+) sampel dipakai, (\d+) dibuang", ekor)
    if m and int(m[2]):
        print(f"\n⚠️ {m[2]} sampel dibuang karena lebih panjang dari konteks training. Kirim baris di atas ke chat.")


def latih_demo(k, kunci="latih-v4"):
    """Mode demo: tidak ada GPU, jadi training diganti adapter tiruan."""
    if kunci == "latih-v3":
        n = sum(1 for b in k.data_v3.read_text(encoding="utf-8").splitlines() if b.strip())
        folder = Path(k.v3)
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "adapter_config.json").write_text(json.dumps({"demo": True}))
        (folder.parent / "status.json").write_text(json.dumps({
            "stage": "done", "data": {"samples": n, "dropped": [], "longest": 6100, "total_steps": 30},
            "result": {"train_runtime_min": 0.1, "train_loss": 0.6}}))
        teks = f"data valid: {n} sampel dari {k.data_v3}\n{n} sampel dipakai, 0 dibuang\n[status] trained\n"
        print(teks)
        return 0, teks
    run = k.folder_v4 / ("qwen3.5-4b-own-4bit" if k.mode == "pilot" else "qwen3.5-4b-own")
    folder = run / "lora-adapter"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "adapter_config.json").write_text(json.dumps({"demo": True}))
    (run / "status.json").write_text(json.dumps({
        "stage": "done", "max_seq_len": k.konteks,
        "data": {"samples": 102, "dropped": [], "longest": 6216, "total_steps": 39},
        "result": {"train_runtime_min": 0.1, "train_loss": 0.5},
        "tests": {"bengkel": {"tokens": 5200, "finished": True}, "absensi": {"tokens": 7400, "finished": True}}}))
    teks = (f"data valid: 102 sampel dari demo\n102 sampel dipakai, 0 dibuang karena > {k.konteks} token []\n"
            "[status] trained: adapter tersimpan\n")
    print(teks)
    return 0, teks


# ---------------------------------------------------------------- sel 4: laporan

def laporan():
    """Papan skor v3 dan v4, daftar yang gagal, dan ringkasan training; ditulis juga ke Drive."""
    k = konfig()
    if k.mode == "a100":
        return laporan_a100(k)
    v4 = adapter_v4(k)
    run_v3 = nama_run(k, k.v3, "v3-demo")
    run_v4 = nama_run(k, v4, "v4-demo") if v4 else None
    potongan = []

    def papan(*args):
        r = subprocess.run([sys.executable, script(k, "papan_skor.py"), "--root", str(k.out), *args],
                           capture_output=True, text=True)
        return r.stdout + r.stderr

    potongan.append(papan("--tag", run_v3))
    if run_v4:
        potongan.append(papan("--tag", run_v4, "--pembanding", run_v3))
    potongan.append(daftar_gagal(k, {"dasar": None, "v3": run_v3, "v4": run_v4}))
    log_latih = k.out / "panel-log" / "latih-v4.log"
    if log_latih.is_file():
        baris = [b.strip() for b in log_latih.read_text(errors="replace").splitlines()
                 if re.search(r"data valid:|sampel dipakai|train_loss", b)]
        potongan.append("=== Training v4-pilot ===\n" + "\n".join(baris[-4:]))
    teks = "\n".join(potongan)
    path = k.out / "laporan-v4-pilot.txt"
    path.write_text(teks, encoding="utf-8")
    print(teks)
    print(f"\nLaporan juga disimpan di {path}. Salin semua teks di atas ke chat.")


def laporan_a100(k):
    v4 = adapter_v4(k)
    run_v3 = nama_run(k, k.v3, "v3-demo")
    run_v4 = nama_run(k, v4, "v4-demo") if v4 else None

    def papan(*args):
        r = subprocess.run([sys.executable, script(k, "papan_skor.py"), "--root", str(k.hasil), *args],
                           capture_output=True, text=True)
        return r.stdout + r.stderr

    potongan = [f"Mode A100: v4 dan v3-ulang dari model dasar, LoRA 16-bit, konteks training {k.konteks}, "
                f"batas jawaban {A100_JAWABAN} token; semua uji 16-bit di {k.hasil}. v3-ulang = data commit "
                f"{V3_ULANG_COMMIT[:7]} ({V3_ULANG_SAMPEL} sampel); v4 = data itu + 23 sampel baru"]
    if run_v4:
        potongan.append(papan("--tag", run_v4, "--pembanding", run_v3))
    potongan.append("Papan v3-ulang di bawah hanya pembanding v3-ulang vs model dasar; gerbang G3 berlaku untuk v4 "
                    "(papan di atas).")
    potongan.append(papan("--tag", run_v3))
    potongan.append(daftar_gagal(k, {"dasar": None, "v3": run_v3, "v4": run_v4}))
    for nama, status in (("v4", k.folder_v4 / "qwen3.5-4b-own" / "status.json"),
                         ("v3-ulang", Path(k.v3).parent / "status.json")):
        if not status.is_file():
            continue
        st = json.loads(status.read_text())
        data, hasil, uji = st.get("data") or {}, st.get("result") or {}, st.get("tests") or {}
        potongan.append(
            f"=== Training {nama} ===\n"
            f"sampel {data.get('samples')}, dibuang {len(data.get('dropped') or [])}, terpanjang {data.get('longest')} "
            f"token, {data.get('total_steps')} step\n"
            f"train_loss {hasil.get('train_loss')}, lama {hasil.get('train_runtime_min')} menit"
            + ("\nwebsite uji: " + ", ".join(f"{n} {t.get('tokens')} token{'' if t.get('finished') else ' (terpotong)'}"
                                             for n, t in uji.items()) if uji else ""))
    if (k.hasil / "eval-indopy-test").is_dir():
        potongan.append("Catatan: IndoPy-test dikunci. Kirim skornya saja, jangan soal atau jawaban yang gagal.")
    teks = "\n".join(potongan)
    path = k.out / "laporan-v4-a100.txt"
    path.write_text(teks, encoding="utf-8")
    print(teks)
    print(f"\nLaporan juga disimpan di {path}. Salin semua teks di atas ke chat.")


def daftar_gagal(k, runs):
    keluar = []
    for folder, kunci_skor, label in (("eval-web", "web_lolos", "Web-eval: website yang gagal"),
                                      ("eval-indopy-dev", "indopy_pass@1", "IndoPy-dev: soal yang gagal")):
        keluar.append(f"\n=== {label} ===")
        for nama, run in runs.items():
            run = run if nama != "dasar" else nama_dasar(k, runs["v3"])
            f = k.hasil / folder / run / "ringkasan.json" if run else None
            if not f or not f.is_file():
                continue
            r = json.loads(f.read_text())
            skor = f"{round(r[kunci_skor] * r['soal'])}/{r['soal']}"
            ekstra = f", format Cek kebutuhan {r['format_cek_kebutuhan']}/{r['soal']}" if folder == "eval-web" else ""
            keluar.append(f"{nama}: lolos {skor}{ekstra}")
            for kunci, alasan in r["gagal"].items():
                keluar.append(f"   {kunci.rsplit('/', 1)[-1]}: {alasan[:150]}")
    return "\n".join(keluar)


if __name__ == "__main__":
    if len(sys.argv) in (3, 4) and sys.argv[1] == "--demo" and sys.argv[3:] in ([], ["--a100"]):
        siapkan(demo_out=sys.argv[2], mode="a100" if sys.argv[3:] else "pilot")
        jalankan(OTOMATIS, True)
        laporan()
    else:
        sys.exit(__doc__)
