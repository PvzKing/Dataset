import hashlib
import hmac
import secrets
import sqlite3

# OWASP menyarankan N=2^17 (128 MB memori per hash). Di sini 2^14 (16 MB) supaya ringan di server kecil; naikkan
# jika server mampu. Parameter disimpan di setiap hash, jadi bisa dinaikkan nanti tanpa merusak hash lama.
N, R, P = 2 ** 14, 8, 1
PANJANG_MINIMAL = 8


def hash_password(password):
    salt = secrets.token_bytes(16)  # salt acak per pengguna: password sama tidak menghasilkan hash sama
    h = hashlib.scrypt(password.encode(), salt=salt, n=N, r=R, p=P, dklen=32)
    return f"scrypt${N}${R}${P}${salt.hex()}${h.hex()}"


def cek_password(password, tersimpan):
    _, n, r, p, salt, h = tersimpan.split("$")
    hasil = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=int(n), r=int(r), p=int(p), dklen=32)
    return hmac.compare_digest(hasil.hex(), h)  # waktu pembandingan tidak bocorkan berapa karakter yang cocok


HASH_PALSU = hash_password(secrets.token_hex(16))


class Akun:
    def __init__(self, path):
        self.db = sqlite3.connect(path)
        self.db.execute("CREATE TABLE IF NOT EXISTS pengguna (username TEXT PRIMARY KEY, password TEXT NOT NULL)")

    def daftar(self, username, password):
        if len(password) < PANJANG_MINIMAL:
            raise ValueError(f"password minimal {PANJANG_MINIMAL} karakter")
        try:
            with self.db:  # commit jika berhasil, rollback jika error
                self.db.execute("INSERT INTO pengguna (username, password) VALUES (?, ?)",
                                (username, hash_password(password)))
        except sqlite3.IntegrityError:
            raise ValueError("username sudah dipakai") from None

    def login(self, username, password):
        """True jika cocok. Pesan gagal yang sama untuk username salah dan password salah."""
        row = self.db.execute("SELECT password FROM pengguna WHERE username = ?", (username,)).fetchone()
        if row is None:
            cek_password(password, HASH_PALSU)  # tetap menghitung hash supaya lama prosesnya sama
            return False
        return cek_password(password, row[0])
