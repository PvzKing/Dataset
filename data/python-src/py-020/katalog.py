"""Buat halaman katalog HTML statis dari produk.json.

Pemakaian:
    python katalog.py produk.json [--keluar FOLDER]
    python katalog.py --tes
"""
import argparse
import json
import re
import sys
import unittest
from html import escape
from pathlib import Path
from urllib.parse import quote

CSS = """*{box-sizing:border-box}body{margin:0;font-family:system-ui,sans-serif;background:#fdf8f3;color:#2d2a26}
header{background:#9a3412;color:#fff;padding:20px 16px}h1{margin:0;font-size:1.5rem}main{max-width:960px;margin:0 auto;padding:16px}
h2{margin:24px 0 12px;font-size:1.15rem}.grid{display:grid;gap:12px;grid-template-columns:repeat(auto-fill,minmax(220px,1fr))}
.kartu{background:#fff;border:1px solid #f1e4d8;border-radius:12px;padding:14px;display:flex;flex-direction:column;gap:8px}
.kartu h3{margin:0;font-size:1rem;overflow-wrap:anywhere}.harga{font-weight:700;color:#9a3412}
.pesan{margin-top:auto;text-align:center;background:#15803d;color:#fff;text-decoration:none;padding:10px;border-radius:8px}
.habis{margin-top:auto;text-align:center;background:#e7e5e4;color:#57534e;padding:10px;border-radius:8px}"""


def rupiah(n):
    return "Rp" + f"{n:,}".replace(",", ".")


def nomor_wa(nomor):
    """'0812-3456-7890' -> '6281234567890' (format wa.me: kode negara tanpa +)."""
    angka = re.sub(r"\D", "", nomor)
    if angka.startswith("0"):
        angka = "62" + angka[1:]
    if not re.fullmatch(r"628\d{7,11}", angka):
        raise ValueError(f"nomor WhatsApp tidak valid: {nomor!r}")
    return angka


def periksa(data):
    """Kumpulkan semua masalah sekaligus, supaya pemilik toko bisa memperbaiki semuanya dalam sekali jalan."""
    masalah = []
    for i, p in enumerate(data.get("produk", []), start=1):
        if not isinstance(p.get("nama"), str) or not p["nama"].strip():
            masalah.append(f"produk ke-{i}: nama wajib diisi")
        for kolom in ("harga", "stok"):
            if not isinstance(p.get(kolom), int) or isinstance(p.get(kolom), bool) or p[kolom] < 0:
                masalah.append(f"produk ke-{i}: {kolom} harus bilangan bulat >= 0")
    if masalah:
        raise ValueError("\n".join(masalah))


def buat_html(data):
    periksa(data)
    toko, wa = data["toko"], nomor_wa(data["whatsapp"])
    per_kategori = {}
    for p in sorted(data["produk"], key=lambda p: (p.get("kategori") or "Lainnya", p["nama"].casefold())):
        per_kategori.setdefault(p.get("kategori") or "Lainnya", []).append(p)
    bagian = []
    for kategori, daftar in per_kategori.items():
        kartu = []
        for p in daftar:
            if p["stok"] > 0:
                teks = f"Halo {toko}, saya mau pesan {p['nama']} ({rupiah(p['harga'])})."
                # Dua lapis: quote() untuk URL, lalu escape() karena URL itu ditaruh di atribut HTML.
                aksi = (f'<a class="pesan" href="{escape(f"https://wa.me/{wa}?text={quote(teks)}")}" '
                        f'target="_blank" rel="noopener">Pesan via WhatsApp</a>')
            else:
                aksi = '<span class="habis">Stok habis</span>'
            kartu.append(f'<article class="kartu"><h3>{escape(p["nama"])}</h3>'
                         f'<span class="harga">{rupiah(p["harga"])}</span>{aksi}</article>')
        bagian.append(f'<section><h2>{escape(kategori)}</h2><div class="grid">{"".join(kartu)}</div></section>')
    return (f'<!DOCTYPE html>\n<html lang="id">\n<head>\n<meta charset="UTF-8">\n'
            f'<meta name="viewport" content="width=device-width, initial-scale=1">\n'
            f'<title>Katalog {escape(toko)}</title>\n<style>{CSS}</style>\n</head>\n<body>\n'
            f'<header><h1>{escape(toko)}</h1></header>\n<main>{"".join(bagian)}</main>\n</body>\n</html>\n')


class Tes(unittest.TestCase):
    def data(self, **produk):
        return {"toko": "Toko <Uji> & Co", "whatsapp": "+62 812-1111-2222",
                "produk": [{"nama": "Kue", "harga": 10000, "kategori": "Kue", "stok": 1, **produk}]}

    def test_escape_teks_dan_atribut(self):
        html = buat_html(self.data(nama='Kue "Spesial" <b>&</b>'))
        self.assertIn("Kue &quot;Spesial&quot; &lt;b&gt;&amp;&lt;/b&gt;", html)
        self.assertNotIn("<b>", html)
        self.assertIn("Toko &lt;Uji&gt; &amp; Co", html)

    def test_link_whatsapp(self):
        html = buat_html(self.data(nama="Kopi & Teh"))
        link = re.search(r'href="([^"]+)"', html)[1]
        self.assertTrue(link.startswith("https://wa.me/6281211112222?text="))
        self.assertIn("Kopi%20%26%20Teh", link)  # & di nama tidak memotong parameter text

    def test_stok_habis_dan_urutan(self):
        data = self.data(stok=0)
        data["produk"].append({"nama": "Air", "harga": 5000, "kategori": "", "stok": 3})
        html = buat_html(data)
        self.assertIn("Stok habis", html)
        self.assertLess(html.index("<h2>Kue</h2>"), html.index("<h2>Lainnya</h2>"))
        self.assertIn("Rp10.000", html)

    def test_semua_masalah_dilaporkan(self):
        data = self.data(harga=-1)
        data["produk"].append({"nama": " ", "harga": 1.5, "stok": True})
        with self.assertRaises(ValueError) as e:
            buat_html(data)
        self.assertEqual(len(str(e.exception).splitlines()), 4)


def main():
    if sys.argv[1:] == ["--tes"]:
        unittest.main(argv=sys.argv[:1])
    parser = argparse.ArgumentParser(description="Buat katalog HTML statis dari JSON.")
    parser.add_argument("data", type=Path)
    parser.add_argument("--keluar", type=Path, default=Path("situs"))
    args = parser.parse_args()
    data = json.loads(args.data.read_text(encoding="utf-8"))
    try:
        html = buat_html(data)
    except ValueError as e:
        sys.exit(f"data belum benar:\n{e}")
    args.keluar.mkdir(parents=True, exist_ok=True)
    (args.keluar / "index.html").write_text(html, encoding="utf-8")
    kategori = {p.get("kategori") or "Lainnya" for p in data["produk"]}
    print(f"ditulis {args.keluar / 'index.html'}: {len(data['produk'])} produk, {len(kategori)} kategori")


if __name__ == "__main__":
    main()
