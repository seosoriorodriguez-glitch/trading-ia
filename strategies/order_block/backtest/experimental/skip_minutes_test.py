# -*- coding: utf-8 -*-
"""
EXPERIMENTAL - Solo para investigacion. NO modifica ni altera el bot live.

Compara el impacto de skip_minutes en la apertura de la sesión NY:

  A) Sin skip (0 min):  Opera desde 13:30 UTC (apertura inmediata)
  B) Skip 15 min:       Opera desde 13:45 UTC (evita primeros 15 min)
  C) Skip 30 min:       Opera desde 14:00 UTC (evita primeros 30 min)

Objetivo: Determinar si los primeros minutos post-apertura añaden valor o degradan métricas.
"""
import sys
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


def run(df_m5, df_m1, skip_minutes: int, label: str):
    params = copy.deepcopy(DEFAULT_PARAMS)
    params["sessions"] = {
        "new_york": {"start": "13:30", "end": "20:00", "skip_minutes": skip_minutes}
    }

    bt = OrderBlockBacktester(params)
    result = bt.run(df_m5, df_m1)

    df_t = result if isinstance(result, pd.DataFrame) else pd.DataFrame(result)
    if df_t is None or len(df_t) == 0:
        print(f"  {label}: 0 trades\n")
        return None

    balance = df_t["balance"].iloc[-1]
    ret  = (balance - params["initial_balance"]) / params["initial_balance"] * 100
    wr   = (df_t["pnl_usd"] > 0).mean() * 100
    
    # Max Drawdown
    mdd  = 0.0
    peak = float(params["initial_balance"])
    for b in df_t["balance"]:
        if b > peak:
            peak = b
        dd = (peak - b) / peak * 100
        if dd > mdd:
            mdd = dd
    
    # Daily Drawdown (max perdida en un solo dia)
    df_t["date"] = pd.to_datetime(df_t["entry_time"]).dt.date
    daily_pnl = df_t.groupby("date")["pnl_usd"].sum()
    max_daily_loss = daily_pnl.min()
    max_daily_dd_pct = (max_daily_loss / params["initial_balance"]) * 100 if max_daily_loss < 0 else 0.0

    longs  = df_t[df_t["direction"] == "long"]
    shorts = df_t[df_t["direction"] == "short"]
    days   = max((df_t["entry_time"].iloc[-1] - df_t["entry_time"].iloc[0]).days, 1)
    
    # Profit Factor
    wins = df_t[df_t["pnl_usd"] > 0]["pnl_usd"].sum()
    losses = abs(df_t[df_t["pnl_usd"] < 0]["pnl_usd"].sum())
    pf = wins / losses if losses > 0 else float('inf')
    
    # R-multiples
    avg_r = df_t["pnl_r"].mean()
    
    # Analizar trades en la ventana de skip
    df_t["entry_hour"] = pd.to_datetime(df_t["entry_time"]).dt.hour
    df_t["entry_minute"] = pd.to_datetime(df_t["entry_time"]).dt.minute
    df_t["minutes_from_1330"] = (df_t["entry_hour"] - 13) * 60 + (df_t["entry_minute"] - 30)
    
    # Trades en los primeros 15 minutos (13:30-13:45)
    early_trades = df_t[df_t["minutes_from_1330"] < 15]
    if len(early_trades) > 0:
        early_wr = (early_trades["pnl_usd"] > 0).mean() * 100
        early_pnl = early_trades["pnl_usd"].sum()
        early_avg_r = early_trades["pnl_r"].mean()
    else:
        early_wr = 0
        early_pnl = 0
        early_avg_r = 0

    print(f"\n{'='*70}")
    print(f"  {label}")
    print(f"{'='*70}")
    print(f"  Trades totales:      {len(df_t):>6}  ({days} dias,  {len(df_t)/days:.2f} trades/dia)")
    print(f"  Win Rate:            {wr:>6.1f}%")
    print(f"  Retorno neto:        {ret:>+7.2f}%")
    print(f"  Max Drawdown:        {mdd:>6.2f}%")
    print(f"  Max Daily DD:        {max_daily_dd_pct:>6.2f}%")
    print(f"  Profit Factor:       {pf:>6.2f}")
    print(f"  Avg R-multiple:      {avg_r:>+6.2f}R")
    print(f"  Balance final:       ${balance:>,.2f}")
    
    if len(longs):
        long_wr = (longs['pnl_usd']>0).mean()*100
        print(f"  Long:  {len(longs):>4} trades  |  WR {long_wr:>5.1f}%")
    if len(shorts):
        short_wr = (shorts['pnl_usd']>0).mean()*100
        print(f"  Short: {len(shorts):>4} trades  |  WR {short_wr:>5.1f}%")
    
    # Estadisticas de la ventana de skip
    if skip_minutes == 0 and len(early_trades) > 0:
        print(f"\n  TRADES EN PRIMEROS 15 MIN (13:30-13:45):")
        print(f"    Cantidad:     {len(early_trades)} trades")
        print(f"    Win Rate:     {early_wr:.1f}%")
        print(f"    PnL total:    ${early_pnl:+,.2f}")
        print(f"    Avg R:        {early_avg_r:+.2f}R")
        print(f"    % del total:  {len(early_trades)/len(df_t)*100:.1f}% de todos los trades")
    
    return {
        "label": label,
        "skip_minutes": skip_minutes,
        "trades": len(df_t),
        "trades_per_day": len(df_t)/days,
        "win_rate": wr,
        "return_pct": ret,
        "max_dd": mdd,
        "max_daily_dd": max_daily_dd_pct,
        "profit_factor": pf,
        "avg_r": avg_r,
        "balance": balance,
        "early_trades": len(early_trades) if skip_minutes == 0 else 0,
        "early_wr": early_wr if skip_minutes == 0 else 0,
        "early_pnl": early_pnl if skip_minutes == 0 else 0,
    }


