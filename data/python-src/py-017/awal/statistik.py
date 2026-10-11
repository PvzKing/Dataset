import sys
import unittest
from statistics import mean, median


def ringkasan_nilai(nilai):
    """Jumlah data, rata-rata, median, tertinggi, dan terendah dari daftar angka."""
    nilai = list(nilai)
    if not nilai:
        raise ValueError("daftar nilai kosong")
    return {"jumlah": len(nilai), "rata_rata": mean(nilai), "median": median(nilai),
            "tertinggi": max(nilai), "terendah": min(nilai)}


class Tes(unittest.TestCase):
    def test_ganjil_dan_genap(self):
        self.assertEqual(ringkasan_nilai([70, 90, 80])["median"], 80)
        r = ringkasan_nilai([70, 90, 80, 100])
        self.assertEqual((r["median"], r["rata_rata"], r["tertinggi"], r["terendah"]), (85, 85, 100, 70))

    def test_satu_nilai_dan_kosong(self):
        self.assertEqual(ringkasan_nilai([77])["rata_rata"], 77)
        with self.assertRaises(ValueError):
            ringkasan_nilai([])


if __name__ == "__main__":
    unittest.main()
