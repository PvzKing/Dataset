"""Buku tamu: Flask + SQLite, halaman HTML dan API JSON.

Pemakaian:
    pip install flask
    python app.py            # server pengembangan di http://127.0.0.1:5000
    python app.py --tes
"""
import sqlite3
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, g, jsonify, request

BATAS = {"nama": 60, "pesan": 500}

HALAMAN = """<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Buku Tamu</title>
<style>
  body { font-family: system-ui, sans-serif; max-width: 640px; margin: 0 auto; padding: 16px; color: #1f2937; }
  form { display: grid; gap: 8px; margin-bottom: 24px; }
  input, textarea, button { font: inherit; padding: 10px; border: 1px solid #cbd5e1; border-radius: 8px; }
  button { background: #0f766e; color: #fff; border: 0; cursor: pointer; }
  .galat { color: #b91c1c; min-height: 1.2em; margin: 0; }
  ul { list-style: none; padding: 0; }
  li { border-bottom: 1px solid #e5e7eb; padding: 10px 0; overflow-wrap: anywhere; }
  small { color: #6b7280; }
</style>
</head>
<body>
<h1>Buku Tamu</h1>
<form id="form">
  <label>Nama <input name="nama" maxlength="60" required></label>
  <label>Pesan <textarea name="pesan" maxlength="500" rows="3" required></textarea></label>
  <p class="galat" id="galat" role="alert"></p>
  <button>Kirim</button>
</form>
<ul id="daftar"></ul>
<script>
  const daftar = document.getElementById('daftar');
  const waktu = new Intl.DateTimeFormat('id-ID', { dateStyle: 'medium', timeStyle: 'short', timeZone: 'Asia/Jakarta' });

  function tampilkan(item) {
    // textContent, bukan innerHTML: isi pesan selalu tampil sebagai teks, tidak pernah dijalankan sebagai HTML.
    const li = document.createElement('li');
    const nama = document.createElement('strong');
    nama.textContent = item.nama;
    const kapan = document.createElement('small');
    kapan.textContent = ' · ' + waktu.format(new Date(item.dibuat)) + ' WIB';
    const isi = document.createElement('p');
    isi.textContent = item.pesan;
    li.append(nama, kapan, isi);
    return li;
  }

  async function muat() {
    const r = await fetch('/api/pesan');
    daftar.replaceChildren(...(await r.json()).map(tampilkan));
  }

  document.getElementById('form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const data = Object.fromEntries(new FormData(e.target));
    const r = await fetch('/api/pesan', { method: 'POST', headers: { 'Content-Type': 'application/json' },
                                         body: JSON.stringify(data) });
    const hasil = await r.json();
    document.getElementById('galat').textContent = r.ok ? '' : Object.values(hasil.galat).join(' ');
    if (r.ok) { e.target.reset(); muat(); }
  });
  muat();
</script>
</body>
</html>"""


def create_app(db_path):
    app = Flask(__name__)

    def db():
        if "db" not in g:
            g.db = sqlite3.connect(db_path)
            g.db.row_factory = sqlite3.Row
        return g.db

    @app.teardown_appcontext
    def tutup(_):
        if (conn := g.pop("db", None)) is not None:
            conn.close()

    with app.app_context():
        db().execute("CREATE TABLE IF NOT EXISTS pesan (id INTEGER PRIMARY KEY, nama TEXT NOT NULL, "
                     "pesan TEXT NOT NULL, dibuat TEXT NOT NULL)")
        db().commit()

    @app.get("/")
    def halaman():
        return HALAMAN

    @app.get("/api/pesan")
    def daftar():
        limit = min(max(request.args.get("limit", 20, type=int), 1), 100)
        rows = db().execute("SELECT id, nama, pesan, dibuat FROM pesan ORDER BY id DESC LIMIT ?", (limit,))
        return jsonify([dict(r) for r in rows])

    @app.post("/api/pesan")
    def kirim():
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return jsonify(galat={"body": "kirim JSON berisi nama dan pesan"}), 400
        bersih, galat = {}, {}
        for kolom, batas in BATAS.items():
            nilai = data.get(kolom)
            nilai = nilai.strip() if isinstance(nilai, str) else ""
            if not nilai:
                galat[kolom] = f"{kolom} wajib diisi."
            elif len(nilai) > batas:
                galat[kolom] = f"{kolom} maksimal {batas} karakter."
            bersih[kolom] = nilai
        if galat:
            return jsonify(galat=galat), 400
        dibuat = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with db():
            cur = db().execute("INSERT INTO pesan (nama, pesan, dibuat) VALUES (?, ?, ?)",
                               (bersih["nama"], bersih["pesan"], dibuat))
        return jsonify(id=cur.lastrowid, dibuat=dibuat, **bersih), 201

    return app


class Tes(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.client = create_app(Path(self.tmp.name) / "tamu.db").test_client()

    def tearDown(self):
        self.tmp.cleanup()

    def kirim(self, **data):
        return self.client.post("/api/pesan", json=data)

    def test_kirim_dan_urutan_terbaru(self):
        self.assertEqual(self.kirim(nama="Ani", pesan="Halo").status_code, 201)
        self.kirim(nama=" Budi ", pesan=" Salam kenal ")
        isi = self.client.get("/api/pesan").get_json()
        self.assertEqual([(p["nama"], p["pesan"]) for p in isi], [("Budi", "Salam kenal"), ("Ani", "Halo")])

    def test_validasi(self):
        for data, kolom in [({"nama": "", "pesan": "x"}, "nama"), ({"nama": "A", "pesan": "   "}, "pesan"),
                            ({"nama": "A" * 61, "pesan": "x"}, "nama"), ({"nama": "A", "pesan": 123}, "pesan")]:
            with self.subTest(data=data):
                r = self.kirim(**data)
                self.assertEqual(r.status_code, 400)
                self.assertIn(kolom, r.get_json()["galat"])
        r = self.client.post("/api/pesan", data="nama=A&pesan=B")
        self.assertEqual(r.status_code, 400)

    def test_xss_tetap_teks(self):
        serangan = '<img src=x onerror="alert(1)">'
        self.kirim(nama="Iseng", pesan=serangan)
        self.assertEqual(self.client.get("/api/pesan").get_json()[0]["pesan"], serangan)  # data disimpan apa adanya
        halaman = self.client.get("/").get_data(as_text=True)
        # dan halaman tidak pernah memasukkannya sebagai HTML, hanya lewat textContent
        self.assertNotRegex(halaman, r"\.innerHTML\s*=|insertAdjacentHTML|document\.write")
        self.assertIn("isi.textContent = item.pesan", halaman)

    def test_batas_limit(self):
        for i in range(5):
            self.kirim(nama="A", pesan=str(i))
        self.assertEqual(len(self.client.get("/api/pesan?limit=2").get_json()), 2)
        self.assertEqual(len(self.client.get("/api/pesan?limit=-5").get_json()), 1)
        self.assertEqual(len(self.client.get("/api/pesan?limit=abc").get_json()), 5)


if __name__ == "__main__":
    if sys.argv[1:] == ["--tes"]:
        unittest.main(argv=sys.argv[:1])
    create_app("tamu.db").run(debug=False)
