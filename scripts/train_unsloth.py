"""Fine-tuning LoRA dengan Unsloth: persiapan data, training, uji coba, dan ekspor GGUF.

Dipakai oleh notebooks/train_colab.ipynb, dan bisa dijalankan langsung dari terminal (termasuk oleh Claude Code,
lihat docs/RUNBOOK_CLAUDE.md). Semua hasil ditulis ke <out>/<model>-<dataset>/:

    status.json      tahap yang sedang berjalan, step, loss, ETA, atau pesan error (dibaca untuk memantau)
    checkpoints/     checkpoint training; training otomatis dilanjutkan dari yang terakhir
    lora-adapter/    adapter LoRA hasil training
    contoh-*.html    website yang dibuat model dari prompt uji (contoh-*.md berisi jawaban lengkapnya)
    gguf/            hasil ekspor GGUF (opsional)

Pemakaian:
    python scripts/train_unsloth.py prepare --model qwen3.5-4b --dataset own    # cek data, tanpa GPU
    python scripts/train_unsloth.py train   --model qwen3.5-4b --dataset own --out /content/drive/MyDrive/finetune-id
    python scripts/train_unsloth.py test    --model qwen3.5-4b --dataset own --out ...   # uji ulang adapter
    python scripts/train_unsloth.py gguf    --model qwen3.5-4b --dataset own --out ...   # ekspor q4_k_m
"""
import argparse
import json
import math
import os
import re
import subprocess
import sys
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EOS = "<|im_end|>"

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
    assert last["role"] == "assistant", "sampel harus diakhiri jawaban assistant"
    return render(tokenizer, template_kwargs, history, add_generation_prompt=True) + last["content"] + EOS


def build_texts(tokenizer, template_kwargs, data_file, max_seq_len):
    """Kembalikan (texts, lengths, dropped). Sampel yang lebih panjang dari max_seq_len dibuang, tidak dipotong."""
    texts, lengths, dropped = [], [], []
    for line in open(data_file, encoding="utf-8"):
        row = json.loads(line)
        text = to_text(tokenizer, template_kwargs, row["messages"])
        n = len(tokenizer(text, add_special_tokens=False)["input_ids"])
        if n > max_seq_len:
            dropped.append((row["id"], n))
            continue
        texts.append(text)
        lengths.append(n)
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
    print(f"{args.epochs} epoch = {total_steps} step, ±{trained_tokens:,} token dilatih")
    print(f"perkiraan waktu ({lo}–{hi} token/detik): {summary['estimate_min'][0]}–{summary['estimate_min'][1]} menit")
    print("\ncontoh awal teks training:\n" + texts[0][:400] + "\n")
    return summary


def data_file_for(args):
    if args.dataset == "own":
        return ROOT / "data/train.jsonl"
    # Data campuran disimpan di --out supaya sesi berikutnya memakai file yang sama persis (penting untuk resume).
    mix = Path(args.out) / "train_mix.jsonl"
    if not mix.exists():
        print("membuat data campuran dengan scripts/mix_general.py ...", flush=True)
        subprocess.run([sys.executable, str(ROOT / "scripts/mix_general.py"), "--seed", str(args.seed),
                        "--output", str(mix)], check=True)
    return mix


def validate(data_file):
    subprocess.run([sys.executable, str(ROOT / "scripts/validate.py"), str(data_file)], check=True)


# ---------------------------------------------------------------- model

def load_model(cfg, args, model_name=None):
    from unsloth import FastLanguageModel

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=model_name or cfg["name"],
        max_seq_length=args.max_seq_len,
        dtype=None,
        load_in_4bit=cfg["load_in_4bit"],
        load_in_16bit=not cfg["load_in_4bit"],
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


# ---------------------------------------------------------------- commands

def cmd_prepare(args, cfg, status):
    from transformers import AutoTokenizer

    data_file = data_file_for(args)
    validate(data_file)
    tokenizer = unwrap_tokenizer(AutoTokenizer.from_pretrained(cfg["tokenizer"]))
    texts, lengths, dropped = build_texts(tokenizer, cfg["template_kwargs"], data_file, args.max_seq_len)
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
    validate(data_file)

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
    texts, lengths, dropped = build_texts(tokenizer, cfg["template_kwargs"], data_file, args.max_seq_len)
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


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=["prepare", "train", "test", "gguf"])
    parser.add_argument("--model", choices=sorted(MODELS), default="qwen3.5-4b")
    parser.add_argument("--dataset", choices=["own", "mix"], default="own")
    parser.add_argument("--out", default=str(ROOT / "runs"), help="folder hasil, misalnya di Google Drive")
    parser.add_argument("--max-seq-len", type=int, default=8192, help="sampel yang lebih panjang dibuang")
    parser.add_argument("--epochs", type=float, help="bawaan: 3 untuk own, 2 untuk mix")
    parser.add_argument("--lr", type=float, default=1e-4)
    parser.add_argument("--lora-r", type=int, default=16)
    parser.add_argument("--lora-alpha", type=int, default=32)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--grad-accum", type=int, default=8)
    parser.add_argument("--save-steps", type=int, default=10)
    parser.add_argument("--max-new-tokens", type=int, default=6000, help="batas panjang jawaban saat uji")
    parser.add_argument("--no-test", action="store_true", help="lewati pembuatan website uji setelah training")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    if args.epochs is None:
        args.epochs = 2 if args.dataset == "mix" else 3

    cfg = MODELS[args.model]
    run_dir = Path(args.out) / f"{args.model}-{args.dataset}"
    run_dir.mkdir(parents=True, exist_ok=True)
    status = Status(run_dir / "status.json")
    status.update(stage="starting", message=args.command, command=args.command, model=args.model,
                  dataset=args.dataset, max_seq_len=args.max_seq_len, pid=os.getpid())
    try:
        {"prepare": lambda: cmd_prepare(args, cfg, status),
         "train": lambda: cmd_train(args, cfg, status, run_dir),
         "test": lambda: cmd_test(args, cfg, status, run_dir),
         "gguf": lambda: cmd_gguf(args, cfg, status, run_dir)}[args.command]()
    except BaseException as e:
        tb = traceback.format_exc()
        hint = None
        if "out of memory" in tb.lower():
            hint = "VRAM tidak cukup: ulangi perintah yang sama dengan --max-seq-len 6144"
        elif re.search(r"\bnan\b", str(e), re.IGNORECASE):
            hint = "loss NaN: pastikan memakai Unsloth terbaru; untuk Qwen3.5 di T4 Unsloth harus beralih ke float32"
        status.update(stage="error", message=f"{type(e).__name__}: {e}"[:500], hint=hint, traceback=tb[-3000:])
        raise


if __name__ == "__main__":
    main()
