Penyebabnya adalah **argumen default yang bisa diubah (mutable)**, salah satu jebakan Python yang paling sering muncul.

**Penyebab**
Nilai default `item=[]` dibuat **satu kali**, saat Python membaca baris `def`, bukan setiap kali `Pesanan(...)` dipanggil. Semua pesanan yang dibuat tanpa argumen `item` memakai list yang sama:

1. `Pesanan("Andi")`: `self.item` menunjuk ke list default, lalu kopi susu ditambahkan ke list itu.
2. `Pesanan("Budi")`: `self.item` menunjuk ke **list yang sama**, yang sudah berisi kopi susu. Teh tarik ditambahkan ke sana.
3. Andi dan Budi sama-sama melihat dua item.

Ada dua masalah lain dengan pola yang sama di file ini:
- `catatan={}` akan bocor dengan cara yang sama begitu ada kode yang mengisi catatan.
- `tanggal=date.today()` dihitung sekali saat program mulai. Kalau kasir berjalan melewati tengah malam, pesanan hari berikutnya tetap tercatat dengan tanggal kemarin.

**Perbaikan**
Gunakan `None` sebagai default, lalu buat objek baru di dalam fungsi. Saya juga menyalin list yang diberikan pemanggil (`list(item)`), supaya `tambah()` tidak diam-diam mengubah list milik pemanggil:

```
<<<<<<< SEARCH
    def __init__(self, pelanggan, item=[], catatan={}):
        self.pelanggan = pelanggan
        self.item = item
        self.catatan = catatan
=======
    def __init__(self, pelanggan, item=None, catatan=None):
        self.pelanggan = pelanggan
        # Default None lalu buat objek baru di sini: default [] atau {} dibuat sekali dan dipakai bersama.
        self.item = list(item) if item is not None else []
        self.catatan = dict(catatan) if catatan is not None else {}
>>>>>>> REPLACE
```

```
<<<<<<< SEARCH
def pesanan_hari_ini(pelanggan, tanggal=date.today()):
    return f"{pelanggan} - {tanggal:%d/%m/%Y}"
=======
def pesanan_hari_ini(pelanggan, tanggal=None):
    tanggal = tanggal or date.today()  # dihitung saat dipanggil, bukan saat program dimulai
    return f"{pelanggan} - {tanggal:%d/%m/%Y}"
>>>>>>> REPLACE
```

Untuk memastikan list milik pemanggil tidak ikut berubah, saya tambahkan satu kasus di bagian bawah:

```
<<<<<<< SEARCH
    print(b.pelanggan, b.item, b.total())
=======
    print(b.pelanggan, b.item, b.total())

    menu = [("Roti bakar", 12000)]
    c = Pesanan("Citra", menu)
    c.tambah("Es jeruk", 8000)
    print(c.pelanggan, c.item, c.total(), "| daftar asli tetap:", menu)
>>>>>>> REPLACE
```

**Cara cek**

```
{{run python pesanan.py}}
```

Sekarang setiap pesanan punya list sendiri. Supaya kesalahan seperti ini tertangkap sebelum dijalankan, pasang linter `ruff` dan aktifkan aturan `B006` dan `B008`. Kedua aturan itu menandai argumen default yang mutable dan pemanggilan fungsi di argumen default. Kalau nanti `Pesanan` diubah menjadi `@dataclass`, pakai `field(default_factory=list)`. Dataclass akan menolak default `[]` dengan error.
