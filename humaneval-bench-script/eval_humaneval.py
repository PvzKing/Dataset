"""Uji benchmark HumanEval/HumanEval+ atau MBPP/MBPP+ untuk model hasil fine-tuning (Qwen3.5-4B + adapter LoRA).

Soal, tes, dan penilaian memakai paket resmi EvalPlus (HumanEval+ v0.1.10, MBPP+ v0.2.0). Prompt memakai template chat
EvalPlus yang sama dengan sampel bench-support, dan jawaban dibuat dengan greedy decoding (pass@1, seperti leaderboard
EvalPlus). Pilih benchmark dengan --dataset humaneval (bawaan, 164 soal) atau --dataset mbpp (378 soal).

Secara bawaan ada dua run dengan satu kali muat model: adapter, lalu model dasar (adapter yang sama dimatikan
sementara, jadi bobot dasar dan kuantisasinya identik). Hasilnya dibandingkan per soal.

Langkah setiap run:
  1. Generate   soal dijawab per batch. Setiap batch langsung disimpan, jadi jika Colab terputus, jalankan ulang
                perintah yang sama dan soal yang sudah selesai dilewati.
  2. Sanitize   kode diambil dari jawaban dengan evalplus.sanitize, seperti pipeline resmi EvalPlus.
  3. Evaluate   evalplus.evaluate menjalankan tes dasar dan tes tambahan (HumanEval+ atau MBPP+).
  4. Ringkasan  skor dan soal yang gagal.
Lalu perbandingan: skor berdampingan, selisih, soal yang hanya lolos dengan adapter, dan soal yang hanya lolos di model
dasar (regresi), beserta uji McNemar untuk melihat apakah selisihnya nyata. Disimpan di perbandingan-<run>.json.

PENTING: adapter bench-lanjut dilatih dengan 164 soal HumanEval beserta jawabannya, jadi skornya terkontaminasi dan
tidak boleh dilaporkan sebagai skor kemampuan. Untuk perbandingan yang bersih, uji v3 atau adapter lain yang belum
pernah melihat soal ini.

Cara memakai di Google Colab (GPU T4 cukup):

    Sel 1:  !pip install --upgrade unsloth "evalplus @ git+https://github.com/evalplus/evalplus@26d6d00bb1fd0fa37f39c99d5290da67891d1c5e"
    Sel 2:  from google.colab import drive; drive.mount("/content/drive")
            REPO = "https://raw.githubusercontent.com/PvzKing/Dataset/main"
            !wget -q -O /content/eval_humaneval.py {REPO}/humaneval-bench-script/eval_humaneval.py
            !wget -q -O /content/chat_gradio.py {REPO}/scripts/chat_gradio.py
    Sel 3:  %run /content/eval_humaneval.py

Opsi bisa diganti lewat argumen, misalnya:

    %run /content/eval_humaneval.py --adapter /content/drive/MyDrive/finetune-id/v3/qwen3.5-4b-own-4bit/lora-adapter
    %run /content/eval_humaneval.py --dataset mbpp          # MBPP+ (378 soal), hasil di folder eval-mbpp
    %run /content/eval_humaneval.py --no-vs-base            # adapter saja, tanpa model dasar
    %run /content/eval_humaneval.py --limit 10              # uji cepat 10 soal
    %run /content/eval_humaneval.py --batch-size 4          # jika VRAM tidak cukup
    %run /content/eval_humaneval.py --demo                  # uji alur tanpa GPU: jawaban dari solusi resmi

EvalPlus dipasang dari commit master, bukan dari PyPI: versi 0.3.1 di PyPI selalu menilai HumanEval/32 (find_zero)
gagal, bahkan untuk solusi resminya, karena pemeriksa khususnya melompati pencatatan tes yang lolos. Script ini berhenti
jika versi yang terpasang masih membawa bug itu.

Model dimuat dengan kelas Engine dari chat_gradio.py: dicari di folder script ini, lalu di scripts/ repo ini, dan
diunduh otomatis jika tidak ada.
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
    "dataset": "humaneval",         # "humaneval" (164 soal) atau "mbpp" (378 soal)
    "results": None,                # None = <Drive>/finetune-id/eval-<dataset> di Colab, eval-<dataset> di tempat lain
    "tag": None,                    # nama run (subfolder hasil); default dari nama folder adapter
    "limit": None,                  # angka = hanya N soal pertama, untuk uji cepat
    "parallel": None,               # jumlah proses evaluasi; None = setengah jumlah CPU
    "vs_base": True,                # True = sekaligus uji model dasar (adapter dimatikan) dan bandingkan
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
NAMES = {"humaneval": ("HumanEval", "HumanEval+"), "mbpp": ("MBPP", "MBPP+")}
EVALPLUS_PIP = "evalplus @ git+https://github.com/evalplus/evalplus@26d6d00bb1fd0fa37f39c99d5290da67891d1c5e"


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--adapter", help='folder lora-adapter, "auto", atau "none"')
    parser.add_argument("--dataset", choices=sorted(NAMES))
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
    parser.add_argument("--vs-base", action=argparse.BooleanOptionalAction, default=None,
                        help="bandingkan dengan model dasar (bawaan: ya); --no-vs-base untuk adapter saja")
    parser.add_argument("--demo", action="store_true", default=None, help="tanpa model, untuk menguji alur")
    args, _ = parser.parse_known_args(sys.argv[1:])  # di notebook sys.argv berisi argumen kernel
    for key, value in CONFIG.items():
        if getattr(args, key, None) is None:
            setattr(args, key, value)
    if args.results is None:
        args.results = default_results(f"eval-{args.dataset}")
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


def default_results(name):
    return f"/content/drive/MyDrive/finetune-id/{name}" if Path("/content").is_dir() else name


def mcnemar_p(gained, lost):
    """Uji eksak McNemar dua sisi: seberapa mungkin selisih sebesar ini muncul hanya karena kebetulan."""
    from math import comb

    n, k = gained + lost, min(gained, lost)
    return 1.0 if n == 0 else min(1.0, 2 * sum(comb(n, i) for i in range(k + 1)) / 2 ** n)


def load_problems(dataset):
    if dataset == "mbpp":
        from evalplus.data import get_mbpp_plus
        return get_mbpp_plus()
    from evalplus.data import get_human_eval_plus
    return get_human_eval_plus()


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
    """Model dimuat sekali, lalu dipakai untuk run adapter dan run model dasar (adapter dimatikan sementara)."""

    def __init__(self, args):
        self.args = args
        self.ciri_terakhir = []  # per jawaban di generate terakhir: jumlah token, terpotong, berulang
        self.prompt_dicetak = False
        if args.demo:
            return
        for folder in (HERE.parent / "scripts", HERE):  # HERE terakhir disisipkan, jadi dicari lebih dulu
            if str(folder) not in sys.path:
                sys.path.insert(0, str(folder))
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

    def close(self):
        """Lepaskan model supaya memori GPU bisa dipakai uji berikutnya di sesi Colab yang sama."""
        self.engine = None
        free_gpu()

    @property
    def can_disable_adapter(self):
        return self.args.demo or (self.engine.has_adapter and hasattr(self.engine.model, "disable_adapter"))

    def prompt(self, task):
        messages = [{"role": "user", "content": f"{INSTRUCTION}\n{FENCE}\n{task['prompt'].strip()}\n{FENCE}"}]
        # Sama dengan teks training: template tanpa mode berpikir, lalu prefiks respons EvalPlus.
        return self.engine.render(messages, thinking=False) + f"{RESPONSE}\n{FENCE}python\n"

    def __call__(self, tasks, use_adapter=True):
        if self.args.demo:
            return [demo_answer(t, use_adapter, self.args.dataset) for t in tasks], 0
        return self.generate([self.prompt(t) for t in tasks], use_adapter, self.args.max_new_tokens,
                             stop_at_fence=True)

    def generate(self, prompts, use_adapter, max_new_tokens, stop_at_fence=False):
        """Greedy decoding berbatch untuk prompt yang sudah dirender. Kembalikan (teks, jumlah token baru)."""
        import contextlib

        torch, tok, model = self.engine.torch, self.engine.tokenizer, self.engine.model
        if not self.prompt_dicetak:  # untuk memastikan format prompt sama dengan teks training
            print(f"akhir prompt pertama: {prompts[0][-80:]!r}", flush=True)
            self.prompt_dicetak = True
        enc = tok(prompts, return_tensors="pt", padding=True, add_special_tokens=False).to(model.device)
        kwargs = dict(**enc, max_new_tokens=max_new_tokens, do_sample=False, repetition_penalty=1.0,
                      pad_token_id=tok.pad_token_id)
        adapter_off = contextlib.nullcontext() if use_adapter else model.disable_adapter()
        with adapter_off, torch.inference_mode():
            out = None
            if stop_at_fence and self.stop_strings:
                try:  # berhenti di penutup blok kode, jangan menunggu batas token
                    out = model.generate(**kwargs, stop_strings=["\n" + FENCE], tokenizer=tok)
                except (TypeError, ValueError) as e:
                    print(f"stop_strings tidak didukung ({e}); berhenti di token akhir saja", flush=True)
                    self.stop_strings = False
            if out is None:
                out = model.generate(**kwargs)
        new = out[:, enc["input_ids"].shape[1]:]
        texts = tok.batch_decode(new, skip_special_tokens=True)
        panjang = (new != tok.pad_token_id).sum(dim=1).tolist()
        self.ciri_terakhir = [{"token": n, "terpotong": n >= max_new_tokens, "berulang": berulang(t)}
                              for n, t in zip(panjang, texts)]
        return texts, int(sum(panjang))

    def ciri(self, texts):
        """Ciri jawaban generate terakhir untuk disimpan di jawaban.jsonl (kosong di mode demo)."""
        return self.ciri_terakhir if len(self.ciri_terakhir) == len(texts) else [{} for _ in texts]


def berulang(teks):
    """True jika jawaban berakhir dengan potongan yang sama diulang minimal 4 kali sepanjang minimal 200 karakter:
    tanda greedy decoding terjebak. Penutup wajar seperti beberapa </div> berturut-turut tidak sepanjang itu."""
    ekor = teks[-4000:]
    for n in range(1, 400):
        ulang = max(4, -(-200 // n))
        if len(ekor) >= n * ulang and ekor.endswith(ekor[-n:] * ulang):
            return True
    return False


def ciri_run(rows):
    """Jumlah jawaban yang terpotong di batas token dan yang berulang, dari baris jawaban.jsonl."""
    rows = [r for r in rows if "token" in r]
    if not rows:
        return {}
    return {"terpotong": sum(r["terpotong"] for r in rows), "berulang": sum(r["berulang"] for r in rows),
            "token_maks": max(r["token"] for r in rows)}


def cetak_ciri(ciri, n):
    if "terpotong" in ciri:
        print(f"jawaban terpotong di batas token: {ciri['terpotong']}/{n}, berulang: {ciri['berulang']}/{n}, "
              f"jawaban terpanjang: {ciri['token_maks']} token")


def free_gpu():
    import gc

    gc.collect()
    torch = sys.modules.get("torch")
    if torch is not None and torch.cuda.is_available():
        torch.cuda.empty_cache()


def demo_answer(task, use_adapter, dataset="humaneval"):
    # Sengaja salah supaya kegagalan dan perbedaan antarmodel terlihat: "adapter" tiap soal ke-7, "dasar" tiap ke-5.
    # Prompt HumanEval berisi signature, jadi solusinya disambung; solusi MBPP sudah berupa kode lengkap.
    code = task["prompt"] + task["canonical_solution"] if dataset == "humaneval" else task["canonical_solution"]
    if task["_index"] % (7 if use_adapter else 5) == 0:
        code = f"def {task['entry_point']}(*args, **kwargs):\n    return None\n"
    return f"{code.rstrip()}\n{FENCE}\n\nPenjelasan singkat yang harus dibuang oleh ekstraksi."


# ---------------------------------------------------------------- evaluate

def evaluate(samples_path, problems, done_ids, parallel, dataset="humaneval"):
    result_path = samples_path.with_name("eval_results.json")
    result_path.unlink(missing_ok=True)  # evalplus memakai ulang hasil lama jika file ini ada
    cmd = [sys.executable, "-m", "evalplus.evaluate", "--dataset", dataset, "--samples", str(samples_path),
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


def score_keys(dataset):
    return [f"{name.lower()}_pass@1" for name in NAMES[dataset]]


def summarize(rows, tag, model_label, args, gen_info, results_dir):
    n = len(rows)
    base = sum(r["base"] for r in rows)
    plus = sum(r["plus"] for r in rows)
    name, name_plus = NAMES[args.dataset]
    key, key_plus = score_keys(args.dataset)
    summary = {"tag": tag, "model": model_label, "dataset": args.dataset, "soal": n,
               key: round(base / n, 6), key_plus: round(plus / n, 6),
               "gagal_dasar": [r["task_id"] for r in rows if not r["base"]],
               "gagal_plus_saja": [r["task_id"] for r in rows if r["base"] and not r["plus"]], **gen_info}
    (results_dir / tag / "ringkasan.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"\n===== {tag}: {n} soal =====")
    print(f"{name + ' ':<11}pass@1: {base / n:6.1%}  ({base}/{n})")
    print(f"{name_plus:<11}pass@1: {plus / n:6.1%}  ({plus}/{n})")
    if summary["gagal_dasar"]:
        print("gagal tes dasar:", short_ids(summary["gagal_dasar"]))
    if summary["gagal_plus_saja"]:
        print("lolos tes dasar, gagal tes tambahan:", short_ids(summary["gagal_plus_saja"]))
    cetak_ciri(summary, n)
    if args.limit:
        print(f"(hanya {n} soal karena --limit; skor ini belum bisa dibandingkan dengan skor semua soal)")
    if "bench" in tag and args.dataset == "humaneval":
        print("PERINGATAN: adapter ini dilatih dengan soal HumanEval: skornya terkontaminasi, bukan skor kemampuan.")
    return summary


def short_ids(task_ids):
    return ", ".join(t.split("/")[1] for t in task_ids) or "-"


def compare(adapter_rows, base_rows, adapter_tag, base_tag, results_dir, names=NAMES["humaneval"],
            short=None):
    """Skor berdampingan dan soal yang berubah status antara model dasar dan adapter, dengan uji McNemar."""
    short = short or short_ids
    n = len(adapter_rows)
    base_by_id = {r["task_id"]: r for r in base_rows}
    report = {"adapter": adapter_tag, "model_dasar": base_tag, "soal": n}
    keys = [k for k in ("base", "plus") if k in adapter_rows[0]][:len(names)]
    print(f"\n===== Perbandingan dengan model dasar ({n} soal) =====")
    print(f"| {'model':<40} |" + "|".join(f" {nm:>10} " for nm in names[:len(keys)]) + "|")
    print(f"|{'-' * 42}|" + "|".join("-" * 12 for _ in keys) + "|")
    for label, rows in ((adapter_tag, adapter_rows), (base_tag, base_rows)):
        print(f"| {label:<40} |" + "|".join(f" {sum(r[k] for r in rows) / n:>10.1%} " for k in keys) + "|")
    for key, name in zip(keys, names):
        diff = sum(r[key] for r in adapter_rows) - sum(r[key] for r in base_rows)
        gained = [r["task_id"] for r in adapter_rows if r[key] and not base_by_id[r["task_id"]][key]]
        lost = [r["task_id"] for r in adapter_rows if not r[key] and base_by_id[r["task_id"]][key]]
        p = mcnemar_p(len(gained), len(lost))
        report[name] = {"selisih_soal": diff, "selisih_poin_persen": round(diff / n * 100, 1), "p_mcnemar": round(p, 4),
                        "hanya_lolos_dengan_adapter": gained, "hanya_lolos_di_model_dasar": lost}
        verdict = "nyata (p < 0,05)" if p < 0.05 else "belum nyata, bisa kebetulan"
        print(f"\n{name}: selisih {diff:+d} soal ({diff / n * 100:+.1f} poin persen), McNemar p = {p:.3f}: {verdict}")
        print(f"  hanya lolos dengan adapter ({len(gained)}): {short(gained)}")
        print(f"  hanya lolos di model dasar, regresi ({len(lost)}): {short(lost)}")
    path = results_dir / f"perbandingan-{adapter_tag}.json"
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"\ndisimpan di {path}")
    if "bench" in adapter_tag and names == NAMES["humaneval"]:
        print("Ingat: adapter bench sudah melihat soal ini, jadi selisihnya bukan ukuran kemampuan.")
    return report


def print_all_runs(results_dir, dataset="humaneval"):
    runs = [json.loads(p.read_text()) for p in sorted(results_dir.glob("*/ringkasan.json"))]
    runs = [r for r in runs if r.get("dataset", "humaneval") == dataset]
    if len(runs) > 1:
        name, name_plus = NAMES[dataset]
        key, key_plus = score_keys(dataset)
        print("\nSemua run di", results_dir)
        print(f"| {'run':<40} | soal | {name:>10} | {name_plus:>10} |")
        print(f"|{'-' * 42}|------|------------|------------|")
        for s in runs:
            print(f"| {s['tag']:<40} | {s['soal']:>4} | {s[key]:>10.1%} | {s[key_plus]:>10.1%} |")


# ---------------------------------------------------------------- run

def run_one(args, tag, model_label, use_adapter, tasks, problems, results_dir, get_generator):
    run_dir = results_dir / tag
    run_dir.mkdir(parents=True, exist_ok=True)
    responses_path = run_dir / "jawaban.jsonl"   # jawaban mentah model, untuk diperiksa manual
    print(f"\n##### run: {tag} ({model_label})\nfolder hasil: {run_dir}", flush=True)

    done = {r["task_id"]: r for r in read_jsonl(responses_path)}
    todo = [t for t in tasks if t["task_id"] not in done]
    if done:
        print(f"{len(done)} soal sudah dijawab sebelumnya, dilewati", flush=True)
    gen_info = {}
    if todo:
        generator = get_generator()
        todo.sort(key=lambda t: len(t["prompt"]))  # prompt sepanjang mirip dalam satu batch: padding lebih sedikit
        start, n_tokens = time.time(), 0
        for i in range(0, len(todo), args.batch_size):
            batch = todo[i:i + args.batch_size]
            texts, tokens = generator(batch, use_adapter)
            n_tokens += tokens
            ciri = generator.ciri(texts) if hasattr(generator, "ciri") else [{} for _ in texts]
            append_jsonl(responses_path, [{"task_id": t["task_id"], "output": o, **c}
                                          for t, o, c in zip(batch, texts, ciri)])
            finished = i + len(batch)
            elapsed = time.time() - start
            eta = elapsed / finished * (len(todo) - finished)
            print(f"[{tag}] {finished}/{len(todo)} soal, {elapsed / 60:.1f} menit, ±{eta / 60:.1f} menit lagi"
                  + (f", {n_tokens / elapsed:.0f} token/detik" if n_tokens else ""), flush=True)
        gen_info = {"menit_generate": round((time.time() - start) / 60, 1), "token_baru": n_tokens}
        done = {r["task_id"]: r for r in read_jsonl(responses_path)}

    # evalplus mewajibkan semua soal: soal yang tidak dijawab (--limit) diisi kosong dan tidak ikut dihitung.
    done_ids = [t["task_id"] for t in tasks]
    samples_path = run_dir / "samples.jsonl"
    samples = [{"task_id": tid, "solution": extract_code(done[tid]["output"], problems[tid]["entry_point"])
                if tid in done_ids else ""} for tid in problems]
    samples_path.write_text("".join(json.dumps(s, ensure_ascii=False) + "\n" for s in samples))
    rows = evaluate(samples_path, problems, done_ids, args.parallel, args.dataset)
    gen_info = {**gen_info, **ciri_run([done[t] for t in done_ids if t in done])}
    summarize(rows, tag, model_label, args, gen_info, results_dir)
    return rows


def main():
    args = parse_args()
    check_evalplus()
    problems = load_problems(args.dataset)
    tasks = [dict(t, _index=i) for i, t in enumerate(problems.values())]
    if args.limit:
        tasks = tasks[:args.limit]
    results_dir = Path(args.results)
    generator = None

    def get_generator():  # model baru dimuat jika ada soal yang belum dijawab
        nonlocal generator
        if generator is None:
            generator = Generator(args)
        return generator

    try:
        tag = run_tag(args)
        vs_base = args.vs_base and args.adapter != "none"
        adapter_label = "demo" if args.demo else ("model dasar" if args.adapter == "none" else args.adapter)
        rows = run_one(args, tag, adapter_label, True, tasks, problems, results_dir, get_generator)
        if vs_base:
            # --tag dan --demo mendapat folder model dasar sendiri, supaya jawaban tiruan atau uji cepat tidak terpakai
            # ulang oleh run sungguhan.
            prefix = args.tag or ("demo" if args.demo else "")
            base_tag = f"{prefix}-model-dasar" if prefix else "model-dasar"
            # Jawaban model dasar tidak bergantung pada adapter, jadi dipakai ulang oleh run adapter mana pun.
            if any(t["task_id"] not in {r["task_id"] for r in read_jsonl(results_dir / base_tag / "jawaban.jsonl")}
                   for t in tasks) and not get_generator().can_disable_adapter:
                raise SystemExit("model ini tidak bisa mematikan adapter sementara; jalankan run terpisah dengan "
                                 "--adapter none untuk model dasar")
            base_rows = run_one(args, base_tag, f"{args.base_model} (adapter dimatikan)", False, tasks, problems,
                                results_dir, get_generator)
            compare(rows, base_rows, tag, base_tag, results_dir, NAMES[args.dataset])
        print_all_runs(results_dir, args.dataset)
    finally:
        if generator is not None:  # lepaskan VRAM supaya uji berikutnya di sesi yang sama punya memori penuh
            generator.close()
        free_gpu()


if __name__ == "__main__":
    main()
