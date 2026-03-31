# -*- coding: utf-8 -*-
"""
Verificación exhaustiva de trades LIMIT con BOS
"""
import sys
import codecs
if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

import pandas as pd

print("\n" + "="*80)
print("  VERIFICACIÓN: LIMIT Orders con BOS")
print("="*80)

df = pd.read_csv("strategies/order_block/backtest/results/ny_trades_LIMIT_ORDERS.csv")

print(f"\nTotal trades: {len(df)}")

# Verificar que todos los trades entran en límites correctos
print(f"\n" + "="*80)
print("  1. VERIFICAR ENTRY EN LÍMITES")
print("="*80)

errors = []

for idx, row in df.iterrows():
    direction = row['direction']
    entry = row['entry_price']
    zone_high = row['ob_zone_high']
    zone_low = row['ob_zone_low']
    sl = row['sl']
    tp = row['tp']
    
    # LONG debe entrar en zone_high
    if direction == 'long':
        if abs(entry - zone_high) > 0.5:  # Tolerancia de 0.5 puntos
            errors.append({
                'trade_id': row['trade_id'],
                'error': f"LONG entry {entry:.2f} != zone_high {zone_high:.2f}",
                'diff': abs(entry - zone_high)
            })
    
    # SHORT debe entrar en zone_low
    else:  # short
        if abs(entry - zone_low) > 0.5:
            errors.append({
                'trade_id': row['trade_id'],
                'error': f"SHORT entry {entry:.2f} != zone_low {zone_low:.2f}",
                'diff': abs(entry - zone_low)
            })

if errors:
    print(f"\n❌ {len(errors)} trades con entry incorrecto:")
    for e in errors[:10]:
        print(f"  Trade #{e['trade_id']}: {e['error']} (diff: {e['diff']:.2f})")
else:
    print(f"\n✅ Todos los trades entran en límites correctos")

# Verificar SL/TP
print(f"\n" + "="*80)
print("  2. VERIFICAR SL/TP")
print("="*80)

sl_tp_errors = []

for idx, row in df.iterrows():
    direction = row['direction']
    entry = row['entry_price']
    sl = row['sl']
    tp = row['tp']
    
    # LONG: SL debe estar DEBAJO de entry, TP ARRIBA
    if direction == 'long':
        if sl >= entry:
            sl_tp_errors.append({
                'trade_id': row['trade_id'],
                'error': f"LONG SL {sl:.2f} >= entry {entry:.2f}"
            })
        if tp <= entry:
            sl_tp_errors.append({
                'trade_id': row['trade_id'],
                'error': f"LONG TP {tp:.2f} <= entry {entry:.2f}"
            })
    
    # SHORT: SL debe estar ARRIBA de entry, TP ABAJO
    else:  # short
        if sl <= entry:
            sl_tp_errors.append({
                'trade_id': row['trade_id'],
                'error': f"SHORT SL {sl:.2f} <= entry {entry:.2f}"
            })
        if tp >= entry:
            sl_tp_errors.append({
                'trade_id': row['trade_id'],
                'error': f"SHORT TP {tp:.2f} >= entry {entry:.2f}"
            })

if sl_tp_errors:
    print(f"\n❌ {len(sl_tp_errors)} trades con SL/TP incorrecto:")
    for e in sl_tp_errors[:10]:
        print(f"  Trade #{e['trade_id']}: {e['error']}")
else:
    print(f"\n✅ Todos los SL/TP están correctos")

# Verificar R:R
print(f"\n" + "="*80)
print("  3. VERIFICAR R:R")
print("="*80)

rr_errors = []

for idx, row in df.iterrows():
    direction = row['direction']
    entry = row['entry_price']
    sl = row['sl']
    tp = row['tp']
    
    risk_pts = abs(entry - sl)
    reward_pts = abs(tp - entry)
    rr = reward_pts / risk_pts if risk_pts > 0 else 0
    
    # R:R debe ser ~2.5 (target_rr)
    expected_rr = 2.5
    if abs(rr - expected_rr) > 0.2:  # Tolerancia de 0.2
        rr_errors.append({
            'trade_id': row['trade_id'],
            'direction': direction,
            'rr': rr,
            'expected': expected_rr,
            'diff': abs(rr - expected_rr)
        })

if rr_errors:
    print(f"\n⚠️  {len(rr_errors)} trades con R:R fuera de rango:")
    for e in rr_errors[:10]:
        print(f"  Trade #{e['trade_id']} ({e['direction']}): R:R {e['rr']:.2f} (esperado {e['expected']:.2f})")
else:
    print(f"\n✅ Todos los R:R están en rango esperado (~2.5)")

# Mostrar ejemplos de trades
print(f"\n" + "="*80)
print("  4. EJEMPLOS DE TRADES")
print("="*80)

print(f"\n📈 LONG Trade (primero):")
df_long = df[df['direction'] == 'long'].head(1)
for idx, row in df_long.iterrows():
    print(f"  Trade #{row['trade_id']}")
    print(f"  Entry time:  {row['entry_time']}")
    print(f"  OB Zone:     {row['ob_zone_low']:.2f} - {row['ob_zone_high']:.2f}")
    print(f"  Entry:       {row['entry_price']:.2f} (debe ser ~{row['ob_zone_high']:.2f})")
    print(f"  SL:          {row['sl']:.2f} (debe estar debajo)")
    print(f"  TP:          {row['tp']:.2f} (debe estar arriba)")
    print(f"  Exit:        {row['exit_price']:.2f}")
    print(f"  PnL:         ${row['pnl_usd']:.2f}")
    print(f"  R-multiple:  {row['pnl_r']:.2f}R")

print(f"\n📉 SHORT Trade (primero):")
df_short = df[df['direction'] == 'short'].head(1)
for idx, row in df_short.iterrows():
    print(f"  Trade #{row['trade_id']}")
    print(f"  Entry time:  {row['entry_time']}")
    print(f"  OB Zone:     {row['ob_zone_low']:.2f} - {row['ob_zone_high']:.2f}")
    print(f"  Entry:       {row['entry_price']:.2f} (debe ser ~{row['ob_zone_low']:.2f})")
    print(f"  SL:          {row['sl']:.2f} (debe estar arriba)")
    print(f"  TP:          {row['tp']:.2f} (debe estar abajo)")
    print(f"  Exit:        {row['exit_price']:.2f}")
    print(f"  PnL:         ${row['pnl_usd']:.2f}")
    print(f"  R-multiple:  {row['pnl_r']:.2f}R")

# Resumen final
print(f"\n" + "="*80)
print("  RESUMEN DE VERIFICACIÓN")
print("="*80)

total_errors = len(errors) + len(sl_tp_errors)

if total_errors == 0:
    print(f"\n✅ VERIFICACIÓN EXITOSA")
    print(f"  • Todos los entries en límites correctos")
    print(f"  • Todos los SL/TP correctos")
    print(f"  • R:R consistente (~2.5)")
    print(f"\n  ✅ LISTO PARA IMPLEMENTACIÓN")
else:
    print(f"\n❌ {total_errors} ERRORES ENCONTRADOS")
    print(f"  • Entry errors: {len(errors)}")
    print(f"  • SL/TP errors: {len(sl_tp_errors)}")
    print(f"\n  ⚠️  REQUIERE CORRECCIÓN ANTES DE IMPLEMENTAR")

print("\n" + "="*80)
