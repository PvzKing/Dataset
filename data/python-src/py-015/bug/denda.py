from datetime import date


def hitung_denda(tgl_pinjam: date, tgl_kembali: date, lama_pinjam=7, denda_per_hari=1000, maksimal=50000):
    """Denda per hari keterlambatan setelah masa pinjam, paling banyak `maksimal` rupiah."""
    terlambat = (tgl_kembali - tgl_pinjam).days - lama_pinjam
    return min(terlambat * denda_per_hari, maksimal)
