from datetime import datetime


def terlambat(tenggat_iso, sekarang=None):
    sekarang = sekarang or datetime.now()
    return sekarang > datetime.fromisoformat(tenggat_iso)


if __name__ == "__main__":
    # tenggat dari API, format ISO 8601
    for t in ["2026-10-12T17:00:00+07:00", "2026-10-12T10:00:00Z"]:
        print(t, "terlambat" if terlambat(t) else "masih ada waktu")
