# -*- coding: utf-8 -*-
"""
Analizar cuántos trades MARKET entraron fuera de zona
"""
import sys
import codecs
if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

import pandas as pd

print("\n" + "="*80)
print("  ANÁLISIS: Entradas FUERA vs DENTRO de zona")
print("="*80)

# Cargar backtest MARKET
df = pd.read_csv("strategies/order_block/backtest/results/ny_all_trades.csv")

print(f"\nTotal trades MARKET: {len(df)}")

# Clasificar entradas
def classify_entry(row):
    entry = row['entry_price']
    zone_low = row['ob_zone_low']
    zone_high = row['ob_zone_high']
    direction = row['direction']
    
    if direction == 'long':
        if entry < zone_low:
            return 'below_zone'
        elif entry > zone_high:
            return 'above_zone'
        else:
            return 'inside_zone'
    else:  # short
        if entry < zone_low:
            return 'below_zone'
        elif entry > zone_high:
            return 'above_zone'
        else:
            return 'inside_zone'

df['entry_location'] = df.apply(classify_entry, axis=1)

# Contar por ubicación
print(f"\n📊 UBICACIÓN DE ENTRADAS:")
print(f"\n  Dentro de zona:  {len(df[df['entry_location'] == 'inside_zone'])}")
print(f"  Arriba de zona:  {len(df[df['entry_location'] == 'above_zone'])}")
print(f"  Abajo de zona:   {len(df[df['entry_location'] == 'below_zone'])}")

# Por dirección
print(f"\n📈 LONG:")
df_long = df[df['direction'] == 'long']
print(f"  Total: {len(df_long)}")
print(f"  Dentro: {len(df_long[df_long['entry_location'] == 'inside_zone'])}")
print(f"  Arriba: {len(df_long[df_long['entry_location'] == 'above_zone'])}")
print(f"  Abajo:  {len(df_long[df_long['entry_location'] == 'below_zone'])}")

print(f"\n📉 SHORT:")
df_short = df[df['direction'] == 'short']
print(f"  Total: {len(df_short)}")
print(f"  Dentro: {len(df_short[df_short['entry_location'] == 'inside_zone'])}")
print(f"  Arriba: {len(df_short[df_short['entry_location'] == 'above_zone'])}")
print(f"  Abajo:  {len(df_short[df_short['entry_location'] == 'below_zone'])}")

# Win Rate por ubicación
print(f"\n🎯 WIN RATE POR UBICACIÓN:")

for loc in ['inside_zone', 'above_zone', 'below_zone']:
    df_loc = df[df['entry_location'] == loc]
    if len(df_loc) > 0:
        winners = len(df_loc[df_loc['pnl_usd'] > 0])
        wr = winners / len(df_loc) * 100
        print(f"\n  {loc.upper()}:")
        print(f"    Trades: {len(df_loc)}")
        print(f"    Winners: {winners}")
        print(f"    Win Rate: {wr:.1f}%")

# Win Rate SHORT por ubicación
print(f"\n📉 WIN RATE SHORT POR UBICACIÓN:")

for loc in ['inside_zone', 'above_zone', 'below_zone']:
    df_loc = df_short[df_short['entry_location'] == loc]
    if len(df_loc) > 0:
        winners = len(df_loc[df_loc['pnl_usd'] > 0])
        wr = winners / len(df_loc) * 100
        print(f"\n  {loc.upper()}:")
        print(f"    Trades: {len(df_loc)}")
        print(f"    Winners: {winners}")
        print(f"    Win Rate: {wr:.1f}%")

print(f"\n" + "="*80)
print("  CONCLUSIÓN")
print("="*80)

inside = len(df[df['entry_location'] == 'inside_zone'])
outside = len(df) - inside

print(f"\n  MARKET permite entradas FUERA de zona:")
print(f"    Dentro: {inside} trades")
print(f"    Fuera:  {outside} trades")
print(f"\n  LIMIT solo permite DENTRO de zona")
print(f"    → Por eso LIMIT debería tener MENOS trades")
print(f"    → Pero tiene MÁS ({205} vs {104})")
print(f"\n  ❓ Esto sugiere que hay OTRO factor...")

print("\n" + "="*80)
