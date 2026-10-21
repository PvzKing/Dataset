"""Sulingan: data latihan dari jawaban model dasar sendiri yang lolos pemeriksaan otomatis (rejection sampling).

Model dasar (Qwen3.5-4B tanpa adapter) menjawab setiap soal beberapa kali dengan sampling. Hanya jawaban yang lolos
pemeriksaan otomatis yang disimpan, lalu dilatih bersama data/train.jsonl. Tujuannya mencegah yang terjadi di V6:
  - Jawaban berasal dari model itu sendiri, jadi bobotnya tidak dipaksa bergeser jauh dan kemampuan umumnya tidak
    terkikis. Yang dipelajari adalah memilih jawaban yang benar (yang lolos tes), bukan menghafal teks orang lain.
  - Soal benchmark yang dipakai untuk menilai (HumanEval+, MBPP+, IndoPy, Web-eval) tidak ikut, jadi keempatnya tetap
    bersih dan bisa dipakai untuk membandingkan V7 dengan model dasar secara jujur.
  - Instruksi gaya (bahasa Indonesia, bagian **Cek kebutuhan**) hanya ada di system prompt saat membuat jawaban, dan
    tidak ikut disimpan. Model belajar menjawab dengan gaya itu tanpa perlu diberi instruksi (context distillation).

Dua sumber soal:
  python  soal MBPP yang TIDAK masuk MBPP+ (589 soal di data/bench-support/mbpp-sisa.jsonl; split latihan MBPP), dalam
          pembungkus permintaan berbahasa Indonesia. Lolos jika kodenya lulus semua assert resmi MBPP, jawabannya
          tidak terpotong, dan ada penjelasan di luar kode.
  web     40 prompt website di data/sulingan/prompt-web.jsonl. Lolos jika di Chromium: dokumen HTML lengkap, tanpa
          error JavaScript saat dibuka dan saat semua input diisi serta semua tombol diklik, halamannya berubah
          setelah dipakai (tombol benar-benar terpasang), tanpa scroll horizontal di layar 375 px, menyimpan ke
          localStorage jika diminta, dan ada bagian **Cek kebutuhan**.

Pemakaian (di Colab, dari clone repo; model dimuat 16-bit tanpa kuantisasi):
    python scripts/sulingan.py python --out <folder>        # kandidat-python.jsonl (bisa dilanjutkan jika terputus)
    python scripts/sulingan.py web --out <folder>           # kandidat-web.jsonl
    python scripts/sulingan.py gabung --out <folder> --hasil <folder>/train_v7.jsonl
    python scripts/sulingan.py python --out /tmp/s --demo   # uji alur tanpa GPU (jawaban tiruan)

`gabung` memilih satu jawaban lolos per soal, membuang yang tumpang tindih (13-gram) dengan soal uji, lalu menulis
data/train.jsonl + sulingan ke --hasil. Hasilnya deterministik, jadi checkpoint training tetap bisa dilanjutkan.
"""
import argparse
import hashlib
import json
import random
import re
import sys
import time
import urllib.request
import warnings
from argparse import Namespace
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
warnings.filterwarnings("ignore", category=SyntaxWarning)  # escape regex lama di kode jawaban saat di-parse
MBPP_URL = "https://raw.githubusercontent.com/google-research/google-research/master/mbpp/mbpp.jsonl"
FENCE = "`" * 3

SYSTEM_PYTHON = (
    "Kamu asisten pemrograman yang selalu menjawab dalam bahasa Indonesia. Untuk soal pemrograman Python: jelaskan "
    "pendekatanmu dalam satu sampai tiga kalimat, lalu tulis solusi lengkap dalam satu blok ```python yang "
    "mendefinisikan fungsi dengan nama persis seperti yang diminta. Jangan memakai input() dan jangan menaruh contoh "
    "pemakaian atau print di luar fungsi. Setelah blok kode, jelaskan singkat kasus khusus yang ditangani.")
