"""Crawler penemu dataset: mencari kandidat dataset di Hugging Face Hub dan menilai lisensinya.

Script ini hanya membaca katalog lewat API resmi Hugging Face (daftar dataset dan dataset card),
ditambah beberapa baris contoh dari dataset viewer resmi Hugging Face. Dataset tidak diunduh utuh
dan halaman web tidak di-scrape. Hasilnya laporan kandidat untuk direview manusia sebelum ada data
yang dipakai.

Pemakaian (butuh akses internet ke huggingface.co):
    python scripts/find_datasets.py
    python scripts/find_datasets.py --search instruct --task text-generation --top 30
    python scripts/find_datasets.py --only-permissive --min-downloads 100
    python scripts/find_datasets.py --no-cards        # lebih cepat, tanpa membaca dataset card
    python scripts/find_datasets.py --preview 5       # ambil 5 baris contoh per kandidat (0 = tidak mengambil)
    python scripts/find_datasets.py --preset coding   # dataset coding (semua bahasa), diurutkan menurut skor kualitas
    python scripts/find_datasets.py --preset coding --live   # tonton laba-labanya merayap selama crawl berjalan

Laporan ditulis ke runs/kandidat_dataset.* (atau runs/kandidat_coding.* untuk preset coding) dalam
format .md, .json, dan .html. File .html adalah visualisasi laba-laba yang memutar ulang jalannya
crawl. Dengan --live, script menjalankan server kecil di http://127.0.0.1:8765 dan membuka browser
supaya jaringnya bisa ditonton tumbuh selama crawl berjalan. Isi variabel lingkungan HF_TOKEN
(opsional) untuk batas request yang lebih longgar.
"""
import argparse
import json
import math
import os
import re
import sys
import threading
import time
import webbrowser
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
VIZ_TEMPLATE = Path(__file__).resolve().parent / "crawler_viz.html"
VIZ_PLACEHOLDER = '<script id="crawl-data" type="application/json">null</script>'
API = "https://huggingface.co/api/datasets"
CARD_URL = "https://huggingface.co/datasets/{id}/raw/main/README.md"
VIEWER_API = "https://datasets-server.huggingface.co"
# Baris contoh dipotong supaya laporan tetap kecil: teks panjang, list, dan objek bersarang diringkas.
PREVIEW_CHARS = 1500
PREVIEW_ITEMS = 12
USER_AGENT = "Dataset-ID-finder/1.0 (+https://github.com/PvzKing/Dataset)"

# Status lisensi, dari yang paling longgar ke yang paling ketat. Jika satu dataset punya beberapa
# lisensi, yang dipakai adalah yang paling ketat.
STATUSES = ["permisif", "share-alike", "bersyarat", "cek manual", "nonkomersial", "tanpa turunan"]

PERMISSIVE = {
    "apache-2.0", "mit", "bsd", "bsd-2-clause", "bsd-3-clause", "bsd-3-clause-clear", "isc", "zlib",
    "unlicense", "wtfpl", "bsl-1.0", "postgresql", "ncsa", "afl-3.0", "ecl-2.0", "ms-pl",
    "cc0-1.0", "cc-by-2.0", "cc-by-2.5", "cc-by-3.0", "cc-by-4.0", "odc-by", "pddl",
    "cdla-permissive-1.0", "cdla-permissive-2.0", "etalab-2.0",
}
SHARE_ALIKE = re.compile(r"(^|-)sa(-|$)|^odbl|^cdla-sharing|^(a|l)?gpl|^gfdl|^mpl|^epl|^eupl|^osl|^cc-by-sa")
NONCOMMERCIAL = re.compile(r"(^|-)nc(-|$)|noncommercial|non-commercial")
NO_DERIVATIVES = re.compile(r"(^|-)nd(-|$)")
# Lisensi model/data yang memuat batasan penggunaan (use-based restrictions) atau syarat khusus.
CONDITIONAL = re.compile(r"openrail|llama|gemma|c-uda|deepfloyd|bigscience|bigcode|intel-research")

# Kolom yang menandakan data sudah berbentuk instruksi/percakapan, cocok diubah ke format messages.
CHAT_COLUMNS = {"messages", "conversations", "conversation", "dialog", "dialogue", "turns"}
INSTRUCT_COLUMNS = {"instruction", "prompt", "input", "query", "inputs", "problem"}
RESPONSE_COLUMNS = {"output", "response", "completion", "answer", "targets", "chosen", "solution"}

