# -*- coding: utf-8 -*-
"""
Debug: ¿Por qué se generan múltiples trades del mismo OB?
"""
import sys
import codecs
if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

import pandas as pd

print("\n" + "="*80)
print("  DEBUG: ¿Múltiples trades del mismo OB?")
print("="*80)

# Cargar resultados
df = pd.read_csv("strategies/order_block/backtest/results/ny_trades_LIMIT_ORDERS.csv")

print(f"\nTotal trades: {len(df)}")

# Agrupar por OB (usando zone_high, zone_low, confirmed_at como identificador único)
df['ob_id'] = df.apply(lambda r: f"{r['ob_zone_high']:.2f}_{r['ob_zone_low']:.2f}_{r['ob_confirmed_at']}", axis=1)

# Contar trades por OB
ob_counts = df.groupby('ob_id').size().sort_values(ascending=False)

print(f"\n📊 OBs únicos: {len(ob_counts)}")
print(f"   Trades totales: {len(df)}")
print(f"   Promedio trades/OB: {len(df)/len(ob_counts):.2f}")

# OBs con múltiples trades
multiple = ob_counts[ob_counts > 1]
print(f"\n⚠️  OBs con MÚLTIPLES trades: {len(multiple)} ({len(multiple)/len(ob_counts)*100:.1f}%)")

if len(multiple) > 0:
    print(f"\n  Top 10 OBs con más trades:")
    for ob_id, count in multiple.head(10).items():
        print(f"    {count} trades: {ob_id[:30]}...")
    
    # Analizar un caso específico
    top_ob = multiple.index[0]
    df_top = df[df['ob_id'] == top_ob].sort_values('entry_time')
    
    print(f"\n" + "="*80)
    print(f"  EJEMPLO: OB con {multiple.iloc[0]} trades")
    print("="*80)
    
    print(f"\n  OB: {top_ob}")
    print(f"  Trades:")
    
    for idx, row in df_top.iterrows():
        print(f"\n    Trade #{row['trade_id']}:")
        print(f"      Entry time: {row['entry_time']}")
        print(f"      Exit time:  {row['exit_time']}")
        print(f"      Direction:  {row['direction']}")
        print(f"      Entry:      {row['entry_price']:.2f}")
        print(f"      Exit:       {row['exit_price']:.2f}")
        print(f"      Reason:     {row['exit_reason']}")
        print(f"      PnL:        ${row['pnl_usd']:.2f}")

print("\n" + "="*80)
print("  CONCLUSIÓN")
print("="*80)

if len(multiple) > 0:
    print(f"\n  ❌ BUG CONFIRMADO:")
    print(f"     {len(multiple)} OBs generaron múltiples trades")
    print(f"     Esto NO debería pasar")
    print(f"     Un OB debe generar máximo 1 trade")
else:
    print(f"\n  ✅ NO HAY BUG:")
    print(f"     Cada OB generó máximo 1 trade")

print("\n" + "="*80)
