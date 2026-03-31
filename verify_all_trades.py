# -*- coding: utf-8 -*-
"""
Verificar que TODOS los trades del CSV tengan SL y TP lógicos
"""
import sys
import codecs
if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

import pandas as pd

# Leer CSV
df = pd.read_csv("strategies/order_block/backtest/results/ny_winners_only.csv")

print("\n" + "="*80)
print("  VERIFICACIÓN DE LÓGICA SL/TP EN TODAS LAS OPERACIONES GANADORAS")
print("="*80)

errors = []

for idx, row in df.iterrows():
    trade_num = idx + 1
    direction = row["direction"]
    entry = row["entry_price"]
    sl = row["sl"]
    tp = row["tp"]
    exit_price = row["exit_price"]
    
    # Verificar lógica según dirección
    if direction == "long":
        # LONG: SL debe estar DEBAJO del entry, TP ARRIBA
        sl_ok = sl < entry
        tp_ok = tp > entry
        
        if not sl_ok:
            errors.append(f"Trade #{trade_num} (LONG): SL {sl:.2f} NO está debajo del entry {entry:.2f}")
        if not tp_ok:
            errors.append(f"Trade #{trade_num} (LONG): TP {tp:.2f} NO está arriba del entry {entry:.2f}")
    
    else:  # short
        # SHORT: SL debe estar ARRIBA del entry, TP DEBAJO
        sl_ok = sl > entry
        tp_ok = tp < entry
        
        if not sl_ok:
            errors.append(f"Trade #{trade_num} (SHORT): SL {sl:.2f} NO está arriba del entry {entry:.2f}")
        if not tp_ok:
            errors.append(f"Trade #{trade_num} (SHORT): TP {tp:.2f} NO está debajo del entry {entry:.2f}")

if errors:
    print(f"\n❌ Se encontraron {len(errors)} errores:\n")
    for error in errors:
        print(f"  • {error}")
else:
    print(f"\n✅ TODAS las {len(df)} operaciones tienen SL y TP correctos")
    print("\n📊 RESUMEN:")
    print(f"  LONG:  {len(df[df['direction'] == 'long'])} trades")
    print(f"  SHORT: {len(df[df['direction'] == 'short'])} trades")
    
    # Verificar algunos trades específicos
    print("\n🔍 VERIFICACIÓN DE TRADES ESPECÍFICOS:")
    
    # Trade #21 (4 febrero)
    t21 = df[df["trade_id"] == 47].iloc[0]
    print(f"\n  Trade #21 (4 feb):")
    print(f"    Dir: {t21['direction'].upper()}")
    print(f"    Entry: {t21['entry_price']:.2f}")
    print(f"    SL:    {t21['sl']:.2f} ({'✅ debajo' if t21['sl'] < t21['entry_price'] else '❌ arriba'})")
    print(f"    TP:    {t21['tp']:.2f} ({'✅ arriba' if t21['tp'] > t21['entry_price'] else '❌ debajo'})")
    print(f"    Exit:  {t21['exit_price']:.2f}")
    
    # Trade #22 (6 febrero)
    t22 = df[df["trade_id"] == 50].iloc[0]
    print(f"\n  Trade #22 (6 feb):")
    print(f"    Dir: {t22['direction'].upper()}")
    print(f"    Entry: {t22['entry_price']:.2f}")
    print(f"    SL:    {t22['sl']:.2f} ({'✅ debajo' if t22['sl'] < t22['entry_price'] else '❌ arriba'})")
    print(f"    TP:    {t22['tp']:.2f} ({'✅ arriba' if t22['tp'] > t22['entry_price'] else '❌ debajo'})")
    print(f"    Exit:  {t22['exit_price']:.2f}")

print("\n" + "="*80)
