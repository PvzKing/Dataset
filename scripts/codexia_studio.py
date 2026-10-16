"""Codexia Studio: inference Gradio untuk model Codexia2 (Qwen3.5-4B + adapter LoRA) tanpa kuantisasi, dengan tampilan
bergaya Claude Code dan editor kode Monaco.

Cara kerja:
  - Editor kosong: model menulis kode baru. Kodenya mengalir langsung ke editor Monaco saat dibuat.
  - Editor berisi kode: permintaan dianggap perubahan pada file itu. Model menjawab dengan blok SEARCH/REPLACE
    (format sampel web_debug dan py_debug di data training). Setiap blok diterapkan ke baris yang sama di editor,
    tanpa menulis ulang file. Baris yang berubah disorot di editor dan ditampilkan sebagai diff di transkrip.
  - Jalankan: Python dijalankan di subprocess (output dan traceback tampil di tab Output), HTML tampil di tab
    Pratinjau. /perbaiki tanpa keterangan mengirim error terakhir ke model.

Model dimuat 16-bit (bf16) atau float32, tidak pernah 4-bit atau 8-bit. Butuh GPU dengan bf16 asli (A100, L4, H100):
Qwen3.5 menghasilkan NaN di float16, dan float32 (±18 GB) tidak muat di T4.

Cara memakai di Google Colab (runtime A100 atau L4). Jangan jalankan di runtime yang sedang training: GPU-nya dipakai.

    Sel 1:  !pip install -q --upgrade unsloth "gradio>=5.40,<7"
    Sel 2:  from google.colab import drive; drive.mount("/content/drive")
            !wget -q -O /content/codexia_studio.py https://raw.githubusercontent.com/PvzKing/Dataset/main/scripts/codexia_studio.py
            (sebelum cabang ini di-merge, ganti main dengan claude/youthful-mayer-lvf8r6)
    Sel 3:  %run /content/codexia_studio.py

Opsi CONFIG bisa diganti lewat argumen, misalnya:

    %run /content/codexia_studio.py --adapter /content/drive/MyDrive/finetune-id/Codexia2/qwen3.5-4b-Codexia2/epoch-5/qwen3.5-4b-Codexia2-lora
    %run /content/codexia_studio.py --merged /content/drive/MyDrive/finetune-id/Codexia2/qwen3.5-4b-Codexia2/qwen3.5-4b-Codexia2-merged-16bit
    %run /content/codexia_studio.py --adapter none     # model dasar tanpa adapter, untuk pembanding
    %run /content/codexia_studio.py --dtype float32 --max-seq-len 8192
    %run /content/codexia_studio.py --demo        # coba tampilan tanpa GPU dan tanpa model

Perintah di kotak input:  /baru <permintaan>  /perbaiki [keluhan]  /jalankan  /undo  /file <nama>  /reset  /bantuan
"""
import argparse
import difflib
import html
import io
import json
import re
import shutil
import subprocess
import sys
import tarfile
import threading
import time
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

# ======================================================== CONFIG: ubah di sini ========================================
CONFIG = {
    # Adapter final Codexia2 (epoch terpilih). Ganti ke epoch-N/... untuk mencoba epoch lain, atau "none" untuk
    # model dasar (base_model) tanpa adapter.
    "adapter": "/content/drive/MyDrive/finetune-id/Codexia2/qwen3.5-4b-Codexia2/qwen3.5-4b-Codexia2-lora",
    "merged": None,                 # folder model 16-bit hasil merge (EKSPOR_16BIT); jika diisi, adapter diabaikan
    "base_model": "unsloth/Qwen3.5-4B",  # dipakai jika adapter = "none" dan sebagai cadangan pemuatan adapter
    "dtype": "bfloat16",            # "bfloat16" (disarankan) atau "float32". Tidak ada 4-bit/8-bit
    "merge_adapter": False,         # True = gabungkan LoRA ke bobot 16-bit setelah dimuat (sedikit lebih cepat)
    "max_seq_len": 16384,           # sama dengan training: prompt + kode + jawaban harus muat di sini
    "thinking": False,              # model dilatih tanpa mode berpikir
    # Menulis kode baru: rekomendasi Qwen3.5 non-thinking.
    "write_temperature": 0.7, "write_top_p": 0.8, "write_top_k": 20, "write_min_p": 0.0,
    "write_repetition_penalty": 1.05, "write_max_new_tokens": 12000,
    # Mengedit: greedy dan tanpa repetition penalty, supaya blok SEARCH menyalin baris kode persis.
    "edit_temperature": 0.0, "edit_top_p": 0.8, "edit_top_k": 20, "edit_min_p": 0.0,
    "edit_repetition_penalty": 1.0, "edit_max_new_tokens": 3072,
    "edit_mode": "patch",           # "patch" = jawaban dimulai dengan blok SEARCH/REPLACE; "bebas" = model memilih
    "retry_failed_patch": True,     # blok SEARCH yang tidak cocok dikirim balik ke model satu kali
    "seed": -1,                     # -1 = acak
    "workdir": "/content/codexia" if Path("/content").is_dir() else "codexia",  # file kerja dan riwayat versinya
    "file": "index.html",           # nama file awal; berubah otomatis sesuai bahasa kode pertama
    "run_timeout": 20,              # detik, batas waktu Jalankan
    "monaco": "auto",               # "auto" = unduh Monaco dari npm lalu sajikan lokal, cadangan CDN; "cdn"; "lokal"
    "monaco_version": "0.52.2",
    "app_name": "Codexia Studio",
    "share": False,                 # True = link publik *.gradio.live (wajib auth)
    "auth": None,                   # "user:sandi"
    "port": None,
    "demo": False,                  # True = model tiruan, untuk mencoba tampilan tanpa GPU
}
# ======================================================================================================================

IN_NOTEBOOK = "ipykernel" in sys.modules
FENCE = "`" * 3
PATCH_BLOCK = re.compile(r"<{7} SEARCH[ \t]*\n(.*?)\n?={7}[ \t]*\n(.*?)\n?>{7} REPLACE", re.S)
CODE_BLOCK = re.compile(FENCE + r"([\w+#.-]*)[ \t]*\n(.*?)\n" + FENCE, re.S)
PATCH_PREFILL = f"**Perbaikan**\n{FENCE}\n<<<<<<< SEARCH\n"
# ekstensi -> (bahasa Monaco, tag blok kode)
LANGS = {".html": ("html", "html"), ".htm": ("html", "html"), ".py": ("python", "python"), ".js": ("javascript", "javascript"),
         ".ts": ("typescript", "typescript"), ".css": ("css", "css"), ".json": ("json", "json"), ".sql": ("sql", "sql"),
         ".sh": ("shell", "bash"), ".md": ("markdown", "markdown"), ".java": ("java", "java"), ".go": ("go", "go"),
         ".php": ("php", "php"), ".c": ("c", "c"), ".cpp": ("cpp", "cpp"), ".rs": ("rust", "rust"), ".txt": ("plaintext", "")}
TAG_TO_EXT = {"html": ".html", "python": ".py", "py": ".py", "javascript": ".js", "js": ".js", "typescript": ".ts",
              "ts": ".ts", "css": ".css", "json": ".json", "sql": ".sql", "bash": ".sh", "sh": ".sh", "java": ".java",
              "go": ".go", "php": ".php", "c": ".c", "cpp": ".cpp", "rust": ".rs"}
DEFAULT_NAME = {".html": "index.html", ".py": "main.py", ".js": "script.js"}
SPINNER = ["Merangkai", "Menimbang", "Meracik", "Menelusuri", "Merapikan", "Menyusun"]
HELP = """**Perintah**
- `<permintaan>`: editor kosong → tulis kode baru; editor berisi kode → ubah file itu dengan blok SEARCH/REPLACE
- `/baru <permintaan>`: tulis kode baru walaupun editor berisi kode
- `/perbaiki [keluhan]`: perbaiki error terakhir dari Jalankan, atau keluhan yang Anda tulis
- `/jalankan`: jalankan file (Python) atau tampilkan pratinjau (HTML)
- `/undo`: kembalikan versi sebelum perubahan terakhir
- `/file <nama>`: ganti nama file aktif, misalnya `/file app.py`
- `/reset`: kosongkan transkrip dan editor
Kode di editor boleh Anda ubah langsung; perubahan Anda ikut dipakai pada perintah berikutnya."""


