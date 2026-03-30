# -*- coding: utf-8 -*-
"""
EXPERIMENTAL - Solo para investigacion. NO modifica ni altera el bot live.

Compara dos ventanas horarias para evaluar si extender hasta el cierre oficial de NY mejora resultados:

  A) NY actual (baseline):  13:30 - 19:30 UTC  (6 horas, config actual del bot)
  B) NY extendida:          13:30 - 21:00 UTC  (7.5 horas, hasta cierre oficial)

Objetivo: Determinar si las ultimas 1.5 horas (19:30-21:00) aportan valor o degradan metricas.
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


def run(df_m5, df_m1, sessions: dict, label: str):
    params = copy.deepcopy(DEFAULT_PARAMS)
    params["sessions"] = sessions

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
    
    return {
        "label": label,
        "trades": len(df_t),
        "trades_per_day": len(df_t)/days,
        "win_rate": wr,
        "return_pct": ret,
        "max_dd": mdd,
        "max_daily_dd": max_daily_dd_pct,
        "profit_factor": pf,
        "avg_r": avg_r,
        "balance": balance,
    }


if __name__ == "__main__":
    print("\n" + "="*70)
    print("  BACKTEST EXPERIMENTAL — EXTENSION DE SESION NY")
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

    # A) Configuracion actual del bot (baseline)
    result_a = run(df_m5, df_m1,
        {"new_york": {"start": "13:30", "end": "19:30", "skip_minutes": 15}},
        "A) NY ACTUAL (13:30-19:30 UTC) — CONFIG DEL BOT LIVE")

    # B) Extension hasta cierre oficial de NY
    result_b = run(df_m5, df_m1,
        {"new_york_extended": {"start": "13:30", "end": "21:00", "skip_minutes": 15}},
        "B) NY EXTENDIDA (13:30-21:00 UTC) — HASTA CIERRE OFICIAL")

    # Comparacion
    if result_a and result_b:
        print("\n" + "="*70)
        print("  COMPARACION DIRECTA")
        print("="*70)
        
        diff_trades = result_b["trades"] - result_a["trades"]
        diff_wr = result_b["win_rate"] - result_a["win_rate"]
        diff_ret = result_b["return_pct"] - result_a["return_pct"]
        diff_dd = result_b["max_dd"] - result_a["max_dd"]
        diff_daily_dd = result_b["max_daily_dd"] - result_a["max_daily_dd"]
        diff_pf = result_b["profit_factor"] - result_a["profit_factor"]
        
        print(f"  Trades adicionales:  {diff_trades:>+6}  ({diff_trades/result_a['trades']*100:+.1f}%)")
        print(f"  Delta Win Rate:      {diff_wr:>+6.1f}pp")
        print(f"  Delta Retorno:       {diff_ret:>+7.2f}pp")
        print(f"  Delta Max DD:        {diff_dd:>+6.2f}pp  {'[PEOR]' if diff_dd > 0 else '[MEJOR]'}")
        print(f"  Delta Daily DD:      {diff_daily_dd:>+6.2f}pp  {'[PEOR]' if diff_daily_dd > 0 else '[MEJOR]'}")
        print(f"  Delta Profit Factor: {diff_pf:>+6.2f}")
        
        print("\n" + "="*70)
        print("  CONCLUSION")
        print("="*70)
        
        # Criterios de decision
        better_metrics = 0
        if diff_ret > 0: better_metrics += 1
        if diff_wr > 0: better_metrics += 1
        if diff_dd <= 0: better_metrics += 1
        if diff_daily_dd <= 0: better_metrics += 1
        if diff_pf > 0: better_metrics += 1
        
        if better_metrics >= 3:
            print("  [+] RECOMENDACION: Extender hasta 21:00 UTC mejora los resultados")
            print(f"      {better_metrics}/5 metricas clave mejoran")
        else:
            print("  [!] RECOMENDACION: Mantener config actual (13:30-19:30 UTC)")
            print(f"      Solo {better_metrics}/5 metricas mejoran con la extension")
            print("      Las ultimas 1.5 horas (19:30-21:00) probablemente anaden ruido")
        
        print("="*70 + "\n")
