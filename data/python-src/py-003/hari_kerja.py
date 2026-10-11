from datetime import date, datetime, timedelta


def _cek_tanggal(nilai, nama):
    # datetime adalah turunan date; membandingkan keduanya memicu TypeError, jadi tolak sejak awal.
    if not isinstance(nilai, date) or isinstance(nilai, datetime):
        raise TypeError(f"{nama} harus datetime.date, bukan {type(nilai).__name__}")


def hari_kerja(mulai, selesai, libur=()):
    """Jumlah hari Senin–Jumat dari mulai sampai selesai (inklusif), dikurangi libur yang jatuh di hari kerja."""
    _cek_tanggal(mulai, "mulai")
    _cek_tanggal(selesai, "selesai")
    if mulai > selesai:
        raise ValueError(f"mulai ({mulai}) tidak boleh setelah selesai ({selesai})")
    total_hari = (selesai - mulai).days + 1
    minggu_penuh, sisa = divmod(total_hari, 7)
    jumlah = minggu_penuh * 5  # setiap 7 hari berturut-turut selalu berisi tepat 5 hari kerja
    for i in range(sisa):
        if (mulai + timedelta(days=minggu_penuh * 7 + i)).weekday() < 5:
            jumlah += 1
    libur_kerja = set()
    for hari in libur:
        _cek_tanggal(hari, "tanggal libur")
        if mulai <= hari <= selesai and hari.weekday() < 5:
            libur_kerja.add(hari)  # set: libur yang tercantum dua kali tidak dikurangi dua kali
    return jumlah - len(libur_kerja)


def _hari_kerja_lambat(mulai, selesai, libur):
    """Cara lambat hari per hari, hanya untuk cek silang."""
    hari, jumlah = mulai, 0
    while hari <= selesai:
        jumlah += hari.weekday() < 5 and hari not in libur
        hari += timedelta(days=1)
    return jumlah


if __name__ == "__main__":
    import random

    libur = [date(2026, 1, 1), date(2026, 1, 3), date(2026, 1, 1)]  # 3 Jan hari Sabtu; 1 Jan tercantum dua kali
    print("Januari 2026:", hari_kerja(date(2026, 1, 1), date(2026, 1, 31), libur))
    print("satu hari Sabtu:", hari_kerja(date(2026, 1, 3), date(2026, 1, 3)))
    print("10 tahun:", hari_kerja(date(2020, 1, 1), date(2029, 12, 31)))

    acak = random.Random(7)
    for _ in range(2000):
        a = date(2024, 1, 1) + timedelta(days=acak.randrange(800))
        b = a + timedelta(days=acak.randrange(60))
        lib = {a + timedelta(days=acak.randrange(60)) for _ in range(5)}
        assert hari_kerja(a, b, lib) == _hari_kerja_lambat(a, b, lib), (a, b, lib)
    print("cek silang 2000 rentang acak: cocok")

    for salah in [(date(2026, 2, 1), date(2026, 1, 1)), (datetime(2026, 1, 1), date(2026, 1, 5))]:
        try:
            hari_kerja(*salah)
        except (ValueError, TypeError) as e:
            print(f"{type(e).__name__}: {e}")
