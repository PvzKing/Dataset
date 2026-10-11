from decimal import ROUND_HALF_UP, Decimal

# Bobot ditulis sebagai string: Decimal(0.3) akan membawa galat float 0.299999999999999988897769...
BOBOT = {"tugas": Decimal("0.3"), "uts": Decimal("0.3"), "uas": Decimal("0.4")}
KKM = 75


def nilai_akhir(nilai):
    """Nilai akhir berbobot, dibulatkan ke bilangan bulat dengan aturan sekolah: ,5 ke atas."""
    total = sum(Decimal(str(nilai[k])) * b for k, b in BOBOT.items())
    return int(total.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


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
