"""IndoPy: uji Python berbahasa Indonesia dengan tes tersembunyi, untuk adapter hasil fine-tuning dan model dasarnya.

Soal ditulis seperti permintaan pengguna sungguhan (bahasa Indonesia, menyebut nama dan signature fungsi). Model
menjawab bebas seperti saat dipakai, lalu kode di blok ```python yang mendefinisikan fungsi itu diambil dan dijalankan
bersama tes tersembunyi. Satu soal lolos jika semua assert lolos dalam batas waktu.

Dua set:
  dev   20 soal  boleh dilihat untuk menganalisis jenis kesalahan model
  test  40 soal  dikunci: hanya untuk penilaian akhir, jangan dijadikan dasar menulis sampel latihan

Cara memakai di Google Colab (setelah sel pip install dan mount Drive dari PROSEDUR):

    REPO = "https://raw.githubusercontent.com/PvzKing/Dataset/main"
    !wget -q -O /content/indopy_eval.py {REPO}/eval-suite/indopy_eval.py
    %run /content/indopy_eval.py --split dev --adapter <folder lora-adapter>
    %run /content/indopy_eval.py --split test --adapter <folder lora-adapter>
    %run /content/indopy_eval.py --demo          # uji alur tanpa GPU: jawaban dari solusi rujukan dan solusi salah

Seperti eval_humaneval.py, secara bawaan model dasar juga diuji (adapter dimatikan sementara) dan hasilnya dibandingkan
dengan uji McNemar. Jawaban disimpan per batch, jadi run yang terputus bisa dilanjutkan dengan perintah yang sama.
"""
import argparse
import ast
import json
import re
import subprocess
import sys
import tempfile
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

# ======================================================== CONFIG: ubah di sini ========================================
CONFIG = {
    "adapter": "/content/drive/MyDrive/finetune-id/qwen3.5-4b-own-4bit/lora-adapter",  # path, "auto", "none"
    "split": "dev",                 # "dev" (20 soal) atau "test" (40 soal, hanya untuk penilaian akhir)
    "out": "/content/drive/MyDrive/finetune-id",
    "base_model": "unsloth/Qwen3.5-4B",
    "load_in_4bit": None,           # None = otomatis: 4-bit di GPU tanpa bf16 asli (T4)
    "max_seq_len": 4096,
    "batch_size": 8,
    "max_new_tokens": 2048,         # jawaban bebas: penjelasan + kode + contoh
    "results": None,                # None = <Drive>/finetune-id/eval-indopy-<split>
    "tag": None,
    "limit": None,
    "timeout": 10,                  # detik per soal saat menjalankan tes
    "vs_base": True,
    "demo": False,
}
# ======================================================================================================================

HERE = Path(__file__).resolve().parent if "__file__" in globals() else Path.cwd()
REPO_RAW = "https://raw.githubusercontent.com/PvzKing/Dataset/main"
BLOCK = re.compile(r"```[ \t]*(?:python|py|python3)?[ \t]*\n(.*?)```", re.S | re.I)


def fetch(local, url, target):
    """File dari repo jika ada, selain itu unduh sekali ke target."""
    if local.is_file():
        return local
    if not target.is_file():
        target.parent.mkdir(parents=True, exist_ok=True)
        print(f"mengunduh {url}", flush=True)
        urllib.request.urlretrieve(url, target)
    return target


def import_eval_humaneval():
    """Generator, McNemar, dan perbandingan dipakai bersama dengan eval_humaneval.py."""
    path = fetch(HERE.parent / "humaneval-bench-script" / "eval_humaneval.py",
                 f"{REPO_RAW}/humaneval-bench-script/eval_humaneval.py", HERE / "eval_humaneval.py")
    if str(path.parent) not in sys.path:
        sys.path.insert(0, str(path.parent))
    import eval_humaneval
    return eval_humaneval