if __name__ == "__main__":
    print("\n" + "="*70)
    print("  BACKTEST EXPERIMENTAL - IMPACTO DE SKIP_MINUTES")
    print("  (NO modifica el bot live)")
    print("="*70)
    
    print("\nCargando datos...")
    df_m5 = load_csv(M5_FILE)
    df_m1 = load_csv(M1_FILE)
    start = max(df_m5["time"].iloc[0], df_m1["time"].iloc[0])
    end   = min(df_m5["time"].iloc[-1], df_m1["time"].iloc[-1])
    df_m5 = df_m5[(df_m5["time"] >= start) & (df_m5["time"] <= end)].reset_index(drop=True)
    df_m1 = df_m1[(df_m1["time"] >= start) & (df_m1["time"] <= end)].reset_index(drop=True)
    print(f"  Periodo: {start} -> {end}")
    print(f"  M5: {len(df_m5):,} velas | M1: {len(df_m1):,} velas")

    # A) Sin skip - opera desde 13:30
    result_a = run(df_m5, df_m1, 0,
        "A) SIN SKIP (13:30-20:00 UTC) - Opera desde apertura")

    # B) Skip 15 min - opera desde 13:45
    result_b = run(df_m5, df_m1, 15,
        "B) SKIP 15 MIN (13:45-20:00 UTC) - Config actual")

    # C) Skip 30 min - opera desde 14:00
    result_c = run(df_m5, df_m1, 30,
        "C) SKIP 30 MIN (14:00-20:00 UTC) - Evita primeros 30 min")

    # Comparacion
    if result_a and result_b and result_c:
        print("\n" + "="*70)
        print("  COMPARACION DIRECTA")
        print("="*70)
        
        print(f"\n  {'Metrica':<25} {'Sin Skip':>12} {'Skip 15':>12} {'Skip 30':>12}")
        print(f"  {'-'*25} {'-'*12} {'-'*12} {'-'*12}")
        print(f"  {'Trades':<25} {result_a['trades']:>12} {result_b['trades']:>12} {result_c['trades']:>12}")
        print(f"  {'Win Rate':<25} {result_a['win_rate']:>11.1f}% {result_b['win_rate']:>11.1f}% {result_c['win_rate']:>11.1f}%")
        print(f"  {'Retorno':<25} {result_a['return_pct']:>+11.2f}% {result_b['return_pct']:>+11.2f}% {result_c['return_pct']:>+11.2f}%")
        print(f"  {'Max DD':<25} {result_a['max_dd']:>11.2f}% {result_b['max_dd']:>11.2f}% {result_c['max_dd']:>11.2f}%")
        print(f"  {'Max Daily DD':<25} {result_a['max_daily_dd']:>11.2f}% {result_b['max_daily_dd']:>11.2f}% {result_c['max_daily_dd']:>11.2f}%")
        print(f"  {'Profit Factor':<25} {result_a['profit_factor']:>12.2f} {result_b['profit_factor']:>12.2f} {result_c['profit_factor']:>12.2f}")
        print(f"  {'Avg R-multiple':<25} {result_a['avg_r']:>+11.2f}R {result_b['avg_r']:>+11.2f}R {result_c['avg_r']:>+11.2f}R")
        
        # Analisis de los primeros 15 minutos
        if result_a['early_trades'] > 0:
            print(f"\n  IMPACTO DE LOS PRIMEROS 15 MIN (13:30-13:45):")
            print(f"  {'-'*70}")
            print(f"    Trades en ventana:  {result_a['early_trades']} ({result_a['early_trades']/result_a['trades']*100:.1f}% del total)")
            print(f"    Win Rate ventana:   {result_a['early_wr']:.1f}%")
            print(f"    PnL ventana:        ${result_a['early_pnl']:+,.2f}")
            print(f"    Trades perdidos:    {result_a['trades'] - result_b['trades']} trades al usar skip 15")
        
        print("\n" + "="*70)
        print("  CONCLUSION")
        print("="*70)
        
        # Determinar cual es mejor
        scores = {
            'sin_skip': 0,
            'skip_15': 0,
            'skip_30': 0
        }
        
        # Retorno (peso 2)
        best_return = max(result_a['return_pct'], result_b['return_pct'], result_c['return_pct'])
        if result_a['return_pct'] == best_return: scores['sin_skip'] += 2
        if result_b['return_pct'] == best_return: scores['skip_15'] += 2
        if result_c['return_pct'] == best_return: scores['skip_30'] += 2
        
        # Win Rate
        best_wr = max(result_a['win_rate'], result_b['win_rate'], result_c['win_rate'])
        if result_a['win_rate'] == best_wr: scores['sin_skip'] += 1
        if result_b['win_rate'] == best_wr: scores['skip_15'] += 1
        if result_c['win_rate'] == best_wr: scores['skip_30'] += 1
        
        # Menor DD (mejor)
        best_dd = min(result_a['max_dd'], result_b['max_dd'], result_c['max_dd'])
        if result_a['max_dd'] == best_dd: scores['sin_skip'] += 1
        if result_b['max_dd'] == best_dd: scores['skip_15'] += 1
        if result_c['max_dd'] == best_dd: scores['skip_30'] += 1
        
        # Profit Factor
        best_pf = max(result_a['profit_factor'], result_b['profit_factor'], result_c['profit_factor'])
        if result_a['profit_factor'] == best_pf: scores['sin_skip'] += 1
        if result_b['profit_factor'] == best_pf: scores['skip_15'] += 1
        if result_c['profit_factor'] == best_pf: scores['skip_30'] += 1
        
        winner = max(scores, key=scores.get)
        winner_label = {
            'sin_skip': 'SIN SKIP (operar desde 13:30)',
            'skip_15': 'SKIP 15 MIN (operar desde 13:45)',
            'skip_30': 'SKIP 30 MIN (operar desde 14:00)'
        }
        
        print(f"\n  Puntuacion:")
        print(f"    Sin skip:   {scores['sin_skip']}/5 puntos")
        print(f"    Skip 15:    {scores['skip_15']}/5 puntos")
        print(f"    Skip 30:    {scores['skip_30']}/5 puntos")
        
        print(f"\n  [+] RECOMENDACION: {winner_label[winner]}")
        
        if winner == 'sin_skip':
            print(f"      Los primeros 15 minutos APORTAN valor positivo")
            print(f"      {result_a['early_trades']} trades adicionales con WR {result_a['early_wr']:.1f}%")
        elif winner == 'skip_15':
            print(f"      Los primeros 15 minutos degradan metricas o no aportan suficiente")
        else:
            print(f"      Los primeros 30 minutos tienen demasiado ruido")
        
        print("="*70 + "\n")
