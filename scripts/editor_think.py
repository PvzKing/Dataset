"""Editor isi tag <think> untuk sampel dataset own, ditulis sendiri oleh manusia.

Editor ini tidak membuat atau menyarankan isi apa pun. Ia hanya menampilkan prompt dan jawaban setiap sampel,
menyediakan kotak untuk menulis isi <think>, lalu saat Simpan:
  1. menulis teks ke data/think/<id>-<n>.md (sumber yang disimpan di repo);
  2. memasangnya ke data/train.jsonl lewat scripts/think_tags.py, lalu menjalankan scripts/validate.py;
  3. jika "Commit & push" aktif: git commit, lalu push ke GitHub.

Jalankan dari clone repo (laptop atau Colab):
    pip install "gradio>=5"
    python scripts/editor_think.py                    # buka http://127.0.0.1:7861
    python scripts/editor_think.py --share            # link publik sementara (wajib --auth user:sandi)
    python scripts/editor_think.py --branch main      # cabang tujuan push (bawaan: main)

Push memakai token GitHub dari variabel lingkungan GITHUB_TOKEN (fine-grained, izin Contents: Read and write untuk
repo ini). Token tidak disimpan ke git config dan tidak ditampilkan. Tanpa token, push memakai kredensial git yang
sudah ada; jika tidak ada, perubahan tetap tersimpan dan ter-commit di clone ini.
"""
import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import think_tags  # noqa: E402

ROOT = HERE.parent
FILTERS = ["Semua", "Belum diisi", "Sudah diisi"]


def git(*args, check=True):
    p = subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True)
    out = (p.stdout + p.stderr).strip()
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        out = out.replace(token, "***")
    if check and p.returncode:
        raise RuntimeError(f"git {args[0]} gagal: {out[-500:]}")
    return out


def remote_url():
    """URL push: memakai GITHUB_TOKEN jika ada, tanpa menyimpannya ke git config."""
    url = git("remote", "get-url", "origin")
    token = os.environ.get("GITHUB_TOKEN")
    m = re.search(r"github\.com[:/](.+?)(\.git)?$", url)
    if token and m:
        return f"https://x-access-token:{token}@github.com/{m.group(1)}.git"
    return "origin"


def commit_and_push(sample_id, branch):
    git("add", "data/think", "data/train.jsonl")
    if not git("status", "--porcelain", "data/think", "data/train.jsonl"):
        return "Tidak ada perubahan untuk di-commit."
    git("commit", "-m", f"think: isi <think> untuk {sample_id}")
    url = remote_url()
    try:
        git("pull", "--rebase", "--autostash", url, branch)
        git("push", url, f"HEAD:{branch}")
    except RuntimeError as e:
        return f"Tersimpan dan ter-commit di clone ini, tetapi push gagal: {e}"
    return f"Tersimpan, di-commit, dan di-push ke {branch}."


def rows_by_id():
    return {r["id"]: r for r in think_tags.load_rows()}


def turns_of(row):
    """[(nomor jawaban, pesan user sebelumnya, jawaban tanpa <think>)] untuk setiap jawaban assistant."""
    out, last_user, n = [], "", 0
    for m in row["messages"]:
        if m["role"] == "user":
            last_user = m["content"]
        elif m["role"] == "assistant":
            n += 1
            out.append((n, last_user, think_tags.strip_think(m["content"])))
    return out


def label(row):
    turns = turns_of(row)
    done = sum(bool(think_tags.read_think(row["id"], n)) for n, _, _ in turns)
    mark = "✅" if done == len(turns) else ("◐" if done else "⬜")
    return f"{mark} {row['id']} · {row['category']}"


def choices(filter_name, query):
    out = []
    for row in rows_by_id().values():
        lab = label(row)
        if filter_name == "Belum diisi" and lab.startswith("✅"):
            continue
        if filter_name == "Sudah diisi" and not lab.startswith("✅"):
            continue
        if query and query.lower() not in lab.lower():
            continue
        out.append(lab)
    return out


def id_of(lab):
    return lab.split(" ", 2)[1] if lab else None


def progress_text():
    done, total = think_tags.status()
    return f"**{done}/{total}** jawaban sudah berisi `<think>`."


def count_text(text):
    words = len(text.split())
    return f"{words} kata · {len(text)} karakter"


