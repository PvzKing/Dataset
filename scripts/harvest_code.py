"""Crawler isi: mengumpulkan bahan mentah terkait kode untuk diolah menjadi dataset SFT.

Semua sumber berlisensi terbuka dan diambil lewat jalur resmi, tanpa scraping halaman web:

    hf      baris dataset Hugging Face berlisensi permisif, lewat dataset viewer resmi
    github  fungsi Python yang punya docstring, dari repo GitHub berlisensi permisif (git clone dangkal)
    mdn     halaman MDN Web Docs (HTML, CSS, JavaScript) dari repo resmi mdn/content

Pemakaian:
    python scripts/harvest_code.py hf --from-report runs/kandidat_coding.json --rows 300
    python scripts/harvest_code.py hf --dataset nama-org/nama-dataset --rows 500
    python scripts/harvest_code.py github --repos 20
    python scripts/harvest_code.py github --repo psf/requests
    python scripts/harvest_code.py mdn --path web/javascript/guide --path web/css
    python scripts/raw_to_sft.py          # ubah hasilnya menjadi draf format messages

Setiap record ditambahkan ke runs/harvest/raw.jsonl lengkap dengan sumber, lisensi, dan atribusi.
Record yang sama tidak disimpan dua kali, jadi perintah aman dijalankan berulang. Daftar sumber
beserta kewajiban lisensinya ditulis ke runs/harvest/ATTRIBUTION.md.

Token (opsional): HF_TOKEN untuk Hugging Face, GITHUB_TOKEN untuk GitHub. Keduanya hanya dikirim
ke layanan pemiliknya masing-masing.
"""
import argparse
import ast
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import textwrap
from datetime import date
from pathlib import Path

import requests

from find_datasets import (API as HF_API, BENCHMARK_ID, VIEWER_API, Fetcher, USER_AGENT, license_status,
                           licenses_of, make_session)

ROOT = Path(__file__).resolve().parent.parent
GITHUB_API = "https://api.github.com"
MDN_REPO = "https://github.com/mdn/content.git"

# Lisensi kode yang boleh dipakai, diubah, dan didistribusikan ulang (termasuk komersial) dengan atribusi.
PERMISSIVE_CODE = {"MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC", "0BSD", "Unlicense", "Zlib", "CC0-1.0"}
# Folder yang biasanya berisi kode pihak ketiga dengan lisensi berbeda dari repo induknya.
SKIP_DIRS = {".git", "vendor", "vendored", "_vendor", "third_party", "thirdparty", "third-party", "external", "extern",
             "node_modules", "site-packages", "build", "dist", ".tox", ".venv", "venv", "__pycache__"}
COPYLEFT_HEADER = re.compile(r"GNU (Lesser |Affero )?General Public License|SPDX-License-Identifier:\s*(A|L)?GPL", re.IGNORECASE)
SPDX_HEADER = re.compile(r"SPDX-License-Identifier:\s*([\w.+-]+)")

# Kunci rahasia yang tidak boleh ikut ke dataset. Record yang memuatnya dibuang seluruhnya.
SECRET = re.compile(
    r"AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{40,}|hf_[A-Za-z0-9]{30,}|"
    r"sk-[A-Za-z0-9_-]{20,}|xox[baprs]-[A-Za-z0-9-]{10,}|-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"
)
# Alamat email adalah data pribadi (UU No. 27 Tahun 2022 tentang PDP). Di teks diganti; di kode
# record dibuang, karena mengganti isi kode bisa merusaknya.
EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+(\.[\w-]+)*\.[A-Za-z]{2,}\b")
MAX_CELL_CHARS = 20000


def http_session(token_env=None, accept=None):
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    if accept:
        session.headers["Accept"] = accept
    token = os.environ.get(token_env) if token_env else None
    if token:
        session.headers["Authorization"] = f"Bearer {token}"
    return session


def scrub_text(text):
    """Kembalikan teks tanpa email, atau None jika memuat kunci rahasia."""
    if SECRET.search(text):
        return None
    return EMAIL.sub("<email>", text)


