"""Ultradistillation: kelompok dataset terpisah dari jawaban AI lain yang dikirim pemilik repo, lalu diperiksa otomatis.

Alur:
  1. `salin`   menulis data/ultradistillation/SALIN.md: setiap pertanyaan yang belum dijawab, sudah digabung dengan
               instruksi awal, siap disalin ke AI (satu percakapan baru per pertanyaan).
  2. Pemilik menyalin jawaban AI itu dan mengirimkannya, beserta nama AI dan versinya.
  3. `simpan`  menyimpan jawaban ke data/ultradistillation/jawaban/<id>.md, dengan sumber di bagian depan berkas.
  4. `cek`     memeriksa setiap jawaban:
                 python, python_debug  kode lulus tes tersembunyi di pertanyaan.jsonl (pengambil kode sama dengan IndoPy)
                 web                   lolos pemeriksaan Chromium yang sama dengan sulingan V7 dan punya Cek kebutuhan
                 hukum                 wajib ditandai `diperiksa: ya` oleh pemilik (pasal dan ayat tidak bisa dicek otomatis)
                 semua                 tidak kosong, tanpa tag <think>, tanpa basa-basi "sebagai AI", dan tidak punya
                                       13-gram yang sama dengan soal uji (IndoPy, Web-eval, HumanEval+, MBPP+)
  5. `bangun`  menulis data/ultradistillation/ultradistillation.jsonl dari jawaban yang lolos, dalam format train.jsonl.
               Instruksi awal tidak ikut disimpan: model belajar menjawab dengan format itu tanpa diberi instruksi.

Pemakaian:
    python scripts/ultradistillation.py salin
    python scripts/ultradistillation.py simpan ud-001 --sumber "Nama AI versi X" < jawaban.md
    python scripts/ultradistillation.py sumber ud-001 "Nama AI versi X"   # sumber yang belum disebut saat dikirim
    python scripts/ultradistillation.py tolak ud-003 "alasan"            # cacat saat ditinjau: tetap tersimpan, tidak dipakai
    python scripts/ultradistillation.py uji-manual ud-003 "catatan"      # sudah diuji tangan di browser
    python scripts/ultradistillation.py periksa ud-012            # tandai jawaban hukum sudah diperiksa pemilik
    python scripts/ultradistillation.py cek [--tanpa-browser] [--tanpa-mbppplus]
    python scripts/ultradistillation.py bangun

Kelompok ini terpisah dari data/train.jsonl dan tidak otomatis ikut training. Baca bagian sumber dan syarat layanan di
data/ultradistillation/README.md sebelum mengisi jawaban.
"""
import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FOLDER = ROOT / "data" / "ultradistillation"
PERTANYAAN = FOLDER / "pertanyaan.jsonl"
JAWABAN = FOLDER / "jawaban"
HASIL = FOLDER / "ultradistillation.jsonl"
INSTRUKSI = FOLDER / "instruksi-awal.md"
BELUM = "belum disebut"  # jawaban sudah dikirim, tetapi nama AI-nya belum; tidak lolos sampai diisi dengan `sumber`
BASA_BASI = re.compile(r"\b(sebagai (sebuah )?(ai|model bahasa|asisten ai)|as an ai|as a language model|"
                       r"saya adalah (sebuah )?(ai|model bahasa)|i am an ai)\b", re.I)

sys.path.insert(0, str(ROOT / "scripts"))


def pertanyaan():
    return {r["id"]: r for r in map(json.loads, PERTANYAAN.read_text(encoding="utf-8").splitlines()) if r}


LABEL = {"web": "Website", "python": "Python", "python_debug": "Python", "hukum": "Hukum Indonesia"}


def instruksi(kategori):
    """Paragraf umum instruksi awal ditambah aturan format untuk kategori itu saja (bawaan: "Lainnya")."""
    baris = [b for b in INSTRUKSI.read_text(encoding="utf-8").splitlines() if b.strip() and not b.startswith(("#", ">"))]
    umum = [b for b in baris if not b.startswith("- ") and not b.startswith("Format ")]
    label = LABEL.get(kategori, "Lainnya")
    aturan = next(b[2:].split(": ", 1)[1] for b in baris if b.startswith(f"- {label}: "))
    return "\n\n".join(umum + ["Format jawaban: " + aturan])


def baca_jawaban(qid):
    """(metadata, isi) dari jawaban/<id>.md, atau None jika belum ada."""
    path = JAWABAN / f"{qid}.md"
    if not path.is_file():
        return None
    teks = path.read_text(encoding="utf-8")
    meta, isi = {}, teks
    m = re.match(r"---\n(.*?)\n---\n", teks, re.S)
    if m:
        for baris in m[1].splitlines():
            k, _, v = baris.partition(":")
            meta[k.strip()] = v.strip()
        isi = teks[m.end():]
    return meta, isi.strip()


