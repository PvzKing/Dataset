from datetime import date


class Pesanan:
    def __init__(self, pelanggan, item=[], catatan={}):
        self.pelanggan = pelanggan
        self.item = item
        self.catatan = catatan

    def tambah(self, nama, harga):
        self.item.append((nama, harga))

    def total(self):
        return sum(harga for _, harga in self.item)


def pesanan_hari_ini(pelanggan, tanggal=date.today()):
    return f"{pelanggan} - {tanggal:%d/%m/%Y}"


if __name__ == "__main__":
    a = Pesanan("Andi")
    a.tambah("Kopi susu", 18000)
    b = Pesanan("Budi")
    b.tambah("Teh tarik", 15000)
    print(a.pelanggan, a.item, a.total())
    print(b.pelanggan, b.item, b.total())
