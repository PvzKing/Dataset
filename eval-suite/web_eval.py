"""Web-eval: 10 prompt website baru yang dinilai otomatis di Chromium headless (Playwright).

Model menjawab setiap prompt seperti saat dipakai. File HTML di blok ```html diambil, dibuka tanpa akses jaringan
(website satu file harus berdiri sendiri), lalu diperiksa:
  html          ada satu dokumen HTML lengkap di jawaban
  tanpa_error   tidak ada error JavaScript atau console.error selama dibuka dan dipakai
  responsif     tidak ada scroll horizontal di layar HP 375 px
  fitur         interaksi utama prompt itu benar, misalnya 100 °C menjadi 212 °F atau data tetap ada setelah reload
Website lolos jika keempatnya lolos. Kolom format (ada bagian **Cek kebutuhan**) dicatat terpisah, tidak ikut menentukan.

Pemeriksaan sengaja longgar soal cara membangun UI (select atau tombol, form atau klik), tapi ketat soal hasilnya.
Prompt dan pemeriksaannya tidak boleh dijadikan sampel latihan.

Cara memakai di Google Colab (setelah sel pip install dan mount Drive dari PROSEDUR):

    !pip install -q playwright && playwright install --with-deps chromium
    REPO = "https://raw.githubusercontent.com/PvzKing/Dataset/main"
    !wget -q -O /content/web_eval.py {REPO}/eval-suite/web_eval.py
    %run /content/web_eval.py --adapter <folder lora-adapter>
    %run /content/web_eval.py --demo        # uji alur tanpa GPU: jawaban dari website rujukan

Secara bawaan model dasar juga diuji (adapter dimatikan sementara). Website yang dihasilkan disimpan di
<folder hasil>/<run>/situs/ untuk dibuka manual.
"""
import argparse
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

# ======================================================== CONFIG: ubah di sini ========================================
CONFIG = {
    "adapter": "/content/drive/MyDrive/finetune-id/qwen3.5-4b-own-4bit/lora-adapter",  # path, "auto", "none"
    "out": "/content/drive/MyDrive/finetune-id",
    "base_model": "unsloth/Qwen3.5-4B",
    "load_in_4bit": None,
    "max_seq_len": 8192,
    "batch_size": 2,                # website panjang: batch kecil supaya muat di VRAM T4
    "max_new_tokens": 6000,
    "results": None,                # None = <Drive>/finetune-id/eval-web
    "tag": None,
    "limit": None,
    "vs_base": True,
    "demo": False,
}
# ======================================================================================================================

HERE = Path(__file__).resolve().parent if "__file__" in globals() else Path.cwd()
REPO_RAW = "https://raw.githubusercontent.com/PvzKing/Dataset/main"