# ---------------------------------------------------------------- argumen

def parse_args():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for key, value in CONFIG.items():
        flag = "--" + key.replace("_", "-")
        if isinstance(value, bool):
            parser.add_argument(flag, action=argparse.BooleanOptionalAction, default=None)
        elif isinstance(value, (int, float)) and not isinstance(value, bool):
            parser.add_argument(flag, type=type(value), default=None)
        else:
            parser.add_argument(flag, type=int if key == "port" else str, default=None)
    args, _ = parser.parse_known_args(sys.argv[1:])  # di notebook sys.argv berisi argumen kernel
    for key, value in CONFIG.items():
        if getattr(args, key, None) is None:
            setattr(args, key, value)
    if args.share and not args.auth:
        raise SystemExit("--share membuat studio bisa diakses siapa pun yang tahu link-nya: tambahkan --auth user:sandi")
    if args.dtype not in ("bfloat16", "float32"):
        raise SystemExit("--dtype harus bfloat16 atau float32 (script ini tidak memuat model terkuantisasi)")
    if args.edit_mode not in ("patch", "bebas"):
        raise SystemExit('--edit-mode harus "patch" atau "bebas"')
    if not args.demo:
        check_model_folder(args)
    return args


def base_only(args):
    """True jika yang dimuat model dasar saja (--adapter none)."""
    return not args.merged and str(args.adapter).lower() == "none"


def check_model_folder(args):
    if base_only(args):
        return
    if args.merged:
        if not (Path(args.merged) / "config.json").is_file():
            raise SystemExit(f"bukan folder model (tidak ada config.json): {args.merged}")
        return
    adapter = Path(args.adapter)
    if (adapter / "adapter_config.json").is_file():
        return
    run = adapter.parent
    epochs = sorted(run.glob("epoch-*/*-lora/adapter_config.json"), key=lambda p: int(p.parts[-3].split("-")[1]))
    hint = ""
    if epochs:
        hint = ("\nAdapter per epoch yang sudah ada:\n" + "\n".join(f"  {p.parent}" for p in epochs) +
                "\nPakai salah satunya dengan --adapter <folder>, atau tunggu training dan pemilihan epoch selesai.")
    raise SystemExit(f"adapter tidak ditemukan: {adapter}\nPastikan Drive sudah di-mount." + hint)


# ---------------------------------------------------------------- model

class Engine:
    """Model 16-bit/float32, tokenizer, dan generasi streaming. Satu generasi berjalan pada satu waktu."""

    def __init__(self, args):
        self.args = args
        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self.last_speed = None
        if args.demo:
            self.name, self.info = "demo", "model tiruan"
            return
        import torch
        if not torch.cuda.is_available():
            raise SystemExit("Tidak ada GPU. Pilih Runtime → Change runtime type → A100 GPU (atau L4).")
        props = torch.cuda.get_device_properties(0)
        if args.dtype == "bfloat16" and props.major < 8:
            raise SystemExit(f"{props.name} tidak mendukung bf16 asli. Qwen3.5 menghasilkan NaN di float16, dan "
                             "float32 butuh ±18 GB VRAM. Pakai runtime A100 atau L4.")
        dtype = getattr(torch, args.dtype)
        from unsloth import FastLanguageModel

        name = args.base_model if base_only(args) else args.merged or args.adapter
        print(f"memuat {name} ({args.dtype}, tanpa kuantisasi) ...", flush=True)
        load = dict(max_seq_length=args.max_seq_len, dtype=dtype, load_in_4bit=False, load_in_8bit=False,
                    load_in_16bit=args.dtype == "bfloat16")
        try:
            model, tokenizer = FastLanguageModel.from_pretrained(model_name=str(name), **load)
        except Exception as e:
            if args.merged or base_only(args):
                raise
            # Cadangan: model dasar 16-bit lalu adapter lewat PEFT.
            base = json.loads((Path(args.adapter) / "adapter_config.json").read_text()).get("base_model_name_or_path")
            print(f"memuat adapter lewat Unsloth gagal ({e}); mencoba {base or args.base_model} + PEFT", flush=True)
            from peft import PeftModel
            model, tokenizer = FastLanguageModel.from_pretrained(model_name=base or args.base_model, **load)
            model = PeftModel.from_pretrained(model, args.adapter)
        if getattr(model, "is_loaded_in_4bit", False) or getattr(model, "is_loaded_in_8bit", False):
            raise SystemExit("model termuat terkuantisasi, padahal diminta tanpa kuantisasi; periksa versi Unsloth")
        if args.merge_adapter and not args.merged and hasattr(model, "merge_and_unload"):
            print("menggabungkan adapter ke bobot ...", flush=True)
            model = model.merge_and_unload()
        FastLanguageModel.for_inference(model)
        self.model, self.torch = model, torch
        self.tokenizer = getattr(tokenizer, "tokenizer", tokenizer)  # processor multimodal -> tokenizer teks
        if self.tokenizer is not tokenizer and not getattr(self.tokenizer, "chat_template", None):
            self.tokenizer.chat_template = tokenizer.chat_template  # sama dengan train_unsloth.unwrap_tokenizer
        param = next(p for p in model.parameters() if p.dtype.is_floating_point)
        self.name = Path(name).name
        self.info = f"{param.dtype}".replace("torch.", "") + f" · {props.name}"
        print(f"siap: {self.name} · {self.info} · {torch.cuda.memory_allocated() / 1e9:.1f} GB VRAM", flush=True)

    def stop(self):
        self.stop_event.set()

    def count_tokens(self, text):
        if self.args.demo:
            return len(text) // 4
        return len(self.tokenizer(text, add_special_tokens=False)["input_ids"])

    def render(self, messages, thinking):
        if self.args.demo:
            return "\n".join(m["content"] for m in messages)
        return self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True,
                                                  enable_thinking=thinking)

    def stream(self, prompt, s):
        """Hasilkan potongan teks jawaban satu per satu. s: dict sampling."""
        self.stop_event.clear()
        if self.args.demo:
            yield from demo_stream(prompt, self.stop_event)
            return
        from transformers import StoppingCriteria, StoppingCriteriaList, TextIteratorStreamer
        stop_event, torch = self.stop_event, self.torch

        class StopOnEvent(StoppingCriteria):
            def __call__(self, input_ids, scores, **kwargs):
                return stop_event.is_set()

        inputs = self.tokenizer(prompt, return_tensors="pt", add_special_tokens=False).to(self.model.device)
        streamer = TextIteratorStreamer(self.tokenizer, skip_prompt=True, skip_special_tokens=True)
        sample = s["temperature"] > 0
        kwargs = dict(**inputs, streamer=streamer, max_new_tokens=s["max_new_tokens"], do_sample=sample,
                      repetition_penalty=s["repetition_penalty"], stopping_criteria=StoppingCriteriaList([StopOnEvent()]))
        if sample:
            kwargs.update(temperature=s["temperature"], top_p=s["top_p"], top_k=s["top_k"], min_p=s["min_p"])
        if s["seed"] >= 0:
            torch.manual_seed(int(s["seed"]))
        error = []

        def run():
            try:
                with torch.inference_mode():
                    self.model.generate(**kwargs)
            except Exception as e:  # tampilkan ke pengguna, jangan biarkan streamer menunggu selamanya
                error.append(e)
                streamer.end()

        with self.lock:
            thread = threading.Thread(target=run, daemon=True)
            thread.start()
            try:
                yield from streamer
            finally:
                stop_event.set()  # dibatalkan (tombol stop/tutup tab): hentikan generate di GPU
                thread.join()
        if error:
            raise error[0]


DEMO_HTML = """<!DOCTYPE html>
<html lang="id">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Penghitung</title>
  <style>
    body { font-family: system-ui, sans-serif; display: grid; place-items: center; min-height: 100vh; margin: 0; }
    button { padding: .8rem 1.4rem; font-size: 1rem; border-radius: 10px; border: 0; background: #d97757; color: #fff; }
  </style>
</head>
<body>
  <button id="tombol">Klik saya</button>
  <script>
    let jumlah = 0;
    const tombol = document.getElementById('tombol');
    tombol.addEventListener('click', () => {
      jumlah++;
      tombol.textContent = 'Diklik ' + jumlah + ' kali';
    });
  </script>
</body>
</html>"""

