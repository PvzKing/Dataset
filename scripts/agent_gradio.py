"""Agen coding bergaya Claude Code untuk model hasil fine-tuning v3: menulis website, mengujinya di browser,
lalu memperbaiki sendiri bug yang ditemukan.

Alur agen untuk setiap permintaan:
  1. Write   model menulis index.html (format sampel web_oneshot). Jika jawaban terpotong di batas token, agen
             menyambungnya otomatis (prefill), bukan meminta ulang dari awal.
  2. Bash    halaman dibuka di Chromium headless (desktop 1280px dan HP 375px). Error JavaScript, console.error,
             request gagal, scroll horizontal, dan error yang muncul setelah setiap tombol diklik dikumpulkan.
  3. Update  jika ada error, kode + daftar error dikirim ke model (format sampel web_debug). Blok SEARCH/REPLACE
             di jawaban diterapkan ke file, lalu kembali ke langkah 2. Maksimal N putaran.
Jika editor sudah berisi kode, pesan biasa diperlakukan sebagai permintaan perubahan pada file itu.

Perintah di kotak input:  /baru <permintaan>  /cek  /perbaiki [keluhan]  /undo  /reset  /bantuan

Cara memakai di Google Colab (GPU T4 cukup):

    Sel 1:  !pip install --upgrade unsloth "gradio>=6.30,<7" playwright
            !playwright install --with-deps chromium
    Sel 2:  from google.colab import drive; drive.mount("/content/drive")
            BR = "https://raw.githubusercontent.com/PvzKing/Dataset/main/scripts"
            !wget -q -O /content/agent_gradio.py {BR}/agent_gradio.py
            !wget -q -O /content/chat_gradio.py {BR}/chat_gradio.py
    Sel 3:  %run /content/agent_gradio.py

Opsi bisa diganti lewat argumen, misalnya:

    %run /content/agent_gradio.py --adapter /content/drive/MyDrive/finetune-id/qwen3.5-4b-own-4bit-lanjut/lora-adapter
    %run /content/agent_gradio.py --max-rounds 2 --workdir /content/drive/MyDrive/proyek-web
    %run /content/agent_gradio.py --demo          # coba tampilan dan alur agen tanpa GPU dan tanpa model

Model, tokenizer, dan generasi streaming memakai kelas Engine dari chat_gradio.py (diunduh otomatis jika belum ada).
"""
import argparse
import difflib
import html
import re
import sys
import tempfile
import threading
import time
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

# ======================================================== CONFIG: ubah di sini ========================================
CONFIG = {
    "adapter": "/content/drive/MyDrive/finetune-id/v3/qwen3.5-4b-own-4bit/lora-adapter",  # "auto", path, atau "none"
    "out": "/content/drive/MyDrive/finetune-id",   # dipakai jika adapter = "auto"
    "base_model": "unsloth/Qwen3.5-4B",
    "load_in_4bit": None,           # None = otomatis: 4-bit di GPU tanpa bf16 asli (T4)
    "max_seq_len": 8192,            # konteks: kode + daftar error + jawaban harus muat di sini
    "workdir": "/content/proyek" if Path("/content").is_dir() else "proyek",  # index.html + riwayat versi
    "max_rounds": 3,                # maksimal putaran cek → perbaiki per permintaan
    "app_name": "Nusantara Code",
    "share": False,                 # True = link publik *.gradio.live (wajib auth)
    "auth": None,                   # "user:sandi"
    "port": None,
    "demo": False,                  # True = model tiruan, untuk mencoba tampilan tanpa GPU
}
# ======================================================================================================================

HERE = Path(__file__).resolve().parent if "__file__" in globals() else Path.cwd()
CHAT_URL = "https://raw.githubusercontent.com/PvzKing/Dataset/main/scripts/chat_gradio.py"
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
try:
    import chat_gradio as cg
except ImportError:
    print(f"chat_gradio.py tidak ditemukan, mengunduh ke {HERE} ...", flush=True)
    urllib.request.urlretrieve(CHAT_URL, HERE / "chat_gradio.py")
    import chat_gradio as cg

FENCE = "`" * 3
HTML_BLOCK = re.compile(FENCE + r"html\s*\n(.*?)\n" + FENCE, re.S)
PATCH_BLOCK = re.compile(r"<{7} SEARCH[ \t]*\n(.*?)\n?={7}[ \t]*\n(.*?)\n?>{7} REPLACE", re.S)
WRITE_SETTINGS = dict(temperature=0.7, top_p=0.8, top_k=20, min_p=0.0, repetition_penalty=1.05, seed=-1,
                      max_new_tokens=6000, thinking=False)
# Perbaikan memakai greedy dan tanpa repetition penalty: blok SEARCH harus menyalin kode prompt persis, dan penalti
# repetisi justru menghukum token yang sudah ada di prompt.
FIX_SETTINGS = dict(WRITE_SETTINGS, temperature=0.0, repetition_penalty=1.0, max_new_tokens=2048)
SPINNER_WORDS = ["Merangkai", "Menimbang", "Meracik", "Menelusuri", "Merapikan", "Menyusun"]
HELP = """**Perintah**
- `<permintaan>`: jika editor kosong, tulis website baru; jika sudah ada kode, ubah file itu
- `/baru <permintaan>`: tulis website baru dari awal walaupun editor berisi kode
- `/cek`: uji halaman di browser tanpa memperbaiki
- `/perbaiki [keluhan]`: perbaiki error hasil uji, atau keluhan yang Anda tulis
- `/undo`: kembalikan versi sebelum perubahan terakhir
- `/reset`: kosongkan transkrip dan editor
Kode di editor boleh diubah langsung; perubahan Anda ikut dipakai pada perintah berikutnya."""


# ---------------------------------------------------------------- argumen