PROMPTS = {
    "konversi-satuan": "Buatkan aplikasi konversi satuan dalam satu file HTML untuk kategori panjang, berat, dan suhu. "
                       "Pengguna memilih kategori, satuan asal, dan satuan tujuan, lalu mengetik angka; hasilnya langsung "
                       "muncul tanpa perlu menekan tombol. Konversi suhu Celsius, Fahrenheit, dan Kelvin harus benar.",
    "pengeluaran": "bikin web pencatat pengeluaran harian. ada form keterangan, kategori, sama nominal, daftar "
                   "pengeluaran yang bisa dihapus, total dalam format Rupiah, ringkasan per kategori, dan datanya tetap "
                   "ada walaupun halaman di-refresh.",
    "galeri": "Buat halaman galeri foto responsif dengan lightbox. Klik foto untuk membuka tampilan besar, ada tombol "
              "sebelumnya/berikutnya dan tombol tutup, dan lightbox bisa ditutup dengan tombol Escape. Pakai gambar "
              "buatan sendiri (SVG atau gradien CSS), jangan file atau URL gambar dari luar.",
    "stopwatch": "Buatkan stopwatch dalam satu file HTML dengan tombol Mulai/Jeda, Reset, dan Putaran. Waktu "
                 "ditampilkan sampai perseratus detik (mm:ss.cc) dan daftar putaran menampilkan waktu tiap putaran.",
    "jam-dunia": "Buat halaman jam dunia yang menampilkan jam sekarang untuk WIB, WITA, WIT, Tokyo, London, dan New York "
                 "dalam format 24 jam, diperbarui setiap detik. Perhatikan zona waktu dan daylight saving untuk London "
                 "dan New York.",
    "seminar": "Buatkan landing page seminar \"AI untuk UMKM\" yang diadakan secara daring: info acara, jadwal sesi, "
               "profil pembicara (fiktif, beri tanda bahwa itu contoh), dan form RSVP berisi nama, email, dan nomor HP "
               "dengan validasi. Setelah form valid dikirim, tampilkan pesan terima kasih tanpa memuat ulang halaman.",
    "faq": "Buat halaman pusat bantuan untuk aplikasi dompet digital fiktif bernama DompetKu: minimal 8 pertanyaan FAQ "
           "berbentuk akordeon yang bisa dibuka-tutup, kolom pencarian yang langsung menyaring pertanyaan saat mengetik, "
           "dan pesan jika tidak ada hasil yang cocok.",
    "memori": "bikin game mencocokkan kartu (memory game) 4x4 pakai emoji. ada hitungan langkah dan waktu, kartu yang "
              "cocok tetap terbuka, tombol main lagi, dan pesan menang kalau semua pasangan ketemu.",
    "tabel": "Buatkan tabel data 30 mahasiswa (data contoh: NIM, nama, program studi, IPK) dengan kolom pencarian, "
             "pengurutan saat judul kolom diklik, dan pagination 10 baris per halaman.",
    "tanggal": "Buat kalkulator selisih tanggal: pengguna memilih tanggal awal dan tanggal akhir, lalu ditampilkan "
               "selisihnya dalam hari (tanggal akhir dikurangi tanggal awal), dalam minggu dan sisa hari, serta jumlah "
               "hari kerja Senin–Jumat di antara kedua tanggal itu.",
}

def import_eval_humaneval():
    """Generator, McNemar, dan perbandingan dipakai bersama dengan eval_humaneval.py (diunduh jika belum ada)."""
    import urllib.request

    path = HERE.parent / "humaneval-bench-script" / "eval_humaneval.py"
    if not path.is_file():
        path = HERE / "eval_humaneval.py"
        if not path.is_file():
            urllib.request.urlretrieve(f"{REPO_RAW}/humaneval-bench-script/eval_humaneval.py", path)
    if str(path.parent) not in sys.path:
        sys.path.insert(0, str(path.parent))
    import eval_humaneval
    return eval_humaneval


HTML_BLOCK = re.compile(r"```[ \t]*html[ \t]*\n(.*?)```", re.S | re.I)
MAPPING = re.compile(r"^\s*- .+→", re.M)


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--adapter")
    parser.add_argument("--out")
    parser.add_argument("--base-model")
    parser.add_argument("--load-in-4bit", action=argparse.BooleanOptionalAction, default=None)
    parser.add_argument("--max-seq-len", type=int)
    parser.add_argument("--batch-size", type=int)
    parser.add_argument("--max-new-tokens", type=int)
    parser.add_argument("--results")
    parser.add_argument("--tag")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--vs-base", action=argparse.BooleanOptionalAction, default=None)
    parser.add_argument("--demo", action="store_true", default=None)
    parser.add_argument("--nilai", help=argparse.SUPPRESS)  # dipakai internal: nilai satu folder run di proses terpisah
    args, _ = parser.parse_known_args(sys.argv[1:])
    for key, value in CONFIG.items():
        if getattr(args, key, None) is None:
            setattr(args, key, value)
    args.dataset = "web"
    if (not args.demo and not args.nilai and args.adapter not in ("auto", "none")
            and not (Path(args.adapter) / "adapter_config.json").is_file()):
        raise SystemExit(f"adapter tidak ditemukan: {args.adapter}")
    return args


