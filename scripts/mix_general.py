"""Campur data/train.jsonl dengan dataset instruksi umum dari Hugging Face.

Hasilnya data/train_mix.jsonl dengan format yang sama seperti train.jsonl. Di LLaMA-Factory
file ini terdaftar sebagai dataset `instruct_id_mix`.

Pemakaian (butuh akses internet ke huggingface.co):
    pip install datasets
    python scripts/mix_general.py
    python scripts/mix_general.py --aya-id 800 --code 300 --chat 150 --seed 7

Data diambil secara streaming, jadi dataset besar tidak perlu diunduh penuh.
"""
import argparse
import json
import random
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHARS_PER_TOKEN = 3        # perkiraan kasar untuk tokenizer Qwen pada teks campuran Indonesia/Inggris/kode
MAX_TOKENS = 7000          # sisakan ruang di bawah cutoff_len 8192
MIN_RESPONSE_CHARS = 15

# Jawaban yang menyebut identitas model lain atau berisi boilerplate "sebagai model bahasa AI" dibuang
# supaya tidak bertentangan dengan identitas dari system prompt bawaan Qwen2.5.
BLOCKLIST = re.compile(
    r"\b(openai|chatgpt|gpt-?3\.5|gpt-?4|as an ai language model|as a language model|"
    r"sebagai model bahasa( ai)?|i am an ai developed by)\b",
    re.IGNORECASE,
)


def turn(role, content):
    return {"role": role, "content": content}


# Kolom setiap dataset diperiksa saat dijalankan. Jika pengelola dataset mengubah skemanya,
# skrip berhenti dengan pesan yang menyebut kolom yang tersedia; sesuaikan entri di bawah ini.
SOURCES = {
    "aya_id": {
        "path": "CohereForAI/aya_dataset",  # ditulis manusia, multibahasa; diambil bagian bahasa Indonesia
        "split": "train",
        "category": "general_id",
        "columns": ["inputs", "targets", "language", "language_code"],
        "keep": lambda r: r["language_code"] in ("ind", "id") or r["language"] == "Indonesian",
        "to_messages": lambda r: [turn("user", r["inputs"]), turn("assistant", r["targets"])],
    },
    "code": {
        "path": "ise-uiuc/Magicoder-Evol-Instruct-110K",  # instruksi pemrograman berbahasa Inggris
        "split": "train",
        "category": "general_code",
        "columns": ["instruction", "response"],
        "to_messages": lambda r: [turn("user", r["instruction"]), turn("assistant", r["response"])],
    },
    "chat": {
        "path": "HuggingFaceH4/ultrachat_200k",  # percakapan umum multi-turn berbahasa Inggris
        "split": "train_sft",
        "category": "general_chat",
        "columns": ["messages"],
        "to_messages": lambda r: [turn(m["role"], m["content"]) for m in r["messages"]],
    },
}


def normalize(text):
    return re.sub(r"\s+", " ", text.lower()).strip()[:300]


def clean(messages):
    """Kembalikan percakapan user/assistant yang valid, atau None jika sampel harus dibuang."""
    messages = [turn(m["role"], (m["content"] or "").strip()) for m in messages]
    while messages and messages[-1]["role"] != "assistant":
        messages.pop()  # percakapan yang berakhir di giliran user dipotong
    if not messages or len(messages) % 2:
        return None
    for i, m in enumerate(messages):
        if m["role"] != ("user" if i % 2 == 0 else "assistant") or not m["content"]:
            return None
        if m["role"] == "assistant" and (len(m["content"]) < MIN_RESPONSE_CHARS or BLOCKLIST.search(m["content"])):
            return None
    if sum(len(m["content"]) for m in messages) / CHARS_PER_TOKEN > MAX_TOKENS:
        return None
    return messages


def collect(name, spec, n, seed, seen_prompts):
    from datasets import load_dataset

    stream = load_dataset(spec["path"], split=spec["split"], streaming=True).shuffle(seed=seed, buffer_size=10_000)
    samples, checked = [], False
    for row in stream:
        if not checked:
            missing = [c for c in spec["columns"] if c not in row]
            if missing:
                sys.exit(f"[{name}] kolom {missing} tidak ada di {spec['path']}. "
                         f"Kolom yang tersedia: {sorted(row)}. Sesuaikan SOURCES['{name}'] di skrip ini.")
            checked = True
        if "keep" in spec and not spec["keep"](row):
            continue
        messages = clean(spec["to_messages"](row))
        if messages is None:
            continue
        key = normalize(messages[0]["content"])
        if key in seen_prompts:
            continue
        seen_prompts.add(key)
        samples.append({"id": f"{name}-{len(samples) + 1:05d}", "category": spec["category"], "messages": messages})
        if len(samples) >= n:
            break
    if len(samples) < n:
        print(f"  peringatan: {name} hanya menghasilkan {len(samples)} dari {n} sampel yang diminta")
    return samples


def approx_tokens(samples):
    return round(sum(len(m["content"]) for s in samples for m in s["messages"]) / CHARS_PER_TOKEN)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default=str(ROOT / "data/train.jsonl"))
    parser.add_argument("--output", default=str(ROOT / "data/train_mix.jsonl"))
    parser.add_argument("--aya-id", type=int, default=600, help="jumlah sampel umum bahasa Indonesia (Aya)")
    parser.add_argument("--code", type=int, default=200, help="jumlah sampel instruksi pemrograman")
    parser.add_argument("--chat", type=int, default=100, help="jumlah sampel percakapan umum")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    own = [json.loads(line) for line in open(args.input, encoding="utf-8")]
    seen = {normalize(next(m["content"] for m in s["messages"] if m["role"] == "user")) for s in own}

    general = []
    for name, n in [("aya_id", args.aya_id), ("code", args.code), ("chat", args.chat)]:
        if n <= 0:
            continue
        print(f"mengambil {n} sampel {name} dari {SOURCES[name]['path']} ...")
        general += collect(name, SOURCES[name], n, args.seed, seen)

    mixed = own + general
    random.Random(args.seed).shuffle(mixed)
    with open(args.output, "w", encoding="utf-8", newline="\n") as f:
        for s in mixed:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")

    own_tok, gen_tok = approx_tokens(own), approx_tokens(general)
    print(f"\n{len(mixed)} sampel ditulis ke {args.output}")
    print(f"  dataset sendiri : {len(own):5d} sampel, ±{own_tok:,} token")
    for category in sorted({s["category"] for s in general}):
        part = [s for s in general if s["category"] == category]
        print(f"  {category:16s}: {len(part):5d} sampel, ±{approx_tokens(part):,} token")
    if own_tok + gen_tok:
        print(f"  porsi dataset sendiri ±{own_tok / (own_tok + gen_tok):.0%} dari total token (perkiraan)")


if __name__ == "__main__":
    main()
