from datetime import date


class Pesanan:
    def __init__(self, pelanggan, item=None, catatan=None):
        self.pelanggan = pelanggan
        # Default None lalu buat objek baru di sini: default [] atau {} dibuat sekali dan dipakai bersama.
        self.item = list(item) if item is not None else []
        self.catatan = dict(catatan) if catatan is not None else {}

    def tambah(self, nama, harga):
        self.item.append((nama, harga))

    def total(self):
        return sum(harga for _, harga in self.item)


def pesanan_hari_ini(pelanggan, tanggal=None):
    tanggal = tanggal or date.today()  # dihitung saat dipanggil, bukan saat program dimulai
    return f"{pelanggan} - {tanggal:%d/%m/%Y}"


if __name__ == "__main__":
    a = Pesanan("Andi")
    a.tambah("Kopi susu", 18000)
    b = Pesanan("Budi")
    b.tambah("Teh tarik", 15000)
    print(a.pelanggan, a.item, a.total())
    print(b.pelanggan, b.item, b.total())

    menu = [("Roti bakar", 12000)]
    c = Pesanan("Citra", menu)
    c.tambah("Es jeruk", 8000)
    print(c.pelanggan, c.item, c.total(), "| daftar asli tetap:", menu)
