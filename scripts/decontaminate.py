"""Periksa tumpang tindih data/train.jsonl dengan soal benchmark dan soal uji (dekontaminasi).

Sumber yang diperiksa:
  HumanEval+   prompt dan solusi (data/bench-support/humaneval.jsonl)
  MBPP+        prompt dan solusi (cache EvalPlus, diunduh jika belum ada)
  IndoPy       prompt, solusi rujukan, dan tes (eval-suite/indopy/)
  Web-eval     teks prompt (eval-suite/web_eval.py)

Metode: 13-gram kata, cara yang lazim dipakai untuk dekontaminasi data kode. Satu 13-gram yang sama sudah dianggap
kontaminasi, karena urutan 13 kata identik hampir tidak mungkin muncul kebetulan. Selain itu, fungsi di sampel latihan
yang namanya sama dengan nama fungsi soal uji dilaporkan sebagai peringatan untuk ditinjau manual.

Pemakaian:
    python scripts/decontaminate.py            # keluar dengan kode 1 jika ada kontaminasi
"""
import ast
import gzip
import json
import re
import sys
import urllib.request
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
N = 13
MBPP_URL = "https://github.com/evalplus/mbppplus_release/releases/download/v0.2.0/MbppPlus.jsonl.gz"
MBPP_CACHE = Path.home() / ".cache" / "evalplus" / "MbppPlus-v0.2.0.jsonl"


def grams(text):
    words = re.findall(r"\w+", text.lower())
    return {" ".join(words[i:i + N]) for i in range(len(words) - N + 1)}


def read_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def humaneval():
    for r in read_jsonl(ROOT / "data" / "bench-support" / "humaneval.jsonl"):
        text = r["messages"][0]["content"] + "\n" + r["messages"][1]["content"]
        entry = re.findall(r"^def (\w+)\(", r["messages"][0]["content"], re.M)
        yield r["source"], text, entry[-1:] if entry else []


def mbpp():
    if not MBPP_CACHE.is_file():
        MBPP_CACHE.parent.mkdir(parents=True, exist_ok=True)
        print(f"mengunduh MBPP+ ke {MBPP_CACHE}", flush=True)
        with urllib.request.urlopen(MBPP_URL) as f:
            MBPP_CACHE.write_bytes(gzip.decompress(f.read()))
    for r in read_jsonl(MBPP_CACHE):
        yield r["task_id"], r["prompt"] + "\n" + r["canonical_solution"], [r["entry_point"]]


def indopy():
    for split in ("dev", "test"):
        path = ROOT / "eval-suite" / "indopy" / f"{split}.jsonl"
        if path.is_file():
            for r in read_jsonl(path):
                yield r["task_id"], "\n".join([r["prompt"], r["canonical_solution"], r["tests"]]), [r["entry_point"]]


def web_eval():
    tree = ast.parse((ROOT / "eval-suite" / "web_eval.py").read_text())
    prompts = next(ast.literal_eval(node.value) for node in tree.body
                   if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "PROMPTS")
    for key, text in prompts.items():
        yield f"Web-eval/{key}", text, []


def main():
    index, names = defaultdict(set), defaultdict(set)
    sources = {"HumanEval+": humaneval, "MBPP+": mbpp, "IndoPy": indopy, "Web-eval": web_eval}
    counts = {}
    for label, load in sources.items():
        counts[label] = 0
        for item_id, text, entry_points in load():
            counts[label] += 1
            for g in grams(text):
                index[g].add(item_id)
            for name in entry_points:
                names[name].add(item_id)
    print("sumber: " + ", ".join(f"{k} {v} soal" for k, v in counts.items()))

    contaminated, warnings = [], []
    for row in read_jsonl(ROOT / "data" / "train.jsonl"):
        text = "\n".join(m["content"] for m in row["messages"])
        hits = defaultdict(int)
        for g in grams(text):
            for item_id in index.get(g, ()):
                hits[item_id] += 1
        if hits:
            contaminated.append((row["id"], dict(hits)))
        defined = set(re.findall(r"^\s*def (\w+)\(", text, re.M))
        for name in sorted(defined & set(names)):
            warnings.append((row["id"], name, sorted(names[name])))

    for sample_id, hits in contaminated:
        top = ", ".join(f"{k} ({v} 13-gram)" for k, v in sorted(hits.items(), key=lambda kv: -kv[1])[:5])
        print(f"KONTAMINASI {sample_id}: {top}")
    for sample_id, name, items in warnings:
        print(f"peringatan {sample_id}: fungsi {name}() bernama sama dengan {', '.join(items[:3])}; tinjau manual")
    if contaminated:
        sys.exit(f"{len(contaminated)} sampel tumpang tindih dengan soal uji")
    print(f"OK: tidak ada 13-gram yang sama ({len(warnings)} peringatan nama fungsi)")


if __name__ == "__main__":
    main()
