"""Periksa kualitas soal IndoPy tanpa model.

Untuk setiap soal:
  1. solusi rujukan + tes harus lolos;
  2. setiap solusi salah (wrong_solutions, minimal 2) harus gagal: bukti tesnya cukup kuat;
  3. prompt menyebut nama fungsi, dan tes memanggilnya.
Juga diperiksa: jumlah soal (dev 20, test 40), penomoran task_id, nama fungsi unik, dan sebaran tingkat.

    python eval-suite/indopy/cek_soal.py
"""
import json
import re
import subprocess
import sys
import tempfile
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
KUNCI = {"task_id", "prompt", "entry_point", "canonical_solution", "tests", "wrong_solutions", "topik", "tingkat"}


def jalankan(kode, tes):
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "uji.py"
        path.write_text(kode + "\n\n" + tes)
        try:
            r = subprocess.run([sys.executable, "-I", str(path)], cwd=tmp, capture_output=True, text=True, timeout=10)
        except subprocess.TimeoutExpired:
            return False
    return r.returncode == 0


def periksa(soal):
    masalah = []
    if set(soal) != KUNCI:
        masalah.append(f"kunci tidak sesuai: {sorted(set(soal) ^ KUNCI)}")
    ep = soal["entry_point"]
    if ep not in soal["prompt"]:
        masalah.append("prompt tidak menyebut nama fungsi")
    if not re.search(rf"\b{re.escape(ep)}\s*\(", soal["tests"]):
        masalah.append("tes tidak memanggil fungsi")
    if soal["tingkat"] not in ("mudah", "sedang", "sulit"):
        masalah.append(f"tingkat tidak dikenal: {soal['tingkat']}")
    if not jalankan(soal["canonical_solution"], soal["tests"]):
        masalah.append("solusi rujukan gagal")
    if len(soal["wrong_solutions"]) < 2:
        masalah.append("solusi salah kurang dari 2")
    for i, salah in enumerate(soal["wrong_solutions"]):
        if jalankan(salah, soal["tests"]):
            masalah.append(f"solusi salah #{i + 1} lolos tes")
    return soal["task_id"], masalah


def main():
    semua, gagal = {}, []
    for split, jumlah in (("dev", 20), ("test", 40)):
        soal = [json.loads(x) for x in (HERE / f"{split}.jsonl").read_text().splitlines() if x.strip()]
        harap = [f"IndoPy/{split}/{i:02d}" for i in range(1, jumlah + 1)]
        if [s["task_id"] for s in soal] != harap:
            gagal.append(f"{split}: task_id harus {harap[0]} .. {harap[-1]} berurutan")
        semua[split] = soal
        print(f"{split}: {len(soal)} soal, tingkat {dict(Counter(s['tingkat'] for s in soal))}")
    nama = Counter(s["entry_point"] for daftar in semua.values() for s in daftar)
    gagal += [f"nama fungsi dipakai lebih dari sekali: {n}" for n, c in nama.items() if c > 1]
    with ThreadPoolExecutor(max_workers=8) as pool:
        for task_id, masalah in pool.map(periksa, [s for daftar in semua.values() for s in daftar]):
            gagal += [f"{task_id}: {m}" for m in masalah]
    if gagal:
        sys.exit("\n".join(gagal))
    n_salah = sum(len(s["wrong_solutions"]) for daftar in semua.values() for s in daftar)
    print(f"OK: 60 solusi rujukan lolos, {n_salah} solusi salah semuanya ditolak, nama fungsi unik")


if __name__ == "__main__":
    main()
