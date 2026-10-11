"""To-do di terminal dengan penyimpanan JSON yang aman dari kerusakan.

Pemakaian:
    python todo.py [--file FILE] tambah "teks tugas"
    python todo.py [--file FILE] daftar [--semua]
    python todo.py [--file FILE] selesai ID
    python todo.py [--file FILE] hapus ID
    python todo.py --tes
"""
import argparse
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

BAWAAN = Path.home() / ".todo.json"


class DataRusak(Exception):
    pass


def muat(path):
    if not path.exists():
        return {"berikutnya": 1, "tugas": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data.get("tugas"), list):
            raise ValueError("kunci 'tugas' tidak ada")
        return data
    except ValueError as e:  # JSONDecodeError turunan ValueError
        # Jangan pernah menimpa file yang gagal dibaca: isinya mungkin masih bisa diselamatkan.
        raise DataRusak(f"{path} tidak bisa dibaca ({e}); file dibiarkan apa adanya") from e


def simpan(path, data):
    """Tulis ke file sementara di folder yang sama, paksa ke disk, lalu ganti file lama dalam satu langkah."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)  # atomik: pembaca melihat file lama utuh atau file baru utuh
    except BaseException:
        os.unlink(tmp)
        raise
    if hasattr(os, "O_DIRECTORY"):  # Linux/macOS: catat juga penggantian nama itu ke disk
        fd = os.open(path.parent, os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)


def cari(data, id_):
    for t in data["tugas"]:
        if t["id"] == id_:
            return t
    raise KeyError(f"tugas #{id_} tidak ada")


def jalankan(argv, path):
    parser = argparse.ArgumentParser(prog="todo.py")
    sub = parser.add_subparsers(dest="perintah", required=True)
    sub.add_parser("tambah").add_argument("teks")
    sub.add_parser("daftar").add_argument("--semua", action="store_true", help="tampilkan juga yang selesai")
    sub.add_parser("selesai").add_argument("id", type=int)
    sub.add_parser("hapus").add_argument("id", type=int)
    args = parser.parse_args(argv)
    data = muat(path)
    if args.perintah == "daftar":
        tampil = [t for t in data["tugas"] if args.semua or not t["selesai"]]
        for t in tampil:
            print(f"{t['id']:>3}. [{'x' if t['selesai'] else ' '}] {t['teks']}")
        print(f"({len(tampil)} tugas)" if tampil else "(kosong)")
        return
    if args.perintah == "tambah":
        teks = args.teks.strip()
        if not teks:
            raise ValueError("teks tugas tidak boleh kosong")
        # ID tidak dipakai ulang setelah dihapus, supaya "selesai 3" tidak salah sasaran.
        data["tugas"].append({"id": data["berikutnya"], "teks": teks, "selesai": False})
        print(f"ditambahkan #{data['berikutnya']}: {teks}")
        data["berikutnya"] += 1
    elif args.perintah == "selesai":
        cari(data, args.id)["selesai"] = True
        print(f"#{args.id} selesai")
    else:
        data["tugas"].remove(cari(data, args.id))
        print(f"#{args.id} dihapus")
    simpan(path, data)


class Tes(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "tugas.json"

    def tearDown(self):
        self.tmp.cleanup()

    def diam(self, *argv):
        with mock.patch("sys.stdout"):
            jalankan(list(argv), self.path)

    def test_alur_lengkap_dan_id_tidak_dipakai_ulang(self):
        self.diam("tambah", "a")
        self.diam("tambah", "b")
        self.diam("hapus", "2")
        self.diam("tambah", "c")
        self.diam("selesai", "1")
        data = muat(self.path)
        self.assertEqual([(t["id"], t["teks"], t["selesai"]) for t in data["tugas"]], [(1, "a", True), (3, "c", False)])

    def test_mati_saat_menyimpan_tidak_merusak_file(self):
        self.diam("tambah", "data penting")
        before = self.path.read_bytes()
        with mock.patch("json.dump", side_effect=KeyboardInterrupt), self.assertRaises(KeyboardInterrupt):
            self.diam("tambah", "tidak jadi")
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(list(self.path.parent.iterdir()), [self.path])  # tidak ada file sementara tertinggal

    def test_file_rusak_tidak_ditimpa(self):
        self.path.write_text('{"tugas": [', encoding="utf-8")
        with self.assertRaises(DataRusak):
            self.diam("tambah", "x")
        self.assertEqual(self.path.read_text(encoding="utf-8"), '{"tugas": [')

    def test_input_salah(self):
        with self.assertRaises(ValueError):
            self.diam("tambah", "   ")
        with self.assertRaises(KeyError):
            self.diam("selesai", "7")


def main():
    if sys.argv[1:] == ["--tes"]:
        unittest.main(argv=sys.argv[:1])
    argv, path = sys.argv[1:], BAWAAN
    if argv[:1] == ["--file"] and len(argv) > 1:
        path, argv = Path(argv[1]), argv[2:]
    try:
        jalankan(argv, path)
    except (DataRusak, ValueError) as e:
        sys.exit(f"error: {e}")
    except KeyError as e:
        sys.exit(f"error: {e.args[0]}")


if __name__ == "__main__":
    main()
