"""Crawler penemu dataset: mencari kandidat dataset di Hugging Face Hub dan menilai lisensinya.

Script ini hanya membaca katalog lewat API resmi Hugging Face (daftar dataset dan dataset card),
tidak mengunduh isi dataset dan tidak men-scrape halaman web. Hasilnya laporan kandidat untuk
direview manusia sebelum ada data yang dipakai.

Pemakaian (butuh akses internet ke huggingface.co):
    python scripts/find_datasets.py
    python scripts/find_datasets.py --search instruct --task text-generation --top 30
    python scripts/find_datasets.py --only-permissive --min-downloads 100
    python scripts/find_datasets.py --no-cards        # lebih cepat, tanpa membaca dataset card

Laporan ditulis ke runs/kandidat_dataset.md dan runs/kandidat_dataset.json. Isi variabel
lingkungan HF_TOKEN (opsional) untuk batas request yang lebih longgar.
"""
import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
API = "https://huggingface.co/api/datasets"
CARD_URL = "https://huggingface.co/datasets/{id}/raw/main/README.md"
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
INSTRUCT_COLUMNS = {"instruction", "prompt", "input", "query", "inputs"}
RESPONSE_COLUMNS = {"output", "response", "completion", "answer", "targets", "chosen"}

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
    }


def check_card(fetcher, candidate):
    """Baca dataset card dan tandai risiko yang perlu dicek manual. Teks card hanya dicocokkan pola, tidak dieksekusi."""
    resp = fetcher.get(CARD_URL.format(id=candidate["id"]))
    if resp.status_code != 200:
        candidate["notes"].append(f"dataset card tidak bisa dibaca (HTTP {resp.status_code})")
        return
    text = resp.text
    hits = sorted({m.group(0).lower() for m in MODEL_OUTPUT.finditer(text)})
    if hits:
        candidate["notes"].append(f"mungkin berisi output model lain ({', '.join(hits[:4])}): cek syarat penggunaan penyedia model")
    hits = sorted({m.group(0).lower() for m in SOCIAL_SOURCE.finditer(text)})
    if hits:
        candidate["notes"].append(f"sumber media sosial/ulasan ({', '.join(hits[:4])}): cek data pribadi (UU PDP) dan syarat platform")
    if len(text.strip()) < 300:
        candidate["notes"].append("dataset card sangat singkat: asal-usul data tidak jelas")


def crawl(fetcher, args):
    params = {"filter": f"language:{args.language}", "sort": args.sort, "direction": -1,
              "limit": min(100, args.scan), "full": "true"}
    if args.search:
        params["search"] = args.search
    if args.task:
        params["filter"] = [params["filter"], f"task_categories:{args.task}"]

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
        url = resp.links.get("next", {}).get("url")
        params = None  # URL halaman berikutnya sudah membawa semua parameter
    return items[: args.scan]


def md_cell(text):
    return str(text).replace("|", "\\|").replace("\n", " ")


def write_report(candidates, args, scanned, out):
    out.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    query = {k: v for k, v in vars(args).items() if k not in ("out", "delay")}
    out.with_suffix(".json").write_text(
        json.dumps({"generated_at": now, "query": query, "scanned": scanned, "candidates": candidates},
                   ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    lines = [
        "# Kandidat dataset",
        "",
        f"Dibuat {now} dari katalog Hugging Face Hub. Bahasa `{args.language}`"
        + (f", kata kunci `{args.search}`" if args.search else "")
        + (f", tugas `{args.task}`" if args.task else "")
        + f". {scanned} dataset dipindai, {len(candidates)} ditampilkan.",
        "",
        "Status lisensi dibaca dari metadata yang diisi pemilik dataset dan bisa saja keliru. "
        "Laporan ini adalah daftar untuk direview, bukan izin memakai data.",
        "",
        "| # | Dataset | Lisensi | Status | Unduhan | Ukuran | Bentuk data | Catatan |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for i, c in enumerate(candidates, 1):
        lines.append("| " + " | ".join(md_cell(v) for v in [
            i, f"[{c['id']}]({c['url']})", ", ".join(c["licenses"]) or "tidak dicantumkan", c["license_status"],
            f"{c['downloads']:,}", c["size"], c["shape"], "; ".join(c["notes"]) or "-",
        ]) + " |")
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
    out.with_suffix(".md").write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--language", default="id", help="kode bahasa di metadata Hugging Face (bawaan: id)")
    parser.add_argument("--search", help="kata kunci pada nama dataset, misalnya instruct, chat, hukum")
    parser.add_argument("--task", help="task_categories, misalnya text-generation atau question-answering")
    parser.add_argument("--sort", default="downloads", choices=["downloads", "likes", "lastModified", "trendingScore"])
    parser.add_argument("--scan", type=int, default=500, help="jumlah maksimal dataset yang dipindai dari katalog")
    parser.add_argument("--top", type=int, default=50, help="jumlah kandidat di laporan")
    parser.add_argument("--min-downloads", type=int, default=0)
    parser.add_argument("--only-permissive", action="store_true", help="hanya tampilkan lisensi permisif")
    parser.add_argument("--no-cards", action="store_true", help="jangan baca dataset card (lebih cepat, catatan risiko lebih sedikit)")
    parser.add_argument("--delay", type=float, default=1.0, help="jeda minimal antar-request dalam detik")
    parser.add_argument("--out", default=str(ROOT / "runs/kandidat_dataset"), help="awalan nama file laporan (.md dan .json)")
    args = parser.parse_args()

    fetcher = Fetcher(make_session(), args.delay)
    print("membaca katalog Hugging Face ...", file=sys.stderr)
    items = crawl(fetcher, args)

    candidates = [summarize(item) for item in items if not item.get("disabled") and not item.get("private")]
    candidates = [c for c in candidates if c["downloads"] >= args.min_downloads]
    if args.only_permissive:
        candidates = [c for c in candidates if c["license_status"] == "permisif"]
    candidates = candidates[: args.top]

    if not args.no_cards:
        print(f"membaca {len(candidates)} dataset card ...", file=sys.stderr)
        for c in candidates:
            check_card(fetcher, c)

    out = Path(args.out)
    write_report(candidates, args, len(items), out)
    counts = {s: sum(c["license_status"] == s for c in candidates) for s in STATUSES}
    print(f"\n{len(candidates)} kandidat dari {len(items)} dataset yang dipindai")
    for status, n in counts.items():
        if n:
            print(f"  {status:14s}: {n}")
    print(f"laporan: {out.with_suffix('.md')} dan {out.with_suffix('.json')}")


if __name__ == "__main__":
    main()
