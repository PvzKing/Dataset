"""Uji pemeriksaan Web-eval dari dua arah, tanpa model.

1. Setiap website rujukan di web/referensi/ harus LOLOS semua pemeriksaan.
2. Setiap website rujukan yang sengaja dirusak dengan satu bug realistis harus DITOLAK.

Jalankan setelah mengubah pemeriksaan di web_eval.py atau website rujukannya:
    pip install playwright && playwright install chromium
    python eval-suite/web/uji_pemeriksa.py
"""
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import web_eval  # noqa: E402

# Satu bug per website: (teks asli, pengganti). Setiap bug harus membuat pemeriksaan fitur atau error gagal.
MUTASI = {
    "konversi-satuan": ("c * 9 / 5 + 32", "c * 9 / 5 + 30"),
    "pengeluaran": ("try { localStorage.setItem(KUNCI, JSON.stringify(data)); }", "try { }"),
    "galeri": ("btn.addEventListener('click', () => buka(i));", ""),
    "stopwatch": ("    tersimpan = 0;\n    totalPutaranSebelumnya = 0;", "    totalPutaranSebelumnya = 0;"),
    "jam-dunia": ("timeZone: z.tz, hourCycle", "hourCycle"),
    "seminar": ("!/^[^\\s@]+@[^\\s@]+\\.[^\\s@]{2,}$/.test(v.trim())", "false"),
    "faq": ("tidakAda.hidden = tampil > 0;", "tidakAda.hidden = true;"),
    "memori": ("el.addEventListener('click', () => klik(k));", ""),
    "tabel": ("const PER_HALAMAN = 10;", "const PER_HALAMAN = 30;"),
    "tanggal": ("const selisih = Math.round((b - a) / HARI_MS);", "const selisih = Math.round((b - a) / HARI_MS) + 1;"),
}


def main():
    from playwright.sync_api import sync_playwright

    assert set(MUTASI) == set(web_eval.PROMPTS), "setiap prompt Web-eval harus punya satu mutasi"
    gagal = []
    with sync_playwright() as p, TemporaryDirectory() as tmp:
        browser = p.chromium.launch()
        for site, (asli, rusak) in MUTASI.items():
            path = HERE / "referensi" / f"{site}.html"
            r = web_eval.judge_site(browser, path, site)
            ok = r["tanpa_error"] and r["responsif"] and r["fitur"]
            print(f"{site:<16} rujukan: {'lolos' if ok else 'GAGAL'} {r['alasan'] or r.get('error', '')}")
            if not ok:
                gagal.append(f"rujukan {site}")
            html = path.read_text()
            if html.count(asli) != 1:
                gagal.append(f"mutasi {site}: teks asli tidak ditemukan tepat sekali")
                continue
            rusak_path = Path(tmp) / f"{site}.html"
            rusak_path.write_text(html.replace(asli, rusak))
            r = web_eval.judge_site(browser, rusak_path, site)
            ditolak = not (r["tanpa_error"] and r["responsif"] and r["fitur"])
            print(f"{'':<16} rusak  : {'ditolak' if ditolak else 'LOLOS (pemeriksaan terlalu longgar)'} "
                  f"{r['alasan'] or r.get('error', '')}")
            if not ditolak:
                gagal.append(f"mutasi {site}")
        browser.close()
    if gagal:
        sys.exit("gagal: " + ", ".join(gagal))
    print(f"OK: {len(MUTASI)} website rujukan lolos dan {len(MUTASI)} versi rusaknya ditolak")


if __name__ == "__main__":
    main()
