# tiruan train_unsloth.py: "own+evalplus" ada di teks supaya dipilih oleh Sel 1
import argparse, json, os, sys
from pathlib import Path
p = argparse.ArgumentParser()
p.add_argument("command"); p.add_argument("--dataset"); p.add_argument("--name"); p.add_argument("--out"); p.add_argument("--data")
p.add_argument("--no-load-in-4bit", action="store_true"); p.add_argument("--max-seq-len"); p.add_argument("--epochs", type=float)
p.add_argument("--epoch-adapters", action="store_true"); p.add_argument("--max-new-tokens")
p.add_argument("--lr"); p.add_argument("--grad-accum", type=int, default=8); p.add_argument("--save-steps", type=int)
a = p.parse_args()
assert a.dataset == "own+evalplus" and a.save_steps == 50
run = Path(a.out) / f"qwen3.5-4b-{a.name}"; run.mkdir(parents=True, exist_ok=True)
lora = run / f"qwen3.5-4b-{a.name}-lora"
bench = [Path(a.out) / "bench-support" / f for f in ("humaneval.jsonl", "mbppplus.jsonl", "mbpp-sisa.jsonl")]
n = sum(1 for f in [Path(a.data), *bench] for l in open(f) if l.strip())  # salinan bench-support dari Sel 1
data = {"samples": n, "dropped": [], "longest": 6231, "total_steps": -(-n // a.grad_accum) * int(a.epochs)}
def status(**kw): (run / "status.json").write_text(json.dumps(kw))
if a.command == "prepare":
    print(f"data valid: {n} sampel"); status(stage="prepared", data=data)
elif a.command == "train":
    if os.environ.get("SIM_FAIL_TRAIN"): print("CUDA out of memory"); sys.exit(1)
    for e in range(1, int(a.epochs) + 1):
        d = run / f"epoch-{e}" / lora.name; d.mkdir(parents=True, exist_ok=True); (d / "adapter_config.json").write_text(json.dumps({"epoch": e}))
        print(f"adapter epoch {e} disimpan: {d}")
    lora.mkdir(exist_ok=True); (lora / "adapter_config.json").write_text(json.dumps({"epoch": int(a.epochs)}))
    status(stage="done", data=data, result={"train_loss": 0.04, "train_runtime_min": 210.0},
           tests={"bengkel": {"tokens": 5100, "finished": True}, "absensi": {"tokens": 6900, "finished": True}})
elif a.command == "gguf":
    g = run / "gguf"; g.mkdir(exist_ok=True); (g / f"qwen3.5-4b-{a.name}.Q4_K_M.gguf").write_text("x")
    print("dipakai adapter:", json.loads((lora / "adapter_config.json").read_text())); status(stage="done")
elif a.command == "merge":
    m = run / f"qwen3.5-4b-{a.name}-merged-16bit"; m.mkdir(exist_ok=True); (m / "config.json").write_text("{}"); status(stage="done")
