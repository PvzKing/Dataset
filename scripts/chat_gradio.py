"""Chatbot Gradio untuk model hasil fine-tuning (Qwen3.5-4B + adapter LoRA), dengan pengaturan lengkap.

Fitur: streaming, mode berpikir, preset instruksi sistem, sampling lengkap, perbandingan adapter vs model dasar tanpa
memuat ulang, ulangi/batalkan/edit pesan, tombol stop, pratinjau website dari blok ```html, unduh HTML dan percakapan,
serta statistik token per detik.

Cara memakai di Google Colab (GPU T4 cukup):

    Sel 1:  !pip install --upgrade unsloth "gradio>=6.30,<7"
    Sel 2:  from google.colab import drive; drive.mount("/content/drive")
            !wget -q -O /content/chat_gradio.py https://raw.githubusercontent.com/PvzKing/Dataset/main/scripts/chat_gradio.py
    Sel 3:  %run /content/chat_gradio.py

Tampilan chat muncul di bawah sel 3. Opsi CONFIG bisa diganti lewat argumen, misalnya:

    %run /content/chat_gradio.py --adapter /content/drive/MyDrive/finetune-id/qwen3.5-4b-own-4bit-lanjut/lora-adapter
    %run /content/chat_gradio.py --adapter none        # model dasar saja
    %run /content/chat_gradio.py --demo                # coba tampilan tanpa GPU dan tanpa model

Di luar Colab: python chat_gradio.py, lalu buka http://localhost:7860.
"""
import argparse
import builtins
import contextlib
import html
import json
import re
import sys
import tempfile
import threading
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

# ======================================================== CONFIG: ubah di sini ========================================
CONFIG = {
    "adapter": "auto",              # "auto" = adapter terbaru di folder out, path folder lora-adapter, atau "none"
    "out": "/content/drive/MyDrive/finetune-id",  # folder hasil training (dipakai saat adapter = "auto")
    "base_model": "unsloth/Qwen3.5-4B",           # dipakai jika adapter = "none"
    "load_in_4bit": None,           # None = otomatis: 4-bit di GPU tanpa bf16 asli (T4), selain itu 16-bit
    "max_seq_len": 8192,            # panjang konteks maksimum (riwayat + jawaban)
    "app_name": "Asisten Nusantara",
    "timezone": "Asia/Jakarta",     # untuk sapaan pagi/siang/sore/malam
    "share": False,                 # True = link publik *.gradio.live (wajib pakai auth)
    "auth": None,                   # "user:sandi"; wajib jika share = True
    "port": None,                   # None = port kosong pertama mulai 7860
    "demo": False,                  # True = jawaban tiruan, untuk mencoba tampilan tanpa GPU
}
# ======================================================================================================================

SYSTEM_PRESETS = {
    "Tanpa instruksi (seperti data training)": "",
    "Asisten umum": "Kamu asisten berbahasa Indonesia yang membantu, jujur, dan ringkas. Jika tidak yakin, katakan "
                    "tidak yakin daripada mengarang.",
    "Web developer (satu file HTML)": "Kamu web developer senior. Buat website lengkap dalam satu file HTML dengan CSS "
                                      "dan JavaScript inline, responsif, aksesibel, dan tanpa library eksternal. Setelah "
                                      "kode, tulis catatan singkat dan bagian **Cek kebutuhan** yang memetakan setiap "
                                      "permintaan ke bagian kode yang mengerjakannya.",
    "Analisis hukum Indonesia": "Kamu membantu analisis hukum Indonesia. Pisahkan fakta, isu hukum, dasar hukum, "
                                "analisis, dan kesimpulan. Sebut peraturan beserta pasal dan ayat hanya jika kamu yakin; "
                                "jika tidak yakin nomornya, katakan demikian. Ingatkan bahwa jawaban ini bukan nasihat "
                                "hukum dan perlu diperiksa ke sumber resmi.",
    "Kustom": None,
}

# Rekomendasi sampling Qwen3/Qwen3.5: (temperature, top_p, top_k, min_p)
QWEN_SAMPLING = {False: (0.7, 0.8, 20, 0.0), True: (0.6, 0.95, 20, 0.0)}

EXAMPLES = [
    "Buatkan landing page satu file HTML untuk bengkel motor \"Gaspol Motor\" di Yogyakarta: hero dengan tombol booking, "
    "daftar layanan dan harga, jam buka, dan form booking dengan validasi. Responsif, tanpa library eksternal.",
    "Buat aplikasi absensi kelas dalam satu file HTML: tambah siswa, tandai hadir/izin/sakit/alfa per tanggal, rekap "
    "persentase, simpan di localStorage, dan ekspor CSV.",
    "Jelaskan perbedaan wanprestasi dan perbuatan melawan hukum, lengkap dengan dasar hukumnya.",
    "Jelaskan konsep big-O dengan analogi sehari-hari.",
]