DEMO_PY = '''def rata_rata(nilai):
    return sum(nilai) / len(nilai)


if __name__ == "__main__":
    print(rata_rata([80, 90, 75]))
    print(rata_rata([]))
'''


def demo_stream(prompt, stop_event):
    """Jawaban tiruan: tulis HTML/Python baru, atau patch SEARCH/REPLACE pada kode di prompt."""
    m = CODE_BLOCK.search(prompt)
    if m and m[2].strip():
        code = m[2]
        if "def rata_rata" in code:
            text = ("    return sum(nilai) / len(nilai)\n=======\n    if not nilai:\n        return 0.0\n"
                    "    return sum(nilai) / len(nilai)\n>>>>>>> REPLACE\n" + FENCE +
                    "\n\n`len([])` bernilai 0, jadi pembagian gagal. List kosong sekarang menghasilkan `0.0`.")
        else:
            line = next((ln for ln in code.split("\n") if "<title>" in ln or "def " in ln), code.split("\n")[0])
            new = line.replace("<title>", "<title>Demo · ") if "<title>" in line else line + "  # diubah"
            text = f"{line}\n=======\n{new}\n>>>>>>> REPLACE\n{FENCE}\n\nHanya satu baris yang diubah."
        if not prompt.endswith(PATCH_PREFILL):  # mode bebas: tanpa prefill, model menulis pembuka blok sendiri
            text = f"Perbaikannya:\n\n{FENCE}\n<<<<<<< SEARCH\n" + text
    else:
        python = "python" in prompt.lower()
        text = ("Berikut programnya.\n\n" + FENCE + ("python\n" + DEMO_PY if python else "html\n" + DEMO_HTML) + "\n" +
                FENCE + "\n\n**Cek kebutuhan**\n- **Contoh** → kode demo tanpa model.")
    for i in range(0, len(text), 8):
        if stop_event.is_set():
            return
        time.sleep(0.008)
        yield text[i:i + 8]


# ---------------------------------------------------------------- kode dan patch

def lang_of(name):
    return LANGS.get(Path(name).suffix.lower(), ("plaintext", ""))


def apply_patch(code, search, replace):
    """Terapkan satu blok SEARCH/REPLACE. Kembalikan (kode baru, cara) atau (None, alasan gagal)."""
    if search.strip() and code.count(search) == 1:
        return code.replace(search, replace, 1), "tepat"
    # Cadangan: cocokkan per baris tanpa memperhitungkan spasi di awal/akhir baris (indentasi model sering meleset).
    want = [line.strip() for line in search.strip("\n").split("\n")]
    if not any(want):
        return None, "blok SEARCH kosong"
    lines = code.split("\n")
    hits = [i for i in range(len(lines) - len(want) + 1) if [ln.strip() for ln in lines[i:i + len(want)]] == want]
    if len(hits) != 1:
        return None, "teks SEARCH tidak ditemukan di file" if not hits else f"teks SEARCH cocok {len(hits)} kali"
    i = hits[0]
    first = next(ln for ln in search.strip("\n").split("\n") if ln.strip())
    model_indent = first[:len(first) - len(first.lstrip())]
    file_indent = lines[i][:len(lines[i]) - len(lines[i].lstrip())]
    new_lines = [file_indent + ln[len(model_indent):] if ln.startswith(model_indent) and ln.strip() else ln
                 for ln in replace.split("\n")]
    return "\n".join(lines[:i] + new_lines + lines[i + len(want):]), "longgar (indentasi disesuaikan)"


def main_code_block(answer, streaming=False):
    """(tag, kode) blok kode utama di jawaban: blok terpanjang yang berbahasa kode. Saat streaming, blok terbuka."""
    blocks = [(t.lower(), c) for t, c in CODE_BLOCK.findall(answer) if t.lower() in TAG_TO_EXT]
    if streaming:
        last = answer.rfind(FENCE)
        opened = re.match(FENCE + r"([\w+#.-]*)[ \t]*\n", answer[last:]) if last >= 0 else None
        if opened and answer.count(FENCE) % 2 == 1 and opened[1].lower() in TAG_TO_EXT:
            return opened[1].lower(), answer[last + opened.end():]
    if not blocks:
        return None, ""
    return max(blocks, key=lambda b: len(b[1]))


def prose_of(answer):
    """Penjelasan model tanpa blok kode panjang dan blok patch (kode tampil di editor dan diff)."""
    text = re.sub(FENCE + r"[a-z]*\s*\n<{7} SEARCH.*?>{7} REPLACE\s*\n?" + FENCE, "", answer, flags=re.S)
    text = PATCH_BLOCK.sub("", text)
    text = CODE_BLOCK.sub(lambda m: "" if m[1].lower() in TAG_TO_EXT and m[2].count("\n") > 8 else m[0], text)
    text = re.sub(FENCE + r"[\w+#.-]*\s*\n.*$", "", text, flags=re.S) if text.count(FENCE) % 2 else text
    text = re.sub(r"^\*\*Perbaikan\*\*\s*|\s*\*\*Perbaikan\*\*\s*$", "", text.strip())
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def changed_ranges(old, new):
    """Rentang baris (1-based, inklusif) di kode baru yang berubah atau ditambahkan."""
    ranges = []
    sm = difflib.SequenceMatcher(None, old.split("\n"), new.split("\n"), autojunk=False)
    for tag, _, _, j1, j2 in sm.get_opcodes():
        if tag in ("replace", "insert") and j2 > j1:
            ranges.append([j1 + 1, j2])
        elif tag == "delete":
            ranges.append([max(j1, 1), max(j1, 1)])
    return ranges


def diff_rows(old, new, context=2, limit=120):
    rows, added, removed, o, n = [], 0, 0, 0, 0
    for line in difflib.unified_diff(old.split("\n"), new.split("\n"), lineterm="", n=context):
        if line.startswith(("---", "+++")):
            continue
        if line.startswith("@@"):
            m = re.match(r"@@ -(\d+)(?:,\d+)? \+(\d+)", line)
            o, n = int(m[1]), int(m[2])
            if rows:
                rows.append(("gap", "", "⋮"))
            continue
        tag, text = line[:1], line[1:]
        if tag == "-":
            rows.append(("del", o, text)); o += 1; removed += 1
        elif tag == "+":
            rows.append(("add", n, text)); n += 1; added += 1
        else:
            rows.append(("ctx", n, text)); o += 1; n += 1
    return rows[:limit], added, removed, len(rows) > limit


# ---------------------------------------------------------------- proyek

@dataclass
class Project:
    name: str = "index.html"
    code: str = ""
    versions: list = field(default_factory=list)   # (nama, kode) sebelumnya untuk /undo
    events: list = field(default_factory=list)     # transkrip
    highlight: list = field(default_factory=list)  # rentang baris yang baru berubah
    last_run: dict = field(default_factory=dict)   # {"cmd", "code", "out", "ok"}
    prompt_tokens: int = 0
    rev: int = 0

    def set_code(self, new, workdir, highlight=None):
        if new == self.code:
            return
        self.versions.append((self.name, self.code))
        del self.versions[:-40]
        self.highlight = highlight if highlight is not None else changed_ranges(self.code, new)
        self.code = new
        save_file(self, workdir)


def save_file(project, workdir):
    folder = Path(workdir)
    try:
        (folder / ".versi").mkdir(parents=True, exist_ok=True)
        (folder / project.name).write_text(project.code, encoding="utf-8")
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        (folder / ".versi" / f"{stamp}-{len(project.versions):03d}-{project.name}").write_text(project.code, encoding="utf-8")
    except OSError as e:
        print(f"gagal menyimpan ke {folder}: {e}", flush=True)


