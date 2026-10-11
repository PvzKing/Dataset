import hashlib
import sqlite3

from akun import Akun, hash_password

akun = Akun(":memory:")
akun.daftar("dr.sari", "Rahasia#2026")
print("password benar :", akun.login("dr.sari", "Rahasia#2026"))
print("password salah :", akun.login("dr.sari", "tebak-tebak"))
print("username asal  :", akun.login("siapa", "x"))
md5_x = hashlib.md5(b"x").hexdigest()
print("injeksi SQL    :", akun.login(f"bukan-siapa-siapa' UNION SELECT '{md5_x}' --", "x"))
print("password sama, hash beda:", hash_password("Rahasia#2026") != hash_password("Rahasia#2026"))
for args in [("dr.sari", "Lain#2026x"), ("budi", "pendek")]:
    try:
        akun.daftar(*args)
    except ValueError as e:
        print("ditolak:", e)
