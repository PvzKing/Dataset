"""Papan skor: kumpulkan hasil semua uji untuk satu adapter dan nilai gerbang penerimaan di docs/RENCANA_PYTHON.md.

Script ini tidak memuat model. Ia hanya membaca folder hasil yang ditulis eval_humaneval.py (HumanEval+ dan MBPP+),
indopy_eval.py, dan web_eval.py, lalu mencetak tabel dan status setiap gerbang:

  G1  Python umum tidak turun   HumanEval+ dan MBPP+: tidak turun nyata (McNemar) dan selisih gabungan >= -1,5 poin
  G2  Python yang diajarkan naik IndoPy-test naik nyata dari model dasar (IndoPy-dev ditampilkan sebagai petunjuk)
  G3  Website tidak turun        jumlah website Web-eval yang lolos >= adapter pembanding (v3)

Pemakaian di Colab (setelah semua uji untuk adapter itu selesai):

    %run /content/papan_skor.py --tag v4-pilot-qwen3.5-4b-own-4bit --pembanding v3-qwen3.5-4b-own-4bit

--tag dan --pembanding adalah nama run, yaitu nama subfolder di folder hasil (tercetak di awal setiap uji).
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = "/content/drive/MyDrive/finetune-id" if Path("/content").is_dir() else "."


def mcnemar_p(gained, lost):
    from math import comb

    n, k = gained + lost, min(gained, lost)
    return 1.0 if n == 0 else min(1.0, 2 * sum(comb(n, i) for i in range(k + 1)) / 2 ** n)


def baca(path):
    path = Path(path)
    return json.loads(path.read_text()) if path.is_file() else None


def baca_jsonl(path):
    path = Path(path)
    return [json.loads(x) for x in path.read_text().splitlines() if x.strip()] if path.is_file() else None


def pct(x):
    return f"{x:.1%}" if x is not None else "-"


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--tag", required=True, help="nama run adapter yang dinilai")
    parser.add_argument("--pembanding", help="nama run adapter pembanding untuk Web-eval (biasanya v3)")
    parser.add_argument("--root", default=ROOT, help="folder yang berisi eval-humaneval, eval-mbpp, dst.")
    args, _ = parser.parse_known_args(sys.argv[1:])
    root, tag = Path(args.root), args.tag
    baris, status = [], {}

    # G1: HumanEval+ dan MBPP+
    total_soal, total_selisih, turun_nyata, ada = 0, 0, False, False
    for folder, nama in (("eval-humaneval", "HumanEval+"), ("eval-mbpp", "MBPP+")):
        rep = baca(root / folder / f"perbandingan-{tag}.json")
        if not rep or nama not in rep:
            baris.append((f"G1 {nama}", "-", "-", "-", "-", "belum diuji"))
            continue
        ada = True
        r = rep[nama]
        key = f"{nama.lower()}_pass@1"
        skor = baca(root / folder / tag / "ringkasan.json") or {}
        dasar = baca(root / folder / rep["model_dasar"] / "ringkasan.json") or {}
        total_soal += rep["soal"]
        total_selisih += r["selisih_soal"]
        turun_nyata |= r["selisih_soal"] < 0 and r["p_mcnemar"] < 0.05
        baris.append((f"G1 {nama}", pct(skor.get(key)), pct(dasar.get(key)), f"{r['selisih_soal']:+d} soal",
                      f"{r['p_mcnemar']:.3f}", ""))
    if ada:
        gabungan = total_selisih / total_soal * 100
        lolos = not turun_nyata and gabungan >= -1.5
        status["G1"] = ("LOLOS" if lolos else "GAGAL") + f" (selisih gabungan {gabungan:+.1f} poin"
        status["G1"] += ", ada penurunan nyata)" if turun_nyata else ")"
    else:
        status["G1"] = "BELUM DIUKUR"

    # G2: IndoPy
    for split in ("dev", "test"):
        rep = baca(root / f"eval-indopy-{split}" / f"perbandingan-{tag}.json")
        nama = f"IndoPy-{split}"
        if not rep:
            baris.append((f"G2 {nama}", "-", "-", "-", "-", "belum diuji"))
            continue
        r = rep[nama]
        skor = baca(root / f"eval-indopy-{split}" / tag / "ringkasan.json") or {}
        dasar = baca(root / f"eval-indopy-{split}" / rep["model_dasar"] / "ringkasan.json") or {}
        catatan = "petunjuk saja" if split == "dev" else ""
        baris.append((f"G2 {nama}", pct(skor.get("indopy_pass@1")), pct(dasar.get("indopy_pass@1")),
                      f"{r['selisih_soal']:+d} soal", f"{r['p_mcnemar']:.3f}", catatan))
        if split == "test":
            naik = r["selisih_soal"] > 0 and r["p_mcnemar"] < 0.05
            status["G2"] = "LOLOS" if naik else "GAGAL (belum naik nyata dari model dasar)"
    status.setdefault("G2", "BELUM DIUKUR (jalankan IndoPy-test saat penilaian akhir)")

    # G3: Web-eval dibanding adapter pembanding
    web = baca_jsonl(root / "eval-web" / tag / "hasil.jsonl")
    pembanding = baca_jsonl(root / "eval-web" / args.pembanding / "hasil.jsonl") if args.pembanding else None
    rep = baca(root / "eval-web" / f"perbandingan-{tag}.json")
    if web:
        n, lolos = len(web), sum(r["base"] for r in web)
        dasar = baca(root / "eval-web" / rep["model_dasar"] / "ringkasan.json") if rep else None
        baris.append(("G3 Web-eval vs dasar", f"{lolos}/{n}", f"{round(dasar['web_lolos'] * dasar['soal'])}/{dasar['soal']}"
                      if dasar else "-", f"{rep['Web-eval']['selisih_soal']:+d}" if rep else "-",
                      f"{rep['Web-eval']['p_mcnemar']:.3f}" if rep else "-", "informasi"))
        if pembanding:
            per_id = {r["task_id"]: r["base"] for r in pembanding}
            lolos_p = sum(per_id.values())
            naik = sum(r["base"] and not per_id.get(r["task_id"], False) for r in web)
            turun = sum(not r["base"] and per_id.get(r["task_id"], False) for r in web)
            baris.append((f"G3 Web-eval vs {args.pembanding}"[:30], f"{lolos}/{n}", f"{lolos_p}/{len(per_id)}",
                          f"{lolos - lolos_p:+d}", f"{mcnemar_p(naik, turun):.3f}", ""))
            status["G3"] = ("LOLOS" if lolos >= lolos_p else "GAGAL") + f" ({lolos} vs {lolos_p} website lolos)"
        else:
            status["G3"] = "BELUM DIUKUR (beri --pembanding <run v3> setelah web_eval dijalankan untuk v3)"
        fmt = sum(r.get("format", False) for r in web)
        baris.append(("   format Cek kebutuhan", f"{fmt}/{n}", "", "", "", "tidak menentukan"))
    else:
        baris.append(("G3 Web-eval", "-", "-", "-", "-", "belum diuji"))
        status["G3"] = "BELUM DIUKUR"

    print(f"\n===== Papan skor: {tag} =====")
    print(f"| {'ukuran':<30} | {'adapter':>8} | {'pembanding':>10} | {'selisih':>9} | {'p':>6} | catatan")
    print(f"|{'-' * 32}|{'-' * 10}|{'-' * 12}|{'-' * 11}|{'-' * 8}|---------")
    for nama, a, b, d, p, c in baris:
        print(f"| {nama:<30} | {a:>8} | {b:>10} | {d:>9} | {p:>6} | {c}")
    print("\nGerbang:")
    for g in ("G1", "G2", "G3"):
        print(f"  {g}: {status[g]}")
    print("  G4 (perbaikan bug): belum ada set ujinya; lihat Fase 3 di docs/RENCANA_PYTHON.md")
    keputusan = all(status[g].startswith("LOLOS") for g in ("G1", "G2", "G3"))
    print("\nKeputusan:", "DITERIMA" if keputusan else "BELUM DITERIMA (lihat gerbang yang belum lolos atau belum diukur)")


if __name__ == "__main__":
    main()
