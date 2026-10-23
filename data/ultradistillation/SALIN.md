# Pertanyaan ultradistillation yang belum dijawab (16 dari 80)

Salin satu blok ke **percakapan baru** di AI-nya. Setelah AI menjawab, salin jawabannya dengan tombol salin (supaya format Markdown dan blok kodenya ikut), lalu kirim ke chat dengan baris pertama `<id> · <nama AI dan versinya>`.

## ud-065 · python

````text
Jawab pertanyaan di bawah garis dalam bahasa Indonesia yang baku tapi luwes. Langsung ke jawabannya: jangan membuka dengan basa-basi, jangan menyebut dirimu AI atau model bahasa, dan jangan menampilkan proses berpikir.

Format jawaban: jelaskan pendekatannya dalam beberapa kalimat, lalu tulis solusi lengkap dalam satu blok ```python dengan nama fungsi persis seperti yang diminta, tanpa input() dan tanpa print di luar fungsi. Setelah itu beri contoh pemakaian singkat dan kasus khusus yang ditangani.

---

Tulis fungsi `urai_json(teks: str) -> object` yang mengurai dokumen JSON sesuai RFC 8259 tanpa memakai modul `json` (juga tanpa `eval` atau `ast`). Objek menjadi dict (untuk kunci kembar nilai terakhir yang menang, dengan posisi kunci mengikuti kemunculan pertamanya), larik menjadi list, string menjadi str, `true`/`false`/`null` menjadi True/False/None, angka tanpa pecahan dan eksponen menjadi int berapa pun besarnya, dan angka lain menjadi float. Escape yang sah hanya `\" \\ \/ \b \f \n \r \t \uXXXX`; pasangan surrogate seperti `😀` digabung menjadi satu karakter, sedangkan surrogate tunggal dibiarkan apa adanya (seperti modul `json`). Lempar `ValueError` untuk dokumen yang tidak sah, antara lain angka dengan nol di depan, `+1`, `.5`, `1.`, `NaN`/`Infinity`, koma di akhir, kunci tanpa tanda kutip, karakter kontrol mentah di dalam string, sisa teks setelah nilai, dan whitespace selain spasi, tab, LF, dan CR. Pengurai harus sanggup menangani larik atau objek bersarang sedalam 50.000 tingkat tanpa `RecursionError`, serta dokumen sebesar 0,5 MB dalam beberapa detik. Gunakan hanya pustaka standar Python.
````

## ud-066 · python

````text
Jawab pertanyaan di bawah garis dalam bahasa Indonesia yang baku tapi luwes. Langsung ke jawabannya: jangan membuka dengan basa-basi, jangan menyebut dirimu AI atau model bahasa, dan jangan menampilkan proses berpikir.

Format jawaban: jelaskan pendekatannya dalam beberapa kalimat, lalu tulis solusi lengkap dalam satu blok ```python dengan nama fungsi persis seperti yang diminta, tanpa input() dan tanpa print di luar fungsi. Setelah itu beri contoh pemakaian singkat dan kasus khusus yang ditangani.

---

Basis data SQLite sebuah toko daring punya tabel berikut:

```sql
CREATE TABLE pelanggan (id INTEGER PRIMARY KEY, nama TEXT NOT NULL, kota TEXT);
CREATE TABLE pesanan (id INTEGER PRIMARY KEY, pelanggan_id INTEGER NOT NULL REFERENCES pelanggan(id),
                      tanggal TEXT NOT NULL, status TEXT NOT NULL);
CREATE TABLE item_pesanan (pesanan_id INTEGER NOT NULL REFERENCES pesanan(id), produk TEXT NOT NULL,
                           jumlah INTEGER NOT NULL, harga_satuan INTEGER NOT NULL);