# Tanda di dataset card bahwa jawaban dibuat oleh model lain: syarat penggunaan penyedia model
# bisa membatasi pemakaiannya untuk melatih model.
MODEL_OUTPUT = re.compile(
    r"\b(gpt-?3\.5|gpt-?4o?|chatgpt|openai|text-davinci|claude|gemini|self-instruct|alpaca|"
    r"distill(ed)? from|generated (by|with|using) (an? )?(llm|model|gpt|claude|gemini|llama|mistral|qwen))\b",
    re.IGNORECASE,
)
# Tanda bahwa isinya diambil dari media sosial atau ulasan pengguna: kemungkinan berisi data pribadi
# (UU No. 27 Tahun 2022 tentang PDP), juga syarat layanan platform asalnya.
SOCIAL_SOURCE = re.compile(
    r"\b(twitter|tweets?|x\.com|instagram|facebook|tiktok|reddit|kaskus|youtube comments?|"
    r"user reviews?|ulasan (pengguna|pelanggan)|komentar (pengguna|warganet)|play ?store reviews?)\b",
    re.IGNORECASE,
)


# Preset coding: kata kunci pencarian di nama dataset, ditambah satu pencarian per tag `code`.
CODING_SEARCHES = ["code", "coding", "program", "python", "javascript", "sql"]
CODING_ID = re.compile(r"code|coding|program|python|javascript|typescript|sql|leetcode|humaneval|mbpp")
NOT_CODING_ID = re.compile(r"barcode|qrcode|qr-code|postcode|post-code|zipcode|zip-code|zip_code|decode|encode|"
                           r"unicode|morse|genetic|icd|codebook|code-?switch|codemix|code-mix", re.IGNORECASE)
CODE_COLUMNS = {"code", "solution", "solutions", "canonical_solution", "test", "tests", "test_list",
                "test_cases", "unit_tests", "function", "func_code_string", "starter_code"}

# Sinyal kualitas di dataset card. Jawaban yang diverifikasi dengan menjalankan tes jauh lebih bisa
# dipercaya daripada jawaban model yang tidak pernah dijalankan.
VERIFIED = re.compile(r"\b(unit tests?|test cases|executed|execution[- ](based|feedback|verified|filter\w*)|"
                      r"pass@\d|passes (all )?(the )?tests|verified (by|with|using|solutions?)|sandbox)\b", re.IGNORECASE)
DECONTAMINATED = re.compile(r"decontaminat\w*", re.IGNORECASE)
DEDUPLICATED = re.compile(r"\b(dedup\w*|near-duplicate|minhash)\b", re.IGNORECASE)
PII_FILTERED = re.compile(r"\b(pii|personal(ly)? identifiable|secrets?|api keys?|redact\w*)\b", re.IGNORECASE)
# Benchmark dipakai untuk mengukur model. Melatih dengan isinya membuat skor evaluasi tidak bersih.
BENCHMARK_ID = re.compile(r"humaneval|mbpp|evalplus|livecodebench|bigcodebench|apps\b|codecontests|ds-1000|swe-bench|cruxeval",
                          re.IGNORECASE)
# Soal dari situs kompetisi/latihan: teks soal dilindungi hak cipta dan syarat layanan situsnya
# umumnya melarang pengambilan otomatis.
CONTEST_SOURCE = re.compile(r"\b(leetcode|codeforces|atcoder|hackerrank|codechef|codewars|kattis|topcoder)\b", re.IGNORECASE)
# Korpus kode mentah dari repositori publik: setiap file punya lisensinya sendiri (termasuk GPL).
RAW_CODE_COLUMNS = {"repo_name", "path", "max_stars_repo_name", "repository_name", "file_path"}


def make_session():
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    token = os.environ.get("HF_TOKEN")
    if token:
        session.headers["Authorization"] = f"Bearer {token}"
    return session


class Fetcher:
    """GET dengan jeda antar-request dan penghormatan terhadap HTTP 429 (Retry-After)."""

    def __init__(self, session, delay):
        self.session = session
        self.delay = delay
        self.last = 0.0

    def get(self, url, params=None, retries=3):
        for attempt in range(retries + 1):
            wait = self.delay - (time.monotonic() - self.last)
            if wait > 0:
                time.sleep(wait)
            self.last = time.monotonic()
            resp = self.session.get(url, params=params, timeout=30)
            if resp.status_code != 429 or attempt == retries:
                return resp
            retry_after = resp.headers.get("Retry-After", "")
            pause = int(retry_after) if retry_after.isdigit() else 30 * (attempt + 1)
            print(f"  dibatasi server (429), menunggu {pause} detik ...", file=sys.stderr)
            time.sleep(pause)
        return resp


