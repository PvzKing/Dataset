# Pertanyaan ultradistillation yang belum dijawab (7 dari 80)

Salin satu blok ke **percakapan baru** di AI-nya. Setelah AI menjawab, salin jawabannya dengan tombol salin (supaya format Markdown dan blok kodenya ikut), lalu kirim ke chat dengan baris pertama `<id> · <nama AI dan versinya>`.

## ud-074 · python

````text
Jawab pertanyaan di bawah garis dalam bahasa Indonesia yang baku tapi luwes. Langsung ke jawabannya: jangan membuka dengan basa-basi, jangan menyebut dirimu AI atau model bahasa, dan jangan menampilkan proses berpikir.

Format jawaban: jelaskan pendekatannya dalam beberapa kalimat, lalu tulis solusi lengkap dalam satu blok ```python dengan nama fungsi persis seperti yang diminta, tanpa input() dan tanpa print di luar fungsi. Setelah itu beri contoh pemakaian singkat dan kasus khusus yang ditangani.

---

Tulis fungsi `kali_polinom(a: list[int], b: list[int]) -> list[int]` yang mengalikan dua polinom berkoefisien bilangan bulat; elemen ke-i adalah koefisien xⁱ, dan nilai mutlak setiap koefisien paling besar 10⁹ (boleh negatif). Hasilnya harus eksak dan panjangnya `len(a) + len(b) - 1` tanpa membuang nol di akhir; jika salah satu list kosong, kembalikan `[]`. Fungsi harus selesai dalam beberapa detik untuk dua polinom yang masing-masing punya 20.000 koefisien, sehingga perkalian O(n²) biasa tidak cukup, dan FFT dengan bilangan floating point biasa tidak eksak untuk koefisien sebesar ini. Gunakan hanya pustaka standar Python.
````

## ud-075 · python

````text
Jawab pertanyaan di bawah garis dalam bahasa Indonesia yang baku tapi luwes. Langsung ke jawabannya: jangan membuka dengan basa-basi, jangan menyebut dirimu AI atau model bahasa, dan jangan menampilkan proses berpikir.

Format jawaban: jelaskan pendekatannya dalam beberapa kalimat, lalu tulis solusi lengkap dalam satu blok ```python dengan nama fungsi persis seperti yang diminta, tanpa input() dan tanpa print di luar fungsi. Setelah itu beri contoh pemakaian singkat dan kasus khusus yang ditangani.

---

Tulis fungsi `cari_banyak_pola(teks: str, pola: list[str]) -> dict[str, list[int]]` yang mencari semua kemunculan setiap pola di `teks`, termasuk yang tumpang tindih. Kunci dict adalah pola unik dengan urutan sesuai kemunculan pertamanya di `pola` (pola kembar cukup satu kunci); nilainya list indeks awal kemunculan secara naik, atau list kosong jika pola tidak muncul. List `pola` kosong menghasilkan `{}`, sedangkan pola berupa string kosong → `ValueError`. Harus selesai dalam beberapa detik untuk teks 300.000 karakter dan 30.000 pola sepanjang 8–12 karakter. Gunakan hanya pustaka standar Python.
````

## ud-076 · python

````text
Jawab pertanyaan di bawah garis dalam bahasa Indonesia yang baku tapi luwes. Langsung ke jawabannya: jangan membuka dengan basa-basi, jangan menyebut dirimu AI atau model bahasa, dan jangan menampilkan proses berpikir.

Format jawaban: jelaskan pendekatannya dalam beberapa kalimat, lalu tulis solusi lengkap dalam satu blok ```python dengan nama fungsi persis seperti yang diminta, tanpa input() dan tanpa print di luar fungsi. Setelah itu beri contoh pemakaian singkat dan kasus khusus yang ditangani.

---

Tulis fungsi `pasangan_terdekat(titik: list[tuple[float, float]]) -> float` yang mengembalikan jarak Euclid terkecil di antara dua titik dengan indeks berbeda (koordinat boleh int atau float; titik kembar memberi `0.0`). Hasilnya selalu bertipe `float`. Kurang dari dua titik → `ValueError`. Harus selesai dalam beberapa detik untuk 100.000 titik, termasuk ketika semua titik terletak pada satu garis vertikal. Gunakan hanya pustaka standar Python.
````

## ud-077 · python

````text
Jawab pertanyaan di bawah garis dalam bahasa Indonesia yang baku tapi luwes. Langsung ke jawabannya: jangan membuka dengan basa-basi, jangan menyebut dirimu AI atau model bahasa, dan jangan menampilkan proses berpikir.

Format jawaban: jelaskan pendekatannya dalam beberapa kalimat, lalu tulis solusi lengkap dalam satu blok ```python dengan nama fungsi persis seperti yang diminta, tanpa input() dan tanpa print di luar fungsi. Setelah itu beri contoh pemakaian singkat dan kasus khusus yang ditangani.

---

