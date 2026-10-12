"""Ubah hasil scripts/harvest_code.py (runs/harvest/raw.jsonl) menjadi draf dataset SFT format messages.

Pemakaian:
    python scripts/raw_to_sft.py
    python scripts/raw_to_sft.py --kinds function doc --max-chars 8000
    python scripts/validate.py runs/harvest/sft_draft.jsonl

Hasilnya draf, bukan data siap latih:
- Sebagian besar sumbernya berbahasa Inggris. Terjemahkan atau tulis ulang jawabannya ke bahasa
  Indonesia, lalu periksa kebenarannya.
- Setiap sampel membawa field `meta` (sumber, URL, lisensi, atribusi), supaya kewajiban lisensinya
  tetap bisa dipenuhi setelah sampel diubah.
"""
import argparse
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

ROLE_MAP = {"user": "user", "human": "user", "prompter": "user", "assistant": "assistant", "gpt": "assistant",
            "bot": "assistant", "model": "assistant", "system": "system"}
PAIRS = [("instruction", "output"), ("instruction", "response"), ("prompt", "response"), ("prompt", "completion"),
         ("question", "answer"), ("problem", "solution"), ("query", "response"), ("inputs", "targets"), ("input", "output")]


def turn(role, content):
    return {"role": role, "content": content}


def from_function(rec):
    doc = rec["docstring"].strip()
    prompt = f"Tulis fungsi Python `{rec['name']}` sesuai dokumentasi berikut.\n\n```\n{doc}\n```"
    answer = f"```python\n{rec['code'].rstrip()}\n```"
    return "code_function", [turn("user", prompt), turn("assistant", answer)]


def from_doc(rec):
    prompt = f"Jelaskan `{rec['title']}` dalam pengembangan web, lengkap dengan contoh kodenya."
    return "web_docs", [turn("user", prompt), turn("assistant", rec["text"])]


def from_row(rec):
    row = rec["row"]
    for key in ("messages", "conversations", "conversation", "dialog"):
        turns = row.get(key)
        if isinstance(turns, list) and turns and all(isinstance(t, dict) for t in turns):
            messages = []
            for t in turns:
                role = ROLE_MAP.get(str(t.get("role", t.get("from", ""))).lower())
                content = t.get("content", t.get("value"))
                if not role or not isinstance(content, str) or not content.strip():
                    return None, None
                messages.append(turn(role, content))
            return "hf_conversation", messages
    for q, a in PAIRS:
        if isinstance(row.get(q), str) and isinstance(row.get(a), str) and row[q].strip() and row[a].strip():
            prompt = row[q]
            # Kolom input tambahan (format Alpaca) digabung ke prompt.
            extra = row.get("input") if (q, a) == ("instruction", "output") else None
            if isinstance(extra, str) and extra.strip():
                prompt = f"{prompt}\n\n{extra}"
            return "hf_instruction", [turn("user", prompt), turn("assistant", row[a])]
    return None, None


def well_formed(messages):
    roles = [m["role"] for m in messages]
    if roles and roles[0] == "system":
        roles = roles[1:]
    return bool(roles) and roles == ["user", "assistant"] * (len(roles) // 2)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--input", default=str(ROOT / "runs/harvest/raw.jsonl"))
    parser.add_argument("--output", default=str(ROOT / "runs/harvest/sft_draft.jsonl"))
    parser.add_argument("--kinds", nargs="+", default=["function", "doc", "row"], choices=["function", "doc", "row"])
    parser.add_argument("--max-chars", type=int, default=12000, help="buang sampel yang lebih panjang dari ini (±4.000 token)")
    args = parser.parse_args()

    converters = {"function": from_function, "doc": from_doc, "row": from_row}
    written, skipped = Counter(), Counter()
    with open(args.input, encoding="utf-8") as src, open(args.output, "w", encoding="utf-8") as out:
        for line in src:
            rec = json.loads(line)
            if rec.get("kind") not in args.kinds:
                continue
            category, messages = converters[rec["kind"]](rec)
            if not messages:
                skipped["format baris tidak dikenali"] += 1
                continue
            if not well_formed(messages):
                skipped["urutan giliran tidak valid"] += 1
                continue
            if sum(len(m["content"]) for m in messages) > args.max_chars:
                skipped["terlalu panjang"] += 1
                continue
            meta = {k: rec.get(k) for k in ("source", "url", "license", "attribution", "repo", "dataset", "risk_notes") if rec.get(k)}
            sample = {"id": f"draft-{rec['hash']}", "category": category, "messages": messages, "meta": meta}
            out.write(json.dumps(sample, ensure_ascii=False) + "\n")
            written[category] += 1

    print(f"{sum(written.values())} sampel draf ditulis ke {args.output}")
    for category, n in sorted(written.items()):
        print(f"  {category}: {n}")
    for reason, n in skipped.items():
        print(f"  dilewati ({reason}): {n}")
    print("\nLangkah berikutnya: terjemahkan atau tulis ulang ke bahasa Indonesia, periksa kebenarannya,\n"
          f"lalu jalankan: python scripts/validate.py {args.output}")


if __name__ == "__main__":
    main()