class Store:
    """Menyimpan record ke raw.jsonl tanpa duplikat dan mencatat atribusi setiap sumber."""

    def __init__(self, out_dir):
        self.dir = Path(out_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.raw_path = self.dir / "raw.jsonl"
        self.sources_path = self.dir / "sources.json"
        self.hashes = set()
        if self.raw_path.exists():
            with self.raw_path.open(encoding="utf-8") as f:
                for line in f:
                    try:
                        self.hashes.add(json.loads(line)["hash"])
                    except (ValueError, KeyError):
                        continue
        self.sources = json.loads(self.sources_path.read_text(encoding="utf-8")) if self.sources_path.exists() else {}
        self.file = self.raw_path.open("a", encoding="utf-8")
        self.added = 0
        self.skipped = {"duplikat": 0, "kunci rahasia": 0, "email di kode": 0, "baris berisi rahasia, gambar, atau sel terlalu panjang": 0}

    def source(self, key, **info):
        entry = self.sources.setdefault(key, {"records": 0})
        entry.update(info)
        entry["retrieved_at"] = date.today().isoformat()

    def add(self, source_key, record, content):
        digest = hashlib.sha1(content.encode("utf-8")).hexdigest()[:16]
        if digest in self.hashes:
            self.skipped["duplikat"] += 1
            return False
        self.hashes.add(digest)
        record = {"id": f"{record['source']}-{digest}", "hash": digest, **record, "retrieved_at": date.today().isoformat()}
        self.file.write(json.dumps(record, ensure_ascii=False) + "\n")
        self.sources[source_key]["records"] += 1
        self.added += 1
        return True

    def close(self):
        self.file.close()
        self.sources_path.write_text(json.dumps(self.sources, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        write_attribution(self.dir / "ATTRIBUTION.md", self.sources)
        print(f"\n{self.added} record baru ditulis ke {self.raw_path}")
        for reason, n in self.skipped.items():
            if n:
                print(f"  dilewati ({reason}): {n}")
        print(f"atribusi: {self.dir / 'ATTRIBUTION.md'}")


def write_attribution(path, sources):
    lines = [
        "# Atribusi sumber",
        "",
        "Dibuat otomatis oleh `scripts/harvest_code.py`. Sertakan file ini (dan teks lisensi yang disebut) "
        "jika dataset atau bagian darinya didistribusikan ulang.",
        "",
        "Kewajiban menurut lisensi:",
        "",
        "- **MIT, BSD, ISC, Zlib:** sertakan pemberitahuan hak cipta dan teks lisensinya.",
        "- **Apache-2.0:** sertakan teks lisensi, pemberitahuan hak cipta, isi file NOTICE (jika ada), dan tandai bahwa isinya telah diubah.",
        "- **CC BY-SA:** cantumkan kredit dan tautan sumber, tandai perubahan, dan bagikan turunannya dengan lisensi yang sama (share-alike).",
        "- **CC0 dan Unlicense:** tidak ada kewajiban, tetapi menyebut sumber tetap praktik yang baik.",
        "",
    ]
    for kind, title in [("github", "Repo GitHub"), ("mdn", "MDN Web Docs"), ("hf", "Dataset Hugging Face")]:
        entries = sorted((k, v) for k, v in sources.items() if v.get("source") == kind)
        if not entries:
            continue
        lines += [f"## {title}", ""]
        for _, v in entries:
            lines.append(f"### [{v['name']}]({v['url']})")
            lines.append("")
            lines.append(f"- Lisensi: {v.get('license', '-')}")
            if v.get("attribution"):
                lines.append(f"- Atribusi: {v['attribution']}")
            lines.append(f"- Jumlah record: {v.get('records', 0)}, diambil {v.get('retrieved_at', '-')}")
            if v.get("notice"):
                lines += ["- NOTICE:", "", "```", v["notice"].strip(), "```"]
            lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def run_git(args, timeout=600):
    if not shutil.which("git"):
        sys.exit("git tidak ditemukan. Pasang Git terlebih dahulu (lihat docs/PANDUAN_CRAWLER.md).")
    result = subprocess.run(["git", *args], capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"git {' '.join(args)} gagal")
    return result.stdout


# ---------------------------------------------------------------- Hugging Face

def hf_dataset_info(fetcher, dataset_id):
    resp = fetcher.get(f"{HF_API}/{dataset_id}", params={"full": "true"})
    if resp.status_code != 200:
        return None
    return resp.json()


def hf_pick_split(fetcher, dataset_id):
    resp = fetcher.get(f"{VIEWER_API}/splits", params={"dataset": dataset_id})
    if resp.status_code != 200:
        return None
    splits = resp.json().get("splits") or []
    if not splits:
        return None
    return next((s for s in splits if s.get("split") == "train"), splits[0])


def clean_cell(value):
    """Batasi panjang teks dan buang gambar/audio; kembalikan None jika baris harus dibuang."""
    if isinstance(value, str):
        if len(value) > MAX_CELL_CHARS:
            return None
        return scrub_text(value)
    if isinstance(value, list):
        out = [clean_cell(v) for v in value]
        return None if any(v is None and o is not None for v, o in zip(out, value)) else out
    if isinstance(value, dict):
        if "src" in value and isinstance(value.get("src"), str):
            return None  # gambar atau audio dari dataset viewer: tidak dipakai untuk SFT teks
        out = {k: clean_cell(v) for k, v in value.items()}
        return None if any(out[k] is None and value[k] is not None for k in value) else out
    return value


def harvest_hf(args, store):
    fetcher = Fetcher(make_session(), args.delay)
    targets = []
    for dataset_id in args.dataset or []:
        targets.append({"id": dataset_id, "notes": []})
    if args.from_report:
        report = json.loads(Path(args.from_report).read_text(encoding="utf-8"))
        for c in report.get("candidates", []):
            if c.get("gated"):
                continue
            if BENCHMARK_ID.search(c["id"].split("/", 1)[-1]) and not args.include_benchmarks:
                continue
            targets.append({"id": c["id"], "notes": c.get("notes", [])})
    if not targets:
        sys.exit("tidak ada dataset: pakai --dataset atau --from-report")

    allowed = set(args.allow_status)
    for target in targets:
        dataset_id = target["id"]
        info = hf_dataset_info(fetcher, dataset_id)
        if info is None:
            print(f"- {dataset_id}: metadata tidak bisa dibaca, dilewati")
            continue
        licenses = licenses_of(info)
        status = max([license_status(n) for n in licenses] or ["cek manual"],
                     key=["permisif", "share-alike", "bersyarat", "cek manual", "nonkomersial", "tanpa turunan"].index)
        if status not in allowed:
            print(f"- {dataset_id}: lisensi {', '.join(licenses) or 'tidak dicantumkan'} ({status}), dilewati")
            continue
        if info.get("gated"):
            print(f"- {dataset_id}: gated, setujui syarat pemiliknya dulu; dilewati")
            continue
        split = hf_pick_split(fetcher, dataset_id)
        if not split:
            print(f"- {dataset_id}: dataset viewer tidak tersedia, dilewati")
            continue
        key = f"hf:{dataset_id}"
        store.source(key, source="hf", name=dataset_id, url=f"https://huggingface.co/datasets/{dataset_id}",
                     license=", ".join(licenses), attribution=f"{dataset_id} di Hugging Face (lihat dataset card)")
        print(f"- {dataset_id}: {', '.join(licenses)}, config {split['config']!r}, split {split['split']!r}")
        offset, taken = 0, 0
        while taken < args.rows:
            length = min(100, args.rows - taken)
            resp = fetcher.get(f"{VIEWER_API}/rows", params={"dataset": dataset_id, "config": split["config"],
                                                            "split": split["split"], "offset": offset, "length": length})
            if resp.status_code != 200:
                print(f"  berhenti: HTTP {resp.status_code}")
                break
            body = resp.json()
            rows = body.get("rows") or []
            if not rows:
                break
            for r in rows:
                offset += 1
                if r.get("truncated_cells"):
                    continue  # sel terpotong oleh dataset viewer: isinya tidak lengkap
                row = clean_cell(r.get("row") or {})
                if not row:
                    store.skipped["baris berisi rahasia, gambar, atau sel terlalu panjang"] += 1
                    continue
                record = {"source": "hf", "kind": "row", "dataset": dataset_id, "config": split["config"],
                          "split": split["split"], "row_idx": r.get("row_idx"),
                          "url": f"https://huggingface.co/datasets/{dataset_id}", "license": ", ".join(licenses),
                          "risk_notes": target["notes"], "row": row}
                if store.add(key, record, json.dumps(row, sort_keys=True, ensure_ascii=False)):
                    taken += 1
            if offset >= (body.get("num_rows_total") or 0):
                break
        print(f"  {taken} baris disimpan")


# ---------------------------------------------------------------- GitHub

def github_repos(session, fetcher, args):
    repos = []
    for full_name in args.repo or []:
        resp = fetcher.get(f"{GITHUB_API}/repos/{full_name}")
        if resp.status_code == 200:
            repos.append(resp.json())
        else:
            print(f"- {full_name}: tidak bisa dibaca (HTTP {resp.status_code})")
    if args.repos > 0:
        seen = {r["full_name"] for r in repos}
        for lic in args.license:
            q = f"language:python license:{lic} stars:>={args.min_stars} fork:false archived:false"
            if args.query:
                q = f"{args.query} {q}"
            resp = fetcher.get(f"{GITHUB_API}/search/repositories",
                               params={"q": q, "sort": "stars", "order": "desc", "per_page": min(100, args.repos * 2)})
            if resp.status_code != 200:
                print(f"pencarian GitHub gagal (HTTP {resp.status_code}): {resp.text[:200]}")
                continue
            for r in resp.json().get("items", []):
                if r["full_name"] not in seen:
                    seen.add(r["full_name"])
                    repos.append(r)
        repos = repos[: len(args.repo or []) + args.repos]
    return repos


def read_license_files(repo_dir):
    copyright_lines, notice = [], ""
    for path in sorted(repo_dir.iterdir()):
        name = path.name.upper()
        if not path.is_file():
            continue
        if name.startswith(("LICENSE", "LICENCE", "COPYING")):
            text = path.read_text(encoding="utf-8", errors="replace")
            copyright_lines += [line.strip() for line in text.splitlines() if line.strip().lower().startswith(("copyright", "(c)", "©"))]
        elif name.startswith("NOTICE"):
            notice = path.read_text(encoding="utf-8", errors="replace")[:4000]
    return copyright_lines[:5], notice


def python_functions(source):
    """Fungsi dan method yang punya docstring cukup panjang dan badan yang wajar."""
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError):
        return
    stack = [(tree, "")]
    while stack:
        node, prefix = stack.pop()
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.ClassDef):
                stack.append((child, f"{prefix}{child.name}."))
            elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                doc = ast.get_docstring(child)
                if not doc or len(doc) < 30 or child.name.startswith("__") or child.name.startswith("test"):
                    continue
                code = ast.get_source_segment(source, child)
                if not code:
                    continue
                # Baris pertama segmen tidak membawa indentasi, baris berikutnya membawa; ratakan untuk method.
                code = textwrap.dedent(" " * child.col_offset + code)
                lines = code.count("\n") + 1
                if 4 <= lines <= 80:
                    yield {"name": child.name, "qualname": prefix + child.name, "docstring": doc, "code": code, "lineno": child.lineno}


def harvest_github(args, store):
    session = http_session("GITHUB_TOKEN", "application/vnd.github+json")
    fetcher = Fetcher(session, args.delay)
    cache = Path(args.out_dir) / "cache" / "github"
    cache.mkdir(parents=True, exist_ok=True)
    for repo in github_repos(session, fetcher, args):
        full_name = repo["full_name"]
        spdx = (repo.get("license") or {}).get("spdx_id")
        if spdx not in PERMISSIVE_CODE:
            print(f"- {full_name}: lisensi {spdx or 'tidak terdeteksi'}, dilewati")
            continue
        if repo.get("size", 0) > args.max_size_mb * 1024:
            print(f"- {full_name}: {repo['size'] // 1024} MB, melebihi --max-size-mb, dilewati")
            continue
        dest = cache / full_name.replace("/", "__")
        if not dest.exists():
            print(f"- {full_name}: clone ...")
            try:
                run_git(["clone", "--depth", "1", "--quiet", repo.get("clone_url") or f"https://github.com/{full_name}.git", str(dest)])
            except (RuntimeError, subprocess.TimeoutExpired) as e:
                print(f"  gagal clone: {e}")
                continue
        else:
            print(f"- {full_name}: memakai clone di cache")
        commit = run_git(["-C", str(dest), "rev-parse", "HEAD"]).strip()
        copyright_lines, notice = read_license_files(dest)
        key = f"github:{full_name}"
        store.source(key, source="github", name=full_name, url=repo.get("html_url") or f"https://github.com/{full_name}",
                     license=spdx, attribution="; ".join(copyright_lines) or f"kontributor {full_name}", notice=notice,
                     commit=commit)
        taken = 0
        for path in sorted(dest.rglob("*.py")):
            rel = path.relative_to(dest)
            if any(part.lower() in SKIP_DIRS for part in rel.parts[:-1]) or taken >= args.max_per_repo:
                continue
            source = path.read_text(encoding="utf-8", errors="replace")
            header = "\n".join(source.splitlines()[:40])
            spdx_file = SPDX_HEADER.search(header)
            if COPYLEFT_HEADER.search(header) or (spdx_file and spdx_file.group(1) not in PERMISSIVE_CODE):
                continue  # file ini berlisensi lain dari repo induknya
            for fn in python_functions(source):
                if SECRET.search(fn["code"]):
                    store.skipped["kunci rahasia"] += 1
                    continue
                if EMAIL.search(fn["code"]):
                    store.skipped["email di kode"] += 1
                    continue
                record = {"source": "github", "kind": "function", "language": "python", "repo": full_name, "path": str(rel).replace(os.sep, "/"),
                          "commit": commit, "url": f"https://github.com/{full_name}/blob/{commit}/{str(rel).replace(os.sep, '/')}#L{fn['lineno']}",
                          "license": spdx, "name": fn["name"], "qualname": fn["qualname"], "docstring": fn["docstring"], "code": fn["code"]}
                if store.add(key, record, fn["code"]):
                    taken += 1
                if taken >= args.max_per_repo:
                    break
        print(f"  {taken} fungsi disimpan")


# ---------------------------------------------------------------- MDN

MACRO = re.compile(r"\{\{\s*([A-Za-z_][\w-]*)\s*(?:\((.*?)\))?\s*\}\}", re.S)
XREF_MACROS = {"jsxref", "domxref", "cssxref", "htmlelement", "htmlattrxref", "svgelement", "svgattr", "httpheader",
               "httpmethod", "httpstatus", "glossary", "event", "jsxref", "mathmlelement", "webextapiref", "cssxref"}
CODE_BLOCK = re.compile(r"```([\w-]*)[^\n]*\n(.*?)```", re.S)


def mdn_clean(markdown):
    """Ganti makro KumaScript MDN dengan teks biasa dan buang bagian yang hanya berisi makro."""
    def replace(m):
        name, raw_args = m.group(1).lower(), m.group(2) or ""
        args = re.findall(r'"([^"]*)"|\'([^\']*)\'', raw_args)
        values = [a or b for a, b in args]
        if name in XREF_MACROS and values:
            # Argumen kedua (jika ada) adalah teks yang ditampilkan, argumen pertama adalah tujuan tautannya.
            text = values[1] if len(values) > 1 and values[1] else values[0]
            return text if name == "glossary" else f"`{text}`"
        return ""
    text = MACRO.sub(replace, markdown)
    text = re.sub(r"\n## (Specifications|Browser compatibility)\n*(?=\n## |\Z)", "", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def front_matter(text):
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    meta = {}
    for line in text[3:end].splitlines():
        if ":" in line and not line.startswith(" "):
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip().strip('"').strip("'")
    return meta, text[end + 4:]


def harvest_mdn(args, store):
    paths = [p.strip("/").lower() for p in (args.path or ["web/javascript/guide", "web/html", "web/css"])]
    if args.mdn_dir:
        repo = Path(args.mdn_dir)
    else:
        repo = Path(args.out_dir) / "cache" / "mdn-content"
        if not repo.exists():
            print("clone mdn/content (sparse, hanya folder yang diminta) ...")
            run_git(["clone", "--depth", "1", "--filter=blob:none", "--sparse", "--quiet", MDN_REPO, str(repo)], timeout=1800)
        run_git(["-C", str(repo), "sparse-checkout", "set", *[f"files/en-us/{p}" for p in paths]], timeout=1800)
    commit = run_git(["-C", str(repo), "rev-parse", "HEAD"]).strip() if (repo / ".git").exists() else ""
    key = "mdn:content"
    store.source(key, source="mdn", name="MDN Web Docs (mdn/content)", url="https://developer.mozilla.org",
                 license="teks: CC-BY-SA-2.5 atau lebih baru; contoh kode: CC0-1.0 (ditambahkan sejak 20 Agustus 2010)",
                 attribution="Mozilla Contributors", commit=commit)
    taken = 0
    for section in paths:
        base = repo / "files" / "en-us" / section
        if not base.exists():
            print(f"- {section}: folder tidak ditemukan di mdn/content, dilewati")
            continue
        count = 0
        for page in sorted(base.rglob("index.md")):
            if taken >= args.max_pages:
                break
            meta, body = front_matter(page.read_text(encoding="utf-8", errors="replace"))
            text = scrub_text(mdn_clean(body))
            if not text or len(text) < 200:
                continue
            slug = meta.get("slug", "")
            blocks = [{"language": lang or "text", "code": code.rstrip()} for lang, code in CODE_BLOCK.findall(text)]
            record = {"source": "mdn", "kind": "doc", "title": meta.get("title", slug), "slug": slug,
                      "page_type": meta.get("page-type", ""), "url": f"https://developer.mozilla.org/en-US/docs/{slug}",
                      "license": {"text": "CC-BY-SA-2.5", "code": "CC0-1.0"}, "attribution": "Mozilla Contributors",
                      "commit": commit, "text": text[:MAX_CELL_CHARS], "code_blocks": blocks}
            if store.add(key, record, text):
                taken += 1
                count += 1
        print(f"- {section}: {count} halaman disimpan")


def main():
    # Opsi umum dipasang di setiap sumber supaya bisa ditulis setelah nama sumbernya.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--out-dir", default=str(ROOT / "runs/harvest"), help="folder hasil (bawaan: runs/harvest)")
    common.add_argument("--delay", type=float, default=1.0, help="jeda minimal antar-request API dalam detik")
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="source", required=True)

    hf = sub.add_parser("hf", parents=[common], help="baris dataset Hugging Face berlisensi permisif")
    hf.add_argument("--dataset", action="append", help="id dataset, boleh diulang")
    hf.add_argument("--from-report", help="laporan JSON dari find_datasets.py, misalnya runs/kandidat_coding.json")
    hf.add_argument("--rows", type=int, default=300, help="jumlah baris maksimal per dataset")
    hf.add_argument("--allow-status", nargs="+", default=["permisif"],
                    choices=["permisif", "share-alike", "bersyarat", "cek manual", "nonkomersial", "tanpa turunan"],
                    help="status lisensi yang diterima (bawaan: hanya permisif)")
    hf.add_argument("--include-benchmarks", action="store_true", help="ikut ambil dataset benchmark (skor eval jadi tidak bersih)")

    gh = sub.add_parser("github", parents=[common], help="fungsi Python berdocstring dari repo berlisensi permisif")
    gh.add_argument("--repo", action="append", help="repo tertentu (pemilik/nama), boleh diulang")
    gh.add_argument("--repos", type=int, default=0, help="jumlah repo hasil pencarian (bawaan 0 jika --repo dipakai, selain itu 10)")
    gh.add_argument("--query", help="kata kunci tambahan untuk pencarian repo, misalnya 'web framework'")
    gh.add_argument("--license", nargs="+", default=["mit", "apache-2.0", "bsd-3-clause"], help="lisensi untuk pencarian repo")
    gh.add_argument("--min-stars", type=int, default=500)
    gh.add_argument("--max-size-mb", type=int, default=100, help="lewati repo yang lebih besar dari ini")
    gh.add_argument("--max-per-repo", type=int, default=300, help="jumlah fungsi maksimal per repo")

    mdn = sub.add_parser("mdn", parents=[common], help="halaman MDN Web Docs (HTML, CSS, JavaScript)")
    mdn.add_argument("--path", action="append", help="folder di bawah files/en-us, misalnya web/javascript/guide; boleh diulang")
    mdn.add_argument("--mdn-dir", help="pakai clone mdn/content yang sudah ada")
    mdn.add_argument("--max-pages", type=int, default=2000)

    args = parser.parse_args()
    if args.source == "github" and not args.repo and args.repos == 0:
        args.repos = 10
    store = Store(args.out_dir)
    try:
        {"hf": harvest_hf, "github": harvest_github, "mdn": harvest_mdn}[args.source](args, store)
    finally:
        store.close()


if __name__ == "__main__":
    main()
