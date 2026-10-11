from decimal import ROUND_HALF_UP, Decimal

print(round(74.5), round(84.5), round(85.5))
print(round(2.675, 2), Decimal("2.675").quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
