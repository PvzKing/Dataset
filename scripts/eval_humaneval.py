"""Uji benchmark HumanEval dan HumanEval+ untuk model hasil fine-tuning (Qwen3.5-4B + adapter LoRA).

Soal, tes, dan penilaian memakai paket resmi EvalPlus (HumanEval+ v0.1.10). Prompt memakai template chat EvalPlus
yang sama dengan sampel bench-support, dan jawaban dibuat dengan greedy decoding (pass@1, seperti leaderboard EvalPlus).

Langkahnya:
  1. Generate   164 soal dijawab per batch. Setiap batch langsung disimpan, jadi jika Colab terputus, jalankan ulang
                perintah yang sama dan soal yang sudah selesai dilewati.
  2. Sanitize   kode diambil dari jawaban dengan evalplus.sanitize, seperti pipeline resmi EvalPlus.
  3. Evaluate   evalplus.evaluate menjalankan tes dasar HumanEval dan tes tambahan HumanEval+.
  4. Ringkasan  skor, soal yang gagal, dan tabel perbandingan semua run di folder hasil.

PENTING: adapter bench-lanjut dilatih dengan 164 soal HumanEval beserta jawabannya. Skornya mengukur hafalan, bukan
kemampuan menyelesaikan soal baru. Bandingkan dengan v3 dan model dasar untuk melihat besarnya efek itu, dan jangan
laporkan skor adapter bench sebagai hasil evaluasi yang bersih.

Cara memakai di Google Colab (GPU T4 cukup):

    Sel 1:  !pip install --upgrade unsloth "evalplus @ git+https://github.com/evalplus/evalplus@26d6d00bb1fd0fa37f39c99d5290da67891d1c5e"
    Sel 2:  from google.colab import drive; drive.mount("/content/drive")
            BR = "https://raw.githubusercontent.com/PvzKing/Dataset/main/scripts"
            !wget -q -O /content/eval_humaneval.py {BR}/eval_humaneval.py
            !wget -q -O /content/chat_gradio.py {BR}/chat_gradio.py
    Sel 3:  %run /content/eval_humaneval.py

Opsi bisa diganti lewat argumen, misalnya:

    %run /content/eval_humaneval.py --adapter /content/drive/MyDrive/finetune-id/v3/qwen3.5-4b-own-4bit/lora-adapter
    %run /content/eval_humaneval.py --adapter none          # model dasar, sebagai pembanding
    %run /content/eval_humaneval.py --limit 10              # uji cepat 10 soal
    %run /content/eval_humaneval.py --batch-size 4          # jika VRAM tidak cukup
    %run /content/eval_humaneval.py --demo                  # uji alur tanpa GPU: jawaban dari solusi resmi

EvalPlus dipasang dari commit master, bukan dari PyPI: versi 0.3.1 di PyPI selalu menilai HumanEval/32 (find_zero)
gagal, bahkan untuk solusi resminya, karena pemeriksa khususnya melompati pencatatan tes yang lolos. Script ini berhenti
jika versi yang terpasang masih membawa bug itu.

Model dimuat dengan kelas Engine dari chat_gradio.py (diunduh otomatis jika belum ada).
"""
import argparse
import json
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

# ======================================================== CONFIG: ubah di sini ========================================
CONFIG = {
    "adapter": "/content/drive/MyDrive/finetune-id/qwen3.5-4b-bench-4bit-lanjut/lora-adapter",  # path, "auto", "none"
    "out": "/content/drive/MyDrive/finetune-id",   # dipakai jika adapter = "auto"
    "base_model": "unsloth/Qwen3.5-4B",
    "load_in_4bit": None,           # None = otomatis: 4-bit di GPU tanpa bf16 asli (T4)
    "max_seq_len": 4096,            # prompt terpanjang ±600 token + jawaban
    "batch_size": 8,                # soal per generate; turunkan jika kehabisan VRAM
    "max_new_tokens": 1024,         # solusi terpanjang di bench-support ±700 token
    "results": "/content/drive/MyDrive/finetune-id/eval-humaneval" if Path("/content").is_dir() else "eval-humaneval",
    "tag": None,                    # nama run (subfolder hasil); default dari nama folder adapter
    "limit": None,                  # angka = hanya N soal pertama, untuk uji cepat
    "parallel": None,               # jumlah proses evaluasi; None = setengah jumlah CPU
    "demo": False,                  # True = tanpa model: jawaban dari solusi resmi, sebagian sengaja dirusak
}
# ======================================================================================================================

