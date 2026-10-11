import unittest
from datetime import date, timedelta

from denda import hitung_denda

PINJAM = date(2026, 3, 2)


def kembali(hari_ke):
    return PINJAM + timedelta(days=hari_ke)


class TesDenda(unittest.TestCase):
    def test_batas_masa_pinjam(self):
        """Hari ke-7 masih gratis, denda mulai hari ke-8."""
        for hari_ke, denda in [(6, 0), (7, 0), (8, 1000), (9, 2000)]:
            with self.subTest(hari_ke=hari_ke):
                self.assertEqual(hitung_denda(PINJAM, kembali(hari_ke)), denda)

    def test_kembali_lebih_cepat(self):
        """Mengembalikan lebih cepat tidak menghasilkan denda negatif."""
        for hari_ke in [0, 1, 3]:
            with self.subTest(hari_ke=hari_ke):
                self.assertEqual(hitung_denda(PINJAM, kembali(hari_ke)), 0)

    def test_batas_maksimal(self):
        """Denda berhenti di Rp50.000: tepat di batas, satu hari setelahnya, dan sangat lama."""
        for hari_ke in [57, 58, 400]:
            with self.subTest(hari_ke=hari_ke):
                self.assertEqual(hitung_denda(PINJAM, kembali(hari_ke)), 50000)
        self.assertEqual(hitung_denda(PINJAM, kembali(56)), 49000)

    def test_melewati_akhir_bulan_dan_kabisat(self):
        """Selisih hari dihitung dengan kalender, termasuk 29 Februari 2028."""
        self.assertEqual(hitung_denda(date(2028, 2, 25), date(2028, 3, 5)), 2000)

    def test_parameter_lain(self):
        self.assertEqual(hitung_denda(PINJAM, kembali(20), lama_pinjam=14, denda_per_hari=500), 3000)

    def test_tanggal_kembali_sebelum_pinjam(self):
        """Data salah input harus ditolak, bukan dihitung sebagai 'tidak terlambat'."""
        with self.assertRaises(ValueError):
            hitung_denda(PINJAM, PINJAM - timedelta(days=1))


if __name__ == "__main__":
    unittest.main()
