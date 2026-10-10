"""Fine-tuning LoRA Qwen3.5-4B dengan Unsloth dalam satu file: data, training, uji coba, dan ekspor GGUF.

Script ini mandiri: tidak butuh clone repo. Jika train.jsonl tidak ditemukan, file diunduh dari repo GitHub publik.
Cara memakai di Google Colab (pilih GPU di Runtime → Change runtime type):

    Sel 1:  !pip install --upgrade unsloth
    Sel 2:  tempel seluruh isi file ini, ubah CONFIG jika perlu, lalu jalankan. Drive di-mount otomatis, lalu
            training, penyimpanan adapter, dan pembuatan website uji berjalan berurutan. Untuk menjalankan tahap lain
            (misalnya uji ulang atau ekspor GGUF), ganti CONFIG["command"] lalu jalankan sel itu lagi.

Atau simpan sebagai file (sel diawali `%%writefile /content/train_unsloth.py`) lalu jalankan dari terminal/sel:

    python train_unsloth.py info       # tampilkan konfigurasi dan lokasi hasil
    python train_unsloth.py prepare    # cek data tanpa GPU
    python train_unsloth.py train      # training + simpan adapter + website uji (bawaan, lihat CONFIG["command"])
    python train_unsloth.py test       # uji ulang adapter yang sudah tersimpan
    python train_unsloth.py gguf       # ekspor GGUF q4_k_m untuk Ollama / llama.cpp
    Opsi CONFIG bisa diganti lewat argumen, misalnya: --dataset mix --load-in-4bit --max-seq-len 6144

Semua hasil ditulis ke <out>/<model>-<dataset>/:
    status.json      tahap yang sedang berjalan, step, loss, ETA, atau pesan error (dibaca untuk memantau)
    checkpoints/     checkpoint training; dilanjutkan dari yang terakhir jika data dan pengaturan masih sama
    arsip/           hasil training lama yang dipindahkan karena data atau pengaturan berubah
    lora-adapter/    adapter LoRA hasil training
    contoh-*.html    website yang dibuat model dari prompt uji (contoh-*.md berisi jawaban lengkapnya)
    gguf/            hasil ekspor GGUF (opsional)
"""
import argparse
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
import traceback
import urllib.request
from pathlib import Path

# Kurangi fragmentasi memori GPU; harus diset sebelum torch di-import.
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")

# ======================================================== CONFIG: ubah di sini ========================================
CONFIG = {
    "command": "train",             # dipakai jika tidak ada argumen: "train", "prepare", "test", "gguf", atau "info"
    "model": "qwen3.5-4b",          # "qwen3.5-4b" atau "qwen2.5-coder-7b" (pembanding)
    "dataset": "own",               # "own" = data/train.jsonl (disarankan), "mix" = ditambah dataset umum
    "out": "/content/drive/MyDrive/finetune-id",  # folder hasil; di Google Drive supaya aman saat sesi putus
    "data": None,                   # path train.jsonl; None = cari otomatis lalu unduh dari GitHub jika tidak ada
    "mix_args": "",                 # argumen tambahan mix_general.py, misalnya "--code 0 --chat 0" (hanya Aya)
    "load_in_4bit": None,           # None = otomatis: 4-bit di GPU kecil tanpa bf16 (T4), selain itu bawaan model.
                                    # True = QLoRA 4-bit (hemat ±6 GB VRAM, akurasi Qwen3.5 sedikit turun)
    "max_seq_len": None,            # None = otomatis: 6144 di T4, 8192 di GPU lain. Sampel lebih panjang DIBUANG
    "epochs": None,                 # None = 3 untuk own, 2 untuk mix
    "lr": 1e-4,
    "lora_r": 16,
    "lora_alpha": 32,
    "batch_size": 1,
    "grad_accum": 8,                # batch efektif = batch_size × grad_accum
    "save_steps": 10,               # checkpoint setiap N step
    "max_new_tokens": 6000,         # batas panjang jawaban saat uji
    "no_test": False,               # True = lewati pembuatan website uji setelah training
    "seed": 42,
}
# ======================================================================================================================