def license_status(name):
    name = name.strip().lower()
    if not name or name in ("unknown", "other", "none"):
        return "cek manual"
    if NO_DERIVATIVES.search(name):
        return "tanpa turunan"
    if NONCOMMERCIAL.search(name):
        return "nonkomersial"
    if SHARE_ALIKE.search(name):
        return "share-alike"
    if CONDITIONAL.search(name):
        return "bersyarat"
    if name in PERMISSIVE:
        return "permisif"
    return "cek manual"


def licenses_of(item):
    names = [t.split(":", 1)[1] for t in item.get("tags", []) if t.startswith("license:")]
    card_license = (item.get("cardData") or {}).get("license")
    if isinstance(card_license, str):
        card_license = [card_license]
    for name in card_license or []:
        if isinstance(name, str) and name.lower() not in names:
            names.append(name.lower())
    return names


def tag_values(item, prefix):
    return [t.split(":", 1)[1] for t in item.get("tags", []) if t.startswith(prefix + ":")]


def feature_names(node):
    """Kumpulkan nama kolom dari dataset_info di metadata card (bentuknya bisa dict atau list per config)."""
    names = set()
    if isinstance(node, dict):
        features = node.get("features")
        if isinstance(features, list):
            names.update(f["name"].lower() for f in features if isinstance(f, dict) and isinstance(f.get("name"), str))
        for value in node.values():
            if isinstance(value, (dict, list)):
                names |= feature_names(value)
    elif isinstance(node, list):
        for value in node:
            names |= feature_names(value)
    return names


def data_shape(columns):
    if columns & CHAT_COLUMNS:
        return "percakapan"
    if columns & INSTRUCT_COLUMNS and columns & RESPONSE_COLUMNS:
        return "instruksi"
    if {"question", "answer"} <= columns or {"question", "answers"} <= columns:
        return "tanya-jawab"
    return "teks/lainnya" if columns else "tidak diketahui"


def summarize(item):
    licenses = licenses_of(item)
    statuses = [license_status(n) for n in licenses] or ["cek manual"]
    columns = feature_names((item.get("cardData") or {}).get("dataset_info"))
    notes = []
    if item.get("gated"):
        notes.append("gated: harus menyetujui syarat pemilik sebelum mengunduh")
    return {
        "id": item["id"],
        "url": f"https://huggingface.co/datasets/{item['id']}",
        "licenses": licenses,
        "license_status": max(statuses, key=STATUSES.index),
        "downloads": item.get("downloads", 0),
        "likes": item.get("likes", 0),
        "last_modified": (item.get("lastModified") or "")[:10],
        "size": ", ".join(tag_values(item, "size_categories")) or "-",
        "tasks": tag_values(item, "task_categories"),
        "languages": tag_values(item, "language"),
        "columns": sorted(columns),
        "shape": data_shape(columns),
        "gated": bool(item.get("gated")),
        "notes": notes,
        "signals": [],
        "score": None,
    }


def check_card(fetcher, candidate, coding=False):
    """Baca dataset card dan tandai risiko yang perlu dicek manual. Teks card hanya dicocokkan pola, tidak dieksekusi."""
    resp = fetcher.get(CARD_URL.format(id=candidate["id"]))
    if resp.status_code != 200:
        candidate["notes"].append(f"dataset card tidak bisa dibaca (HTTP {resp.status_code})")
        return
    text = resp.text
    if coding:
        check_coding_card(candidate, text)
    hits = sorted({m.group(0).lower() for m in MODEL_OUTPUT.finditer(text)})
    if hits:
        candidate["notes"].append(f"mungkin berisi output model lain ({', '.join(hits[:4])}): cek syarat penggunaan penyedia model")
    hits = sorted({m.group(0).lower() for m in SOCIAL_SOURCE.finditer(text)})
    if hits:
        candidate["notes"].append(f"sumber media sosial/ulasan ({', '.join(hits[:4])}): cek data pribadi (UU PDP) dan syarat platform")
    if len(text.strip()) < 300:
        candidate["notes"].append("dataset card sangat singkat: asal-usul data tidak jelas")