IN_NOTEBOOK = "ipykernel" in sys.modules
EXPORT_DIR = Path(tempfile.mkdtemp(prefix="chat_gradio_"))


# ---------------------------------------------------------------- argumen

def parse_args():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--adapter", help='folder lora-adapter, "auto", atau "none"')
    parser.add_argument("--out", help="folder hasil training untuk adapter auto")
    parser.add_argument("--base-model")
    parser.add_argument("--load-in-4bit", action=argparse.BooleanOptionalAction, default=None)
    parser.add_argument("--max-seq-len", type=int)
    parser.add_argument("--app-name")
    parser.add_argument("--timezone")
    parser.add_argument("--share", action="store_true", default=None, help="buat link publik (wajib --auth)")
    parser.add_argument("--auth", help="user:sandi")
    parser.add_argument("--port", type=int)
    parser.add_argument("--demo", action="store_true", default=None, help="jawaban tiruan tanpa GPU")
    # Saat ditempel ke sel notebook, sys.argv berisi argumen kernel Jupyter: abaikan yang tidak dikenal.
    args, _ = parser.parse_known_args(sys.argv[1:])
    for key, value in CONFIG.items():
        if getattr(args, key, None) is None:
            setattr(args, key, value)
    if args.share and not args.auth:
        raise SystemExit("--share membuat chat bisa diakses siapa pun yang tahu link-nya: tambahkan --auth user:sandi")
    return args


# ---------------------------------------------------------------- model

def find_adapter(args):
    """Kembalikan folder adapter yang dipakai, atau None untuk model dasar."""
    if args.adapter == "none":
        return None
    if args.adapter != "auto":
        folder = Path(args.adapter)
        if not (folder / "adapter_config.json").is_file():
            raise SystemExit(f"bukan folder adapter LoRA (tidak ada adapter_config.json): {folder}")
        return folder
    found = sorted(Path(args.out).glob("*/lora-adapter/adapter_model.safetensors"), key=lambda p: p.stat().st_mtime)
    if not found:
        print(f"tidak ada adapter di {args.out}, memakai model dasar {args.base_model}", flush=True)
        return None
    return found[-1].parent


def native_bf16(torch):
    """bf16 asli (Ampere ke atas). torch.cuda.is_bf16_supported() bernilai True juga di T4 karena emulasi."""
    return torch.cuda.is_available() and torch.cuda.get_device_properties(0).major >= 8


class Engine:
    """Model, tokenizer, dan generasi streaming. Satu generasi berjalan pada satu waktu."""

    def __init__(self, args):
        self.args = args
        self.adapter = None
        self.lock = threading.Lock()
        self.current_stop = threading.Event()
        if args.demo:
            self.info = "**Mode demo**: jawaban tiruan, tanpa model."
            return
        import torch
        from unsloth import FastLanguageModel

        if args.load_in_4bit is None:
            args.load_in_4bit = not native_bf16(torch)
        self.adapter = find_adapter(args)
        name = str(self.adapter or args.base_model)
        print(f"memuat {name} (4-bit: {args.load_in_4bit}) ...", flush=True)
        load = dict(max_seq_length=args.max_seq_len, dtype=None, load_in_4bit=args.load_in_4bit,
                    load_in_16bit=not args.load_in_4bit)
        try:
            model, tokenizer = FastLanguageModel.from_pretrained(model_name=name, **load)
        except Exception as e:
            if not self.adapter:
                raise
            # Cadangan: muat model dasar lalu pasang adapter dengan PEFT.
            base = json.loads((self.adapter / "adapter_config.json").read_text()).get("base_model_name_or_path")
            print(f"memuat adapter lewat Unsloth gagal ({e}); mencoba {base} + PEFT", flush=True)
            from peft import PeftModel
            model, tokenizer = FastLanguageModel.from_pretrained(model_name=base or args.base_model, **load)
            model = PeftModel.from_pretrained(model, str(self.adapter))
        FastLanguageModel.for_inference(model)
        self.model = model
        self.tokenizer = getattr(tokenizer, "tokenizer", tokenizer)  # processor multimodal -> tokenizer teks
        self.torch = torch
        gpu = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU"
        self.info = (f"**Model:** `{args.base_model if not self.adapter else self.adapter}`  \n"
                     f"**GPU:** {gpu} · {'4-bit' if args.load_in_4bit else '16-bit'} · konteks {args.max_seq_len:,} token")

    def stop(self):
        """Hentikan generasi yang sedang berjalan (tombol stop atau percakapan baru)."""
        self.current_stop.set()

    @property
    def has_adapter(self):
        return self.adapter is not None

    def count_tokens(self, text):
        if self.args.demo:
            return len(text) // 4
        return len(self.tokenizer(text, add_special_tokens=False)["input_ids"])

    def render(self, messages, thinking):
        if self.args.demo:
            return "\n".join(m["content"] for m in messages)
        return self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True,
                                                  enable_thinking=thinking)

    def stream(self, prompt, settings, use_adapter, stop_event):
        """Hasilkan potongan teks jawaban satu per satu."""
        if self.args.demo:
            yield from demo_stream(prompt, settings, stop_event)
            return
        from transformers import StoppingCriteria, StoppingCriteriaList, TextIteratorStreamer

        class StopOnEvent(StoppingCriteria):
            def __call__(self, input_ids, scores, **kwargs):
                return stop_event.is_set()

        torch = self.torch
        inputs = self.tokenizer(prompt, return_tensors="pt", add_special_tokens=False).to(self.model.device)
        # Token khusus dibiarkan supaya </think> tetap terlihat, lalu token <|...|> dibuang di split_thinking.
        streamer = TextIteratorStreamer(self.tokenizer, skip_prompt=True, skip_special_tokens=False)
        sample = settings["temperature"] > 0
        kwargs = dict(**inputs, streamer=streamer, max_new_tokens=settings["max_new_tokens"], do_sample=sample,
                      repetition_penalty=settings["repetition_penalty"],
                      stopping_criteria=StoppingCriteriaList([StopOnEvent()]))
        if sample:
            kwargs.update(temperature=settings["temperature"], top_p=settings["top_p"], top_k=settings["top_k"],
                          min_p=settings["min_p"])
        if settings["seed"] >= 0:
            torch.manual_seed(settings["seed"])
        can_disable = self.has_adapter and hasattr(self.model, "disable_adapter")
        adapter_off = self.model.disable_adapter() if can_disable and not use_adapter else contextlib.nullcontext()
        error = []

        def run():
            try:
                with adapter_off, torch.inference_mode():
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


