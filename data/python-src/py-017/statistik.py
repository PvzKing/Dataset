import unittest
from statistics import mean, median


def ke_angka(sel):
    """Angka dari sel spreadsheet: 85, 85.5, "85", "85,5". None jika bukan angka (kosong, "sakit", True)."""
    if isinstance(sel, bool):
        return None
    if isinstance(sel, (int, float)):
        return sel
    if isinstance(sel, str):
        teks = sel.strip().replace(",", ".")
        try:
            return int(teks) if teks.isdigit() else float(teks)
        except ValueError:
            return None
    return None


def ringkasan_nilai(nilai):
    """Ringkasan dari sel yang berisi angka. Sel lain dilewati dan dilaporkan di "dilewati" (posisi, isi)."""
    angka, dilewati = [], []
    for posisi, sel in enumerate(nilai, start=1):
        x = ke_angka(sel)
        if x is None or x != x:  # x != x: NaN dari sel error di spreadsheet
            dilewati.append((posisi, sel))
        else:
            angka.append(x)
    if not angka:
        raise ValueError(f"tidak ada nilai berupa angka ({len(dilewati)} sel dilewati)")
    return {"jumlah": len(angka), "rata_rata": mean(angka), "median": median(angka),
            "tertinggi": max(angka), "terendah": min(angka), "dilewati": dilewati}


class Tes(unittest.TestCase):
    def test_ganjil_dan_genap(self):
        self.assertEqual(ringkasan_nilai([70, 90, 80])["median"], 80)
        r = ringkasan_nilai([70, 90, 80, 100])
        self.assertEqual((r["median"], r["rata_rata"], r["tertinggi"], r["terendah"]), (85, 85, 100, 70))

    def test_satu_nilai_dan_kosong(self):
        self.assertEqual(ringkasan_nilai([77])["rata_rata"], 77)
        with self.assertRaises(ValueError):
            ringkasan_nilai([])

    def test_data_spreadsheet(self):
        r = ringkasan_nilai([85, "90", "", "85,5", " sakit ", None, 70, True, float("nan")])
        self.assertEqual((r["jumlah"], r["tertinggi"], r["terendah"]), (4, 90, 70))
        self.assertAlmostEqual(r["rata_rata"], 82.625)
        self.assertEqual([p for p, _ in r["dilewati"]], [3, 5, 6, 8, 9])

    def test_semua_bukan_angka(self):
        with self.assertRaises(ValueError):
            ringkasan_nilai(["", "izin", None])


if __name__ == "__main__":
    unittest.main()