HERE = Path(__file__).resolve().parent if "__file__" in globals() else Path.cwd()
CHAT_URL = "https://raw.githubusercontent.com/PvzKing/Dataset/main/scripts/chat_gradio.py"
# Teks persis dari template chat EvalPlus, sama dengan scripts/build_bench_support.py.
INSTRUCTION = ("Please provide a self-contained Python script that solves the following problem in a markdown "
               "code block:")
RESPONSE = ("Below is a Python script with a self-contained function that solves the problem and passes "
            "corresponding tests:")
FENCE = "`" * 3
EVALPLUS_PIP = "evalplus @ git+https://github.com/evalplus/evalplus@26d6d00bb1fd0fa37f39c99d5290da67891d1c5e"


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--adapter", help='folder lora-adapter, "auto", atau "none"')
    parser.add_argument("--out", help="folder hasil training untuk adapter auto")
    parser.add_argument("--base-model")
    parser.add_argument("--load-in-4bit", action=argparse.BooleanOptionalAction, default=None)
    parser.add_argument("--max-seq-len", type=int)
    parser.add_argument("--batch-size", type=int)
    parser.add_argument("--max-new-tokens", type=int)
    parser.add_argument("--results", help="folder hasil evaluasi")
    parser.add_argument("--tag", help="nama run")
    parser.add_argument("--limit", type=int, help="hanya N soal pertama")
    parser.add_argument("--parallel", type=int, help="jumlah proses evaluasi")
    parser.add_argument("--demo", action="store_true", default=None, help="tanpa model, untuk menguji alur")
    args, _ = parser.parse_known_args(sys.argv[1:])  # di notebook sys.argv berisi argumen kernel
    for key, value in CONFIG.items():
        if getattr(args, key, None) is None:
            setattr(args, key, value)
    if not args.demo and args.adapter not in ("auto", "none") and not (Path(args.adapter) / "adapter_config.json").is_file():
        raise SystemExit(f"adapter tidak ditemukan: {args.adapter}\n"
                         "Pastikan Drive sudah di-mount, atau pilih adapter lain dengan --adapter <folder lora-adapter> "
                         "(atau --adapter auto / none).")
    return args


def check_evalplus():
    """Tolak EvalPlus yang selalu menggagalkan find_zero (HumanEval/32): skor akan turun satu soal tanpa alasan."""
    import inspect

    try:
        import evalplus.eval as ev
    except ImportError:
        raise SystemExit(f'evalplus belum terpasang: !pip install "{EVALPLUS_PIP}"')
    if re.search(r"_poly\(\*inp, out\)\) <= atol\s*\n\s*continue", inspect.getsource(ev.unsafe_execute)):
        raise SystemExit("evalplus yang terpasang (0.3.1 dari PyPI) selalu menilai HumanEval/32 gagal. Pasang versi "
                         f'yang sudah diperbaiki:\n  !pip install --force-reinstall --no-deps "{EVALPLUS_PIP}"')


def run_tag(args):
    if args.tag:
        return args.tag
    if args.demo:
        return "demo"
    if args.adapter == "none":
        return "model-dasar"
    if args.adapter == "auto":
        return "auto"
    folder = Path(args.adapter).parent  # .../<run>/lora-adapter
    # v3/qwen3.5-4b-own-4bit → "v3-qwen3.5-4b-own-4bit", supaya run lama yang diarsipkan tidak tertimpa.
    return f"{folder.parent.name}-{folder.name}" if folder.parent.name != Path(args.out).name else folder.name


def read_jsonl(path):
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def append_jsonl(path, rows):
    with path.open("a") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def extract_code(output, entry_point):
    """Kode dari jawaban model. Jawaban dimulai di dalam blok ```python dari prefiks respons."""
    from evalplus.sanitize import sanitize

    raw = output.split(FENCE)[0] if not output.lstrip().startswith(FENCE) else output
    try:
        code = sanitize(raw, entry_point)
    except Exception:  # sanitize gagal mem-parse: pakai teks mentah, biar tes yang menilai
        code = ""
    return code or raw