def demo_stream(prompt, settings, stop_event):
    thinking = "Pengguna meminta contoh. Aku jawab singkat dengan satu blok HTML supaya pratinjau bisa dicoba.</think>"
    answer = ("Berikut contoh halaman kecil untuk mencoba **pratinjau website**.\n\n```html\n<!DOCTYPE html>\n"
              "<html lang=\"id\"><head><meta charset=\"UTF-8\"><title>Demo</title><style>body{font-family:system-ui;"
              "display:grid;place-items:center;height:100vh;margin:0;background:#f5f4ed}button{padding:.8rem 1.4rem;"
              "border:0;border-radius:10px;background:#c96442;color:#fff;font-size:1rem}</style></head><body>"
              "<button id=\"b\">Klik saya</button><script>let n=Number(localStorage.getItem('n')||0);"
              "const b=document.getElementById('b');b.onclick=()=>{n++;localStorage.setItem('n',n);"
              "b.textContent=`Diklik ${n} kali`};</script></body></html>\n```\n\n"
              "Catatan:\n- Tombol → menghitung klik dan menyimpannya di `localStorage`.\n\n"
              "| Pengaturan | Nilai |\n|---|---|\n"
              f"| temperature | {settings['temperature']} |\n| max token | {settings['max_new_tokens']} |\n")
    text = (thinking if settings["thinking"] else "") + answer
    for i in range(0, len(text), 6):
        if stop_event.is_set():
            return
        time.sleep(0.01)
        yield text[i:i + 6]


# ---------------------------------------------------------------- percakapan

def text_of(content):
    """Isi pesan Gradio bisa berupa string atau daftar potongan {'type': 'text', 'text': ...}."""
    if isinstance(content, str):
        return content
    if isinstance(content, dict):
        return content.get("text", "")
    return "".join(part.get("text", "") for part in content or [] if isinstance(part, dict))


def is_thought(message):
    return bool((message.get("metadata") or {}).get("title"))


def to_model_messages(history, system):
    """Riwayat Gradio -> pesan untuk model: tanpa proses berpikir, pesan berurutan dari role yang sama digabung."""
    messages = [{"role": "system", "content": system}] if system.strip() else []
    for m in history:
        if is_thought(m):
            continue
        text = text_of(m["content"])
        if messages and messages[-1]["role"] == m["role"]:
            messages[-1]["content"] += "\n\n" + text
        else:
            messages.append({"role": m["role"], "content": text})
    return messages


