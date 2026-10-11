Hitunganmu benar. Masalahnya ada di `round()` bawaan Python, yang tidak memakai aturan ",5 ke atas".

**Penyebab**
Sejak Python 3, `round()` memakai **pembulatan bankir** (*round half to even*): angka yang tepat di tengah dibulatkan ke bilangan **genap** terdekat. Jadi 74,5 menjadi 74 dan 84,5 menjadi 84, sedangkan 85,5 menjadi 86. Hasilnya benar separuh waktu, dan karena itu kesalahan ini sering lolos dari pengecekan sekilas:

```python
{{file cek.py}}
```

```
{{run python cek.py}}
```

Baris kedua menunjukkan masalah kedua. Bobot `0.3` dan `0.4` adalah `float`, dan float tidak bisa menyimpan sebagian besar pecahan desimal dengan tepat. `2.675` sebenarnya tersimpan sebagai 2,67499999…, sehingga `round(2.675, 2)` menghasilkan 2,67. Di data kelas ini kebetulan belum muncul, tapi begitu ada nilai berkoma seperti 82,35, hasilnya bisa meleset dengan cara yang sama.

**Perbaikan**
Hitung dengan `Decimal`, tulis bobot sebagai string, dan bulatkan secara eksplisit dengan `ROUND_HALF_UP`:

```
<<<<<<< SEARCH
BOBOT = {"tugas": 0.3, "uts": 0.3, "uas": 0.4}
KKM = 75


def nilai_akhir(nilai):
    return round(sum(nilai[k] * b for k, b in BOBOT.items()))
=======
from decimal import ROUND_HALF_UP, Decimal

# Bobot ditulis sebagai string: Decimal(0.3) akan membawa galat float 0.299999999999999988897769...
BOBOT = {"tugas": Decimal("0.3"), "uts": Decimal("0.3"), "uas": Decimal("0.4")}
KKM = 75


def nilai_akhir(nilai):
    """Nilai akhir berbobot, dibulatkan ke bilangan bulat dengan aturan sekolah: ,5 ke atas."""
    total = sum(Decimal(str(nilai[k])) * b for k, b in BOBOT.items())
    return int(total.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
>>>>>>> REPLACE
```

Nilai siswa diubah lewat `Decimal(str(...))`, jadi input boleh tetap berupa `int` atau `float` dari spreadsheet. `str()` mengambil angka seperti yang tertulis, misalnya `82.35`, bukan representasi biner float-nya.

**Cara cek**

```
{{run python rapor.py}}
```

Ayu sekarang 75 dan tuntas, Bima 85. Citra dan Dewi tidak berubah, karena nilai mereka tidak tepat di ,5.

Karena status tuntas menentukan remedial, sebaiknya rekap yang sudah terlanjur dibagikan dengan script lama dicek ulang, terutama untuk siswa yang nilai akhirnya tepat 1 poin di bawah KKM.