def run_file(project, workdir, timeout):
    """Jalankan file aktif. Kembalikan dict hasil, atau None jika bahasanya tidak dijalankan di sini."""
    path = Path(workdir) / project.name
    ext = path.suffix.lower()
    if ext == ".py":
        cmd = [sys.executable, "-u", path.name]
    elif ext == ".js" and shutil.which("node"):
        cmd = ["node", path.name]
    elif ext == ".sh":
        cmd = ["bash", path.name]
    else:
        return None
    try:
        r = subprocess.run(cmd, cwd=workdir, capture_output=True, text=True, timeout=timeout, stdin=subprocess.DEVNULL)
        out, code = (r.stdout + r.stderr), r.returncode
    except subprocess.TimeoutExpired as e:
        out = ((e.stdout or b"").decode(errors="replace") if isinstance(e.stdout, bytes) else (e.stdout or ""))
        out += f"\n[dihentikan: lebih dari {timeout} detik]"
        code = -1
    out = out.rstrip()
    if len(out) > 8000:
        out = out[:3000] + "\n…\n" + out[-4500:]
    return {"cmd": " ".join([Path(cmd[0]).name, *cmd[1:]]), "code": code, "out": out, "ok": code == 0}


def runnable(name):
    ext = Path(name).suffix.lower()
    return ext in (".py", ".sh") or (ext == ".js" and shutil.which("node") is not None)


# ---------------------------------------------------------------- prompt

def write_messages(request):
    return [{"role": "user", "content": request}]


def edit_messages(project, instruction, error_out="", patch_mode=True, failed=None):
    """Format sampel debug di data training: keluhan, lalu kode lengkap dalam blok kode, lalu output/error."""
    tag = lang_of(project.name)[1]
    parts = [instruction.strip() or "Tolong cari penyebabnya dan perbaiki bagian yang rusak saja."]
    parts.append(f"{FENCE}{tag}\n{project.code}\n{FENCE}")
    if error_out:
        parts.append(f"Outputnya:\n\n{FENCE}\n{error_out}\n{FENCE}")
    if failed:
        parts.append("Blok SEARCH berikut tidak cocok persis dengan kode di atas, jadi belum diterapkan:\n\n" +
                     "\n\n".join(f"{FENCE}\n{s}\n{FENCE}" for s in failed) +
                     "\n\nTulis ulang blok itu dengan menyalin baris SEARCH persis dari kode di atas.")
    if patch_mode:
        parts.append("Ubah hanya baris yang perlu dengan blok SEARCH/REPLACE, jangan tulis ulang seluruh file.")
    return [{"role": "user", "content": "\n\n".join(parts)}]


def settings_from(values):
    keys = ["temperature", "top_p", "top_k", "min_p", "repetition_penalty", "max_new_tokens"]
    s = dict(zip(keys, values))
    s["top_k"], s["max_new_tokens"] = int(s["top_k"]), int(s["max_new_tokens"])
    return s


# ---------------------------------------------------------------- agen

class Studio:
    def __init__(self, engine, args):
        self.engine, self.args = engine, args
        self.user_stop = threading.Event()

    def budget(self, project, prompt, s):
        """Batasi max_new_tokens supaya prompt + jawaban muat di konteks. None jika prompt saja sudah terlalu panjang."""
        used = self.engine.count_tokens(prompt)
        project.prompt_tokens = used
        room = self.args.max_seq_len - used
        if room < 256:
            return None
        return dict(s, max_new_tokens=min(s["max_new_tokens"], room))

    def generate(self, project, prompt, s, label, on_text):
        """Streaming dengan spinner; on_text(teks) -> kode live atau None. Hasilkan (spinner, kode live)."""
        word = SPINNER[len(project.events) % len(SPINNER)]
        text, last, start, tokens = "", 0.0, time.time(), 0
        for piece in self.engine.stream(prompt, s):
            text += piece
            tokens += 1
            now = time.time()
            if now - last > 0.2:
                last = now
                speed = tokens / max(now - start, 1e-6)
                yield ("spinner", f"{word} · {label}", f"{now - start:.0f} dtk · ±{speed:.0f} tok/dtk"), on_text(text)
            if self.user_stop.is_set():
                break
        elapsed = time.time() - start
        self.engine.last_speed = (self.engine.count_tokens(text) / elapsed) if elapsed > 0 else None
        return text

    def write(self, project, request, s, thinking):
        prompt = self.engine.render(write_messages(request), thinking)
        s = self.budget(project, prompt, s)
        if s is None:
            project.events.append(tool("Write", project.name, "error", [("t-red", "permintaan terlalu panjang untuk konteks")]))
            return False
        live = {"tag": None}

        def on_text(text):
            tag, code = main_code_block(text, streaming=True)
            if tag:
                live["tag"] = tag
            return (code, True, []) if code else None

        answer = yield from self.generate(project, prompt, s, "menulis kode", on_text)
        tag, code = main_code_block(answer)
        prose = prose_of(answer)
        if prose:
            project.events.append({"kind": "text", "text": prose})
        if not code.strip():
            project.events.append(tool("Write", project.name, "warn", [("t-orange", "jawaban tidak berisi blok kode")]))
            return False
        ext = TAG_TO_EXT.get(tag, Path(project.name).suffix)
        if Path(project.name).suffix.lower() != ext:
            project.name = DEFAULT_NAME.get(ext, "kode" + ext)
        old = project.code
        project.set_code(code.strip("\n") + "\n", self.args.workdir, highlight=[])
        stopped = " (dihentikan)" if self.user_stop.is_set() else ""
        lines = project.code.count("\n")
        project.events.append(tool("Write", project.name, "ok",
                                   [("", f"menulis {lines} baris{stopped}" + (" (menggantikan file lama)" if old else ""))]))
        return True

    def edit(self, project, instruction, s, thinking, patch_mode, retry, error_out=""):
        """Ubah file aktif dengan blok SEARCH/REPLACE. Kembalikan True jika kode berubah."""
        before = project.code
        failed_search, attempt = None, 0
        while True:
            attempt += 1
            messages = edit_messages(project, instruction, error_out, patch_mode, failed_search)
            prefill = PATCH_PREFILL if patch_mode else ""
            prompt = self.engine.render(messages, thinking) + prefill
            s2 = self.budget(project, prompt, s)
            if s2 is None:
                project.events.append(tool("Update", project.name, "error",
                                           [("t-red", "kode + permintaan terlalu panjang untuk konteks "
                                                      f"{self.args.max_seq_len:,} token")]))
                return False
            base = project.code
            state = {"applied": 0, "code": base}

            def on_text(text):
                # Terapkan blok yang sudah lengkap saat itu juga, supaya editor berubah selagi model menulis.
                blocks = PATCH_BLOCK.findall(prefill + text)
                code = state["code"]
                for search, replace in blocks[state["applied"]:]:
                    out, _ = apply_patch(code, search, replace)
                    if out is not None:
                        code = out
                    state["applied"] += 1
                state["code"] = code
                if not patch_mode and not blocks:
                    tag, live = main_code_block(text, streaming=True)
                    return (live, True, []) if live else None
                return (code, False, changed_ranges(base, code)) if code != base else None

            answer = prefill + (yield from self.generate(project, prompt, s2, "mengedit " + project.name, on_text))
            blocks = PATCH_BLOCK.findall(answer)
            results, code = [], base
            for search, replace in blocks:
                out, how = apply_patch(code, search, replace)
                results.append((out is not None, how, search))
                if out is not None:
                    code = out
            prose = prose_of(answer)
            if prose:
                project.events.append({"kind": "text", "text": prose})
            if not blocks:
                tag, full = main_code_block(answer)
                if full.strip() and not patch_mode:
                    old = project.code
                    project.set_code(full.strip("\n") + "\n", self.args.workdir)
                    project.events.append(tool("Update", project.name, "warn",
                                               [("t-orange", "model menulis ulang seluruh file")],
                                               diff=diff_rows(old, project.code)))
                    return True
                project.events.append(tool("Update", project.name, "warn",
                                           [("t-orange", "jawaban tidak berisi blok SEARCH/REPLACE")]))
                return project.code != before
            ok = [r for r in results if r[0]]
            bad = [r for r in results if not r[0]]
            if ok:
                old = project.code
                project.set_code(code, self.args.workdir)
                rows = diff_rows(old, project.code)
                loose = sum(1 for r in ok if r[1] != "tepat")
                lines = [("", f"{len(ok)} blok diterapkan · +{rows[1]} / −{rows[2]} baris" +
                          (f" · {loose} dicocokkan longgar" if loose else ""))]
                project.events.append(tool("Update", project.name, "ok" if not bad else "warn", lines, diff=rows))
            for _, how, search in bad:
                first = next((ln.strip() for ln in search.split("\n") if ln.strip()), "")[:90]
                project.events.append(tool("Update", project.name, "error", [("t-red", f"blok gagal: {how}"),
                                                                              ("t-dim", first)]))
            if bad and retry and attempt == 1 and not self.user_stop.is_set():
                failed_search = [r[2] for r in bad]
                project.events.append({"kind": "text", "text": "Mengirim ulang blok yang tidak cocok ke model."})
                continue
            return project.code != before

    def run(self, project):
        if not project.code.strip():
            project.events.append({"kind": "text", "text": "Editor masih kosong."})
            return None
        result = run_file(project, self.args.workdir, self.args.run_timeout)
        if result is None:
            if project.name.lower().endswith((".html", ".htm")):
                project.events.append(tool("Preview", project.name, "ok", [("", "lihat tab Pratinjau")]))
            else:
                project.events.append(tool("Bash", project.name, "warn",
                                           [("t-orange", "bahasa ini tidak dijalankan di studio")]))
            return None
        project.last_run = result
        out = result["out"] or "(tidak ada output)"
        shown = out.split("\n")
        lines = [("t-red" if not result["ok"] else "", ln) for ln in (shown[:12] + (["…"] if len(shown) > 12 else []))]
        status = "ok" if result["ok"] else "error"
        lines.append(("t-dim", f"exit code {result['code']}"))
        project.events.append(tool("Bash", result["cmd"], status, lines))
        return result


