"""Nominal rupiah dalam angka dan huruf (terbilang) untuk kwitansi, perjanjian, dan akta.

Pemakaian:
    python terbilang.py 1.250.000,50
    python terbilang.py --tes
"""
import re
import sys
import unittest
from decimal import Decimal

SATUAN = ["", "satu", "dua", "tiga", "empat", "lima", "enam", "tujuh", "delapan", "sembilan"]
SKALA = ["", "ribu", "juta", "miliar", "triliun"]
BATAS = 1000 ** len(SKALA)  # 10^15: di atas 999 triliun tidak ada nama skala lagi
SEN = Decimal("0.01")
# Format Indonesia: titik pemisah ribuan (selalu per 3 angka), koma desimal (paling banyak 2 angka sen).
POLA_RUPIAH = re.compile(r"(?:rp\.?\s*)?(\d{1,3}(?:\.\d{3})+|\d+)(?:,(\d{1,2}))?", re.I)


def _ratusan(n):
    """Kata-kata untuk 1..999; daftar kosong untuk 0."""
    ratus, sisa = divmod(n, 100)
    kata = ["seratus"] if ratus == 1 else [SATUAN[ratus], "ratus"] if ratus else []
    if sisa == 10:
        kata.append("sepuluh")
    elif sisa == 11:
        kata.append("sebelas")
    elif 11 < sisa < 20:
        kata += [SATUAN[sisa - 10], "belas"]
    else:
        puluh, satu = divmod(sisa, 10)
        kata += [SATUAN[puluh], "puluh"] if puluh else []
        kata += [SATUAN[satu]] if satu else []
    return kata


def terbilang(n):
    """Bilangan bulat dalam huruf: terbilang(1001000) -> 'satu juta seribu'."""
    if isinstance(n, bool) or not isinstance(n, int):
        raise TypeError(f"terbilang() butuh int, bukan {type(n).__name__}")
    if n < 0:
        return "minus " + terbilang(-n)
    if n == 0:
        return "nol"
    if n >= BATAS:
        raise ValueError("nilai terlalu besar: batasnya 999 triliun lebih sedikit")
    kata = []
    for i in reversed(range(len(SKALA))):
        grup = n // 1000 ** i % 1000
        if grup == 1 and i == 1:
            kata.append("seribu")  # "seribu", tetapi "satu juta", "satu miliar"
        elif grup:
            kata += _ratusan(grup) + ([SKALA[i]] if SKALA[i] else [])
    return " ".join(kata)


def ke_rupiah(nilai):
    """Ubah int, Decimal, atau teks format Indonesia menjadi Decimal dengan tepat 2 angka sen."""
    if isinstance(nilai, (bool, float)):
        raise TypeError("pakai int, Decimal, atau teks; float tidak tepat untuk uang (0.1 + 0.2 != 0.3)")
    if isinstance(nilai, str):
        cocok = POLA_RUPIAH.fullmatch(nilai.strip())
        if not cocok:
            raise ValueError(f"format tidak dikenali: {nilai!r}; contoh yang benar: 1.250.000,50")
        nilai = Decimal(cocok[1].replace(".", "") + "." + (cocok[2] or "0"))
    elif not isinstance(nilai, (int, Decimal)):
        raise TypeError(f"tipe {type(nilai).__name__} tidak didukung")
    d = Decimal(nilai)
    if not d.is_finite() or d < 0:
        raise ValueError("nominal uang harus angka 0 atau lebih")
    if d >= BATAS:  # dicek sebelum quantize, yang gagal untuk angka sangat besar
        raise ValueError("nominal terlalu besar: batasnya 999 triliun lebih sedikit")
    if d != d.quantize(SEN):
        raise ValueError(f"{d} punya lebih dari 2 angka di belakang koma; bulatkan dulu secara sadar")
    return d.quantize(SEN)


def kwitansi(nilai):
    """'Rp1.250.000,50 (satu juta dua ratus lima puluh ribu rupiah lima puluh sen)'."""
    rupiah, sen = divmod(int(ke_rupiah(nilai) * 100), 100)
    bagian = [terbilang(rupiah) + " rupiah"] if rupiah or not sen else []
    bagian += [terbilang(sen) + " sen"] if sen else []
    angka = f"Rp{rupiah:,}".replace(",", ".") + f",{sen:02d}"
    return f"{angka} ({' '.join(bagian)})"


class Tes(unittest.TestCase):
    def test_terbilang(self):
        kasus = {
            0: "nol", 7: "tujuh", 10: "sepuluh", 11: "sebelas", 12: "dua belas", 19: "sembilan belas",
            20: "dua puluh", 21: "dua puluh satu", 100: "seratus", 101: "seratus satu", 111: "seratus sebelas",
            250: "dua ratus lima puluh", 1000: "seribu", 1001: "seribu satu", 1100: "seribu seratus",
            11000: "sebelas ribu", 101000: "seratus satu ribu", 1000000: "satu juta",
            1001000: "satu juta seribu", 2000000000: "dua miliar", 10 ** 12: "satu triliun",
            1000000000001: "satu triliun satu", -45: "minus empat puluh lima",
        }
        for n, kata in kasus.items():
            with self.subTest(n=n):
                self.assertEqual(terbilang(n), kata)

    def test_angka_terbesar(self):
        sembilan = "sembilan ratus sembilan puluh sembilan"
        semua = " ".join(f"{sembilan} {s}".strip() for s in reversed(SKALA))
        self.assertEqual(terbilang(BATAS - 1), semua)

    def test_kwitansi(self):
        kasus = {
            1250000: "Rp1.250.000,00 (satu juta dua ratus lima puluh ribu rupiah)",
            "Rp 1.250.000,50": "Rp1.250.000,50 (satu juta dua ratus lima puluh ribu rupiah lima puluh sen)",
            "1250000,5": "Rp1.250.000,50 (satu juta dua ratus lima puluh ribu rupiah lima puluh sen)",
            Decimal("0.75"): "Rp0,75 (tujuh puluh lima sen)",
            "rp.1.000": "Rp1.000,00 (seribu rupiah)",
            0: "Rp0,00 (nol rupiah)",
        }
        for nilai, hasil in kasus.items():
            with self.subTest(nilai=nilai):
                self.assertEqual(kwitansi(nilai), hasil)

    def test_input_ditolak(self):
        salah_nilai = ["1,250,000.50", "12.50", "1,234", "1.25.000", "", "satu juta", Decimal("1.005"),
                       Decimal("NaN"), -1, BATAS, Decimal("1E+20")]
        for nilai in salah_nilai:
            with self.subTest(nilai=nilai), self.assertRaises(ValueError):
                kwitansi(nilai)
        for nilai in [0.1, True, None, [1000]]:
            with self.subTest(nilai=nilai), self.assertRaises(TypeError):
                kwitansi(nilai)


if __name__ == "__main__":
    if sys.argv[1:] == ["--tes"]:
        unittest.main(argv=sys.argv[:1])
    elif len(sys.argv) < 2:
        sys.exit(__doc__)
    try:
        print(kwitansi(" ".join(sys.argv[1:])))
    except ValueError as e:
        sys.exit(f"error: {e}")
