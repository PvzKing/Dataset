"""Rekap transaksi CSV (ekspor Excel) per bulan dan per kategori.

Pemakaian:
    python rekap.py FILE.csv
    python rekap.py --tes
"""
import csv
import io
import re
import sys
import unittest
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal

FORMAT_TANGGAL = ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y")
NOMINAL = re.compile(r"(-?)(?:rp\.?\s*)?(\d{1,3}(?:\.\d{3})*|\d+)(?:,(\d{1,2}))?", re.I)


def baca_tanggal(teks):
    for fmt in FORMAT_TANGGAL:
        try:
            return datetime.strptime(teks.strip(), fmt).date()
        except ValueError:
            pass
    raise ValueError(f"tanggal tidak valid: {teks!r}")


def baca_nominal(teks):
    """'Rp 1.250.000,50' -> Decimal('1250000.50'). Titik = ribuan, koma = desimal (format Indonesia)."""
    cocok = NOMINAL.fullmatch(teks.strip())
    if not cocok:
        raise ValueError(f"nominal tidak valid: {teks!r}")
    tanda, ribuan, sen = cocok.groups()
    return Decimal(f"{tanda}{ribuan.replace('.', '')}.{sen or '0'}")


def buka_csv(path):
    """Baca teks dengan encoding Excel yang umum; utf-8-sig membuang BOM di awal file."""
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            with open(path, encoding=encoding, newline="") as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    raise ValueError(f"{path}: encoding tidak dikenali")


def rekap(teks):
    """Kembalikan (per_bulan, per_kategori, daftar kesalahan per baris)."""
    try:
        dialek = csv.Sniffer().sniff(teks.splitlines()[0], delimiters=";,\t")
    except csv.Error:
        dialek = csv.excel
    baris = csv.reader(io.StringIO(teks), dialek)  # bukan splitlines(): sel berkutip boleh berisi baris baru
    kolom = [k.strip().lower() for k in next(baris)]
    hilang = {"tanggal", "kategori", "nominal"} - set(kolom)
    if hilang:
        raise ValueError(f"kolom tidak ditemukan: {', '.join(sorted(hilang))}")
    per_bulan, per_kategori, salah = defaultdict(Decimal), defaultdict(Decimal), []
    for nomor, isi in enumerate(baris, start=2):  # nomor baris seperti di Excel: baris 1 = judul kolom
        if not any(sel.strip() for sel in isi):
            continue
        data = dict(zip(kolom, isi))
        try:
            tanggal = baca_tanggal(data.get("tanggal", ""))
            nominal = baca_nominal(data.get("nominal", ""))
            kategori = " ".join(data.get("kategori", "").split()).capitalize() or "Tanpa kategori"
        except ValueError as e:
            salah.append((nomor, str(e)))
            continue
        per_bulan[tanggal.strftime("%Y-%m")] += nominal
        per_kategori[kategori] += nominal
    return dict(per_bulan), dict(per_kategori), salah


def rp(x):
    bulat, sen = f"{abs(x):.2f}".split(".")
    teks = "Rp" + f"{int(bulat):,}".replace(",", ".") + ("" if sen == "00" else f",{sen}")
    return "-" + teks if x < 0 else teks


class Tes(unittest.TestCase):
    def test_nominal(self):
        for teks, nilai in [("1.250.000", "1250000"), ("Rp 300.000", "300000"), ("250.000,50", "250000.50"),
                            ("-25.000", "-25000"), ("87500", "87500")]:
            self.assertEqual(baca_nominal(teks), Decimal(nilai))
        for teks in ["", "1,250,000.00", "12.50", "satu juta"]:
            with self.assertRaises(ValueError):
                baca_nominal(teks)

    def test_tanggal(self):
        self.assertEqual(baca_tanggal("03/01/2026"), date(2026, 1, 3))
        self.assertEqual(baca_tanggal("2026-02-27"), date(2026, 2, 27))
        with self.assertRaises(ValueError):
            baca_tanggal("31/02/2026")

    def test_koma_dan_kolom_hilang(self):
        per_bulan, per_kategori, salah = rekap("tanggal,kategori,nominal\n01/03/2026,Makan,10000\n")
        self.assertEqual(per_bulan, {"2026-03": Decimal("10000.0")})
        with self.assertRaises(ValueError):
            rekap("tanggal;nominal\n01/03/2026;10000\n")

    def test_sel_berisi_baris_baru(self):
        teks = 'tanggal;keterangan;kategori;nominal\n01/03/2026;"dua\nbaris";Makan;5.000\n02/03/2026;x;Makan;1.000\n'
        self.assertEqual(rekap(teks)[1], {"Makan": Decimal("6000.0")})


def main():
    if sys.argv[1:] == ["--tes"]:
        unittest.main(argv=sys.argv[:1])
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    per_bulan, per_kategori, salah = rekap(buka_csv(sys.argv[1]))
    print("Per bulan:")
    for bulan, total in sorted(per_bulan.items()):
        print(f"  {bulan}  {rp(total):>16}")
    print("Per kategori:")
    for kategori, total in sorted(per_kategori.items(), key=lambda kv: -kv[1]):
        print(f"  {kategori:<14}{rp(total):>16}")
    print(f"Total: {rp(sum(per_bulan.values()))}")
    if salah:
        print(f"{len(salah)} baris dilewati:")
        for nomor, alasan in salah:
            print(f"  baris {nomor}: {alasan}")


if __name__ == "__main__":
    main()
