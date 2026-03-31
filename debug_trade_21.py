# -*- coding: utf-8 -*-
"""
Debug Trade #21 para entender por qué SL y TP parecen invertidos
"""
import sys
import codecs
if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

import pandas as pd

# Leer CSV
df = pd.read_csv("strategies/order_block/backtest/results/ny_winners_only.csv")

# Trade #21 (índice 21 en la lista, fila 22 del CSV)
trade_21 = df[df["trade_id"] == 47].iloc[0]

print("\n" + "="*80)
print("  DEBUG TRADE #21 (trade_id=47)")
print("="*80)

print(f"\n📋 DATOS DEL CSV:")
print(f"  Fecha:         {trade_21['entry_time']}")
print(f"  Dirección:     {trade_21['direction']}")
print(f"  Entry:         {trade_21['entry_price']:.2f}")
print(f"  SL (CSV):      {trade_21['sl']:.2f}")
print(f"  TP (CSV):      {trade_21['tp']:.2f}")
print(f"  Exit:          {trade_21['exit_price']:.2f}")
print(f"  PnL:           ${trade_21['pnl_usd']:.2f}")

print(f"\n📊 ZONA OB:")
print(f"  Zone High:     {trade_21['ob_zone_high']:.2f}")
print(f"  Zone Low:      {trade_21['ob_zone_low']:.2f}")
print(f"  OB confirmado: {trade_21['ob_confirmed_at']}")

print(f"\n🔍 ANÁLISIS:")

entry = trade_21['entry_price']
sl_csv = trade_21['sl']
tp_csv = trade_21['tp']
exit_price = trade_21['exit_price']
direction = trade_21['direction']

print(f"\n  Para {direction.upper()}:")
print(f"    Entry: {entry:.2f}")
print(f"    SL (CSV): {sl_csv:.2f} → {'ARRIBA' if sl_csv > entry else 'ABAJO'} del entry")
print(f"    TP (CSV): {tp_csv:.2f} → {'ARRIBA' if tp_csv > entry else 'ABAJO'} del entry")

if direction == "long":
    print(f"\n  ✅ DEBERÍA SER:")
    print(f"    SL: DEBAJO del entry (< {entry:.2f})")
    print(f"    TP: ARRIBA del entry (> {entry:.2f})")
    
    if sl_csv > entry:
        print(f"\n  ❌ ERROR: SL está ARRIBA del entry ({sl_csv:.2f} > {entry:.2f})")
    if tp_csv < entry:
        print(f"  ❌ ERROR: TP está DEBAJO del entry ({tp_csv:.2f} < {entry:.2f})")
    
    # Verificar si intercambiando tiene sentido
    print(f"\n  🔄 SI INTERCAMBIAMOS SL y TP:")
    print(f"    SL: {tp_csv:.2f} (debajo) ✅")
    print(f"    TP: {sl_csv:.2f} (arriba) ✅")
    print(f"    Exit: {exit_price:.2f}")
    
    if exit_price >= sl_csv:
        print(f"    → Exit alcanzó el TP ✅")
    else:
        print(f"    → Exit NO alcanzó el TP ❌")

else:  # short
    print(f"\n  ✅ DEBERÍA SER:")
    print(f"    SL: ARRIBA del entry (> {entry:.2f})")
    print(f"    TP: DEBAJO del entry (< {entry:.2f})")
    
    if sl_csv < entry:
        print(f"\n  ❌ ERROR: SL está DEBAJO del entry ({sl_csv:.2f} < {entry:.2f})")
    if tp_csv > entry:
        print(f"  ❌ ERROR: TP está ARRIBA del entry ({tp_csv:.2f} > {entry:.2f})")

# Verificar la lógica del código
print(f"\n" + "="*80)
print("  VERIFICACIÓN DE LÓGICA DEL CÓDIGO")
print("="*80)

zone_low = trade_21['ob_zone_low']
zone_high = trade_21['ob_zone_high']
buffer = 20  # Buffer actual

print(f"\n📐 CÁLCULO SEGÚN CÓDIGO (risk_manager.py):")

if direction == "long":
    # Código dice: sl = ob.zone_low - buf
    sl_calculado = zone_low - buffer
    # Código dice: tp = entry_price + (entry_price - sl) * target_rr
    tp_calculado = entry + (entry - sl_calculado) * 2.5
    
    print(f"\n  OB bullish → LONG")
    print(f"  Zone Low: {zone_low:.2f}")
    print(f"  Buffer: {buffer}")
    print(f"  SL calculado: {zone_low:.2f} - {buffer} = {sl_calculado:.2f}")
    print(f"  TP calculado: {entry:.2f} + ({entry:.2f} - {sl_calculado:.2f}) × 2.5 = {tp_calculado:.2f}")
    
    print(f"\n  🔍 COMPARACIÓN:")
    print(f"    SL calculado: {sl_calculado:.2f}")
    print(f"    SL en CSV:    {sl_csv:.2f}")
    print(f"    ¿Coinciden?   {'✅ SÍ' if abs(sl_calculado - sl_csv) < 1 else '❌ NO'}")
    
    print(f"\n    TP calculado: {tp_calculado:.2f}")
    print(f"    TP en CSV:    {tp_csv:.2f}")
    print(f"    ¿Coinciden?   {'✅ SÍ' if abs(tp_calculado - tp_csv) < 1 else '❌ NO'}")

print("\n" + "="*80)
