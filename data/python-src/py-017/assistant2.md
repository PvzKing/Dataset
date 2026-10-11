Kebutuhannya sekarang berubah: input bukan lagi list angka yang bersih, tapi isi sel spreadsheet. Jadi setiap sel diubah dulu menjadi angka, dan sel yang tidak bisa diubah dicatat. Aturan yang saya pakai:

- **Diterima:** angka biasa (`85`, `85.5`), angka berupa teks (`"90"`), dan desimal berkoma (`"85,5"`).
- **Dilewati dan dilaporkan** beserta posisinya (dihitung dari 1, seperti nomor baris di spreadsheet):
  - sel kosong dan `None`;
  - teks seperti `"sakit"`;
  - `True`/`False` dari kolom centang. Di Python `True` juga bertipe `int` dan bernilai 1, jadi tanpa pengecekan khusus nilainya diam-diam ikut dihitung sebagai 1;
  - `NaN` dari sel error. `NaN` merusak rata-rata, dan `max`/`min` memberi hasil yang bergantung pada urutan data.
- **Kalau semua sel dilewati**, hasilnya `ValueError` dengan jumlah sel yang dilewati, bukan ringkasan kosong.

Perubahannya ada di bagian atas file. `import sys` yang tidak terpakai sekalian saya buang:

```
<<<<<<< SEARCH
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
=======
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
>>>>>>> REPLACE
```

Tes lama tetap berlaku. Saya tambahkan dua tes untuk data spreadsheet:

```
<<<<<<< SEARCH
        with self.assertRaises(ValueError):
            ringkasan_nilai([])
=======
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
>>>>>>> REPLACE
```

```
{{run python statistik.py}}
{{run python pakai.py}}
```

Sel ke-3 (kosong), ke-5 (`sakit`), dan ke-7 (`None`) dilewati, sedangkan `"85,5"` terbaca sebagai 85,5. Kalau ingin menampilkannya ke guru, posisi di `dilewati` bisa langsung dicocokkan dengan nomor baris di sheet, ditambah satu kalau baris pertama sheet berisi judul kolom.