SYSTEM_WEB = (
    "Kamu web developer senior yang selalu menjawab dalam bahasa Indonesia. Untuk permintaan website: buka dengan satu "
    "kalimat singkat, lalu tulis satu dokumen HTML lengkap dalam satu blok ```html. CSS dan JavaScript ada di dalam "
    "file itu, tanpa library, font, gambar, atau file dari luar. Halaman harus responsif sampai lebar 375 px, aksesibel, "
    "dan tanpa error JavaScript. Bungkus akses localStorage dengan try/catch. Setelah blok kode, tulis bagian "
    "**Cek kebutuhan** berupa daftar `- **<permintaan pengguna>** → <bagian kode yang memenuhinya>` untuk setiap hal "
    "yang diminta, lalu bagian **Catatan teknis** singkat jika perlu.")

PYTHON_TEMPLATES = [
    "Tulis fungsi Python `{name}` untuk soal berikut.\n\n{text}\n\nContoh yang harus benar:\n```python\n{example}\n```",
    "Tolong buatkan fungsi `{name}` di Python. Soalnya: {text}\n\nFungsinya harus lolos tes ini:\n{example}",
    "{text}\nNama fungsinya `{name}`. Contoh pemakaian: `{example}`",
    "Saya butuh fungsi Python bernama `{name}`. {text}\n\n```python\n{example}\n```",
]
BUILTINS = {"set", "sorted", "abs", "round", "str", "int", "float", "tuple", "list", "len", "isclose", "math", "dict",
            "sum", "max", "min", "any", "all", "bool", "type", "frozenset", "reversed", "map", "next", "iter"}

CONFIG = {
    "out": "/content/drive/MyDrive/finetune-id/V7/sulingan",
    "base_model": "unsloth/Qwen3.5-4B",
    "max_seq_len": 16384,
    "k": None,                      # kandidat per soal; None = 4 untuk python, 2 untuk web
    "batch": None,                  # soal per generate; None = 8 untuk python, 2 untuk web
    "max_new_tokens": None,         # None = 1536 untuk python, 10000 untuk web
    "temperature": 0.7, "top_p": 0.8, "top_k": 20,  # rekomendasi Qwen3.5 tanpa mode berpikir
    "timeout": 10,
    "limit": None,
    "seed": 42,
    "maks_python": 300,             # batas sampel python di data gabungan, supaya website dan data sendiri tidak tenggelam
    "own": None,                    # data/train.jsonl; None = dari repo
    "hasil": None,                  # file gabungan untuk training
    "chromium": None,               # path Chromium jika bukan bawaan Playwright
    "demo": False,
}


# ---------------------------------------------------------------- utilitas

def read_jsonl(path):
    path = Path(path)
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()] if path.is_file() else []


