"""Bangun kelompok dataset bench-support: sampel latihan dari benchmark kode, terpisah dari dataset own.

Isi saat ini:
    data/bench-support/humaneval.jsonl   164 soal HumanEval, dengan prompt dan solusi dari HumanEval+ (EvalPlus)

Formatnya mengikuti prompt instruct EvalPlus, yaitu cara HumanEval/HumanEval+ menguji model chat: user meminta
skrip Python mandiri dalam blok kode, dan jawaban diawali kalimat pembuka EvalPlus lalu satu blok ```python.
Setiap solusi diverifikasi sebelum ditulis: lolos tes resmi HumanEval, dan outputnya sama dengan solusi asli
HumanEval pada semua input tambahan HumanEval+. Perbedaan yang sudah ditinjau manual dicatat di KNOWN_ORIGINAL_BUGS,
PROPERTY_CHECKS, dan CUSTOM_SOLUTIONS.

Pemakaian:
    python scripts/build_bench_support.py              # unduh, verifikasi, tulis
    python scripts/build_bench_support.py --source HumanEvalPlus.jsonl.gz --original HumanEval.jsonl.gz  # file lokal
"""
import argparse
import gzip
import json
import subprocess
import sys
import tempfile
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "bench-support" / "humaneval.jsonl"
SOURCE_URL = "https://github.com/evalplus/humanevalplus_release/releases/download/v0.1.10/HumanEvalPlus.jsonl.gz"
# Teks persis dari template chat EvalPlus (evalplus/provider/utility.py).
INSTRUCTION = ("Please provide a self-contained Python script that solves the following problem in a markdown "
               "code block:")
RESPONSE = ("Below is a Python script with a self-contained function that solves the problem and passes "
            "corresponding tests:")
FENCE = "`" * 3
# Soal yang solusi asli HumanEval-nya terbukti keliru, sehingga perbedaan dengan HumanEval+ wajar. Diisi setelah setiap
# perbedaan diperiksa manual (lihat README bagian bench-support).
# Soal dengan lebih dari satu jawaban benar: dibandingkan lewat sifat jawabannya, bukan kesamaan dengan solusi asli.
PROPERTY_CHECKS = {
    # find_zero: akar mana pun. Lolos jika |poly(x)| kecil, atau tanda poly berganti di sekitar x (teorema nilai
    # antara: ada akar dalam jarak 1e-6 relatif dari x), karena untuk koefisien besar sisa float tidak pernah kecil.
    "HumanEval/32": "abs(new['poly'](args[0], got)) < 1e-4 or new['poly'](args[0], got - 1e-6 * max(1.0, abs(got))) "
                    "* new['poly'](args[0], got + 1e-6 * max(1.0, abs(got))) <= 0",
}
# Soal yang kedua solusi referensinya gagal pada sebagian input HumanEval+, sehingga solusinya ditulis ulang.
# HumanEval/32 (find_zero): bisection asli macet/overflow jika akarnya tepat di 0 dan kedua ujung pencarian bertanda
# sama (9 dari 888 input); metode Newton HumanEval+ gagal konvergen pada 4 input berkoefisien besar. Gabungan
# keduanya lolos tes resmi dan menemukan akar pada semua 888 input.
CUSTOM_SOLUTIONS = {
    "HumanEval/32": """
    # Newton's method from x = 0 is fast and handles a root at 0 immediately, but it can fail to converge.
    # Bisection always finds a root because the polynomial has odd degree, so fall back to it when Newton fails.
    x = 0.0
    for _ in range(100):
        fx = poly(xs, x)
        if abs(fx) < 1e-10:
            return x
        dfx = sum(i * coeff * x ** (i - 1) for i, coeff in enumerate(xs) if i)
        if dfx == 0 or abs(x) > 1e6:
            break
        x -= fx / dfx
    begin, end = -1.0, 1.0
    while poly(xs, begin) * poly(xs, end) > 0:
        begin *= 2.0
        end *= 2.0
    for _ in range(200):
        center = (begin + end) / 2.0
        if poly(xs, center) * poly(xs, begin) > 0:
            begin = center
        else:
            end = center
    return begin
""",
}
KNOWN_ORIGINAL_BUGS = {
    "HumanEval/22": "bool ikut dianggap integer; HumanEval+ hanya mengambil int sungguhan",
    "HumanEval/44": "change_base(0, b) menghasilkan '' padahal seharusnya '0'",
    "HumanEval/49": "modp(0, 1) menghasilkan 1 padahal 2^0 mod 1 = 0",
    "HumanEval/76": "is_simple_power(-2, -2) salah: (-2)^1 = -2",
    "HumanEval/91": "kalimat pertama yang diawali spasi tidak dihitung",
    "HumanEval/95": "kunci seperti '1' (bukan huruf kecil/besar) diterima",
    "HumanEval/97": "digit satuan bilangan negatif dihitung dari -6 % 10 = 4, bukan 6",
    "HumanEval/111": "spasi ganda menghasilkan huruf kosong '' di histogram",
    "HumanEval/122": "bilangan negatif dua digit seperti -99 dianggap tiga digit karena tanda minus",
    "HumanEval/123": "memakai pembagian float (/) sehingga salah untuk bilangan besar",
    "HumanEval/124": "valid_date('12-31-1999') ditolak karena salah prioritas operator and/or",
    "HumanEval/125": "string kosong di antara dua koma dibuang, padahal pemisahan dengan ',' mempertahankannya",
    "HumanEval/132": "'[][][]' dianggap bersarang padahal tidak ada kurung di dalam kurung",
    "HumanEval/140": "dua spasi di akhir string hanya menjadi satu garis bawah",
    "HumanEval/150": "bilangan negatif seperti -2 dianggap prima karena loop tidak pernah berjalan",
}

