# -*- coding: utf-8 -*-
"""
Optimización de R:R y Buffer de SL
"""
import sys
import codecs
if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

import pandas as pd
from strategies.order_block.backtest.backtester_limit_orders import OrderBlockBacktesterLimitOrders
from strategies.order_block.backtest.config import DEFAULT_PARAMS

print("\n" + "="*80)
print("  OPTIMIZACIÓN: R:R y BUFFER SL")
print("="*80)

# Cargar datos
print("\nCargando datos...")
df_m5 = pd.read_csv("data/US30_cash_M5_260d.csv")
df_m1 = pd.read_csv("data/US30_cash_M1_260d.csv")

df_m5["time"] = pd.to_datetime(df_m5["time"])
df_m1["time"] = pd.to_datetime(df_m1["time"])

print(f"  M5: {len(df_m5):,} velas | M1: {len(df_m1):,} velas")

# Configuraciones a probar
rr_values = [1.5, 2.0, 2.5, 3.0, 3.5]
buffer_values = [10, 15, 20, 25, 30]

results = []

print("\n" + "="*80)
print("  EJECUTANDO BACKTESTS...")
print("="*80)

total_tests = len(rr_values) * len(buffer_values)
current_test = 0

for rr in rr_values:
    for buffer in buffer_values:
        current_test += 1
        print(f"\n[{current_test}/{total_tests}] Testing R:R={rr} | Buffer={buffer} puntos...", end=" ")
        
        # Configurar parámetros
        params = DEFAULT_PARAMS.copy()
        params["target_rr"] = rr
        params["buffer_points"] = buffer
        params["require_bos"] = False  # Sin BOS
        
        try:
            # Ejecutar backtest
            bt = OrderBlockBacktesterLimitOrders(params)
            df_trades = bt.run(df_m5, df_m1)
            
            # Calcular métricas
            balance_inicial = params["initial_balance"]
            total_pnl = df_trades["pnl_usd"].sum()
            balance_final = balance_inicial + total_pnl
            retorno_pct = (balance_final - balance_inicial) / balance_inicial * 100
            
            winners = df_trades[df_trades["pnl_usd"] > 0]
            losers = df_trades[df_trades["pnl_usd"] <= 0]
            
            win_rate = len(winners) / len(df_trades) * 100 if len(df_trades) > 0 else 0
            
            profit_factor = abs(winners["pnl_usd"].sum() / losers["pnl_usd"].sum()) if len(losers) > 0 and losers["pnl_usd"].sum() != 0 else 0
            
            # Calcular Max DD
            equity = [balance_inicial]
            balance = balance_inicial
            peak = balance_inicial
            max_dd = 0
            
            for idx, row in df_trades.sort_values("exit_time").iterrows():
                balance += row["pnl_usd"]
                equity.append(balance)
                
                if balance > peak:
                    peak = balance
                
                dd = peak - balance
                dd_pct = (dd / peak) * 100 if peak > 0 else 0
                
                if dd_pct > max_dd:
                    max_dd = dd_pct
            
            results.append({
                "rr": rr,
                "buffer": buffer,
                "trades": len(df_trades),
                "win_rate": win_rate,
                "retorno_pct": retorno_pct,
                "pnl_usd": total_pnl,
                "profit_factor": profit_factor,
                "max_dd": max_dd,
                "avg_win": winners["pnl_usd"].mean() if len(winners) > 0 else 0,
                "avg_loss": losers["pnl_usd"].mean() if len(losers) > 0 else 0,
            })
            
            print(f"✓ {len(df_trades)} trades | {retorno_pct:+.1f}% | WR {win_rate:.1f}%")
            
        except Exception as e:
            print(f"✗ Error: {e}")
            results.append({
                "rr": rr,
                "buffer": buffer,
                "trades": 0,
                "win_rate": 0,
                "retorno_pct": 0,
                "pnl_usd": 0,
                "profit_factor": 0,
                "max_dd": 0,
                "avg_win": 0,
                "avg_loss": 0,
            })

# Crear DataFrame de resultados
df_results = pd.DataFrame(results)

# Guardar resultados
df_results.to_csv("optimizacion_rr_buffer.csv", index=False)
print(f"\n✅ Resultados guardados en: optimizacion_rr_buffer.csv")

print("\n" + "="*80)
print("  RESULTADOS - ORDENADOS POR RETORNO")
print("="*80)

df_sorted = df_results.sort_values("retorno_pct", ascending=False)

print(f"\n{'R:R':<6} {'Buffer':<8} {'Trades':<8} {'WR %':<8} {'Retorno %':<12} {'PF':<6} {'Max DD %':<10}")
print("-" * 70)
for idx, row in df_sorted.head(15).iterrows():
    print(f"{row['rr']:<6.1f} {row['buffer']:<8.0f} {row['trades']:<8.0f} "
          f"{row['win_rate']:<8.1f} {row['retorno_pct']:<12.2f} "
          f"{row['profit_factor']:<6.2f} {row['max_dd']:<10.2f}")

print("\n" + "="*80)
print("  RESULTADOS - ORDENADOS POR PROFIT FACTOR")
print("="*80)

