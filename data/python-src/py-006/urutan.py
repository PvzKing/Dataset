import heapq


class DependensiMelingkar(ValueError):
    def __init__(self, siklus):
        self.siklus = siklus
        super().__init__("dependensi melingkar: " + " -> ".join(siklus))


def urutan_instalasi(dependensi):
    """Urutan topologis (algoritma Kahn). Di antara paket yang sama-sama siap, urutan alfabetis agar hasilnya tetap."""
    semua = set(dependensi) | {d for deps in dependensi.values() for d in deps}
    sisa_dep = {p: set(dependensi.get(p, ())) for p in semua}   # set: dependensi ganda dihitung sekali
    pemakai = {p: [] for p in semua}
    for paket, deps in sisa_dep.items():
        for d in deps:
            pemakai[d].append(paket)
    siap = [p for p in semua if not sisa_dep[p]]
    heapq.heapify(siap)
    urutan = []
    while siap:
        paket = heapq.heappop(siap)
        urutan.append(paket)
        for p in pemakai[paket]:
            sisa_dep[p].discard(paket)
            if not sisa_dep[p]:
                heapq.heappush(siap, p)
    if len(urutan) < len(semua):
        raise DependensiMelingkar(_cari_siklus({p: d for p, d in sisa_dep.items() if d}))
    return urutan


def _cari_siklus(tersisa):
    """Telusuri dependensi yang belum terpenuhi sampai bertemu paket yang sudah dilewati."""
    jalur, posisi = [], {}
    paket = min(tersisa)
    while paket not in posisi:
        posisi[paket] = len(jalur)
        jalur.append(paket)
        paket = min(tersisa[paket])  # setiap paket yang tersisa pasti masih punya dependensi yang tersisa
    return jalur[posisi[paket]:] + [paket]


if __name__ == "__main__":
    print(urutan_instalasi({"app": ["web", "db"], "web": ["util"], "db": ["util"]}))
    print(urutan_instalasi({"b": [], "a": [], "c": ["a", "a"]}))
    print(urutan_instalasi({}))
    for data in [{"a": ["b"], "b": ["c"], "c": ["a"], "d": ["a"]}, {"x": ["x"]}]:
        try:
            urutan_instalasi(data)
        except DependensiMelingkar as e:
            print(e, "| siklus:", e.siklus)
