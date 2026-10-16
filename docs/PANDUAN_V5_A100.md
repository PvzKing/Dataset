# Panduan Colab V5 di A100: dataset own + HumanEval, dengan checkpoint di Google Drive

<!-- colab-gpu: A100 -->

Panduan ini melatih **V5**, adapter LoRA untuk Qwen3.5-4B, dari model dasar di GPU A100 Google Colab. Datanya gabungan:

| Bagian data | Sampel | Token | Isi |
|---|---|---|---|
| `data/train.jsonl` (own) | 125 | ±329 ribu | website one-shot dan perbaikan bug, Python terverifikasi, teknologi, matematika, sains |
| `data/bench-support/humaneval.jsonl` | 164 | ±66 ribu | 164 soal HumanEval dengan solusi yang diverifikasi HumanEval+ |
| **Total V5** | **289** | **±395 ribu** | dilatih bersama dalam satu run, dari model dasar |

Semua hasil disimpan di Google Drive, dan setiap nama model memuat **V5**. Checkpoint disimpan setiap 10 step. Kalau Colab terputus, jalankan Sel 1, 2, dan 3 lagi: training lanjut dari checkpoint terakhir, dan uji yang sudah selesai tidak diulang.

<!-- hanya-md -->
**Buka notebook-nya di Colab:** [notebooks/v5_a100_colab.ipynb](https://colab.research.google.com/github/PvzKing/Dataset/blob/main/notebooks/v5_a100_colab.ipynb). Notebook itu dibangun dari file ini dengan `python scripts/md_to_notebook.py docs/PANDUAN_V5_A100.md notebooks/v5_a100_colab.ipynb`, jadi isinya sama.
<!-- /hanya-md -->

## Gambaran

### Cara singkat

1. Buka notebook di Colab, pilih **Runtime → Change runtime type → A100 GPU** (High-RAM jika ada), lalu **File → Save a copy in Drive**.
2. Jalankan **Sel 1**, lalu periksa semua baris pengecekan bertanda ✅.
3. Jalankan **Sel 2**. Sel ini hanya mendefinisikan langkah-langkahnya, jadi selesai dalam sekejap.
4. Jalankan **Sel 3**. Sel ini menjalankan semua langkah secara berurutan:
   - training V5;
   - uji V5 dan model dasar;
   - pemilihan epoch terbaik;
   - ekspor model;
   - laporan.
   
   Runtime tetap menyala setelah selesai. Matikan sendiri lewat **Runtime → Disconnect and delete runtime**, atau jalankan sel `matikan_runtime()` di Bagian E, supaya compute unit tidak terus terpakai.
5. Baca laporannya di output Sel 3 atau di `MyDrive/finetune-id/V5/laporan-V5.txt`.

Perkiraan total ±2,5–4 jam di A100. Angka ini belum pernah diukur untuk resep V5; ETA di setiap progress bar menunjukkan waktu sebenarnya.

| Langkah | Isi | Perkiraan |
|---|---|---|
| Sel 1 | cek GPU, pasang paket, hubungkan Drive, unduh script dan data, cek data | ±8–12 menit pertama kali, berikutnya <1 menit |
| Training | 289 sampel × 3 epoch, batch efektif 4 = 219 step, lalu 2 website uji | ±25–65 menit, ditambah ±10 menit website uji |
| Uji epoch 3 | MBPP+, IndoPy-dev, Web-eval, HumanEval+; model dasar ikut dijawab sekali | ±60–90 menit |
| Uji epoch 2 | MBPP+, IndoPy-dev, Web-eval; jawaban model dasar dipakai ulang | ±35–50 menit |
| Ekspor | GGUF Q4_K_M (dan model 16-bit jika dipilih) | ±10–20 menit |

### Resep V5 dan alasannya

| Pengaturan | V5 | Alasan |
|---|---|---|
| Titik awal | model dasar `unsloth/Qwen3.5-4B` | Adapter tidak disambung dari adapter lama. Penyambungan seperti itulah yang membuat percobaan bench-lanjut mengacak hasil v3 (lihat [`RENCANA_PYTHON.md`](RENCANA_PYTHON.md)) |
| Data | own + HumanEval dalam **satu** run (`--dataset own+bench`) | Website dan Python dilatih bersama, jadi kemampuan website tidak tergeser oleh data Python |
| Presisi | LoRA 16-bit (bf16) | Cara yang disarankan Unsloth untuk Qwen3.5. A100 mendukung bf16 asli |
| Konteks training | 16.384 token | Sampel terpanjang ±6.200 token, jadi tidak ada yang dibuang |
| LoRA | r 16, alpha 32, semua layer linear bahasa, vision dibekukan | Sama dengan v3 |
| Optimasi | **lr 2e-4** cosine, warmup 10%, **batch efektif 4** (1 × grad-accum 4), seed 42 | Resep yang terbukti berhasil di v3. Lihat penjelasan di bawah |
| **Epoch** | **3, dengan adapter epoch 2 dan 3 disimpan, lalu dipilih yang terbaik dari hasil uji** | Lihat di bawah |
| Checkpoint | setiap 10 step ke Drive, 2 checkpoint terakhir disimpan | Resume otomatis jika Colab terputus |
| Batas jawaban saat uji | 12.000 token | Website panjang tidak terpotong |

**Kenapa lr 2e-4, batch efektif 4, dan 3 epoch.** Resep ini diambil dari run Colab sungguhan sebelumnya (semuanya di T4):

| Run | Resep | Hasil |
|---|---|---|
| v2 | 62 sampel, lr 1e-4, batch efektif 8, 3 epoch (24 update) | format jawaban **tidak** terbentuk; dinilai terlalu lemah |
| v3 | 79 sampel, lr 2e-4, batch efektif 4, 3 epoch (60 update) | format terbentuk; train_loss 0,60 |
| bench-lanjut | v3 + 164 soal HumanEval saja, lr 1e-4, batch 8, 3 epoch | loss turun sampai 0,03–0,06 (menghafal), mutu website turun, dan bagian **Cek kebutuhan** hilang |

- **Lr 2e-4 dengan batch efektif 4 = dosis v3.** Data own V5 lebih banyak dan dicampur HumanEval. Dengan resep v4 (lr 1e-4, batch 8), dosis per sampel untuk data own hanya ±⅓ dari v3, mendekati v2 yang gagal.
- **Hasilnya, epoch 2 kira-kira setara dengan v3,** dan epoch 3 ±1,5 kali lebih kuat.
- **Kenapa epoch 2 tetap diuji:** pada dosis epoch 3, risikonya adalah 164 jawaban HumanEval yang ringkas mulai mendominasi, seperti di bench-lanjut. Karena itu adapter epoch 2 dan epoch 3 sama-sama disimpan dan diuji.
- **Aturan pemilihan:** epoch 2 dipakai sebagai V5 hanya jika rata-ratanya minimal 1 poin lebih tinggi. Rata-rata itu dihitung dari MBPP+, IndoPy-dev, Web-eval, dan kepatuhan format **Cek kebutuhan**.
- **Keputusan diambil dari hasil uji, bukan dari loss.** Loss training menyesatkan untuk data seperti ini (`RENCANA_PYTHON.md`, pelajaran 3), dan loss bench-lanjut yang sangat rendah justru tanda menghafal.

### Peringatan: skor HumanEval V5 tidak bersih

V5 dilatih dengan soal HumanEval beserta jawabannya. Akibatnya **skor HumanEval dan HumanEval+ V5 bukan ukuran kemampuan**: model sudah melihat soalnya. Uji itu tetap dijalankan dan dicantumkan di laporan dengan tanda "terkontaminasi", tetapi tidak dipakai untuk memilih epoch.

Ukuran yang bersih untuk V5:

| Uji | Mengukur | Kenapa bersih |
|---|---|---|
| **MBPP+** (378 soal) | Python umum | tidak ada di data latihan |
| **IndoPy-dev** (20 soal) | Python berbahasa Indonesia, konteks lokal | ditulis terpisah dan diperiksa `decontaminate.py` |
| **Web-eval** (10 website) | website one-shot, dinilai di Chromium | prompt-nya dijaga agar berbeda dari sampel web |
| IndoPy-test (40 soal, opsional) | penilaian akhir | dikunci; jalankan sekali saja |

Setiap uji juga menjawab soal dengan **model dasar**, lalu membandingkannya dengan uji McNemar. `p < 0,05` berarti selisihnya nyata. Kalau `p ≥ 0,05`, selisih itu bisa kebetulan.

### Isi Google Drive setelah selesai

```
MyDrive/finetune-id/V5/
├── qwen3.5-4b-V5/                          folder run
│   ├── qwen3.5-4b-V5-lora/                 ← adapter V5 final (epoch terpilih)
│   ├── epoch-2/qwen3.5-4b-V5-lora/         adapter di akhir epoch 2
│   ├── epoch-3/qwen3.5-4b-V5-lora/         adapter di akhir epoch 3
│   ├── gguf/qwen3.5-4b-V5.Q4_K_M.gguf      ← model V5 siap pakai untuk Ollama / llama.cpp / LM Studio
│   ├── qwen3.5-4b-V5-merged-16bit/         ← model V5 16-bit utuh (hanya jika EKSPOR_16BIT = True)
│   ├── checkpoints/                        checkpoint training untuk resume
│   ├── PILIHAN_EPOCH.txt                   epoch yang dipakai dan alasannya
│   ├── ringkasan-training.json             jumlah sampel, step, loss, lama training
│   └── contoh-*.html / contoh-*.md         2 website yang dibuat V5 setelah training
├── uji/eval-*/                             jawaban dan skor setiap uji (V5 epoch 2, epoch 3, model dasar)
├── log/                                    log lengkap setiap langkah
├── train_own_bench.jsonl                   data gabungan yang dilatih
└── laporan-V5.txt                          ← laporan akhir
```

Siapkan ruang Drive kosong minimal **±8 GB**: adapter, checkpoint, dan GGUF ±3,5 GB, ditambah ruang sementara saat ekspor. Kalau `EKSPOR_16BIT = True`, tambah ±9 GB lagi.

---

## Bagian A. Persiapan sebelum menjalankan sel

1. Buka notebook ini dengan **akun Google yang Drive-nya akan menyimpan hasil**.
2. **File → Save a copy in Drive.** Salinan ini menyimpan output sel, jadi hasilnya tetap bisa dibaca setelah runtime dimatikan.
3. **Runtime → Change runtime type**: pilih **A100 GPU** dan aktifkan **High-RAM** jika ada, lalu **Save**.
4. A100 memakai **compute unit** (Colab Pro atau Pay As You Go). Cek sisanya di **Runtime → View resources** sebelum mulai. Untuk ±3–4 jam A100, siapkan sekitar 50 unit; tarif persisnya terlihat di halaman itu.
5. Biarkan tab browser tetap terbuka selama Sel 3 berjalan. Di Colab Pro biasa, runtime bisa terputus kalau tab ditutup lama. Kalau itu terjadi, cukup ulangi Sel 1, 2, dan 3.

---

## Bagian B. Sel 1: pengaturan dan persiapan

Jalankan **di awal setiap sesi**, termasuk setelah Colab terputus atau Restart session. Pengaturan ada di baris paling atas. Pengaturan bawaannya sudah resep V5, jadi tidak perlu diubah.

```python
# ===== SEL 1: PENGATURAN DAN PERSIAPAN (jalankan di awal setiap sesi) =====
KONTEKS = 16384                 # panjang maksimum satu sampel latihan; ganti ke 12288 hanya jika training kehabisan VRAM
EPOCH = 3                       # resep V5; mengubahnya setelah training dimulai akan mengulang training dari awal
PILIH_EPOCH_TERBAIK = True      # uji juga adapter epoch 2, lalu pakai yang skornya lebih tinggi sebagai V5
SERTAKAN_INDOPY_TEST = False    # set uji akhir yang dikunci (40 soal); True hanya sekali, untuk penilaian akhir
EKSPOR_GGUF = True              # file GGUF Q4_K_M (±2,7 GB) untuk Ollama, llama.cpp, LM Studio
EKSPOR_16BIT = False            # model 16-bit utuh (±9 GB) untuk transformers/vLLM; butuh ruang Drive lebih besar

import codecs, importlib.metadata, importlib.util, json, os, re, shutil, subprocess, sys, time, urllib.request
from pathlib import Path

NAMA, MODEL = "V5", "qwen3.5-4b"
ROOT = Path("/content/drive/MyDrive/finetune-id")
FOLDER = ROOT / NAMA                          # semua hasil V5
RUN = FOLDER / f"{MODEL}-{NAMA}"              # checkpoint, adapter, status.json
LORA = RUN / f"{MODEL}-{NAMA}-lora"           # adapter V5 final
HASIL = FOLDER / "uji"
LOG = FOLDER / "log"
JUMLAH_SAMPEL = 289                           # 125 sampel own + 164 soal HumanEval
CABANG = ["main", "claude/zen-babbage-wyppwh"]  # script diambil dari cabang pertama yang sudah mendukung V5
EVALPLUS = "evalplus @ git+https://github.com/evalplus/evalplus@26d6d00bb1fd0fa37f39c99d5290da67891d1c5e"
OOM = r"CUDA out of memory|OutOfMemoryError"
LATIH = ["--dataset", "own+bench", "--name", NAMA, "--out", str(FOLDER), "--data", "/content/train.jsonl",
         "--no-load-in-4bit", "--max-seq-len", str(KONTEKS), "--epochs", str(EPOCH),
         "--lr", "2e-4", "--grad-accum", "4"]  # sama di semua perintah; dosis per sampel sama dengan v3
WEB = ["--max-seq-len", str(KONTEKS), "--max-new-tokens", "12000"]
UJI_FINAL = [  # (nama, script, folder hasil, argumen tambahan, batch); HumanEval+ terakhir karena terkontaminasi
    ("MBPP+", "eval_humaneval.py", "eval-mbpp", ["--dataset", "mbpp"], 32),
    ("IndoPy-dev", "indopy_eval.py", "eval-indopy-dev", ["--split", "dev"], 16),
    ("Web-eval", "web_eval.py", "eval-web", WEB, 5),
    ("HumanEval+ (terkontaminasi)", "eval_humaneval.py", "eval-humaneval", [], 32),
] + ([("IndoPy-test", "indopy_eval.py", "eval-indopy-test", ["--split", "test"], 16)] if SERTAKAN_INDOPY_TEST else [])
UJI_EPOCH = UJI_FINAL[:3]  # untuk memilih epoch: hanya uji yang bersih


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
    print("memasang Chromium untuk Web-eval (±1–2 menit) ...", flush=True)
    subprocess.run([sys.executable, "-m", "playwright", "install", "--with-deps", "chromium"], check=True,
                   stdout=subprocess.DEVNULL)
importlib.invalidate_caches()
paket = {p: importlib.util.find_spec(p) is not None for p in ("unsloth", "evalplus", "playwright")}
paket["chromium"] = bool(list(Path.home().glob(".cache/ms-playwright/chromium-*")))
cek.append(("Paket", all(paket.values()), ", ".join(f"{p} {'ok' if v else 'GAGAL'}" for p, v in paket.items())))

if not Path("/content/drive/MyDrive").is_dir():
    from google.colab import drive
    drive.mount("/content/drive")
for folder in (FOLDER, HASIL, LOG):
    folder.mkdir(parents=True, exist_ok=True)
try:
    kosong = shutil.disk_usage("/content/drive/MyDrive").free / 1e9
    perlu = 8 + (9 if EKSPOR_16BIT else 0)
    cek.append(("Google Drive", kosong >= perlu, f"{FOLDER}, ruang kosong ±{kosong:.0f} GB (butuh ±{perlu} GB)"))
except OSError:
    cek.append(("Google Drive", True, f"{FOLDER} (ruang kosong tidak terbaca; pastikan ±8 GB tersedia)"))

for REF in CABANG:  # pakai cabang pertama yang script training-nya sudah mengenal --dataset own+bench
    try:
        urllib.request.urlretrieve(f"https://raw.githubusercontent.com/PvzKing/Dataset/{REF}/scripts/train_unsloth.py",
                                   "/content/train_unsloth.py")
    except OSError:
        continue
    if '"own+bench"' in Path("/content/train_unsloth.py").read_text():
        break
else:
    raise SystemExit("Script V5 belum tersedia di GitHub. Kirim pesan ini ke chat.")
for nama, path in [("eval_humaneval.py", "humaneval-bench-script"), ("indopy_eval.py", "eval-suite"),
                   ("web_eval.py", "eval-suite"), ("train.jsonl", "data")]:
    urllib.request.urlretrieve(f"https://raw.githubusercontent.com/PvzKing/Dataset/{REF}/{path}/{nama}", f"/content/{nama}")
cek.append(("Script dan data", True, f"cabang {REF}"))

if (LORA / "adapter_config.json").is_file():
    cek.append(("Data training", True, "training V5 sudah selesai, cek data dilewati"))
else:
    print("memeriksa data training (tokenizer saja, tanpa model) ...", flush=True)
    kode, ekor = jalan(["train_unsloth.py", "prepare", *LATIH], LOG / "cek-data.log")
    data = json.loads((RUN / "status.json").read_text()).get("data") or {} if kode == 0 else {}
    ok = data.get("samples") == JUMLAH_SAMPEL and not data.get("dropped")
    cek.append(("Data training", ok, f"{data.get('samples')} sampel (seharusnya {JUMLAH_SAMPEL}), "
                f"{len(data.get('dropped') or [])} dibuang, terpanjang {data.get('longest')} token, "
                f"{data.get('total_steps')} step" if data else f"cek data gagal (exit code {kode}); lihat error di atas"))

print()
for nama, ok, info in cek:
    print(f"{'✅' if ok else '❌'} {nama:<16} {info}")
print(f"\nResep: {EPOCH} epoch, konteks {KONTEKS}, pilih epoch terbaik {'ya' if PILIH_EPOCH_TERBAIK else 'tidak'}, "
      f"GGUF {'ya' if EKSPOR_GGUF else 'tidak'}, 16-bit {'ya' if EKSPOR_16BIT else 'tidak'}.")
print("Siap. Jalankan Sel 2, lalu Sel 3." if all(ok for _, ok, _ in cek) else
      "Perbaiki yang bertanda ❌ (atau kirim pesannya ke chat), lalu jalankan sel ini lagi.")
```

**Output yang benar** (angka bisa sedikit berbeda):

```
✅ GPU              NVIDIA A100-SXM4-40GB, 40960 MiB
✅ Paket            unsloth ok, evalplus ok, playwright ok, chromium ok
✅ Google Drive     /content/drive/MyDrive/finetune-id/V5, ruang kosong ±80 GB (butuh ±8 GB)
✅ Script dan data  cabang main
✅ Data training    289 sampel (seharusnya 289), 0 dibuang, terpanjang 62xx token, 219 step
```

| Kalau muncul | Artinya | Yang dilakukan |
|---|---|---|
| `AssertionError: GPU sekarang: Tesla T4 ...` | runtime bukan A100 | ulangi Bagian A langkah 3. Resep 16-bit dengan konteks 16.384 tidak muat di T4 |
| `Data training 288 sampel` atau kurang | `train.jsonl` versi lama (124 sampel own atau kurang) | perubahan dataset belum ada di cabang yang dipakai; kirim pesan ini ke chat |
| `chromium GAGAL` | Chromium untuk Web-eval gagal terpasang | jalankan `!playwright install --with-deps chromium` di sel baru, lalu Sel 1 lagi |
| `Google Drive ❌ ... ruang kosong` | Drive hampir penuh | kosongkan Drive, atau set `EKSPOR_16BIT = False` |
| tombol **Restart session** setelah instalasi | paket baru butuh runtime segar | klik tombolnya, lalu jalankan Sel 1 lagi |

---

## Bagian C. Sel 2: definisi langkah

Sel ini hanya mendefinisikan fungsi untuk setiap langkah, tanpa menjalankan apa pun, jadi selesai dalam sekejap. Jalankan setelah Sel 1, termasuk setelah Colab terputus.

```python
# ===== SEL 2: DEFINISI LANGKAH (tidak menjalankan apa-apa) =====
def latih():
    judul(f"1. Training {NAMA}: {EPOCH} epoch, LoRA 16-bit, konteks {KONTEKS}, checkpoint tiap 10 step")
    if (LORA / "adapter_config.json").is_file():
        print(f"sudah selesai: {LORA}")
        return
    kode, ekor = jalan(["train_unsloth.py", "train", *LATIH, "--epoch-adapters", "--max-new-tokens", "12000"],
                       LOG / "latih.log")
    if kode != 0:
        raise SystemExit(f"❌ Training gagal (exit code {kode}). " + (
            "VRAM habis: ganti KONTEKS = 12288 di Sel 1, lalu jalankan Sel 1, 2, dan 3 lagi." if re.search(OOM, ekor)
            else "Jalankan Sel 1, 2, dan 3 lagi untuk melanjutkan dari checkpoint. "
                 f"Kalau gagal lagi, kirim log {LOG / 'latih.log'} ke chat."))
    shutil.copy(RUN / "status.json", RUN / "ringkasan-training.json")  # status.json ditimpa oleh langkah ekspor


def uji(n, daftar):
    adapter = epoch_lora(n)
    assert (adapter / "adapter_config.json").is_file(), f"Adapter epoch {n} belum ada: {adapter}. Jalankan training dulu."
    for i, (nama, script, folder, extra, batch) in enumerate(daftar, 1):
        judul(f"Uji epoch {n} · {i}/{len(daftar)}: {nama}")
        if (HASIL / folder / tag_epoch(n) / "ringkasan.json").is_file():
            print("sudah selesai")
            continue
        while True:  # model dasar ikut dijawab (sekali saja, lalu dipakai ulang) dan dibandingkan dengan McNemar
            kode, ekor = jalan([script, "--adapter", str(adapter), "--results", str(HASIL / folder), "--no-load-in-4bit",
                                "--batch-size", str(batch), *extra], LOG / f"{folder}-epoch{n}.log")
            if kode != 0 and batch > 1 and re.search(OOM, ekor):
                batch //= 2  # jawaban tersimpan per batch, jadi diulang dengan batch lebih kecil tanpa kehilangan hasil
                print(f"\n⚠️ VRAM habis: {nama} diulang dengan batch {batch}", flush=True)
                continue
            break
        if kode != 0:
            raise SystemExit(f"❌ {nama} gagal (exit code {kode}). Jalankan Sel 1, 2, dan 3 lagi untuk melanjutkan. "
                             f"Kalau gagal lagi, kirim log {LOG / (folder + f'-epoch{n}.log')} ke chat.")


def skor(n, folder, kunci):
    f = HASIL / folder / (tag_epoch(n) if n else "model-dasar") / "ringkasan.json"
    return json.loads(f.read_text()).get(kunci) if f.is_file() else None


BERSIH = [("MBPP+", "eval-mbpp", "mbpp+_pass@1"), ("IndoPy-dev", "eval-indopy-dev", "indopy_pass@1"),
          ("Web-eval", "eval-web", "web_lolos")]


def pilih_epoch():
    judul("Memilih epoch untuk V5")
    catatan = RUN / "PILIHAN_EPOCH.txt"
    if catatan.is_file():
        print(catatan.read_text())
        return
    pilihan, alasan = EPOCH, "epoch terakhir (PILIH_EPOCH_TERBAIK = False)"
    if PILIH_EPOCH_TERBAIK and EPOCH >= 2:
        rata = {}
        for n in (EPOCH - 1, EPOCH):
            nilai = [skor(n, folder, kunci) for _, folder, kunci in BERSIH]
            web = HASIL / "eval-web" / tag_epoch(n) / "ringkasan.json"
            if None in nilai or not web.is_file():
                raise SystemExit(f"Uji epoch {n} belum lengkap. Jalankan uji({n}, UJI_EPOCH) dulu.")
            web = json.loads(web.read_text())
            nilai.append(web["format_cek_kebutuhan"] / web["soal"])  # format yang hilang di percobaan bench-lanjut
            rata[n] = sum(nilai) / len(nilai)
        if rata[EPOCH - 1] >= rata[EPOCH] + 0.01:  # epoch lebih awal hanya dipilih jika unggul minimal 1 poin
            pilihan = EPOCH - 1
        alasan = (f"rata-rata MBPP+, IndoPy-dev, Web-eval, dan format Cek kebutuhan: epoch {EPOCH - 1} "
                  f"{rata[EPOCH - 1]:.1%}, epoch {EPOCH} {rata[EPOCH]:.1%}")
    if pilihan != EPOCH:
        shutil.rmtree(LORA)
        shutil.copytree(epoch_lora(pilihan), LORA)
    teks = f"{NAMA} memakai adapter epoch {pilihan} ({LORA}).\nAlasan: {alasan}."
    catatan.write_text(teks + "\n", encoding="utf-8")
    print(teks)


def ekspor():
    assert (RUN / "PILIHAN_EPOCH.txt").is_file(), "Pilih epoch dulu, supaya yang diekspor adalah adapter final."
    langkah = [("GGUF Q4_K_M", "gguf", EKSPOR_GGUF, lambda: list((RUN / "gguf").glob(f"*{NAMA}*.gguf"))),
               ("model 16-bit", "merge", EKSPOR_16BIT, lambda: (RUN / f"{MODEL}-{NAMA}-merged-16bit" / "config.json").is_file())]
    for nama, perintah, aktif, sudah in langkah:
        if not aktif:
            continue
        judul(f"Ekspor {nama}")
        if sudah():
            print("sudah selesai")
            continue
        kode, _ = jalan(["train_unsloth.py", perintah, *LATIH], LOG / f"{perintah}.log")
        if kode != 0:
            raise SystemExit(f"❌ Ekspor {nama} gagal (exit code {kode}). Adapter V5 aman di {LORA}. "
                             f"Kirim log {LOG / (perintah + '.log')} ke chat.")


def laporan():
    judul("Laporan V5 (salin semua teks di bawah ke chat)")
    pilih = (RUN / "PILIHAN_EPOCH.txt").read_text().strip() if (RUN / "PILIHAN_EPOCH.txt").is_file() else "belum dipilih"
    epochs = [n for n in (EPOCH - 1, EPOCH) if n >= 1 and (HASIL / "eval-mbpp" / tag_epoch(n)).is_dir()]
    kolom = ["model dasar"] + [f"V5 epoch {n}" for n in epochs]
    baris = [f"V5: own + HumanEval ({JUMLAH_SAMPEL} sampel), LoRA 16-bit dari model dasar, {EPOCH} epoch, konteks "
             f"{KONTEKS}, uji 16-bit di A100, greedy pass@1.", pilih, "",
             f"{'uji':<28}" + "".join(f"{k:>14}" for k in kolom)]
    daftar = BERSIH + [("HumanEval+ (terkontaminasi)", "eval-humaneval", "humaneval+_pass@1")]
    if SERTAKAN_INDOPY_TEST:
        daftar.append(("IndoPy-test", "eval-indopy-test", "indopy_pass@1"))
    for nama, folder, kunci in daftar:
        nilai = [skor(n, folder, kunci) for n in [None] + epochs]
        baris.append(f"{nama:<28}" + "".join(f"{'-' if v is None else f'{v:.1%}':>14}" for v in nilai))
    baris.append("\nPerbandingan dengan model dasar (McNemar; p < 0,05 berarti nyata):")
    for n in epochs:
        for nama, folder, _ in daftar:
            f = HASIL / folder / f"perbandingan-{tag_epoch(n)}.json"
            if not f.is_file():
                continue
            for uji_, r in json.loads(f.read_text()).items():
                if isinstance(r, dict) and "p_mcnemar" in r:
                    baris.append(f"  epoch {n} · {uji_:<12} selisih {r['selisih_soal']:+d} soal "
                                 f"({r['selisih_poin_persen']:+.1f} poin), p = {r['p_mcnemar']:.3f}"
                                 + ("  [terkontaminasi]" if "humaneval" in folder else ""))
    for n in epochs:
        f = HASIL / "eval-web" / tag_epoch(n) / "ringkasan.json"
        if f.is_file():
            r = json.loads(f.read_text())
            baris.append(f"\nWeb-eval epoch {n}: format Cek kebutuhan {r['format_cek_kebutuhan']}/{r['soal']}")
            baris += [f"   gagal {k.rsplit('/', 1)[-1]}: {alasan[:150]}" for k, alasan in r["gagal"].items()]
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
    model = [str(LORA)] + [str(f) for f in sorted((RUN / "gguf").glob("*.gguf"))]
    if (RUN / f"{MODEL}-{NAMA}-merged-16bit").is_dir():
        model.append(str(RUN / f"{MODEL}-{NAMA}-merged-16bit"))
    baris += ["\n=== Model V5 di Drive ==="] + [f"  {m}" for m in model]
    if SERTAKAN_INDOPY_TEST:
        baris.append("Catatan: IndoPy-test dikunci. Kirim skornya saja, jangan soal atau jawaban yang gagal.")
    teks = "\n".join(baris)
    (FOLDER / "laporan-V5.txt").write_text(teks + "\n", encoding="utf-8")
    print(teks)
    print(f"\nLaporan juga disimpan di {FOLDER / 'laporan-V5.txt'}")


def matikan_runtime():
    """Putuskan dan hapus runtime supaya compute unit berhenti terpakai. Output sel tetap tersimpan di notebook."""
    print("\nMenyimpan Drive, lalu mematikan runtime dalam 30 detik ...", flush=True)
    from google.colab import drive, runtime
    time.sleep(30)  # beri waktu output terakhir tampil dan tersimpan di notebook
    drive.flush_and_unmount()
    runtime.unassign()


def jalankan_semua():
    latih()
    uji(EPOCH, UJI_FINAL)
    if PILIH_EPOCH_TERBAIK and EPOCH >= 2:
        uji(EPOCH - 1, UJI_EPOCH)
    pilih_epoch()
    ekspor()
    laporan()


print("Langkah siap. Jalankan Sel 3 untuk menjalankan semuanya, atau sel di Bagian E untuk satu langkah.")
```

## Bagian D. Sel 3: jalankan semua

Sel ini menjalankan semua langkah yang belum selesai, berurutan. Langkah yang sudah selesai dilewati, jadi aman dijalankan ulang kapan pun. Runtime tetap menyala setelah selesai atau gagal, jadi output dan error bisa langsung diperiksa. Setelah selesai, matikan runtime sendiri supaya compute unit tidak terus terpakai (lihat Bagian E).

```python
# ===== SEL 3: JALANKAN SEMUA (training, uji, pilih epoch, ekspor, laporan) =====
jalankan_semua()
```

**Yang muncul berurutan:**

| Bagian | Baris penting | Arti |
|---|---|---|
| 1. Training | `folder hasil: .../finetune-id/V5/qwen3.5-4b-V5` | folder V5 |
| | banner Unsloth memuat `A100` dan `Bfloat16 = TRUE` | training 16-bit di A100 |
| | `data valid: 289 sampel` dan `289 sampel dipakai, 0 dibuang` | semua data ikut |
| | `cek masking: ... token sampel pertama ikut dilatih` | hanya jawaban asisten yang dilatih |
| | `[status] training: mulai dari awal` atau `mulai dari .../checkpoint-60` | baris kedua berarti melanjutkan dari checkpoint |
| | progress bar sampai `213/213`, dengan `adapter epoch 1/2/3 disimpan` di akhir tiap epoch | training berjalan |
| | dua website uji mengalir di layar, lalu `[status] done` | adapter V5 sudah ada di Drive |
| Uji | `[qwen3.5-4b-V5-epoch-3] 64/378 soal ...`, lalu `model-dasar`, lalu tabel perbandingan | uji berjalan; model dasar hanya dijawab sekali |
| Pilih epoch | `V5 memakai adapter epoch 3 ...` beserta alasannya | adapter final sudah ditentukan |
| Ekspor | log llama.cpp yang panjang, lalu `[status] done: GGUF tersimpan` | file `qwen3.5-4b-V5.Q4_K_M.gguf` sudah ada |
| Laporan | tabel skor model dasar, V5 epoch 2, dan V5 epoch 3 | salin ke chat |
| Jika gagal | pesan `❌ ...` di akhir output, beserta lokasi log-nya | perbaiki sesuai pesan (Bagian F), lalu jalankan Sel 1, 2, dan 3 lagi. Langkah yang sudah selesai tidak diulang |

**Contoh bentuk laporan.** Angka di bawah hanya contoh tampilan, bukan hasil model:

```
uji                            model dasar    V5 epoch 2    V5 epoch 3
MBPP+                                 x,x%          x,x%          x,x%
IndoPy-dev                            x,x%          x,x%          x,x%
Web-eval                              x,x%          x,x%          x,x%
HumanEval+ (terkontaminasi)           x,x%             -          x,x%
```

---

## Bagian E. Langkah satu per satu (opsional)

Pakai sel-sel ini sebagai pengganti Sel 3, misalnya untuk menjalankan ulang satu langkah. Jalankan Sel 1 dan Sel 2 dulu. Sel `matikan_runtime()` di bawah menyimpan Drive lalu memutus runtime, jadi compute unit berhenti terpakai dan output sel tetap terlihat.

```python
latih()                     # training V5 (lanjut dari checkpoint jika ada)
```

```python
uji(EPOCH, UJI_FINAL)       # uji adapter epoch terakhir + model dasar
```

```python
uji(EPOCH - 1, UJI_EPOCH)   # uji adapter epoch 2 (jawaban model dasar dipakai ulang)
```

```python
pilih_epoch()               # tentukan adapter V5 final
ekspor()                    # GGUF (dan 16-bit jika dipilih)
laporan()
```

```python
matikan_runtime()           # matikan runtime sekarang; output sel tetap ada
```

**Cek progres setelah Colab terputus**, tanpa memuat model. Jalankan setelah Sel 1 dan Sel 2:

```python
for nama, ada in [("Training", (LORA / "adapter_config.json").is_file()),
                  *[(f"Uji epoch {EPOCH} {n}", (HASIL / f / tag_epoch(EPOCH) / "ringkasan.json").is_file()) for n, _, f, _, _ in UJI_FINAL],
                  *[(f"Uji epoch {EPOCH - 1} {n}", (HASIL / f / tag_epoch(EPOCH - 1) / "ringkasan.json").is_file()) for n, _, f, _, _ in UJI_EPOCH],
                  ("Pilih epoch", (RUN / "PILIHAN_EPOCH.txt").is_file()),
                  ("GGUF", bool(list((RUN / "gguf").glob("*.gguf")))),
                  ("Laporan", (FOLDER / "laporan-V5.txt").is_file())]:
    print(f"{'✅' if ada else '⬜'} {nama}")
if (RUN / "status.json").is_file():
    st = json.loads((RUN / "status.json").read_text())
    print("\nstatus terakhir:", {k: st.get(k) for k in ("stage", "message", "step", "max_steps", "loss", "eta_min")})
```

---

## Bagian F. Kalau ada masalah

| Gejala | Penyebab | Yang dilakukan |
|---|---|---|
| Colab terputus, atau runtime mati di tengah jalan | sesi habis, tab ditutup, atau A100 diambil kembali | jalankan Sel 1, 2, dan 3 lagi. Training lanjut dari checkpoint terakhir (maksimal 10 step terulang), dan uji yang selesai dilewati |
| `CUDA out of memory` saat training | VRAM A100 40 GB tidak cukup | ganti `KONTEKS = 12288` di Sel 1, lalu jalankan Sel 1, 2, dan 3. Checkpoint lama otomatis dipindah ke `arsip/` dan training mulai dari awal |
| `CUDA out of memory` saat uji | batch terlalu besar | tidak perlu apa-apa: batch diturunkan otomatis dan uji diulang tanpa kehilangan jawaban |
| `data atau pengaturan berubah: hasil lama dipindah ke ...arsip...` | `EPOCH`, `KONTEKS`, atau data berubah sejak checkpoint dibuat | wajar jika memang sengaja diubah. Kalau tidak, kembalikan pengaturannya dan pindahkan isi `arsip/` kembali |
| loss `nan` | versi Unsloth bermasalah | `!pip install --upgrade --force-reinstall unsloth`, Restart session, lalu Sel 1, 2, dan 3 |
| Uji berjalan sangat lambat (puluhan token/detik) | paket `causal_conv1d` untuk lapisan Gated DeltaNet Qwen3.5 belum terpasang | opsional: `!pip install causal-conv1d --no-build-isolation` (kompilasi ±10–20 menit), Restart session, lalu Sel 1–3. Hasil tidak berubah, hanya lebih cepat |
| Sel 1 memakai cabang `claude/...` padahal PR sudah di-merge | GitHub raw kadang menyajikan file lama sampai ±5 menit setelah merge | tidak masalah: isinya sama. Kalau ingin `main`, tunggu beberapa menit lalu jalankan Sel 1 lagi |
| Ekspor GGUF gagal | kompilasi llama.cpp gagal atau Drive penuh | adapter V5 tetap aman. Kirim `log/gguf.log` ke chat. Adapter tetap bisa dipakai langsung (Bagian G) |
| Ingin melatih ulang V5 dari nol | | hapus folder `MyDrive/finetune-id/V5/qwen3.5-4b-V5` di Drive, lalu jalankan Sel 1, 2, dan 3 |
| Ingin memilih epoch secara manual | | hapus `PILIHAN_EPOCH.txt`, salin `epoch-N/qwen3.5-4b-V5-lora` menggantikan `qwen3.5-4b-V5-lora`, tulis `PILIHAN_EPOCH.txt` sendiri, hapus folder `gguf/`, lalu jalankan `ekspor()` |

---

## Bagian G. Memakai model V5

**Chat di Colab dengan tampilan Gradio** (GPU apa pun, termasuk T4 dengan `--load-in-4bit`):

```python
!wget -q -O /content/chat_gradio.py https://raw.githubusercontent.com/PvzKing/Dataset/main/scripts/chat_gradio.py
%run /content/chat_gradio.py --adapter /content/drive/MyDrive/finetune-id/V5/qwen3.5-4b-V5/qwen3.5-4b-V5-lora
```

**Di komputer sendiri dengan Ollama.** Unduh `qwen3.5-4b-V5.Q4_K_M.gguf` dari Drive, lalu buat file `Modelfile` di folder yang sama:

```
FROM ./qwen3.5-4b-V5.Q4_K_M.gguf
PARAMETER temperature 0.7
PARAMETER top_p 0.8
PARAMETER top_k 20
```

Lalu jalankan `ollama create qwen3.5-4b-V5 -f Modelfile` dan `ollama run qwen3.5-4b-V5`. Kalau Ollama tidak mengenali chat template model ini, pakai LM Studio atau `llama-server` dari llama.cpp, yang membaca template dari file GGUF.

Pengaturan sampling di atas sama dengan yang dipakai untuk membuat website uji setelah training.

---

## Catatan hukum

- **Lisensi model dasar.** Qwen3.5-4B dirilis dengan Apache License 2.0; pastikan lagi di model card saat membagikan. Jika adapter, GGUF, atau model 16-bit V5 dibagikan, Pasal 4 lisensi itu mewajibkan:
  - salinan lisensi ikut disertakan;
  - pemberitahuan bahwa file sudah diubah (fine-tuning);
  - pemberitahuan hak cipta dan atribusi karya asal dipertahankan.
- **Data HumanEval.** V5 memuat turunan dua karya:
  - HumanEval (OpenAI), berlisensi MIT;
  - HumanEval+ (EvalPlus), berlisensi Apache 2.0.
  
  Kalau data `train_own_bench.jsonl` dibagikan, sertakan kedua teks lisensinya dari `data/bench-support/`. Lisensi MIT mewajibkan pemberitahuan hak cipta dan izinnya disertakan pada setiap salinan atau bagian substansial. Untuk bobot model, kewajiban itu umumnya dianggap tidak melekat, tetapi menyebutkan sumber data di model card adalah praktik yang aman.
- **Klaim mutu.** Kalau V5 ditawarkan sebagai produk atau jasa:
  - jangan memakai skor HumanEval atau HumanEval+ V5 sebagai bukti kemampuan, karena model sudah melihat soalnya;
  - pakai MBPP+, IndoPy, dan Web-eval, sebutkan kondisi ujinya (greedy, pass@1, EvalPlus commit `26d6d00`, 16-bit di A100), dan sebut IndoPy serta Web-eval sebagai uji buatan sendiri;
  - klaim "lebih baik" hanya untuk selisih yang nyata menurut McNemar (`p < 0,05`).
  
  Klaim yang tidak sesuai kenyataan berisiko melanggar Pasal 9 ayat (1) dan Pasal 10 UU No. 8 Tahun 1999 tentang Perlindungan Konsumen.
- **Data pribadi.** Dataset ini tidak berisi data pribadi orang sungguhan; nama, alamat, dan nomor di sampel web adalah contoh. Kalau nanti ditambah sampel dari pekerjaan nyata, hapus atau samarkan data pribadinya dulu sesuai UU No. 27 Tahun 2022 tentang Pelindungan Data Pribadi.
