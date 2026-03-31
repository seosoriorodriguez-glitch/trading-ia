# -*- coding: utf-8 -*-
"""
Investigar por qué los trades SHORT no pasan los filtros después de la corrección
"""
import sys
import codecs
if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from strategies.order_block.backtest.config import DEFAULT_PARAMS

print("\n" + "="*80)
print("  ANÁLISIS DE FILTROS DE RIESGO PARA SHORT")
print("="*80)

params = DEFAULT_PARAMS.copy()

print(f"\n📋 PARÁMETROS DE RIESGO:")
print(f"  buffer_points:    {params['buffer_points']}")
print(f"  min_risk_points:  {params['min_risk_points']}")
print(f"  max_risk_points:  {params['max_risk_points']}")
print(f"  target_rr:        {params['target_rr']}")
print(f"  min_rr_ratio:     {params['min_rr_ratio']}")

print(f"\n" + "="*80)
print("  SIMULACIÓN: Trade SHORT #7 del backtest anterior")
print("="*80)

# Datos del trade #7 original
ob_zone_high = 48454.03
ob_zone_low = 48443.53
entry_price = 48496.71
buffer = params['buffer_points']
target_rr = params['target_rr']

print(f"\n📊 DATOS:")
print(f"  OB bearish:")
print(f"    Zone High: {ob_zone_high:.2f}")
print(f"    Zone Low:  {ob_zone_low:.2f}")
print(f"  Entry:       {entry_price:.2f}")

print(f"\n🔧 CÁLCULO CON BUG (anterior):")
sl_bug = ob_zone_high + buffer
tp_bug = entry_price - (sl_bug - entry_price) * target_rr
risk_bug = abs(entry_price - sl_bug)

print(f"  sl = zone_high + buffer")
print(f"  sl = {ob_zone_high:.2f} + {buffer} = {sl_bug:.2f}")
print(f"  tp = entry - (sl - entry) × target_rr")
print(f"  tp = {entry_price:.2f} - ({sl_bug:.2f} - {entry_price:.2f}) × {target_rr}")
print(f"  tp = {tp_bug:.2f}")
print(f"  Risk: {risk_bug:.2f} puntos")

print(f"\n  ✅ Filtros:")
print(f"    min_risk ({params['min_risk_points']}): {risk_bug:.2f} >= {params['min_risk_points']} → {'✅ PASA' if risk_bug >= params['min_risk_points'] else '❌ NO PASA'}")
print(f"    max_risk ({params['max_risk_points']}): {risk_bug:.2f} <= {params['max_risk_points']} → {'✅ PASA' if risk_bug <= params['max_risk_points'] else '❌ NO PASA'}")

print(f"\n🔧 CÁLCULO CORREGIDO (nuevo):")
tp_corr = ob_zone_high + buffer
risk_corr = abs(entry_price - tp_corr)
sl_corr = entry_price + risk_corr * target_rr

print(f"  tp = zone_high + buffer")
print(f"  tp = {ob_zone_high:.2f} + {buffer} = {tp_corr:.2f}")
print(f"  risk = |entry - tp|")
print(f"  risk = |{entry_price:.2f} - {tp_corr:.2f}| = {risk_corr:.2f} puntos")
print(f"  sl = entry + risk × target_rr")
print(f"  sl = {entry_price:.2f} + {risk_corr:.2f} × {target_rr} = {sl_corr:.2f}")

print(f"\n  ✅ Filtros:")
print(f"    min_risk ({params['min_risk_points']}): {risk_corr:.2f} >= {params['min_risk_points']} → {'✅ PASA' if risk_corr >= params['min_risk_points'] else '❌ NO PASA'}")
print(f"    max_risk ({params['max_risk_points']}): {risk_corr:.2f} <= {params['max_risk_points']} → {'✅ PASA' if risk_corr <= params['max_risk_points'] else '❌ NO PASA'}")

print(f"\n" + "="*80)
print("  CONCLUSIÓN")
print("="*80)

if risk_corr > params['max_risk_points']:
    print(f"\n  ❌ EL PROBLEMA:")
    print(f"  Con la corrección, el riesgo para SHORT es {risk_corr:.2f} puntos")
    print(f"  Esto EXCEDE el max_risk_points de {params['max_risk_points']}")
    print(f"  Por eso los trades SHORT son RECHAZADOS")
    
    print(f"\n  💡 EXPLICACIÓN:")
    print(f"  Para SHORT:")
    print(f"    • TP está en zone_high + buffer = {tp_corr:.2f} (debajo del entry)")
    print(f"    • Entry está en {entry_price:.2f}")
    print(f"    • Risk = {risk_corr:.2f} puntos")
    print(f"    • SL = entry + risk × {target_rr} = {sl_corr:.2f} (muy arriba)")
    
    print(f"\n  Con el bug (anterior):")
    print(f"    • 'sl' estaba en {sl_bug:.2f} (realmente era el TP)")
    print(f"    • Risk calculado: {risk_bug:.2f} puntos ✅ Pasaba el filtro")
    
    print(f"\n  Con la corrección:")
    print(f"    • SL está en {sl_corr:.2f} (correctamente arriba)")
    print(f"    • Risk calculado: {risk_corr:.2f} puntos ❌ NO pasa el filtro")
else:
    print(f"\n  ✅ Los filtros deberían pasar")
    print(f"  Hay otro problema que impide los trades SHORT")

print(f"\n" + "="*80)
print("  SOLUCIONES POSIBLES")
print("="*80)

print(f"\n  1️⃣  AUMENTAR max_risk_points:")
print(f"     Actual: {params['max_risk_points']}")
print(f"     Necesario: ~{risk_corr:.0f} o más")
print(f"     Recomendado: {risk_corr * 1.2:.0f} (con margen)")

print(f"\n  2️⃣  REDUCIR target_rr para SHORT:")
print(f"     Actual: {target_rr}")
print(f"     Alternativa: 1.5 o 2.0")
print(f"     Esto reduciría el SL y el riesgo")

print(f"\n  3️⃣  ACEPTAR QUE SOLO OPERE LONG:")
print(f"     Si los SHORT requieren demasiado riesgo,")
print(f"     puede ser más seguro operar solo LONG")

print("\n" + "="*80)
