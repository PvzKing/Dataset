"""Validasi data/train.jsonl sebelum training.

Pemakaian:
    python scripts/validate.py
    python scripts/validate.py --tokenizer Qwen/Qwen3.5-4B --max-len 6144   # batas otomatis di T4

Opsi --tokenizer butuh paket `transformers` dan menghitung panjang token setelah chat template diterapkan.
"""
import argparse
import json
import re
import sys
from collections import Counter

HTML_BLOCK = re.compile(r"```html\n(.*?)\n```", re.S)


def check_sample(sample, line_no):
    errors = []
    if not isinstance(sample.get("id"), str) or not sample["id"]:
        errors.append("field 'id' wajib berupa string")
    if not isinstance(sample.get("category"), str) or not sample["category"]:
        errors.append("field 'category' wajib berupa string")
    messages = sample.get("messages")
    if not isinstance(messages, list) or len(messages) < 2:
        return errors + ["field 'messages' wajib berupa list berisi minimal 2 pesan"]

    for m in messages:
        if set(m) != {"role", "content"} or not isinstance(m["content"], str) or not m["content"].strip():
            errors.append(f"pesan tidak valid: {str(m)[:60]}")
    roles = [m.get("role") for m in messages]
    if roles[0] == "system":
        roles = roles[1:]
    expected = ["user", "assistant"] * (len(roles) // 2)
    if roles != expected or not roles:
        errors.append(f"urutan role harus [system] lalu user/assistant bergantian, diakhiri assistant: {roles}")

    if sample.get("category") == "web_oneshot":
        blocks = HTML_BLOCK.findall(messages[-1]["content"])
        if len(blocks) != 1:
            errors.append(f"sampel web harus berisi tepat satu blok ```html, ditemukan {len(blocks)}")
        elif not (blocks[0].lstrip().startswith("<!DOCTYPE html>") and blocks[0].rstrip().endswith("</html>")):
            errors.append("blok HTML harus dokumen lengkap dari <!DOCTYPE html> sampai </html>")
        # Penjelasan setelah kode memetakan setiap permintaan di prompt ke implementasinya ("- **permintaan** → ...").
        # Sampel dengan system prompt boleh tanpa judul "Cek kebutuhan" bila system prompt membatasi formatnya.
        notes = messages[-1]["content"].rsplit("\n```", 1)[-1]
        mapped = [line for line in notes.splitlines() if line.lstrip().startswith("- ") and "→" in line]
        if len(mapped) < 2:
            errors.append("penjelasan sampel web harus memetakan permintaan ke implementasi: minimal 2 baris '- **permintaan** → ...'")
        if messages[0]["role"] != "system" and "**Cek kebutuhan**" not in notes:
            errors.append("penjelasan sampel web harus diawali bagian **Cek kebutuhan**")
    return [f"baris {line_no}: {e}" for e in errors]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("path", nargs="?", default="data/train.jsonl")
    parser.add_argument("--tokenizer", help="nama/path tokenizer Hugging Face untuk menghitung token")
    parser.add_argument("--max-len", type=int, default=8192, help="batas cutoff_len saat training")
    args = parser.parse_args()

    samples, errors = [], []
    with open(args.path, encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            try:
                sample = json.loads(line)
            except json.JSONDecodeError as e:
                errors.append(f"baris {line_no}: JSON tidak valid ({e})")
                continue
            errors += check_sample(sample, line_no)
            samples.append(sample)

    def first_user_prompt(sample):
        return next((m.get("content") for m in sample.get("messages") or [] if m.get("role") == "user"), None)

    for label, values in [("id", [s.get("id") for s in samples]), ("prompt user", [first_user_prompt(s) for s in samples])]:
        dupes = [v for v, n in Counter(values).items() if n > 1]
        if dupes:
            errors.append(f"{label} duplikat: {[str(d)[:50] for d in dupes]}")

    print(f"{len(samples)} sampel di {args.path}")
    for category, n in sorted(Counter(s.get("category") for s in samples).items()):
        print(f"  {category}: {n}")

    if args.tokenizer:
        from transformers import AutoTokenizer

        tokenizer = AutoTokenizer.from_pretrained(args.tokenizer)

        def token_count(messages):
            text = tokenizer.apply_chat_template(messages, tokenize=False)
            return len(tokenizer(text, add_special_tokens=False)["input_ids"])

        lengths = [(token_count(s["messages"]), s["id"]) for s in samples]
        longest = max(lengths)
        print(f"token: total {sum(n for n, _ in lengths)}, terpanjang {longest[0]} ({longest[1]})")
        over = [sid for n, sid in lengths if n > args.max_len]
        if over:
            errors.append(f"{len(over)} sampel melebihi --max-len {args.max_len} dan akan terpotong: {over}")

    if errors:
        print(f"\n{len(errors)} masalah ditemukan:")
        for e in errors:
            print("  - " + e)
        sys.exit(1)
    print("OK, semua sampel valid.")


if __name__ == "__main__":
    main()
