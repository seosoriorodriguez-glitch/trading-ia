# -*- coding: utf-8 -*-
"""
BACKTEST NY + EXPORTAR OPERACIONES GANADORAS
Ejecuta backtest de NY y exporta tabla completa de winners
"""
import sys
import codecs
if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

import copy
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from strategies.order_block.backtest.config import DEFAULT_PARAMS
from strategies.order_block.backtest.data_loader import load_csv
from strategies.order_block.backtest.backtester import OrderBlockBacktester

_ROOT   = Path(__file__).parent.parent.parent.parent.parent
M5_FILE = str(_ROOT / "data/US30_cash_M5_260d.csv")
M1_FILE = str(_ROOT / "data/US30_cash_M1_260d.csv")
OUTPUT_DIR = _ROOT / "strategies/order_block/backtest/results"


if __name__ == "__main__":
    print("\n" + "="*80)
    print("  BACKTEST NY + EXPORTAR OPERACIONES GANADORAS")
    print("="*80)
    
    print("\nCargando datos...")
    df_m5 = load_csv(M5_FILE)
    df_m1 = load_csv(M1_FILE)
    start = max(df_m5["time"].iloc[0], df_m1["time"].iloc[0])
    end   = min(df_m5["time"].iloc[-1], df_m1["time"].iloc[-1])
    df_m5 = df_m5[(df_m5["time"] >= start) & (df_m5["time"] <= end)].reset_index(drop=True)
    df_m1 = df_m1[(df_m1["time"] >= start) & (df_m1["time"] <= end)].reset_index(drop=True)
    print(f"  Período: {start} -> {end}")
    print(f"  M5: {len(df_m5):,} velas | M1: {len(df_m1):,} velas")
    
    # Configuración actual (solo NY)
    params = copy.deepcopy(DEFAULT_PARAMS)
    params["sessions"] = {"new_york": {"start": "13:30", "end": "20:00", "skip_minutes": 15}}
    
    print("\n" + "="*80)
    print("  EJECUTANDO BACKTEST...")
    print("="*80)
    
    bt = OrderBlockBacktester(params)
    df_trades = bt.run(df_m5, df_m1)
    
    if df_trades.empty:
        print("\n❌ No se generaron trades")
        sys.exit(1)
    
    # Crear directorio de resultados
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Guardar todos los trades
    all_trades_file = OUTPUT_DIR / "ny_all_trades.csv"
    df_trades.to_csv(all_trades_file, index=False)
    print(f"\n✅ Todos los trades guardados en: {all_trades_file}")
    
    # Filtrar solo winners
    df_winners = df_trades[df_trades["pnl_usd"] > 0].copy()
    
    # ✅ SL y TP ya vienen correctos del backtester, NO recalcular
    
    # Calcular risk en puntos
    df_winners["risk_pts"] = df_winners.apply(
        lambda row: abs(row["entry_price"] - row["sl"]),
        axis=1
    )
    
    # Calcular reward en puntos
    df_winners["reward_pts"] = df_winners.apply(
        lambda row: abs(row["exit_price"] - row["entry_price"]),
        axis=1
    )
    
    # Calcular R:R real
    df_winners["rr_ratio"] = df_winners["reward_pts"] / df_winners["risk_pts"]
    
    # Guardar winners
    winners_file = OUTPUT_DIR / "ny_winners_only.csv"
    df_winners.to_csv(winners_file, index=False)
    print(f"✅ Operaciones ganadoras guardadas en: {winners_file}")
    
    # Métricas generales
    balance_inicial = params["initial_balance"]
    balance_final = df_trades["balance"].iloc[-1]
    retorno = (balance_final - balance_inicial) / balance_inicial * 100
    
    losers = df_trades[df_trades["pnl_usd"] <= 0]
    wr = len(df_winners) / len(df_trades) * 100
    
    print("\n" + "="*80)
    print("  RESUMEN DEL BACKTEST")
    print("="*80)
    
    print(f"\n💰 RENTABILIDAD:")
    print(f"  Balance inicial:  ${balance_inicial:,.2f}")
    print(f"  Balance final:    ${balance_final:,.2f}")
    print(f"  Retorno:          {retorno:+.2f}%")
    
    print(f"\n📊 TRADES:")
    print(f"  Total:            {len(df_trades)}")
    print(f"  Winners:          {len(df_winners)} ({wr:.1f}%)")
    print(f"  Losers:           {len(losers)} ({100-wr:.1f}%)")
    
    print("\n" + "="*80)
    print(f"  TABLA DE {len(df_winners)} OPERACIONES GANADORAS")
    print("="*80)
    
    # Mostrar tabla completa de winners
    print(f"\n{'#':<4} {'Fecha':<20} {'Dir':<6} {'Entry':<10} {'SL':<10} {'TP':<10} {'Exit':<10} {'PnL':<12} {'R':<8}")
    print("-" * 95)
    
    for idx, (_, trade) in enumerate(df_winners.iterrows(), 1):
        direction = trade["direction"].upper()[:5]
        r_mult = trade["pnl_r"] if "pnl_r" in trade else trade["rr_ratio"]
        print(f"{idx:<4} {str(trade['entry_time']):<20} {direction:<6} "
              f"{trade['entry_price']:<10.2f} {trade['sl']:<10.2f} {trade['tp']:<10.2f} "
              f"{trade['exit_price']:<10.2f} ${trade['pnl_usd']:>10,.2f} {r_mult:>6.2f}R")
    
    # Estadísticas de winners
    print("\n" + "="*80)
    print("  ESTADÍSTICAS DE OPERACIONES GANADORAS")
    print("="*80)
    
    longs = df_winners[df_winners["direction"] == "long"]
    shorts = df_winners[df_winners["direction"] == "short"]
    
    print(f"\n📈 POR DIRECCIÓN:")
    if len(longs) > 0:
        print(f"  LONG:  {len(longs)} trades ({len(longs)/len(df_winners)*100:.1f}%)")
        print(f"         PnL total: ${longs['pnl_usd'].sum():,.2f}")
        print(f"         PnL promedio: ${longs['pnl_usd'].mean():,.2f}")
    
    if len(shorts) > 0:
        print(f"  SHORT: {len(shorts)} trades ({len(shorts)/len(df_winners)*100:.1f}%)")
        print(f"         PnL total: ${shorts['pnl_usd'].sum():,.2f}")
        print(f"         PnL promedio: ${shorts['pnl_usd'].mean():,.2f}")
    
    print(f"\n💵 MÉTRICAS:")
    print(f"  PnL total:        ${df_winners['pnl_usd'].sum():,.2f}")
    print(f"  PnL promedio:     ${df_winners['pnl_usd'].mean():,.2f}")
    print(f"  PnL mínimo:       ${df_winners['pnl_usd'].min():,.2f}")
    print(f"  PnL máximo:       ${df_winners['pnl_usd'].max():,.2f}")
    
    if "pnl_r" in df_winners.columns or "rr_ratio" in df_winners.columns:
        r_col = "pnl_r" if "pnl_r" in df_winners.columns else "rr_ratio"
        print(f"\n📊 R-MULTIPLES:")
        print(f"  R promedio:       {df_winners[r_col].mean():.2f}R")
        print(f"  R mínimo:         {df_winners[r_col].min():.2f}R")
        print(f"  R máximo:         {df_winners[r_col].max():.2f}R")
    
    # Distribución mensual
    print(f"\n📅 DISTRIBUCIÓN MENSUAL:")
    df_winners["month"] = pd.to_datetime(df_winners["entry_time"]).dt.to_period("M")
    monthly = df_winners.groupby("month").agg({
        "pnl_usd": ["count", "sum", "mean"]
    })
    
    print(f"\n{'Mes':<12} {'Trades':<10} {'PnL Total':<15} {'PnL Promedio':<15}")
    print("-" * 55)
    for month, row in monthly.iterrows():
        count = int(row[("pnl_usd", "count")])
        total = row[("pnl_usd", "sum")]
        avg = row[("pnl_usd", "mean")]
        print(f"{str(month):<12} {count:<10} ${total:>12,.2f} ${avg:>12,.2f}")
    
    print("\n" + "="*80)
    print("  ARCHIVOS GENERADOS")
    print("="*80)
    print(f"\n  1. {all_trades_file}")
    print(f"     → Todos los {len(df_trades)} trades (winners + losers)")
    print(f"\n  2. {winners_file}")
    print(f"     → Solo las {len(df_winners)} operaciones ganadoras")
    print("\n" + "="*80)