def tulis_jawaban(qid, meta, isi):
    JAWABAN.mkdir(parents=True, exist_ok=True)
    depan = "\n".join(f"{k}: {v}" for k, v in meta.items())
    (JAWABAN / f"{qid}.md").write_text(f"---\n{depan}\n---\n{isi.strip()}\n", encoding="utf-8")


# ---------------------------------------------------------------- perintah

def cmd_salin(args):
    qs = pertanyaan()
    belum = [q for qid, q in qs.items() if args.semua or baca_jawaban(qid) is None]
    blok = [f"# Pertanyaan ultradistillation yang belum dijawab ({len(belum)} dari {len(qs)})\n",
            "Salin satu blok ke **percakapan baru** di AI-nya. Setelah AI menjawab, salin jawabannya dengan tombol "
            "salin (supaya format Markdown dan blok kodenya ikut), lalu kirim ke chat dengan baris pertama "
            "`<id> · <nama AI dan versinya>`.\n"]
    for q in belum:
        blok.append(f"## {q['id']} · {q['kategori']}\n\n````text\n{instruksi(q['kategori'])}\n\n---\n\n{q['prompt']}\n````\n")
    teks = "\n".join(blok)
    (FOLDER / "SALIN.md").write_text(teks, encoding="utf-8")
    print(teks if args.cetak else f"{len(belum)} pertanyaan ditulis ke {FOLDER / 'SALIN.md'}")


def cmd_simpan(args):
    qs = pertanyaan()
    if args.id not in qs:
        sys.exit(f"id tidak dikenal: {args.id}")
    if baca_jawaban(args.id) and not args.timpa:
        sys.exit(f"{args.id} sudah punya jawaban; tambahkan --timpa untuk menggantinya")
    isi = Path(args.berkas).read_text(encoding="utf-8") if args.berkas else sys.stdin.read()
    if not isi.strip():
        sys.exit("jawaban kosong")
    meta = {"sumber": args.sumber, "tanggal": date.today().isoformat()}
    if qs[args.id]["kategori"] == "hukum":
        meta["diperiksa"] = "belum"
    tulis_jawaban(args.id, meta, isi)
    print(f"tersimpan: {JAWABAN / (args.id + '.md')} ({len(isi)} karakter, sumber {args.sumber})")


def cmd_sumber(args):
    j = baca_jawaban(args.id)
    if j is None:
        sys.exit(f"{args.id} belum punya jawaban")
    meta, isi = j
    meta["sumber"] = args.sumber
    tulis_jawaban(args.id, meta, isi)
    print(f"sumber {args.id}: {args.sumber}")


def ubah_meta(qid, **nilai):
    j = baca_jawaban(qid)
    if j is None:
        sys.exit(f"{qid} belum punya jawaban")
    meta, isi = j
    meta.update(nilai)
    tulis_jawaban(qid, meta, isi)


def cmd_tolak(args):
    ubah_meta(args.id, ditolak=args.alasan)
    print(f"{args.id} ditolak: {args.alasan}")


def cmd_uji_manual(args):
    ubah_meta(args.id, uji_manual=f"{date.today().isoformat()}: {args.catatan}")
    print(f"{args.id}: uji manual dicatat")


def cmd_periksa(args):
    j = baca_jawaban(args.id)
    if j is None:
        sys.exit(f"{args.id} belum punya jawaban")
    meta, isi = j
    meta["diperiksa"] = "ya"
    meta["diperiksa_tanggal"] = date.today().isoformat()
    tulis_jawaban(args.id, meta, isi)
    print(f"{args.id} ditandai sudah diperiksa pemilik")


