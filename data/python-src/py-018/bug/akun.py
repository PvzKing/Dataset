import hashlib
import sqlite3

db = sqlite3.connect("klinik.db")
db.execute("CREATE TABLE IF NOT EXISTS pengguna (username TEXT PRIMARY KEY, password TEXT)")


def daftar(username, password):
    h = hashlib.md5(password.encode()).hexdigest()
    db.execute(f"INSERT INTO pengguna VALUES ('{username}', '{h}')")
    db.commit()


def login(username, password):
    h = hashlib.md5(password.encode()).hexdigest()
    row = db.execute(f"SELECT password FROM pengguna WHERE username = '{username}'").fetchone()
    if row is None:
        return "username tidak ditemukan"
    if row[0] != h:
        return "password salah"
    return "berhasil"