Tulis fungsi `leluhur_bersama(n: int, sisi: list[tuple[int, int]], akar: int, kueri: list[tuple[int, int]]) -> list[int]`. Sebuah pohon tak berarah dengan simpul 0 sampai n−1 diberikan lewat daftar sisinya. Jika pohon itu berakar di `akar`, kembalikan leluhur bersama terendah (LCA) untuk setiap kueri `(u, v)`, sesuai urutan kueri (LCA simpul dengan dirinya sendiri adalah simpul itu). Lempar `ValueError` jika sisi tidak membentuk pohon (jumlahnya bukan n−1, ada sisi ke diri sendiri, ada siklus, atau tidak terhubung), atau jika `akar`, ujung sisi, maupun simpul kueri di luar rentang. Harus selesai dalam beberapa detik untuk n = 100.000 dan 100.000 kueri, termasuk pohon berbentuk rantai sepanjang n. Gunakan hanya pustaka standar Python.
````

## ud-078 · python

````text
Jawab pertanyaan di bawah garis dalam bahasa Indonesia yang baku tapi luwes. Langsung ke jawabannya: jangan membuka dengan basa-basi, jangan menyebut dirimu AI atau model bahasa, dan jangan menampilkan proses berpikir.

Format jawaban: jelaskan pendekatannya dalam beberapa kalimat, lalu tulis solusi lengkap dalam satu blok ```python dengan nama fungsi persis seperti yang diminta, tanpa input() dan tanpa print di luar fungsi. Setelah itu beri contoh pemakaian singkat dan kasus khusus yang ditangani.

---

Tulis fungsi `proses_operasi(data: list[int], operasi: list[tuple]) -> list[int]` yang memproses operasi rentang pada salinan `data` (list aslinya tidak boleh berubah). Operasinya: `("tambah", l, r, x)` menambahkan x ke setiap elemen berindeks l sampai r (inklusif), `("jumlah", l, r)` meminta jumlah elemen l sampai r saat itu, dan `("min", l, r)` meminta nilai minimumnya. Kembalikan hasil semua operasi `jumlah` dan `min` sesuai urutan. Lempar `ValueError` untuk nama operasi lain, l > r, atau indeks di luar rentang. Harus selesai dalam beberapa detik untuk 60.000 elemen dan 60.000 operasi. Gunakan hanya pustaka standar Python.
````

## ud-079 · python

````text
Jawab pertanyaan di bawah garis dalam bahasa Indonesia yang baku tapi luwes. Langsung ke jawabannya: jangan membuka dengan basa-basi, jangan menyebut dirimu AI atau model bahasa, dan jangan menampilkan proses berpikir.

Format jawaban: jelaskan pendekatannya dalam beberapa kalimat, lalu tulis solusi lengkap dalam satu blok ```python dengan nama fungsi persis seperti yang diminta, tanpa input() dan tanpa print di luar fungsi. Setelah itu beri contoh pemakaian singkat dan kasus khusus yang ditangani.

---

Tulis fungsi `logaritma_diskrit(g: int, h: int, p: int) -> int | None` yang mencari bilangan bulat terkecil x ≥ 0 dengan gˣ ≡ h (mod p). `p` dijamin prima dengan 2 ≤ p ≤ 10¹², sedangkan `g` dan `h` boleh bilangan bulat apa pun (negatif atau ≥ p direduksi modulo p dulu). Pakai konvensi 0⁰ = 1, jadi h ≡ 1 selalu memberi 0. Kembalikan `None` jika tidak ada x yang memenuhi. Harus selesai dalam beberapa detik untuk p sekitar 10¹² dengan p − 1 = 2q dan q prima, sehingga mencoba x satu per satu tidak mungkin. Gunakan hanya pustaka standar Python.
````

## ud-080 · python

````text
Jawab pertanyaan di bawah garis dalam bahasa Indonesia yang baku tapi luwes. Langsung ke jawabannya: jangan membuka dengan basa-basi, jangan menyebut dirimu AI atau model bahasa, dan jangan menampilkan proses berpikir.

Format jawaban: jelaskan pendekatannya dalam beberapa kalimat, lalu tulis solusi lengkap dalam satu blok ```python dengan nama fungsi persis seperti yang diminta, tanpa input() dan tanpa print di luar fungsi. Setelah itu beri contoh pemakaian singkat dan kasus khusus yang ditangani.

---

Tulis fungsi `tur_terpendek(jarak: list[list[int]]) -> tuple[int, list[int]]` untuk masalah pedagang keliling asimetris: `jarak[i][j]` adalah biaya dari kota i ke kota j (bilangan bulat ≥ 0). Cari tur yang berawal dan berakhir di kota 0, mengunjungi setiap kota lain tepat sekali, dengan total biaya minimum. Kembalikan `(biaya, rute)`, dengan `rute` berupa list n kota yang diawali 0 tanpa mengulang 0 di akhir. Jika ada beberapa tur optimal, kembalikan rute yang terkecil secara leksikografis. Untuk n = 1 hasilnya `(0, [0])`. Matriks kosong, tidak persegi, atau berisi bilangan negatif → `ValueError`. Harus selesai dalam beberapa detik untuk n = 14. Gunakan hanya pustaka standar Python.
````
