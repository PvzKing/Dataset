"""Cari file duplikat (isi identik) di sebuah folder. Hanya melapor, tidak menghapus apa pun.

Pemakaian:
    python duplikat.py FOLDER [--min-ukuran BYTE]
    python duplikat.py --tes
"""
import argparse
import hashlib
import os
import sys
import tempfile
import unittest
from collections import defaultdict
from pathlib import Path

BLOK = 1024 * 1024
AWAL = 64 * 1024


def sidik(path, batas=None):
    """SHA-256 isi file, dibaca per blok supaya file video besar tidak dimuat sekaligus ke memori."""
    h, dibaca = hashlib.sha256(), 0
    with open(path, "rb") as f:
        while batas is None or dibaca < batas:
            blok = f.read(BLOK if batas is None else min(BLOK, batas - dibaca))
            if not blok:
                break
            h.update(blok)
            dibaca += len(blok)
    return h.hexdigest()


def kelompokkan(paths, kunci, peringatan):
    """Kelompokkan path berdasarkan kunci(path); buang kelompok berisi satu file dan file yang gagal dibaca."""
    kelompok = defaultdict(list)
    for p in paths:
        try:
            kelompok[kunci(p)].append(p)
        except OSError as e:  # izin ditolak, atau file terhapus di tengah pemindaian
            peringatan.append(f"dilewati {p}: {e.strerror}")
    return [g for g in kelompok.values() if len(g) > 1]


def cari_duplikat(folder, min_ukuran=1):
    """Kembalikan (daftar kelompok duplikat, peringatan). Setiap kelompok berisi path yang isinya identik."""
    per_ukuran, inode_dilihat, peringatan = defaultdict(list), set(), []
    for akar, subfolder, files in os.walk(folder, onerror=lambda e: peringatan.append(f"dilewati {e.filename}: {e.strerror}")):
        subfolder.sort()
        for nama in sorted(files):
            p = Path(akar, nama)
            try:
                st = p.lstat()
            except OSError as e:
                peringatan.append(f"dilewati {p}: {e.strerror}")
                continue
            if not p.is_file() or p.is_symlink() or st.st_size < min_ukuran:
                continue
            if (st.st_dev, st.st_ino) in inode_dilihat:
                continue  # hard link ke file yang sama: bukan salinan, menghapusnya tidak menghemat ruang
            inode_dilihat.add((st.st_dev, st.st_ino))
            per_ukuran[st.st_size].append(p)
    # Tiga tahap dari yang paling murah: ukuran, 64 KB pertama, lalu seluruh isi.
    hasil = []
    for kandidat in per_ukuran.values():
        if len(kandidat) < 2:
            continue
        for g in kelompokkan(kandidat, lambda p: sidik(p, AWAL), peringatan):
            hasil += kelompokkan(g, sidik, peringatan)
    hasil = [sorted(g) for g in hasil]
    hasil.sort(key=lambda g: (-g[0].stat().st_size * (len(g) - 1), g[0]))
    return hasil, peringatan


def ukuran_terbaca(n):
    for satuan in ("B", "KB", "MB", "GB"):
        if n < 1024 or satuan == "GB":
            return f"{n:.0f} {satuan}" if satuan == "B" else f"{n:.1f} {satuan}"
        n /= 1024


class Tes(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def tulis(self, nama, isi):
        p = self.root / nama
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(isi)
        return p

    def test_duplikat_di_subfolder(self):
        a = self.tulis("a/x.bin", b"sama" * 1000)
        b = self.tulis("b/c/y.bin", b"sama" * 1000)
        self.tulis("lain.bin", b"beda" * 1000)  # ukuran sama, isi beda
        self.assertEqual(cari_duplikat(self.root)[0], [[a, b]])

    def test_awal_sama_akhir_beda(self):
        # 64 KB pertama identik: tahap kedua lolos, tahap ketiga harus memisahkannya
        self.tulis("p.bin", b"\0" * AWAL + b"1")
        self.tulis("q.bin", b"\0" * AWAL + b"2")
        self.assertEqual(cari_duplikat(self.root)[0], [])

    def test_hard_link_dan_file_kosong(self):
        a = self.tulis("a.txt", b"isi")
        os.link(a, self.root / "a-link.txt")
        self.tulis("k1.txt", b"")
        self.tulis("k2.txt", b"")
        self.assertEqual(cari_duplikat(self.root)[0], [])

    def test_symlink_diabaikan(self):
        a = self.tulis("a.txt", b"isi")
        (self.root / "tautan.txt").symlink_to(a)
        self.assertEqual(cari_duplikat(self.root)[0], [])

    def test_urutan_menurut_ruang_terbuang(self):
        kecil = [self.tulis(f"k{i}.txt", b"k") for i in range(3)]
        besar = [self.tulis(f"b{i}.txt", b"b" * 100) for i in range(2)]
        self.assertEqual(cari_duplikat(self.root)[0], [besar, kecil])


def main():
    if sys.argv[1:] == ["--tes"]:
        unittest.main(argv=sys.argv[:1])
    parser = argparse.ArgumentParser(description="Cari file duplikat. Tidak menghapus apa pun.")
    parser.add_argument("folder", type=Path)
    parser.add_argument("--min-ukuran", type=int, default=1, help="abaikan file lebih kecil dari ini (byte)")
    args = parser.parse_args()
    if not args.folder.is_dir():
        sys.exit(f"bukan folder: {args.folder}")
    kelompok, peringatan = cari_duplikat(args.folder, args.min_ukuran)
    hemat = 0
    for i, g in enumerate(kelompok, 1):
        ukuran = g[0].stat().st_size
        hemat += ukuran * (len(g) - 1)
        print(f"[{i}] {len(g)} file × {ukuran_terbaca(ukuran)}")
        for p in g:
            print(f"    {p}")
    for w in peringatan:
        print("peringatan:", w, file=sys.stderr)
    print(f"{len(kelompok)} kelompok duplikat; ruang yang bisa dihemat: {ukuran_terbaca(hemat)}")


if __name__ == "__main__":
    main()