def tool(name, arg, status, lines, diff=None):
    return {"kind": "tool", "name": name, "arg": arg, "status": status, "lines": lines, "diff": diff}


# ---------------------------------------------------------------- tampilan

def md(text):
    """Markdown sederhana -> HTML. Semua teks di-escape dulu."""
    out = []
    for i, part in enumerate(re.split(FENCE + r"[\w+#.-]*\n?", text)):
        if i % 2:
            out.append(f'<pre class="t-code">{html.escape(part.rstrip())}</pre>')
            continue
        lines = []
        for line in part.strip("\n").split("\n"):
            s = html.escape(line)
            s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
            s = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", s)
            if re.match(r"#{1,6} ", line):
                s = f"<b>{s.lstrip('#').strip()}</b>"
            elif re.match(r"\s*[-*] ", line):
                s = re.sub(r"^(\s*)[-*] ", r"\1• ", s)
            lines.append(s)
        out.append("<br>".join(lines))
    return "".join(out)


def render_event(e):
    kind = e["kind"]
    if kind == "welcome":
        return (f'<div class="t-welcome"><div><span class="t-star">✻</span> Selamat datang di <b>{html.escape(e["app"])}</b>!</div>'
                f'<div class="t-dim">/bantuan untuk daftar perintah</div>'
                f'<div class="t-dim">model: {html.escape(e["model"])}</div>'
                f'<div class="t-dim">folder: {html.escape(e["workdir"])}</div></div>')
    if kind == "user":
        return f'<div class="t-user"><span class="t-caret">&gt;</span> {html.escape(e["text"])}</div>'
    if kind == "text":
        return f'<div class="t-row"><span class="t-dot">●</span><div class="t-body">{md(e["text"])}</div></div>'
    if kind == "spinner":
        return (f'<div class="t-spinner"><span class="t-glyph"></span> {html.escape(e["text"])}… '
                f'<span class="t-dim">({html.escape(e["detail"])} · ■ untuk berhenti)</span></div>')
    if kind == "tool":
        color = {"ok": "t-green", "error": "t-red", "warn": "t-orange"}[e["status"]]
        head = (f'<div class="t-row"><span class="t-dot {color}">●</span><div class="t-body"><b>{html.escape(e["name"])}</b>'
                f'<span class="t-dim">({html.escape(e["arg"])})</span></div></div>')
        subs = "".join(f'<div class="t-sub"><span class="t-elbow">{"⎿" if i == 0 else " "}</span>'
                       f'<span class="{cls}">{html.escape(text)}</span></div>' for i, (cls, text) in enumerate(e["lines"]))
        diff = ""
        if e.get("diff"):
            rows, _, _, more = e["diff"]
            cells = "".join(f'<div class="d-{k}"><span class="d-no">{no}</span><span class="d-sign">'
                            f'{"+" if k == "add" else "-" if k == "del" else " "}</span>'
                            f'<span class="d-text">{html.escape(t)}</span></div>' for k, no, t in rows)
            diff = f'<div class="t-diff">{cells}{"<div class=d-gap>… diff dipotong</div>" if more else ""}</div>'
        return head + subs + diff
    return ""


def render_terminal(events, busy=None):
    items = list(events) + ([{"kind": "spinner", "text": busy[1], "detail": busy[2]}] if busy else [])
    return f'<div class="term-scroll"><div class="term-inner">{"".join(render_event(e) for e in items)}</div></div>'


def render_output(project):
    r = project.last_run
    if not r:
        return '<div class="out-empty">Belum ada yang dijalankan. Tekan ▶ Jalankan (Python, JavaScript, Bash).</div>'
    cls = "out-ok" if r["ok"] else "out-err"
    return (f'<div class="out-head">$ {html.escape(r["cmd"])} <span class="{cls}">exit {r["code"]}</span></div>'
            f'<pre class="out-pre">{html.escape(r["out"] or "(tidak ada output)")}</pre>')


def render_preview(project):
    if not project.name.lower().endswith((".html", ".htm")) or not project.code.strip():
        return '<div class="out-empty">Pratinjau tersedia untuk file HTML.</div>'
    return (f'<iframe class="preview-frame" sandbox="allow-scripts allow-forms allow-modals" '
            f'srcdoc="{html.escape(project.code, quote=True)}"></iframe>')


def status_line(project, args, engine, busy=False):
    ctx = f"konteks {project.prompt_tokens:,}/{args.max_seq_len:,}" if project.prompt_tokens else f"konteks {args.max_seq_len:,}"
    speed = f"{engine.last_speed:.0f} tok/dtk" if engine.last_speed else ""
    parts = [args.app_name, engine.name, engine.info, ctx, speed, project.name,
             f"{project.code.count(chr(10))} baris" if project.code else "", "● bekerja" if busy else ""]
    return '<div class="statusline">' + "".join(f"<span>{html.escape(p)}</span>" for p in parts if p) + "</div>"


