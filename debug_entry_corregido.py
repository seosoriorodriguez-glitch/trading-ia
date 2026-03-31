# -*- coding: utf-8 -*-
"""
Debug: Analizar lógica de entrada en backtest CORREGIDO
"""
import sys
import codecs
if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

import pandas as pd

print("\n" + "="*80)
print("  ANÁLISIS: Backtest CORREGIDO - Entradas fuera de zona")
print("="*80)

# Cargar backtest corregido
df = pd.read_csv("strategies/order_block/backtest/results/ny_all_trades_CORREGIDO.csv")

print(f"\n📊 TOTAL TRADES: {len(df)}")
print(f"  LONG:  {len(df[df['direction'] == 'long'])}")
print(f"  SHORT: {len(df[df['direction'] == 'short'])}")

# Analizar SHORT
df_short = df[df['direction'] == 'short'].copy()

if len(df_short) > 0:
    df_short['dentro_zona'] = (df_short['entry_price'] >= df_short['ob_zone_low']) & \
                               (df_short['entry_price'] <= df_short['ob_zone_high'])
    df_short['debajo_zona'] = df_short['entry_price'] < df_short['ob_zone_low']
    df_short['arriba_zona'] = df_short['entry_price'] > df_short['ob_zone_high']

    dentro = df_short['dentro_zona'].sum()
    debajo = df_short['debajo_zona'].sum()
    arriba = df_short['arriba_zona'].sum()

    print(f"\n📊 SHORT:")
    print(f"  Total:           {len(df_short)}")
    print(f"  Dentro de zona:  {dentro} ({dentro/len(df_short)*100:.1f}%)")
    print(f"  Debajo de zona:  {debajo} ({debajo/len(df_short)*100:.1f}%)")
    print(f"  Arriba de zona:  {arriba} ({arriba/len(df_short)*100:.1f}%)")

    if arriba > 0:
        print(f"\n  ⚠️  HAY {arriba} SHORT que entraron ARRIBA de la zona:")
        for idx, row in df_short[df_short['arriba_zona']].head(5).iterrows():
            print(f"\n    Trade #{row['trade_id']}:")
            print(f"      Entry: {row['entry_price']:.2f}")
            print(f"      Zone:  {row['ob_zone_low']:.2f} - {row['ob_zone_high']:.2f}")
            print(f"      Diff:  {row['entry_price'] - row['ob_zone_high']:.2f} puntos arriba")
            print(f"      PnL:   ${row['pnl_usd']:.2f} ({'✅' if row['pnl_usd'] > 0 else '❌'})")

        # Win Rate
        wr_arriba = df_short[df_short['arriba_zona']]['pnl_usd'].apply(lambda x: x > 0).sum() / arriba * 100
        wr_dentro = df_short[df_short['dentro_zona']]['pnl_usd'].apply(lambda x: x > 0).sum() / dentro * 100 if dentro > 0 else 0

        print(f"\n  📊 WIN RATE:")
        print(f"    Dentro de zona: {wr_dentro:.1f}%")
        print(f"    Arriba de zona: {wr_arriba:.1f}%")
else:
    print(f"\n  ⚠️  NO HAY TRADES SHORT en el backtest corregido")

print("\n" + "="*80)
print("  COMPARACIÓN: Anterior vs Corregido")
print("="*80)

# Cargar anterior
df_old = pd.read_csv("strategies/order_block/backtest/results/ny_all_trades.csv")
df_short_old = df_old[df_old['direction'] == 'short'].copy()
df_short_old['arriba_zona'] = df_short_old['entry_price'] > df_short_old['ob_zone_high']
arriba_old = df_short_old['arriba_zona'].sum()

print(f"\n  BACKTEST ANTERIOR (con bug):")
print(f"    Total SHORT:     {len(df_short_old)}")
print(f"    Arriba de zona:  {arriba_old} ({arriba_old/len(df_short_old)*100:.1f}%)")

if len(df_short) > 0:
    print(f"\n  BACKTEST CORREGIDO:")
    print(f"    Total SHORT:     {len(df_short)}")
    print(f"    Arriba de zona:  {arriba} ({arriba/len(df_short)*100:.1f}%)")
    
    print(f"\n  📉 DIFERENCIA:")
    print(f"    Trades SHORT:    {len(df_short) - len(df_short_old)}")
    print(f"    Arriba de zona:  {arriba - arriba_old}")
else:
    print(f"\n  BACKTEST CORREGIDO:")
    print(f"    Total SHORT:     0")
    print(f"    ⚠️  Todos los SHORT fueron eliminados")

print("\n" + "="*80)
