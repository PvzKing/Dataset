# tiruan eval_humaneval/indopy_eval/web_eval: struktur folder dan file hasil sama dengan aslinya
import argparse, json, os, sys
from pathlib import Path
script = Path(sys.argv[0]).name
p = argparse.ArgumentParser()
p.add_argument("--adapter"); p.add_argument("--results"); p.add_argument("--no-load-in-4bit", action="store_true")
p.add_argument("--batch-size", type=int); p.add_argument("--dataset", default="humaneval"); p.add_argument("--split")
p.add_argument("--max-seq-len"); p.add_argument("--max-new-tokens")
a = p.parse_args()
folder = Path(a.adapter).parent
tag = f"{folder.parent.name}-{folder.name}"
epoch = int(tag.rsplit("-", 1)[1])
if os.environ.get("SIM_OOM") and a.batch_size > 4 and script == "web_eval.py":
    print("torch.OutOfMemoryError: CUDA out of memory"); sys.exit(1)
res = Path(a.results)
if script == "eval_humaneval.py":
    keys = [f"{a.dataset}_pass@1", f"{a.dataset}+_pass@1"]; names = ["MBPP", "MBPP+"] if a.dataset == "mbpp" else ["HumanEval", "HumanEval+"]
elif script == "indopy_eval.py":
    keys = ["indopy_pass@1"]; names = [f"IndoPy-{a.split}"]
else:
    keys = ["web_lolos"]; names = ["Web-eval"]
bonus = {int(k): float(v) for k, v in (x.split(":") for x in os.environ.get("SIM_BONUS", "").split(",") if x)}
for t, base in ((tag, 0.70 + bonus.get(epoch, 0)), ("model-dasar", 0.65)):
    d = res / t; d.mkdir(parents=True, exist_ok=True)
    r = {"tag": t, "soal": 10, **{k: round(base, 4) for k in keys}}
    if script == "web_eval.py": r.update(format_cek_kebutuhan=9, gagal={"web/jam-dunia": "zona waktu salah"})
    (d / "ringkasan.json").write_text(json.dumps(r))
(res / f"perbandingan-{tag}.json").write_text(json.dumps({"adapter": tag, **{n: {"selisih_soal": 2, "selisih_poin_persen": 5.0, "p_mcnemar": 0.25} for n in names}}))
print(f"[sim] {script} {tag} batch {a.batch_size} selesai")