CSS = """
:root { --t-bg: #1a1a19; --t-panel: #232321; --t-border: #3a3936; --t-text: #e8e6df; --t-dim: #8f8c83;
  --t-accent: #d97757; --t-green: #6fbf73; --t-red: #e5736a; --t-orange: #e0a458; }
body, gradio-app, .gradio-container { background: var(--t-bg) !important; color: var(--t-text); }
.gradio-container { max-width: 100% !important; padding: 8px 12px !important; }
footer { display: none !important; }
.cx-hidden { display: none !important; }
#term { border: 1px solid var(--t-border); border-radius: 10px; background: var(--t-bg); padding: 0 !important; }
.term-scroll { height: 68vh; overflow-y: auto; display: flex; flex-direction: column-reverse; padding: 10px 14px; }
.term-inner { margin-bottom: auto; font-family: "JetBrains Mono", ui-monospace, Menlo, Consolas, monospace;
  font-size: 13px; line-height: 1.55; color: var(--t-text); }
.t-welcome { border: 1px solid var(--t-accent); border-radius: 8px; padding: 8px 12px; margin-bottom: 12px;
  display: inline-block; max-width: 100%; overflow-wrap: anywhere; }
.t-star, .t-spinner { color: var(--t-accent); }
.t-dim { color: var(--t-dim); }
.t-user { background: #2b2a27; border-radius: 6px; padding: 6px 10px; margin: 12px 0 8px; white-space: pre-wrap; }
.t-caret { color: var(--t-dim); }
.t-row { display: flex; gap: 8px; margin-top: 8px; }
.t-dot { flex: none; }
.t-body { min-width: 0; overflow-wrap: anywhere; }
.t-green { color: var(--t-green); } .t-red { color: var(--t-red); } .t-orange { color: var(--t-orange); }
.t-sub { display: flex; gap: 8px; padding-left: 4px; white-space: pre-wrap; }
.t-elbow { color: var(--t-dim); flex: none; width: 1.2em; }
.t-code { background: var(--t-panel); border-radius: 6px; padding: 6px 8px; margin: 4px 0; white-space: pre-wrap; }
.term-inner code { color: var(--t-accent); background: transparent; }
.t-spinner { margin-top: 10px; }
.t-glyph::before { content: "✻"; display: inline-block; animation: glyph 1.2s steps(1) infinite; }
@keyframes glyph { 0% { content: "·"; } 17% { content: "✢"; } 33% { content: "✳"; } 50% { content: "✶"; }
  67% { content: "✻"; } 83% { content: "✽"; } }
@media (prefers-reduced-motion: reduce) { .t-glyph::before { animation: none; } }
.t-diff { margin: 4px 0 4px 1.6em; border: 1px solid var(--t-border); border-radius: 6px; overflow-x: auto; font-size: 12px; }
.t-diff > div { display: flex; white-space: pre; }
.d-no { width: 3.2em; text-align: right; color: var(--t-dim); padding-right: 6px; flex: none; user-select: none; }
.d-sign { width: 1.2em; flex: none; }
.d-add { background: rgba(80, 160, 90, .22); } .d-add .d-sign { color: var(--t-green); }
.d-del { background: rgba(200, 80, 70, .22); } .d-del .d-sign { color: var(--t-red); }
.d-gap { color: var(--t-dim); padding-left: 4.4em; }
#prompt { border: 1px solid var(--t-border) !important; border-radius: 10px !important; background: var(--t-bg) !important; }
#prompt textarea { font-family: "JetBrains Mono", ui-monospace, monospace !important; font-size: 13px;
  background: transparent !important; color: var(--t-text) !important; border: 0 !important; box-shadow: none !important; }
#prompt button.submit-button { background: var(--t-accent) !important; color: #fff !important; }
.statusline { display: flex; flex-wrap: wrap; gap: 4px 14px; font: 12px "JetBrains Mono", ui-monospace, monospace;
  color: var(--t-dim); padding: 4px 2px; }
.statusline span:first-child { color: var(--t-accent); }
#cx-monaco { height: 70vh; border: 1px solid var(--t-border); border-radius: 10px; overflow: hidden; }
#cx-monaco textarea.cx-fallback { width: 100%; height: 100%; background: var(--t-bg); color: var(--t-text);
  font: 13px "JetBrains Mono", ui-monospace, monospace; border: 0; padding: 10px; resize: none; tab-size: 4; }
.cx-hl { background: rgba(111, 191, 115, .18); }
.cx-hl-gutter { border-left: 3px solid var(--t-green); }
.preview-frame { width: 100%; height: 70vh; border: 1px solid var(--t-border); border-radius: 10px; background: #fff; }
.out-empty { height: 30vh; display: grid; place-items: center; color: var(--t-dim); border: 1px dashed var(--t-border);
  border-radius: 10px; font: 13px ui-monospace, monospace; text-align: center; padding: 12px; }
.out-head { font: 12.5px "JetBrains Mono", ui-monospace, monospace; color: var(--t-dim); margin-bottom: 6px; }
.out-ok { color: var(--t-green); } .out-err { color: var(--t-red); }
.out-pre { background: var(--t-panel); color: var(--t-text); border-radius: 8px; padding: 10px 12px; max-height: 62vh;
  overflow: auto; font: 12.5px "JetBrains Mono", ui-monospace, monospace; white-space: pre-wrap; }
#toolbar { gap: 6px !important; align-items: center; }
#toolbar button { min-width: 0 !important; }
#fname input { font-family: "JetBrains Mono", ui-monospace, monospace !important; }
"""

# Monaco dimuat lewat loader AMD-nya. Python mengirim isi editor lewat kotak tersembunyi #cx-sync (JSON), dan
# window.cxGet() dipanggil sebelum setiap perintah untuk mengambil kode terbaru dari editor.
MONACO_HEAD = """
<script>
(function () {
  const SOURCES = __SOURCES__;  // ["gradio-file:/folder/vs" dan/atau URL CDN], dicoba berurutan
  const LANG = { html: "html", python: "python", javascript: "javascript", typescript: "typescript", css: "css",
    json: "json", sql: "sql", shell: "shell", markdown: "markdown", java: "java", go: "go", php: "php", c: "c",
    cpp: "cpp", rust: "rust", plaintext: "plaintext" };
  let editor = null, fallback = null, pending = null, decorations = [], fadeTimer = null, booted = false;
  window.cxGet = function () {
    if (editor) return editor.getValue();
    if (fallback) return fallback.value;
    return pending ? pending.code : "";
  };
  function apply(p) {
    if (fallback) {
      if (fallback.value !== p.code) fallback.value = p.code;
      fallback.readOnly = !!p.busy;
      if (p.busy) fallback.scrollTop = fallback.scrollHeight;
      return;
    }
    const model = editor.getModel();
    monaco.editor.setModelLanguage(model, LANG[p.lang] || "plaintext");
    if (model.getValue() !== p.code) {
      // pushEditOperations menjaga riwayat Ctrl+Z, berbeda dengan setValue
      model.pushEditOperations([], [{ range: model.getFullModelRange(), text: p.code }], () => null);
    }
    editor.updateOptions({ readOnly: !!p.busy });
    const ranges = (p.hl || []).map(([a, b]) => ({ range: new monaco.Range(a, 1, b, 1),
      options: { isWholeLine: true, className: "cx-hl", linesDecorationsClassName: "cx-hl-gutter" } }));
    decorations = editor.deltaDecorations(decorations, ranges);
    clearTimeout(fadeTimer);
    if (ranges.length && !p.busy) fadeTimer = setTimeout(() => { decorations = editor.deltaDecorations(decorations, []); }, 8000);
    if (p.busy && p.follow) editor.revealLine(model.getLineCount());
    else if (ranges.length) editor.revealLineInCenterIfOutsideViewport(ranges[0].range.startLineNumber);
  }
  window.cxApply = function (raw) {
    let p;
    try { p = typeof raw === "string" ? JSON.parse(raw) : raw; } catch (e) { return; }
    if (!p || typeof p.code !== "string") return;
    if (!editor && !fallback) { pending = p; return; }
    apply(p);
  };
  function useFallback(host, reason) {
    if (editor || fallback) return;
    console.warn("Monaco tidak dimuat (" + reason + "), memakai editor teks biasa");
    host.innerHTML = "";
    fallback = document.createElement("textarea");
    fallback.className = "cx-fallback";
    fallback.spellcheck = false;
    fallback.setAttribute("aria-label", "Editor kode");
    host.appendChild(fallback);
    if (pending) apply(pending);
  }
  function resolve(src) {
    if (!src.startsWith("gradio-file:")) return src;
    // URL absolut dari root Gradio: worker Monaco tidak bisa memakai URL relatif
    let root = (window.gradio_config && window.gradio_config.root) || location.href;
    if (!/^https?:/.test(root)) root = new URL(root, location.href).href;
    return new URL("gradio_api/file=" + src.slice(12), (root.endsWith("/") ? root : root + "/")).href;
  }
  function boot() {
    const host = document.getElementById("cx-monaco");
    if (!host) { setTimeout(boot, 200); return; }
    if (booted) return;
    booted = true;
    load(host, 0);
  }
  function load(host, i) {
    if (i >= SOURCES.length) { useFallback(host, "semua sumber gagal"); return; }
    const BASE = resolve(SOURCES[i]);
    const crossOrigin = new URL(BASE).origin !== location.origin;
    // Worker dari domain lain harus lewat data: URL; dari domain sendiri cukup URL absolut
    window.MonacoEnvironment = { getWorkerUrl: (_, label) => crossOrigin ? "data:text/javascript;charset=utf-8," +
      encodeURIComponent("self.MonacoEnvironment={baseUrl:'" + BASE.replace(/vs$/, "") + "'};importScripts('" + BASE +
      "/base/worker/workerMain.js');") : BASE + "/base/worker/workerMain.js#" + label };
    const timer = setTimeout(() => useFallback(host, "waktu habis"), 25000);
    const s = document.createElement("script");
    s.src = BASE + "/loader.js";
    s.onerror = () => { clearTimeout(timer); s.remove(); load(host, i + 1); };
    s.onload = () => {
      window.require.config({ paths: { vs: BASE } });
      window.require(["vs/editor/editor.main"], () => {
        clearTimeout(timer);
        if (fallback) return;
        host.innerHTML = "";
        editor = monaco.editor.create(host, { value: "", language: "html", theme: "vs-dark", automaticLayout: true,
          fontSize: 13, fontFamily: "JetBrains Mono, ui-monospace, Menlo, Consolas, monospace", minimap: { enabled: true },
          scrollBeyondLastLine: false, tabSize: 4, insertSpaces: true, wordWrap: "off", renderWhitespace: "selection",
          bracketPairColorization: { enabled: true }, smoothScrolling: true });
        window.cxEditor = editor;
        if (pending) apply(pending);
      }, (err) => { clearTimeout(timer); useFallback(host, String(err)); });
    };
    document.head.appendChild(s);
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot); else boot();
})();
</script>
"""