def parse_args():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--adapter", help='folder lora-adapter, "auto", atau "none"')
    parser.add_argument("--out", help="folder hasil training untuk adapter auto")
    parser.add_argument("--base-model")
    parser.add_argument("--load-in-4bit", action=argparse.BooleanOptionalAction, default=None)
    parser.add_argument("--max-seq-len", type=int)
    parser.add_argument("--workdir", help="folder index.html dan riwayat versinya")
    parser.add_argument("--max-rounds", type=int, help="maksimal putaran cek → perbaiki")
    parser.add_argument("--app-name")
    parser.add_argument("--share", action="store_true", default=None, help="buat link publik (wajib --auth)")
    parser.add_argument("--auth", help="user:sandi")
    parser.add_argument("--port", type=int)
    parser.add_argument("--demo", action="store_true", default=None, help="model tiruan tanpa GPU")
    args, _ = parser.parse_known_args(sys.argv[1:])  # di notebook sys.argv berisi argumen kernel
    for key, value in CONFIG.items():
        if getattr(args, key, None) is None:
            setattr(args, key, value)
    if args.share and not args.auth:
        raise SystemExit("--share membuat agen bisa diakses siapa pun yang tahu link-nya: tambahkan --auth user:sandi")
    if not args.demo and args.adapter not in ("auto", "none") and not (Path(args.adapter) / "adapter_config.json").is_file():
        raise SystemExit(f"adapter tidak ditemukan: {args.adapter}\n"
                         "Pastikan Drive sudah di-mount dan training v3 sudah selesai, atau pilih adapter lain dengan "
                         "--adapter <folder lora-adapter> (atau --adapter auto / none).")
    return args


# ---------------------------------------------------------------- proyek

@dataclass
class Problem:
    level: str      # "error" memicu perbaikan otomatis, "warning" hanya ditampilkan
    text: str       # dalam format yang dikirim ke model, mirip console browser
    where: str = ""


@dataclass
class Project:
    code: str = ""
    versions: list = field(default_factory=list)   # versi sebelumnya untuk /undo
    events: list = field(default_factory=list)     # transkrip
    problems: list = field(default_factory=list)
    last_check: str = "belum diuji"
    context_used: int = 0

    def set_code(self, new, workdir):
        if new == self.code:
            return
        if self.code:
            self.versions.append(self.code)
            del self.versions[:-30]
        self.code = new
        save_files(self, workdir)


def save_files(project, workdir):
    folder = Path(workdir)
    try:
        (folder / ".versi").mkdir(parents=True, exist_ok=True)
        (folder / "index.html").write_text(project.code, encoding="utf-8")
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        (folder / ".versi" / f"{stamp}-{len(project.versions):03d}.html").write_text(project.code, encoding="utf-8")
    except OSError as e:
        print(f"gagal menyimpan ke {folder}: {e}", flush=True)


# ---------------------------------------------------------------- uji di browser

def static_problems(code):
    problems = []
    if not re.search(r"<!DOCTYPE html>", code, re.I):
        problems.append(Problem("warning", "File tidak diawali <!DOCTYPE html>."))
    if not code.rstrip().lower().endswith("</html>"):
        problems.append(Problem("warning", "File tidak diakhiri </html>: kemungkinan jawaban terpotong."))
    for url in sorted(set(re.findall(r"""<(?:script|link|img|iframe)[^>]+(?:src|href)=["'](https?://[^"']+)""", code, re.I)))[:5]:
        problems.append(Problem("warning", f"Memuat resource dari luar: {url}"))
    return problems


