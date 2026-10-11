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