def fit_context(engine, messages, thinking, max_new_tokens):
    """Buang pasangan tanya-jawab terlama sampai prompt + jawaban muat di konteks. Kembalikan (prompt, n_token, dibuang)."""
    limit = engine.args.max_seq_len - max_new_tokens
    dropped = 0
    while True:
        prompt = engine.render(messages, thinking)
        n = engine.count_tokens(prompt)
        first = 1 if messages and messages[0]["role"] == "system" else 0
        if n <= limit or len(messages) - first <= 1:
            return prompt, n, dropped
        del messages[first:first + 2]
        dropped += 1


SPECIAL_TOKEN = re.compile(r"<\|[a-z_]+\|>")


def split_thinking(raw, thinking):
    """Pisahkan proses berpikir dan jawaban. Kembalikan (pikiran, jawaban, pikiran_selesai)."""
    raw = SPECIAL_TOKEN.sub("", raw)
    if not thinking:
        return "", raw, True
    raw = raw.removeprefix("<think>").lstrip("\n")
    if "</think>" in raw:
        thought, answer = raw.split("</think>", 1)
        return thought.strip(), answer.lstrip("\n"), True
    return raw, "", False


def last_html(history):
    for m in reversed(history):
        if m["role"] == "assistant" and not is_thought(m):
            blocks = re.findall(r"```html\s*\n(.*?)(?:```|$)", text_of(m["content"]), re.S)
            if blocks:
                return blocks[-1].strip()
    return None


# localStorage tidak tersedia di iframe sandbox tanpa allow-same-origin; ganti dengan penyimpanan di memori supaya
# aplikasi buatan model tetap jalan, tanpa memberi iframe akses ke halaman chat.
STORAGE_SHIM = ("<script>(()=>{try{window.localStorage.length}catch(e){const mk=()=>{const m=new Map();return{"
                "getItem:k=>m.has(String(k))?m.get(String(k)):null,setItem:(k,v)=>m.set(String(k),String(v)),"
                "removeItem:k=>m.delete(String(k)),clear:()=>m.clear(),key:i=>[...m.keys()][i]??null,"
                "get length(){return m.size}}};for(const n of['localStorage','sessionStorage'])"
                "Object.defineProperty(window,n,{value:mk(),configurable:true})}})()</script>")


def preview_html(page):
    if not page:
        return '<div class="preview-empty">Pratinjau muncul di sini saat jawaban berisi kode HTML.</div>'
    doc = STORAGE_SHIM + page
    return (f'<iframe class="preview-frame" title="Pratinjau website" '
            f'sandbox="allow-scripts allow-forms allow-modals allow-downloads allow-popups" '
            f'srcdoc="{html.escape(doc, quote=True)}"></iframe>')


def export_files(history):
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    md, data = [], []
    for m in history:
        text = text_of(m["content"])
        if is_thought(m):
            md.append(f"<details><summary>Proses berpikir</summary>\n\n{text}\n\n</details>\n")
            continue
        md.append(f"### {'Anda' if m['role'] == 'user' else 'Asisten'}\n\n{text}\n")
        data.append({"role": m["role"], "content": text})
    md_path = EXPORT_DIR / f"percakapan-{stamp}.md"
    md_path.write_text("\n".join(md), encoding="utf-8")
    json_path = EXPORT_DIR / f"percakapan-{stamp}.json"
    json_path.write_text(json.dumps({"messages": data}, ensure_ascii=False, indent=1), encoding="utf-8")
    return [str(md_path), str(json_path)]


def greeting(args):
    hour = datetime.now(ZoneInfo(args.timezone)).hour
    part = "pagi" if 4 <= hour < 11 else "siang" if hour < 15 else "sore" if hour < 18 else "malam"
    return f"Selamat {part}"


# ---------------------------------------------------------------- tampilan

THEME_FONTS = ("Inter", "Source Serif 4")