def browser_problems(code, click_buttons=True):
    """Buka halaman di Chromium headless. Kembalikan (daftar Problem, ringkasan) atau (None, alasan) jika tidak bisa."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None, "Playwright belum terpasang: !pip install playwright && !playwright install --with-deps chromium"
    folder = Path(tempfile.mkdtemp(prefix="agen_cek_"))
    page_file = folder / "index.html"
    page_file.write_text(code, encoding="utf-8")
    url = page_file.as_uri()
    found, seen, clicked = [], set(), 0

    def add(level, text, where=""):
        key = (level, text)
        if key not in seen:
            seen.add(key)
            found.append(Problem(level, text, where))

    def location(stack):
        m = re.search(r"index\.html:(\d+):(\d+)", stack or "")
        return f"\n    at index.html:{m[1]}:{m[2]}" if m else ""

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            for name, width, height in (("desktop 1280px", 1280, 800), ("HP 375px", 375, 740)):
                ctx = browser.new_context(viewport={"width": width, "height": height})
                page = ctx.new_page()
                stage = {"now": "saat halaman dibuka"}
                page.on("pageerror", lambda e: add("error", f"Uncaught {e.name}: {e.message}{location(e.stack)}",
                                                   stage["now"]))
                page.on("console", lambda m: m.type == "error" and add("error", f"console.error: {m.text}",
                                                                       stage["now"]))
                page.on("dialog", lambda d: d.dismiss())

                def route(r):
                    if r.request.url.startswith(("file:", "data:", "blob:")):
                        return r.continue_()
                    add("warning", f"Request ke luar diblokir saat uji: {r.request.url[:120]}")
                    return r.abort()

                page.route("**/*", route)
                page.goto(url, wait_until="load", timeout=15000)
                page.wait_for_timeout(400)
                overflow = page.evaluate("document.documentElement.scrollWidth - window.innerWidth")
                if overflow > 0:
                    add("error", f"[{name}] Halaman bisa digeser ke samping: konten {width + overflow}px, "
                                 f"layar {width}px.")
                if click_buttons and width > 1000:
                    buttons = page.locator("button:visible, input[type=button]:visible, [role=button]:visible")
                    for i in range(min(buttons.count(), 20)):
                        try:
                            button = buttons.nth(i)
                            label = (button.inner_text(timeout=300) or button.get_attribute("aria-label") or "?")
                            stage["now"] = f"setelah klik tombol \"{' '.join(label.split())[:30]}\""
                            button.click(timeout=800, no_wait_after=True)
                            clicked += 1
                            page.wait_for_timeout(120)
                        except Exception:
                            continue
                        if page.url.split("?")[0] != url:  # tombol berpindah halaman: kembali
                            page.goto(url, wait_until="load", timeout=15000)
                ctx.close()
            browser.close()
    except Exception as e:
        return None, f"browser gagal dijalankan: {str(e).splitlines()[0][:200]}"
    summary = "Chromium 1280px + 375px" + (f", klik {clicked} tombol" if clicked else "")
    return found, summary


def run_check(code, click_buttons):
    problems = static_problems(code)
    found, summary = browser_problems(code, click_buttons)
    if found is None:
        problems.append(Problem("warning", f"Uji browser dilewati: {summary}"))
        return problems, "pemeriksaan statis saja"
    return problems + found, summary


def problems_for_model(problems):
    lines = []
    for p in problems:
        if p.level != "error":
            continue
        prefix = f"({p.where}) " if p.where and p.where != "saat halaman dibuka" else ""
        lines.append(prefix + p.text)
    return "\n".join(lines)


# ---------------------------------------------------------------- prompt dan patch

def write_messages(request):
    return [{"role": "user", "content": request}]


def fix_messages(code, problems, complaint=""):
    errors = problems_for_model(problems)
    parts = [complaint.strip()] if complaint.strip() else []
    if errors:
        intro = "Hasil uji di browser:" if parts else "Website ini bermasalah saat diuji di browser. Muncul:"
        parts.append(f"{intro}\n\n{FENCE}\n{errors}\n{FENCE}")
        if len(parts) == 1:
            parts.append("Tolong cari penyebabnya dan perbaiki bagian yang rusak saja.")
    parts.append(f"{FENCE}html\n{code}\n{FENCE}")
    return [{"role": "user", "content": "\n\n".join(parts)}]


def apply_patch(code, search, replace):
    """Terapkan satu blok SEARCH/REPLACE. Kembalikan (kode baru, cara) atau (None, alasan gagal)."""
    if search.strip() and code.count(search) == 1:
        return code.replace(search, replace, 1), "tepat"
    # Cadangan: cocokkan per baris tanpa memperhitungkan spasi di awal/akhir baris (indentasi model sering meleset).
    want = [line.strip() for line in search.strip("\n").split("\n")]
    if not any(want):
        return None, "blok SEARCH kosong"
    lines = code.split("\n")
    hits = [i for i in range(len(lines) - len(want) + 1)
            if [line.strip() for line in lines[i:i + len(want)]] == want]
    if len(hits) != 1:
        return None, "teks SEARCH tidak ditemukan di file" if not hits else f"teks SEARCH cocok {len(hits)} kali"
    i = hits[0]
    # Sesuaikan indentasi pengganti: geser dari indentasi blok SEARCH ke indentasi baris yang cocok di file.
    first = next(line for line in search.strip("\n").split("\n") if line.strip())
    model_indent = first[:len(first) - len(first.lstrip())]
    file_indent = lines[i][:len(lines[i]) - len(lines[i].lstrip())]
    new_lines = [file_indent + line[len(model_indent):] if line.startswith(model_indent) and line.strip() else line
                 for line in replace.split("\n")]
    return "\n".join(lines[:i] + new_lines + lines[i + len(want):]), "longgar (abaikan indentasi)"


def apply_answer(code, answer):
    """Kembalikan (kode baru atau None, daftar hasil per blok, mode)."""
    patches = PATCH_BLOCK.findall(answer)
    if patches:
        results, new = [], code
        for search, replace in patches:
            out, how = apply_patch(new, search, replace)
            results.append((out is not None, how, search))
            if out is not None:
                new = out
        return (new if new != code else None), results, "patch"
    full = [b for b in HTML_BLOCK.findall(answer) if b.lstrip().lower().startswith("<!doctype")]
    if full:
        return full[-1].strip(), [(True, "file ditulis ulang", "")], "rewrite"
    return None, [], "none"


def prose_of(answer):
    """Teks penjelasan model tanpa blok kode panjang (kode tampil di editor dan diff)."""
    text = HTML_BLOCK.sub("", answer)
    text = re.sub(FENCE + r"[a-z]*\s*\n<{7} SEARCH.*?>{7} REPLACE\s*\n?" + FENCE,
                  "→ diterapkan di Update(index.html)", text, flags=re.S)
    text = PATCH_BLOCK.sub("→ diterapkan di Update(index.html)", text)
    text = re.sub(FENCE + r"html\s*\n.*$", "", text, flags=re.S)  # blok html yang belum ditutup
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def extract_html(answer):
    blocks = HTML_BLOCK.findall(answer)
    if blocks:
        return blocks[-1].strip()
    m = re.search(FENCE + r"html\s*\n(.*)$", answer, re.S)  # belum ditutup (masih streaming / terpotong)
    return m[1] if m else ""


# ---------------------------------------------------------------- tampilan transkrip

def md(text):
    """Markdown sederhana -> HTML: blok kode, judul, daftar, **tebal**, `kode`. Semua teks di-escape dulu."""
    out = []
    for i, part in enumerate(re.split(FENCE + r"[a-zA-Z0-9]*\n?", text)):
        if i % 2:
            out.append(f'<pre class="t-code">{html.escape(part.rstrip())}</pre>')
            continue
        lines = []
        for line in part.strip("\n").split("\n"):
            s = html.escape(line)
            s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
            s = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", s)
            if re.match(r"#{1,6} ", line):
                s = f"<b>{s.lstrip('#').strip()}</b>"
            elif re.match(r"\s*[-*] ", line):
                s = re.sub(r"^(\s*)[-*] ", r"\1• ", s)
            lines.append(s)
        out.append("<br>".join(lines))
    return "".join(out)


def diff_rows(old, new, context=2, limit=80):
    rows, added, removed = [], 0, 0
    o = n = 0
    for line in difflib.unified_diff(old.split("\n"), new.split("\n"), lineterm="", n=context):
        if line.startswith(("---", "+++")):
            continue
        if line.startswith("@@"):
            m = re.match(r"@@ -(\d+)(?:,\d+)? \+(\d+)", line)
            o, n = int(m[1]), int(m[2])
            if rows:
                rows.append(("gap", "", "⋮"))
            continue
        tag, text = line[:1], line[1:]
        if tag == "-":
            rows.append(("del", o, text)); o += 1; removed += 1
        elif tag == "+":
            rows.append(("add", n, text)); n += 1; added += 1
        else:
            rows.append(("ctx", n, text)); o += 1; n += 1
    return rows[:limit], added, removed, len(rows) > limit


def render_event(e):
    kind = e["kind"]
    if kind == "welcome":
        return (f'<div class="t-welcome"><div><span class="t-star">✻</span> Selamat datang di '
                f'<b>{html.escape(e["app"])}</b>!</div><div class="t-dim">/bantuan untuk daftar perintah</div>'
                f'<div class="t-dim">model: {html.escape(e["model"])}</div>'
                f'<div class="t-dim">folder: {html.escape(e["workdir"])}</div></div>')
    if kind == "user":
        return f'<div class="t-user"><span class="t-caret">&gt;</span> {html.escape(e["text"])}</div>'
    if kind == "text":
        return f'<div class="t-row"><span class="t-dot t-white">●</span><div class="t-body">{md(e["text"])}</div></div>'
    if kind == "spinner":
        return (f'<div class="t-spinner"><span class="t-glyph"></span> {html.escape(e["text"])}… '
                f'<span class="t-dim">({html.escape(e.get("detail", ""))} · tombol ■ untuk berhenti)</span></div>')
    if kind == "tool":
        color = {"ok": "t-green", "error": "t-red", "warn": "t-orange", "run": "t-orange"}[e.get("status", "ok")]
        head = (f'<div class="t-row"><span class="t-dot {color}">●</span><div class="t-body"><b>{html.escape(e["name"])}</b>'
                f'<span class="t-dim">({html.escape(e.get("arg", ""))})</span></div></div>')
        subs = "".join(f'<div class="t-sub"><span class="t-elbow">{"⎿" if i == 0 else " "}</span>'
                       f'<span class="{cls}">{md(text)}</span></div>' for i, (cls, text) in enumerate(e.get("lines", [])))
        diff = ""
        if e.get("diff"):
            rows, _, _, more = e["diff"]
            cells = "".join(
                f'<div class="d-{kind_}"><span class="d-no">{no}</span><span class="d-sign">'
                f'{"+" if kind_ == "add" else "-" if kind_ == "del" else " "}</span>'
                f'<span class="d-text">{html.escape(text)}</span></div>' for kind_, no, text in rows)
            diff = f'<div class="t-diff">{cells}{"<div class=d-gap>… diff dipotong</div>" if more else ""}</div>'
        return head + subs + diff
    return ""


def render_terminal(events, busy=None):
    body = "".join(render_event(e) for e in events)
    if busy:
        body += render_event(busy)
    # column-reverse membuat area gulir selalu menempel di bawah, seperti terminal.
    return f'<div class="term-scroll"><div class="term-inner">{body}</div></div>'


def render_problems(project):
    if not project.problems:
        return f'<div class="p-empty">✓ Tidak ada masalah ({html.escape(project.last_check)})</div>'
    rows = []
    for p in project.problems:
        icon = "⛔" if p.level == "error" else "⚠️"
        where = f'<span class="p-where">{html.escape(p.where)}</span>' if p.where else ""
        rows.append(f'<div class="p-row p-{p.level}">{icon} <pre>{html.escape(p.text)}</pre>{where}</div>')
    return f'<div class="p-head">{html.escape(project.last_check)}</div>' + "".join(rows)


def status_line(project, args, engine, busy=False):
    if args.demo:
        model = "demo"
    elif engine.adapter:
        adapter = Path(str(engine.adapter))
        model = f"{adapter.parent.parent.name}/{adapter.parent.name}"
    else:
        model = "model dasar"
    errors = sum(p.level == "error" for p in project.problems)
    lines = project.code.count("\n") + 1 if project.code else 0
    state = "● bekerja" if busy else "○ siap"
    return (f'<div class="statusline"><span>{state}</span><span>◆ {html.escape(model)}</span>'
            f'<span>konteks {project.context_used:,}/{args.max_seq_len:,}</span>'
            f'<span>index.html · {lines} baris</span><span>{errors} error</span>'
            f'<span>versi {len(project.versions)}</span></div>')


# ---------------------------------------------------------------- model tiruan (mode demo)

DEMO_SITE = """<!DOCTYPE html>
<html lang="id">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Penghitung</title>
  <style>
    body { font-family: system-ui, sans-serif; display: grid; place-items: center; min-height: 100vh; margin: 0; background: #f5f4ed; }
    .card { background: #fff; padding: 2rem; border-radius: 16px; text-align: center; box-shadow: 0 8px 24px rgba(0,0,0,.08); }
    output { display: block; font-size: 3rem; margin: 1rem 0; }
    button { font: inherit; padding: .6rem 1.2rem; border: 0; border-radius: 10px; background: #c96442; color: #fff; cursor: pointer; }
  </style>
</head>
<body>
  <main class="card">
    <h1>Penghitung</h1>
    <output id="count">0</output>
    <button type="button" id="add">Tambah</button>
    <button type="button" id="reset">Ulang</button>
  </main>
  <script>
    let count = 0;
    const countEl = document.getElementById('count');
    document.getElementById('add').addEventListener('click', () => {
      count++;
      countEl.textContent = count;
    });
    document.getElementById('reset').addEventListener('click', () => {
      count = 0;
      counEl.textContent = count;
    });
  </script>
</body>
</html>"""


def demo_answer(messages):
    user = messages[-1]["content"]
    if FENCE + "html" not in user:
        return ("Berikut penghitung sederhana dalam satu file HTML.\n\n" + FENCE + "html\n" + DEMO_SITE + "\n" + FENCE +
                "\n\n**Cek kebutuhan**\n- **Tambah** → tombol `#add` menaikkan `count`.\n"
                "- **Ulang** → tombol `#reset` mengembalikan ke 0.")
    if "counEl" in user:
        return ("Error itu muncul karena salah ketik nama variabel di handler tombol **Ulang**.\n\n**Penyebab**\n"
                "Variabelnya bernama `countEl`, tetapi di handler tertulis `counEl`, sehingga JavaScript melempar "
                "`ReferenceError` saat tombol diklik.\n\n**Perbaikan**\n" + FENCE + "\n<<<<<<< SEARCH\n"
                "      counEl.textContent = count;\n=======\n      countEl.textContent = count;\n>>>>>>> REPLACE\n"
                + FENCE + "\n\n**Cara cek:** klik **Ulang**; angka kembali ke 0 tanpa error di console.")
    return "Saya tidak menemukan masalah lain di kode ini. (mode demo)"


def demo_stream(messages, stop_event):
    text = demo_answer(messages)
    for i in range(0, len(text), 24):
        if stop_event.is_set():
            return
        time.sleep(0.015)
        yield text[i:i + 24]


# ---------------------------------------------------------------- agen

class Agent:
    """Satu permintaan pengguna -> rangkaian langkah. Setiap metode adalah generator yang menghasilkan tampilan."""

    def __init__(self, engine, args):
        self.engine = engine
        self.args = args
        # Engine.stream selalu menyetel stop_event miliknya saat generasi selesai, jadi permintaan berhenti dari
        # pengguna dicatat di flag terpisah ini.
        self.user_stop = threading.Event()

    # -- model
    def generate(self, project, messages, settings, label, on_partial=None):
        """Generator: menghasilkan event spinner selama model menulis; nilai akhir lewat StopIteration.value."""
        engine, args = self.engine, self.args
        stop_event = engine.current_stop = threading.Event()
        prompt = engine.render(messages, False)
        n_prompt = engine.count_tokens(prompt)
        project.context_used = n_prompt
        budget = args.max_seq_len - n_prompt
        if budget < 256:
            raise ValueError(f"prompt {n_prompt:,} token, konteks {args.max_seq_len:,}: tidak ada ruang untuk jawaban. "
                             "Perkecil file atau jalankan dengan --max-seq-len lebih besar.")
        raw, start, last_yield = "", time.time(), 0.0
        word = SPINNER_WORDS[int(start) % len(SPINNER_WORDS)]
        for attempt in range(3):  # 1 generasi + maksimal 2 sambungan otomatis jika terpotong
            limit = min(settings["max_new_tokens"], args.max_seq_len - engine.count_tokens(prompt + raw))
            if limit < 128:
                break
            run_settings = dict(settings, max_new_tokens=limit)
            stream = demo_stream(messages, self.user_stop) if args.demo else \
                engine.stream(prompt + raw, run_settings, True, stop_event)
            produced = ""
            for piece in stream:
                produced += piece
                now = time.time()
                if now - last_yield > 0.4:
                    last_yield = now
                    text = cg.SPECIAL_TOKEN.sub("", raw + produced)
                    detail = f"{label} · {now - start:.0f} dtk · {engine.count_tokens(text):,} token"
                    yield {"kind": "spinner", "text": word, "detail": detail}, text
            raw += produced
            if self.user_stop.is_set():
                break
            clean = cg.SPECIAL_TOKEN.sub("", raw)
            # Terpotong: blok kode masih terbuka dan model berhenti karena batas token, bukan karena selesai.
            if clean.count(FENCE) % 2 == 0 or engine.count_tokens(produced) < limit - 8:
                break
            project.events.append({"kind": "tool", "name": "Lanjutkan", "arg": "jawaban terpotong", "status": "warn",
                                   "lines": [("t-dim", "Batas token tercapai di tengah kode; menyambung otomatis "
                                                       "dari titik terakhir.")]})
        project.context_used = engine.count_tokens(prompt + raw)
        return cg.SPECIAL_TOKEN.sub("", raw).strip()

    # -- langkah
    def write(self, project, request, settings):
        events = project.events
        answer = None
        gen = self.generate(project, write_messages(request), settings, "menulis index.html")
        try:
            while True:
                busy, partial = next(gen)
                yield busy, extract_html(partial) or None
        except StopIteration as stop:
            answer = stop.value
        code = extract_html(answer)
        prose = prose_of(answer)
        if not code.strip():
            events.append({"kind": "text", "text": prose or "_(model tidak menulis kode)_"})
            yield None
            return False
        intro, _, notes = prose.partition("\n\n")
        if intro:
            events.append({"kind": "text", "text": intro})
        project.set_code(code.strip(), self.args.workdir)
        n_lines = project.code.count("\n") + 1
        events.append({"kind": "tool", "name": "Write", "arg": "index.html", "status": "ok",
                       "lines": [("", f"Menulis **{n_lines}** baris ke `{self.args.workdir}/index.html`")]})
        if notes.strip():
            events.append({"kind": "text", "text": notes.strip()})
        yield None
        return True

    def check(self, project, click_buttons):
        project.events.append({"kind": "tool", "name": "Bash", "arg": "uji di Chromium", "status": "run",
                               "lines": [("t-dim", "membuka halaman di desktop 1280px dan HP 375px…")]})
        yield {"kind": "spinner", "text": "Menguji di browser", "detail": "Chromium headless"}
        started = time.time()
        problems, summary = run_check(project.code, click_buttons)
        project.problems = problems
        errors = [p for p in problems if p.level == "error"]
        warnings = [p for p in problems if p.level == "warning"]
        project.last_check = f"{summary} · {datetime.now():%H:%M:%S}"
        lines = [("t-red" if errors else "t-green",
                  f"**{len(errors)} error**, {len(warnings)} peringatan ({summary}, {time.time() - started:.1f} dtk)")]
        for p in errors[:4]:
            lines.append(("t-red", p.text.split("\n")[0] + (f" — {p.where}" if p.where else "")))
        if len(errors) > 4:
            lines.append(("t-dim", f"… dan {len(errors) - 4} lainnya (lihat tab Masalah)"))
        project.events[-1] = {"kind": "tool", "name": "Bash", "arg": "uji di Chromium",
                              "status": "error" if errors else "warn" if warnings else "ok", "lines": lines}
        yield None
        return errors

    def fix(self, project, complaint=""):
        """Satu putaran perbaikan. Kembalikan True jika file berubah."""
        messages = fix_messages(project.code, project.problems, complaint)
        answer = None
        gen = self.generate(project, messages, FIX_SETTINGS, "mencari penyebab")
        try:
            while True:
                busy, _ = next(gen)
                yield busy
        except StopIteration as stop:
            answer = stop.value
        prose = prose_of(answer)
        if prose:
            project.events.append({"kind": "text", "text": prose})
        old = project.code
        new, results, mode = apply_answer(old, answer)
        failed = [(how, search) for ok, how, search in results if not ok]
        if new is None:
            reason = "; ".join(how for how, _ in failed) if failed else "jawaban tidak berisi blok SEARCH/REPLACE"
            project.events.append({"kind": "tool", "name": "Update", "arg": "index.html", "status": "error",
                                   "lines": [("t-red", f"Perubahan tidak bisa diterapkan: {reason}")]})
            yield None
            return False
        project.set_code(new, self.args.workdir)
        rows, added, removed, more = diff_rows(old, new)
        lines = [("", f"{'Menulis ulang file' if mode == 'rewrite' else f'{len(results) - len(failed)} perubahan'}: "
                      f"**+{added}** / **−{removed}** baris")]
        for how, search in failed:
            lines.append(("t-red", f"1 blok dilewati: {how}"))
        if any(how.startswith("longgar") for _, how, _ in results):
            lines.append(("t-dim", "sebagian blok dicocokkan tanpa memperhitungkan indentasi"))
        project.events.append({"kind": "tool", "name": "Update", "arg": "index.html",
                               "status": "warn" if failed else "ok", "lines": lines, "diff": (rows, added, removed, more)})
        yield None
        return True

    def loop(self, project, rounds, auto_fix, click_buttons, complaint=""):
        """Cek → perbaiki → cek lagi. Keluhan pengguna (jika ada) diperbaiki dulu sebelum uji pertama."""
        if complaint:
            changed = yield from self.fix(project, complaint)
            if not changed:
                return
        for round_no in range(rounds + 1):
            if self.user_stop.is_set():
                return
            errors = yield from self.check(project, click_buttons)
            if not errors:
                return
            if not auto_fix:
                project.events.append({"kind": "text", "text": "Ketik `/perbaiki` untuk memperbaiki error di atas."})
                return
            if round_no == rounds:
                project.events.append({"kind": "text", "text": f"Masih ada {len(errors)} error setelah {rounds} "
                                       "putaran perbaikan. Periksa tab **Masalah**, ubah kode di editor, atau beri "
                                       "petunjuk lewat `/perbaiki <keluhan>`."})
                return
            changed = yield from self.fix(project)
            if not changed:
                return


# ---------------------------------------------------------------- tampilan

CSS = """
:root { --t-bg: #1a1a19; --t-panel: #222220; --t-border: #3a3936; --t-text: #e8e6df; --t-dim: #8f8c83;
  --t-accent: #d97757; --t-green: #6fbf73; --t-red: #e5736a; --t-orange: #e0a458; }
body, gradio-app, .gradio-container { background: var(--t-bg) !important; color: var(--t-text); }
.gradio-container { max-width: 100% !important; padding: 8px 12px !important; }
footer { display: none !important; }
#term { border: 1px solid var(--t-border); border-radius: 10px; background: var(--t-bg); padding: 0 !important; }
.term-scroll { height: 66vh; overflow-y: auto; display: flex; flex-direction: column-reverse; padding: 10px 14px; }
.term-inner { margin-bottom: auto !important; font-family: "JetBrains Mono", ui-monospace, Menlo, Consolas, monospace; font-size: 13px; line-height: 1.55;
  color: var(--t-text); }
.t-welcome { border: 1px solid var(--t-accent); border-radius: 8px; padding: 8px 12px; margin-bottom: 12px;
  display: inline-block; max-width: 100%; overflow-wrap: anywhere; }
.t-star { color: var(--t-accent); }
.t-dim { color: var(--t-dim); }
.t-user { background: #2b2a27; border-radius: 6px; padding: 6px 10px; margin: 12px 0 8px; white-space: pre-wrap; }
.t-caret { color: var(--t-dim); }
.t-row { display: flex; gap: 8px; margin-top: 8px; }
.t-dot { flex: none; }
.t-body { min-width: 0; overflow-wrap: anywhere; }
.t-white { color: var(--t-text); } .t-green { color: var(--t-green); } .t-red { color: var(--t-red); }
.t-orange { color: var(--t-orange); }
.t-sub { display: flex; gap: 8px; padding-left: 4px; }
.t-elbow { color: var(--t-dim); flex: none; width: 1.2em; }
.t-code { background: var(--t-panel); border-radius: 6px; padding: 6px 8px; margin: 4px 0; white-space: pre-wrap; }
.term-inner code { color: var(--t-accent); background: transparent; }
.t-spinner { margin-top: 10px; color: var(--t-accent); }
.t-glyph::before { content: "✻"; display: inline-block; animation: glyph 1.2s steps(1) infinite; }
@keyframes glyph { 0% { content: "·"; } 17% { content: "✢"; } 33% { content: "✳"; } 50% { content: "✶"; }
  67% { content: "✻"; } 83% { content: "✽"; } }
.t-diff { margin: 4px 0 4px 1.6em; border: 1px solid var(--t-border); border-radius: 6px; overflow-x: auto; font-size: 12px; }
.t-diff > div { display: flex; white-space: pre; }
.d-no { width: 3.2em; text-align: right; color: var(--t-dim); padding-right: 6px; flex: none; user-select: none; }
.d-sign { width: 1.2em; flex: none; }
.d-add { background: rgba(80, 160, 90, .22); } .d-add .d-sign { color: var(--t-green); }
.d-del { background: rgba(200, 80, 70, .22); } .d-del .d-sign { color: var(--t-red); }
.d-gap { color: var(--t-dim); padding-left: 4.4em; }
#prompt { border: 1px solid var(--t-border) !important; border-radius: 10px !important; background: var(--t-bg) !important; }
#prompt textarea { font-family: "JetBrains Mono", ui-monospace, monospace !important; font-size: 13px;
  background: transparent !important; color: var(--t-text) !important; border: 0 !important; box-shadow: none !important; }
#prompt button.submit-button { background: var(--t-accent) !important; color: #fff !important; }
.statusline { display: flex; flex-wrap: wrap; gap: 6px 16px; font: 12px "JetBrains Mono", ui-monospace, monospace;
  color: var(--t-dim); padding: 4px 2px; }
.statusline span:first-child { color: var(--t-accent); }
#editor .cm-editor { height: 62vh; font-size: 12.5px; }
.preview-frame { width: 100%; height: 66vh; border: 1px solid var(--t-border); border-radius: 10px; background: #fff; }
.preview-empty { height: 66vh; display: grid; place-items: center; color: var(--t-dim);
  border: 1px dashed var(--t-border); border-radius: 10px; }
.p-head { color: var(--t-dim); font: 12px ui-monospace, monospace; margin-bottom: 8px; }
.p-empty { color: var(--t-green); font: 13px ui-monospace, monospace; padding: 12px; }
.p-row { border-left: 3px solid var(--t-orange); background: var(--t-panel); border-radius: 6px; padding: 6px 10px;
  margin-bottom: 6px; font: 12.5px ui-monospace, monospace; }
.p-error { border-left-color: var(--t-red); }
.p-row pre { display: inline; white-space: pre-wrap; margin: 0; background: transparent; color: var(--t-text); }
.p-where { display: block; color: var(--t-dim); font-size: 11.5px; }
.tool-btn { min-width: 0 !important; }
"""

FORCE_DARK_JS = "() => { document.body.classList.add('dark'); }"


def build_app(engine, args):
    import gradio as gr

    model_name = "demo (model tiruan)" if args.demo else str(engine.adapter or args.base_model)
    welcome = {"kind": "welcome", "app": args.app_name, "model": model_name, "workdir": str(Path(args.workdir).resolve())}
    agent = Agent(engine, args)

    with gr.Blocks(title=args.app_name, fill_height=True) as demo:
        project_state = gr.State(Project(events=[welcome]))
        with gr.Row(equal_height=False):
            with gr.Column(scale=5, min_width=380):
                term = gr.HTML(render_terminal([welcome]), elem_id="term", padding=False)
                prompt = gr.Textbox(elem_id="prompt", show_label=False, lines=1, max_lines=8, container=False,
                                    placeholder="> Minta website, ubah kode, atau ketik /bantuan  (Enter kirim)",
                                    submit_btn=True, stop_btn=True, autofocus=True)
                status = gr.HTML(status_line(Project(), args, engine))
                with gr.Accordion("Pengaturan agen", open=False):
                    auto_fix = gr.Checkbox(True, label="Perbaiki otomatis (auto-accept edits)",
                                           info="Error hasil uji langsung dikirim ke model dan patch-nya diterapkan.")
                    rounds = gr.Slider(0, 6, args.max_rounds, step=1, label="Maks. putaran perbaikan per permintaan")
                    click_buttons = gr.Checkbox(True, label="Klik semua tombol saat uji",
                                                info="Menangkap error yang baru muncul setelah tombol ditekan.")
                    temperature = gr.Slider(0, 1.5, WRITE_SETTINGS["temperature"], step=0.05,
                                            label="Temperature saat menulis website",
                                            info="Perbaikan selalu greedy (0) supaya blok SEARCH menyalin kode persis.")
                    max_new_tokens = gr.Slider(1024, 8192, WRITE_SETTINGS["max_new_tokens"], step=256,
                                               label="Maks. token jawaban saat menulis website")
            with gr.Column(scale=6, min_width=380):
                with gr.Row(elem_id="toolbar"):
                    check_btn = gr.Button("▶ Uji", size="sm", elem_classes="tool-btn")
                    fix_btn = gr.Button("🔧 Perbaiki", size="sm", variant="primary", elem_classes="tool-btn")
                    undo_btn = gr.Button("↶ Undo", size="sm", elem_classes="tool-btn")
                    stop_btn = gr.Button("■ Stop", size="sm", variant="stop", elem_classes="tool-btn")
                    download = gr.DownloadButton("⬇ Unduh", size="sm", visible=False, elem_classes="tool-btn")
                with gr.Tabs():
                    with gr.Tab("index.html"):
                        editor = gr.Code("", language="html", interactive=True, lines=30, show_label=False,
                                         elem_id="editor", buttons=["copy"])
                    with gr.Tab("Pratinjau"):
                        preview = gr.HTML(cg.preview_html(None))
                    with gr.Tab("Masalah"):
                        problems_view = gr.HTML(render_problems(Project()))

        outputs = [term, editor, preview, problems_view, status, project_state, download]
        settings_in = [auto_fix, rounds, click_buttons, temperature, max_new_tokens]

        def view(project, busy=None, live_code=None, streaming=False):
            """Nilai untuk semua komponen. Saat streaming, editor menampilkan kode yang sedang ditulis model."""
            code = live_code if streaming and live_code is not None else project.code
            index = Path(args.workdir) / "index.html"
            return (render_terminal(project.events, busy), code,
                    gr.update() if streaming else cg.preview_html(project.code or None),
                    render_problems(project), status_line(project, args, engine, busy is not None), project,
                    gr.update(value=str(index), visible=True) if project.code and index.is_file() else
                    gr.update(visible=False))

        def drive(project, steps):
            """Jalankan generator langkah agen sambil memperbarui tampilan."""
            try:
                for item in steps:
                    if isinstance(item, tuple):
                        yield view(project, item[0], item[1], streaming=True)
                    else:
                        yield view(project, item)
            except Exception as e:  # tampilkan di transkrip, jangan putuskan sesi
                project.events.append({"kind": "tool", "name": "Error", "arg": type(e).__name__, "status": "error",
                                       "lines": [("t-red", str(e)[:500])]})
            yield view(project)

        def handle(text, code, project, auto_fix, rounds, click_buttons, temperature, max_new_tokens):
            text = (text or "").strip()
            agent.user_stop.clear()
            if code is not None and code.strip() != project.code.strip():  # pengguna mengubah kode di editor
                project.set_code(code.strip(), args.workdir)
                project.events.append({"kind": "tool", "name": "Edit", "arg": "index.html oleh Anda", "status": "ok",
                                       "lines": [("t-dim", "perubahan manual di editor dipakai")]})
            if not text:
                yield view(project)
                return
            settings = dict(WRITE_SETTINGS, temperature=float(temperature), max_new_tokens=int(max_new_tokens))
            rounds = int(rounds)
            command, _, rest = text.partition(" ")
            command = command.lower() if text.startswith("/") else ""
            project.events.append({"kind": "user", "text": text})

            def steps():
                if command in ("/bantuan", "/help"):
                    project.events.append({"kind": "text", "text": HELP})
                elif command in ("/reset", "/clear"):
                    project.events[:] = [welcome]
                    if project.code:
                        project.versions.append(project.code)
                    project.code, project.problems, project.last_check = "", [], "belum diuji"
                elif command == "/undo":
                    if project.versions:
                        previous = project.versions.pop()
                        diff = diff_rows(project.code, previous)
                        project.code = previous
                        save_files(project, args.workdir)
                        project.events.append({"kind": "tool", "name": "Undo", "arg": "index.html", "status": "ok",
                                               "lines": [("", f"kembali ke versi sebelumnya: +{diff[1]} / −{diff[2]} baris")],
                                               "diff": diff})
                    else:
                        project.events.append({"kind": "text", "text": "Tidak ada versi sebelumnya."})
                elif command == "/cek":
                    if project.code:
                        yield from agent.check(project, click_buttons)
                    else:
                        project.events.append({"kind": "text", "text": "Editor masih kosong."})
                elif command == "/perbaiki":
                    if not project.code:
                        project.events.append({"kind": "text", "text": "Editor masih kosong."})
                    elif rest.strip():
                        yield from agent.loop(project, max(rounds, 1), auto_fix, click_buttons, complaint=rest.strip())
                    else:
                        errors = yield from agent.check(project, click_buttons)
                        if not errors:
                            project.events.append({"kind": "text", "text": "Uji browser tidak menemukan error. "
                                                   "Jelaskan masalahnya: `/perbaiki <keluhan>`."})
                        elif (yield from agent.fix(project)):
                            yield from agent.loop(project, max(rounds - 1, 0), True, click_buttons)
                elif command and command != "/baru":
                    project.events.append({"kind": "text", "text": f"Perintah `{command}` tidak dikenal.\n\n{HELP}"})
                elif command == "/baru" or not project.code:
                    request = rest if command == "/baru" else text
                    if not request.strip():
                        project.events.append({"kind": "text", "text": "Tulis permintaannya: `/baru <permintaan>`."})
                        return
                    if (yield from agent.write(project, request, settings)):
                        yield from agent.loop(project, rounds, auto_fix, click_buttons)
                else:  # permintaan perubahan pada file yang sudah ada
                    yield from agent.loop(project, max(rounds, 1), auto_fix, click_buttons, complaint=text)

            yield from drive(project, steps())

        def command_button(command):
            def run(code, project, auto_fix, rounds, click_buttons, temperature, max_new_tokens):
                yield from handle(command, code, project, auto_fix, rounds, click_buttons, temperature, max_new_tokens)
            return run

        def stop():
            agent.user_stop.set()
            engine.stop()

        # Teks diambil dan kotak input dikosongkan dulu supaya terasa responsif, lalu agen berjalan.
        pending = gr.State("")
        submitted = prompt.submit(lambda t: ("", t), prompt, [prompt, pending], queue=False)
        runs = [submitted.then(handle, [pending, editor, project_state, *settings_in], outputs,
                               concurrency_limit=1, concurrency_id="gpu")]
        for btn, command in ((check_btn, "/cek"), (fix_btn, "/perbaiki"), (undo_btn, "/undo")):
            runs.append(btn.click(command_button(command), [editor, project_state, *settings_in], outputs,
                                  concurrency_limit=1, concurrency_id="gpu"))
        prompt.stop(stop, None, None, cancels=runs, queue=False)
        stop_btn.click(stop, None, None, cancels=runs, queue=False)
        # Pratinjau mengikuti editor saat fokus keluar; kodenya baru dipakai agen pada perintah berikutnya.
        editor.blur(lambda code: cg.preview_html(code or None), editor, preview, queue=False, show_progress="hidden")
        demo.load(None, None, None, js=FORCE_DARK_JS)
    return demo


def main():
    args = parse_args()
    import gradio as gr

    gr.close_all()  # tutup tampilan lama jika sel dijalankan ulang
    Path(args.workdir).mkdir(parents=True, exist_ok=True)
    engine = cg.get_engine(args)
    demo = build_app(engine, args)
    auth = tuple(args.auth.split(":", 1)) if args.auth else None
    demo.queue(default_concurrency_limit=1).launch(
        share=args.share, auth=auth, server_port=args.port, theme=cg.build_theme(gr), css=CSS, height=900,
        show_error=True, debug=not cg.IN_NOTEBOOK, allowed_paths=[str(Path(args.workdir).resolve())],
    )
    return demo


if __name__ == "__main__":
    main()