def shorten(value, depth=0):
    if isinstance(value, str):
        return value if len(value) <= PREVIEW_CHARS else value[:PREVIEW_CHARS] + f"… ({len(value) - PREVIEW_CHARS} karakter lagi)"
    if isinstance(value, list):
        items = [shorten(v, depth + 1) for v in value[:PREVIEW_ITEMS]]
        if len(value) > PREVIEW_ITEMS:
            items.append(f"… {len(value) - PREVIEW_ITEMS} item lagi")
        return items
    if isinstance(value, dict):
        if depth >= 4:
            return "{…}"
        return {str(k): shorten(v, depth + 1) for k, v in list(value.items())[:30]}
    return value


def fetch_preview(fetcher, dataset_id, n):
    """Ambil n baris pertama lewat dataset viewer Hugging Face, tanpa mengunduh dataset.

    Kebanyakan dataset memakai config `default` dan split `train`, jadi itu dicoba dulu (satu request).
    Kalau tidak ada, daftar split dibaca untuk memilih `train` atau split pertama.
    """
    def first_rows(config, split):
        return fetcher.get(f"{VIEWER_API}/first-rows", params={"dataset": dataset_id, "config": config, "split": split})

    def as_json(resp):
        try:
            body = resp.json()
        except ValueError:
            return None
        return body if isinstance(body, dict) else None

    resp = first_rows("default", "train")
    body = as_json(resp) if resp.status_code == 200 else None
    if body is None:
        resp = fetcher.get(f"{VIEWER_API}/splits", params={"dataset": dataset_id})
        splits = (as_json(resp) or {}).get("splits") if resp.status_code == 200 else None
        if not splits:
            return {"error": f"dataset viewer tidak tersedia untuk dataset ini (HTTP {resp.status_code})"}
        pick = next((x for x in splits if x.get("split") == "train"), splits[0])
        resp = first_rows(pick.get("config"), pick.get("split"))
        body = as_json(resp) if resp.status_code == 200 else None
        if body is None:
            return {"error": f"baris contoh tidak bisa dibaca (HTTP {resp.status_code})"}
    rows = [r.get("row", {}) for r in body.get("rows", []) if isinstance(r, dict)][:n]
    return {
        "config": body.get("config"),
        "split": body.get("split"),
        "columns": [f.get("name") for f in body.get("features", []) if isinstance(f, dict)],
        "rows": [shorten(row) for row in rows],
    }


def is_coding(item):
    """Saring hasil pencarian kata kunci yang bukan dataset kode (barcode, encoder, code-switching, ...)."""
    name = item["id"].split("/", 1)[-1]
    columns = feature_names((item.get("cardData") or {}).get("dataset_info"))
    if columns & (CODE_COLUMNS | RAW_CODE_COLUMNS) or "code" in item.get("tags", []):
        return True
    return bool(CODING_ID.search(name.lower())) and not NOT_CODING_ID.search(name)


def check_coding_card(candidate, text):
    signals = candidate["signals"]
    if VERIFIED.search(text):
        signals.append("diverifikasi dengan tes/eksekusi")
    if DECONTAMINATED.search(text):
        signals.append("didekontaminasi dari benchmark")
    if DEDUPLICATED.search(text):
        signals.append("dideduplikasi")
    if PII_FILTERED.search(text):
        signals.append("menyebut penyaringan PII/secret")
    if len(text) >= 2000:
        signals.append("dokumentasi lengkap")
    hits = sorted({m.group(0).lower() for m in CONTEST_SOURCE.finditer(text)})
    if hits:
        candidate["notes"].append(f"soal dari situs kompetisi ({', '.join(hits[:3])}): teks soal berhak cipta, cek syarat layanan situsnya")


def coding_score(c):
    """Skor 0-100 dari metadata dan dataset card. Ini perkiraan untuk mengurutkan kandidat, bukan ukuran mutu pasti."""
    score = {"permisif": 25, "share-alike": 10, "bersyarat": 5}.get(c["license_status"], 0)
    score += {"percakapan": 25, "instruksi": 25, "tanya-jawab": 15}.get(c["shape"], 0)
    score += min(15, 3 * math.log10(c["downloads"] + 1)) + min(5, math.log2(c["likes"] + 1))
    score += 15 * ("diverifikasi dengan tes/eksekusi" in c["signals"])
    score += 5 * ("didekontaminasi dari benchmark" in c["signals"])
    score += 5 * ("dideduplikasi" in c["signals"])
    score += 5 * ("dokumentasi lengkap" in c["signals"])
    if BENCHMARK_ID.search(c["id"].split("/", 1)[-1]):
        score -= 30
    return max(0, round(score))