REPO_RAW = "https://raw.githubusercontent.com/PvzKing/Dataset/main"
EOS = "<|im_end|>"
IN_NOTEBOOK = "ipykernel" in sys.modules  # True jika file ini ditempel langsung ke sel Colab/Jupyter
HERE = Path(__file__).resolve().parent if "__file__" in globals() else Path.cwd()

MODELS = {
    # Salinan Unsloth dari Qwen/Qwen3.5-4B. LoRA 16-bit, karena Unsloth tidak menyarankan QLoRA 4-bit untuk Qwen3.5.
    # Di GPU tanpa bf16 (T4), Unsloth otomatis melatih Qwen3.5 dalam float32 karena fp16 menghasilkan NaN.
    "qwen3.5-4b": {
        "name": "unsloth/Qwen3.5-4B",
        "tokenizer": "Qwen/Qwen3.5-4B",
        "load_in_4bit": False,
        "template_kwargs": {"enable_thinking": False},
    },
    # Pembanding: Qwen/Qwen2.5-Coder-7B-Instruct yang sudah dikuantisasi 4-bit (QLoRA), supaya muat di T4.
    "qwen2.5-coder-7b": {
        "name": "unsloth/Qwen2.5-Coder-7B-Instruct-bnb-4bit",
        "tokenizer": "Qwen/Qwen2.5-Coder-7B-Instruct",
        "load_in_4bit": True,
        "template_kwargs": {},
    },
}

TEST_PROMPTS = {
    "bengkel": "Buatkan landing page satu file HTML untuk bengkel motor \"Gaspol Motor\" di Yogyakarta: hero dengan "
               "tombol booking servis, daftar layanan dan harga, testimoni, jam buka, dan form booking dengan validasi. "
               "Responsif dan tanpa library eksternal.",
    "absensi": "Buat aplikasi absensi kelas dalam satu file HTML: tambah siswa, tandai hadir/izin/sakit/alfa per tanggal, "
               "rekap persentase kehadiran, simpan di localStorage, dan tombol ekspor CSV.",
}


# ---------------------------------------------------------------- status

class Status:
    """Tulis kondisi terkini ke status.json supaya proses yang berjalan di latar belakang mudah dipantau."""

    def __init__(self, path):
        self.path = Path(path)
        self.data = {}

    def update(self, **fields):
        self.data.update(fields, updated=time.strftime("%Y-%m-%d %H:%M:%S"))
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.data, ensure_ascii=False, indent=1), encoding="utf-8")
        tmp.replace(self.path)
        print(f"[status] {self.data.get('stage')}: {self.data.get('message', '')}", flush=True)


# ---------------------------------------------------------------- data

def ensure_drive(out):
    """Pastikan Google Drive ter-mount jika folder hasil ada di Drive."""
    if not str(out).startswith("/content/drive") or os.path.isdir("/content/drive/MyDrive"):
        return
    if IN_NOTEBOOK:
        from google.colab import drive
        drive.mount("/content/drive")
    else:
        raise RuntimeError("Google Drive belum ter-mount: jalankan `from google.colab import drive; "
                           "drive.mount('/content/drive')` di sel notebook, lalu ulangi")


def download(url, dest):
    print(f"mengunduh {url}", flush=True)
    dest = Path(dest)
    tmp = dest.with_suffix(dest.suffix + ".part")
    urllib.request.urlretrieve(url, tmp)
    tmp.replace(dest)
    return dest


