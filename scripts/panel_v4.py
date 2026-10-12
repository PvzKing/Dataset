"""Panel interaktif v4-pilot untuk Google Colab: siapkan, jalankan langkah yang belum selesai, progres, laporan.

Dipakai oleh notebooks/v4_pilot_interaktif.ipynb. Cara kerjanya:
  - setiap langkah (uji atau training) dijalankan sebagai proses terpisah, jadi memori GPU selalu bersih di awal
    langkah berikutnya dan sesi Colab tidak perlu di-restart;
  - status setiap langkah dibaca dari hasilnya di Google Drive, jadi kalau Colab terputus, jalankan sel yang sama
    lagi dan panel melanjutkan dari langkah yang belum selesai;
  - output setiap langkah juga disimpan di Drive (finetune-id/panel-log/), dan laporan akhir ditulis ke
    finetune-id/laporan-v4-pilot.txt.

Mode demo (tanpa GPU dan tanpa Colab) menguji alurnya dengan jawaban tiruan:
    python scripts/panel_v4.py --demo /tmp/panel-demo
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
    log: list = field(default_factory=list)


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
    return (k.out / folder / run / "ringkasan.json").is_file()


# ---------------------------------------------------------------- daftar langkah

def langkah_langkah(k, mbpp_v3=False):
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


# ---------------------------------------------------------------- sel 1: siapkan

def siapkan(adapter_v3=V3_BAWAAN, demo_out=None):
    """Cek GPU, pasang paket yang belum ada, mount Drive, unduh script terbaru, dan periksa adapter v3."""
    global KONFIG
    k = Konfig(v3=adapter_v3.strip()) if demo_out is None else Konfig(
        v3="demo", out=Path(demo_out), kerja=ROOT_REPO, demo=True, limit=12)
    cek = []
    judul("Persiapan")
    if not k.demo:
        gpu = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
                             capture_output=True, text=True)
        if gpu.returncode != 0:
            cek.append(("GPU", False, "tidak ada GPU. Pilih Runtime → Change runtime type → T4 GPU, lalu jalankan "
                                      "sel ini lagi"))
            return laporkan_cek(cek)
        cek.append(("GPU", True, gpu.stdout.strip()))

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

        ada_v3 = (Path(k.v3) / "adapter_config.json").is_file()
        info = k.v3
        if not ada_v3:
            calon = sorted(str(p.parent) for p in k.out.glob("*/*/lora-adapter/adapter_config.json"))
            info = f"tidak ditemukan: {k.v3}" + ("\n      adapter yang ada di Drive:\n      " + "\n      ".join(calon)
                                                   if calon else "")
        cek.append(("Adapter v3", ada_v3, info))
    else:
        k.out.mkdir(parents=True, exist_ok=True)
        cek.append(("Mode demo", True, f"hasil di {k.out}"))

    KONFIG = k
    if all(ok for _, ok, _ in cek) and not k.demo:
        CONFIG_FILE.write_text(json.dumps({"v3": k.v3}))  # supaya sel 2–4 tetap jalan setelah Restart session
    laporkan_cek(cek)
    if all(ok for _, ok, _ in cek):
        progres()


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
        KONFIG = Konfig(v3=json.loads(CONFIG_FILE.read_text())["v3"])
    if KONFIG is None:
        raise SystemExit("Jalankan sel 1 (Siapkan) dulu.")
    return KONFIG


# ---------------------------------------------------------------- sel 3: progres

def progres(mbpp_v3=False):
    k = konfig()
    daftar = langkah_langkah(k, mbpp_v3)
    ada_v4 = adapter_v4(k) is not None
    berikut = next((d for d in daftar if not d["selesai"] and not d["dilewati"]), None)
    print(f"\n{'':2} {'langkah':<22} {'perkiraan':>10}   status")
    sisa = 0
    for i, d in enumerate(daftar, 1):
        if d["selesai"]:
            ikon, status = "✅", "selesai"
        elif d["dilewati"]:
            ikon, status = "➖", "opsional, dilewati (centang sertakan_mbpp_v3 untuk menjalankan)"
        elif d is berikut:
            ikon, status = "▶️", "berikutnya"
        elif d["butuh_v4"] and not ada_v4:
            ikon, status = "⏳", "menunggu training v4-pilot"
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

def jalankan(pilihan=OTOMATIS, mbpp_v3=False):
    k = konfig()
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
            raise SystemExit(f"{d['judul']} butuh adapter v4-pilot. Jalankan langkah 'Latih v4-pilot' dulu.")
        nomor = daftar.index(d) + 1
        judul(f"▶️ Langkah {nomor}/{len(daftar)}: {d['judul']} (±{d['menit']} menit)  ·  mulai {time.strftime('%H:%M')}")
        if k.demo and d["kunci"] == "latih-v4":
            kode, ekor = latih_demo(k)
        else:
            kode, ekor = jalankan_proses([sys.executable, "-u", *d["argv"]], cwd=str(k.kerja),
                                         log_path=log_dir / f"{d['kunci']}.log")
        if kode != 0:
            judul(f"❌ {d['judul']} gagal (exit code {kode})")
            saran = [s for pola, s in SARAN if re.search(pola, ekor)]
            print("\n".join(saran) if saran else
                  "Lihat pesan error di atas. Jalankan sel 2 lagi untuk mencoba ulang; hasil yang sudah tersimpan "
                  f"tidak hilang. Log lengkap: {log_dir / (d['kunci'] + '.log')}")
            return
        if d["kunci"] == "latih-v4":
            ringkas_training(ekor)
        judul(f"✅ {d['judul']} selesai  ·  {time.strftime('%H:%M')}")
        if pilihan != OTOMATIS:
            progres(mbpp_v3)
            return
        progres(mbpp_v3)


def ringkas_training(ekor):
    baris = [b for b in ekor.splitlines() if re.search(r"data valid:|sampel dipakai|train_loss|\[status\] trained", b)]
    if baris:
        print("\nRingkasan training:\n  " + "\n  ".join(b.strip() for b in baris[-5:]))
    m = re.search(r"data valid: (\d+) sampel", ekor)
    if m and int(m[1]) != 102:
        print(f"\n⚠️ Training memakai {m[1]} sampel, bukan 102. Hapus finetune-id/v4-pilot/train.jsonl di Drive, "
              "hapus folder v4-pilot/qwen3.5-4b-own-4bit, lalu jalankan langkah 'Latih v4-pilot' lagi.")


def latih_demo(k):
    """Mode demo: tidak ada GPU, jadi training diganti adapter tiruan."""
    folder = k.out / "v4-pilot" / "qwen3.5-4b-own-4bit" / "lora-adapter"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "adapter_config.json").write_text(json.dumps({"demo": True}))
    teks = "data valid: 102 sampel dari demo\n102 sampel dipakai, 0 dibuang\n[status] trained: adapter tersimpan\n"
    print(teks)
    return 0, teks


# ---------------------------------------------------------------- sel 4: laporan

def laporan():
    """Papan skor v3 dan v4-pilot, daftar yang gagal, dan ringkasan training; ditulis juga ke Drive."""
    k = konfig()
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


def daftar_gagal(k, runs):
    keluar = []
    for folder, kunci_skor, label in (("eval-web", "web_lolos", "Web-eval: website yang gagal"),
                                      ("eval-indopy-dev", "indopy_pass@1", "IndoPy-dev: soal yang gagal")):
        keluar.append(f"\n=== {label} ===")
        for nama, run in runs.items():
            run = run if nama != "dasar" else nama_dasar(k, runs["v3"])
            f = k.out / folder / run / "ringkasan.json" if run else None
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
    if len(sys.argv) == 3 and sys.argv[1] == "--demo":
        siapkan(demo_out=sys.argv[2])
        jalankan(OTOMATIS, mbpp_v3=True)
        laporan()
    else:
        sys.exit(__doc__)