def coding_notes(c):
    if BENCHMARK_ID.search(c["id"].split("/", 1)[-1]):
        c["notes"].insert(0, "benchmark: pakai untuk evaluasi, bukan training (skor eval jadi tidak bersih)")
    if set(c["columns"]) & RAW_CODE_COLUMNS:
        c["notes"].append("korpus kode mentah dari repo publik: lisensi tiap file berbeda (termasuk GPL)"
                          + ("" if "menyebut penyaringan PII/secret" in c["signals"] else ", cek juga email/API key di dalam kode"))


def crawl(fetcher, args, search=None, extra_filter=None, on_page=None):
    filters = [f"language:{args.language}"] if args.language else []
    if args.task:
        filters.append(f"task_categories:{args.task}")
    if extra_filter:
        filters.append(extra_filter)
    params = {"sort": args.sort, "direction": -1, "limit": min(100, args.scan), "full": "true"}
    if filters:
        params["filter"] = filters
    if search:
        params["search"] = search

    items, url = [], API
    while url and len(items) < args.scan:
        resp = fetcher.get(url, params=params)
        if resp.status_code != 200:
            sys.exit(f"gagal membaca katalog Hugging Face: HTTP {resp.status_code} {resp.text[:200]}")
        page = resp.json()
        if not page:
            break
        items.extend(page)
        print(f"  {len(items)} dataset terbaca ...", file=sys.stderr)
        if on_page:
            on_page(page)
        url = resp.links.get("next", {}).get("url")
        params = None  # URL halaman berikutnya sudah membawa semua parameter
    return items[: args.scan]


def md_cell(text):
    return str(text).replace("|", "\\|").replace("\n", " ")


def write_viz(report, out):
    """Tulis visualisasi jaring: template HTML yang diisi hasil crawl. JSON di-escape supaya `</script>` di data tidak menutup tag."""
    payload = json.dumps(report, ensure_ascii=False).replace("</", "<\\/")
    html = VIZ_TEMPLATE.read_text(encoding="utf-8")
    assert html.count(VIZ_PLACEHOLDER) == 1, "penanda data di crawler_viz.html tidak ditemukan"
    html = html.replace(VIZ_PLACEHOLDER, f'<script id="crawl-data" type="application/json">{payload}</script>')
    out.with_suffix(".html").write_text(html, encoding="utf-8")