def find_own_data(args):
    """Cari train.jsonl: --data, folder script/repo, folder kerja; jika tidak ada, unduh versi terbaru dari GitHub."""
    candidates = [args.data] if args.data else []
    candidates += [HERE / "train.jsonl", HERE.parent / "data/train.jsonl", Path.cwd() / "train.jsonl",
                   Path.cwd() / "data/train.jsonl"]
    for path in candidates:
        if path and Path(path).is_file():
            return Path(path)
    if args.data:
        raise FileNotFoundError(f"file data tidak ditemukan: {args.data}")
    # Selalu unduh ulang supaya perubahan dataset di GitHub ikut terpakai; salinan lama hanya dipakai jika offline.
    cached = Path(args.out) / "train.jsonl"
    try:
        return download(f"{REPO_RAW}/data/train.jsonl", cached)
    except OSError as e:
        if not cached.is_file():
            raise
        print(f"unduhan gagal ({e}), memakai salinan lama {cached}", flush=True)
        return cached


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def data_file_for(args):
    own = find_own_data(args)
    if args.dataset == "own":
        return own
    # Data campuran disimpan di folder hasil supaya sesi berikutnya memakai file yang sama persis (penting untuk resume),
    # dan dibuat ulang otomatis jika data own, mix_args, atau seed berubah.
    mix = Path(args.out) / "train_mix.jsonl"
    source = Path(args.out) / "train_mix.source"
    key = f"{sha256_file(own)} {args.mix_args} {args.seed}"
    if not mix.exists() or not source.exists() or source.read_text().strip() != key:
        mixer = HERE / "mix_general.py"
        if not mixer.exists():
            mixer = download(f"{REPO_RAW}/scripts/mix_general.py", Path(args.out) / "mix_general.py")
        print("membuat data campuran ...", flush=True)
        subprocess.run([sys.executable, str(mixer), "--input", str(own), "--output", str(mix),
                        "--seed", str(args.seed), *args.mix_args.split()], check=True)
        source.write_text(key)
    return mix


