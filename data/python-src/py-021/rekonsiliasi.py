BATAS_FAKTUR = 40  # 2 × 2^20 jumlah subset: beberapa detik. Di atas ini waktu dan memori naik dua kali lipat per faktur.


def _semua_jumlah(item):
    """Pasangan (jumlah, mask) untuk semua subset item, dibangun dengan penggandaan: 2^len(item) pasangan."""
    jumlah, mask = [0], [0]
    for i, (_, nominal) in enumerate(item):
        bit = 1 << i
        jumlah += [s + nominal for s in jumlah]
        mask += [m | bit for m in mask]
    return jumlah, mask


def cocokkan_transfer(transfer, faktur, maks=2):
    """Kombinasi faktur yang jumlahnya tepat sama dengan transfer, paling banyak `maks` kombinasi.

    faktur: {nomor_faktur: nominal}; nota retur boleh bernilai negatif. Hasilnya list tuple nomor faktur:
      []                tidak ada yang cocok
      [satu kombinasi]  cocok pasti, aman dicatat otomatis
      2 kombinasi       ambigu: jangan dicatat otomatis, serahkan ke petugas
    """
    if isinstance(transfer, bool) or not isinstance(transfer, int) or transfer <= 0:
        raise ValueError(f"transfer harus bilangan bulat rupiah > 0, bukan {transfer!r}")
    if maks < 1:
        raise ValueError(f"maks minimal 1, bukan {maks}")
    if len(faktur) > BATAS_FAKTUR:
        raise ValueError(f"{len(faktur)} faktur; batasnya {BATAS_FAKTUR}. Saring dulu per pelanggan atau per periode")
    for nomor, nominal in faktur.items():
        if isinstance(nominal, bool) or not isinstance(nominal, int) or nominal == 0:
            raise ValueError(f"nominal {nomor} harus bilangan bulat rupiah selain 0, bukan {nominal!r}")

    item = sorted(faktur.items())
    kiri, kanan = item[:len(item) // 2], item[len(item) // 2:]
    jumlah_kiri, mask_kiri = _semua_jumlah(kiri)
    peta = {}  # jumlah -> paling banyak `maks` mask kiri dengan jumlah itu
    for s, m in zip(jumlah_kiri, mask_kiri):
        daftar = peta.setdefault(s, [])
        if len(daftar) < maks:
            daftar.append(m)
    del jumlah_kiri, mask_kiri

    hasil = []
    for s, m_kanan in zip(*_semua_jumlah(kanan)):
        for m_kiri in peta.get(transfer - s, ()):
            # Subset kosong berjumlah 0, sedangkan transfer > 0, jadi tidak mungkin ikut terpilih.
            hasil.append(tuple(sorted([kiri[i][0] for i in range(len(kiri)) if m_kiri >> i & 1] +
                                      [kanan[i][0] for i in range(len(kanan)) if m_kanan >> i & 1])))
            if len(hasil) == maks:
                return sorted(hasil)
    return sorted(hasil)


def _cocokkan_lambat(transfer, faktur):
    """Semua kombinasi lewat 2^n subset, hanya untuk cek silang pada n kecil."""
    from itertools import combinations

    nomor = sorted(faktur)
    return {k for r in range(1, len(nomor) + 1) for k in combinations(nomor, r)
            if sum(faktur[x] for x in k) == transfer}


if __name__ == "__main__":
    import random
    import time

    faktur = {"INV-0412": 1_250_000, "INV-0415": 3_480_000, "INV-0419": 725_000,
              "INV-0423": 3_480_000, "RET-0007": -180_000}
    print("transfer 4.205.000:", cocokkan_transfer(4_205_000, faktur))
    print("transfer 1.070.000:", cocokkan_transfer(1_070_000, faktur))
    print("transfer 1.795.000:", cocokkan_transfer(1_795_000, faktur))
    print("transfer 9.999.999:", cocokkan_transfer(9_999_999, faktur))

    acak = random.Random(21)
    for _ in range(3000):
        n = acak.randint(0, 12)
        f = {f"F{i:02d}": acak.choice([-1, 1, 1, 1]) * acak.randint(1, 30) * 5_000 for i in range(n)}
        t = acak.randint(1, 60) * 5_000
        semua = _cocokkan_lambat(t, f)
        hasil = cocokkan_transfer(t, f)
        assert len(hasil) == min(len(semua), 2) and set(hasil) <= semua, (t, f, hasil, semua)
    print("cek silang 3000 kasus acak dengan cara lambat: cocok")

    besar = {f"INV-{i:04d}": acak.randint(100, 9_000) * 1_000 for i in range(40)}
    mulai = time.perf_counter()
    kosong = cocokkan_transfer(12_345_678, besar)  # bukan kelipatan 1.000: tidak ada yang cocok, semua subset diperiksa
    print(f"40 faktur, kasus terberat: {kosong}, selesai di bawah 10 detik: {time.perf_counter() - mulai < 10}")
    pilihan = acak.sample(sorted(besar), 9)
    print("40 faktur, transfer = jumlah 9 faktur:", len(cocokkan_transfer(sum(besar[x] for x in pilihan), besar)),
          "kombinasi")

    for salah in [(4_205_000.0, faktur), (0, faktur), (100, {"X": 0}), (100, besar | {"INV-9999": 1})]:
        try:
            cocokkan_transfer(*salah)
        except ValueError as e:
            print("ValueError:", e)