```

`tanggal` berformat `YYYY-MM-DD`. Tulis fungsi Python `laporan_penjualan(conn: sqlite3.Connection) -> list[tuple]` yang menjalankan **tepat satu** kueri SQL (CTE dan window function boleh; jangan membuat tabel sementara atau mengolah data mentah di Python) dan mengembalikan satu baris untuk setiap kombinasi bulan dan kota yang punya minimal satu pesanan berstatus `'selesai'`: `(bulan 'YYYY-MM', kota, omzet, jumlah_pelanggan, peringkat, omzet_kumulatif, pertumbuhan)`. Ketentuannya: hanya pesanan `'selesai'` yang dihitung; kota pelanggan yang NULL ditulis `'Tidak diketahui'`; omzet adalah jumlah `jumlah * harga_satuan` (pesanan selesai tanpa item tetap dihitung dengan omzet 0); jumlah_pelanggan adalah banyaknya pelanggan berbeda yang punya pesanan selesai di bulan dan kota itu; peringkat adalah peringkat padat (tanpa lompatan saat seri) kota dalam bulan yang sama menurut omzet terbesar; omzet_kumulatif adalah total omzet kota itu dari bulan pertamanya sampai bulan tersebut; pertumbuhan adalah persentase perubahan omzet dibanding **bulan kalender sebelumnya** untuk kota yang sama, dibulatkan 1 desimal, dan NULL jika bulan sebelumnya tidak ada atau omzetnya 0 (Januari dibandingkan dengan Desember tahun sebelumnya). Urutkan menurut bulan, peringkat, lalu nama kota. Jelaskan juga indeks apa yang akan Anda tambahkan jika tabelnya berisi jutaan baris. Gunakan hanya pustaka standar Python.
````

## ud-067 · python

````text
Jawab pertanyaan di bawah garis dalam bahasa Indonesia yang baku tapi luwes. Langsung ke jawabannya: jangan membuka dengan basa-basi, jangan menyebut dirimu AI atau model bahasa, dan jangan menampilkan proses berpikir.

Format jawaban: jelaskan pendekatannya dalam beberapa kalimat, lalu tulis solusi lengkap dalam satu blok ```python dengan nama fungsi persis seperti yang diminta, tanpa input() dan tanpa print di luar fungsi. Setelah itu beri contoh pemakaian singkat dan kasus khusus yang ditangani.

---

Rancang penyimpan kunci–nilai di memori yang mendukung transaksi bersarang. Tulis sebuah kelas dan fungsi `buat_penyimpan()` yang mengembalikan objek baru dari kelas itu, dengan metode: `atur(kunci, nilai)`; `ambil(kunci)` yang mengembalikan nilai atau `None`; `hapus(kunci)` (tanpa error jika kunci tidak ada); `hitung(nilai)` yang mengembalikan banyaknya kunci yang saat ini bernilai itu; `mulai()` yang membuka transaksi baru di dalam transaksi yang sedang terbuka; `batal()` yang membatalkan semua perubahan di transaksi terdalam lalu menutupnya; dan `komit()` yang menutup transaksi terdalam dan menggabungkan perubahannya ke transaksi di luarnya (perubahan baru permanen setelah transaksi terluar dikomit). `batal()` atau `komit()` tanpa transaksi terbuka → `RuntimeError`, dan nilai `None` → `ValueError`. Kompleksitasnya: `ambil` dan `hitung` O(1) berapa pun kedalaman transaksinya, sedangkan `batal` dan `komit` sebanding dengan banyaknya kunci yang diubah di transaksi itu, bukan dengan ukuran seluruh data; 100.000 kunci dengan 2.000 transaksi bersarang harus tetap cepat. Jelaskan struktur data dan alasan kompleksitasnya. Gunakan hanya pustaka standar Python.
````

## ud-068 · python

````text
Jawab pertanyaan di bawah garis dalam bahasa Indonesia yang baku tapi luwes. Langsung ke jawabannya: jangan membuka dengan basa-basi, jangan menyebut dirimu AI atau model bahasa, dan jangan menampilkan proses berpikir.

Format jawaban: jelaskan pendekatannya dalam beberapa kalimat, lalu tulis solusi lengkap dalam satu blok ```python dengan nama fungsi persis seperti yang diminta, tanpa input() dan tanpa print di luar fungsi. Setelah itu beri contoh pemakaian singkat dan kasus khusus yang ditangani.

---

Kali ini yang diminta adalah **tes**, bukan implementasi. Spesifikasi fungsi `gabung_rentang(rentang: list[tuple[int, int]]) -> list[tuple[int, int]]`: setiap rentang `(a, b)` adalah rentang bilangan bulat tertutup dengan a ≤ b (bilangan negatif boleh); rentang yang tumpang tindih atau bersebelahan, misalnya (1, 3) dan (4, 6), digabung; hasilnya list tuple yang urut menurut awal rentang; list masukan tidak boleh diubah; list kosong menghasilkan `[]`; dan rentang dengan a > b → `ValueError`. Tulis fungsi `uji_gabung_rentang(fungsi)` yang menguji sebuah implementasi `fungsi` terhadap spesifikasi itu: kembalikan `None` jika implementasinya benar, dan lempar `AssertionError` jika ada penyimpangan apa pun, termasuk jika implementasi itu melempar exception yang tidak semestinya. Fungsi uji Anda akan dijalankan pada beberapa implementasi benar yang ditulis dengan cara berbeda dan pada belasan implementasi salah dengan bug halus; semua implementasi salah harus tertangkap, dan tidak boleh ada implementasi benar yang ditolak. Jelaskan strategi pengujian Anda, misalnya kasus batas, tes acak dengan oracle, dan tes properti. Gunakan hanya pustaka standar Python.
````

## ud-069 · python

````text
Jawab pertanyaan di bawah garis dalam bahasa Indonesia yang baku tapi luwes. Langsung ke jawabannya: jangan membuka dengan basa-basi, jangan menyebut dirimu AI atau model bahasa, dan jangan menampilkan proses berpikir.

Format jawaban: jelaskan pendekatannya dalam beberapa kalimat, lalu tulis solusi lengkap dalam satu blok ```python dengan nama fungsi persis seperti yang diminta, tanpa input() dan tanpa print di luar fungsi. Setelah itu beri contoh pemakaian singkat dan kasus khusus yang ditangani.