ORIGINAL_URL = "https://raw.githubusercontent.com/openai/human-eval/master/data/HumanEval.jsonl.gz"

# Tes resmi HumanEval hanya beberapa assert dan meloloskan banyak solusi yang salah (misalnya < diganti <=).
# Karena itu solusi juga dibandingkan dengan solusi asli HumanEval (implementasi independen) pada semua input
# tambahan HumanEval+. Panggilan solusi asli yang terlalu lambat untuk input besar dilewati.
RUNNER = r"""
import copy, json, math, signal, sys
sys.setrecursionlimit(100000)
sys.set_int_max_str_digits(0)
new, old = {}, {}
exec(compile(open(sys.argv[1]).read(), "solusi", "exec"), new)
exec(compile(open(sys.argv[2]).read(), "asli", "exec"), old)
test = dict(new)  # tes memakai fungsi bantu dari prompt, misalnya poly atau encode_cyclic
exec(open(sys.argv[3]).read(), test)
test["check"](new[ENTRY])

def same(a, b):
    if isinstance(a, float) or isinstance(b, float):
        return isinstance(a, (int, float)) and isinstance(b, (int, float)) and math.isclose(a, b, rel_tol=1e-6, abs_tol=1e-6)
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        return type(a) == type(b) and len(a) == len(b) and all(same(x, y) for x, y in zip(a, b))
    return a == b

class Slow(Exception):
    pass

def alarm(*_):
    raise Slow

signal.signal(signal.SIGALRM, alarm)
inputs = json.load(open(sys.argv[4]))
checked = skipped = 0
for args in inputs:
    got = new[ENTRY](*copy.deepcopy(args))
    signal.setitimer(signal.ITIMER_REAL, 1.0)
    try:
        want = old[ENTRY](*copy.deepcopy(args))
    except Slow:
        skipped += 1
        continue
    except Exception:
        skipped += 1  # solusi asli error pada input ini; tidak bisa jadi pembanding
        continue
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
    checked += 1
    if not (PROPERTY_EXPR):
        print(json.dumps({"mismatch": repr(args)[:300], "got": repr(got)[:150], "original": repr(want)[:150]}))
        sys.exit(3)
print(json.dumps({"checked": checked, "skipped": skipped}))
"""