CSS = """
:root, .light {
  --cc-bg: #f5f4ed; --cc-sidebar: #efede4; --cc-surface: #ffffff; --cc-user: #e9e6dc; --cc-text: #2b2a26;
  --cc-muted: #6f6c62; --cc-border: #dedad0; --cc-accent: #c96442; --cc-accent-hover: #b4553a; --cc-code: #f0eee6;
}
.dark {
  --cc-bg: #262624; --cc-sidebar: #1f1e1d; --cc-surface: #30302e; --cc-user: #141413; --cc-text: #ecebe6;
  --cc-muted: #a6a39a; --cc-border: #3e3d39; --cc-accent: #d97757; --cc-accent-hover: #e08a6e; --cc-code: #1f1e1d;
}
body, gradio-app, .gradio-container { background: var(--cc-bg) !important; color: var(--cc-text); }
.gradio-container { max-width: 100% !important; padding: 0 !important; }
footer { display: none !important; }

/* sidebar */
.sidebar { background: var(--cc-sidebar) !important; border-right: 1px solid var(--cc-border) !important; }
.brand { display: flex; align-items: center; gap: .6rem; padding: .25rem 0 .75rem; }
.brand-mark { width: 30px; height: 30px; border-radius: 9px; background: var(--cc-accent); color: #fff;
  display: grid; place-items: center; font-family: "Source Serif 4", Georgia, serif; font-weight: 600; font-size: 17px; }
.brand-name { font-family: "Source Serif 4", Georgia, serif; font-size: 1.15rem; font-weight: 600; color: var(--cc-text); }

/* kolom chat */
#chat-col { max-width: 820px; margin: 0 auto; width: 100%; padding: 0 16px; }
#chatbot { background: transparent !important; border: 0 !important; box-shadow: none !important; }
#chatbot .message-row { background: transparent !important; }
#chatbot .message.user, #chatbot .message.user .message-content {
  background: var(--cc-user) !important; border: 0 !important; border-radius: 16px !important; color: var(--cc-text); }
#chatbot .bot-row .message, #chatbot .message.bot { background: transparent !important; border: 0 !important;
  box-shadow: none !important; max-width: 100% !important; width: 100%; padding-left: 0 !important; }
#chatbot .bot-row .flex-wrap, #chatbot .bot-row .role { max-width: 100% !important; width: 100%; }
#chatbot .message.bot .message-content, #chatbot .message.bot .prose, #chatbot .message.bot .md {
  font-family: "Source Serif 4", Georgia, serif !important; font-size: 1.06rem; line-height: 1.72; color: var(--cc-text); }
#chatbot .message.bot .prose h1, #chatbot .message.bot .prose h2, #chatbot .message.bot .prose h3 {
  font-family: "Source Serif 4", Georgia, serif !important; color: var(--cc-text); }
#chatbot .icon-button-wrapper, #chatbot .icon-button { background: transparent !important; border-color: transparent !important; }
#chatbot .message.bot table { font-family: Inter, system-ui, sans-serif; font-size: .92rem; }
#chatbot pre, #chatbot code { background: var(--cc-code) !important; border-radius: 8px; }
#chatbot .placeholder-content, #chatbot .placeholder { color: var(--cc-text); }
.hello { text-align: center; padding-top: 12vh; }
.hello .mark { width: 44px; height: 44px; border-radius: 12px; background: var(--cc-accent); color: #fff;
  display: inline-grid; place-items: center; font-family: "Source Serif 4", Georgia, serif; font-size: 24px; }
.hello h1 { font-family: "Source Serif 4", Georgia, serif; font-weight: 400; font-size: 2.3rem; margin: .8rem 0 .3rem;
  color: var(--cc-text); }
.hello p { color: var(--cc-muted); margin: 0; }

/* kotak ketik */
#composer { background: var(--cc-surface) !important; border: 1px solid var(--cc-border) !important;
  border-radius: 18px !important; box-shadow: 0 4px 18px rgba(0,0,0,.06) !important; padding: 6px 8px !important; }
#composer textarea { background: transparent !important; border: 0 !important; box-shadow: none !important;
  font-size: 1rem; color: var(--cc-text); }
#composer button.submit-button, #composer .submit-button { background: var(--cc-accent) !important;
  border-radius: 10px !important; color: #fff !important; }
#composer button.submit-button:hover { background: var(--cc-accent-hover) !important; }
.stats, .stats * { font-size: .78rem !important; color: var(--cc-muted) !important; text-align: center; }
.disclaimer, .disclaimer * { font-size: .74rem !important; color: var(--cc-muted) !important; text-align: center; }
.model-info, .model-info * { font-size: .8rem !important; color: var(--cc-muted) !important; }

/* pratinjau */
#preview-col { border-left: 1px solid var(--cc-border); padding: 0 12px !important; }
.preview-frame { width: 100%; height: 72vh; border: 1px solid var(--cc-border); border-radius: 12px; background: #fff; }
.preview-empty { height: 72vh; display: grid; place-items: center; text-align: center; color: var(--cc-muted);
  border: 1px dashed var(--cc-border); border-radius: 12px; padding: 1rem; }

/* tombol */
.cc-btn { border-radius: 10px !important; }
.cc-primary { background: var(--cc-accent) !important; color: #fff !important; border: 0 !important; }
.cc-primary:hover { background: var(--cc-accent-hover) !important; }
"""

TOGGLE_DARK_JS = "() => { document.body.classList.toggle('dark'); }"
# Di layar sempit sidebar menutupi chat: tutup otomatis saat halaman dibuka.
CLOSE_SIDEBAR_ON_PHONE_JS = """() => { if (window.innerWidth < 768) {
  const b = document.querySelector('.sidebar.open .toggle-button'); if (b) b.click(); } }"""