def extract_html(output):
    """Dokumen HTML terpanjang di blok ```html; None jika tidak ada dokumen lengkap."""
    docs = [b.strip() for b in HTML_BLOCK.findall(output) if re.search(r"<html|<!doctype", b, re.I)]
    return max(docs, key=len) if docs else None


# ---------------------------------------------------------------- pemeriksaan (dijalankan di proses terpisah)

def visible_text(page):
    """Teks yang terlihat ditambah nilai input/output, karena hasil sering ditulis ke <input> atau <output>."""
    return page.evaluate("""() => document.body.innerText + '\\n' +
        [...document.querySelectorAll('input, output, textarea')].map(e => e.value ?? e.textContent).join('\\n')""")


def button(page, pattern):
    """Elemen mirip tombol pertama yang terlihat dan labelnya cocok dengan pola."""
    loc = page.locator("button, [role=button], input[type=button], input[type=submit], a, summary")
    for i in range(loc.count()):
        el = loc.nth(i)
        if not el.is_visible():
            continue
        label = el.evaluate("e => (e.innerText || e.value || e.getAttribute('aria-label') || e.title || '').trim()")
        if re.search(pattern, label, re.I):
            return el
    return None


def choose(select, pattern):
    index = select.evaluate("(s, p) => [...s.options].findIndex(o => new RegExp(p, 'i').test(o.textContent + ' ' + o.value))",
                            pattern)
    if index < 0:
        return False
    select.select_option(index=index)
    return True


def editable_inputs(page, types=("number", "text", "")):
    """Input yang bisa diketik dan terlihat, sesuai urutan di halaman."""
    loc = page.locator("input")
    found = []
    for i in range(loc.count()):
        el = loc.nth(i)
        info = el.evaluate("e => [e.type, e.readOnly || e.disabled, e.getAttribute('type') || '']")
        if el.is_visible() and not info[1] and (info[2].lower() in types or info[0] in types):
            found.append(el)
    return found


def mark_repeated(page, minimum, min_w, min_h, mark):
    """Tandai elemen pertama yang punya >= minimum saudara sejenis berukuran mirip (kartu, item galeri)."""
    return page.evaluate("""([minimum, minW, minH, mark]) => {
        const ok = e => { const r = e.getBoundingClientRect(), s = getComputedStyle(e);
            return r.width >= minW && r.height >= minH && s.visibility !== 'hidden' && s.display !== 'none'
                && s.position !== 'fixed'; };
        for (const e of document.querySelectorAll('body *')) {
            if (!e.parentElement || !ok(e)) continue;
            const same = [...e.parentElement.children].filter(c => c.tagName === e.tagName && ok(c));
            if (same.length >= minimum) { e.setAttribute('data-ujiweb', mark); return same.length; }
        }
        return 0; }""", [minimum, min_w, min_h, mark])


def overlays(page):
    return page.evaluate("""() => [...document.querySelectorAll('body *')].filter(e => {
        const s = getComputedStyle(e), r = e.getBoundingClientRect();
        const layer = s.position === 'fixed' || (e.tagName === 'DIALOG' && e.open);
        return layer && s.display !== 'none' && s.visibility !== 'hidden' && +s.opacity > 0.05
            && r.width * r.height > innerWidth * innerHeight * 0.5; }).length""")


def check_konversi(page):
    picked = any(choose(s, "suhu|temperatur") for s in page.locator("select").all() if s.is_visible())
    if not picked and (b := button(page, r"suhu|temperatur")):
        b.click()
    page.wait_for_timeout(300)
    selects = [s for s in page.locator("select").all() if s.is_visible()
               and s.evaluate("s => [...s.options].some(o => /celsius|°c/i.test(o.textContent + o.value))")]
    if len(selects) < 2:
        return False, "tidak ada dua pilihan satuan suhu (Celsius dan Fahrenheit)"
    if not (choose(selects[0], "celsius|°c") and choose(selects[1], "fahrenheit|°f")):
        return False, "satuan Celsius/Fahrenheit tidak bisa dipilih"
    fields = editable_inputs(page)
    if not fields:
        return False, "tidak ada kolom angka"
    fields[0].fill("100")
    page.wait_for_timeout(400)
    if re.search(r"\b212\b", visible_text(page)):
        return True, ""
    return False, "100 °C tidak menghasilkan 212 °F tanpa menekan tombol"