# ---------------------------------------------------------------- generate

class Generator:
    def __init__(self, args):
        self.args = args
        if args.demo:
            return
        sys.path.insert(0, str(HERE))
        try:
            import chat_gradio as cg
        except ImportError:
            print(f"chat_gradio.py tidak ditemukan, mengunduh ke {HERE} ...", flush=True)
            urllib.request.urlretrieve(CHAT_URL, HERE / "chat_gradio.py")
            import chat_gradio as cg
        self.engine = cg.Engine(argparse.Namespace(**{**vars(args), "demo": False}))
        tok = self.engine.tokenizer
        tok.padding_side = "left"  # generate berbatch: padding di kiri supaya token baru langsung menyambung
        if tok.pad_token is None:
            tok.pad_token = tok.eos_token
        self.stop_strings = True

    def prompt(self, task):
        messages = [{"role": "user", "content": f"{INSTRUCTION}\n{FENCE}\n{task['prompt'].strip()}\n{FENCE}"}]
        # Sama dengan teks training: template tanpa mode berpikir, lalu prefiks respons EvalPlus.
        return self.engine.render(messages, thinking=False) + f"{RESPONSE}\n{FENCE}python\n"

    def __call__(self, tasks):
        if self.args.demo:
            return [demo_answer(t, i) for i, t in enumerate(tasks)], 0
        torch, tok, model = self.engine.torch, self.engine.tokenizer, self.engine.model
        enc = tok([self.prompt(t) for t in tasks], return_tensors="pt", padding=True,
                  add_special_tokens=False).to(model.device)
        kwargs = dict(**enc, max_new_tokens=self.args.max_new_tokens, do_sample=False, repetition_penalty=1.0,
                      pad_token_id=tok.pad_token_id)
        with torch.inference_mode():
            if self.stop_strings:
                try:  # berhenti di penutup blok kode, jangan menunggu batas token
                    out = model.generate(**kwargs, stop_strings=["\n" + FENCE], tokenizer=tok)
                except (TypeError, ValueError) as e:
                    print(f"stop_strings tidak didukung ({e}); berhenti di token akhir saja", flush=True)
                    self.stop_strings = False
            if not self.stop_strings:
                out = model.generate(**kwargs)
        new = out[:, enc["input_ids"].shape[1]:]
        texts = tok.batch_decode(new, skip_special_tokens=True)
        return texts, int((new != tok.pad_token_id).sum())


def demo_answer(task, i):
    code = task["prompt"] + task["canonical_solution"]
    if task["_index"] % 7 == 0:  # sengaja salah, untuk memastikan kegagalan terdeteksi
        code = task["prompt"] + "    return None\n"
    return f"{code.rstrip()}\n{FENCE}\n\nPenjelasan singkat yang harus dibuang oleh ekstraksi."


# ---------------------------------------------------------------- evaluate