def load_tasks(split):
    path = fetch(HERE / "indopy" / f"{split}.jsonl", f"{REPO_RAW}/eval-suite/indopy/{split}.jsonl",
                 HERE / "indopy-data" / f"{split}.jsonl")
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--adapter", help='folder lora-adapter, "auto", atau "none"')
    parser.add_argument("--split", choices=["dev", "test"])
    parser.add_argument("--out")
    parser.add_argument("--base-model")
    parser.add_argument("--load-in-4bit", action=argparse.BooleanOptionalAction, default=None)
    parser.add_argument("--max-seq-len", type=int)
    parser.add_argument("--batch-size", type=int)
    parser.add_argument("--max-new-tokens", type=int)
    parser.add_argument("--results")
    parser.add_argument("--tag")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--timeout", type=int)
    parser.add_argument("--vs-base", action=argparse.BooleanOptionalAction, default=None)
    parser.add_argument("--demo", action="store_true", default=None)
    args, _ = parser.parse_known_args(sys.argv[1:])
    for key, value in CONFIG.items():
        if getattr(args, key, None) is None:
            setattr(args, key, value)
    args.dataset = "indopy"
    if not args.demo and args.adapter not in ("auto", "none") and not (Path(args.adapter) / "adapter_config.json").is_file():
        raise SystemExit(f"adapter tidak ditemukan: {args.adapter}\nPastikan Drive sudah di-mount, atau pilih "
                         "--adapter <folder lora-adapter> (atau auto / none).")
    return args


# ---------------------------------------------------------------- jawaban dan penilaian

def is_main_guard(node):
    test = node.test
    return (isinstance(node, ast.If) and isinstance(test, ast.Compare) and isinstance(test.left, ast.Name)
            and test.left.id == "__name__" and any(isinstance(c, ast.Constant) and c.value == "__main__"
                                                   for c in test.comparators))


def clean_code(code):
    """Buang kode demo tingkat atas (blok __main__, print, loop, assert) supaya tidak mengganggu tes.

    Import, konstanta, fungsi, dan kelas dipertahankan apa adanya. evalplus.sanitize tidak dipakai karena ia bisa
    membuang fungsi pembantu yang sebenarnya dipanggil, sehingga jawaban yang benar dinilai salah.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return code  # biarkan tes yang menilai
    drop = set()
    for node in tree.body:
        demo = isinstance(node, (ast.For, ast.AsyncFor, ast.While, ast.With, ast.AsyncWith, ast.Assert))
        demo |= isinstance(node, ast.Expr) and not isinstance(node.value, ast.Constant)  # docstring modul tetap
        demo |= isinstance(node, ast.If) and is_main_guard(node)
        if demo:
            drop.update(range(node.lineno - 1, node.end_lineno))
    return "\n".join(line for i, line in enumerate(code.splitlines()) if i not in drop)


def extract_code(output, entry_point):
    """Blok kode terakhir yang mendefinisikan fungsi yang diminta, dibersihkan dari kode demo tingkat atas."""
    blocks = BLOCK.findall(output)
    defines = [b for b in blocks if re.search(rf"^\s*def\s+{re.escape(entry_point)}\s*\(", b, re.M)]
    return clean_code((defines or blocks or [output])[-1])


def run_tests(code, tests, timeout):
    """Jalankan kode + tes di proses terpisah. Kembalikan (lolos, alasan gagal)."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "uji.py"
        path.write_text(code + "\n\n" + tests)
        try:
            r = subprocess.run([sys.executable, "-I", str(path)], cwd=tmp, capture_output=True, text=True,
                               timeout=timeout, stdin=subprocess.DEVNULL)
        except subprocess.TimeoutExpired:
            return False, f"melewati batas waktu {timeout} detik"
    if r.returncode == 0:
        return True, ""
    lines = r.stderr.strip().splitlines()
    return False, (lines[-1] if lines else f"exit code {r.returncode}")[:300]


def demo_answer(task, use_adapter):
    # Solusi rujukan, kecuali tiap soal ke-4 ("adapter") atau ke-3 ("dasar") yang memakai solusi salah.
    i = int(task["task_id"].rsplit("/", 1)[1])
    code = task["wrong_solutions"][0] if i % (4 if use_adapter else 3) == 0 else task["canonical_solution"]
    return f"Berikut solusinya.\n\n```python\n{code.strip()}\n\nif __name__ == \"__main__\":\n    print('contoh')\n```\n"


# ---------------------------------------------------------------- run

