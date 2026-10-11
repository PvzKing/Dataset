# Prosedur benchmark HumanEval (adapter vs model dasar)

Prosedur ini menguji kemampuan Python model hasil fine-tuning dengan 164 soal HumanEval dan tes tambahan HumanEval+, lalu membandingkannya dengan model dasar Qwen3.5-4B. Semua langkah dijalankan di Google Colab.

**Hasil akhir yang didapat:**
1. Skor **bench-lanjut vs model dasar**. Skor ini terkontaminasi, karena adapter sudah melihat soal-soal ini (lihat langkah 7).
2. Skor **v3 vs model dasar**. Ini perbandingan yang bersih.
3. Daftar soal yang hanya lolos dengan adapter dan daftar regresinya, untuk tiap perbandingan.

Perkiraan total waktu: 1,5–3 jam di T4. Waktu pasti tiap run terlihat di log.

---

## Langkah 0. Persiapan

1. Buka Colab, lalu pilih **Runtime → Change runtime type → T4 GPU**.
2. Pastikan Google Drive berisi kedua adapter berikut:

   | Model | Folder di Drive |
   |---|---|
   | bench-lanjut (terbaru) | `MyDrive/finetune-id/qwen3.5-4b-bench-4bit-lanjut/lora-adapter` |
   | v3 | `MyDrive/finetune-id/v3/qwen3.5-4b-own-4bit/lora-adapter` |

   Setiap folder harus berisi `adapter_config.json` dan `adapter_model.safetensors`.
3. Siapkan ruang kosong di Drive sekitar 10 MB untuk hasil.

## Langkah 1. Pasang paket

```python
!pip install --upgrade unsloth "evalplus @ git+https://github.com/evalplus/evalplus@26d6d00bb1fd0fa37f39c99d5290da67891d1c5e"
```

- **Jangan pakai `pip install evalplus`.** Versi 0.3.1 di PyPI selalu menilai HumanEval/32 gagal. Script akan berhenti jika versi itu yang terpasang.
- Jika Colab meminta restart setelah instalasi, klik **Restart session**, lalu lanjut ke Langkah 2. Langkah 1 tidak perlu diulang.

## Langkah 2. Mount Drive dan unduh script

```python
from google.colab import drive; drive.mount("/content/drive")
REPO = "https://raw.githubusercontent.com/PvzKing/Dataset/main"
!wget -q -O /content/eval_humaneval.py {REPO}/humaneval-bench-script/eval_humaneval.py
!wget -q -O /content/chat_gradio.py {REPO}/scripts/chat_gradio.py
!ls /content/drive/MyDrive/finetune-id/qwen3.5-4b-bench-4bit-lanjut/lora-adapter
```

Perintah `ls` di baris terakhir harus menampilkan `adapter_config.json`. Kalau tidak, periksa path-nya sebelum lanjut.

## Langkah 3. Uji cepat (±5–10 menit)

```python
%run /content/eval_humaneval.py --limit 10 --tag uji-cepat
```

Hasilnya masuk folder `uji-cepat` dan `uji-cepat-model-dasar`, jadi tidak tercampur dengan run penuh.

**Lanjut ke Langkah 4 jika:**
- model dimuat tanpa error;
- muncul baris progres seperti `[uji-cepat] 8/10 soal, ...`;
- ringkasan kedua run dan tabel perbandingan tercetak;
- skornya masuk akal. Model 4B biasanya lolos sebagian besar dari 10 soal awal.

**Berhenti dan kirim log-nya ke saya jika:**
- skor 0 dari 10 di salah satu model. Itu tanda format jawaban tidak terbaca;
- muncul error yang tidak ada di tabel Langkah 8.

## Langkah 4. Run penuh: bench-lanjut vs model dasar

```python
%run /content/eval_humaneval.py
```

Yang terjadi:
1. Model dimuat sekali.
2. 164 soal dijawab dengan adapter bench-lanjut. Hasilnya masuk folder `qwen3.5-4b-bench-4bit-lanjut`.
3. 164 soal dijawab lagi dengan adapter dimatikan. Hasilnya masuk folder `model-dasar`.
4. Kedua set jawaban dinilai dengan `evalplus.evaluate`, yaitu tes dasar dan tes tambahan HumanEval+. Penilaian butuh ±1–3 menit per run.
5. Tabel perbandingan dicetak dan disimpan ke `perbandingan-qwen3.5-4b-bench-4bit-lanjut.json`.

Selama generate, baris progres menampilkan sisa waktu dan kecepatan, misalnya:
```
[qwen3.5-4b-bench-4bit-lanjut] 48/164 soal, 9.6 menit, ±23.2 menit lagi, 38 token/detik
```

**Jika Colab terputus,** ulangi Langkah 2, lalu jalankan perintah yang sama lagi. Soal yang sudah dijawab dilewati.

## Langkah 5. Run penuh: v3 vs model dasar

Restart dulu supaya VRAM kosong: **Runtime → Restart session**. Setelah itu ulangi Langkah 2, lalu:

```python
%run /content/eval_humaneval.py --adapter /content/drive/MyDrive/finetune-id/v3/qwen3.5-4b-own-4bit/lora-adapter
```

Jawaban model dasar dari Langkah 4 dipakai ulang, jadi hanya v3 yang dijawab. Waktunya sekitar setengah Langkah 4. Hasil perbandingan disimpan ke `perbandingan-v3-qwen3.5-4b-own-4bit.json`.

## Langkah 6. Kumpulkan hasil

Semua hasil ada di `MyDrive/finetune-id/eval-humaneval/`:

```
eval-humaneval/
├── qwen3.5-4b-bench-4bit-lanjut/   jawaban.jsonl, samples.jsonl, eval_results.json, ringkasan.json
├── v3-qwen3.5-4b-own-4bit/         (isi sama)
├── model-dasar/                    (isi sama)
├── uji-cepat/, uji-cepat-model-dasar/
├── perbandingan-qwen3.5-4b-bench-4bit-lanjut.json
└── perbandingan-v3-qwen3.5-4b-own-4bit.json
```

| File | Kegunaan |
|---|---|
| `jawaban.jsonl` | jawaban mentah. Periksa di sini jika ada soal gagal yang aneh |
| `samples.jsonl` | kode yang benar-benar dinilai |
| `eval_results.json` | status per soal, termasuk input tes yang gagal |
| `ringkasan.json` | skor dan daftar soal gagal |
| `perbandingan-*.json` | selisih, soal yang hanya lolos dengan adapter, dan regresi |

Untuk menampilkan ulang tabel semua run tanpa menjalankan model, jalankan perintah run yang sama. Semua soal sudah dijawab, jadi script langsung menilai dan mencetak tabel:
```python
%run /content/eval_humaneval.py --no-vs-base
```

## Langkah 7. Membaca hasil

| Perbandingan | Arti selisihnya | Boleh dilaporkan? |
|---|---|---|
| **v3 vs model dasar** | efek fine-tuning website (dataset own) terhadap kemampuan Python umum. Kalau negatif, berarti ada kemampuan yang hilang (*forgetting*) | **Ya**, ini angka yang bersih |
| **bench-lanjut vs model dasar** | terutama hafalan. Adapter dilatih dengan 164 soal ini beserta jawabannya sampai loss ±0,03 | **Tidak** sebagai skor kemampuan. Boleh disebut dengan label "terkontaminasi" |
| **bench-lanjut vs v3** | seberapa banyak hafalan menambah skor | hanya sebagai catatan internal |

**Hal lain yang perlu diperhatikan:**
- **HumanEval+ selalu lebih rendah atau sama dengan HumanEval.** Tes tambahannya menangkap solusi yang hanya lolos contoh dasar. Kalau selisih keduanya besar, model sering lupa menangani kasus tepi.
- **Regresi** adalah soal yang dijawab benar oleh model dasar tapi salah oleh adapter. Buka `jawaban.jsonl` untuk soal-soal itu dan cari polanya, misalnya jawaban terpotong, format berubah, atau logika keliru.
- **Satu soal = 0,6 poin persen.** Selisih 1–2 soal masih dalam batas wajar akibat perbedaan numerik kecil saat generate berbatch, jadi jangan disimpulkan berlebihan.

**Catatan hukum.** Jika model ini nanti ditawarkan sebagai produk atau jasa, jangan pakai skor bench-lanjut sebagai klaim kemampuan. Menyebut skor yang diperoleh dari menghafal soal ujian sebagai mutu model bisa dinilai sebagai promosi yang tidak benar tentang standar mutu atau kegunaan jasa. Ini dilarang Pasal 9 ayat (1) huruf a dan Pasal 10 huruf b UU No. 8 Tahun 1999 tentang Perlindungan Konsumen. Untuk klaim publik, pakai skor v3 atau model lain yang tidak terkontaminasi, dan sebutkan kondisi ujinya: greedy, pass@1, EvalPlus HumanEval+ v0.1.10, 4-bit.

## Langkah 8. Mengatasi masalah

| Gejala | Penyebab | Solusi |
|---|---|---|
| `evalplus yang terpasang (0.3.1 dari PyPI)...` | EvalPlus versi PyPI | jalankan perintah `pip install --force-reinstall --no-deps ...` yang ditampilkan, restart session, lalu ulangi dari Langkah 2 |
| `adapter tidak ditemukan` | Drive belum di-mount atau path salah | ulangi Langkah 2 dan periksa hasil `ls` |
| `CUDA out of memory` | batch terlalu besar | tambahkan `--batch-size 4`, atau `2` |
| `model ini tidak bisa mematikan adapter sementara` | model dimuat tanpa adapter LoRA | jalankan adapter dengan `--no-vs-base`, lalu model dasar terpisah dengan `--adapter none` |
| `stop_strings tidak didukung...` | versi transformers | tidak perlu tindakan. Generate tetap jalan, hanya sedikit lebih lambat |
| Error import setelah pip install | Colab perlu restart | Restart session, lalu ulangi dari Langkah 2 |
| Colab terputus | sesi habis atau idle | ulangi Langkah 2 dan perintah yang sama. Run dilanjutkan |
| Skor model dasar janggal setelah ganti `--max-new-tokens` atau model dasar | jawaban lama dipakai ulang | hapus folder `model-dasar` lalu jalankan ulang |
| Adapter dilatih ulang dengan nama folder sama | jawaban lama dipakai ulang | hapus folder hasilnya, atau pakai `--tag` baru |

## Langkah 9. Kirim hasil untuk dianalisis

Salin dua tabel perbandingan dari output Langkah 4 dan 5, beserta baris "hanya lolos dengan adapter" dan "regresi". Kalau ada soal yang gagal dengan cara aneh, sertakan juga potongan `jawaban.jsonl`-nya. Format ringkas yang bisa dipakai:

| Model | HumanEval | HumanEval+ | Catatan |
|---|---|---|---|
| model dasar Qwen3.5-4B (4-bit) | | | pembanding |
| v3 | | | bersih |
| bench-lanjut | | | terkontaminasi |