def write_report(candidates, args, scanned, out, passes, card_order):
    out.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    query = {k: v for k, v in vars(args).items() if k not in ("out", "delay", "live", "port", "no_browser")}
    # Urutan perayapan disimpan supaya visualisasi bisa memutar ulang jalannya crawl.
    shown = {c["id"] for c in candidates}
    report = {
        "generated_at": now, "preset": args.preset, "query": query, "scanned": scanned,
        "passes": [{"label": p["label"], "ids": [i for i in p["ids"] if i in shown]} for p in passes],
        "card_order": [i for i in card_order if i in shown],
        "candidates": candidates,
    }
    out.with_suffix(".json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_viz(report, out)
    return report

    coding = args.preset == "coding"
    lines = [
        "# Kandidat dataset coding" if coding else "# Kandidat dataset",
        "",
        f"Dibuat {now} dari katalog Hugging Face Hub. "
        + (f"Bahasa `{args.language}`" if args.language else "Semua bahasa")
        + (f", kata kunci `{args.search}`" if args.search else "")
        + (f", kata kunci `{'`, `'.join(CODING_SEARCHES)}` dan tag `code`" if coding and not args.search else "")
        + (f", tugas `{args.task}`" if args.task else "")
        + f". {scanned} dataset dipindai, {len(candidates)} ditampilkan.",
        "",
        "Status lisensi dibaca dari metadata yang diisi pemilik dataset dan bisa saja keliru. "
        "Laporan ini adalah daftar untuk direview, bukan izin memakai data.",
        "",
    ]
    if coding:
        lines += [
            "Skor 0–100 adalah perkiraan dari metadata dan dataset card: lisensi (25), bentuk instruksi/percakapan (25), "
            "popularitas (20), diverifikasi dengan tes/eksekusi (15), dekontaminasi, deduplikasi, dan dokumentasi (masing-masing 5). "
            "Benchmark dikurangi 30 karena bukan untuk training.",
            "",
        ]
    header = ["#", "Dataset"] + (["Skor"] if coding else []) + ["Lisensi", "Status", "Unduhan", "Ukuran", "Bentuk data"]
    header += ["Sinyal kualitas"] if coding else []
    header += ["Catatan"]
    lines += ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    for i, c in enumerate(candidates, 1):
        row = [i, f"[{c['id']}]({c['url']})"] + ([c["score"]] if coding else [])
        row += [", ".join(c["licenses"]) or "tidak dicantumkan", c["license_status"], f"{c['downloads']:,}", c["size"], c["shape"]]
        row += ["; ".join(c["signals"]) or "-"] if coding else []
        row += ["; ".join(c["notes"]) or "-"]
        lines.append("| " + " | ".join(md_cell(v) for v in row) + " |")
    lines += [
        "",
        "## Arti status lisensi",
        "",
        "- **permisif**: boleh dipakai, diubah, dan didistribusikan ulang, termasuk komersial, dengan atribusi dan menyertakan teks lisensi.",
        "- **share-alike**: turunan yang didistribusikan harus memakai lisensi yang sama. Perhatikan sebelum dicampur ke dataset yang lisensinya berbeda.",
        "- **bersyarat**: ada batasan penggunaan atau syarat khusus. Baca teks lisensinya.",
        "- **cek manual**: lisensi tidak dicantumkan atau tidak dikenali. Tanpa lisensi, ciptaan tetap dilindungi "
        "hak cipta (UU No. 28 Tahun 2014), jadi anggap tidak boleh dipakai sampai ada kejelasan.",
        "- **nonkomersial**: hanya untuk riset atau penggunaan nonkomersial. Model hasil training juga ikut terbatas.",
        "- **tanpa turunan**: tidak boleh diubah, sehingga tidak cocok diubah ke format instruct atau dicampur.",
        "",
        "## Sebelum memakai kandidat",
        "",
        "1. Buka dataset card dan pastikan lisensinya sama dengan metadata.",
        "2. Periksa asal-usul data: ditulis manusia, hasil terjemahan, hasil scraping, atau output model lain.",
        "3. Periksa contoh baris untuk data pribadi (nama, nomor HP, email, akun media sosial).",
        "4. Catat sumber, lisensi, dan tanggal akses, lalu sertakan atribusi serta teks lisensi saat mendistribusikan ulang.",
        "",
    ]
    if coding:
        lines[-1:-1] = [
            "5. Kode termasuk ciptaan yang dilindungi (Pasal 40 ayat (1) huruf s UU No. 28 Tahun 2014). Untuk korpus dari repo publik, "
            "pastikan hanya file berlisensi permisif yang dipakai dan ada mekanisme opt-out bagi pemilik kode.",
            "6. Jalankan sendiri sebagian solusi dengan tesnya sebelum dipakai. Sinyal \"diverifikasi\" di atas hanya klaim dari dataset card.",
        ]
    out.with_suffix(".md").write_text("\n".join(lines), encoding="utf-8")


def select(items, args, top):
    """Saring dan urutkan kandidat dari dataset yang sudah dipindai (tanpa membaca dataset card)."""
    candidates = [summarize(item) for item in items if not item.get("disabled") and not item.get("private")]
    candidates = [c for c in candidates if c["downloads"] >= args.min_downloads]
    if args.only_permissive:
        candidates = [c for c in candidates if c["license_status"] == "permisif"]
    if args.preset == "coding":
        for c in candidates:
            c["score"] = coding_score(c)
        candidates.sort(key=lambda c: -c["score"])
    return candidates[:top]


def run(args, emit=lambda event: None):
    """Jalankan crawl dan tulis laporan. `emit` menerima setiap kejadian untuk visualisasi live."""
    coding = args.preset == "coding"
    out = Path(args.out or ROOT / ("runs/kandidat_coding" if coding else "runs/kandidat_dataset"))

    def passes_for(candidates):
        shown = {c["id"] for c in candidates}
        return [{"label": p["label"], "ids": [i for i in p["ids"] if i in shown]} for p in passes_log]

    def emit_candidates(stage, candidates):
        emit({"type": "candidates", "stage": stage, "candidates": candidates, "passes": passes_for(candidates)})

    fetcher = Fetcher(make_session(), args.delay)
    emit({"type": "start", "preset": args.preset})
    print("membaca katalog Hugging Face ...", file=sys.stderr)
    if coding and not args.search:
        # Beberapa pencarian digabung; dataset yang muncul di lebih dari satu pencarian dihitung sekali.
        passes = [(term, None) for term in CODING_SEARCHES] + [(None, "code")]
    else:
        passes = [(args.search, None)]
    items, seen, passes_log = [], set(), []
    for search, extra_filter in passes:
        label = search or (f"tag {extra_filter}" if extra_filter else f"bahasa {args.language}" if args.language else "semua")
        if len(passes) > 1:
            print(f"pencarian {label!r} ...", file=sys.stderr)
        emit({"type": "pass", "label": label})
        log = {"label": label, "ids": []}
        passes_log.append(log)

        def on_page(page, log=log):
            for item in page[: args.scan - len(log["ids"])]:
                log["ids"].append(item["id"])
                if item["id"] not in seen:
                    seen.add(item["id"])
                    if not coding or is_coding(item):
                        items.append(item)
            emit({"type": "page", "label": log["label"], "count": len(log["ids"]), "scanned": len(seen)})

        crawl(fetcher, args, search, extra_filter, on_page)
        # Kandidat sementara setelah setiap pencarian, supaya jaring di browser tumbuh bertahap.
        emit_candidates("pencarian", select(items, args, args.top))

    # Preset coding membaca card untuk dua kali jumlah --top, supaya dataset yang skornya naik
    # karena sinyal di card tetap punya kesempatan masuk.
    candidates = select(items, args, args.top * (2 if coding and not args.no_cards else 1))
    emit_candidates("card", candidates)

    card_order = []
    if not args.no_cards:
        print(f"membaca {len(candidates)} dataset card ...", file=sys.stderr)
    for c in candidates:
        if not args.no_cards:
            check_card(fetcher, c, coding)
            card_order.append(c["id"])
        if coding:
            coding_notes(c)
            c["score"] = coding_score(c)
        if not args.no_cards:
            emit({"type": "card", "id": c["id"], "candidate": c})
    if coding:
        candidates.sort(key=lambda c: -c["score"])
        candidates = candidates[: args.top]

    if args.preview > 0:
        print(f"mengambil {args.preview} baris contoh dari {len(candidates)} dataset ...", file=sys.stderr)
        for c in candidates:
            if c["gated"]:
                # Dataset gated baru boleh dibaca setelah syarat pemiliknya disetujui; jangan diakali.
                c["preview"] = {"error": "dataset gated: setujui syarat pemiliknya di Hugging Face dulu, isinya tidak diambil"}
            else:
                c["preview"] = fetch_preview(fetcher, c["id"], args.preview)
            emit({"type": "preview", "id": c["id"], "preview": c["preview"]})

    report = write_report(candidates, args, len(seen), out, passes_log, card_order)
    emit_candidates("final", candidates)
    files = {ext: str(out.with_suffix("." + ext)) for ext in ("md", "json", "html")}
    emit({"type": "done", "scanned": len(seen), "generated_at": report["generated_at"], "files": files})

    counts = {s: sum(c["license_status"] == s for c in candidates) for s in STATUSES}
    print(f"\n{len(candidates)} kandidat dari {len(seen)} dataset yang dipindai")
    for status, n in counts.items():
        if n:
            print(f"  {status:14s}: {n}")
    print(f"laporan: {files['md']} dan {files['json']}")
    print(f"visualisasi jaring: buka {files['html']} di browser")


class LiveServer:
    """Server lokal untuk --live: halaman visualisasi di `/` dan aliran kejadian crawl (Server-Sent Events) di `/events`.

    Server hanya mendengarkan 127.0.0.1, jadi tidak bisa dibuka dari perangkat lain di jaringan yang sama.
    Semua kejadian disimpan, sehingga tab yang dibuka belakangan atau tersambung ulang tetap menerima urutan lengkap.
    """

    def __init__(self, port):
        self.events = []
        self.cond = threading.Condition()
        self.connected = threading.Event()
        html = VIZ_TEMPLATE.read_text(encoding="utf-8")
        assert html.count(VIZ_PLACEHOLDER) == 1, "penanda data di crawler_viz.html tidak ditemukan"
        self.page = html.replace(VIZ_PLACEHOLDER, '<script id="crawl-data" type="application/json">{"live": true}</script>').encode()
        self.httpd = ThreadingHTTPServer(("127.0.0.1", port), self._handler())
        self.httpd.daemon_threads = True
        self.url = f"http://127.0.0.1:{self.httpd.server_address[1]}/"

    def emit(self, event):
        with self.cond:
            self.events.append(event)
            self.cond.notify_all()

    def _handler(self):
        server = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                path = self.path.split("?", 1)[0]
                if path == "/":
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Cache-Control", "no-store")
                    self.send_header("Content-Length", str(len(server.page)))
                    self.end_headers()
                    self.wfile.write(server.page)
                elif path == "/events":
                    self.stream()
                else:
                    self.send_error(404)

            def stream(self):
                last = self.headers.get("Last-Event-ID", "")
                index = int(last) + 1 if last.isdigit() else 0
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                server.connected.set()
                try:
                    while True:
                        with server.cond:
                            server.cond.wait_for(lambda: len(server.events) > index, timeout=15)
                            batch = server.events[index:]
                        if not batch:
                            self.wfile.write(b": masih jalan\n\n")  # komentar SSE agar koneksi tidak dianggap mati
                        for event in batch:
                            self.wfile.write(f"id: {index}\ndata: {json.dumps(event, ensure_ascii=False)}\n\n".encode())
                            index += 1
                        self.wfile.flush()
                        if batch and batch[-1]["type"] in ("done", "error"):
                            return
                except (BrokenPipeError, ConnectionResetError):
                    return

        return Handler


def run_live(args):
    try:
        server = LiveServer(args.port)
    except OSError as e:
        sys.exit(f"tidak bisa membuka port {args.port} ({e}); coba --port lain")
    threading.Thread(target=server.httpd.serve_forever, daemon=True).start()
    print(f"visualisasi live: {server.url}")
    if not args.no_browser:
        webbrowser.open(server.url)
    # Tunggu halaman tersambung supaya crawl ditonton dari awal (paling lama 15 detik).
    server.connected.wait(timeout=15)
    failed = False
    try:
        run(args, server.emit)
    except (Exception, SystemExit) as e:
        failed = True
        message = str(e.code if isinstance(e, SystemExit) else e) or type(e).__name__
        server.emit({"type": "error", "message": message})
        print(f"crawl gagal: {message}", file=sys.stderr)
    print(f"\nhalaman tetap bisa dibuka di {server.url}; tekan Ctrl+C untuk berhenti")
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        server.httpd.shutdown()
    if failed:
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--preset", default="umum", choices=["umum", "coding"],
                        help="umum: dataset berbahasa Indonesia; coding: dataset kode semua bahasa, diurutkan menurut skor kualitas")
    parser.add_argument("--language", help="kode bahasa di metadata Hugging Face (bawaan: id untuk umum, semua bahasa untuk coding)")
    parser.add_argument("--search", help="kata kunci pada nama dataset, misalnya instruct, chat, hukum")
    parser.add_argument("--task", help="task_categories, misalnya text-generation atau question-answering")
    parser.add_argument("--sort", default="downloads", choices=["downloads", "likes", "lastModified", "trendingScore"])
    parser.add_argument("--scan", type=int, default=500, help="jumlah maksimal dataset yang dipindai per pencarian")
    parser.add_argument("--top", type=int, default=50, help="jumlah kandidat di laporan")
    parser.add_argument("--min-downloads", type=int, default=0)
    parser.add_argument("--only-permissive", action="store_true", help="hanya tampilkan lisensi permisif")
    parser.add_argument("--no-cards", action="store_true", help="jangan baca dataset card (lebih cepat, catatan risiko lebih sedikit)")
    parser.add_argument("--preview", type=int, default=3, help="jumlah baris contoh per kandidat dari dataset viewer (0 = tidak mengambil)")
    parser.add_argument("--delay", type=float, default=1.0, help="jeda minimal antar-request dalam detik")
    parser.add_argument("--out", help="awalan nama file laporan (.md, .json, dan .html)")
    parser.add_argument("--live", action="store_true", help="tonton crawl secara langsung di browser lewat server lokal")
    parser.add_argument("--port", type=int, default=8765, help="port server lokal untuk --live")
    parser.add_argument("--no-browser", action="store_true", help="dengan --live: jangan buka browser otomatis")
    args = parser.parse_args()
    if args.language is None:
        args.language = "" if args.preset == "coding" else "id"
    if args.live:
        run_live(args)
    else:
        run(args)


if __name__ == "__main__":
    main()