def load_rows(data_file):
    """Baca JSONL dan periksa strukturnya: (system) lalu user/assistant bergantian, diakhiri assistant."""
    rows, errors, ids = [], [], set()
    for no, line in enumerate(open(data_file, encoding="utf-8"), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as e:
            errors.append(f"baris {no}: JSON tidak valid ({e})")
            continue
        rid, messages = row.get("id", f"baris-{no}"), row.get("messages")
        if rid in ids:
            errors.append(f"{rid}: id duplikat")
        ids.add(rid)
        if not isinstance(messages, list) or not messages:
            errors.append(f"{rid}: 'messages' kosong atau bukan list")
            continue
        turns = messages[1:] if messages[0].get("role") == "system" else messages
        roles = [m.get("role") for m in turns]
        if not turns or roles != ["user", "assistant"] * (len(turns) // 2) or len(turns) % 2:
            errors.append(f"{rid}: urutan role harus user/assistant bergantian dan diakhiri assistant")
        if any(not isinstance(m.get("content"), str) or not m["content"].strip() for m in messages):
            errors.append(f"{rid}: ada content yang kosong")
        rows.append(row)
    if errors:
        raise ValueError(f"{len(errors)} masalah di {data_file}:\n  " + "\n  ".join(errors[:20]))
    print(f"data valid: {len(rows)} sampel dari {data_file}", flush=True)
    return rows


def unwrap_tokenizer(tokenizer):
    """Model multimodal bisa mengembalikan processor; training teks cukup memakai tokenizer di dalamnya."""
    if hasattr(tokenizer, "tokenizer"):
        processor, tokenizer = tokenizer, tokenizer.tokenizer
        if not getattr(tokenizer, "chat_template", None):
            tokenizer.chat_template = processor.chat_template
    return tokenizer


def render(tokenizer, template_kwargs, messages, **kw):
    return tokenizer.apply_chat_template(messages, tokenize=False, **template_kwargs, **kw)


def to_text(tokenizer, template_kwargs, messages):
    """Jawaban terakhir ditempel tepat setelah prompt inferensi, jadi format training sama dengan saat dipakai
    (termasuk blok <think> kosong pada mode non-thinking Qwen3.5)."""
    *history, last = messages
    return render(tokenizer, template_kwargs, history, add_generation_prompt=True) + last["content"] + EOS


def build_texts(tokenizer, template_kwargs, rows, max_seq_len):
    """Kembalikan (texts, lengths, dropped). Sampel yang lebih panjang dari max_seq_len dibuang, tidak dipotong."""
    texts, lengths, dropped = [], [], []
    for row in rows:
        text = to_text(tokenizer, template_kwargs, row["messages"])
        n = len(tokenizer(text, add_special_tokens=False)["input_ids"])
        if n > max_seq_len:
            dropped.append((row["id"], n))
            continue
        texts.append(text)
        lengths.append(n)
    if not texts:
        raise ValueError(f"semua sampel lebih panjang dari max_seq_len={max_seq_len}")
    return texts, lengths, dropped


def summarize(texts, lengths, dropped, args, bf16):
    total_steps = math.ceil(len(texts) / (args.batch_size * args.grad_accum)) * args.epochs
    trained_tokens = sum(lengths) * args.epochs
    lo, hi = (300, 900) if bf16 else (60, 200)  # token/detik, perkiraan kasar (T4 tanpa bf16 jauh lebih lambat)
    summary = {
        "samples": len(texts),
        "dropped": dropped,
        "tokens_per_epoch": sum(lengths),
        "longest": max(lengths),
        "epochs": args.epochs,
        "total_steps": total_steps,
        "trained_tokens": trained_tokens,
        "estimate_min": [round(trained_tokens / hi / 60), round(trained_tokens / lo / 60)],
    }
    print(f"{len(texts)} sampel dipakai, {len(dropped)} dibuang karena > {args.max_seq_len} token {dropped[:5]}")
    print(f"token per epoch: {sum(lengths):,} | terpanjang: {max(lengths):,} | rata-rata: {sum(lengths) // len(lengths):,}")
    print(f"{args.epochs:g} epoch = {total_steps} step, ±{trained_tokens:,} token dilatih")
    print(f"perkiraan waktu ({lo}–{hi} token/detik): {summary['estimate_min'][0]}–{summary['estimate_min'][1]} menit")
    print("\ncontoh awal teks training:\n" + texts[0][:400] + "\n", flush=True)
    return summary


# ---------------------------------------------------------------- model

def load_model(cfg, args, model_name=None):
    from unsloth import FastLanguageModel

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=model_name or cfg["name"],
        max_seq_length=args.max_seq_len,
        dtype=None,
        load_in_4bit=args.load_in_4bit,
        load_in_16bit=not args.load_in_4bit,
    )
    return model, unwrap_tokenizer(tokenizer)


def generate_tests(model, tokenizer, cfg, run_dir, max_new_tokens):
    from transformers import TextStreamer
    from unsloth import FastLanguageModel

    FastLanguageModel.for_inference(model)
    results = {}
    for key, prompt in TEST_PROMPTS.items():
        text = render(tokenizer, cfg["template_kwargs"], [{"role": "user", "content": prompt}], add_generation_prompt=True)
        inputs = tokenizer(text, return_tensors="pt", add_special_tokens=False).to("cuda")
        start = time.time()
        output = model.generate(
            **inputs, max_new_tokens=max_new_tokens, temperature=0.7, top_p=0.8, top_k=20, repetition_penalty=1.05,
            streamer=TextStreamer(tokenizer, skip_prompt=True),
        )
        new_tokens = output[0][inputs["input_ids"].shape[1]:]
        answer = tokenizer.decode(new_tokens, skip_special_tokens=True)
        (run_dir / f"contoh-{key}.md").write_text(answer, encoding="utf-8")
        has_html = "```html" in answer
        if has_html:
            page = answer.split("```html", 1)[1].split("```", 1)[0]
            (run_dir / f"contoh-{key}.html").write_text(page, encoding="utf-8")
        results[key] = {"tokens": len(new_tokens), "seconds": round(time.time() - start), "html": has_html,
                        "finished": len(new_tokens) < max_new_tokens}
        print(f"\n[{key}] {results[key]}", flush=True)
    return results


# ---------------------------------------------------------------- resume

# Pengaturan yang menentukan hasil training; checkpoint hanya dilanjutkan jika semuanya sama.
TRAINING_KEYS = ["model", "dataset", "mix_args", "load_in_4bit", "max_seq_len", "epochs", "lr", "lora_r", "lora_alpha",
                 "batch_size", "grad_accum", "seed"]


def archive_stale_run(run_dir, ckpt_dir, fingerprint):
    """Jika checkpoint lama berasal dari data atau pengaturan lain, pindahkan hasil lama ke arsip/ supaya training
    dimulai dari awal (melanjutkannya akan diam-diam memakai bobot lama)."""
    fp_file = ckpt_dir / "fingerprint.json"
    if not ckpt_dir.exists() or (fp_file.exists() and fp_file.read_text() == fingerprint):
        return
    old = [p for p in run_dir.iterdir() if p.name in ("checkpoints", "lora-adapter", "gguf") or p.name.startswith("contoh-")]
    if not old:
        return
    dest = run_dir / "arsip" / time.strftime("%Y%m%d-%H%M%S")
    dest.mkdir(parents=True)
    for p in old:
        shutil.move(str(p), str(dest / p.name))
    print(f"data atau pengaturan berubah: hasil lama dipindah ke {dest}, training dimulai dari awal", flush=True)


# ---------------------------------------------------------------- commands

def cmd_prepare(args, cfg, status, run_dir):
    from transformers import AutoTokenizer

    rows = load_rows(data_file_for(args))
    tokenizer = unwrap_tokenizer(AutoTokenizer.from_pretrained(cfg["tokenizer"]))
    texts, lengths, dropped = build_texts(tokenizer, cfg["template_kwargs"], rows, args.max_seq_len)
    try:
        import torch
        bf16 = torch.cuda.is_available() and torch.cuda.is_bf16_supported()
    except ImportError:
        bf16 = False
    summary = summarize(texts, lengths, dropped, args, bf16)
    status.update(stage="prepared", message="data siap, belum training", data=summary)


def cmd_train(args, cfg, status, run_dir):
    status.update(stage="loading", message=f"memuat {cfg['name']}")
    data_file = data_file_for(args)
    rows = load_rows(data_file)

    from unsloth import FastLanguageModel, is_bfloat16_supported  # harus di-import sebelum trl/transformers
    from datasets import Dataset
    from transformers import TrainerCallback
    from transformers.trainer_utils import get_last_checkpoint
    from trl import SFTConfig, SFTTrainer
    from unsloth.chat_templates import train_on_responses_only

    model, tokenizer = load_model(cfg, args)
    model = FastLanguageModel.get_peft_model(
        model,
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=0,                  # 0 adalah jalur tercepat di Unsloth
        bias="none",
        target_modules=None,             # semua layer linear di attention (termasuk Gated DeltaNet) dan MLP
        finetune_vision_layers=False,
        finetune_language_layers=True,
        finetune_attention_modules=True,
        finetune_mlp_modules=True,
        use_gradient_checkpointing="unsloth",
        random_state=args.seed,
    )

    bf16 = is_bfloat16_supported()
    texts, lengths, dropped = build_texts(tokenizer, cfg["template_kwargs"], rows, args.max_seq_len)
    summary = summarize(texts, lengths, dropped, args, bf16)
    status.update(stage="prepared", message="data siap", data=summary)

    class StatusCallback(TrainerCallback):
        def on_train_begin(self, a, state, control, **kw):
            self.t0, self.step0 = time.time(), state.global_step

        def on_log(self, a, state, control, logs=None, **kw):
            done = state.global_step - self.step0
            elapsed = time.time() - self.t0
            eta = elapsed / done * (state.max_steps - state.global_step) / 60 if done else None
            status.update(stage="training", message=f"step {state.global_step}/{state.max_steps}",
                          step=state.global_step, max_steps=state.max_steps, epoch=round(state.epoch or 0, 2),
                          loss=(logs or {}).get("loss", status.data.get("loss")),
                          elapsed_min=round(elapsed / 60, 1), eta_min=round(eta, 1) if eta is not None else None)

    ckpt_dir = run_dir / "checkpoints"
    fingerprint = json.dumps({"data": sha256_file(data_file), **{k: getattr(args, k) for k in TRAINING_KEYS}},
                             sort_keys=True)
    archive_stale_run(run_dir, ckpt_dir, fingerprint)
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    (ckpt_dir / "fingerprint.json").write_text(fingerprint)
    trainer = SFTTrainer(
        model=model,
        processing_class=tokenizer,
        train_dataset=Dataset.from_dict({"text": texts}),
        callbacks=[StatusCallback()],
        args=SFTConfig(
            output_dir=str(ckpt_dir),
            dataset_text_field="text",
            max_length=args.max_seq_len,
            packing=False,
            per_device_train_batch_size=args.batch_size,
            gradient_accumulation_steps=args.grad_accum,
            num_train_epochs=args.epochs,
            learning_rate=args.lr,
            lr_scheduler_type="cosine",
            warmup_steps=max(1, round(0.1 * summary["total_steps"])),  # 10% dari total step
            weight_decay=0.01,
            optim="adamw_8bit",
            fp16=not bf16,               # Unsloth mengganti ke float32 sendiri jika model tidak aman di fp16
            bf16=bf16,
            logging_steps=1,
            save_strategy="steps",
            save_steps=args.save_steps,
            save_total_limit=2,
            seed=args.seed,
            report_to="none",
            dataset_num_proc=2,
        ),
    )
    trainer = train_on_responses_only(trainer, instruction_part="<|im_start|>user\n",
                                      response_part="<|im_start|>assistant\n")

    labels = trainer.train_dataset[0]["labels"]
    trained = tokenizer.decode([t for t in labels if t != -100])
    print(f"cek masking: {sum(t != -100 for t in labels)} dari {len(labels)} token sampel pertama ikut dilatih:")
    print(trained[:300], "...\n", flush=True)

    last = get_last_checkpoint(str(ckpt_dir)) if ckpt_dir.exists() else None
    status.update(stage="training", message=f"mulai dari {last or 'awal'}", resumed_from=last)
    stats = trainer.train(resume_from_checkpoint=last)

    status.update(stage="saving", message="menyimpan adapter")
    adapter_dir = run_dir / "lora-adapter"
    model.save_pretrained(str(adapter_dir))
    tokenizer.save_pretrained(str(adapter_dir))
    result = {"train_runtime_min": round(stats.metrics["train_runtime"] / 60, 1),
              "train_loss": round(stats.metrics["train_loss"], 4), "adapter": str(adapter_dir)}
    status.update(stage="trained", message="adapter tersimpan", result=result)

    if not args.no_test:
        status.update(stage="testing", message="membuat website dari prompt uji")
        status.update(stage="done", message="selesai", tests=generate_tests(model, tokenizer, cfg, run_dir, args.max_new_tokens))
    else:
        status.update(stage="done", message="selesai (tanpa uji)")


def cmd_test(args, cfg, status, run_dir):
    status.update(stage="testing", message="memuat adapter")
    model, tokenizer = load_model(cfg, args, model_name=str(run_dir / "lora-adapter"))
    status.update(stage="done", message="uji selesai", tests=generate_tests(model, tokenizer, cfg, run_dir, args.max_new_tokens))


def cmd_gguf(args, cfg, status, run_dir):
    status.update(stage="exporting", message="menggabungkan adapter dan membuat GGUF q4_k_m")
    model, tokenizer = load_model(cfg, args, model_name=str(run_dir / "lora-adapter"))
    model.save_pretrained_gguf(str(run_dir / "gguf"), tokenizer, quantization_method="q4_k_m")
    status.update(stage="done", message="GGUF tersimpan", gguf=str(run_dir / "gguf"))


def detect_small_gpu():
    """True jika GPU tidak mendukung bf16 dan VRAM < 20 GB (misalnya T4): Qwen3.5 dilatih dalam float32 di sana,
    dan di T4 16-bit maupun 4-bit dengan konteks 8192 terbukti kehabisan memori."""
    try:
        import torch
        if not torch.cuda.is_available():
            return False
        return not torch.cuda.is_bf16_supported() and torch.cuda.get_device_properties(0).total_memory < 20e9
    except ImportError:
        return False


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", nargs="?", choices=["info", "prepare", "train", "test", "gguf"])
    parser.add_argument("--model", choices=sorted(MODELS))
    parser.add_argument("--dataset", choices=["own", "mix"])
    parser.add_argument("--out", help="folder hasil, misalnya di Google Drive")
    parser.add_argument("--data", help="path train.jsonl (bawaan: cari otomatis, lalu unduh dari GitHub)")
    parser.add_argument("--mix-args", help='argumen tambahan mix_general.py, tulis dengan =, misalnya --mix-args="--code 0 --chat 0"')
    parser.add_argument("--load-in-4bit", action=argparse.BooleanOptionalAction, default=None,
                        help="QLoRA 4-bit (hemat VRAM); --no-load-in-4bit memaksa bawaan model")
    parser.add_argument("--max-seq-len", type=int, help="sampel yang lebih panjang dibuang")
    parser.add_argument("--epochs", type=float, help="bawaan: 3 untuk own, 2 untuk mix")
    parser.add_argument("--lr", type=float)
    parser.add_argument("--lora-r", type=int)
    parser.add_argument("--lora-alpha", type=int)
    parser.add_argument("--batch-size", type=int)
    parser.add_argument("--grad-accum", type=int)
    parser.add_argument("--save-steps", type=int)
    parser.add_argument("--max-new-tokens", type=int, help="batas panjang jawaban saat uji")
    parser.add_argument("--no-test", action="store_true", default=None, help="lewati website uji setelah training")
    parser.add_argument("--seed", type=int)
    # Saat ditempel ke sel notebook, argumen kernel Jupyter diabaikan dan CONFIG yang dipakai.
    args = parser.parse_args([] if IN_NOTEBOOK else None)
    for key, value in CONFIG.items():
        if getattr(args, key, None) is None:
            setattr(args, key, value)
    if args.command not in ("info", "prepare", "train", "test", "gguf"):
        raise ValueError(f"command tidak dikenal: {args.command!r}")
    if args.epochs is None:
        args.epochs = 2 if args.dataset == "mix" else 3
    if args.load_in_4bit is None or args.max_seq_len is None:
        small = detect_small_gpu()
        if args.load_in_4bit is None:
            args.load_in_4bit = MODELS[args.model]["load_in_4bit"] or small
        if args.max_seq_len is None:
            args.max_seq_len = 6144 if small else 8192
        if small:
            print("GPU kecil tanpa bf16 terdeteksi (misalnya T4): memakai pengaturan hemat memori "
                  f"(load_in_4bit={args.load_in_4bit}, max_seq_len={args.max_seq_len})", flush=True)
    return args


def main():
    args = parse_args()
    cfg = MODELS[args.model]
    # Hasil QLoRA 4-bit untuk model yang bawaannya 16-bit disimpan terpisah supaya checkpoint tidak tercampur.
    suffix = "-4bit" if args.load_in_4bit and not cfg["load_in_4bit"] else ""
    run_dir = Path(args.out) / f"{args.model}-{args.dataset}{suffix}"
    if args.command == "info":
        print(json.dumps({"model": args.model, "dataset": args.dataset, "load_in_4bit": args.load_in_4bit,
                          "max_seq_len": args.max_seq_len,
                          "epochs": args.epochs, "run_dir": str(run_dir), "status": str(run_dir / "status.json")},
                         indent=1))
        return

    ensure_drive(args.out)
    run_dir.mkdir(parents=True, exist_ok=True)
    print(f"folder hasil: {run_dir}", flush=True)
    status = Status(run_dir / "status.json")
    status.update(stage="starting", message=args.command, command=args.command, model=args.model,
                  dataset=args.dataset, load_in_4bit=args.load_in_4bit, max_seq_len=args.max_seq_len,
                  pid=os.getpid())
    commands = {"prepare": cmd_prepare, "train": cmd_train, "test": cmd_test, "gguf": cmd_gguf}
    try:
        commands[args.command](args, cfg, status, run_dir)
    except BaseException as e:
        tb = traceback.format_exc()
        hint = None
        if "out of memory" in tb.lower() and not args.load_in_4bit:
            hint = "VRAM tidak cukup: ulangi dengan --load-in-4bit --max-seq-len 6144 (di T4 keduanya diperlukan)"
        elif "out of memory" in tb.lower():
            smaller = 6144 if args.max_seq_len > 6144 else 4096
            hint = (f"VRAM tidak cukup: ulangi dengan --max-seq-len {smaller}"
                    + (" (sebagian besar sampel web akan terbuang; GPU L4 lebih disarankan)" if smaller < 6144 else ""))
        elif re.search(r"\bnan\b", str(e), re.IGNORECASE):
            hint = "loss NaN: pasang ulang Unsloth terbaru; untuk Qwen3.5 di T4 Unsloth harus beralih ke float32"
        elif "drive belum ter-mount" in str(e).lower():
            hint = "mount Google Drive dari sel notebook"
        status.update(stage="error", message=f"{type(e).__name__}: {e}"[:500], hint=hint, traceback=tb[-3000:])
        raise


if __name__ == "__main__":
    main()
