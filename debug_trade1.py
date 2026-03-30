# -*- coding: utf-8 -*-
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import pandas as pd

df = pd.read_csv('strategies/pivot_scalping/data/backtest_M5M1_baseline_29d.csv')
t1 = df.iloc[0]

print("Trade #1:")
print(f"Type: {t1['type']}")
print(f"Entry: {t1['entry_price']}")
print(f"SL: {t1['stop_loss']}")
print(f"TP: {t1['take_profit']}")
print(f"Exit: {t1['exit_price']}")
print(f"Status: {t1['status']}")

print("\nSi el codigo es correcto (SHORT):")
print(f"SL = pivot.price_high + 20")
print(f"→ pivot.price_high = {t1['stop_loss'] - 20:.2f}")
print(f"\nPero el SL esta ABAJO del entry, lo cual es imposible si:")
print(f"- Es un SHORT en un pivot HIGH (resistencia)")
print(f"- El pivot HIGH debe estar cerca del entry")
print(f"- El SL debe estar ARRIBA del pivot HIGH")

print(f"\n¿Que esta pasando?")
print(f"Si SL = 49643.61 y buffer = 20:")
print(f"→ pivot.price_high = 49623.61")
print(f"→ Entry = 49659.61")
print(f"\nEl entry esta 36 puntos ARRIBA del pivot.price_high!")
print(f"Eso no tiene sentido para un SHORT en resistencia.")
