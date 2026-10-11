Error itu dan selisih 7 jam di server punya penyebab yang sama: `datetime.now()` tidak tahu zona waktunya.

**Penyebab**
Python membedakan dua jenis `datetime`:
- **naive** (tanpa zona waktu), seperti hasil `datetime.now()`. Nilainya hanya "jam di dinding" mesin yang menjalankannya.
- **aware** (dengan zona waktu), seperti hasil `fromisoformat("...+07:00")`. Nilainya menunjuk satu titik waktu yang pasti.

Python menolak membandingkan keduanya karena memang tidak bisa diketahui mana yang lebih dulu, makanya muncul `TypeError`.

`.replace(tzinfo=None)` menghilangkan error dengan membuang informasi zona waktu tenggatnya. Setelah itu kedua angka jam dibandingkan apa adanya. Di laptop, `datetime.now()` berisi jam WIB, jadi hasilnya kebetulan benar. Server umumnya memakai UTC, yang 7 jam di belakang WIB. Saat pukul 17.30 WIB, `datetime.now()` di server berisi 10.30, dan 10.30 < 17.00, jadi tugas dianggap belum terlambat sampai jam server menunjukkan 17.00 UTC, yaitu pukul 24.00 WIB.

**Perbaikan**
Jangan buang zona waktu. Ambil waktu sekarang dalam bentuk aware dengan `datetime.now(timezone.utc)`. Datetime aware dengan zona berbeda (+07:00, Z, +08:00) dibandingkan sebagai titik waktu yang sama di dunia, jadi hasilnya benar di mesin mana pun. Tenggat tanpa zona waktu saya tolak dengan pesan yang jelas, karena tenggat seperti itu memang ambigu:

```
<<<<<<< SEARCH
from datetime import datetime


def terlambat(tenggat_iso, sekarang=None):
    sekarang = sekarang or datetime.now()
    return sekarang > datetime.fromisoformat(tenggat_iso)
=======
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

WIB = ZoneInfo("Asia/Jakarta")


def terlambat(tenggat_iso, sekarang=None):
    tenggat = datetime.fromisoformat(tenggat_iso)
    if tenggat.tzinfo is None:
        raise ValueError(f"tenggat harus menyertakan zona waktu, misalnya +07:00: {tenggat_iso!r}")
    sekarang = sekarang or datetime.now(timezone.utc)  # waktu sekarang yang tahu zona waktunya
    if sekarang.tzinfo is None:
        raise ValueError("sekarang harus datetime dengan zona waktu")
    return sekarang > tenggat  # datetime ber-zona dibandingkan sebagai titik waktu yang sama di dunia
>>>>>>> REPLACE
```

Untuk mengecek, saya pakai waktu "sekarang" yang tetap, yaitu 17.30 WIB, supaya hasilnya bisa diperiksa tanpa bergantung pada jam saat kode dijalankan:

```
<<<<<<< SEARCH
if __name__ == "__main__":
    # tenggat dari API, format ISO 8601
    for t in ["2026-10-12T17:00:00+07:00", "2026-10-12T10:00:00Z"]:
        print(t, "terlambat" if terlambat(t) else "masih ada waktu")
=======
if __name__ == "__main__":
    # Waktu tetap supaya hasilnya bisa diperiksa: 12 Oktober 2026 pukul 10.30 UTC = 17.30 WIB.
    sekarang = datetime(2026, 10, 12, 10, 30, tzinfo=timezone.utc)
    print("sekarang:", sekarang.astimezone(WIB).strftime("%d-%m-%Y %H.%M WIB"))
    for t in ["2026-10-12T17:00:00+07:00", "2026-10-12T10:00:00Z", "2026-10-12T18:00:00+08:00", "2026-10-12T18:00:00+07:00"]:
        print(t, "terlambat" if terlambat(t, sekarang) else "masih ada waktu")
    try:
        terlambat("2026-10-12T17:00:00", sekarang)
    except ValueError as e:
        print("ValueError:", e)
>>>>>>> REPLACE
```

**Cara cek**

```
{{run python tenggat.py}}
```

Tenggat 18.00 WITA (+08:00) sama dengan 17.00 WIB, jadi juga sudah lewat pada 17.30 WIB, sedangkan tenggat 18.00 WIB belum. Hasil ini sama di laptop maupun di server UTC.

Dua catatan untuk pemakaian di aplikasi:
- **Simpan dan bandingkan waktu dalam UTC**, lalu ubah ke WIB, WITA, atau WIT hanya saat ditampilkan dengan `.astimezone(ZoneInfo("Asia/Jakarta"))`.
- **Akhiran `Z` pada tenggat baru diterima `fromisoformat` sejak Python 3.11.** Di versi lama, ganti dulu `Z` menjadi `+00:00`. `ZoneInfo` di Windows butuh `pip install tzdata`.