def build_ui(branch, push_default):
    import gradio as gr

    with gr.Blocks(title="Editor <think> dataset own") as demo:
        gr.Markdown("# Editor isi `<think>`\nTulis sendiri rencana atau penalaran sebelum jawaban untuk setiap sampel. "
                    "Editor ini tidak menulis isi apa pun untukmu.")
        progress = gr.Markdown(progress_text())
        with gr.Row():
            with gr.Column(scale=1, min_width=260):
                filt = gr.Radio(FILTERS, value="Belum diisi", label="Tampilkan")
                query = gr.Textbox(label="Cari id atau kategori", placeholder="mis. web-0, py_")
                pick = gr.Dropdown(choices("Belum diisi", ""), label="Sampel", interactive=True)
                turn = gr.Radio([1], value=1, label="Jawaban ke-", visible=False)
            with gr.Column(scale=3):
                prompt = gr.Markdown(label="Prompt")
                with gr.Accordion("Jawaban sampel (tanpa <think>)", open=False):
                    answer = gr.Markdown()
                think = gr.Textbox(label="Isi <think>", lines=14, max_lines=40,
                                   placeholder="Tulis di sini. Kosongkan lalu Simpan untuk menghapus <think> dari sampel ini.")
                counter = gr.Markdown()
                with gr.Row():
                    push = gr.Checkbox(value=push_default, label=f"Commit & push ke {branch} setelah simpan")
                    save = gr.Button("Simpan", variant="primary")
                    save_next = gr.Button("Simpan & lanjut ke yang belum")
                result = gr.Markdown()

        def show(lab, n):
            row = rows_by_id().get(id_of(lab))
            if not row:
                return "", "", "", gr.update(visible=False), ""
            turns = turns_of(row)
            n = n if n in [t[0] for t in turns] else 1
            _, user, ans = turns[n - 1]
            text = think_tags.read_think(row["id"], n)
            return (f"**{row['id']}** · `{row['category']}`\n\n{user}", ans, text,
                    gr.update(choices=[t[0] for t in turns], value=n, visible=len(turns) > 1), count_text(text))

        def save_one(lab, n, text, do_push):
            sid = id_of(lab)
            if not sid:
                return "Pilih sampel dulu."
            path = think_tags.think_path(sid, n)
            path.parent.mkdir(parents=True, exist_ok=True)
            text = text.replace("\r\n", "\n").strip()
            if text:
                if "<think>" in text or "</think>" in text:
                    return "❌ Jangan menulis tag `<think>` atau `</think>` sendiri; tulis isinya saja."
                path.write_text(text + "\n", encoding="utf-8")
            elif path.exists():
                path.unlink()
            think_tags.apply()
            check = subprocess.run([sys.executable, str(HERE / "validate.py")], cwd=ROOT, capture_output=True, text=True)
            if check.returncode:
                return f"❌ Tersimpan, tetapi validasi dataset gagal:\n```\n{check.stdout[-1500:]}\n```"
            msg = f"✅ {sid} jawaban ke-{n} tersimpan ({count_text(text)}), dataset valid."
            if do_push:
                msg += "\n\n" + commit_and_push(sid, branch)
            return msg

        def refresh(filter_name, q, lab):
            opts = choices(filter_name, q)
            if lab and lab not in opts:  # sampel yang baru selesai tetap terpilih walaupun filternya "Belum diisi"
                opts.append(lab)
            return gr.update(choices=opts, value=lab), progress_text()

        def next_empty(filter_name, q, lab):
            semua = choices("Semua", "")
            start = semua.index(lab) + 1 if lab in semua else 0
            nxt = next((c for c in semua[start:] + semua[:start] if not c.startswith("✅")), None)
            return refresh(filter_name, q, nxt or label(rows_by_id()[id_of(lab)]))

        pick.change(show, [pick, turn], [prompt, answer, think, turn, counter])
        turn.change(show, [pick, turn], [prompt, answer, think, turn, counter])
        think.change(count_text, think, counter)
        for comp in (filt, query):
            comp.change(lambda f, q: gr.update(choices=choices(f, q), value=None), [filt, query], pick)
        save.click(save_one, [pick, turn, think, push], result).then(
            lambda f, q, lab: refresh(f, q, label(rows_by_id()[id_of(lab)]) if lab else None), [filt, query, pick], [pick, progress])
        save_next.click(save_one, [pick, turn, think, push], result).then(next_empty, [filt, query, pick], [pick, progress])
    return demo


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--branch", default="main", help="cabang tujuan push")
    parser.add_argument("--no-push", action="store_true", help="matikan commit & push sebagai bawaan")
    parser.add_argument("--port", type=int, default=7861)
    parser.add_argument("--share", action="store_true", help="link publik sementara (wajib --auth)")
    parser.add_argument("--auth", help="user:sandi")
    args = parser.parse_args([] if "ipykernel" in sys.modules else None)
    if args.share and not args.auth:
        raise SystemExit("--share membuat link yang bisa dibuka siapa pun; tambahkan --auth user:sandi")
    demo = build_ui(args.branch, not args.no_push)
    auth = tuple(args.auth.split(":", 1)) if args.auth else None
    demo.launch(server_port=args.port, share=args.share, auth=auth)


if __name__ == "__main__":
    main()