def run_one(eh, args, tag, model_label, use_adapter, tasks, results_dir, get_generator):
    run_dir = results_dir / tag
    run_dir.mkdir(parents=True, exist_ok=True)
    responses_path = run_dir / "jawaban.jsonl"
    print(f"\n##### run: {tag} ({model_label})\nfolder hasil: {run_dir}", flush=True)
    done = {r["task_id"]: r for r in eh.read_jsonl(responses_path)}
    todo = [t for t in tasks if t["task_id"] not in done]
    if done:
        print(f"{len(done)} soal sudah dijawab sebelumnya, dilewati", flush=True)
    gen_info = {}
    if todo:
        start, n_tokens = time.time(), 0
        generator = None if args.demo else get_generator()
        todo.sort(key=lambda t: len(t["prompt"]))
        for i in range(0, len(todo), args.batch_size):
            batch = todo[i:i + args.batch_size]
            if args.demo:
                texts, tokens = [demo_answer(t, use_adapter) for t in batch], 0
            else:
                prompts = [generator.engine.render([{"role": "user", "content": t["prompt"]}], thinking=False)
                           for t in batch]
                texts, tokens = generator.generate(prompts, use_adapter, args.max_new_tokens)
            n_tokens += tokens
            eh.append_jsonl(responses_path, [{"task_id": t["task_id"], "output": o} for t, o in zip(batch, texts)])
            elapsed = time.time() - start
            finished = i + len(batch)
            print(f"[{tag}] {finished}/{len(todo)} soal, {elapsed / 60:.1f} menit"
                  + (f", {n_tokens / elapsed:.0f} token/detik" if n_tokens else ""), flush=True)
        gen_info = {"menit_generate": round((time.time() - start) / 60, 1), "token_baru": n_tokens}
        done = {r["task_id"]: r for r in eh.read_jsonl(responses_path)}

    def judge(task):
        code = extract_code(done[task["task_id"]]["output"], task["entry_point"])
        ok, reason = run_tests(code, task["tests"], args.timeout)
        return {"task_id": task["task_id"], "base": ok, "tingkat": task["tingkat"], "topik": task["topik"],
                "alasan": reason, "kode": code}

    with ThreadPoolExecutor(max_workers=4) as pool:
        rows = list(pool.map(judge, tasks))
    (run_dir / "hasil.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    summarize(rows, tag, model_label, args, gen_info, results_dir)
    return rows


def summarize(rows, tag, model_label, args, gen_info, results_dir):
    n, ok = len(rows), sum(r["base"] for r in rows)
    per_level = {}
    for r in rows:
        level = per_level.setdefault(r["tingkat"], [0, 0])
        level[0] += r["base"]
        level[1] += 1
    summary = {"tag": tag, "model": model_label, "dataset": f"indopy-{args.split}", "soal": n,
               "indopy_pass@1": round(ok / n, 4), "per_tingkat": {k: f"{a}/{b}" for k, (a, b) in per_level.items()},
               "gagal": {r["task_id"]: r["alasan"] for r in rows if not r["base"]}, **gen_info}
    (results_dir / tag / "ringkasan.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"\n===== {tag}: IndoPy-{args.split}, {n} soal =====")
    print(f"pass@1: {ok / n:6.1%}  ({ok}/{n})   per tingkat: "
          + ", ".join(f"{k} {a}/{b}" for k, (a, b) in sorted(per_level.items())))
    for task_id, reason in summary["gagal"].items():
        print(f"  gagal {task_id.rsplit('/', 1)[1]}: {reason}")
    if args.limit:
        print(f"(hanya {n} soal karena --limit)")


def main():
    eh = import_eval_humaneval()
    args = parse_args()
    tasks = load_tasks(args.split)
    if args.limit:
        tasks = tasks[:args.limit]
    if args.split == "test":
        print("Set test dikunci: pakai hanya untuk penilaian akhir, jangan jadikan dasar menulis sampel latihan.")
    results_dir = Path(args.results or eh.default_results(f"eval-indopy-{args.split}"))
    generator = None

    def get_generator():
        nonlocal generator
        if generator is None:
            generator = eh.Generator(args)
        return generator

    tag = eh.run_tag(args)
    adapter_label = "demo" if args.demo else ("model dasar" if args.adapter == "none" else args.adapter)
    rows = run_one(eh, args, tag, adapter_label, True, tasks, results_dir, get_generator)
    if args.vs_base and args.adapter != "none":
        prefix = args.tag or ("demo" if args.demo else "")
        base_tag = f"{prefix}-model-dasar" if prefix else "model-dasar"
        need = {t["task_id"] for t in tasks} - {r["task_id"] for r in eh.read_jsonl(results_dir / base_tag / "jawaban.jsonl")}
        if need and not args.demo and not get_generator().can_disable_adapter:
            raise SystemExit("model ini tidak bisa mematikan adapter sementara; jalankan --adapter none terpisah")
        base_rows = run_one(eh, args, base_tag, f"{args.base_model} (adapter dimatikan)", False, tasks, results_dir,
                            get_generator)
        eh.compare(rows, base_rows, tag, base_tag, results_dir, names=(f"IndoPy-{args.split}",),
                   short=lambda ids: ", ".join(t.rsplit("/", 1)[1] for t in ids) or "-")


if __name__ == "__main__":
    main()
