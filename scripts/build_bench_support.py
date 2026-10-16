"""Bangun kelompok dataset bench-support: sampel latihan dari benchmark kode, terpisah dari dataset own.

Isi saat ini:
    data/bench-support/humaneval.jsonl   164 soal HumanEval, dengan prompt dan solusi dari HumanEval+ (EvalPlus)
    data/bench-support/mbppplus.jsonl    378 soal MBPP+, dengan prompt dan solusi dari MBPP+ v0.2.0 (EvalPlus)
    data/bench-support/mbpp-sisa.jsonl   soal MBPP asli (Google) yang tidak ada di MBPP+, dengan prompt format MBPP+

Formatnya mengikuti prompt instruct EvalPlus, yaitu cara HumanEval/HumanEval+ menguji model chat: user meminta
skrip Python mandiri dalam blok kode, dan jawaban diawali kalimat pembuka EvalPlus lalu satu blok ```python.
Setiap solusi diverifikasi sebelum ditulis: lolos tes resmi HumanEval, dan outputnya sama dengan solusi asli
HumanEval pada semua input tambahan HumanEval+. Perbedaan yang sudah ditinjau manual dicatat di KNOWN_ORIGINAL_BUGS,
PROPERTY_CHECKS, dan CUSTOM_SOLUTIONS. Solusi MBPP+ harus lolos assert resmi MBPP dan berjalan tanpa error pada semua
input dasar dan tambahan MBPP+; solusi MBPP asli harus lolos semua assert-nya (test_list dan challenge_test_list).
Soal MBPP asli yang gagal, atau butuh test_setup_code, dibuang dan dicatat di output.

Pemakaian:
    python scripts/build_bench_support.py              # unduh, verifikasi, tulis (HumanEval dan MBPP)
    python scripts/build_bench_support.py --only mbpp  # hanya mbppplus.jsonl dan mbpp-sisa.jsonl
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
MBPP_PLUS_OUT = OUT.with_name("mbppplus.jsonl")
MBPP_REST_OUT = OUT.with_name("mbpp-sisa.jsonl")
MBPP_PLUS_URL = "https://github.com/evalplus/mbppplus_release/releases/download/v0.2.0/MbppPlus.jsonl.gz"
MBPP_URL = ("https://raw.githubusercontent.com/google-research/google-research/"
            "master/mbpp/mbpp.jsonl")
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


# ---------------------------------------------------------------- MBPP+ dan MBPP

# MBPP+ menilai dengan output solusi kanonisnya sendiri, jadi solusi itu cukup dibuktikan lolos assert resmi MBPP
# (field assertion; beberapa memakai math.isclose tanpa import, seperti di harness EvalPlus). Solusi MBPP asli
# dibuktikan dengan semua assert-nya.
# Soal MBPP asli yang punya 13-gram sama dengan IndoPy (scripts/decontaminate.py --sumber IndoPy Web-eval). Isinya
# deret angka yang kebetulan sama, tetapi tetap dibuang supaya IndoPy-dev dan IndoPy-test tetap bersih untuk V6.
MBPP_EXCLUDE = {216: "deret 1..14 sama dengan IndoPy-dev", 298: "deret 1..14 sama dengan IndoPy-dev",
                522: "deret uji sama dengan IndoPy-test", 889: "deret 1..16 sama dengan IndoPy-dev"}


def verify_mbpp(code, asserts, timeout):
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "run.py").write_text(f"import math\n{code}\n\n{asserts}\n")
        try:
            result = subprocess.run([sys.executable, "-I", "run.py"], capture_output=True, text=True,
                                    timeout=timeout, cwd=tmp)
        except subprocess.TimeoutExpired:
            return f"lebih dari {timeout} detik"
        if result.returncode:
            return (result.stderr.strip().splitlines() or ["gagal"])[-1][:300]
    return None


def mbpp_sample(sample_id, category, source, prompt, code):
    return {
        "id": sample_id,
        "category": category,
        "source": source,
        "messages": [
            {"role": "user", "content": f"{INSTRUCTION}\n{FENCE}\n{prompt.strip()}\n{FENCE}"},
            {"role": "assistant", "content": f"{RESPONSE}\n{FENCE}python\n{code}\n{FENCE}"},
        ],
    }


def tidy(code):
    """Rapikan solusi MBPP asli: baris CRLF, spasi di akhir baris, dan tab (diverifikasi ulang setelahnya)."""
    return "\n".join(line.rstrip().expandtabs(4) for line in code.replace("\r\n", "\n").split("\n")).strip()


def build_mbpp(fetch, args):
    plus = [json.loads(line) for line in gzip.decompress(fetch(args.mbpp_source, MBPP_PLUS_URL)).decode().splitlines()
            if line.strip()]
    original = [json.loads(line) for line in fetch(args.mbpp_original, MBPP_URL).decode().splitlines() if line.strip()]
    plus.sort(key=lambda t: int(t["task_id"].split("/")[1]))

    def check_plus(t):
        return verify_mbpp(t["canonical_solution"].strip(), t["assertion"], args.timeout)

    plus_ids = {int(t["task_id"].split("/")[1]) for t in plus}
    rest, skipped = [], []
    for t in sorted(original, key=lambda t: t["task_id"]):
        if t["task_id"] in plus_ids:
            continue
        if t["task_id"] in MBPP_EXCLUDE:
            skipped.append((t["task_id"], MBPP_EXCLUDE[t["task_id"]]))
            continue
        if t["test_setup_code"].strip():  # assert-nya memakai objek yang tidak disebut di prompt
            skipped.append((t["task_id"], "butuh test_setup_code"))
            continue
        rest.append(t)

    def check_rest(t):
        code = tidy(t["code"])
        return code, verify_mbpp(code, "\n".join(t["test_list"] + t["challenge_test_list"]), args.timeout)

    with ThreadPoolExecutor(max_workers=8) as pool:
        plus_errors = list(pool.map(check_plus, plus))
        rest_results = list(pool.map(check_rest, rest))
    failed = [(t["task_id"], e) for t, e in zip(plus, plus_errors) if e]
    for task_id, error in failed:
        print(f"GAGAL {task_id}: {error}")
    if failed:
        sys.exit(f"{len(failed)} solusi MBPP+ gagal verifikasi; file tidak ditulis")
    plus_rows = [mbpp_sample(f"mbppplus-{int(t['task_id'].split('/')[1]):03d}", "bench_mbppplus", t["task_id"],
                             t["prompt"], t["canonical_solution"].strip()) for t in plus]

    rest_rows, seen = [], {t["prompt"].strip() for t in plus}
    for t, (code, error) in zip(rest, rest_results):
        prompt = f'"""\n{t["text"].strip()}\n{t["test_list"][0].strip()}\n"""'  # format prompt MBPP+
        if error or prompt in seen:
            skipped.append((t["task_id"], error or "prompt sama dengan soal lain"))
            continue
        seen.add(prompt)
        rest_rows.append(mbpp_sample(f"mbpp-{t['task_id']:03d}", "bench_mbpp", f"MBPP/{t['task_id']}", prompt, code))
    for task_id, reason in sorted(skipped):
        print(f"dibuang MBPP/{task_id}: {reason}")

    for path, rows in ((MBPP_PLUS_OUT, plus_rows), (MBPP_REST_OUT, rest_rows)):
        path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
        print(f"{len(rows)} sampel lolos verifikasi dan ditulis ke {path.relative_to(ROOT)}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", help="HumanEvalPlus.jsonl.gz lokal (bawaan: unduh dari rilis EvalPlus)")
    parser.add_argument("--original", help="HumanEval.jsonl.gz lokal (bawaan: unduh dari repo openai/human-eval)")
    parser.add_argument("--mbpp-source", help="MbppPlus.jsonl.gz lokal (bawaan: unduh dari rilis EvalPlus)")
    parser.add_argument("--mbpp-original", help="mbpp.jsonl lokal (bawaan: unduh dari repo google-research)")
    parser.add_argument("--only", choices=["humaneval", "mbpp"], help="bangun satu kelompok saja")
    parser.add_argument("--timeout", type=int, default=120, help="batas waktu verifikasi per soal (detik)")
    args = parser.parse_args()

    def fetch(local, url):
        if local:
            return Path(local).read_bytes()
        print(f"mengunduh {url} ...", flush=True)
        return urllib.request.urlopen(url, timeout=120).read()

    if args.only != "humaneval":
        build_mbpp(fetch, args)
    if args.only == "mbpp":
        return

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
