# Panduan Colab V7 di A100: anti-hafalan, data sulingan model dasar, dan gerbang melawan model dasar

<!-- colab-gpu: A100 -->

Panduan ini melatih **V7**, adapter LoRA untuk Qwen3.5-4B, di GPU A100 Google Colab. V7 dibuat untuk memperbaiki masalah V6 (Codexia2): setelah 10 epoch, model menyalin sampel latihan kata per kata dan gagal di permintaan baru, sampai kalah dari model dasarnya sendiri.

| Bukti dari V6 | Artinya |
|---|---|
| Prompt to-do (sampel web-003): jawaban epoch 9 **identik 100%** dengan sampel latihan | menghafal |
| Prompt baru (antrean puskesmas): epoch 9 **error di baris pertama**, tidak ada satu tombol pun | kemampuan umum terkikis |
| Prompt baru yang sama di epoch 3: tidak error, tapi tombol Panggil tidak pernah dipasang | lebih sehat, tapi masih kurang |
| 1.131 dari 1.256 sampel adalah jawaban MBPP/HumanEval berukuran ±60–200 token, dilihat 10 kali | dosis besar pada data sempit |

<!-- hanya-md -->
**Buka notebook-nya di Colab:** [notebooks/v7_a100_colab.ipynb](https://colab.research.google.com/github/PvzKing/Dataset/blob/main/notebooks/v7_a100_colab.ipynb). Notebook itu dibangun dari file ini dengan `python scripts/md_to_notebook.py docs/PANDUAN_V7_A100.md notebooks/v7_a100_colab.ipynb`, jadi isinya sama.
<!-- /hanya-md -->

## Gambaran

### Empat perubahan dari V6

1. **Tanpa jawaban benchmark.** Jawaban HumanEval, MBPP+, dan MBPP tidak dilatih lagi. Akibatnya **keempat uji kembali bersih**: IndoPy-dev, Web-eval, MBPP+ (378 soal), dan HumanEval+ (164 soal). Dengan 562 soal yang bersih, perbandingan dengan model dasar jauh lebih bisa dipercaya daripada di V6 yang hanya punya 30 soal bersih.
2. **Data sulingan dari model dasar sendiri** (`scripts/sulingan.py`). Model dasar menjawab setiap soal beberapa kali, lalu hanya jawaban yang **lolos pemeriksaan otomatis** yang disimpan:
   - **Python:** 589 soal MBPP yang tidak masuk MBPP+ (split latihan MBPP), dibungkus sebagai permintaan berbahasa Indonesia. Lolos jika kodenya lulus **semua assert resmi** MBPP dan ada penjelasan di luar kode.
   - **Website:** 40 prompt baru di `data/sulingan/prompt-web.jsonl`. Lolos jika di Chromium halamannya terbuka tanpa error, tidak error saat semua input diisi dan semua tombol diklik, **benar-benar berubah setelah dipakai** (tombolnya terpasang), tidak ada scroll horizontal di HP, menyimpan ke localStorage jika diminta, dan ada bagian **Cek kebutuhan**.

   Karena jawabannya berasal dari model itu sendiri, bobotnya tidak dipaksa bergeser jauh. Yang dipelajari adalah **memilih jawaban yang benar**, bukan menghafal teks orang lain. Instruksi gaya (bahasa Indonesia, **Cek kebutuhan**) hanya dipakai saat membuat jawaban dan tidak ikut disimpan, jadi model belajar menjawab dengan gaya itu tanpa perlu diberi instruksi.
3. **Dosis kecil:** 2 epoch, lr 1e-4, batch efektif 8. Di V6: 10 epoch, lr 2e-4, batch efektif 4, atau ±20 kali lebih banyak update per sampel.
4. **Gerbang melawan model dasar.** Setiap epoch diuji dengan keempat uji bersih. Adapter V7 **hanya dipakai jika rata-ratanya minimal sama dengan model dasar**. Kalau model dasar lebih baik, laporan mengatakannya terus terang, ekspor dilewati, dan yang disarankan adalah memakai model dasar.

### Cara singkat

1. Buka notebook di Colab, pilih **Runtime → Change runtime type → A100 GPU** (High-RAM jika ada), lalu **File → Save a copy in Drive**.
2. Jalankan **Sel 1**, lalu periksa semua baris pengecekan bertanda ✅.
3. Jalankan **Sel 2**. Sel ini hanya mendefinisikan langkah-langkahnya, jadi selesai dalam sekejap.
4. Jalankan **Sel 3**. Sel ini menjalankan semua langkah secara berurutan:
   - sulingan Python dan website dari model dasar;
   - penggabungan data dan pengecekan kontaminasi;
   - training V7, 2 epoch;
   - uji setiap epoch dan model dasar;
   - gerbang: adapter atau model dasar;
   - ekspor dan laporan.

   Runtime tetap menyala setelah selesai. Matikan sendiri lewat **Runtime → Disconnect and delete runtime**, atau jalankan sel `matikan_runtime()` di Bagian E.
5. Baca laporannya di output Sel 3 atau di `MyDrive/finetune-id/V7/laporan-V7.txt`.

Perkiraan total **±4–7 jam** di A100. Angka ini belum pernah diukur; ETA di setiap langkah menunjukkan waktu sebenarnya.

| Langkah | Isi | Perkiraan |
|---|---|---|
| Sel 1 | cek GPU, pasang paket, hubungkan Drive, clone repo | ±8–12 menit pertama kali, berikutnya ±1 menit |
| Sulingan Python | 589 soal × 4 jawaban, diperiksa dengan assert MBPP | ±40–80 menit |
| Sulingan website | 40 prompt × 2 jawaban, diperiksa di Chromium | ±60–120 menit |
| Gabung dan cek data | pilih satu jawaban lolos per soal, buang yang tumpang tindih dengan soal uji | ±2 menit |
| Training | ±400–500 sampel × 2 epoch, lalu 2 website uji | ±30–60 menit |
| Uji | IndoPy-dev, Web-eval, MBPP+, HumanEval+ untuk epoch 1, epoch 2, dan model dasar | ±2–3 jam |
| Ekspor | GGUF Q4_K_M, hanya jika adapter lolos gerbang | ±10–20 menit |

### Resep V7

| Pengaturan | V7 | V6 | Alasan |
|---|---|---|---|
| Data | own (125) + sulingan website + sulingan Python (maks. 300) | own + jawaban HumanEval/MBPP+/MBPP (1.131) | jawaban sendiri, terverifikasi, tanpa jawaban benchmark |
| Epoch | **2**, adapter tiap epoch disimpan dan diuji | 10 | lebih dari ini mulai menghafal |
| Optimasi | lr **1e-4** cosine, warmup 10%, batch efektif **8** (1 × grad-accum 8) | lr 2e-4, batch efektif 4 | update lebih kecil dan lebih jarang |
| LoRA | r 16, alpha 32, semua layer linear bahasa, LoRA 16-bit (bf16) | sama | |
| Konteks | 16.384 token | sama | jawaban website sulingan bisa ±10 ribu token |
| Pemilihan | epoch terbaik dari 4 uji bersih, **dan** tidak boleh kalah dari model dasar | epoch 10 kecuali kandidat unggul ≥ 1 poin, tanpa pembanding dasar | gerbang yang jujur |
| Checkpoint | setiap 20 step ke Drive | setiap 50 step | run lebih pendek |

### Isi Google Drive setelah selesai

```
MyDrive/finetune-id/V7/
├── sulingan/
│   ├── kandidat-python.jsonl          semua jawaban model dasar + hasil pemeriksaannya (untuk melanjutkan)
│   ├── kandidat-web.jsonl
│   ├── situs/                         halaman website kandidat, bisa dibuka manual
│   ├── sulingan-python.jsonl          jawaban yang dipakai
│   ├── sulingan-web.jsonl
│   └── ringkasan-sulingan.json        tingkat lolos, jumlah dipakai, yang dibuang karena kontaminasi
├── train_v7.jsonl                     data gabungan yang dilatih
├── qwen3.5-4b-V7/
│   ├── qwen3.5-4b-V7-lora/            ← adapter V7 (epoch terpilih)
│   ├── epoch-1/ epoch-2/              adapter di akhir setiap epoch
│   ├── gguf/qwen3.5-4b-V7.Q4_K_M.gguf ← hanya jika V7 lolos gerbang
│   └── checkpoints/ …
├── PILIHAN-V7.json                    adapter atau model dasar, beserta angkanya
├── uji/eval-*/                        jawaban dan skor setiap uji
├── log/                               log lengkap setiap langkah
└── laporan-V7.txt                     ← laporan akhir
```

Siapkan ruang Drive kosong minimal **±8 GB**. Kalau `EKSPOR_16BIT = True`, tambah ±9 GB lagi.

---

## Bagian A. Persiapan sebelum menjalankan sel

1. Buka notebook ini dengan **akun Google yang Drive-nya akan menyimpan hasil**.
2. **File → Save a copy in Drive.** Salinan ini menyimpan output sel, jadi hasilnya tetap bisa dibaca setelah runtime dimatikan.
3. **Runtime → Change runtime type**: pilih **A100 GPU** dan aktifkan **High-RAM** jika ada, lalu **Save**.
4. A100 memakai **compute unit**. Cek sisanya di **Runtime → View resources**. Untuk ±4–7 jam A100, siapkan sekitar **55–95 unit**.
5. Biarkan tab browser tetap terbuka selama Sel 3 berjalan. Kalau runtime terputus, cukup ulangi Sel 1, 2, dan 3: sulingan, training, dan uji semuanya lanjut dari titik terakhir.

---

## Bagian B. Sel 1: pengaturan dan persiapan

Jalankan **di awal setiap sesi**, termasuk setelah Colab terputus atau Restart session. Pengaturan bawaannya sudah resep V7.

```python
# ===== SEL 1: PENGATURAN DAN PERSIAPAN (jalankan di awal setiap sesi) =====
KONTEKS = 16384                 # panjang maksimum satu sampel latihan; ganti ke 12288 hanya jika training kehabisan VRAM
EPOCH = 2                       # setiap epoch diuji; mengubahnya setelah training dimulai akan mengulang training
KANDIDAT_PYTHON = 4             # jawaban model dasar per soal MBPP; yang lolos semua assert yang dipakai
KANDIDAT_WEB = 2                # jawaban per prompt website; yang lolos pemeriksaan Chromium yang dipakai
MAKS_PYTHON = 300               # batas sampel Python sulingan, supaya data sendiri dan website tidak tenggelam
SERTAKAN_INDOPY_TEST = False    # set uji akhir yang dikunci (40 soal); True hanya sekali, untuk penilaian akhir
EKSPOR_GGUF = True              # file GGUF Q4_K_M (±2,7 GB), hanya jika V7 lolos gerbang
EKSPOR_16BIT = False            # model 16-bit utuh (±9 GB), hanya jika V7 lolos gerbang

import codecs, importlib.metadata, importlib.util, json, os, re, shutil, subprocess, sys, time
from pathlib import Path

NAMA, MODEL = "V7", "qwen3.5-4b"
ROOT = Path("/content/drive/MyDrive/finetune-id")
FOLDER = ROOT / NAMA                          # semua hasil V7
RUN = FOLDER / f"{MODEL}-{NAMA}"              # checkpoint, adapter, status.json
LORA = RUN / f"{MODEL}-{NAMA}-lora"           # adapter V7 final
SUL = FOLDER / "sulingan"                     # jawaban model dasar dan hasil pemeriksaannya
DATA = FOLDER / "train_v7.jsonl"              # own + sulingan, yang dilatih
PILIHAN = FOLDER / f"PILIHAN-{NAMA}.json"
HASIL = FOLDER / "uji"
LOG = FOLDER / "log"
REPO = Path("/content/Dataset")               # clone repo: script, data, dan soal uji
CABANG = ["main", "claude/youthful-mayer-lvf8r6"]  # dipakai cabang pertama yang sudah punya scripts/sulingan.py
EVALPLUS = "evalplus @ git+https://github.com/evalplus/evalplus@26d6d00bb1fd0fa37f39c99d5290da67891d1c5e"
OOM = r"CUDA out of memory|OutOfMemoryError"
LATIH = ["--dataset", "own", "--data", str(DATA), "--name", NAMA, "--out", str(FOLDER), "--no-load-in-4bit",
         "--max-seq-len", str(KONTEKS), "--epochs", str(EPOCH), "--lr", "1e-4", "--grad-accum", "8",
         "--save-steps", "20"]  # sama di semua perintah
WEB = ["--max-seq-len", str(KONTEKS), "--max-new-tokens", "12000"]
UJI = [  # (nama, script, folder hasil, argumen tambahan, batch, kunci skor); semuanya bersih di V7
    ("IndoPy-dev", "eval-suite/indopy_eval.py", "eval-indopy-dev", ["--split", "dev"], 16, "indopy_pass@1"),
    ("Web-eval", "eval-suite/web_eval.py", "eval-web", WEB, 5, "web_lolos"),
    ("MBPP+", "humaneval-bench-script/eval_humaneval.py", "eval-mbpp", ["--dataset", "mbpp"], 32, "mbpp+_pass@1"),
    ("HumanEval+", "humaneval-bench-script/eval_humaneval.py", "eval-humaneval", [], 32, "humaneval+_pass@1"),
]
UJI_AKHIR = ("IndoPy-test", "eval-suite/indopy_eval.py", "eval-indopy-test", ["--split", "test"], 16, "indopy_pass@1")


def judul(teks):
    print(f"\n{'=' * 78}\n{teks}\n{'=' * 78}", flush=True)


def jalan(argv, log):
    """Jalankan script sebagai proses terpisah (memori GPU bersih tiap langkah); output tampil langsung dan masuk log."""
    p = subprocess.Popen([sys.executable, "-u", *argv], cwd="/content", stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    dekode, ekor = codecs.getincrementaldecoder("utf-8")("replace"), ""
    try:
        with open(log, "a", encoding="utf-8") as f:
            while blok := os.read(p.stdout.fileno(), 4096):
                teks = dekode.decode(blok)
                print(teks, end="", flush=True)
                f.write(teks)
                ekor = (ekor + teks)[-20000:]
    except KeyboardInterrupt:  # tombol Stop di Colab: hentikan juga proses anaknya
        p.kill()
        raise
    return p.wait(), ekor


def epoch_lora(n):
    return RUN / f"epoch-{n}" / LORA.name


def tag_epoch(n):
    return f"{RUN.name}-epoch-{n}"  # nama run yang dibuat script uji dari path epoch_lora(n)


def pip(*a):
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", *a], check=True)


cek = []
judul("Sel 1. Persiapan")
gpu = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
                     capture_output=True, text=True).stdout.strip()
assert re.search(r"A100|H100", gpu), (f"GPU sekarang: {gpu or 'tidak ada'}. Pilih Runtime → Change runtime type → "
                                      "A100 GPU, lalu jalankan sel ini lagi.")
cek.append(("GPU", True, gpu))

if importlib.util.find_spec("unsloth") is None:
    print("memasang unsloth (±3–5 menit) ...", flush=True)
    pip("--upgrade", "unsloth")
if importlib.util.find_spec("evalplus") is None:
    print("memasang evalplus ...", flush=True)
    pip(EVALPLUS)
elif importlib.metadata.version("evalplus").startswith("0.3"):  # versi PyPI salah menilai HumanEval/32
    pip("--force-reinstall", "--no-deps", EVALPLUS)
if importlib.util.find_spec("playwright") is None:
    pip("playwright")
if not list(Path.home().glob(".cache/ms-playwright/chromium-*")):
    print("memasang Chromium untuk sulingan website dan Web-eval (±1–2 menit) ...", flush=True)
    subprocess.run([sys.executable, "-m", "playwright", "install", "--with-deps", "chromium"], check=True,
                   stdout=subprocess.DEVNULL)
importlib.invalidate_caches()
paket = {p: importlib.util.find_spec(p) is not None for p in ("unsloth", "evalplus", "playwright")}
paket["chromium"] = bool(list(Path.home().glob(".cache/ms-playwright/chromium-*")))
cek.append(("Paket", all(paket.values()), ", ".join(f"{p} {'ok' if v else 'GAGAL'}" for p, v in paket.items())))

if not Path("/content/drive/MyDrive").is_dir():
    from google.colab import drive
    drive.mount("/content/drive")
for folder in (FOLDER, SUL, HASIL, LOG):
    folder.mkdir(parents=True, exist_ok=True)
try:
    kosong = shutil.disk_usage("/content/drive/MyDrive").free / 1e9
    perlu = 8 + (9 if EKSPOR_16BIT else 0)
    cek.append(("Google Drive", kosong >= perlu, f"{FOLDER}, ruang kosong ±{kosong:.0f} GB (butuh ±{perlu} GB)"))
except OSError:
    cek.append(("Google Drive", True, f"{FOLDER} (ruang kosong tidak terbaca; pastikan ±8 GB tersedia)"))

for REF in CABANG:  # clone ulang setiap sesi supaya script dan soal uji sama dengan repo
    shutil.rmtree(REPO, ignore_errors=True)
    r = subprocess.run(["git", "clone", "-q", "--depth", "1", "--branch", REF, "https://github.com/PvzKing/Dataset",
                        str(REPO)], capture_output=True, text=True)
    if r.returncode == 0 and (REPO / "scripts" / "sulingan.py").is_file():
        break
else:
    raise SystemExit("Script V7 belum tersedia di GitHub. Kirim pesan ini ke chat.")
commit = subprocess.run(["git", "-C", str(REPO), "rev-parse", "--short", "HEAD"], capture_output=True,
                        text=True).stdout.strip()
own = sum(1 for baris in open(REPO / "data" / "train.jsonl") if baris.strip())
web = sum(1 for baris in open(REPO / "data" / "sulingan" / "prompt-web.jsonl") if baris.strip())
cek.append(("Repo", own > 0 and web > 0, f"cabang {REF} ({commit}): {own} sampel own, {web} prompt website sulingan"))

if (SUL / "ringkasan-sulingan.json").is_file():
    r = json.loads((SUL / "ringkasan-sulingan.json").read_text())
    cek.append(("Sulingan", True, f"sudah digabung: {r['total']} sampel di {DATA.name}"))
else:
    sudah = {j: sum(1 for b in open(SUL / f"kandidat-{j}.jsonl") if b.strip()) if (SUL / f"kandidat-{j}.jsonl").is_file()
             else 0 for j in ("python", "web")}
    cek.append(("Sulingan", True, f"belum selesai: {sudah['python']} soal Python dan {sudah['web']} prompt website "
                                  "sudah dijawab (dilanjutkan di Sel 3)"))

print()
for nama, ok, info in cek:
    print(f"{'✅' if ok else '❌'} {nama:<16} {info}")
print(f"\nResep: sulingan {KANDIDAT_PYTHON} jawaban/soal Python (maks. {MAKS_PYTHON} dipakai) dan {KANDIDAT_WEB} "
      f"jawaban/prompt website, {EPOCH} epoch, lr 1e-4, konteks {KONTEKS}, gerbang melawan model dasar.")
print("Siap. Jalankan Sel 2, lalu Sel 3." if all(ok for _, ok, _ in cek) else
      "Perbaiki yang bertanda ❌ (atau kirim pesannya ke chat), lalu jalankan sel ini lagi.")
```

**Output yang benar** (angka bisa sedikit berbeda):

```
✅ GPU              NVIDIA A100-SXM4-40GB, 40960 MiB
✅ Paket            unsloth ok, evalplus ok, playwright ok, chromium ok
✅ Google Drive     /content/drive/MyDrive/finetune-id/V7, ruang kosong ±80 GB (butuh ±8 GB)
✅ Repo             cabang main (abc1234): 125 sampel own, 40 prompt website sulingan
✅ Sulingan         belum selesai: 0 soal Python dan 0 prompt website sudah dijawab (dilanjutkan di Sel 3)
```

| Kalau muncul | Artinya | Yang dilakukan |
|---|---|---|
| `AssertionError: GPU sekarang: Tesla T4 ...` | runtime bukan A100 | ulangi Bagian A langkah 3 |
| `Script V7 belum tersedia di GitHub` | kedua cabang belum punya `scripts/sulingan.py`, atau clone gagal | kirim pesan ini ke chat |
| `chromium GAGAL` | Chromium gagal terpasang | jalankan `!playwright install --with-deps chromium` di sel baru, lalu Sel 1 lagi |
| tombol **Restart session** setelah instalasi | paket baru butuh runtime segar | klik tombolnya, lalu jalankan Sel 1 lagi |

---

## Bagian C. Sel 2: definisi langkah

Sel ini hanya mendefinisikan fungsi untuk setiap langkah, tanpa menjalankan apa pun. Jalankan setelah Sel 1, termasuk setelah Colab terputus.

```python
# ===== SEL 2: DEFINISI LANGKAH (tidak menjalankan apa-apa) =====
def sulingan(jenis):
    k, batch = (KANDIDAT_PYTHON, 8) if jenis == "python" else (KANDIDAT_WEB, 2)
    judul(f"Sulingan {jenis}: {k} jawaban model dasar per soal, hanya yang lolos pemeriksaan yang dipakai")
    if (SUL / "ringkasan-sulingan.json").is_file():
        print("sudah selesai")
        return
    while True:  # jawaban tersimpan per batch, jadi VRAM habis cukup diulang dengan batch lebih kecil
        kode, ekor = jalan([str(REPO / "scripts" / "sulingan.py"), jenis, "--out", str(SUL), "--k", str(k),
                            "--batch", str(batch), "--max-seq-len", str(KONTEKS)], LOG / f"sulingan-{jenis}.log")
        if kode != 0 and batch > 1 and re.search(OOM, ekor):
            batch //= 2
            print(f"\n⚠️ VRAM habis: sulingan {jenis} diulang dengan batch {batch}", flush=True)
            continue
        break
    if kode != 0:
        raise SystemExit(f"❌ Sulingan {jenis} gagal (exit code {kode}). Jalankan Sel 1, 2, dan 3 lagi untuk "
                         f"melanjutkan. Kalau gagal lagi, kirim log {LOG / f'sulingan-{jenis}.log'} ke chat.")


def gabung():
    judul("Gabung: own + sulingan, buang yang tumpang tindih dengan soal uji")
    kode, _ = jalan([str(REPO / "scripts" / "sulingan.py"), "gabung", "--out", str(SUL), "--hasil", str(DATA),
                     "--maks-python", str(MAKS_PYTHON)], LOG / "gabung.log")
    if kode != 0:
        raise SystemExit(f"❌ Gabung gagal (exit code {kode}). Kirim log {LOG / 'gabung.log'} ke chat.")
    r = json.loads((SUL / "ringkasan-sulingan.json").read_text())
    if r["sulingan_web"]["dipakai"] + r["sulingan_python"]["dipakai"] == 0:
        (SUL / "ringkasan-sulingan.json").unlink()
        raise SystemExit("❌ Tidak ada jawaban sulingan yang lolos. Kirim log sulingan di folder log ke chat.")


def cek_data():
    judul("Cek data training (tokenizer saja, tanpa model)")
    if (RUN / "ringkasan-training.json").is_file():
        print("training sudah selesai, cek data dilewati")
        return
    total = json.loads((SUL / "ringkasan-sulingan.json").read_text())["total"]
    kode, _ = jalan([str(REPO / "scripts" / "train_unsloth.py"), "prepare", *LATIH], LOG / "cek-data.log")
    data = (json.loads((RUN / "status.json").read_text()).get("data") or {}) if kode == 0 else {}
    if data.get("samples") != total or data.get("dropped"):
        raise SystemExit(f"❌ Data training tidak sesuai: {data.get('samples')} sampel (seharusnya {total}), "
                         f"{len(data.get('dropped') or [])} dibuang karena lebih dari {KONTEKS} token. Kirim log "
                         f"{LOG / 'cek-data.log'} ke chat.")
    print(f"✅ {total} sampel, 0 dibuang, terpanjang {data.get('longest')} token, {data.get('total_steps')} step")


def latih():
    judul(f"Training {NAMA}: {EPOCH} epoch, lr 1e-4, LoRA 16-bit, konteks {KONTEKS}, checkpoint tiap 20 step")
    if (RUN / "ringkasan-training.json").is_file():
        print(f"sudah selesai: {LORA}")
        return
    kode, ekor = jalan([str(REPO / "scripts" / "train_unsloth.py"), "train", *LATIH, "--epoch-adapters",
                        "--max-new-tokens", "12000"], LOG / "latih.log")
    if kode != 0:
        raise SystemExit(f"❌ Training gagal (exit code {kode}). " + (
            "VRAM habis: ganti KONTEKS = 12288 di Sel 1, lalu jalankan Sel 1, 2, dan 3 lagi." if re.search(OOM, ekor)
            else "Jalankan Sel 1, 2, dan 3 lagi untuk melanjutkan dari checkpoint. "
                 f"Kalau gagal lagi, kirim log {LOG / 'latih.log'} ke chat."))
    shutil.copy(RUN / "status.json", RUN / "ringkasan-training.json")  # status.json ditimpa oleh langkah ekspor


def uji(n, daftar=UJI):
    adapter = epoch_lora(n)
    assert (adapter / "adapter_config.json").is_file(), f"Adapter epoch {n} belum ada: {adapter}. Jalankan training dulu."
    for i, (nama, script, folder, extra, batch, _) in enumerate(daftar, 1):
        judul(f"Uji epoch {n} · {i}/{len(daftar)}: {nama}")
        if (HASIL / folder / tag_epoch(n) / "ringkasan.json").is_file():
            print("sudah selesai")
            continue
        while True:  # model dasar ikut dijawab (sekali saja, lalu dipakai ulang) dan dibandingkan dengan McNemar
            kode, ekor = jalan([str(REPO / script), "--adapter", str(adapter), "--results", str(HASIL / folder),
                                "--no-load-in-4bit", "--batch-size", str(batch), *extra], LOG / f"{folder}-epoch{n}.log")
            if kode != 0 and batch > 1 and re.search(OOM, ekor):
                batch //= 2
                print(f"\n⚠️ VRAM habis: {nama} diulang dengan batch {batch}", flush=True)
                continue
            break
        if kode != 0:
            raise SystemExit(f"❌ {nama} gagal (exit code {kode}). Jalankan Sel 1, 2, dan 3 lagi untuk melanjutkan. "
                             f"Kalau gagal lagi, kirim log {LOG / (folder + f'-epoch{n}.log')} ke chat.")


def skor(n, folder, kunci):
    f = HASIL / folder / (tag_epoch(n) if n else "model-dasar") / "ringkasan.json"
    return json.loads(f.read_text()).get(kunci) if f.is_file() else None


def rata(n):
    """Rata-rata empat uji bersih untuk epoch n, atau model dasar jika n None."""
    nilai = [skor(n, folder, kunci) for _, _, folder, _, _, kunci in UJI]
    if None in nilai:
        raise SystemExit(f"Uji {'model dasar' if n is None else f'epoch {n}'} belum lengkap. Jalankan uji dulu.")
    return sum(nilai) / len(nilai)


def pilih():
    judul(f"Gerbang {NAMA}: epoch terbaik melawan model dasar")
    if PILIHAN.is_file():
        print(json.loads(PILIHAN.read_text())["teks"])
        return
    nilai = {n: rata(n) for n in range(1, EPOCH + 1)}
    dasar = rata(None)
    terbaik = max(nilai, key=lambda n: (nilai[n], n))
    rinci = (f"rata-rata IndoPy-dev, Web-eval, MBPP+, dan HumanEval+: model dasar {dasar:.1%}, "
             + ", ".join(f"epoch {n} {v:.1%}" for n, v in sorted(nilai.items())))
    if nilai[terbaik] >= dasar:
        if terbaik != EPOCH:
            shutil.rmtree(LORA)
            shutil.copytree(epoch_lora(terbaik), LORA)
        pakai = f"epoch-{terbaik}"
        teks = f"{NAMA} memakai adapter epoch {terbaik} ({LORA}).\nAlasan: {rinci}."
    else:
        pakai = "model-dasar"
        teks = (f"{NAMA} TIDAK dipakai: model dasar lebih baik.\nAlasan: {rinci}.\n"
                f"Pakai model dasar (misalnya codexia_studio.py --adapter none). Adapter epoch {terbaik} tetap ada di "
                f"{epoch_lora(terbaik)} untuk dianalisis, tetapi tidak diekspor.")
    PILIHAN.write_text(json.dumps({"pakai": pakai, "epoch_terbaik": terbaik, "rata_epoch": nilai, "rata_dasar": dasar,
                                   "teks": teks}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(teks)


def uji_akhir():
    if not SERTAKAN_INDOPY_TEST:
        return
    n = json.loads(PILIHAN.read_text())["epoch_terbaik"]
    uji(n, [UJI_AKHIR])  # model dasar ikut dijawab, jadi tetap ada pembanding walaupun gerbang memilih model dasar


def ekspor():
    assert PILIHAN.is_file(), "Jalankan pilih() dulu, supaya yang diekspor adalah adapter final."
    if json.loads(PILIHAN.read_text())["pakai"] == "model-dasar":
        judul("Ekspor dilewati: model dasar lebih baik daripada V7")
        return
    langkah = [("GGUF Q4_K_M", "gguf", EKSPOR_GGUF, lambda: list((RUN / "gguf").glob(f"*{NAMA}*.gguf"))),
               ("model 16-bit", "merge", EKSPOR_16BIT, lambda: (RUN / f"{MODEL}-{NAMA}-merged-16bit" / "config.json").is_file())]
    for nama, perintah, aktif, sudah in langkah:
        if not aktif:
            continue
        judul(f"Ekspor {nama}")
        if sudah():
            print("sudah selesai")
            continue
        kode, _ = jalan([str(REPO / "scripts" / "train_unsloth.py"), perintah, *LATIH], LOG / f"{perintah}.log")
        if kode != 0:
            raise SystemExit(f"❌ Ekspor {nama} gagal (exit code {kode}). Adapter {NAMA} aman di {LORA}. "
                             f"Kirim log {LOG / (perintah + '.log')} ke chat.")


def laporan():
    judul(f"Laporan {NAMA} (salin semua teks di bawah ke chat)")
    pilihan = json.loads(PILIHAN.read_text())["teks"] if PILIHAN.is_file() else "gerbang belum dijalankan"
    epochs = [n for n in range(1, EPOCH + 1) if (HASIL / "eval-web" / tag_epoch(n)).is_dir()]
    kolom = ["model dasar"] + [f"{NAMA} ep {n}" for n in epochs]
    baris = [f"{NAMA}: own + sulingan model dasar, tanpa jawaban benchmark, LoRA 16-bit, {EPOCH} epoch, lr 1e-4, "
             f"konteks {KONTEKS}, uji 16-bit di A100, greedy pass@1. Semua uji bersih.", pilihan, "",
             f"{'uji':<22}" + "".join(f"{k:>13}" for k in kolom)]
    daftar = [(n, f, k) for n, _, f, _, _, k in UJI + ([UJI_AKHIR] if SERTAKAN_INDOPY_TEST else [])]
    for nama, folder, kunci in daftar:
        nilai = [skor(n, folder, kunci) for n in [None] + epochs]
        baris.append(f"{nama:<22}" + "".join(f"{'-' if v is None else f'{v:.1%}':>13}" for v in nilai))
    format_web = []
    for n in [None] + epochs:
        f = HASIL / "eval-web" / (tag_epoch(n) if n else "model-dasar") / "ringkasan.json"
        format_web.append(f"{json.loads(f.read_text())['format_cek_kebutuhan']}/{json.loads(f.read_text())['soal']}"
                          if f.is_file() else "-")
    baris.append(f"{'format Cek kebutuhan':<22}" + "".join(f"{v:>13}" for v in format_web))
    baris.append("\nPerbandingan dengan model dasar (McNemar; p < 0,05 berarti nyata):")
    for n in epochs:
        for nama, folder, _ in daftar:
            f = HASIL / folder / f"perbandingan-{tag_epoch(n)}.json"
            if not f.is_file():
                continue
            for uji_, r in json.loads(f.read_text()).items():
                if isinstance(r, dict) and "p_mcnemar" in r:
                    baris.append(f"  epoch {n} · {uji_:<12} selisih {r['selisih_soal']:+d} soal "
                                 f"({r['selisih_poin_persen']:+.1f} poin), p = {r['p_mcnemar']:.3f}")
    for n in epochs:
        f = HASIL / "eval-web" / tag_epoch(n) / "ringkasan.json"
        if f.is_file():
            baris += [f"Web-eval epoch {n} gagal {k.rsplit('/', 1)[-1]}: {alasan[:150]}"
                      for k, alasan in json.loads(f.read_text())["gagal"].items()]
    s = SUL / "ringkasan-sulingan.json"
    if s.is_file():
        s = json.loads(s.read_text())
        baris.append("\n=== Sulingan ===")
        for jenis in ("python", "web"):
            r = s[f"sulingan_{jenis}"]
            baris.append(f"{jenis:<7} kandidat lolos {r['kandidat_lolos']}/{r['kandidat']}, "
                         f"{r['soal_punya_jawaban_lolos']}/{r['soal']} soal punya jawaban lolos, dipakai {r['dipakai']}")
        baris.append(f"dibuang karena tumpang tindih dengan soal uji: {len(s['dibuang_kontaminasi'])}; "
                     f"data training {s['total']} sampel ({s['own']} own)")
    st = RUN / "ringkasan-training.json"
    if st.is_file():
        st = json.loads(st.read_text())
        data, hasil, tes = st.get("data") or {}, st.get("result") or {}, st.get("tests") or {}
        baris += ["\n=== Training ===",
                  f"sampel {data.get('samples')}, dibuang {len(data.get('dropped') or [])}, terpanjang "
                  f"{data.get('longest')} token, {data.get('total_steps')} step",
                  f"train_loss {hasil.get('train_loss')}, lama {hasil.get('train_runtime_min')} menit",
                  "website uji: " + (", ".join(f"{k} {t.get('tokens')} token{'' if t.get('finished') else ' (terpotong)'}"
                                               for k, t in tes.items()) or "-")]
    model = [str(f) for f in sorted((RUN / "gguf").glob("*.gguf"))]
    if (RUN / f"{MODEL}-{NAMA}-merged-16bit").is_dir():
        model.append(str(RUN / f"{MODEL}-{NAMA}-merged-16bit"))
    baris += [f"\n=== Model {NAMA} di Drive ===", f"  {LORA}"] + [f"  {m}" for m in model]
    if SERTAKAN_INDOPY_TEST:
        baris.append("Catatan: IndoPy-test dikunci. Kirim skornya saja, jangan soal atau jawaban yang gagal.")
    teks = "\n".join(baris)
    (FOLDER / f"laporan-{NAMA}.txt").write_text(teks + "\n", encoding="utf-8")
    print(teks)
    print(f"\nLaporan juga disimpan di {FOLDER / f'laporan-{NAMA}.txt'}")


def matikan_runtime():
    """Putuskan dan hapus runtime supaya compute unit berhenti terpakai. Output sel tetap tersimpan di notebook."""
    print("\nMenyimpan Drive, lalu mematikan runtime dalam 30 detik ...", flush=True)
    from google.colab import drive, runtime
    time.sleep(30)  # beri waktu output terakhir tampil dan tersimpan di notebook
    drive.flush_and_unmount()
    runtime.unassign()


def jalankan_semua():
    sulingan("python")
    sulingan("web")
    if not (SUL / "ringkasan-sulingan.json").is_file():
        gabung()
    cek_data()
    latih()
    for n in sorted(range(1, EPOCH + 1), reverse=True):  # epoch terakhir dulu; model dasar ikut dijawab sekali
        uji(n)
    pilih()
    uji_akhir()
    ekspor()
    laporan()


print("Langkah siap. Jalankan Sel 3 untuk menjalankan semuanya, atau sel di Bagian E untuk satu langkah.")
```

## Bagian D. Sel 3: jalankan semua

Sel ini menjalankan semua langkah yang belum selesai, berurutan. Langkah yang sudah selesai dilewati, jadi aman dijalankan ulang kapan pun. Runtime tetap menyala setelah selesai atau gagal.

```python
# ===== SEL 3: JALANKAN SEMUA (sulingan, training, uji, gerbang, ekspor, laporan) =====
jalankan_semua()
```

**Yang muncul berurutan:**

| Bagian | Baris penting | Arti |
|---|---|---|
| Sulingan Python | `python: 589 soal, 0 sudah, 589 dikerjakan; 4 kandidat per soal` | soal MBPP di luar MBPP+ |
| | `akhir prompt pertama: '...'` | ujung prompt yang dikirim ke model: template chat tanpa mode berpikir, sama dengan training |
| | `[python] 16/589 soal · batch ini 7/8 punya jawaban lolos · 2 menit, sisa ±60 menit` | berjalan; tersimpan per batch |
| | `gagal mbpp-12: AssertionError` | contoh jawaban yang dibuang. Wajar, itulah gunanya pemeriksaan |
| Sulingan website | `[web] 2/40 soal · batch ini 1/2 punya jawaban lolos` | setiap halaman diuji di Chromium |
| | `gagal sw-03-kpr: halaman tidak berubah apa pun setelah ...` | tombolnya tidak terpasang, dibuang |
| Gabung | `python 589 soal, kandidat lolos 1700/2356 (72%), ... dipakai 300` | angka sebenarnya bergantung pada model dasar |
| | `data gabungan: 125 own + 31 web + 300 python = 456 sampel` | data yang dilatih |
| Cek data | `✅ 456 sampel, 0 dibuang, terpanjang ±10000 token, 114 step` | semua sampel muat |
| Training | `cek masking: ... token sampel pertama ikut dilatih`, progress bar, `adapter epoch 1 … 2 disimpan` | hanya jawaban asisten yang dilatih |
| Uji | `[qwen3.5-4b-V7-epoch-2] ...`, lalu `model-dasar`, lalu tabel perbandingan | model dasar hanya dijawab sekali per uji |
| Gerbang | `V7 memakai adapter epoch N` **atau** `V7 TIDAK dipakai: model dasar lebih baik` | keputusan akhir beserta angkanya |
| Laporan | tabel model dasar dan setiap epoch | salin ke chat |

**Cara membaca loss.** Loss jawaban sulingan sudah rendah sejak awal karena jawabannya berasal dari model itu sendiri. Loss yang turun pelan **bukan** tanda gagal. Yang menentukan adalah tabel uji di laporan.

**Contoh bentuk laporan.** Angka di bawah hanya contoh tampilan:

```
uji                      model dasar     V7 ep 1     V7 ep 2
IndoPy-dev                      x,x%        x,x%        x,x%
Web-eval                        x,x%        x,x%        x,x%
MBPP+                           x,x%        x,x%        x,x%
HumanEval+                      x,x%        x,x%        x,x%
format Cek kebutuhan            x/10        x/10        x/10
```

---

## Bagian E. Langkah satu per satu (opsional)

Pakai sel-sel ini sebagai pengganti Sel 3. Jalankan Sel 1 dan Sel 2 dulu.

```python
sulingan("python")          # jawaban model dasar untuk soal MBPP di luar MBPP+ (lanjut jika terputus)
sulingan("web")             # jawaban model dasar untuk 40 prompt website
gabung()                    # pilih jawaban lolos, buang yang tumpang tindih dengan soal uji
```

```python
cek_data()
latih()                     # training V7 (lanjut dari checkpoint jika ada)
```

```python
for n in range(EPOCH, 0, -1):   # uji setiap epoch; model dasar ikut dijawab sekali
    uji(n)
pilih()                     # gerbang: adapter atau model dasar
uji_akhir()                 # IndoPy-test, hanya jika SERTAKAN_INDOPY_TEST = True
ekspor()
laporan()
```

```python
matikan_runtime()           # matikan runtime sekarang; output sel tetap ada
```

**Cek progres setelah Colab terputus**, tanpa memuat model. Jalankan setelah Sel 1 dan Sel 2:

```python
def baris_jsonl(f):
    return sum(1 for b in open(f) if b.strip()) if f.is_file() else 0

for nama, ada in [("Sulingan Python", baris_jsonl(SUL / "kandidat-python.jsonl") >= 580),
                  ("Sulingan website", baris_jsonl(SUL / "kandidat-web.jsonl") >= 40),
                  ("Gabung", (SUL / "ringkasan-sulingan.json").is_file()),
                  ("Training", (RUN / "ringkasan-training.json").is_file()),
                  *[(f"Adapter epoch {n}", (epoch_lora(n) / "adapter_config.json").is_file()) for n in range(1, EPOCH + 1)],
                  *[(f"Uji epoch {n} {u[0]}", (HASIL / u[2] / tag_epoch(n) / "ringkasan.json").is_file())
                    for n in range(1, EPOCH + 1) for u in UJI],
                  ("Gerbang", PILIHAN.is_file()),
                  ("Laporan", (FOLDER / f"laporan-{NAMA}.txt").is_file())]:
    print(f"{'✅' if ada else '⬜'} {nama}")
print(f"\nsoal yang sudah dijawab: Python {baris_jsonl(SUL / 'kandidat-python.jsonl')}, "
      f"website {baris_jsonl(SUL / 'kandidat-web.jsonl')}")
if (RUN / "status.json").is_file():
    st = json.loads((RUN / "status.json").read_text())
    print("status training terakhir:", {k: st.get(k) for k in ("stage", "message", "step", "max_steps", "loss", "eta_min")})
```

---

## Bagian F. Kalau ada masalah

| Gejala | Penyebab | Yang dilakukan |
|---|---|---|
| Colab terputus di tengah jalan | sesi habis, tab ditutup, atau A100 diambil kembali | jalankan Sel 1, 2, dan 3 lagi. Sulingan lanjut dari batch terakhir, training dari checkpoint terakhir, dan uji yang selesai dilewati |
| `VRAM habis: sulingan ... diulang dengan batch N` | batch generate terlalu besar | tidak perlu apa-apa: batch diturunkan otomatis tanpa kehilangan jawaban |
| tingkat lolos sulingan website sangat rendah (misalnya 5 dari 40) | model dasar sering membuat halaman yang error atau tombol yang tidak terpasang | wajar untuk model 4B. Training tetap jalan dengan yang lolos. Kalau ingin lebih banyak, naikkan `KANDIDAT_WEB = 3`, hapus `sulingan/kandidat-web.jsonl`, lalu Sel 1–3 |
| `Tidak ada jawaban sulingan yang lolos` | ada yang salah dengan model atau pemeriksaan | kirim `log/sulingan-python.log` ke chat |
| `CUDA out of memory` saat training | jawaban website sulingan yang panjang | ganti `KONTEKS = 12288` di Sel 1, lalu jalankan Sel 1, 2, dan 3. Sampel yang lebih panjang dari itu dibuang, dan cek data akan melaporkannya |
| `data atau pengaturan berubah: hasil lama dipindah ke ...arsip...` | `EPOCH`, `KONTEKS`, atau data gabungan berubah sejak checkpoint dibuat | wajar jika memang sengaja diubah |
| Gerbang memilih model dasar | V7 tidak lebih baik daripada model dasar di uji bersih | ini hasil yang sah, bukan error. Pakai model dasar, dan kirim laporannya ke chat untuk dianalisis |
| Uji berjalan sangat lambat (puluhan token/detik) | paket `causal_conv1d` belum terpasang | opsional: `!pip install causal-conv1d --no-build-isolation` (kompilasi ±10–20 menit), Restart session, lalu Sel 1–3 |
| Ingin mengulang sulingan dari nol | | hapus folder `MyDrive/finetune-id/V7/sulingan` dan `train_v7.jsonl`, lalu Sel 1–3. Training ikut diulang karena datanya berubah |

---

## Bagian G. Memakai model V7

Kalau gerbang memilih adapter V7, buka di Codexia Studio (A100 atau L4):

```python
!pip install -q --upgrade unsloth "gradio>=5.40,<7"
!wget -q -O /content/codexia_studio.py https://raw.githubusercontent.com/PvzKing/Dataset/main/scripts/codexia_studio.py
%run /content/codexia_studio.py --adapter /content/drive/MyDrive/finetune-id/V7/qwen3.5-4b-V7/qwen3.5-4b-V7-lora
```

Kalau gerbang memilih model dasar, ganti baris terakhir dengan `%run /content/codexia_studio.py --adapter none`.

Untuk Ollama, LM Studio, atau llama.cpp, unduh `qwen3.5-4b-V7.Q4_K_M.gguf` dari Drive, lalu ikuti langkah Bagian G di `docs/PANDUAN_V6_A100.md` dengan nama V7.

---

## Catatan hukum

- **Jawaban model dasar sebagai data latihan.** Qwen3.5-4B dirilis dengan Apache License 2.0 (pastikan lagi di model card saat membagikan). Lisensi itu tidak membatasi pemakaian output model, jadi melatih model dengan jawabannya sendiri diperbolehkan. Ini juga alasan V7 **tidak** memakai jawaban dari layanan AI lain: syarat layanan beberapa penyedia melarang outputnya dipakai untuk melatih model, dan melanggarnya adalah wanprestasi (Pasal 1238 dan 1243 KUHPerdata).
- **Soal MBPP.** Sampel sulingan Python memuat teks soal dan contoh assert dari MBPP (Google Research), CC BY 4.0. Kalau `train_v7.jsonl` atau `sulingan-python.jsonl` dibagikan, Section 3(a) lisensi itu mewajibkan: sebut pencipta (Google Research), cantumkan lisensi atau tautannya (`data/bench-support/LICENSE-MBPP-CC-BY-4.0.txt`), dan nyatakan perubahannya: soal dibungkus ulang sebagai permintaan berbahasa Indonesia, dan jawabannya dibuat ulang oleh Qwen3.5-4B, bukan solusi asli MBPP.
- **Lisensi model dasar.** Jika adapter atau GGUF V7 dibagikan, Pasal 4 Apache 2.0 mewajibkan salinan lisensi disertakan, pemberitahuan bahwa model sudah diubah (fine-tuning), dan atribusi karya asal dipertahankan.
- **Klaim mutu.** Berbeda dengan V6, keempat uji V7 bersih, jadi skornya boleh dipakai sebagai ukuran kemampuan, dengan syarat:
  - sebutkan kondisi ujinya (greedy, pass@1, 16-bit di A100), dan bahwa IndoPy dan Web-eval adalah uji buatan sendiri;
  - sebutkan bahwa data latihan memuat soal-soal split latihan MBPP (bukan soal MBPP+);
  - klaim "lebih baik dari model dasar" hanya untuk selisih yang nyata menurut McNemar (`p < 0,05`);
  - kalau gerbang memilih model dasar, jangan menawarkan V7 sebagai peningkatan.

  Menawarkan produk dengan klaim mutu yang tidak sesuai kenyataan dilarang Pasal 8 ayat (1) huruf f dan Pasal 9 ayat (1) huruf a dan k UU No. 8 Tahun 1999 tentang Perlindungan Konsumen, dan Pasal 10 melarang pernyataan yang menyesatkan tentang kegunaan barang atau jasa, dengan ancaman pidana menurut Pasal 62 ayat (1).
- **Data pribadi.** Prompt website sulingan memakai data contoh dan fiktif. Halaman yang dibuat model bisa berisi nama atau nomor HP rekaan; tidak ada data pribadi orang sungguhan yang dikumpulkan. Kalau prompt baru ditambahkan dari pekerjaan nyata, hapus atau samarkan data pribadinya dulu sesuai UU No. 27 Tahun 2022 tentang Pelindungan Data Pribadi.
