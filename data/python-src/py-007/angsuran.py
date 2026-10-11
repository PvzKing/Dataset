"""Angsuran anuitas dan tabel amortisasi.

Pemakaian:
    python angsuran.py POKOK BUNGA_PERSEN_PER_TAHUN TENOR_BULAN
    python angsuran.py --tes
"""
import sys
import unittest
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

RUPIAH = Decimal("1")


@dataclass(frozen=True)
class Baris:
    bulan: int
    angsuran: Decimal
    bunga: Decimal
    pokok: Decimal
    sisa: Decimal


def bulat(x):
    return x.quantize(RUPIAH, rounding=ROUND_HALF_UP)


def jadwal(pokok, bunga_tahunan, tenor):
    """Tabel amortisasi. Bulan terakhir melunasi sisa pokok, jadi total pokok selalu tepat sama dengan pinjaman."""
    pokok, bunga_tahunan = Decimal(str(pokok)), Decimal(str(bunga_tahunan))
    if pokok <= 0 or bunga_tahunan < 0:
        raise ValueError("pokok harus > 0 dan bunga tidak boleh negatif")
    if not isinstance(tenor, int) or tenor < 1:
        raise ValueError("tenor harus bilangan bulat minimal 1 bulan")
    r = bunga_tahunan / 100 / 12
    angsuran = bulat(pokok / tenor if r == 0 else pokok * r / (1 - (1 + r) ** -tenor))
    sisa, tabel = pokok, []
    for bulan in range(1, tenor + 1):
        bunga = bulat(sisa * r)
        bayar_pokok = sisa if bulan == tenor else angsuran - bunga
        sisa -= bayar_pokok
        tabel.append(Baris(bulan, bunga + bayar_pokok, bunga, bayar_pokok, sisa))
    return tabel


def rp(x):
    return "Rp" + f"{int(x):,}".replace(",", ".")


def cetak(tabel):
    print(f"Angsuran per bulan: {rp(tabel[0].angsuran)} (bulan terakhir {rp(tabel[-1].angsuran)})")
    print(f"Total bunga: {rp(sum(b.bunga for b in tabel))}")
    print(f"{'Bulan':>5} {'Angsuran':>14} {'Bunga':>12} {'Pokok':>14} {'Sisa':>15}")
    tampil = tabel if len(tabel) <= 8 else tabel[:3] + [None] + tabel[-3:]
    for b in tampil:
        if b is None:
            print(f"{'...':>5}")
            continue
        print(f"{b.bulan:>5} {rp(b.angsuran):>14} {rp(b.bunga):>12} {rp(b.pokok):>14} {rp(b.sisa):>15}")


class Tes(unittest.TestCase):
    def test_total_pokok_tepat(self):
        for pokok, bunga, tenor in [(100_000_000, 12, 12), (7_500_000, 9.5, 36), (1_000_001, 24, 7), (250_000_000, 7.25, 240)]:
            with self.subTest(pokok=pokok, bunga=bunga, tenor=tenor):
                tabel = jadwal(pokok, bunga, tenor)
                self.assertEqual(sum(b.pokok for b in tabel), pokok)
                self.assertEqual(tabel[-1].sisa, 0)
                self.assertEqual(len({b.angsuran for b in tabel[:-1]}), 1)  # angsuran tetap kecuali bulan terakhir

    def test_nilai_rumus(self):
        # 100 juta, 12%/tahun (1%/bulan), 12 bulan: 100.000.000 × 0,01 / (1 − 1,01^−12) = 8.884.878,79
        self.assertEqual(jadwal(100_000_000, 12, 12)[0].angsuran, 8_884_879)

    def test_bunga_nol(self):
        tabel = jadwal(1_000_000, 0, 3)
        self.assertEqual([b.angsuran for b in tabel], [333_333, 333_333, 333_334])
        self.assertTrue(all(b.bunga == 0 for b in tabel))

    def test_input_salah(self):
        for args in [(0, 10, 12), (-5, 10, 12), (1_000_000, -1, 12), (1_000_000, 10, 0), (1_000_000, 10, 1.5)]:
            with self.subTest(args=args), self.assertRaises(ValueError):
                jadwal(*args)


if __name__ == "__main__":
    if sys.argv[1:] == ["--tes"]:
        unittest.main(argv=sys.argv[:1])
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    try:
        cetak(jadwal(Decimal(sys.argv[1]), Decimal(sys.argv[2]), int(sys.argv[3])))
    except (ValueError, ArithmeticError) as e:
        sys.exit(f"error: {e}")
