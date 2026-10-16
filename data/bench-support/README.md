# Kelompok dataset bench-support

Sampel latihan yang diambil dari benchmark kode. Kelompok ini disimpan terpisah dari dataset `own` (`data/train.jsonl`), dan dilatih sendiri dengan `--dataset bench` sebagai lanjutan adapter hasil `own`:

```bash
python scripts/train_unsloth.py train --dataset bench --init-adapter <folder lora-adapter v3>
```

Di T4, training 164 sampel × 3 epoch diperkirakan memakan ±19–27 menit.

| File | Sampel | Token | Sumber |
|---|---|---|---|
| `humaneval.jsonl` | 164 | ±65 ribu (terpanjang ±1.000) | HumanEval (OpenAI) + HumanEval+ (EvalPlus) |
| `mbppplus.jsonl` | 378 | ±65 ribu (perkiraan) | MBPP (Google) + MBPP+ v0.2.0 (EvalPlus) |
| `mbpp-sisa.jsonl` | 589 | ±115 ribu (perkiraan) | MBPP asli (Google): soal yang tidak masuk MBPP+ |

`--dataset bench` dan `own+bench` (V5) hanya memakai `humaneval.jsonl`. `--dataset own+evalplus` (V6, [`docs/PANDUAN_V6_A100.md`](../../docs/PANDUAN_V6_A100.md)) memakai ketiganya.

**Kontaminasi benchmark disengaja.** Model yang dilatih dengan kelompok ini sudah melihat soal HumanEval (dan, untuk V6, MBPP) beserta jawabannya. Akibatnya, skor HumanEval, HumanEval+, MBPP, atau MBPP+ model tersebut tidak lagi mengukur kemampuan menyelesaikan soal baru. Jangan laporkan skor itu sebagai hasil evaluasi yang bersih.

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

## MBPP+ dan MBPP

`python scripts/build_bench_support.py --only mbpp` membangun dua file dengan format yang sama. Prompt-nya sama persis dengan yang dipakai `eval_humaneval.py --dataset mbpp`: deskripsi soal dan satu assert contoh di dalam docstring.

- **`mbppplus.jsonl`:** 378 soal MBPP+ v0.2.0. Jawabannya solusi kanonis EvalPlus, yang juga menjadi kunci jawaban MBPP+. Setiap solusi harus lolos assert resmi MBPP (field `assertion`).
- **`mbpp-sisa.jsonl`:** soal MBPP asli (974 soal) yang tidak masuk MBPP+. Prompt dibuat dengan format MBPP+, dan jawabannya kode asli MBPP yang dirapikan (CRLF, tab, spasi di akhir baris). Setiap solusi harus lolos semua assert-nya (`test_list` dan `challenge_test_list`). Yang dibuang:

  | Soal MBPP | Alasan |
  |---|---|
  | 367, 927 | assert-nya butuh `test_setup_code` (pohon biner) yang tidak disebut di prompt |
  | 347 | prompt-nya sama persis dengan soal lain |
  | 216, 298, 889 | punya 13-gram yang sama dengan IndoPy-dev (deret angka 1, 2, 3, …) |
  | 522 | punya 13-gram yang sama dengan IndoPy-test (deret uji yang sama) |

  Lima soal terakhir dibuang supaya IndoPy tetap bersih untuk memilih epoch V6. Periksa dengan `python scripts/decontaminate.py --sumber IndoPy Web-eval --data data/bench-support/*.jsonl`.

Solusi asli MBPP tidak diperiksa silang dengan input tambahan MBPP+, karena soalnya memang tidak ada di MBPP+. Jadi mutu `mbpp-sisa.jsonl` setara dengan MBPP asli: lolos tiga assert, tetapi bisa keliru pada kasus tepi.

## Menguji skor

`humaneval-bench-script/eval_humaneval.py` menjalankan 164 soal dengan template chat yang sama, greedy decoding, lalu menilainya dengan harness resmi EvalPlus (tes dasar HumanEval dan tes tambahan HumanEval+). Petunjuk Colab ada di `humaneval-bench-script/README.md`.

