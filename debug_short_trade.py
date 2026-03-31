# -*- coding: utf-8 -*-
"""
Debug trade SHORT #7 para entender el problema
"""
import sys
import codecs
if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

print("\n" + "="*80)
print("  DEBUG TRADE #7 (SHORT)")
print("="*80)

# Datos del CSV
entry = 48496.71
sl_csv = 48474.03
tp_csv = 48553.41
exit_price = 48474.03
pnl = 465.33
exit_reason = "sl"

# Datos de la zona OB
zone_high = 48454.03
zone_low = 48443.53

print(f"\n📋 DATOS DEL CSV:")
print(f"  Direction:     SHORT")
print(f"  Entry:         {entry:.2f}")
print(f"  SL (CSV):      {sl_csv:.2f}")
print(f"  TP (CSV):      {tp_csv:.2f}")
print(f"  Exit:          {exit_price:.2f}")
print(f"  Exit reason:   {exit_reason}")
print(f"  PnL:           ${pnl:.2f}")

print(f"\n📊 ZONA OB:")
print(f"  Zone High:     {zone_high:.2f}")
print(f"  Zone Low:      {zone_low:.2f}")

print(f"\n🔍 ANÁLISIS:")
print(f"\n  Para SHORT:")
print(f"    Entry: {entry:.2f}")
print(f"    SL (CSV): {sl_csv:.2f} → {'ARRIBA' if sl_csv > entry else 'DEBAJO'} del entry ❌")
print(f"    TP (CSV): {tp_csv:.2f} → {'ARRIBA' if tp_csv > entry else 'DEBAJO'} del entry ❌")

print(f"\n  ✅ DEBERÍA SER:")
print(f"    SL: ARRIBA del entry (> {entry:.2f})")
print(f"    TP: DEBAJO del entry (< {entry:.2f})")

print(f"\n  🤔 PERO... el exit_reason es 'sl' y salió en {exit_price:.2f}")
print(f"     que coincide con sl_csv ({sl_csv:.2f})")
print(f"     Y además fue GANADOR (+${pnl:.2f})")

print(f"\n📐 CÁLCULO SEGÚN CÓDIGO (risk_manager.py):")
print(f"\n  Para SHORT (ob_type='bearish'):")
print(f"    sl = ob.zone_high + buffer")
print(f"    tp = entry_price - (sl - entry_price) * target_rr")

buffer = 20
target_rr = 2.5

sl_calculado = zone_high + buffer
tp_calculado = entry - (sl_calculado - entry) * target_rr

print(f"\n  Zone High: {zone_high:.2f}")
print(f"  Buffer: {buffer}")
print(f"  SL calculado: {zone_high:.2f} + {buffer} = {sl_calculado:.2f}")
print(f"  TP calculado: {entry:.2f} - ({sl_calculado:.2f} - {entry:.2f}) × {target_rr} = {tp_calculado:.2f}")

print(f"\n  🔍 COMPARACIÓN:")
print(f"    SL calculado: {sl_calculado:.2f}")
print(f"    SL en CSV:    {sl_csv:.2f}")
print(f"    ¿Coinciden?   {'✅ SÍ' if abs(sl_calculado - sl_csv) < 1 else '❌ NO'}")

print(f"\n    TP calculado: {tp_calculado:.2f}")
print(f"    TP en CSV:    {tp_csv:.2f}")
print(f"    ¿Coinciden?   {'✅ SÍ' if abs(tp_calculado - tp_csv) < 1 else '❌ NO'}")

# Analizar el PnL
print(f"\n💰 ANÁLISIS DEL PnL:")
print(f"\n  Entry: {entry:.2f}")
print(f"  Exit:  {exit_price:.2f}")
print(f"  Diferencia: {entry - exit_price:.2f} puntos")
print(f"\n  Para SHORT:")
print(f"    Si exit < entry → GANANCIA ✅")
print(f"    Si exit > entry → PÉRDIDA ❌")
print(f"\n  {exit_price:.2f} < {entry:.2f} → GANANCIA de {entry - exit_price:.2f} puntos")
print(f"  PnL reportado: ${pnl:.2f} ✅")

print(f"\n🎯 CONCLUSIÓN:")
print(f"  El trade SHORT es CORRECTO:")
print(f"  • Entry en {entry:.2f}")
print(f"  • Bajó a {exit_price:.2f}")
print(f"  • Ganó {entry - exit_price:.2f} puntos")
print(f"\n  PERO las etiquetas SL/TP están INVERTIDAS en el CSV:")
print(f"  • Lo que dice 'sl' ({sl_csv:.2f}) es realmente el TP")
print(f"  • Lo que dice 'tp' ({tp_csv:.2f}) es realmente el SL")

print("\n" + "="*80)