def build_theme(gr):
    accent = gr.themes.Color(c50="#fbf1ec", c100="#f6dfd4", c200="#eebfaa", c300="#e39d80", c400="#d97757",
                             c500="#c96442", c600="#b4553a", c700="#944530", c800="#743728", c900="#552920",
                             c950="#3a1c16", name="terracotta")
    stone = gr.themes.Color(c50="#faf9f5", c100="#f5f4ed", c200="#e9e6dc", c300="#dedad0", c400="#b7b3a7",
                            c500="#8f8b80", c600="#6f6c62", c700="#3e3d39", c800="#30302e", c900="#262624",
                            c950="#1f1e1d", name="stone_warm")
    theme = gr.themes.Base(
        primary_hue=accent, secondary_hue=accent, neutral_hue=stone, radius_size=gr.themes.sizes.radius_lg,
        font=[gr.themes.GoogleFont(THEME_FONTS[0]), "system-ui", "sans-serif"],
        font_mono=[gr.themes.GoogleFont("JetBrains Mono"), "ui-monospace", "monospace"],
    )
    return theme.set(
        body_background_fill="#f5f4ed", body_background_fill_dark="#262624",
        body_text_color="#2b2a26", body_text_color_dark="#ecebe6",
        background_fill_primary="#ffffff", background_fill_primary_dark="#30302e",
        background_fill_secondary="#efede4", background_fill_secondary_dark="#1f1e1d",
        block_background_fill="#faf9f5", block_background_fill_dark="#2b2b29",
        block_border_color="#dedad0", block_border_color_dark="#3e3d39",
        input_background_fill="#ffffff", input_background_fill_dark="#30302e",
        button_primary_background_fill="#c96442", button_primary_background_fill_hover="#b4553a",
        button_primary_background_fill_dark="#d97757", button_primary_text_color="#ffffff",
        slider_color="#c96442", slider_color_dark="#d97757",
        checkbox_background_color_selected="#c96442", checkbox_background_color_selected_dark="#d97757",
    )