FORCE_DARK_JS = "() => { document.body.classList.add('dark'); }"
GET_CODE_JS = "(code) => (window.cxGet ? window.cxGet() : code)"
SYNC_JS = "(payload) => { if (window.cxApply) window.cxApply(payload); }"


def monaco_sources(args):
    """Sumber folder vs Monaco yang dicoba browser berurutan: salinan lokal (disajikan Gradio, diunduh dari npm),
    lalu CDN. Kembalikan (daftar sumber, folder cache untuk allowed_paths)."""
    version = args.monaco_version
    cdn = f"https://cdn.jsdelivr.net/npm/monaco-editor@{version}/min/vs"
    if args.monaco == "cdn":
        return [cdn], None
    cache = Path.home() / ".cache" / "codexia-studio" / f"monaco-{version}"
    vs = cache / "package" / "min" / "vs"
    if not (vs / "loader.js").is_file():
        try:
            print(f"mengunduh Monaco {version} dari npm (sekali saja, ±18 MB) ...", flush=True)
            url = f"https://registry.npmjs.org/monaco-editor/-/monaco-editor-{version}.tgz"
            data = urllib.request.urlopen(url, timeout=120).read()
            with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
                members = [m for m in tar.getmembers() if m.name.startswith("package/min/vs/") and m.isfile()]
                tar.extractall(cache, members=members)
        except Exception as e:
            if args.monaco == "lokal":
                raise SystemExit(f"Monaco gagal diunduh ({e}); pakai --monaco cdn")
            print(f"Monaco gagal diunduh ({e}); memakai CDN {cdn}", flush=True)
            return [cdn], None
    sources = [f"gradio-file:{vs.resolve()}"] + ([cdn] if args.monaco == "auto" else [])
    return sources, str(cache.resolve())


# ---------------------------------------------------------------- aplikasi