- **Pasang EvalPlus dari commit master.** Versi 0.3.1 di PyPI selalu menilai HumanEval/32 gagal, bahkan untuk solusi resminya. Script berhenti dengan pesan jelas jika versi itu yang terpasang.
- **Perbandingan dengan model dasar otomatis.** Setiap run juga menjawab soal dengan adapter dimatikan, lalu mencetak selisih skor, soal yang hanya lolos dengan adapter, dan regresinya. Jalankan juga dengan adapter v3 (`--adapter <folder v3>`) untuk perbandingan yang bersih.
- **Skor adapter bench-lanjut tidak bersih**, sesuai peringatan di atas: model sudah melihat soal dan jawabannya. Hasil ujinya pun tidak naik: 78,0% HumanEval dan 72,0% HumanEval+, dibanding model dasar 82,3% dan 73,8%. Model meniru gaya ringkas jawaban latihan tanpa menguasai isinya. Karena itu kelompok ini tidak lagi dilatih sendiri sebagai lanjutan (lihat `docs/RENCANA_PYTHON.md`). V5 memakainya dengan cara lain ([`docs/PANDUAN_V5_A100.md`](../../docs/PANDUAN_V5_A100.md)):
  - dicampur dengan `own` dalam satu run dari model dasar (`--dataset own+bench`);
  - adapter epoch 2 dan 3 disimpan, lalu yang dipakai dipilih dari uji yang bersih (MBPP+, IndoPy-dev, Web-eval);
  - skor HumanEval V5 tetap ditandai terkontaminasi.

## Lisensi dan perubahan

| Komponen | Lisensi | Pemegang hak cipta | Teks lisensi |
|---|---|---|---|
| HumanEval (soal, tes, solusi asli) | MIT | OpenAI | `LICENSE-HumanEval-MIT.txt` |
| HumanEval+ dan MBPP+ (solusi yang ditulis ulang, input tambahan) | Apache License 2.0 | tim EvalPlus | `LICENSE-EvalPlus-Apache-2.0.txt` |
| MBPP (soal, assert, solusi asli) | Creative Commons Attribution 4.0 (CC BY 4.0) | Google Research (Austin dkk., 2021) | `LICENSE-MBPP-CC-BY-4.0.txt` |

Kedua lisensi mengizinkan pemakaian ulang, modifikasi, dan distribusi, termasuk untuk komersial, dengan beberapa syarat:
- **MIT:** pemberitahuan hak cipta dan izin MIT wajib disertakan pada setiap salinan atau bagian substansialnya.
- **CC BY 4.0 Section 3(a):** sebut pencipta (Google Research, *Program Synthesis with Large Language Models*, Austin dkk., 2021), cantumkan lisensinya, dan nyatakan bahwa materi telah diubah. Lisensi ini tidak mengizinkan pembatasan tambahan bagi penerima (Section 2(a)(5)(B)), jadi data turunannya tidak boleh dibagikan dengan syarat yang lebih ketat.
- **Apache 2.0 Pasal 4:**
  - salinan lisensinya wajib diberikan;
  - pemberitahuan hak cipta wajib dipertahankan;
  - file yang diubah wajib diberi pemberitahuan yang jelas tentang perubahannya.
  
  EvalPlus tidak menyediakan file NOTICE, jadi tidak ada kewajiban tambahan dari sana.

**Perubahan terhadap karya asal**, sebagai pemberitahuan menurut Apache 2.0 Pasal 4(b):
- Soal dan solusi diformat ulang menjadi pasangan percakapan user/assistant dengan template EvalPlus.
- Kontrak input (`contract`) HumanEval+ tidak disertakan.
- Solusi HumanEval/32 ditulis ulang seperti dijelaskan di atas.
- MBPP: prompt dibuat dengan format MBPP+, kode asli dirapikan (CRLF, tab, spasi di akhir baris), dan beberapa soal dibuang seperti dijelaskan di bagian *MBPP+ dan MBPP*. Ini juga pernyataan perubahan menurut CC BY 4.0 Section 3(a)(1)(B).

Jika dataset ini atau model hasil training-nya didistribusikan, sertakan folder ini beserta ketiga file lisensinya.