def evaluate(samples_path, problems, done_ids, parallel):
    result_path = samples_path.with_name("eval_results.json")
    result_path.unlink(missing_ok=True)  # evalplus memakai ulang hasil lama jika file ini ada
    cmd = [sys.executable, "-m", "evalplus.evaluate", "--dataset", "humaneval", "--samples", str(samples_path),
           "--output_file", str(result_path)]
    if parallel:
        cmd += ["--parallel", str(parallel)]
    print("\n$ " + " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True)  # proses terpisah: tidak ikut membawa model di GPU
    results = json.loads(result_path.read_text())["eval"]
    rows = []
    for task_id in done_ids:
        r = results[task_id][0]
        rows.append({"task_id": task_id, "base": r["base_status"] == "pass",
                     "plus": r["base_status"] == r["plus_status"] == "pass"})
    return rows


def summarize(rows, tag, args, gen_info, results_dir):
    n = len(rows)
    base = sum(r["base"] for r in rows)
    plus = sum(r["plus"] for r in rows)
    summary = {"tag": tag, "adapter": None if args.demo else args.adapter, "soal": n,
               "humaneval_pass@1": round(base / n, 4), "humaneval+_pass@1": round(plus / n, 4),
               "gagal_dasar": [r["task_id"] for r in rows if not r["base"]],
               "gagal_plus_saja": [r["task_id"] for r in rows if r["base"] and not r["plus"]], **gen_info}
    (results_dir / tag / "ringkasan.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"\n===== {tag}: {n} soal =====")
    print(f"HumanEval  pass@1: {base / n:6.1%}  ({base}/{n})")
    print(f"HumanEval+ pass@1: {plus / n:6.1%}  ({plus}/{n})")
    if summary["gagal_dasar"]:
        print("gagal tes dasar:", ", ".join(t.split("/")[1] for t in summary["gagal_dasar"]))
    if summary["gagal_plus_saja"]:
        print("lolos tes dasar, gagal tes tambahan:", ", ".join(t.split("/")[1] for t in summary["gagal_plus_saja"]))
    if args.limit:
        print(f"(hanya {n} soal karena --limit; skor ini belum bisa dibandingkan dengan skor 164 soal)")
    if "bench" in tag:
        print("PERINGATAN: adapter ini dilatih dengan soal HumanEval, jadi skornya mengukur hafalan (kontaminasi).")

    runs = [json.loads(p.read_text()) for p in sorted(results_dir.glob("*/ringkasan.json"))]
    if len(runs) > 1:
        print("\nPerbandingan semua run di", results_dir)
        print(f"| {'run':<40} | soal | HumanEval | HumanEval+ |")
        print(f"|{'-' * 42}|------|-----------|------------|")
        for s in runs:
            print(f"| {s['tag']:<40} | {s['soal']:>4} | {s['humaneval_pass@1']:>9.1%} | {s['humaneval+_pass@1']:>10.1%} |")


def main():
    args = parse_args()
    check_evalplus()
    from evalplus.data import get_human_eval_plus

    problems = get_human_eval_plus()
    tasks = [dict(t, _index=i) for i, t in enumerate(problems.values())]
    if args.limit:
        tasks = tasks[:args.limit]
    tag = run_tag(args)
    results_dir = Path(args.results)
    run_dir = results_dir / tag
    run_dir.mkdir(parents=True, exist_ok=True)
    responses_path = run_dir / "jawaban.jsonl"   # jawaban mentah model, untuk diperiksa manual
    print(f"run: {tag}\nfolder hasil: {run_dir}", flush=True)

    done = {r["task_id"]: r for r in read_jsonl(responses_path)}
    todo = [t for t in tasks if t["task_id"] not in done]
    if done:
        print(f"{len(done)} soal sudah dijawab sebelumnya, dilewati", flush=True)
    gen_info = {}
    if todo:
        generator = Generator(args)
        todo.sort(key=lambda t: len(t["prompt"]))  # prompt sepanjang mirip dalam satu batch: padding lebih sedikit
        start, n_tokens = time.time(), 0
        for i in range(0, len(todo), args.batch_size):
            batch = todo[i:i + args.batch_size]
            texts, tokens = generator(batch)
            n_tokens += tokens
            append_jsonl(responses_path, [{"task_id": t["task_id"], "output": o} for t, o in zip(batch, texts)])
            finished = i + len(batch)
            elapsed = time.time() - start
            eta = elapsed / finished * (len(todo) - finished)
            print(f"[{finished}/{len(todo)}] {elapsed / 60:.1f} menit, ±{eta / 60:.1f} menit lagi"
                  + (f", {n_tokens / elapsed:.0f} token/detik" if n_tokens else ""), flush=True)
        gen_info = {"menit_generate": round((time.time() - start) / 60, 1), "token_baru": n_tokens}
        done = {r["task_id"]: r for r in read_jsonl(responses_path)}

    # evalplus mewajibkan 164 soal: soal yang tidak dijawab (--limit) diisi kosong dan tidak ikut dihitung.
    done_ids = [t["task_id"] for t in tasks]
    samples_path = run_dir / "samples.jsonl"
    samples = [{"task_id": tid, "solution": extract_code(done[tid]["output"], problems[tid]["entry_point"])
                if tid in done_ids else ""} for tid in problems]
    samples_path.write_text("".join(json.dumps(s, ensure_ascii=False) + "\n" for s in samples))
    rows = evaluate(samples_path, problems, done_ids, args.parallel)
    summarize(rows, tag, args, gen_info, results_dir)


if __name__ == "__main__":
    main()
