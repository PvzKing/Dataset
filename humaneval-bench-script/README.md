# HumanEval bench script

`eval_humaneval.py` menguji model hasil fine-tuning (Qwen3.5-4B + adapter LoRA) dengan 164 soal HumanEval dan tes tambahan HumanEval+. Penilaiannya memakai harness resmi EvalPlus.

## Cara memakai di Google Colab (GPU T4 cukup)

```python
# Sel 1
!pip install --upgrade unsloth "evalplus @ git+https://github.com/evalplus/evalplus@26d6d00bb1fd0fa37f39c99d5290da67891d1c5e"

# Sel 2
from google.colab import drive; drive.mount("/content/drive")
REPO = "https://raw.githubusercontent.com/PvzKing/Dataset/main"
!wget -q -O /content/eval_humaneval.py {REPO}/humaneval-bench-script/eval_humaneval.py
!wget -q -O /content/chat_gradio.py {REPO}/scripts/chat_gradio.py

# Sel 3
%run /content/eval_humaneval.py --limit 10   # uji cepat dulu
%run /content/eval_humaneval.py              # 164 soal penuh
```

`chat_gradio.py` dibutuhkan untuk memuat model (kelas `Engine`).

| Opsi | Kegunaan |
|---|---|
| `--adapter <folder>` | adapter yang diuji. Bawaan: `/content/drive/MyDrive/finetune-id/qwen3.5-4b-bench-4bit-lanjut/lora-adapter` |
| `--adapter none` | model dasar, sebagai pembanding |
| `--limit N` | hanya N soal pertama |
| `--batch-size N` | soal per generate (bawaan 8). Turunkan jika VRAM tidak cukup |
| `--demo` | uji alur tanpa GPU: jawaban diambil dari solusi resmi, satu dari tiap tujuh soal sengaja dirusak (hasil yang benar: 140/164) |

## Hasil

Hasil disimpan di `/content/drive/MyDrive/finetune-id/eval-humaneval/<nama run>/`. Nama run diambil dari folder adapter, misalnya `qwen3.5-4b-bench-4bit-lanjut`, `v3-qwen3.5-4b-own-4bit`, atau `model-dasar`.

| File | Isi |
|---|---|
| `jawaban.jsonl` | jawaban mentah model. Disimpan setiap batch, jadi jika Colab terputus, jalankan ulang perintah yang sama untuk melanjutkan |
| `samples.jsonl` | kode yang sudah diambil dari jawaban (`evalplus.sanitize`) |
| `eval_results.json` | hasil per soal dari `evalplus.evaluate` |
| `ringkasan.json` | skor pass@1, soal yang gagal, waktu generate |

Di akhir, script mencetak tabel perbandingan semua run di folder hasil.

## Catatan

- **EvalPlus dipasang dari commit master.** Versi 0.3.1 di PyPI selalu menilai HumanEval/32 (`find_zero`) gagal, bahkan untuk solusi resminya. Penyebabnya, pemeriksa khusus soal itu melompati pencatatan tes yang lolos. Script berhenti dengan pesan jelas jika versi itu yang terpasang.
- **Skor adapter bench-lanjut tidak bersih.** Adapter itu dilatih dengan 164 soal HumanEval beserta jawabannya (lihat `data/bench-support/README.md`), jadi skornya mengukur hafalan. Jalankan juga dengan adapter v3 dan model dasar untuk melihat besarnya efek itu, dan jangan laporkan skor adapter bench sebagai hasil evaluasi yang bersih.