def periksa_semua(args):
    """Kembalikan list (id, kategori, lolos, alasan) untuk setiap jawaban yang ada."""
    import sulingan

    qs = pertanyaan()
    ada = {qid: j for qid in qs if (j := baca_jawaban(qid))}
    index, grams, _ = sulingan.contamination_index(demo=args.tanpa_mbppplus)
    browser = playwright = None
    if not args.tanpa_browser and any(qs[q]["kategori"] == "web" for q in ada):
        from playwright.sync_api import sync_playwright
        playwright = sync_playwright().start()
        browser = playwright.chromium.launch(**({"executable_path": args.chromium} if args.chromium else {}))
    situs = FOLDER / ".situs"
    situs.mkdir(exist_ok=True)
    hasil = []
    try:
        for qid, (meta, isi) in ada.items():
            q = qs[qid]
            kand = {"text": isi, "selesai": True}
            alasan = None
            if meta.get("ditolak"):
                alasan = "ditolak saat ditinjau: " + meta["ditolak"]
            elif meta.get("sumber", "").lower() in ("", BELUM):
                alasan = "sumber jawaban belum dicatat"
            elif "<think>" in isi or "</think>" in isi:
                alasan = "berisi tag think"
            elif BASA_BASI.search(isi):
                alasan = f"basa-basi identitas AI: \"{BASA_BASI.search(isi)[0]}\""
            elif hits := {i for g in grams(q["prompt"] + "\n" + isi) for i in index.get(g, ())}:
                alasan = "tumpang tindih dengan soal uji: " + ", ".join(sorted(hits)[:3])
            elif q["kategori"] in ("python", "python_debug"):
                ok, why = sulingan.check_python({"entry": q["entry"], "tests": q["tes"]}, kand, 10)
                alasan = None if ok else f"tes gagal: {why}"
            elif q["kategori"] == "web":
                if browser is None:
                    alasan = "pemeriksaan Chromium dilewati (--tanpa-browser)"
                else:
                    # localStorage yang baru terisi setelah satu permainan selesai tidak terdeteksi pemeriksaan umum;
                    # uji-manual mencatat bahwa penyimpanannya sudah diuji tangan.
                    simpan = q.get("simpan") and not meta.get("uji_manual")
                    ok, why, _ = sulingan.check_web({**q, "simpan": simpan}, kand, browser, situs)
                    alasan = None if ok else why
            elif q["kategori"] == "hukum" and meta.get("diperiksa") != "ya":
                alasan = "menunggu pemeriksaan pemilik (pasal, ayat, dan nomor peraturan)"
            hasil.append((qid, q["kategori"], alasan is None, alasan or "lolos"))
    finally:
        if browser:
            browser.close()
            playwright.stop()
    return hasil


def cmd_cek(args):
    hasil = periksa_semua(args)
    for qid, kat, ok, alasan in hasil:
        print(f"{'✅' if ok else '❌'} {qid} {kat:<16} {alasan}")
    print(f"\n{sum(r[2] for r in hasil)} lolos dari {len(hasil)} jawaban; {len(pertanyaan()) - len(hasil)} pertanyaan "
          "belum dijawab")
    return hasil


def cmd_bangun(args):
    qs = pertanyaan()
    hasil = cmd_cek(args)
    rows = []
    for qid, kat, ok, _ in hasil:
        if not ok:
            continue
        meta, isi = baca_jawaban(qid)
        rows.append({"id": qid, "category": f"ud_{kat}", "source": f"ultradistillation: {meta['sumber']}",
                     "messages": [{"role": "user", "content": qs[qid]["prompt"]},
                                  {"role": "assistant", "content": isi}]})
    HASIL.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    print(f"ditulis {HASIL}: {len(rows)} sampel")


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="perintah", required=True)
    s = sub.add_parser("salin", help="tulis SALIN.md berisi pertanyaan siap salin")
    s.add_argument("--semua", action="store_true", help="termasuk yang sudah dijawab")
    s.add_argument("--cetak", action="store_true", help="cetak juga ke layar")
    s = sub.add_parser("simpan", help="simpan jawaban dari stdin atau --berkas")
    s.add_argument("id")
    s.add_argument("--sumber", required=True, help="nama AI dan versinya, misalnya \"DeepSeek-V3.2 (bobot terbuka)\"")
    s.add_argument("--berkas")
    s.add_argument("--timpa", action="store_true")
    s = sub.add_parser("sumber", help="isi atau ganti sumber jawaban yang sudah tersimpan")
    s.add_argument("id")
    s.add_argument("sumber")
    s = sub.add_parser("tolak", help="tolak jawaban yang cacat saat ditinjau (tetap tersimpan, tidak dipakai)")
    s.add_argument("id")
    s.add_argument("alasan")
    s = sub.add_parser("uji-manual", help="catat uji tangan di browser (melewati heuristik localStorage)")
    s.add_argument("id")
    s.add_argument("catatan")
    s = sub.add_parser("periksa", help="tandai jawaban hukum sudah diperiksa pemilik")
    s.add_argument("id")
    for nama in ("cek", "bangun"):
        s = sub.add_parser(nama)
        s.add_argument("--tanpa-browser", action="store_true", help="lewati pemeriksaan Chromium (jawaban web tidak lolos)")
        s.add_argument("--tanpa-mbppplus", action="store_true", help="jangan unduh MBPP+ untuk cek kontaminasi")
        s.add_argument("--chromium", help="path Chromium jika bukan bawaan Playwright")
    args = p.parse_args(argv)
    {"salin": cmd_salin, "simpan": cmd_simpan, "sumber": cmd_sumber, "tolak": cmd_tolak, "uji-manual": cmd_uji_manual,
     "periksa": cmd_periksa, "cek": cmd_cek, "bangun": cmd_bangun}[args.perintah](args)


if __name__ == "__main__":
    main()
