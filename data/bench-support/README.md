# Kelompok dataset bench-support

Sampel latihan yang diambil dari benchmark kode. Kelompok ini disimpan terpisah dari dataset `own` (`data/train.jsonl`), dan dilatih sendiri dengan `--dataset bench` sebagai lanjutan adapter hasil `own`:

```bash
python scripts/train_unsloth.py train --dataset bench --init-adapter <folder lora-adapter v3>
```

Di T4, training 164 sampel × 3 epoch diperkirakan memakan ±19–27 menit.

| File | Sampel | Token | Sumber |
|---|---|---|---|
| `humaneval.jsonl` | 164 | ±65 ribu (terpanjang ±1.000) | HumanEval (OpenAI) + HumanEval+ (EvalPlus) |

**Kontaminasi benchmark disengaja.** Model yang dilatih dengan kelompok ini sudah melihat soal HumanEval beserta jawabannya. Akibatnya, skor HumanEval atau HumanEval+ model tersebut tidak lagi mengukur kemampuan menyelesaikan soal baru. Jangan laporkan skor itu sebagai hasil evaluasi yang bersih.

## Format

Setiap sampel memakai template chat EvalPlus, yaitu cara HumanEval dan HumanEval+ menguji model instruct:

- **user:** `Please provide a self-contained Python script that solves the following problem in a markdown code block:`, lalu prompt soal di dalam blok kode.
- **assistant:** `Below is a Python script with a self-contained function that solves the problem and passes corresponding tests:`, lalu satu blok ```` ```python ```` berisi fungsi lengkap. Fungsi lengkap artinya import, fungsi bantu dari prompt, signature, docstring, dan isi fungsi.

Field `source` menyimpan ID soal aslinya, misalnya `HumanEval/0`.

## Cara dibuat dan diverifikasi

Semua langkah dijalankan oleh `scripts/build_bench_support.py`:

1. **Ambil data.** Prompt dan solusi diambil dari HumanEval+ v0.1.10. HumanEval+ menulis ulang 155 dari 164 solusi asli supaya benar dan efisien untuk input yang lebih berat.
2. **Uji dengan tes resmi.** Setiap solusi harus lolos tes resmi HumanEval.
3. **Periksa silang dengan solusi asli.** Tes resmi HumanEval hanya berisi beberapa assert. Saat diuji, tes itu meloloskan solusi yang salah, misalnya `<` yang diganti `<=`. Karena itu, output setiap solusi juga dibandingkan dengan output solusi asli HumanEval, yang ditulis terpisah, pada semua input tambahan HumanEval+.
   - Totalnya sekitar 111.700 input cocok.
   - Sekitar 90 input dilewati karena solusi aslinya terlalu lambat atau error. Jumlah persisnya bisa bergeser sedikit tiap run, karena bergantung pada batas waktu 1 detik per input.
4. **Tinjau setiap perbedaan secara manual.**
   - **15 soal: solusi asli HumanEval terbukti keliru.** Contohnya `modp(0, 1)` dan `valid_date('12-31-1999')`. Untuk soal ini solusi HumanEval+ dipakai. Daftar dan alasannya ada di `KNOWN_ORIGINAL_BUGS`.
   - **HumanEval/32 (`find_zero`): kedua solusi referensi gagal pada sebagian input.**
     - Bisection asli macet atau overflow jika akarnya tepat di 0.
     - Metode Newton HumanEval+ gagal konvergen pada 4 input berkoefisien besar.
     
     Solusinya ditulis ulang sebagai gabungan keduanya. Hasilnya lolos tes resmi dan menemukan akar pada semua 888 input.

File hanya ditulis jika semua soal lolos verifikasi. Menjalankan ulang `python scripts/build_bench_support.py` membuat file yang sama persis.

## Lisensi dan perubahan

| Komponen | Lisensi | Pemegang hak cipta | Teks lisensi |
|---|---|---|---|
| HumanEval (soal, tes, solusi asli) | MIT | OpenAI | `LICENSE-HumanEval-MIT.txt` |
| HumanEval+ (solusi yang ditulis ulang, input tambahan) | Apache License 2.0 | tim EvalPlus | `LICENSE-EvalPlus-Apache-2.0.txt` |

Kedua lisensi mengizinkan pemakaian ulang, modifikasi, dan distribusi, termasuk untuk komersial, dengan beberapa syarat:
- **MIT:** pemberitahuan hak cipta dan izin MIT wajib disertakan pada setiap salinan atau bagian substansialnya.
- **Apache 2.0 Pasal 4:**
  - salinan lisensinya wajib diberikan;
  - pemberitahuan hak cipta wajib dipertahankan;
  - file yang diubah wajib diberi pemberitahuan yang jelas tentang perubahannya.
  
  EvalPlus tidak menyediakan file NOTICE, jadi tidak ada kewajiban tambahan dari sana.

**Perubahan terhadap karya asal**, sebagai pemberitahuan menurut Apache 2.0 Pasal 4(b):
- Soal dan solusi diformat ulang menjadi pasangan percakapan user/assistant dengan template EvalPlus.
- Kontrak input (`contract`) HumanEval+ tidak disertakan.
- Solusi HumanEval/32 ditulis ulang seperti dijelaskan di atas.

Jika dataset ini atau model hasil training-nya didistribusikan, sertakan folder ini beserta kedua file lisensinya.