def build_app(engine, args):
    import gradio as gr

    initial = args.app_name[:1].upper()
    hello = (f'<div class="hello"><div class="mark">{html.escape(initial)}</div>'
             f'<h1>{greeting(args)}</h1><p>Ada yang bisa dibantu hari ini?</p></div>')

    with gr.Blocks(title=args.app_name, fill_height=True) as demo:
        with gr.Sidebar(open=not IN_NOTEBOOK, width=330, elem_classes="sidebar"):
            gr.HTML(f'<div class="brand"><div class="brand-mark">{html.escape(initial)}</div>'
                    f'<div class="brand-name">{html.escape(args.app_name)}</div></div>')
            new_chat = gr.Button("＋  Percakapan baru", elem_classes=["cc-btn", "cc-primary"])
            with gr.Accordion("Model", open=True):
                use_adapter = gr.Radio(["Fine-tune (adapter)", "Model dasar"], value="Fine-tune (adapter)",
                                       label="Bobot yang dipakai", interactive=engine.has_adapter or args.demo,
                                       info="Bandingkan hasil fine-tune dengan model dasar tanpa memuat ulang.")
                thinking = gr.Checkbox(False, label="Mode berpikir (thinking)",
                                       info="Model dilatih tanpa mode berpikir; aktifkan untuk eksperimen.")
                gr.Markdown(engine.info, elem_classes="model-info")
            with gr.Accordion("Instruksi sistem", open=False):
                preset = gr.Dropdown(list(SYSTEM_PRESETS), value=next(iter(SYSTEM_PRESETS)), label="Preset")
                system = gr.Textbox("", lines=5, label="Isi instruksi", placeholder="Kosong = tanpa instruksi sistem")
            with gr.Accordion("Sampling", open=False):
                temperature = gr.Slider(0, 2, 0.7, step=0.05, label="Temperature", info="0 = deterministik (greedy)")
                top_p = gr.Slider(0.05, 1, 0.8, step=0.01, label="Top-p")
                top_k = gr.Slider(0, 200, 20, step=1, label="Top-k", info="0 = nonaktif")
                min_p = gr.Slider(0, 0.5, 0.0, step=0.01, label="Min-p")
                repetition_penalty = gr.Slider(1.0, 1.5, 1.05, step=0.01, label="Repetition penalty")
                seed = gr.Number(-1, precision=0, label="Seed", info="-1 = acak")
                recommended = gr.Button("Pakai rekomendasi Qwen", size="sm", elem_classes="cc-btn")
            with gr.Accordion("Panjang & konteks", open=False):
                max_new_tokens = gr.Slider(64, 8192, 6000, step=64, label="Maks. token jawaban",
                                           info="Website satu file butuh ±4.000–6.000 token")
                gr.Markdown(f"Konteks total {args.max_seq_len:,} token. Riwayat terlama dibuang otomatis jika "
                            "tidak muat.", elem_classes="model-info")
            with gr.Accordion("Tampilan & ekspor", open=False):
                show_preview = gr.Checkbox(True, label="Panel pratinjau website")
                dark = gr.Button("🌓  Mode gelap/terang", size="sm", elem_classes="cc-btn")
                export = gr.Files(label="Unduh percakapan (.md / .json)", interactive=False)

        with gr.Row(equal_height=False):
            with gr.Column(scale=3, elem_id="chat-col"):
                chatbot = gr.Chatbot(
                    elem_id="chatbot", show_label=False, layout="bubble", placeholder=hello, editable="user",
                    buttons=["copy", "copy_all"], height="74vh", autoscroll=True,
                    examples=[{"text": e} for e in EXAMPLES], group_consecutive_messages=False,
                    latex_delimiters=[{"left": "$$", "right": "$$", "display": True}],
                )
                composer = gr.Textbox(
                    # lines=1 + max_lines>1: Enter mengirim, Shift+Enter baris baru, kotak memanjang otomatis.
                    elem_id="composer", show_label=False, lines=1, max_lines=12, autofocus=True, container=False,
                    placeholder=f"Tulis pesan untuk {args.app_name}…  (Enter kirim, Shift+Enter baris baru)",
                    submit_btn=True, stop_btn=True,
                )
                stats = gr.Markdown("", elem_classes="stats")
                gr.Markdown(f"{args.app_name} dapat keliru. Periksa kembali jawaban penting, terutama dasar hukum "
                            "dan kode.", elem_classes="disclaimer")
            with gr.Column(scale=2, elem_id="preview-col") as preview_col:
                gr.Markdown("#### Pratinjau website")
                preview = gr.HTML(preview_html(None))
                html_file = gr.DownloadButton("Unduh HTML", visible=False, elem_classes="cc-btn")

        settings_inputs = [system, thinking, temperature, top_p, top_k, min_p, repetition_penalty, seed,
                           max_new_tokens, use_adapter]

        # -------------------------------------------------- logika

        def respond(history, system, thinking, temperature, top_p, top_k, min_p, repetition_penalty, seed,
                    max_new_tokens, use_adapter):
            settings = dict(thinking=thinking, temperature=float(temperature), top_p=float(top_p), top_k=int(top_k),
                            min_p=float(min_p), repetition_penalty=float(repetition_penalty),
                            seed=int(seed if seed is not None else -1), max_new_tokens=int(max_new_tokens))
            messages = to_model_messages(history, system or "")
            if not messages or messages[-1]["role"] != "user":
                yield history, ""
                return
            prompt, n_prompt, dropped = fit_context(engine, messages, thinking, settings["max_new_tokens"])
            if dropped:
                gr.Warning(f"{dropped} pasangan tanya-jawab terlama tidak dikirim ke model karena konteks penuh.")
            stop_event = engine.current_stop = threading.Event()
            start, raw, first_token = time.time(), "", None
            thought_msg = {"role": "assistant", "content": "", "metadata": {"title": "💭 Proses berpikir",
                                                                             "status": "pending"}}
            answer_msg = {"role": "assistant", "content": ""}
            try:
                for piece in engine.stream(prompt, settings, use_adapter.startswith("Fine"), stop_event):
                    first_token = first_token or time.time()
                    raw += piece
                    thought, answer, done = split_thinking(raw, thinking)
                    shown = []
                    if thinking:
                        thought_msg["content"] = thought or "…"
                        if done:
                            thought_msg["metadata"]["status"] = "done"
                            thought_msg["metadata"]["duration"] = round(time.time() - start, 1)
                        shown.append(thought_msg)
                    if answer or not thinking:
                        answer_msg["content"] = answer
                        shown.append(answer_msg)
                    yield history + shown, "⏳ menulis…"
            finally:
                stop_event.set()
            elapsed = time.time() - start
            n_out = engine.count_tokens(SPECIAL_TOKEN.sub("", raw))
            speed = n_out / (time.time() - first_token) if first_token and time.time() > first_token else 0
            label = "dasar" if not use_adapter.startswith("Fine") else ("adapter" if engine.has_adapter else "dasar")
            info = (f"{n_out:,} token · {speed:.1f} token/detik · {elapsed:.0f} detik · prompt {n_prompt:,} token · "
                    f"model {label}")
            if n_out >= settings["max_new_tokens"] - 1:
                info += " · ⚠️ terpotong di batas maks. token"
            thought, answer, _ = split_thinking(raw, thinking)
            final = []
            if thinking and thought:
                thought_msg["content"] = thought
                thought_msg["metadata"]["status"] = "done"
                final.append(thought_msg)
            final.append({"role": "assistant", "content": answer or "_(jawaban kosong)_"})
            yield history + final, info

        def add_user(text, history):
            text = (text or "").strip()
            if not text:
                return gr.update(), history
            return "", history + [{"role": "user", "content": text}]

        def after_reply(history, show):
            page = last_html(history)
            files = export_files(history) if history else None
            if page:
                path = EXPORT_DIR / f"website-{datetime.now().strftime('%Y%m%d-%H%M%S')}.html"
                path.write_text(page, encoding="utf-8")
                return gr.update(value=preview_html(page)), gr.update(value=str(path), visible=True), files
            return gr.update(), gr.update(), files

        def trim_to_last_user(history):
            while history and history[-1]["role"] != "user":
                history = history[:-1]
            return history

        def on_retry(history):
            return trim_to_last_user(history)

        def on_undo(history):
            last = max((i for i, m in enumerate(history) if m["role"] == "user"), default=None)
            if last is None:
                return history, gr.update()
            return history[:last], text_of(history[last]["content"])

        def on_edit(history, evt: gr.EditData):
            history = history[:evt.index + 1]
            history[-1] = {"role": "user", "content": evt.value if isinstance(evt.value, str) else text_of(evt.value)}
            return history

        def on_example(history, evt: gr.SelectData):
            value = evt.value
            text = value.get("text", "") if isinstance(value, dict) else str(value)
            return history + [{"role": "user", "content": text}]

        def on_preset(name, current):
            value = SYSTEM_PRESETS.get(name)
            return current if value is None else value

        def on_recommended(thinking):
            t, p, k, m = QWEN_SAMPLING[bool(thinking)]
            return t, p, k, m, 1.0 if thinking else 1.05

        run = dict(fn=respond, inputs=[chatbot, *settings_inputs], outputs=[chatbot, stats],
                   concurrency_limit=1, concurrency_id="gpu")
        done = dict(fn=after_reply, inputs=[chatbot, show_preview], outputs=[preview, html_file, export])

        generations = []
        for trigger in (composer.submit(add_user, [composer, chatbot], [composer, chatbot], queue=False),
                        chatbot.retry(on_retry, chatbot, chatbot, queue=False),
                        chatbot.edit(on_edit, chatbot, chatbot, queue=False),
                        chatbot.example_select(on_example, chatbot, chatbot, queue=False)):
            gen = trigger.then(**run)
            gen.then(**done)
            generations.append(gen)
        composer.stop(engine.stop, None, None, cancels=generations, queue=False)
        chatbot.undo(on_undo, chatbot, [chatbot, composer], queue=False)

        def reset():
            engine.stop()
            return [], "", gr.update(value=preview_html(None)), gr.update(visible=False), None

        new_chat.click(reset, None, [chatbot, stats, preview, html_file, export], cancels=generations, queue=False)
        preset.change(on_preset, [preset, system], system, queue=False)
        recommended.click(on_recommended, thinking, [temperature, top_p, top_k, min_p, repetition_penalty],
                          queue=False)
        show_preview.change(lambda v: gr.update(visible=v), show_preview, preview_col, queue=False)
        dark.click(None, None, None, js=TOGGLE_DARK_JS)
        demo.load(None, None, None, js=CLOSE_SIDEBAR_ON_PHONE_JS)
    return demo


