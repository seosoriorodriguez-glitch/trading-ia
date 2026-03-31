# -*- coding: utf-8 -*-
"""
Debug: Por qué no se generan trades SHORT
"""
import sys
import codecs
if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd
from strategies.order_block.backtest.backtester import OrderBlockBacktester
from strategies.order_block.backtest.config import DEFAULT_PARAMS
from strategies.order_block.backtest.data_loader import load_csv
from strategies.order_block.backtest.ob_detection import detect_order_blocks

print("\n" + "="*80)
print("  DEBUG: ¿Por qué no se generan trades SHORT?")
print("="*80)

# Cargar datos
print("\nCargando datos...")
df_m5 = load_csv("data/US30_cash_M5_260d.csv")
df_m1 = load_csv("data/US30_cash_M1_260d.csv")

start = max(df_m5["time"].iloc[0], df_m1["time"].iloc[0])
end   = min(df_m5["time"].iloc[-1], df_m1["time"].iloc[-1])
df_m5 = df_m5[(df_m5["time"] >= start) & (df_m5["time"] <= end)].reset_index(drop=True)
df_m1 = df_m1[(df_m1["time"] >= start) & (df_m1["time"] <= end)].reset_index(drop=True)

print(f"  Período: {start} -> {end}")

# Configuración
params = DEFAULT_PARAMS.copy()
params["sessions"] = {"new_york": {"start": "13:30", "end": "20:00", "skip_minutes": 15}}

# Detectar OBs
print("\nDetectando OBs...")
all_obs = detect_order_blocks(df_m5, params)
bearish_obs = [ob for ob in all_obs if ob.ob_type == "bearish"]

print(f"  Total OBs: {len(all_obs)}")
print(f"  Bearish:   {len(bearish_obs)}")

# Tomar un OB bearish de ejemplo
if bearish_obs:
    ob = bearish_obs[0]
    print(f"\n📊 EJEMPLO: OB Bearish #1")
    print(f"  Zone High: {ob.zone_high:.2f}")
    print(f"  Zone Low:  {ob.zone_low:.2f}")
    print(f"  Confirmed: {ob.confirmed_at}")
    
    # Simular entry
    entry_price = ob.zone_high - 10  # Entry dentro de la zona
    
    print(f"\n🔧 SIMULACIÓN DE ENTRADA:")
    print(f"  Entry simulado: {entry_price:.2f}")
    
    # Calcular SL/TP
    from strategies.order_block.backtest.risk_manager import calculate_sl_tp
    
    sl, tp = calculate_sl_tp(ob, entry_price, params)
    
    if sl is None:
        print(f"\n  ❌ calculate_sl_tp retornó None")
        print(f"  El trade fue RECHAZADO por los filtros")
        
        # Calcular manualmente para ver qué filtro falló
        buf = params["buffer_points"]
        target_rr = params["target_rr"]
        
        tp_calc = ob.zone_high + buf
        risk_pts = abs(entry_price - tp_calc)
        sl_calc = entry_price + risk_pts * target_rr
        
        print(f"\n  📐 CÁLCULO MANUAL:")
        print(f"    TP:   {tp_calc:.2f}")
        print(f"    Risk: {risk_pts:.2f} puntos")
        print(f"    SL:   {sl_calc:.2f}")
        
        print(f"\n  ✅ FILTROS:")
        print(f"    min_risk ({params['min_risk_points']}): {risk_pts:.2f} >= {params['min_risk_points']} → {'✅' if risk_pts >= params['min_risk_points'] else '❌'}")
        print(f"    max_risk ({params['max_risk_points']}): {risk_pts:.2f} <= {params['max_risk_points']} → {'✅' if risk_pts <= params['max_risk_points'] else '❌'}")
        
        reward_pts = abs(tp_calc - entry_price)
        rr = reward_pts / risk_pts if risk_pts > 0 else 0
        print(f"    min_rr ({params['min_rr_ratio']}): {rr:.2f} >= {params['min_rr_ratio']} → {'✅' if rr >= params['min_rr_ratio'] else '❌'}")
        
    else:
        print(f"\n  ✅ calculate_sl_tp PASÓ")
        print(f"    SL: {sl:.2f}")
        print(f"    TP: {tp:.2f}")
        
        # Verificar que estén correctos
        if sl > entry_price and tp < entry_price:
            print(f"\n  ✅ SL/TP correctos para SHORT")
        else:
            print(f"\n  ❌ SL/TP INCORRECTOS")
            print(f"    SL debería estar ARRIBA: {sl:.2f} {'✅' if sl > entry_price else '❌'}")
            print(f"    TP debería estar DEBAJO: {tp:.2f} {'✅' if tp < entry_price else '❌'}")

print("\n" + "="*80)