def append_jsonl(path, rows):
    with open(path, "a", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def write_if_changed(path, text):
    """Tulis hanya jika isinya berubah, supaya sidik jari data training (dan resume checkpoint) tetap sama."""
    path = Path(path)
    if not path.is_file() or path.read_text(encoding="utf-8") != text:
        path.write_text(text, encoding="utf-8")


def eval_module(name):
    """indopy_eval dan web_eval dari repo: pengambil kode dan pemeriksa yang sama dengan uji, supaya kriterianya sama."""
    folder = str(ROOT / "eval-suite")
    if folder not in sys.path:
        sys.path.insert(0, folder)
    return __import__(name)


def pick(seed, key, items):
    """Pilihan acak yang deterministik per soal."""
    return random.Random(f"{seed}:{key}").choice(items)


def berulang(text):
    """Tanda degenerasi: satu baris, atau blok 2-3 baris, berulang minimal 4 kali berturut-turut. Baris yang sama di
    tempat berbeda (misalnya enam <label class="field"> di satu form) wajar dan tidak dihitung, begitu juga baris tanpa
    kata (misalnya baris papan catur `"........" +` di literal posisi awal)."""
    lines = [l.strip() for l in text.splitlines() if len(l.strip()) > 10 and sum(ch.isalnum() for ch in l) >= 4]
    for period in (1, 2, 3):
        run = 0
        for i in range(period, len(lines)):
            run = run + 1 if lines[i] == lines[i - period] else 0
            if run >= 3 * period:  # pola sepanjang `period` baris muncul 4 kali berturut-turut
                return True
    return False


# ---------------------------------------------------------------- soal

def python_tasks(args):
    """Soal MBPP di luar MBPP+ dengan semua assert resminya."""
    sisa = read_jsonl(ROOT / "data" / "bench-support" / "mbpp-sisa.jsonl")
    if args.demo:  # tanpa jaringan: assert yang ada di prompt dan solusi rujukan dari mbpp-sisa
        original = {}
        for r in sisa:
            body = r["messages"][0]["content"].split('"""')[1].strip().splitlines()
            code = r["messages"][1]["content"].split(f"{FENCE}python\n", 1)[1].rsplit(FENCE, 1)[0]
            original[int(r["source"].split("/")[1])] = {"text": " ".join(l for l in body if not l.startswith("assert")),
                                                         "test_list": [l for l in body if l.startswith("assert")],
                                                         "challenge_test_list": [], "code": code}
    else:
        cache = Path(args.out) / "mbpp.jsonl"
        if not cache.is_file():
            print(f"mengunduh MBPP asli ke {cache}", flush=True)
            urllib.request.urlretrieve(MBPP_URL, cache)
        original = {t["task_id"]: t for t in read_jsonl(cache)}
    tasks = []
    for r in sisa:
        tid = int(r["source"].split("/")[1])
        t = original[tid]
        defined = re.findall(r"^def (\w+)\s*\(", t["code"], re.M)
        called = [n for n in re.findall(r"(\w+)\s*\(", t["test_list"][0]) if n not in BUILTINS]
        name = next((n for n in called if n in defined), called[0] if called else None)
        if not name:
            continue
        example = t["test_list"][0].strip()
        template = pick(args.seed, f"py{tid}", PYTHON_TEMPLATES)
        user = template.format(name=name, text=t["text"].strip(), example=example)
        tasks.append({"id": f"mbpp-{tid}", "source": f"MBPP/{tid}", "entry": name, "user": user,
                      "tests": "\n".join(t["test_list"] + t["challenge_test_list"]), "solusi": t["code"]})
    return tasks[:args.limit] if args.limit else tasks


def web_tasks(args):
    tasks = [{**r, "user": r["prompt"]} for r in read_jsonl(ROOT / "data" / "sulingan" / "prompt-web.jsonl")]
    return tasks[:args.limit] if args.limit else tasks


# ---------------------------------------------------------------- generate

class Generator:
    """Model dasar 16-bit tanpa adapter, dimuat lewat chat_gradio.Engine seperti skrip uji."""

    def __init__(self, args):
        self.args = args
        if args.demo:
            return
        sys.path.insert(0, str(ROOT / "scripts"))
        import chat_gradio as cg

        self.engine = cg.Engine(Namespace(adapter="none", base_model=args.base_model, load_in_4bit=False,
                                          max_seq_len=args.max_seq_len, out=args.out, demo=False))
        tok = self.engine.tokenizer
        tok.padding_side = "left"
        if tok.pad_token is None:
            tok.pad_token = tok.eos_token
        self.printed = False

    def __call__(self, system, users, k, max_new_tokens, seed):
        """k jawaban sampling untuk setiap prompt. Kembalikan list per prompt berisi dict text/token/selesai."""
        torch, tok, model = self.engine.torch, self.engine.tokenizer, self.engine.model
        prompts = [self.engine.render([{"role": "system", "content": system}, {"role": "user", "content": u}],
                                      thinking=False) for u in users]
        if not self.printed:
            print(f"akhir prompt pertama: {prompts[0][-120:]!r}", flush=True)
            self.printed = True
        enc = tok(prompts, return_tensors="pt", padding=True, add_special_tokens=False).to(model.device)
        torch.manual_seed(seed)
        a = self.args
        with torch.inference_mode():
            out = model.generate(**enc, do_sample=True, temperature=a.temperature, top_p=a.top_p, top_k=a.top_k,
                                 num_return_sequences=k, max_new_tokens=max_new_tokens, pad_token_id=tok.pad_token_id)
        new = out[:, enc["input_ids"].shape[1]:]
        texts = tok.batch_decode(new, skip_special_tokens=True)
        eos = {tok.eos_token_id, tok.convert_tokens_to_ids("<|im_end|>")}
        rows = []
        for i, text in enumerate(texts):
            ids = new[i].tolist()
            n = sum(1 for t in ids if t != tok.pad_token_id)
            rows.append({"text": text.strip(), "token": n, "selesai": any(t in eos for t in ids)})
        return [rows[i * k:(i + 1) * k] for i in range(len(users))]


def demo_python(task, k):
    """Jawaban tiruan: solusi rujukan (lolos) bergantian dengan solusi yang sengaja salah."""
    good = (f"Pendekatannya sederhana: fungsi `{task['entry']}` memproses masukan langsung.\n\n"
            f"{FENCE}python\n{task['solusi'].strip()}\n{FENCE}\n\nKasus khusus seperti masukan kosong ikut ditangani.")
    bad = f"{FENCE}python\ndef {task['entry']}(*a):\n    return None\n{FENCE}"
    return [{"text": good if (i + len(task['id'])) % 3 else bad, "token": 120, "selesai": True} for i in range(k)]


DEMO_HTML = """<!DOCTYPE html>
<html lang="id"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Demo</title><style>body{font-family:system-ui;margin:0;padding:1rem}input,button{font:inherit}</style></head>
<body><h1>Demo</h1><input id="isi" placeholder="Isi"><button id="tambah">Tambah</button><ul id="daftar"></ul>
<script>
const daftar = document.getElementById('daftar');
document.getElementById('tambah').addEventListener('click', () => {
  const li = document.createElement('li'); li.textContent = document.getElementById('isi').value; daftar.append(li);
  try { localStorage.setItem('demo', daftar.innerHTML); } catch (e) {}
  %RUSAK%
});
</script></body></html>"""


def demo_web(task, k):
    rows = []
    for i in range(k):
        broken = (i + len(task["id"])) % 3 == 0
        html = DEMO_HTML.replace("%RUSAK%", "belumAda();" if broken else "")
        text = (f"Berikut halamannya.\n\n{FENCE}html\n{html}\n{FENCE}\n\n**Cek kebutuhan**\n"
                f"- **Fitur utama** → tombol Tambah.\n- **Simpan** → localStorage.")
        rows.append({"text": text, "token": 900, "selesai": True})
    return rows


# ---------------------------------------------------------------- pemeriksaan

def check_python(task, cand, timeout):
    """(lolos, alasan) dengan pengambil kode dan penjalan tes yang sama dengan IndoPy."""
    indopy = eval_module("indopy_eval")
    text = cand["text"]
    if not cand["selesai"]:
        return False, "terpotong"
    if berulang(text):
        return False, "berulang"
    blocks = indopy.BLOCK.findall(text)
    if not any(re.search(rf"^\s*def\s+{re.escape(task['entry'])}\s*\(", b, re.M) for b in blocks):
        return False, f"tidak ada blok python yang mendefinisikan {task['entry']}"
    prose = indopy.BLOCK.sub("", text).strip()
    if len(prose) < 40:
        return False, "tanpa penjelasan"
    if "<think>" in text or "</think>" in text:
        return False, "berisi tag think"
    ok, why = indopy.run_tests("import math\n" + indopy.extract_code(text, task["entry"]), task["tests"], timeout)
    return ok, why or "lolos"


JS_INTERAKSI = """() => [...document.querySelectorAll('button, [role=button], input, select, textarea, canvas, summary')]
    .filter(e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0; }).length"""
# Keadaan halaman: isi DOM, gambar canvas, dan (dengan nilai=true) isi input serta status centang. Tombol yang tidak
# terpasang ke apa pun tidak mengubah satu pun dari ini.
JS_KEADAAN = """(nilai) => document.body.innerHTML + '|' + [...document.querySelectorAll('canvas')]
    .map(c => { try { return c.toDataURL().length; } catch (e) { return 0; } }).join(',') + '|' + (nilai ?
    [...document.querySelectorAll('input, textarea, select, output')].map(e => e.value + (e.checked ? '+' : '')).join('|')
    : '')"""
NILAI_INPUT = {"number": "5", "range": None, "date": "2026-03-15", "time": "09:30", "datetime-local": "2026-03-15T09:30",
               "month": "2026-03", "email": "uji@contoh.id", "tel": "081234567890", "url": "https://contoh.id",
               "color": None, "checkbox": None, "radio": None, "file": None, "hidden": None, "submit": None,
               "button": None, "reset": None, "search": "uji", "password": "Rahasia123!"}


def check_web_page(browser, path, need_storage):
    """Buka, isi semua input, klik semua tombol, tekan beberapa tombol keyboard. Kembalikan (lolos, alasan, skor)."""
    errors = []
    context = browser.new_context(viewport={"width": 1280, "height": 800})
    context.route("**/*", lambda route: route.continue_() if route.request.url.startswith(("file:", "data:", "blob:"))
                  else route.abort())
    page = context.new_page()
    page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
    page.on("console", lambda m: m.type == "error" and not re.search(r"Failed to load resource|net::ERR", m.text)
            and errors.append(f"console: {m.text}"))
    page.on("dialog", lambda d: d.accept("Uji") if d.type == "prompt" else d.accept())
    page.set_default_timeout(1500)
    url = path.resolve().as_uri()
    try:
        page.goto(url)
        page.wait_for_timeout(700)
        if errors:
            return False, "error saat dibuka: " + errors[0][:200], 0
        skor = page.evaluate(JS_INTERAKSI)
        if skor == 0:
            return False, "tidak ada elemen interaktif", 0
        page.set_viewport_size({"width": 375, "height": 740})
        page.wait_for_timeout(300)
        if not page.evaluate("() => document.documentElement.scrollWidth <= innerWidth + 1"):
            return False, "ada scroll horizontal di layar 375 px", skor
        page.set_viewport_size({"width": 1280, "height": 800})
        awal = page.evaluate(JS_KEADAAN, False)
        for el in page.locator("input, textarea, select").all()[:20]:
            try:
                if not el.is_visible() or not el.is_enabled():
                    continue
                tag = el.evaluate("e => e.tagName.toLowerCase()")
                if tag == "select":
                    n = el.evaluate("e => e.options.length")
                    if n > 1:
                        el.select_option(index=1)
                    continue
                kind = (el.get_attribute("type") or "text").lower()
                value = NILAI_INPUT.get(kind, "Uji coba")
                if value is not None and not el.evaluate("e => e.readOnly"):
                    el.fill(value)
            except Exception:
                pass  # elemen tertutup elemen lain atau tidak bisa diisi: lanjut ke elemen berikutnya
        berubah = page.evaluate(JS_KEADAAN, False) != awal  # hasil langsung saat mengetik, tanpa tombol
        sebelum = page.evaluate(JS_KEADAAN, True)
        clicked = 0
        buttons = page.locator("button, [role=button], input[type=button], input[type=submit], summary")
        for i in range(min(buttons.count(), 30)):
            if page.url != url:  # tautan atau form memuat halaman lain: kembali supaya pemeriksaan berlanjut
                page.goto(url)
                page.wait_for_timeout(300)
            try:
                el = buttons.nth(i)
                if el.is_visible() and el.is_enabled():
                    el.click(timeout=1000)
                    clicked += 1
                    page.wait_for_timeout(120)
                    # dicek setiap klik, karena tombol terakhir bisa saja Reset yang mengembalikan keadaan awal
                    berubah = berubah or (page.url == url and page.evaluate(JS_KEADAAN, True) != sebelum)
            except Exception:
                pass
        for key in ("ArrowUp", "ArrowLeft", "Space", "Enter", "Escape"):
            page.keyboard.press(key)
        page.wait_for_timeout(500)
        berubah = berubah or (page.url == url and page.evaluate(JS_KEADAAN, True) != sebelum)
        if errors:
            return False, "error saat dipakai: " + errors[0][:200], skor
        if not berubah:
            return False, "halaman tidak berubah apa pun setelah semua input diisi dan tombol diklik", skor
        if need_storage and not page.evaluate("() => { try { return localStorage.length > 0; } catch (e) { return false; } }"):
            return False, "diminta menyimpan, tapi localStorage tetap kosong setelah dipakai", skor
        return True, f"lolos ({clicked} klik)", skor + clicked
    except Exception as e:
        return False, f"pemeriksaan gagal: {str(e).splitlines()[0][:200]}", 0
    finally:
        context.close()


def check_web(task, cand, browser, folder):
    web = eval_module("web_eval")
    text = cand["text"]
    if not cand["selesai"]:
        return False, "terpotong", 0
    if berulang(text):
        return False, "berulang", 0
    if "<think>" in text or "</think>" in text:
        return False, "berisi tag think", 0
    html = web.extract_html(text)
    if html is None or not re.search(r"</html>\s*$", html, re.I):
        return False, "tidak ada dokumen HTML lengkap", 0
    if "cek kebutuhan" not in text.lower() or len(web.MAPPING.findall(text)) < 2:
        return False, "tanpa bagian Cek kebutuhan", 0
    if re.search(r"<(script|link)[^>]+(src|href)\s*=\s*[\"']?(https?:)?//", html, re.I):
        return False, "memuat file dari luar", 0
    path = folder / f"{task['id']}-{hashlib.sha1(html.encode()).hexdigest()[:8]}.html"
    path.write_text(html, encoding="utf-8")
    return check_web_page(browser, path, task.get("simpan"))


# ---------------------------------------------------------------- langkah

def run_source(args, kind):
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    tasks = python_tasks(args) if kind == "python" else web_tasks(args)
    k = args.k or (4 if kind == "python" else 2)
    batch = args.batch or (8 if kind == "python" else 2)
    max_new = args.max_new_tokens or (1536 if kind == "python" else 10000)
    file = out / f"kandidat-{kind}.jsonl"
    done = {r["id"] for r in read_jsonl(file)}
    todo = [t for t in tasks if t["id"] not in done]
    print(f"{kind}: {len(tasks)} soal, {len(done)} sudah, {len(todo)} dikerjakan; {k} kandidat per soal", flush=True)
    if not todo:
        return
    gen = None if args.demo else Generator(args)
    browser = playwright = None
    if kind == "web":
        from playwright.sync_api import sync_playwright
        playwright = sync_playwright().start()
        browser = playwright.chromium.launch(**({"executable_path": args.chromium} if args.chromium else {}))
        (out / "situs").mkdir(exist_ok=True)
    start, n_done = time.time(), 0
    try:
        for i in range(0, len(todo), batch):
            part = todo[i:i + batch]
            if args.demo:
                cands = [(demo_python if kind == "python" else demo_web)(t, k) for t in part]
            else:
                system = SYSTEM_PYTHON if kind == "python" else SYSTEM_WEB
                cands = gen(system, [t["user"] for t in part], k, max_new, args.seed + len(done) + i)
            rows = []
            for t, cs in zip(part, cands):
                for c in cs:
                    if kind == "python":
                        c["lolos"], c["alasan"] = check_python(t, c, args.timeout)
                    else:
                        c["lolos"], c["alasan"], c["skor"] = check_web(t, c, browser, out / "situs")
                rows.append({"id": t["id"], "source": t.get("source", f"sulingan/{t['id']}"), "user": t["user"],
                             "kandidat": cs})
            append_jsonl(file, rows)
            n_done += len(part)
            lolos = sum(any(c["lolos"] for c in r["kandidat"]) for r in rows)
            menit = (time.time() - start) / 60
            eta = menit / n_done * (len(todo) - n_done)
            print(f"[{kind}] {len(done) + n_done}/{len(tasks)} soal · batch ini {lolos}/{len(rows)} punya jawaban lolos"
                  f" · {menit:.0f} menit, sisa ±{eta:.0f} menit", flush=True)
            for r in rows:
                for c in r["kandidat"]:
                    if not c["lolos"]:
                        print(f"   gagal {r['id']}: {c['alasan'][:120]}", flush=True)
                        break
    finally:
        if browser:
            browser.close()
            playwright.stop()


def contamination_index(demo):
    """13-gram soal uji: MBPP+, HumanEval+ (tanpa teks template EvalPlus), IndoPy, dan Web-eval."""
    sys.path.insert(0, str(ROOT / "scripts"))
    import decontaminate as d

    hev = eval_module("web_eval").import_eval_humaneval()
    template = (hev.INSTRUCTION, hev.RESPONSE)
    sources = [("HumanEval+", d.humaneval), ("IndoPy", d.indopy), ("Web-eval", d.web_eval)]
    if not demo:
        sources.append(("MBPP+", d.mbpp))
    index = {}
    for label, load in sources:
        for item_id, text, _ in load():
            for t in template:
                text = text.replace(t, "")
            for g in d.grams(text):
                index.setdefault(g, set()).add(item_id)
    return index, d.grams, [s[0] for s in sources]


def combine(args):
    out = Path(args.out)
    own_file = Path(args.own) if args.own else ROOT / "data" / "train.jsonl"
    own = read_jsonl(own_file)
    index, grams, labels = contamination_index(args.demo)
    picked, dropped, stats = {"python": [], "web": []}, [], {}
    for kind in ("python", "web"):
        rows = read_jsonl(out / f"kandidat-{kind}.jsonl")
        kand = [c for r in rows for c in r["kandidat"]]
        samples = []
        for r in rows:
            ok = [c for c in r["kandidat"] if c["lolos"]]
            if not ok:
                continue
            if kind == "web":  # yang paling banyak elemen interaktif dan klik tanpa error
                best = max(ok, key=lambda c: (c.get("skor", 0), -len(c["text"])))
            else:
                best = pick(args.seed, r["id"], ok)
            sample = {"id": f"sul-{'py' if kind == 'python' else 'web'}-{r['id']}", "category": f"sulingan_{kind}",
                      "source": f"{r['source']} (jawaban model dasar Qwen3.5-4B, lolos pemeriksaan otomatis)",
                      "messages": [{"role": "user", "content": r["user"]}, {"role": "assistant", "content": best["text"]}]}
            hits = {i for g in grams(r["user"] + "\n" + best["text"]) for i in index.get(g, ())}
            if hits:
                dropped.append((sample["id"], sorted(hits)[:3]))
                continue
            samples.append(sample)
        if kind == "python" and len(samples) > args.maks_python:
            samples = sorted(random.Random(args.seed).sample(samples, args.maks_python), key=lambda s: s["id"])
        picked[kind] = samples
        stats[kind] = {"soal": len(rows), "kandidat": len(kand),
                       "kandidat_lolos": sum(c["lolos"] for c in kand),
                       "soal_punya_jawaban_lolos": sum(any(c["lolos"] for c in r["kandidat"]) for r in rows),
                       "dipakai": len(samples)}
    for kind, samples in picked.items():
        write_if_changed(out / f"sulingan-{kind}.jsonl",
                         "".join(json.dumps(s, ensure_ascii=False) + "\n" for s in samples))
    merged = own + picked["web"] + picked["python"]
    hasil = Path(args.hasil) if args.hasil else out / "train_v7.jsonl"
    write_if_changed(hasil, "".join(json.dumps(s, ensure_ascii=False) + "\n" for s in merged))
    summary = {"own": len(own), **{f"sulingan_{k}": v for k, v in stats.items()}, "total": len(merged),
               "dibuang_kontaminasi": [f"{i}: {', '.join(h)}" for i, h in dropped],
               "dicek_terhadap": labels, "hasil": str(hasil)}
    write_if_changed(out / "ringkasan-sulingan.json", json.dumps(summary, ensure_ascii=False, indent=1) + "\n")
    for kind, s in stats.items():
        rate = s["kandidat_lolos"] / s["kandidat"] if s["kandidat"] else 0
        print(f"{kind:<7} {s['soal']} soal, kandidat lolos {s['kandidat_lolos']}/{s['kandidat']} ({rate:.0%}), "
              f"{s['soal_punya_jawaban_lolos']} soal punya jawaban lolos, dipakai {s['dipakai']}")
    print(f"dibuang karena tumpang tindih dengan soal uji ({', '.join(labels)}): {len(dropped)}")
    print(f"data gabungan: {len(own)} own + {len(picked['web'])} web + {len(picked['python'])} python = "
          f"{len(merged)} sampel -> {hasil}")
    return summary


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("langkah", choices=["python", "web", "gabung"])
    for key, value in CONFIG.items():
        flag = "--" + key.replace("_", "-")
        if isinstance(value, bool):
            parser.add_argument(flag, action="store_true", default=None)
        elif isinstance(value, float):
            parser.add_argument(flag, type=float)
        elif isinstance(value, int) or key in ("k", "batch", "max_new_tokens", "limit"):
            parser.add_argument(flag, type=int)
        else:
            parser.add_argument(flag)
    args = parser.parse_args(argv)
    for key, value in CONFIG.items():
        if getattr(args, key) is None:
            setattr(args, key, value)
    return args


def main(argv=None):
    args = parse_args(argv)
    if args.langkah == "gabung":
        combine(args)
    else:
        run_source(args, args.langkah)


if __name__ == "__main__":
    main()