---

Tulis fungsi `cron_berikutnya(ekspresi: str, setelah: datetime.datetime) -> datetime.datetime` yang mengembalikan waktu paling awal yang **lebih dari** `setelah` (detik dan mikrodetik dibuang) dan cocok dengan ekspresi cron lima kolom: menit (0–59), jam (0–23), tanggal (1–31), bulan (1–12 atau JAN–DEC), dan hari dalam minggu (0–7 atau SUN–SAT; 0 dan 7 sama-sama Minggu). Nama tidak peka huruf besar-kecil. Setiap kolom boleh berisi `*`, angka, rentang `a-b`, daftar dengan koma, dan langkah `/n` setelah `*`, rentang, atau angka (`5/20` berarti 5, 25, 45, seperti Vixie cron). Aturan tanggal dan hari juga mengikuti Vixie cron: jika kolom tanggal atau kolom hari diawali `*` (termasuk `*/2`), keduanya harus cocok; jika keduanya tidak diawali `*`, cukup salah satu yang cocok. Lempar `ValueError` untuk ekspresi yang tidak sah (jumlah kolom bukan lima, nilai di luar rentang, rentang terbalik, langkah 0, nama tak dikenal, atau bagian kosong) dan jika tidak ada waktu yang cocok dalam 50 tahun ke depan, misalnya tanggal 31 April. Pencarian harus cepat, jadi jangan memeriksa menit demi menit. Gunakan hanya pustaka standar Python.
````

## ud-070 · web

````text
Jawab pertanyaan di bawah garis dalam bahasa Indonesia yang baku tapi luwes. Langsung ke jawabannya: jangan membuka dengan basa-basi, jangan menyebut dirimu AI atau model bahasa, dan jangan menampilkan proses berpikir.

Format jawaban: satu kalimat pembuka, lalu satu dokumen HTML lengkap dalam satu blok ```html. CSS dan JavaScript ada di dalam file itu, tanpa library, font, gambar, atau file dari luar. Halaman harus responsif sampai lebar 375 px, tanpa error JavaScript, dan akses localStorage dibungkus try/catch. Setelah kode, tulis bagian **Cek kebutuhan** berupa daftar `- **<hal yang diminta>** → <bagian kode yang memenuhinya>` untuk setiap permintaan, lalu **Catatan teknis** singkat.

---

Buat komponen combobox pilih-banyak yang aksesibel dalam satu file HTML untuk memilih kota tujuan pengiriman dari minimal 100 nama kota/kabupaten di Indonesia yang disimpan di dalam file. Ikuti pola combobox ARIA 1.2: input `role="combobox"` dengan `aria-expanded`, `aria-controls`, `aria-autocomplete="list"`, dan `aria-activedescendant`, serta daftar `role="listbox"` berisi `role="option"` dengan `aria-selected`. Ketikan menyaring daftar tanpa peka huruf besar-kecil maupun diakritik, dengan debounce sekitar 150 ms, dan bagian yang cocok ditandai dengan `<mark>`. Keyboard: panah atas/bawah memindahkan sorotan (berputar di ujung daftar), Home/End, Enter memilih, Escape menutup daftar (Escape kedua mengosongkan input), dan Backspace pada input kosong menghapus pilihan terakhir. Pilihan tampil sebagai chip dengan tombol hapus ber-`aria-label` "Hapus <nama kota>"; maksimal 5 pilihan, disertai pesan yang jelas saat batas tercapai; jumlah hasil diumumkan lewat live region; dan klik di luar komponen menutup daftar. Ketikan pengguna tidak boleh pernah disisipkan sebagai HTML: mengetik `<img src=x onerror=alert(1)>` harus aman. Sediakan tombol Kirim yang menampilkan pilihan sebagai JSON.
````

## ud-071 · python

````text
Jawab pertanyaan di bawah garis dalam bahasa Indonesia yang baku tapi luwes. Langsung ke jawabannya: jangan membuka dengan basa-basi, jangan menyebut dirimu AI atau model bahasa, dan jangan menampilkan proses berpikir.

Format jawaban: jelaskan pendekatannya dalam beberapa kalimat, lalu tulis solusi lengkap dalam satu blok ```python dengan nama fungsi persis seperti yang diminta, tanpa input() dan tanpa print di luar fungsi. Setelah itu beri contoh pemakaian singkat dan kasus khusus yang ditangani.

