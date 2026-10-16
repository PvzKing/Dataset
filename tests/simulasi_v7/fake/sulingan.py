# tiruan scripts/sulingan.py: kandidat dan ringkasan dengan struktur yang sama, tanpa model dan tanpa Chromium
import argparse, json, os, sys
from pathlib import Path
p = argparse.ArgumentParser()
p.add_argument("langkah"); p.add_argument("--out"); p.add_argument("--k", type=int); p.add_argument("--batch", type=int)
p.add_argument("--max-seq-len"); p.add_argument("--hasil"); p.add_argument("--maks-python", type=int)
a = p.parse_args()
out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
repo = Path(__file__).resolve().parent.parent
if a.langkah in ("python", "web"):
    if os.environ.get("SIM_OOM_SUL") and a.langkah == "web" and a.batch > 1:
        print("torch.OutOfMemoryError: CUDA out of memory"); sys.exit(1)
    n = 589 if a.langkah == "python" else 40
    f = out / f"kandidat-{a.langkah}.jsonl"
    sudah = sum(1 for l in open(f) if l.strip()) if f.is_file() else 0
    with open(f, "a") as w:
        for i in range(sudah, n):
            w.write(json.dumps({"id": f"{a.langkah}-{i}", "kandidat": [{"lolos": i % 4 != 0}] * a.k}) + "\n")
    print(f"[sim] sulingan {a.langkah} k={a.k} batch {a.batch}: {n - sudah} soal dikerjakan")
else:
    own = [l for l in open(repo / "data" / "train.jsonl") if l.strip()]
    web = [json.dumps({"id": f"sul-web-{i}", "messages": []}) + "\n" for i in range(30)]
    py = [json.dumps({"id": f"sul-py-{i}", "messages": []}) + "\n" for i in range(a.maks_python)]
    Path(a.hasil).write_text("".join(own + web + py))
    r = {"own": len(own), "sulingan_python": {"soal": 589, "kandidat": 2356, "kandidat_lolos": 1700, "soal_punya_jawaban_lolos": 520, "dipakai": len(py)},
         "sulingan_web": {"soal": 40, "kandidat": 80, "kandidat_lolos": 41, "soal_punya_jawaban_lolos": 30, "dipakai": len(web)},
         "total": len(own) + len(web) + len(py), "dibuang_kontaminasi": ["sul-py-mbpp-928: Mbpp/427"], "hasil": a.hasil}
    (out / "ringkasan-sulingan.json").write_text(json.dumps(r))
    print(f"[sim] gabung: {r['total']} sampel")
