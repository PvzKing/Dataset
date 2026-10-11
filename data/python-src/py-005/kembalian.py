from math import gcd


def pecahan_minimal(jumlah, pecahan):
    """Kombinasi {pecahan: banyaknya} dengan total keping paling sedikit, atau None jika tidak bisa dibentuk."""
    if not all(isinstance(x, int) and not isinstance(x, bool) for x in [jumlah, *pecahan]):
        raise TypeError("jumlah dan pecahan harus bilangan bulat (rupiah, bukan float)")
    if jumlah < 0 or not pecahan or any(p <= 0 for p in pecahan):
        raise ValueError("jumlah harus >= 0 dan setiap pecahan harus > 0")
    pecahan = sorted(set(pecahan))
    # Semua pecahan Rupiah kelipatan 100: bagi dengan FPB supaya tabel 100x lebih kecil.
    fpb = gcd(*pecahan)
    if jumlah % fpb:
        return None
    n, satuan = jumlah // fpb, [p // fpb for p in pecahan]
    TAK_TERHINGGA = n + 1
    keping = [0] + [TAK_TERHINGGA] * n   # keping[i] = jumlah keping minimal untuk nominal i
    terakhir = [0] * (n + 1)             # pecahan terakhir yang dipakai, untuk merekonstruksi jawaban
    for i in range(1, n + 1):
        for s in satuan:
            if s > i:
                break
            if keping[i - s] + 1 < keping[i]:
                keping[i], terakhir[i] = keping[i - s] + 1, s
    if keping[n] == TAK_TERHINGGA:
        return None
    hasil = {}
    while n:
        hasil[terakhir[n] * fpb] = hasil.get(terakhir[n] * fpb, 0) + 1
        n -= terakhir[n]
    return dict(sorted(hasil.items(), reverse=True))


def serakah(jumlah, pecahan):
    """Ambil pecahan terbesar dulu. Benar untuk pecahan Rupiah, tapi tidak untuk sembarang pecahan."""
    hasil = {}
    for p in sorted(pecahan, reverse=True):
        if jumlah >= p:
            hasil[p], jumlah = divmod(jumlah, p)
    return hasil if jumlah == 0 else None


if __name__ == "__main__":
    rupiah = [100, 200, 500, 1000, 2000, 5000, 10000, 20000, 50000, 100000]
    print("Rp87.300:", pecahan_minimal(87_300, rupiah))
    print("Rp0:", pecahan_minimal(0, rupiah))
    print("Rp150 dengan pecahan Rupiah:", pecahan_minimal(150, rupiah))
    print("6 dengan [1, 3, 4]  serakah:", serakah(6, [1, 3, 4]), " minimal:", pecahan_minimal(6, [1, 3, 4]))
    print("7 dengan [2, 4]:", pecahan_minimal(7, [2, 4]))
    print("Rp9.999.900:", sum(pecahan_minimal(9_999_900, rupiah).values()), "keping")
    try:
        pecahan_minimal(1000.5, rupiah)
    except TypeError as e:
        print("TypeError:", e)
