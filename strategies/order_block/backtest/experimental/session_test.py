# -*- coding: utf-8 -*-
"""
EXPERIMENTAL - Solo para investigacion. NO modifica ni altera el bot live.

Compara tres ventanas horarias para la estrategia OB:

  A) NY completa (baseline): 13:30 - 19:30 UTC
  B) London/NY overlap:      13:30 - 16:00 UTC  (maximo volumen institucional)
  C) NY puro:                16:00 - 19:30 UTC  (solo NY, sin Londres)
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
        return

    balance = df_t["balance"].iloc[-1]
    ret  = (balance - params["initial_balance"]) / params["initial_balance"] * 100
    wr   = (df_t["pnl_usd"] > 0).mean() * 100
    mdd  = 0.0
    peak = float(params["initial_balance"])
    for b in df_t["balance"]:
        if b > peak:
            peak = b
        dd = (peak - b) / peak * 100
        if dd > mdd:
            mdd = dd

    longs  = df_t[df_t["direction"] == "long"]
    shorts = df_t[df_t["direction"] == "short"]
    days   = max((df_t["entry_time"].iloc[-1] - df_t["entry_time"].iloc[0]).days, 1)

    print(f"  {label}")
    print(f"    Trades:    {len(df_t)}  ({days} dias,  {len(df_t)/days:.2f}/dia)")
    print(f"    Win Rate:  {wr:.1f}%")
    print(f"    Retorno:   {ret:+.2f}%")
    print(f"    Max DD:    {mdd:.2f}%")
    if len(longs):
        print(f"    Long:  {len(longs)} trades  WR {(longs['pnl_usd']>0).mean()*100:.0f}%")
    if len(shorts):
        print(f"    Short: {len(shorts)} trades  WR {(shorts['pnl_usd']>0).mean()*100:.0f}%")
    print()


if __name__ == "__main__":
    print("Cargando datos...")
    df_m5 = load_csv(M5_FILE)
    df_m1 = load_csv(M1_FILE)
    start = max(df_m5["time"].iloc[0], df_m1["time"].iloc[0])
    end   = min(df_m5["time"].iloc[-1], df_m1["time"].iloc[-1])
    df_m5 = df_m5[(df_m5["time"] >= start) & (df_m5["time"] <= end)].reset_index(drop=True)
    df_m1 = df_m1[(df_m1["time"] >= start) & (df_m1["time"] <= end)].reset_index(drop=True)
    print(f"  Periodo: {start} -> {end}")
    print(f"  M5: {len(df_m5)} velas | M1: {len(df_m1)} velas")
    print()

    print("=" * 58)
    print("  BACKTEST EXPERIMENTAL — SESIONES HORARIAS")
    print("  (NO modifica el bot live)")
    print("=" * 58)
    print()

    run(df_m5, df_m1,
        {"new_york": {"start": "13:30", "end": "19:30", "skip_minutes": 15}},
        "A) NY completa  13:30-19:30 UTC (baseline)")

    run(df_m5, df_m1,
        {"overlap": {"start": "13:30", "end": "16:00", "skip_minutes": 15}},
        "B) London/NY overlap  13:30-16:00 UTC")

    run(df_m5, df_m1,
        {"ny_pure": {"start": "16:00", "end": "19:30", "skip_minutes": 0}},
        "C) NY puro  16:00-19:30 UTC")

    print("=" * 58)
    print("  A = baseline live")
    print("  B = overlap = maximo volumen institucional")
    print("  C = NY solo = sin ruido de Londres")
    print("=" * 58)
