"""Isi tag <think> yang ditulis manusia untuk sampel dataset own.

Sumbernya file teks di data/think/<id>-<n>.md: isi <think> untuk jawaban assistant ke-n (mulai dari 1) pada sampel
<id>. File-file itu ditulis lewat scripts/editor_think.py, lalu `apply` memasangnya ke data/train.jsonl sebagai

    <think>
    ...isi file...
    </think>

    <jawaban asli>

Pemasangan selalu dimulai dari jawaban tanpa <think>, jadi menjalankannya berulang kali hasilnya sama. Menghapus file
juga menghapus <think> dari sampelnya.

Pemakaian:
    python scripts/think_tags.py status    # berapa jawaban yang sudah punya isi <think>
    python scripts/think_tags.py apply     # pasang semua file data/think/ ke data/train.jsonl
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TRAIN = ROOT / "data" / "train.jsonl"
THINK_DIR = ROOT / "data" / "think"
BLOCK = re.compile(r"\A<think>\n(.*?)\n</think>\n\n", re.S)


def strip_think(content):
    """Jawaban tanpa blok <think> di awalnya."""
    return BLOCK.sub("", content, count=1)


def think_of(content):
    m = BLOCK.match(content)
    return m.group(1) if m else ""


def think_path(sample_id, turn):
    return THINK_DIR / f"{sample_id}-{turn}.md"


def read_think(sample_id, turn):
    path = think_path(sample_id, turn)
    return path.read_text(encoding="utf-8").strip() if path.is_file() else ""


def apply_to_row(row):
    """Pasang isi <think> dari data/think/ ke setiap jawaban assistant di satu sampel."""
    turn = 0
    for msg in row["messages"]:
        if msg["role"] != "assistant":
            continue
        turn += 1
        answer = strip_think(msg["content"])
        text = read_think(row["id"], turn)
        msg["content"] = f"<think>\n{text}\n</think>\n\n{answer}" if text else answer
    return row


def load_rows():
    return [json.loads(line) for line in TRAIN.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_rows(rows):
    TRAIN.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


def apply():
    rows = [apply_to_row(r) for r in load_rows()]
    write_rows(rows)
    return rows


def status(rows=None):
    """(jumlah jawaban yang sudah berisi <think>, jumlah semua jawaban assistant)."""
    rows = rows or load_rows()
    answers = [m for r in rows for m in r["messages"] if m["role"] == "assistant"]
    return sum(bool(think_of(m["content"])) for m in answers), len(answers)


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "apply":
        rows = apply()
        done, total = status(rows)
        print(f"ditulis: {TRAIN.relative_to(ROOT)}, {done}/{total} jawaban berisi <think>")
    elif cmd == "status":
        done, total = status()
        print(f"{done}/{total} jawaban berisi <think>")
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