def check_pengeluaran(page):
    texts = editable_inputs(page, ("text", ""))
    numbers = editable_inputs(page, ("number",)) or [t for t in texts if re.search(
        r"nominal|jumlah|harga|rp", t.evaluate("e => (e.name + e.id + e.placeholder + (e.labels?.[0]?.innerText || ''))"), re.I)]
    if not texts or not numbers:
        return False, "form keterangan atau nominal tidak ditemukan"
    texts[0].fill("Makan siang uji")
    for t in texts[1:]:
        if t not in numbers and not t.input_value():
            t.fill("Makan")
    numbers[0].fill("25000")
    for d in editable_inputs(page, ("date",)):
        if not d.input_value():
            d.fill("2026-10-11")
    for s in page.locator("select").all():
        if s.is_visible() and not s.input_value():
            s.select_option(index=1)
    if b := button(page, r"tambah|simpan|catat|^\+$|kirim"):
        b.click()
    else:
        numbers[0].press("Enter")
    page.wait_for_timeout(400)
    text = visible_text(page)
    if "Makan siang uji" not in text or not re.search(r"25\.000", text):
        return False, "pengeluaran baru atau nominal Rp25.000 tidak tampil"
    page.reload()
    page.wait_for_timeout(600)
    if "Makan siang uji" not in visible_text(page):
        return False, "data hilang setelah halaman dimuat ulang"
    return True, ""


def check_galeri(page):
    before = overlays(page)
    if mark_repeated(page, 6, 80, 60, "galeri") == 0:
        return False, "tidak ada deretan minimal 6 foto"
    page.locator("[data-ujiweb=galeri]").first.click()
    page.wait_for_timeout(500)
    if overlays(page) <= before:
        return False, "klik foto tidak membuka tampilan besar"
    page.keyboard.press("Escape")
    page.wait_for_timeout(500)
    if overlays(page) > before:
        return False, "tombol Escape tidak menutup lightbox"
    return True, ""


def times(page):
    return re.findall(r"\b\d{1,2}:\d{2}[.,:]\d{2}\b", visible_text(page))


def check_stopwatch(page):
    start = button(page, r"mulai|start|▶")
    if not start:
        return False, "tombol Mulai tidak ditemukan"
    initial = times(page)
    start.click()
    page.wait_for_timeout(1300)
    running = times(page)
    if running == initial or all(re.fullmatch(r"0?0:00[.,:]00", t) for t in running):
        return False, "waktu tidak berjalan setelah Mulai"
    lap = button(page, r"putaran|lap")
    if not lap:
        return False, "tombol Putaran tidak ditemukan"
    lap.click()
    page.wait_for_timeout(300)
    if len(times(page)) <= len(running):
        return False, "Putaran tidak menambah daftar waktu"
    if pause := button(page, r"jeda|pause|berhenti|stop"):
        pause.click()
    reset = button(page, r"reset|ulang")
    if not reset:
        return False, "tombol Reset tidak ditemukan"
    reset.click()
    page.wait_for_timeout(300)
    if not re.search(r"\b0?0:00[.,:]00\b", visible_text(page)):
        return False, "Reset tidak mengembalikan waktu ke 00:00.00"
    return True, ""


