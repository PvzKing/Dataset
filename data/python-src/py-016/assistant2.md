Kode tadi memakai dua fitur yang belum ada di Python 3.8:

- **`match`/`case`** baru ada sejak Python 3.10. Inilah yang memicu `SyntaxError`.
- **`list[tuple[int, str]]` sebagai type hint** baru bisa dipakai sejak Python 3.9. Di 3.8, anotasi fungsi dievaluasi saat `def` dijalankan, jadi baris ini akan memicu `TypeError: 'type' object is not subscriptable` begitu `SyntaxError`-nya diperbaiki.

`SyntaxError` hanya menunjukkan masalah pertama yang ditemukan, jadi saya periksa seluruh file sekaligus. Dua fitur di atas adalah satu-satunya yang perlu diganti. `re`, f-string, dan `unittest` dengan `subTest` sudah tersedia di 3.8.

`match` saya ganti dengan tabel `SATUAN`. Hasilnya bahkan lebih ringkas, karena alias seperti `mnt` cukup ditambah satu baris di tabel:

```
<<<<<<< SEARCH
import re
import sys
import unittest

BAGIAN = re.compile(r"\s*(\d+)\s*([a-zA-Z]+)\s*")
=======
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
>>>>>>> REPLACE
```

```
<<<<<<< SEARCH
def pecah(teks: str) -> list[tuple[int, str]]:
=======
def pecah(teks: str) -> List[Tuple[int, str]]:
>>>>>>> REPLACE
```

```
<<<<<<< SEARCH
    for angka, satuan in bagian:
        match satuan:
            case "j" | "jam":
                kunci, detik = "jam", 3600
            case "m" | "mnt" | "menit":
                kunci, detik = "menit", 60
            case "d" | "dtk" | "detik":
                kunci, detik = "detik", 1
            case _:
                raise ValueError(f"satuan tidak dikenal: {satuan!r}")
=======
    for angka, satuan in bagian:
        if satuan not in SATUAN:
            raise ValueError(f"satuan tidak dikenal: {satuan!r}")
        kunci, detik = SATUAN[satuan]
>>>>>>> REPLACE
```

Dicek dengan Python 3.8 dan versi terbaru:

```
{{run python3.8 durasi.py --tes}}
{{run python durasi.py --tes}}
```

Python 3.8 sudah tidak menerima pembaruan keamanan sejak Oktober 2024. Selama server belum di-upgrade, tambahkan `python3.8 durasi.py --tes` ke proses deploy, supaya fitur Python baru yang tidak sengaja terpakai langsung ketahuan sebelum sampai ke server.