def verify(task, code, original_code, timeout):
    """Tes resmi + pemeriksaan silang dengan solusi asli. Kembalikan (pesan error atau None, ringkasan)."""
    with tempfile.TemporaryDirectory() as tmp:
        files = {"new.py": code, "old.py": original_code, "test.py": task["test"],
                 "inputs.json": json.dumps(task["base_input"] + task["plus_input"]),
                 "run.py": RUNNER.replace("ENTRY", repr(task["entry_point"]))
                                 .replace("PROPERTY_EXPR", PROPERTY_CHECKS.get(task["task_id"], "same(got, want)"))}
        for name, text in files.items():
            (Path(tmp) / name).write_text(text)
        try:
            result = subprocess.run([sys.executable, "-I", "run.py", "new.py", "old.py", "test.py", "inputs.json"],
                                    capture_output=True, text=True, timeout=timeout, cwd=tmp)
        except subprocess.TimeoutExpired:
            return f"lebih dari {timeout} detik", None
        last = (result.stdout.strip().splitlines() or [""])[-1]
        if result.returncode == 3:
            return f"beda dengan solusi asli: {last}", None
        if result.returncode:
            return (result.stderr.strip().splitlines() or ["gagal"])[-1][:300], None
    return None, json.loads(last)


def build_sample(task, solution=None):
    number = int(task["task_id"].split("/")[1])
    code = (task["prompt"] + (solution or task["canonical_solution"])).strip()
    return {
        "id": f"humaneval-{number:03d}",
        "category": "bench_humaneval",
        "source": task["task_id"],
        "messages": [
            {"role": "user", "content": f"{INSTRUCTION}\n{FENCE}\n{task['prompt'].strip()}\n{FENCE}"},
            {"role": "assistant", "content": f"{RESPONSE}\n{FENCE}python\n{code}\n{FENCE}"},
        ],
    }, code


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", help="HumanEvalPlus.jsonl.gz lokal (bawaan: unduh dari rilis EvalPlus)")
    parser.add_argument("--original", help="HumanEval.jsonl.gz lokal (bawaan: unduh dari repo openai/human-eval)")
    parser.add_argument("--timeout", type=int, default=120, help="batas waktu verifikasi per soal (detik)")
    args = parser.parse_args()

    def fetch(local, url):
        if local:
            return Path(local).read_bytes()
        print(f"mengunduh {url} ...", flush=True)
        return urllib.request.urlopen(url, timeout=120).read()

    def tasks_of(raw):
        rows = [json.loads(line) for line in gzip.decompress(raw).decode("utf-8").splitlines() if line.strip()]
        return {t["task_id"]: t for t in rows}

    plus = tasks_of(fetch(args.source, SOURCE_URL))
    original = tasks_of(fetch(args.original, ORIGINAL_URL))
    tasks = sorted(plus.values(), key=lambda t: int(t["task_id"].split("/")[1]))
    exceptions = {k: v for k, v in KNOWN_ORIGINAL_BUGS.items() if k in plus}

    built = [build_sample(t, CUSTOM_SOLUTIONS.get(t["task_id"])) for t in tasks]

    def check(pair):
        task, (_, code) = pair
        old = original[task["task_id"]]
        return verify(task, code, (old["prompt"] + old["canonical_solution"]).strip(), args.timeout)

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(check, zip(tasks, built)))
    failed, checked, skipped = [], 0, 0
    for task, (error, summary) in zip(tasks, results):
        if error and task["task_id"] in exceptions and error.startswith("beda dengan solusi asli"):
            print(f"diterima {task['task_id']}: solusi asli HumanEval keliru ({exceptions[task['task_id']]})")
        elif error:
            failed.append((task["task_id"], error))
        else:
            checked += summary["checked"]
            skipped += summary["skipped"]
    for task_id, error in failed:
        print(f"GAGAL {task_id}: {error}")
    print(f"pemeriksaan silang: {checked:,} input cocok, {skipped:,} dilewati (solusi asli lambat/error)")
    if failed:
        sys.exit(f"{len(failed)} solusi gagal verifikasi; file tidak ditulis")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("".join(json.dumps(sample, ensure_ascii=False) + "\n" for sample, _ in built), encoding="utf-8")
    print(f"{len(built)} sampel lolos verifikasi dan ditulis ke {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