def check_jam_dunia(page):
    from zoneinfo import ZoneInfo

    text = visible_text(page)
    for label in ("WIB", "WITA", "WIT", "Tokyo", "London", "New York"):
        if label.lower() not in text.lower():
            return False, f"label {label} tidak tampil"
    now = datetime.now()
    for tz in ("Asia/Jakarta", "Asia/Makassar", "Asia/Jayapura", "Asia/Tokyo", "Europe/London", "America/New_York"):
        local = datetime.now(ZoneInfo(tz))
        expected = {(local + timedelta(minutes=d)).strftime(f"%H{sep}%M") for d in (-1, 0, 1) for sep in (":", ".")}
        if not any(e in text for e in expected):
            return False, f"jam {tz} tidak sesuai (diharapkan sekitar {local:%H:%M})"
    page.wait_for_timeout(1200)
    if visible_text(page) == text and datetime.now() - now < timedelta(seconds=5):
        return False, "jam tidak diperbarui setiap detik"
    return True, ""


def check_seminar(page):
    emails = editable_inputs(page, ("email",)) or [t for t in editable_inputs(page, ("text", "")) if re.search(
        "mail", t.evaluate("e => e.name + e.id + e.placeholder + (e.labels?.[0]?.innerText || '')"), re.I)]
    if not emails:
        return False, "kolom email tidak ditemukan"
    email = emails[0]
    others = [t for t in editable_inputs(page, ("text", "", "tel")) if t not in emails]
    for t in others:
        kind = t.evaluate("e => e.type + e.name + e.id + e.placeholder + (e.labels?.[0]?.innerText || '')")
        t.fill("081234567890" if re.search(r"tel|hp|telepon|whatsapp|wa\b|ponsel", kind, re.I) else "Budi Santoso")
    page.evaluate("() => { window.__ujiweb = 1; }")
    count = lambda: len(re.findall(r"terima\s*kasih", page.evaluate("() => document.body.innerText"), re.I))
    before = count()

    def submit():
        # Kirim form yang memuat kolom email. requestSubmit() sama dengan menekan tombol kirim (termasuk validasi
        # bawaan browser) tanpa bergantung pada posisi tombol, yang bisa bergeser saat pesan error muncul atau hilang.
        # Tautan navigasi seperti "Daftar" atau "#rsvp" bukan pengirim, jadi tidak dicari lewat teks.
        form = email.locator("xpath=ancestor::form[1]")
        if form.count():
            form.evaluate("f => f.requestSubmit()")
        else:
            loc = page.locator("button, input[type=submit], input[type=button]")
            matches = [loc.nth(i) for i in range(loc.count()) if loc.nth(i).is_visible() and re.search(
                r"daftar|kirim|rsvp|submit|konfirmasi|ikut", loc.nth(i).evaluate("e => e.innerText || e.value"), re.I)]
            matches[0].click() if matches else email.press("Enter")
        page.wait_for_timeout(500)

    email.fill("bukan-email")
    submit()
    if page.evaluate("() => window.__ujiweb") != 1:
        return False, "halaman dimuat ulang saat form dikirim"
    if count() > before:
        return False, "pesan terima kasih muncul walaupun email tidak valid"
    email.fill("budi@contoh.id")
    submit()
    if page.evaluate("() => window.__ujiweb") != 1:
        return False, "halaman dimuat ulang saat form dikirim"
    if count() <= before:
        return False, "pesan terima kasih tidak muncul setelah data valid dikirim"
    return True, ""


def check_faq(page):
    fields = editable_inputs(page, ("search", "text", ""))
    if not fields:
        return False, "kolom pencarian tidak ditemukan"
    fields[0].fill("zzqxjv")
    page.wait_for_timeout(400)
    if not re.search(r"tidak (ada|ditemukan|cocok)|belum ada|tak ada|no result|0 hasil", visible_text(page), re.I):
        return False, "tidak ada pesan saat pencarian tanpa hasil"
    fields[0].fill("")
    page.wait_for_timeout(400)
    toggle = page.locator("summary, [aria-expanded]").first
    if not toggle.count() or not toggle.is_visible():
        mark_repeated(page, 8, 100, 20, "faq")
        toggle = page.locator("[data-ujiweb=faq]").first
        if not toggle.count():
            return False, "tidak ada daftar minimal 8 pertanyaan"
    state = lambda: page.evaluate("""() => [document.body.innerText.length, document.body.getBoundingClientRect().height,
        document.querySelectorAll('[aria-expanded=true], details[open]').length]""")
    before = state()
    toggle.click()
    page.wait_for_timeout(600)
    after = state()
    if not (after[0] > before[0] + 15 or after[1] > before[1] + 10 or after[2] > before[2]):
        return False, "klik pertanyaan tidak membuka jawabannya"
    return True, ""