---

Tulis fungsi `array_sufiks(s: str) -> tuple[list[int], list[int]]` yang mengembalikan suffix array dan LCP array dari string `s`. Suffix array berisi indeks awal semua sufiks `s`, diurutkan secara leksikografis menurut perbandingan string Python biasa (per titik kode Unicode). LCP array sama panjangnya: `lcp[0] = 0`, dan untuk i ≥ 1, `lcp[i]` adalah panjang awalan bersama terpanjang sufiks `sa[i-1]` dan `sa[i]`. String kosong menghasilkan `([], [])`. Fungsi harus selesai dalam beberapa detik untuk string 50.000 karakter, termasuk kasus terburuk seperti `'a' * 50000`, sehingga mengurutkan potongan `s[i:]` secara langsung tidak cukup. Gunakan hanya pustaka standar Python.
````

## ud-072 · python

````text
Jawab pertanyaan di bawah garis dalam bahasa Indonesia yang baku tapi luwes. Langsung ke jawabannya: jangan membuka dengan basa-basi, jangan menyebut dirimu AI atau model bahasa, dan jangan menampilkan proses berpikir.

Format jawaban: jelaskan pendekatannya dalam beberapa kalimat, lalu tulis solusi lengkap dalam satu blok ```python dengan nama fungsi persis seperti yang diminta, tanpa input() dan tanpa print di luar fungsi. Setelah itu beri contoh pemakaian singkat dan kasus khusus yang ditangani.

---

Tulis fungsi `aliran_maksimum(n: int, sisi: list[tuple[int, int, int]], s: int, t: int) -> tuple[int, set[int]]`. Graf berarah punya simpul 0 sampai n−1; setiap sisi `(u, v, kapasitas)` berkapasitas bilangan bulat ≥ 0. Boleh ada sisi ganda dan sisi berlawanan arah; sisi dari simpul ke dirinya sendiri diabaikan. Kembalikan nilai aliran maksimum dari `s` ke `t` beserta himpunan simpul sisi-s dari potongan minimum, yaitu semua simpul yang masih bisa dicapai dari `s` di graf residu setelah aliran maksimum tercapai. Lempar `ValueError` jika `s == t`, jika `s`, `t`, atau ujung sisi di luar rentang, atau jika ada kapasitas negatif. Harus cepat untuk 2.000 simpul dan 20.000 sisi. Gunakan hanya pustaka standar Python.
````

## ud-073 · python

````text
Jawab pertanyaan di bawah garis dalam bahasa Indonesia yang baku tapi luwes. Langsung ke jawabannya: jangan membuka dengan basa-basi, jangan menyebut dirimu AI atau model bahasa, dan jangan menampilkan proses berpikir.

Format jawaban: jelaskan pendekatannya dalam beberapa kalimat, lalu tulis solusi lengkap dalam satu blok ```python dengan nama fungsi persis seperti yang diminta, tanpa input() dan tanpa print di luar fungsi. Setelah itu beri contoh pemakaian singkat dan kasus khusus yang ditangani.

---

Tulis fungsi `dua_sat(n: int, klausa: list[tuple[int, int]]) -> list[bool] | None` untuk menyelesaikan 2-SAT. Variabel bernomor 1 sampai n; literal `k` berarti variabel k bernilai benar dan `-k` berarti salah. Klausa `(a, b)` berarti `a OR b` (boleh `a == b`). Kembalikan list n nilai `bool` untuk variabel 1..n yang memenuhi semua klausa (penugasan mana pun yang sah diterima), atau `None` jika tidak ada. `n = 0` tanpa klausa menghasilkan `[]`. Literal 0 atau yang nomornya melebihi n → `ValueError`. Harus selesai dalam beberapa detik untuk n = 50.000 dan sekitar 150.000 klausa, termasuk rantai implikasi sepanjang puluhan ribu langkah, jadi perhatikan batas rekursi Python. Gunakan hanya pustaka standar Python.
````

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
