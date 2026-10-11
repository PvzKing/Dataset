import re

PEMISAH = re.compile(r"[\s\-.()]")
# Nomor seluler Indonesia: setelah kode negara diawali 8, total 9–12 digit.
# [0-9], bukan \d: \d juga cocok dengan angka Unicode lain seperti ٠١٢.
NOMOR_SELULER = re.compile(r"8[0-9]{8,11}")


def normalisasi_hp(nomor: str) -> str:
    """'0812-3456-7890' -> '+6281234567890'. ValueError jika bukan nomor HP Indonesia."""
    if not isinstance(nomor, str):
        raise TypeError(f"nomor harus str, bukan {type(nomor).__name__}")
    bersih = PEMISAH.sub("", nomor)
    for awalan in ("+62", "62", "0"):
        if bersih.startswith(awalan):
            inti = bersih[len(awalan):]
            break
    else:
        raise ValueError(f"nomor harus diawali 0, 62, atau +62: {nomor!r}")
    if awalan != "0" and inti.startswith("0"):
        inti = inti[1:]  # "+62 0812..." sering ditulis orang; maksudnya jelas
    if not NOMOR_SELULER.fullmatch(inti):
        raise ValueError(f"bukan nomor HP Indonesia yang valid: {nomor!r}")
    return "+62" + inti


if __name__ == "__main__":
    contoh = ["0812-3456-7890", "62 812 3456 7890", "+62 (812) 3456.7890", "+62 0812 3456 7890", "0811234567"]
    for n in contoh:
        print(f"{n!r:24} -> {normalisasi_hp(n)}")
    for salah in ["0212345678", "812345678", "0812-34", "08123456789012", "0812abc4567", "0812٣٤٥٦٧٨٩٠", ""]:
        try:
            normalisasi_hp(salah)
        except ValueError as e:
            print("ditolak:", e)