def check_memori(page):
    if mark_repeated(page, 16, 40, 40, "kartu") < 16:
        return False, "tidak ada 16 kartu"
    card = page.locator("[data-ujiweb=kartu]").first
    # Isi dan atribut kartu (kelas, style inline, aria), bukan gaya hasil CSS: efek :hover juga mengubah transform.
    state = "e => e.outerHTML.replace(/ data-ujiweb=\"kartu\"/, '') + e.innerText"
    before = card.evaluate(state)
    card.click()
    page.wait_for_timeout(700)
    after = card.evaluate(state)
    if after == before:
        return False, "klik kartu tidak membalik kartu"
    return True, ""


def check_tabel(page):
    rows = lambda: [r for r in page.locator("tbody tr").all() if r.is_visible()]
    first = rows()
    if not 1 <= len(first) <= 10:
        return False, f"{len(first)} baris terlihat, seharusnya 1–10 per halaman"
    cells = [c.inner_text().strip() for c in first[0].locator("td").all()]
    name = max((c for c in cells if re.fullmatch(r"[A-Za-z' .]{4,}", c)), key=len, default="")
    search = editable_inputs(page, ("search", "text", ""))
    if not name or not search:
        return False, "kolom pencarian atau nama di tabel tidak ditemukan"
    search[0].fill(name)
    page.wait_for_timeout(400)
    found = rows()
    if not found or len(found) > len(first) or any(name not in r.inner_text() for r in found):
        return False, "pencarian nama tidak menyaring baris"
    search[0].fill("")
    page.wait_for_timeout(400)
    header = page.locator("th").filter(has_text=re.compile("IPK", re.I)).first
    if not header.count():
        return False, "judul kolom IPK tidak ditemukan"
    top = rows()[0].inner_text()
    header.click()
    page.wait_for_timeout(300)
    if rows()[0].inner_text() == top:
        header.click()
        page.wait_for_timeout(300)
        if rows()[0].inner_text() == top:
            return False, "klik judul kolom tidak mengubah urutan"
    nxt = button(page, r"berikut|selanjutnya|next|›|»|→|^2$")
    if not nxt:
        return False, "tombol halaman berikutnya tidak ditemukan"
    top = rows()[0].inner_text()
    nxt.click()
    page.wait_for_timeout(300)
    if rows()[0].inner_text() == top:
        return False, "pindah halaman tidak mengubah isi tabel"
    return True, ""


def check_tanggal(page):
    dates = editable_inputs(page, ("date",))
    if len(dates) < 2:
        return False, "tidak ada dua input tanggal"
    dates[0].fill("2026-01-01")
    dates[1].fill("2026-01-31")
    if b := button(page, r"hitung|cek|proses"):
        b.click()
    page.wait_for_timeout(400)
    text = visible_text(page)
    if not re.search(r"\b30\b", text):
        return False, "selisih 1–31 Januari 2026 bukan 30 hari"
    if not (re.search(r"\b4\s*minggu", text, re.I) and re.search(r"\b2\s*hari", text, re.I)):
        return False, "30 hari tidak ditampilkan sebagai 4 minggu 2 hari"
    if not re.search(r"\b2[12]\b", text):
        return False, "jumlah hari kerja tidak 21 atau 22"
    return True, ""


CHECKS = {"konversi-satuan": check_konversi, "pengeluaran": check_pengeluaran, "galeri": check_galeri,
          "stopwatch": check_stopwatch, "jam-dunia": check_jam_dunia, "seminar": check_seminar, "faq": check_faq,
          "memori": check_memori, "tabel": check_tabel, "tanggal": check_tanggal}