def get_engine(args):
    """Di notebook, sel ini bisa dijalankan ulang: pakai lagi model yang sudah dimuat supaya VRAM tidak penuh."""
    key = (args.adapter, args.out, args.base_model, args.load_in_4bit, args.max_seq_len, args.demo)
    cached = getattr(builtins, "_chat_gradio_engine", None)
    if cached and cached[0] == key:
        print("memakai model yang sudah dimuat", flush=True)
        return cached[1]
    if cached:  # pengaturan model berubah: lepas model lama dulu
        delattr(builtins, "_chat_gradio_engine")
        del cached
        import gc
        gc.collect()
        if "torch" in sys.modules:
            sys.modules["torch"].cuda.empty_cache()
    engine = Engine(args)
    builtins._chat_gradio_engine = (key, engine)
    return engine


def main():
    args = parse_args()
    import gradio as gr

    gr.close_all()  # tutup tampilan lama jika sel dijalankan ulang
    engine = get_engine(args)
    demo = build_app(engine, args)
    auth = tuple(args.auth.split(":", 1)) if args.auth else None
    demo.queue(default_concurrency_limit=1).launch(
        share=args.share, auth=auth, server_port=args.port, theme=build_theme(gr), css=CSS,
        height=900, show_error=True, debug=not IN_NOTEBOOK,
    )
    return demo


if __name__ == "__main__":
    main()