df_sorted_pf = df_results.sort_values("profit_factor", ascending=False)

print(f"\n{'R:R':<6} {'Buffer':<8} {'Trades':<8} {'WR %':<8} {'Retorno %':<12} {'PF':<6} {'Max DD %':<10}")
print("-" * 70)
for idx, row in df_sorted_pf.head(15).iterrows():
    print(f"{row['rr']:<6.1f} {row['buffer']:<8.0f} {row['trades']:<8.0f} "
          f"{row['win_rate']:<8.1f} {row['retorno_pct']:<12.2f} "
          f"{row['profit_factor']:<6.2f} {row['max_dd']:<10.2f}")

print("\n" + "="*80)
print("  RESULTADOS - ORDENADOS POR MAX DD (menor mejor)")
print("="*80)

df_sorted_dd = df_results.sort_values("max_dd", ascending=True)

print(f"\n{'R:R':<6} {'Buffer':<8} {'Trades':<8} {'WR %':<8} {'Retorno %':<12} {'PF':<6} {'Max DD %':<10}")
print("-" * 70)
for idx, row in df_sorted_dd.head(15).iterrows():
    print(f"{row['rr']:<6.1f} {row['buffer']:<8.0f} {row['trades']:<8.0f} "
          f"{row['win_rate']:<8.1f} {row['retorno_pct']:<12.2f} "
          f"{row['profit_factor']:<6.2f} {row['max_dd']:<10.2f}")

# Encontrar mejor configuración balanceada
print("\n" + "="*80)
print("  ANÁLISIS: MEJOR CONFIGURACIÓN BALANCEADA")
print("="*80)

# Filtrar configuraciones con retorno > 15% y Max DD < 10%
df_filtered = df_results[(df_results["retorno_pct"] > 15) & (df_results["max_dd"] < 10)]

if len(df_filtered) > 0:
    # Ordenar por score combinado
    df_filtered["score"] = (
        df_filtered["retorno_pct"] * 0.4 +  # 40% peso en retorno
        df_filtered["profit_factor"] * 10 * 0.3 +  # 30% peso en PF
        (100 - df_filtered["max_dd"]) * 0.3  # 30% peso en bajo DD
    )
    
    best = df_filtered.sort_values("score", ascending=False).iloc[0]
    
    print(f"\n🏆 MEJOR CONFIGURACIÓN:")
    print(f"  R:R:            {best['rr']:.1f}")
    print(f"  Buffer SL:      {best['buffer']:.0f} puntos")
    print(f"  Trades:         {best['trades']:.0f}")
    print(f"  Win Rate:       {best['win_rate']:.1f}%")
    print(f"  Retorno:        {best['retorno_pct']:+.2f}%")
    print(f"  Profit Factor:  {best['profit_factor']:.2f}")
    print(f"  Max DD:         {best['max_dd']:.2f}%")
    print(f"  Avg Win:        ${best['avg_win']:,.2f}")
    print(f"  Avg Loss:       ${best['avg_loss']:,.2f}")
else:
    print("\n⚠️  No se encontraron configuraciones con Retorno >15% y Max DD <10%")
    
    # Mostrar la mejor por retorno
    best = df_results.sort_values("retorno_pct", ascending=False).iloc[0]
    print(f"\n🏆 MEJOR POR RETORNO:")
    print(f"  R:R:            {best['rr']:.1f}")
    print(f"  Buffer SL:      {best['buffer']:.0f} puntos")
    print(f"  Trades:         {best['trades']:.0f}")
    print(f"  Win Rate:       {best['win_rate']:.1f}%")
    print(f"  Retorno:        {best['retorno_pct']:+.2f}%")
    print(f"  Profit Factor:  {best['profit_factor']:.2f}")
    print(f"  Max DD:         {best['max_dd']:.2f}%")

print("\n" + "="*80)
print("  ANÁLISIS POR R:R")
print("="*80)

for rr in rr_values:
    df_rr = df_results[df_results["rr"] == rr]
    best_buffer = df_rr.sort_values("retorno_pct", ascending=False).iloc[0]
    
    print(f"\nR:R = {rr}:")
    print(f"  Mejor buffer:   {best_buffer['buffer']:.0f} puntos")
    print(f"  Retorno:        {best_buffer['retorno_pct']:+.2f}%")
    print(f"  Win Rate:       {best_buffer['win_rate']:.1f}%")
    print(f"  Max DD:         {best_buffer['max_dd']:.2f}%")

print("\n" + "="*80)
print("  ANÁLISIS POR BUFFER")
print("="*80)

for buffer in buffer_values:
    df_buf = df_results[df_results["buffer"] == buffer]
    best_rr = df_buf.sort_values("retorno_pct", ascending=False).iloc[0]
    
    print(f"\nBuffer = {buffer} puntos:")
    print(f"  Mejor R:R:      {best_rr['rr']:.1f}")
    print(f"  Retorno:        {best_rr['retorno_pct']:+.2f}%")
    print(f"  Win Rate:       {best_rr['win_rate']:.1f}%")
    print(f"  Max DD:         {best_rr['max_dd']:.2f}%")

print("\n" + "="*80)