def judge_site(browser, path, site_id):
    """Nilai satu file HTML. Kembalikan dict hasil per pemeriksaan."""
    result = {"tanpa_error": True, "responsif": False, "fitur": False, "alasan": ""}
    errors = []
    context = browser.new_context(viewport={"width": 1280, "height": 800})
    # Tanpa jaringan: hanya file itu sendiri yang boleh dimuat.
    context.route("**/*", lambda route: route.continue_() if route.request.url.startswith("file:") else route.abort())
    page = context.new_page()
    page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
    page.on("console", lambda m: m.type == "error" and not re.search(r"Failed to load resource|net::ERR", m.text)
            and errors.append(f"console: {m.text}"))
    page.set_default_timeout(3000)
    try:
        page.goto(path.resolve().as_uri())
        page.wait_for_timeout(800)
        page.set_viewport_size({"width": 375, "height": 740})
        page.wait_for_timeout(300)
        result["responsif"] = page.evaluate("() => document.documentElement.scrollWidth <= innerWidth + 1")
        page.set_viewport_size({"width": 1280, "height": 800})
        page.wait_for_timeout(200)
        ok, reason = CHECKS[site_id](page)
        result["fitur"], result["alasan"] = ok, reason
    except Exception as e:
        result["alasan"] = f"pemeriksaan gagal: {str(e).splitlines()[0][:200]}"
    finally:
        context.close()
    if errors:
        result["tanpa_error"] = False
        result["error"] = errors[:3]
    if not result["responsif"] and not result["alasan"]:
        result["alasan"] = "ada scroll horizontal di layar 375 px"
    return result


