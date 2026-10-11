# Prosedur v4-pilot: ukur v3, latih v4-pilot, bandingkan

Prosedur ini menjalankan bagian [`RENCANA_PYTHON.md`](RENCANA_PYTHON.md) yang butuh GPU:

- **Fase 0:** mengukur v3 dan model dasar dengan papan skor lengkap.
- **Fase 2:** melatih v4-pilot (dataset own yang sekarang berisi 20 sampel Python baru) dan mengukurnya.

Semua dijalankan di Google Colab dengan GPU T4.

**Hasil akhir yang didapat:**
1. Papan skor v3: HumanEval+, MBPP+, IndoPy-dev, dan Web-eval, masing-masing dibandingkan dengan model dasar.
2. Papan skor v4-pilot dengan gerbang G1 (Python umum tidak turun) dan G3 (website ≥ v3).
3. Daftar soal dan website yang gagal, untuk menentukan sampel berikutnya.

Perkiraan waktu total: ±6–8 jam GPU. Pekerjaan ini bisa dipecah ke beberapa sesi, karena setiap uji menyimpan jawabannya per batch dan bisa dilanjutkan.

---

## Langkah 0. Persiapan

1. Buka Colab, lalu pilih **Runtime → Change runtime type → T4 GPU**.
2. Pastikan adapter v3 ada di `MyDrive/finetune-id/v3/qwen3.5-4b-own-4bit/lora-adapter`.
3. Jawaban model dasar dari uji HumanEval sebelumnya (`MyDrive/finetune-id/eval-humaneval/model-dasar`) dipakai ulang secara otomatis. Jangan dihapus.

## Langkah 1. Pasang paket

```python
!pip install --upgrade unsloth "evalplus @ git+https://github.com/evalplus/evalplus@26d6d00bb1fd0fa37f39c99d5290da67891d1c5e"
!pip install -q playwright && playwright install --with-deps chromium
```

Playwright dan Chromium dipakai Web-eval untuk membuka dan mencoba website. Jika Colab meminta restart, klik **Restart session**, lalu lanjut ke Langkah 2.

## Langkah 2. Mount Drive dan unduh script

Jalankan sel ini di awal setiap sesi:

```python
from google.colab import drive; drive.mount("/content/drive")
REPO = "https://raw.githubusercontent.com/PvzKing/Dataset/main"
!wget -q -O /content/eval_humaneval.py {REPO}/humaneval-bench-script/eval_humaneval.py
!wget -q -O /content/chat_gradio.py {REPO}/scripts/chat_gradio.py
!wget -q -O /content/indopy_eval.py {REPO}/eval-suite/indopy_eval.py
!wget -q -O /content/web_eval.py {REPO}/eval-suite/web_eval.py
!wget -q -O /content/papan_skor.py {REPO}/eval-suite/papan_skor.py
!wget -q -O /content/train_unsloth.py {REPO}/scripts/train_unsloth.py
V3 = "/content/drive/MyDrive/finetune-id/v3/qwen3.5-4b-own-4bit/lora-adapter"
V4 = "/content/drive/MyDrive/finetune-id/v4-pilot/qwen3.5-4b-own-4bit/lora-adapter"
!ls {V3}
```

`ls` di baris terakhir harus menampilkan `adapter_config.json`.

## Langkah 3. Ukur v3 (Fase 0)

Jalankan satu per satu. Setiap perintah juga menguji model dasar, kecuali jawaban model dasar untuk benchmark itu sudah ada.

```python
%run /content/eval_humaneval.py --adapter {V3}                 # ±20 menit, model dasar dipakai ulang
```
```python
%run /content/indopy_eval.py --split dev --adapter {V3}        # ±10–15 menit (v3 + model dasar)
```
```python
%run /content/web_eval.py --adapter {V3}                       # ±60–90 menit (v3 + model dasar)
```
```python
%run /content/eval_humaneval.py --dataset mbpp --adapter {V3}  # ±80–110 menit (v3 + model dasar)
```

- **Restart di antara uji yang panjang.** Setiap uji memuat model sendiri. Jika muncul `CUDA out of memory` di uji berikutnya, pilih **Runtime → Restart session**, ulangi Langkah 2, lalu jalankan uji itu lagi. Jawaban yang sudah tersimpan tidak hilang.
- **Jangan jalankan `indopy_eval.py --split test` sekarang.** Set test dikunci untuk penilaian akhir v4.