def build_app(engine, args):
    import gradio as gr

    model_label = ("demo (model tiruan)" if args.demo else f"{args.base_model} (tanpa adapter)" if base_only(args)
                   else str(args.merged or args.adapter))
    welcome = {"kind": "welcome", "app": args.app_name, "model": model_label, "workdir": str(Path(args.workdir).resolve())}
    studio = Studio(engine, args)

    with gr.Blocks(title=args.app_name, fill_height=True) as demo:
        project_state = gr.State(None)
        with gr.Row(equal_height=False):
            with gr.Column(scale=5, min_width=360):
                term = gr.HTML(render_terminal([welcome]), elem_id="term", padding=False)
                prompt = gr.Textbox(elem_id="prompt", show_label=False, lines=1, max_lines=8, container=False,
                                    placeholder="> Minta kode baru, minta perubahan, atau ketik /bantuan  (Enter kirim)",
                                    submit_btn=True, stop_btn=True, autofocus=True)
                status = gr.HTML(status_line(Project(name=args.file), args, engine))
                with gr.Accordion("Pengaturan model", open=False):
                    edit_mode = gr.Radio([("Patch SEARCH/REPLACE (edit beberapa baris)", "patch"),
                                          ("Bebas (model boleh menulis ulang)", "bebas")], value=args.edit_mode,
                                         label="Cara mengedit kode yang sudah ada")
                    retry = gr.Checkbox(args.retry_failed_patch, label="Kirim ulang blok SEARCH yang tidak cocok (sekali)")
                    thinking = gr.Checkbox(args.thinking, label="Mode berpikir (thinking)",
                                           info="Codexia2 dilatih tanpa mode berpikir.")
                    seed = gr.Number(args.seed, precision=0, label="Seed", info="-1 = acak")
                    timeout = gr.Slider(1, 300, args.run_timeout, step=1, label="Batas waktu Jalankan (detik)")
                    with gr.Tab("Menulis kode baru"):
                        w = [gr.Slider(0, 1.5, args.write_temperature, step=0.05, label="Temperature"),
                             gr.Slider(0.05, 1, args.write_top_p, step=0.01, label="Top-p"),
                             gr.Slider(0, 200, args.write_top_k, step=1, label="Top-k", info="0 = nonaktif"),
                             gr.Slider(0, 0.5, args.write_min_p, step=0.01, label="Min-p"),
                             gr.Slider(1.0, 1.5, args.write_repetition_penalty, step=0.01, label="Repetition penalty"),
                             gr.Slider(256, 16000, args.write_max_new_tokens, step=256, label="Maks. token jawaban")]
                    with gr.Tab("Mengedit"):
                        e = [gr.Slider(0, 1.5, args.edit_temperature, step=0.05, label="Temperature",
                                       info="0 = greedy; disarankan supaya SEARCH menyalin kode persis"),
                             gr.Slider(0.05, 1, args.edit_top_p, step=0.01, label="Top-p"),
                             gr.Slider(0, 200, args.edit_top_k, step=1, label="Top-k"),
                             gr.Slider(0, 0.5, args.edit_min_p, step=0.01, label="Min-p"),
                             gr.Slider(1.0, 1.5, args.edit_repetition_penalty, step=0.01, label="Repetition penalty",
                                       info="1,0 disarankan: penalti menghukum token yang memang harus disalin"),
                             gr.Slider(256, 8192, args.edit_max_new_tokens, step=256, label="Maks. token jawaban")]
            with gr.Column(scale=7, min_width=360):
                with gr.Row(elem_id="toolbar"):
                    fname = gr.Textbox(args.file, show_label=False, container=False, scale=3, elem_id="fname",
                                       max_lines=1, placeholder="nama file, misalnya main.py")
                    run_btn = gr.Button("▶ Jalankan", size="sm", scale=1)
                    fix_btn = gr.Button("🔧 Perbaiki", size="sm", variant="primary", scale=1)
                    undo_btn = gr.Button("↶ Undo", size="sm", scale=1)
                    stop_btn = gr.Button("■ Stop", size="sm", variant="stop", scale=1)
                    download = gr.DownloadButton("⬇", size="sm", visible=False, scale=0)
                with gr.Tabs() as tabs:
                    with gr.Tab("Kode", id="kode"):
                        gr.HTML('<div id="cx-monaco"><div class="out-empty">memuat editor…</div></div>', padding=False)
                    with gr.Tab("Pratinjau", id="pratinjau"):
                        preview = gr.HTML(render_preview(Project()))
                    with gr.Tab("Output", id="output"):
                        output = gr.HTML(render_output(Project()))
        code_box = gr.Textbox("", elem_id="cx-code", elem_classes="cx-hidden", show_label=False, container=False)
        sync = gr.Textbox("", elem_id="cx-sync", elem_classes="cx-hidden", show_label=False, container=False)

        outputs = [term, sync, preview, output, status, project_state, download, fname, tabs]
        settings_in = [edit_mode, retry, thinking, seed, timeout, *w, *e]

        def new_project():
            return Project(name=args.file, events=[welcome])

        def view(project, busy=None, live=None, tab=None):
            """Nilai semua komponen. live = kode yang sedang ditulis model (editor ikut berubah selagi streaming)."""
            project.rev += 1
            code, follow, hl = live if live is not None else (project.code, False, project.highlight)
            payload = {"rev": project.rev, "code": code, "lang": lang_of(project.name)[0], "hl": hl,
                       "busy": busy is not None, "follow": follow}
            path = Path(args.workdir) / project.name
            return (render_terminal(project.events, busy), json.dumps(payload),
                    gr.update() if busy else render_preview(project), render_output(project),
                    status_line(project, args, engine, busy is not None), project,
                    gr.update(value=str(path), visible=True) if project.code and path.is_file() else gr.update(visible=False),
                    project.name, gr.Tabs(selected=tab) if tab else gr.update())

        def drive(project, steps):
            try:
                for item in steps:
                    if isinstance(item, tuple) and item and isinstance(item[0], tuple):
                        yield view(project, item[0], item[1])
                    elif isinstance(item, str):
                        yield view(project, tab=item)
            except Exception as ex:  # tampilkan di transkrip, jangan putuskan sesi
                project.events.append(tool("Error", type(ex).__name__, "error", [("t-red", str(ex)[:600])]))
            project.highlight = project.highlight or []
            yield view(project)

        def handle(text, code, name, project, edit_mode, retry, thinking, seed, timeout, *values):
            project = project or new_project()
            studio.user_stop.clear()
            args.run_timeout = int(timeout)
            ws = dict(settings_from(values[:6]), seed=int(seed))
            es = dict(settings_from(values[6:]), seed=int(seed))
            name = (name or "").strip() or project.name
            if Path(name).name != name or name.startswith("."):
                project.events.append({"kind": "text", "text": "Nama file harus tanpa folder, misalnya `main.py`."})
                name = project.name
            if name != project.name:
                project.name = name
                if project.code:
                    save_file(project, args.workdir)
            # Kode kosong dari editor diabaikan jika proyek berisi kode (editor belum siap); kosongkan lewat /reset.
            if code is not None and code != project.code and code.strip():
                project.set_code(code, args.workdir, highlight=[])  # perubahan manual di editor
                project.events.append(tool("Edit", f"{project.name} oleh Anda", "ok", [("t-dim", "perubahan di editor dipakai")]))
            text = (text or "").strip()
            if not text:
                yield view(project)
                return
            project.events.append({"kind": "user", "text": text})
            command, _, rest = text.partition(" ")
            command = command.lower() if text.startswith("/") else ""
            patch = edit_mode == "patch"

            def steps():
                if command in ("/bantuan", "/help"):
                    project.events.append({"kind": "text", "text": HELP})
                elif command in ("/reset", "/clear"):
                    if project.code:
                        project.versions.append((project.name, project.code))
                    project.events[:] = [welcome]
                    project.code, project.highlight, project.last_run = "", [], {}
                elif command == "/undo":
                    if not project.versions:
                        project.events.append({"kind": "text", "text": "Tidak ada versi sebelumnya."})
                        return
                    old_name, old_code = project.versions.pop()
                    rows = diff_rows(project.code, old_code)
                    project.highlight = changed_ranges(project.code, old_code)
                    project.name, project.code = old_name, old_code
                    save_file(project, args.workdir)
                    project.events.append(tool("Undo", project.name, "ok",
                                               [("", f"kembali ke versi sebelumnya: +{rows[1]} / −{rows[2]} baris")], diff=rows))
                elif command == "/file":
                    new = rest.strip()
                    if new and Path(new).name == new:
                        project.name = new
                        if project.code:
                            save_file(project, args.workdir)
                        project.events.append(tool("File", new, "ok", [("", f"bahasa: {lang_of(new)[0]}")]))
                    else:
                        project.events.append({"kind": "text", "text": "Contoh: `/file main.py`"})
                elif command == "/jalankan":
                    result = studio.run(project)
                    yield "output" if result else ("pratinjau" if project.name.endswith((".html", ".htm")) else "output")
                elif command == "/perbaiki":
                    if not project.code.strip():
                        project.events.append({"kind": "text", "text": "Editor masih kosong."})
                        return
                    error_out = ""
                    if project.last_run and not project.last_run["ok"]:
                        error_out = project.last_run["out"]
                    if not rest.strip() and not error_out:
                        project.events.append({"kind": "text", "text": "Tidak ada error dari Jalankan. Jelaskan masalahnya: "
                                                                       "`/perbaiki <keluhan>`."})
                        return
                    complaint = rest.strip() or "Program ini error saat dijalankan. Tolong cari penyebabnya dan perbaiki."
                    yield "kode"
                    changed = yield from studio.edit(project, complaint, es, thinking, patch, retry, error_out)
                    if changed and project.last_run and runnable(project.name):
                        result = studio.run(project)  # jalankan ulang untuk membuktikan perbaikannya
                        if result:
                            yield "output"
                elif command and command != "/baru":
                    project.events.append({"kind": "text", "text": f"Perintah `{command}` tidak dikenal.\n\n{HELP}"})
                elif command == "/baru" or not project.code.strip():
                    request = rest if command == "/baru" else text
                    if not request.strip():
                        project.events.append({"kind": "text", "text": "Tulis permintaannya: `/baru <permintaan>`."})
                        return
                    yield "kode"  # kode mengalir ke editor selagi ditulis
                    yield from studio.write(project, request, ws, thinking)
                else:
                    yield "kode"
                    yield from studio.edit(project, text, es, thinking, patch, retry)

            yield from drive(project, steps())

        def command_button(command):
            def run(code, name, project, *settings):
                yield from handle(command, code, name, project, *settings)
            return run

        def stop():
            studio.user_stop.set()
            engine.stop()

        pending = gr.State("")
        # 1) Ambil teks dan kode terbaru dari Monaco, kosongkan kotak input; 2) jalankan agen.
        submitted = prompt.submit(lambda t, c: ("", t, c), [prompt, code_box], [prompt, pending, code_box], queue=False,
                                  js="(t, c) => [t, window.cxGet ? window.cxGet() : c]")
        runs = [submitted.then(handle, [pending, code_box, fname, project_state, *settings_in], outputs,
                               concurrency_limit=1, concurrency_id="gpu")]
        for btn, command in ((run_btn, "/jalankan"), (fix_btn, "/perbaiki"), (undo_btn, "/undo")):
            grabbed = btn.click(lambda c: c, code_box, code_box, js=GET_CODE_JS, queue=False)
            runs.append(grabbed.then(command_button(command), [code_box, fname, project_state, *settings_in], outputs,
                                     concurrency_limit=1, concurrency_id="gpu"))
        prompt.stop(stop, None, None, cancels=runs, queue=False)
        stop_btn.click(stop, None, None, cancels=runs, queue=False)
        sync.change(None, sync, None, js=SYNC_JS, queue=False, show_progress="hidden")
        demo.load(lambda: view(new_project()), None, outputs, js=FORCE_DARK_JS)
    return demo


def launch_kwargs(gr, base_cache, args):
    """Gradio 6 menerima head/css/theme di launch(); Gradio 5 di Blocks()."""
    import inspect
    allowed = [str(Path(args.workdir).resolve())] + ([base_cache] if base_cache else [])
    auth = tuple(args.auth.split(":", 1)) if args.auth else None
    kw = dict(share=args.share, auth=auth, server_port=args.port, show_error=True, debug=not IN_NOTEBOOK,
              allowed_paths=allowed, height=950)
    return kw, "head" in inspect.signature(gr.Blocks.launch).parameters


def main():
    args = parse_args()
    import gradio as gr

    gr.close_all()  # tutup tampilan lama jika sel dijalankan ulang
    Path(args.workdir).mkdir(parents=True, exist_ok=True)
    sources, cache = monaco_sources(args)
    head = MONACO_HEAD.replace("__SOURCES__", json.dumps(sources))
    theme = gr.themes.Base(primary_hue="orange", neutral_hue="stone",
                           font_mono=[gr.themes.GoogleFont("JetBrains Mono"), "ui-monospace", "monospace"])
    engine = Engine(args)
    kw, new_api = launch_kwargs(gr, cache, args)
    if new_api:
        demo = build_app(engine, args)
        kw.update(head=head, css=CSS, theme=theme)
    else:
        original = gr.Blocks.__init__

        def patched(self, *a, **k):  # Gradio 5: head/css/theme diteruskan ke Blocks()
            k.setdefault("head", head), k.setdefault("css", CSS), k.setdefault("theme", theme)
            original(self, *a, **k)

        gr.Blocks.__init__ = patched
        try:
            demo = build_app(engine, args)
        finally:
            gr.Blocks.__init__ = original
    demo.queue(default_concurrency_limit=1).launch(**kw)
    return demo


if __name__ == "__main__":
    main()