def judge_run(run_dir):
    """Proses terpisah: Playwright sync API tidak bisa berjalan di dalam event loop notebook."""
    from playwright.sync_api import sync_playwright

    answers = {r["task_id"]: r["output"] for r in map(json.loads, (run_dir / "jawaban.jsonl").read_text().splitlines())}
    site_dir = run_dir / "situs"
    site_dir.mkdir(exist_ok=True)
    rows = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for site_id in PROMPTS:
            if site_id not in answers:
                continue
            output = answers[site_id]
            html = extract_html(output)
            row = {"task_id": site_id, "html": html is not None,
                   "format": "cek kebutuhan" in output.lower() and len(MAPPING.findall(output)) >= 2}
            if html is None:
                row.update(tanpa_error=False, responsif=False, fitur=False, alasan="tidak ada dokumen HTML lengkap")
            else:
                path = site_dir / f"{site_id}.html"
                path.write_text(html)
                row.update(judge_site(browser, path, site_id))
            row["base"] = row["html"] and row["tanpa_error"] and row["responsif"] and row["fitur"]
            rows.append(row)
        browser.close()
    (run_dir / "hasil.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))


# ---------------------------------------------------------------- generate dan ringkasan

def demo_answer(site_id, use_adapter, index):
    # Website rujukan; "dasar" tanpa bagian Cek kebutuhan dan tiap website ke-3 diberi error JavaScript.
    local = HERE / "web" / "referensi" / f"{site_id}.html"
    if not local.is_file():  # di Colab: unduh website rujukan dari repo
        import urllib.request
        local.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(f"{REPO_RAW}/eval-suite/web/referensi/{site_id}.html", local)
    html = local.read_text()
    if not use_adapter and index % 3 == 0:
        html = html.replace("</body>", "<script>belumAda();</script>\n</body>")
    notes = "\n\n**Cek kebutuhan**\n- **fitur utama** → sudah ada\n- **tampilan HP** → responsif" if use_adapter else ""
    return f"Berikut websitenya.\n\n```html\n{html}\n```{notes}\n"


def run_one(eh, args, tag, model_label, use_adapter, results_dir, get_generator):
    run_dir = results_dir / tag
    run_dir.mkdir(parents=True, exist_ok=True)
    responses_path = run_dir / "jawaban.jsonl"
    print(f"\n##### run: {tag} ({model_label})\nfolder hasil: {run_dir}", flush=True)
    ids = list(PROMPTS)[:args.limit] if args.limit else list(PROMPTS)
    done = {r["task_id"] for r in eh.read_jsonl(responses_path)}
    todo = [i for i in ids if i not in done]
    gen_info = {}
    if todo:
        start, n_tokens = time.time(), 0
        generator = None if args.demo else get_generator()
        for i in range(0, len(todo), args.batch_size):
            batch = todo[i:i + args.batch_size]
            if args.demo:
                texts, tokens = [demo_answer(s, use_adapter, list(PROMPTS).index(s)) for s in batch], 0
            else:
                prompts = [generator.engine.render([{"role": "user", "content": PROMPTS[s]}], thinking=False)
                           for s in batch]
                texts, tokens = generator.generate(prompts, use_adapter, args.max_new_tokens)
            n_tokens += tokens
            eh.append_jsonl(responses_path, [{"task_id": s, "output": o} for s, o in zip(batch, texts)])
            elapsed = time.time() - start
            print(f"[{tag}] {i + len(batch)}/{len(todo)} website, {elapsed / 60:.1f} menit"
                  + (f", {n_tokens / elapsed:.0f} token/detik" if n_tokens else ""), flush=True)
        gen_info = {"menit_generate": round((time.time() - start) / 60, 1), "token_baru": n_tokens}
    subprocess.run([sys.executable, str(Path(__file__).resolve()), "--nilai", str(run_dir)], check=True)
    rows = [r for r in eh.read_jsonl(run_dir / "hasil.jsonl") if r["task_id"] in ids]
    n, ok = len(rows), sum(r["base"] for r in rows)
    summary = {"tag": tag, "model": model_label, "dataset": "web", "soal": n, "web_lolos": round(ok / n, 6),
               "format_cek_kebutuhan": sum(r["format"] for r in rows),
               "gagal": {r["task_id"]: r["alasan"] or "; ".join(r.get("error", [])) for r in rows if not r["base"]},
               **gen_info}
    (run_dir / "ringkasan.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"\n===== {tag}: Web-eval, {n} website =====")
    print(f"lolos: {ok}/{n}   format Cek kebutuhan: {summary['format_cek_kebutuhan']}/{n}")
    print(f"| {'website':<16} | html | tanpa error | responsif | fitur | alasan")
    for r in rows:
        mark = lambda v: "ya" if v else "TIDAK"
        reason = r["alasan"] or "; ".join(r.get("error", []))
        print(f"| {r['task_id']:<16} | {mark(r['html']):<4} | {mark(r['tanpa_error']):<11} | {mark(r['responsif']):<9} "
              f"| {mark(r['fitur']):<5} | {reason[:90]}")
    return rows


def main():
    args = parse_args()
    if args.nilai:
        judge_run(Path(args.nilai))
        return
    eh = import_eval_humaneval()
    results_dir = Path(args.results or eh.default_results("eval-web"))
    generator = None

    def get_generator():
        nonlocal generator
        if generator is None:
            generator = eh.Generator(args)
        return generator

    tag = eh.run_tag(args)
    label = "demo" if args.demo else ("model dasar" if args.adapter == "none" else args.adapter)
    rows = run_one(eh, args, tag, label, True, results_dir, get_generator)
    if args.vs_base and args.adapter != "none":
        prefix = args.tag or ("demo" if args.demo else "")
        base_tag = f"{prefix}-model-dasar" if prefix else "model-dasar"
        base_rows = run_one(eh, args, base_tag, f"{args.base_model} (adapter dimatikan)", False, results_dir,
                            get_generator)
        eh.compare(rows, base_rows, tag, base_tag, results_dir, names=("Web-eval",), short=lambda ids: ", ".join(ids) or "-")


if __name__ == "__main__":
    main()
