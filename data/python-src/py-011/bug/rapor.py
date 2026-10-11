BOBOT = {"tugas": 0.3, "uts": 0.3, "uas": 0.4}
KKM = 75


def nilai_akhir(nilai):
    return round(sum(nilai[k] * b for k, b in BOBOT.items()))


def rekap(kelas):
    for nama, nilai in kelas.items():
        akhir = nilai_akhir(nilai)
        status = "Tuntas" if akhir >= KKM else "Tidak tuntas"
        print(f"{nama:<6} {akhir:>3}  {status}")


if __name__ == "__main__":
    rekap({
        "Ayu": {"tugas": 80, "uts": 75, "uas": 70},
        "Bima": {"tugas": 85, "uts": 90, "uas": 80},
        "Citra": {"tugas": 90, "uts": 85, "uas": 81},
        "Dewi": {"tugas": 70, "uts": 71, "uas": 80},
    })