Lihat papan skor v3:

```python
%run /content/papan_skor.py --tag v3-qwen3.5-4b-own-4bit
```

## Langkah 4. Latih v4-pilot (Fase 2)

```python
!python /content/train_unsloth.py train --out /content/drive/MyDrive/finetune-id/v4-pilot
```

- `train.jsonl` terbaru diunduh otomatis dari GitHub. Pastikan log menampilkan `data valid: 102 sampel`.
- Resepnya sama persis dengan v3: model dasar, 3 epoch, LoRA r 16, lr 1e-4, QLoRA 4-bit, konteks 6144. Jadi perbedaan hasilnya berasal dari data.
- Perkiraan waktu ±55–65 menit, lalu dua website uji dibuat seperti biasa.
- Hasilnya masuk ke folder `v4-pilot/qwen3.5-4b-own-4bit`, jadi adapter v3 tidak tersentuh.

## Langkah 5. Ukur v4-pilot

Restart session, ulangi Langkah 2, lalu:

```python
%run /content/eval_humaneval.py --adapter {V4}                 # ±20 menit
```
```python
%run /content/indopy_eval.py --split dev --adapter {V4}        # ±5–10 menit
```
```python
%run /content/web_eval.py --adapter {V4}                       # ±30–45 menit
```
```python
%run /content/eval_humaneval.py --dataset mbpp --adapter {V4}  # ±40–55 menit
```

Jawaban model dasar semuanya dipakai ulang dari Langkah 3, jadi waktunya sekitar separuh Langkah 3.

## Langkah 6. Papan skor dan keputusan

```python
%run /content/papan_skor.py --tag v4-pilot-qwen3.5-4b-own-4bit --pembanding v3-qwen3.5-4b-own-4bit
```

| Hasil | Langkah berikutnya |
|---|---|
| G1 lolos, G3 lolos, IndoPy-dev naik dari v3 | gaya sampel terbukti. Lanjut ke Fase 3: data penuh dan set uji G4 |
| IndoPy-dev tidak naik | jangan tambah data dulu. Periksa jawaban yang gagal di `eval-indopy-dev/<run>/hasil.jsonl` |
| G3 gagal | bandingkan kolom alasan Web-eval v3 dan v4-pilot: kegagalan baru (regresi) atau sama |
| G1 gagal | cek soal regresi di `perbandingan-*.json`, lalu pertimbangkan swa-distilasi (Fase 4) |

G2 tercatat "BELUM DIUKUR" untuk pilot. Itu memang disengaja: IndoPy-test baru dijalankan pada v4 penuh.

## Langkah 7. Kirim hasil

Salin ke chat:
1. output kedua papan skor (v3 dan v4-pilot);
2. tabel Web-eval v3 dan v4-pilot, yaitu tabel `| website | html | tanpa error | ...`;
3. daftar "gagal" IndoPy-dev untuk v3, v4-pilot, dan model dasar.

Dari situ saya bisa menganalisis jenis kesalahan dan menyusun sampel Fase 3.

## Mengatasi masalah

| Gejala | Penyebab | Solusi |
|---|---|---|
| `No module named 'playwright'` atau Chromium tidak ditemukan | Langkah 1 belum dijalankan di sesi ini | jalankan baris kedua Langkah 1 |
| `CUDA out of memory` di uji kedua dan seterusnya | memori model uji sebelumnya belum dilepas | Restart session, Langkah 2, ulangi perintah yang sama |
| `adapter tidak ditemukan` | Drive belum di-mount atau path salah | jalankan Langkah 2 dan periksa hasil `ls` |
| `evalplus yang terpasang (0.3.1 dari PyPI)...` | EvalPlus versi PyPI | jalankan perintah `pip install --force-reinstall` yang ditampilkan, lalu restart |
| Colab terputus di tengah uji | sesi habis | Langkah 2, lalu perintah yang sama. Soal dan website yang sudah dijawab dilewati |
| `data valid: 82 sampel` atau angka lain saat training | `train.jsonl` lama di cache, atau main belum berisi data baru | hapus `MyDrive/finetune-id/v4-pilot/train.jsonl`, lalu ulangi Langkah 4 |
| v4-pilot dilatih ulang dengan folder yang sama | jawaban uji lama dipakai ulang | hapus subfolder `v4-pilot-qwen3.5-4b-own-4bit` di setiap folder `eval-*` |
