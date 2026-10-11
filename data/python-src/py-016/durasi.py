import re
import sys
import unittest
from typing import List, Tuple

BAGIAN = re.compile(r"\s*(\d+)\s*([a-zA-Z]+)\s*")
SATUAN = {
    "j": ("jam", 3600), "jam": ("jam", 3600),
    "m": ("menit", 60), "mnt": ("menit", 60), "menit": ("menit", 60),
    "d": ("detik", 1), "dtk": ("detik", 1), "detik": ("detik", 1),
}


def pecah(teks: str) -> List[Tuple[int, str]]:
    """'1j 30m' -> [(1, 'j'), (30, 'm')]. Seluruh teks harus terbaca; sisa yang tidak dikenali adalah error."""
    hasil, posisi = [], 0
    while posisi < len(teks):
        m = BAGIAN.match(teks, posisi)
        if not m:
            raise ValueError(f"tidak bisa membaca {teks[posisi:]!r}")
        hasil.append((int(m[1]), m[2].lower()))
        posisi = m.end()
    return hasil


def parse_durasi(teks: str) -> int:
    """Durasi seperti '1j 30m 15d' (jam, menit, detik) menjadi jumlah detik."""
    total, dipakai = 0, set()
    bagian = pecah(teks)
    if not bagian:
        raise ValueError("durasi kosong")
    for angka, satuan in bagian:
        if satuan not in SATUAN:
            raise ValueError(f"satuan tidak dikenal: {satuan!r}")
        kunci, detik = SATUAN[satuan]
        if kunci in dipakai:
            raise ValueError(f"satuan {kunci} ditulis dua kali")
        dipakai.add(kunci)
        total += angka * detik
    return total


class Tes(unittest.TestCase):
    def test_valid(self):
        for teks, detik in [("1j 30m", 5400), ("90m", 5400), ("1j30m15d", 5415), ("2 jam 5 menit", 7500),
                            ("  45D ", 45), ("0m", 0)]:
            with self.subTest(teks=teks):
                self.assertEqual(parse_durasi(teks), detik)

    def test_tidak_valid(self):
        for teks in ["", "   ", "1j 2j", "1x", "j30", "1.5j", "-5m", "1j abc"]:
            with self.subTest(teks=teks), self.assertRaises(ValueError):
                parse_durasi(teks)


if __name__ == "__main__":
    if sys.argv[1:] == ["--tes"]:
        unittest.main(argv=sys.argv[:1])
    print(parse_durasi(" ".join(sys.argv[1:])))
