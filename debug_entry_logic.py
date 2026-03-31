# -*- coding: utf-8 -*-
"""
Debug: Analizar lógica de entrada - ¿Entra solo DENTRO de la zona?
"""
import sys
import codecs
if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

import pandas as pd

print("\n" + "="*80)
print("  ANÁLISIS: Lógica de Entrada - ¿Solo DENTRO de la zona?")
print("="*80)

# Cargar backtest anterior
df = pd.read_csv("strategies/order_block/backtest/results/ny_all_trades.csv")

print(f"\n📊 TOTAL TRADES: {len(df)}")
print(f"  LONG:  {len(df[df['direction'] == 'long'])}")
print(f"  SHORT: {len(df[df['direction'] == 'short'])}")

# Analizar LONG
print("\n" + "="*80)
print("  ANÁLISIS LONG")
print("="*80)

df_long = df[df['direction'] == 'long'].copy()
df_long['dentro_zona'] = (df_long['entry_price'] >= df_long['ob_zone_low']) & \
                          (df_long['entry_price'] <= df_long['ob_zone_high'])
df_long['debajo_zona'] = df_long['entry_price'] < df_long['ob_zone_low']
df_long['arriba_zona'] = df_long['entry_price'] > df_long['ob_zone_high']

dentro_long = df_long['dentro_zona'].sum()
debajo_long = df_long['debajo_zona'].sum()
arriba_long = df_long['arriba_zona'].sum()

print(f"\n  Total LONG: {len(df_long)}")
print(f"  Dentro de zona:  {dentro_long} ({dentro_long/len(df_long)*100:.1f}%)")
print(f"  Debajo de zona:  {debajo_long} ({debajo_long/len(df_long)*100:.1f}%)")
print(f"  Arriba de zona:  {arriba_long} ({arriba_long/len(df_long)*100:.1f}%)")

if debajo_long > 0:
    print(f"\n  ⚠️  HAY {debajo_long} LONG que entraron DEBAJO de la zona")
    print(f"  Ejemplos:")
    for idx, row in df_long[df_long['debajo_zona']].head(3).iterrows():
        print(f"    Trade #{row['trade_id']}: Entry {row['entry_price']:.2f} < Zone Low {row['ob_zone_low']:.2f}")

if arriba_long > 0:
    print(f"\n  ⚠️  HAY {arriba_long} LONG que entraron ARRIBA de la zona")
    print(f"  Ejemplos:")
    for idx, row in df_long[df_long['arriba_zona']].head(3).iterrows():
        print(f"    Trade #{row['trade_id']}: Entry {row['entry_price']:.2f} > Zone High {row['ob_zone_high']:.2f}")

# Analizar SHORT
print("\n" + "="*80)
print("  ANÁLISIS SHORT")
print("="*80)

df_short = df[df['direction'] == 'short'].copy()
df_short['dentro_zona'] = (df_short['entry_price'] >= df_short['ob_zone_low']) & \
                           (df_short['entry_price'] <= df_short['ob_zone_high'])
df_short['debajo_zona'] = df_short['entry_price'] < df_short['ob_zone_low']
df_short['arriba_zona'] = df_short['entry_price'] > df_short['ob_zone_high']

dentro_short = df_short['dentro_zona'].sum()
debajo_short = df_short['debajo_zona'].sum()
arriba_short = df_short['arriba_zona'].sum()

print(f"\n  Total SHORT: {len(df_short)}")
print(f"  Dentro de zona:  {dentro_short} ({dentro_short/len(df_short)*100:.1f}%)")
print(f"  Debajo de zona:  {debajo_short} ({debajo_short/len(df_short)*100:.1f}%)")
print(f"  Arriba de zona:  {arriba_short} ({arriba_short/len(df_short)*100:.1f}%)")

if debajo_short > 0:
    print(f"\n  ⚠️  HAY {debajo_short} SHORT que entraron DEBAJO de la zona")
    print(f"  Ejemplos:")
    for idx, row in df_short[df_short['debajo_zona']].head(3).iterrows():
        print(f"    Trade #{row['trade_id']}: Entry {row['entry_price']:.2f} < Zone Low {row['ob_zone_low']:.2f}")

if arriba_short > 0:
    print(f"\n  ⚠️  HAY {arriba_short} SHORT que entraron ARRIBA de la zona")
    print(f"  Ejemplos:")
    for idx, row in df_short[df_short['arriba_zona']].head(3).iterrows():
        print(f"    Trade #{row['trade_id']}: Entry {row['entry_price']:.2f} > Zone High {row['ob_zone_high']:.2f}")
        print(f"      Zone: {row['ob_zone_low']:.2f} - {row['ob_zone_high']:.2f}")
        print(f"      Diferencia: {row['entry_price'] - row['ob_zone_high']:.2f} puntos arriba")

# Análisis de Win Rate por ubicación
print("\n" + "="*80)
print("  WIN RATE POR UBICACIÓN")
print("="*80)

print("\n  LONG:")
if dentro_long > 0:
    wr_dentro_long = df_long[df_long['dentro_zona']]['pnl_usd'].apply(lambda x: x > 0).sum() / dentro_long * 100
    print(f"    Dentro de zona: {wr_dentro_long:.1f}% WR")
if debajo_long > 0:
    wr_debajo_long = df_long[df_long['debajo_zona']]['pnl_usd'].apply(lambda x: x > 0).sum() / debajo_long * 100
    print(f"    Debajo de zona: {wr_debajo_long:.1f}% WR")
if arriba_long > 0:
    wr_arriba_long = df_long[df_long['arriba_zona']]['pnl_usd'].apply(lambda x: x > 0).sum() / arriba_long * 100
    print(f"    Arriba de zona: {wr_arriba_long:.1f}% WR")

print("\n  SHORT:")
if dentro_short > 0:
    wr_dentro_short = df_short[df_short['dentro_zona']]['pnl_usd'].apply(lambda x: x > 0).sum() / dentro_short * 100
    print(f"    Dentro de zona: {wr_dentro_short:.1f}% WR")
if debajo_short > 0:
    wr_debajo_short = df_short[df_short['debajo_zona']]['pnl_usd'].apply(lambda x: x > 0).sum() / debajo_short * 100
    print(f"    Debajo de zona: {wr_debajo_short:.1f}% WR")
if arriba_short > 0:
    wr_arriba_short = df_short[df_short['arriba_zona']]['pnl_usd'].apply(lambda x: x > 0).sum() / arriba_short * 100
    print(f"    Arriba de zona: {wr_arriba_short:.1f}% WR")

# Conclusión
print("\n" + "="*80)
print("  CONCLUSIÓN")
print("="*80)

print(f"\n  📋 LÓGICA ESPERADA:")
print(f"     Entrar solo cuando candle_close está DENTRO de la zona OB")
print(f"     zone_low <= entry <= zone_high")

print(f"\n  📊 LÓGICA ACTUAL:")
total_fuera = debajo_long + arriba_long + debajo_short + arriba_short
if total_fuera > 0:
    print(f"     ❌ HAY {total_fuera} trades FUERA de la zona ({total_fuera/len(df)*100:.1f}%)")
    print(f"        • LONG debajo: {debajo_long}")
    print(f"        • LONG arriba: {arriba_long}")
    print(f"        • SHORT debajo: {debajo_short}")
    print(f"        • SHORT arriba: {arriba_short}")
else:
    print(f"     ✅ TODOS los trades entraron DENTRO de la zona")

print("\n" + "="*80)
