"""Bangun sampel Python dari sumbernya di data/python-src/, dengan output hasil eksekusi sungguhan.

Setiap sampel adalah satu folder data/python-src/<id>/ berisi:
  sample.json   {"id", "category", "turns": [file giliran user/assistant berurutan], opsional "python": "3.8",
                 opsional "patches": [{"turn": <indeks giliran assistant>, "from": <file awal>, "to": <file akhir>}],
                 opsional "before_turn": {"<indeks giliran>": {"<file di folder kerja>": "<file sumber>"}}}
  *.md          teks tiap giliran, boleh berisi arahan di bawah
  file kode     yang dirujuk arahan

Arahan di file giliran:
  {{file NAMA}}      isi file NAMA
  {{run PERINTAH}}   "$ PERINTAH" lalu outputnya (stdout + stderr), dijalankan di salinan folder sampel.
                     Semua perintah satu sampel berjalan berurutan di salinan yang sama, seperti satu sesi terminal.
  {{output PERINTAH}} outputnya saja, misalnya traceback yang ditempel user
  {{copy SUMBER TUJUAN}} salin file sumber ke folder kerja tanpa menampilkan apa pun, misalnya untuk menjalankan
                     tes pada kode ber-bug lalu pada kode yang sudah diperbaiki dalam satu giliran
Perintah diawali "python" dijalankan dengan interpreter sampel: Python saat ini, atau versi di "python" (lewat uv).
Perintah diawali "python3.X" dijalankan dengan Python versi itu (lewat uv), misalnya untuk sampel kompatibilitas versi.

"before_turn" menyalin file sebelum giliran itu dirender. Contohnya sampel debug: giliran user menjalankan versi
ber-bug sebagai keranjang.py, lalu giliran assistant menjalankan versi perbaikan dengan nama yang sama.

Untuk "patches", blok <<<<<<< SEARCH / ======= / >>>>>>> REPLACE di giliran itu diterapkan ke file "from" dan hasilnya
harus sama persis dengan file "to". Jadi patch di jawaban terbukti benar.

Pemakaian:
    python scripts/build_python_samples.py            # bangun ulang dan tulis ke data/train.jsonl
    python scripts/build_python_samples.py --check    # pastikan data/train.jsonl sama dengan hasil bangun ulang
"""
import argparse
import json
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import think_tags  # noqa: E402  isi <think> dari data/think/ ikut dipasang saat menulis train.jsonl

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "python-src"
TRAIN = ROOT / "data" / "train.jsonl"
DIRECTIVE = re.compile(r"\{\{(file|run|output|copy) ([^}]+)\}\}(\n?)")
PATCH = re.compile(r"<<<<<<< SEARCH\n(.*?)\n=======\n(.*?)\n>>>>>>> REPLACE", re.S)
TIMING = re.compile(r"(Ran \d+ tests?) in \d+\.\d+s")


def interpreter(version):
    if not version:
        return sys.executable
    found = subprocess.run(["uv", "python", "find", version], capture_output=True, text=True)
    if found.returncode != 0:
        raise SystemExit(f"Python {version} tidak ditemukan; pasang dengan: uv python install {version}")
    return found.stdout.strip()


def run(command, work, python):
    """Jalankan perintah di folder kerja sampel; path folder kerja dihapus dari output."""
    args = shlex.split(command)
    if args[0] == "python":
        args[0] = python
    elif re.fullmatch(r"python3\.\d+", args[0]):
        args[0] = interpreter(args[0][len("python"):])
    r = subprocess.run(args, cwd=work, capture_output=True, text=True, timeout=60, stdin=subprocess.DEVNULL,
                       env={"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8", "PYTHONHASHSEED": "0",
                            "PYTHONDONTWRITEBYTECODE": "1", "TZ": "UTC", "HOME": str(work)})
    output = (r.stdout + r.stderr).rstrip("\n")
    return output.replace(f"{work}/", "").replace(str(work), ".")


def render(text, folder, work, python):
    def replace(m):
        kind, arg, newline = m.group(1), m.group(2).strip(), m.group(3)
        if kind == "copy":
            src, dest = arg.split()
            shutil.copyfile(folder / src, work / dest)
            return ""
        if kind == "file":
            return (folder / arg).read_text().rstrip("\n") + newline
        output = run(arg, work, python)
        return (output if kind == "output" else f"$ {arg}\n{output}") + newline
    return DIRECTIVE.sub(replace, text).strip()


def apply_patches(text, source):
    for search, replace in PATCH.findall(text):
        if source.count(search) != 1:
            raise ValueError(f"blok SEARCH harus cocok tepat 1 kali, ditemukan {source.count(search)}: {search[:60]!r}")
        source = source.replace(search, replace)
    return source


def build_one(folder):
    spec = json.loads((folder / "sample.json").read_text())
    python = interpreter(spec.get("python"))
    roles = ["user", "assistant"] * len(spec["turns"])
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "kerja"
        shutil.copytree(folder, work)
        messages = []
        for i, (role, name) in enumerate(zip(roles, spec["turns"])):
            for dest, src in spec.get("before_turn", {}).get(str(i), {}).items():
                shutil.copyfile(folder / src, work / dest)
            messages.append({"role": role, "content": render((folder / name).read_text(), folder, work, python)})
    for patch in spec.get("patches", []):
        before = (folder / patch["from"]).read_text()
        after = apply_patches(messages[patch["turn"]]["content"], before)
        if after != (folder / patch["to"]).read_text():
            raise ValueError(f"{spec['id']}: patch di giliran {patch['turn']} tidak menghasilkan {patch['to']}")
    return {"id": spec["id"], "category": spec["category"], "messages": messages}


def normalize(entry):
    # Isi <think> ditulis manusia lewat data/think/, bukan dari sumber Python, jadi tidak ikut dibandingkan.
    entry = {**entry, "messages": [{**m, "content": think_tags.strip_think(m["content"])} if m["role"] == "assistant" else m
                                   for m in entry["messages"]]}
    return json.loads(TIMING.sub(r"\1", json.dumps(entry, ensure_ascii=False)))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="hanya periksa, jangan tulis")
    args = parser.parse_args()
    built = {e["id"]: e for e in (build_one(f) for f in sorted(SRC.iterdir()) if (f / "sample.json").is_file())}
    rows = [json.loads(line) for line in TRAIN.read_text().splitlines() if line.strip()]
    ids = [r["id"] for r in rows]
    if args.check:
        stale = [i for i, e in built.items() if i not in ids or normalize(rows[ids.index(i)]) != normalize(e)]
        if stale:
            raise SystemExit(f"data/train.jsonl tidak sesuai sumbernya: {', '.join(stale)}\n"
                             "Jalankan: python scripts/build_python_samples.py")
        print(f"OK: {len(built)} sampel Python sesuai sumber dan hasil eksekusinya")
        return
    rows = [think_tags.apply_to_row(built.pop(r["id"], r)) for r in rows] + [think_tags.apply_to_row(e) for e in built.values()]
    TRAIN.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    print(f"ditulis: {len(rows)} sampel di {TRAIN.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
