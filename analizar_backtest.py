# -*- coding: utf-8 -*-
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import pandas as pd

df = pd.read_csv('strategies/pivot_scalping/data/backtest_M5M1_baseline_29d.csv')

print("="*80)
print("ANALISIS DE SL EN TRADES")
print("="*80)

# Analizar SHORTS
shorts = df[df['type'] == 'short']
print(f"\nSHORTS ({len(shorts)} trades):")
print("-"*80)

for _, t in shorts.head(10).iterrows():
    sl_position = "ARRIBA OK" if t['stop_loss'] > t['entry_price'] else "ABAJO ERROR"
    tp_position = "ABAJO OK" if t['take_profit'] < t['entry_price'] else "ARRIBA ERROR"
    
    print(f"\nTrade #{int(t['trade_id'])}:")
    print(f"  Entry: {t['entry_price']:.2f}")
    print(f"  SL:    {t['stop_loss']:.2f} ({sl_position}) - Diff: {t['stop_loss'] - t['entry_price']:+.2f} pts")
    print(f"  TP:    {t['take_profit']:.2f} ({tp_position}) - Diff: {t['take_profit'] - t['entry_price']:+.2f} pts")
    print(f"  Exit:  {t['exit_price']:.2f} - Status: {t['status']}")
    print(f"  PnL:   {t['pnl_usd']:.2f} USD ({t['r_multiple']:.2f}R)")

# Analizar LONGS
longs = df[df['type'] == 'long']
print(f"\n\nLONGS ({len(longs)} trades):")
print("-"*80)

for _, t in longs.iterrows():
    sl_position = "ABAJO OK" if t['stop_loss'] < t['entry_price'] else "ARRIBA ERROR"
    tp_position = "ARRIBA OK" if t['take_profit'] > t['entry_price'] else "ABAJO ERROR"
    
    print(f"\nTrade #{int(t['trade_id'])}:")
    print(f"  Entry: {t['entry_price']:.2f}")
    print(f"  SL:    {t['stop_loss']:.2f} ({sl_position}) - Diff: {t['stop_loss'] - t['entry_price']:+.2f} pts")
    print(f"  TP:    {t['take_profit']:.2f} ({tp_position}) - Diff: {t['take_profit'] - t['entry_price']:+.2f} pts")
    print(f"  Exit:  {t['exit_price']:.2f} - Status: {t['status']}")
    print(f"  PnL:   {t['pnl_usd']:.2f} USD ({t['r_multiple']:.2f}R)")

print("\n" + "="*80)
print("RESUMEN")
print("="*80)

# Contar SL invertidos
shorts_sl_wrong = len(shorts[shorts['stop_loss'] < shorts['entry_price']])
longs_sl_wrong = len(longs[longs['stop_loss'] > longs['entry_price']])

print(f"\nSHORTS con SL ABAJO (incorrecto): {shorts_sl_wrong}/{len(shorts)}")
print(f"LONGS con SL ARRIBA (incorrecto): {longs_sl_wrong}/{len(longs)}")

if shorts_sl_wrong > 0 or longs_sl_wrong > 0:
    print("\nHAY UN BUG: Los SL estan invertidos en algunos trades")
else:
    print("\nTodos los SL estan correctos")
