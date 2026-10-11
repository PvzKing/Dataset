# HumanEval bench script

`eval_humaneval.py` menguji model hasil fine-tuning (Qwen3.5-4B + adapter LoRA) dengan 164 soal HumanEval dan tes tambahan HumanEval+, lalu membandingkannya dengan model dasarnya. Penilaiannya memakai harness resmi EvalPlus.

Secara bawaan ada dua run dengan satu kali muat model:
1. **adapter**, bawaan `qwen3.5-4b-bench-4bit-lanjut`;
2. **model dasar**, yaitu adapter yang sama dimatikan sementara. Bobot dasar dan kuantisasinya identik, jadi perbedaannya murni efek adapter.

Prosedur langkah demi langkah, termasuk cara membaca hasil dan mengatasi masalah, ada di [`PROSEDUR.md`](PROSEDUR.md).

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
%run /content/eval_humaneval.py              # 164 soal penuh: adapter + model dasar
```

Waktu generate kira-kira dua kali lipat karena ada dua run. Jawaban model dasar disimpan di folder `model-dasar` dan dipakai ulang oleh run adapter lain, misalnya v3, jadi model dasar cukup dijawab sekali.

`chat_gradio.py` dibutuhkan untuk memuat model (kelas `Engine`).

| Opsi | Kegunaan |
|---|---|
| `--adapter <folder>` | adapter yang diuji. Bawaan: `/content/drive/MyDrive/finetune-id/qwen3.5-4b-bench-4bit-lanjut/lora-adapter` |
| `--dataset mbpp` | MBPP+ (378 soal) sebagai ganti HumanEval+. Hasilnya di folder `eval-mbpp` |
| `--no-vs-base` | adapter saja, tanpa run model dasar |
| `--adapter none` | model dasar saja |
| `--tag <nama>` | nama folder hasil. Folder model dasarnya ikut menjadi `<nama>-model-dasar` |
| `--limit N` | hanya N soal pertama |
| `--batch-size N` | soal per generate (bawaan 8). Turunkan jika VRAM tidak cukup |
| `--demo` | uji alur tanpa GPU: jawaban diambil dari solusi resmi. "Adapter" sengaja salah di tiap soal ke-7 (hasil benar 140/164), "model dasar" di tiap soal ke-5 (131/164). Hasilnya disimpan di folder `demo` dan `demo-model-dasar` |

## Hasil

Hasil disimpan di `/content/drive/MyDrive/finetune-id/eval-humaneval/<nama run>/`. Nama run diambil dari folder adapter, misalnya `qwen3.5-4b-bench-4bit-lanjut`, `v3-qwen3.5-4b-own-4bit`, atau `model-dasar`.

| File | Isi |
|---|---|
| `jawaban.jsonl` | jawaban mentah model. Disimpan setiap batch, jadi jika Colab terputus, jalankan ulang perintah yang sama untuk melanjutkan |
| `samples.jsonl` | kode yang sudah diambil dari jawaban (`evalplus.sanitize`) |
| `eval_results.json` | hasil per soal dari `evalplus.evaluate` |
| `ringkasan.json` | skor pass@1, soal yang gagal, waktu generate |

Perbandingan dengan model dasar disimpan di `eval-humaneval/perbandingan-<nama run>.json`. Isinya:
- selisih skor dalam soal dan poin persen, untuk HumanEval dan HumanEval+;
- soal yang hanya lolos dengan adapter;
- soal yang hanya lolos di model dasar (regresi).

Contoh keluaran di akhir run:

```
===== Perbandingan dengan model dasar (164 soal) =====
| model                                    | HumanEval | HumanEval+ |
|------------------------------------------|-----------|------------|
| qwen3.5-4b-bench-4bit-lanjut             |     xx.x% |      xx.x% |
| model-dasar                              |     xx.x% |      xx.x% |

HumanEval: selisih +N soal (+x.x poin persen), McNemar p = 0.xxx: belum nyata, bisa kebetulan
  hanya lolos dengan adapter (n): ...
  hanya lolos di model dasar, regresi (n): ...
```

Setelah itu dicetak juga tabel semua run di folder hasil.

## Catatan

- **EvalPlus dipasang dari commit master.** Versi 0.3.1 di PyPI selalu menilai HumanEval/32 (`find_zero`) gagal, bahkan untuk solusi resminya. Penyebabnya, pemeriksa khusus soal itu melompati pencatatan tes yang lolos. Script berhenti dengan pesan jelas jika versi itu yang terpasang.
- **Uji McNemar** dicetak untuk setiap selisih. Uji ini membandingkan dua model pada soal yang sama dan menghitung seberapa mungkin selisih sebesar itu muncul hanya karena kebetulan. Selisih dengan p ≥ 0,05 jangan disimpulkan sebagai naik atau turun.
- **Skor adapter bench-lanjut tidak bersih.** Adapter itu dilatih dengan 164 soal HumanEval beserta jawabannya (lihat `data/bench-support/README.md`), jadi skornya tidak boleh dilaporkan sebagai hasil evaluasi.
  - Hasil ujinya justru menunjukkan model **tidak** menghafal: 78,0% / 72,0%, dibanding model dasar 82,3% / 73,8%.
  - Jawabannya meniru gaya ringkas jawaban latihan, tapi isinya tidak. Selisih −7 soal juga tidak nyata secara statistik (McNemar p = 0,34).
  - Pelajaran ini menjadi dasar [`docs/RENCANA_PYTHON.md`](../docs/RENCANA_PYTHON.md).
- **Perbandingan yang bersih adalah v3 dengan model dasar.** v3 belum pernah melihat soal ini, jadi selisihnya menunjukkan efek fine-tuning website terhadap kemampuan Python umum: `%run /content/eval_humaneval.py --adapter /content/drive/MyDrive/finetune-id/v3/qwen3.5-4b-own-4bit/lora-adapter`.
- **Jika adapter dilatih ulang dengan nama folder yang sama,** hapus folder hasil lamanya atau pakai `--tag` baru. Tanpa itu, jawaban lama yang dipakai.
