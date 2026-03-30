# -*- coding: utf-8 -*-
"""
EXPERIMENTAL - Solo para investigacion. NO modifica ni altera el bot live.

OBs M15 + entradas M1, barrido de R:R: 2.5 (baseline) / 3 / 4 / 5
"""
import sys
import copy
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from strategies.order_block.backtest.config import DEFAULT_PARAMS
from strategies.order_block.backtest.data_loader import load_csv
from strategies.order_block.backtest.backtester import OrderBlockBacktester

_ROOT    = Path(__file__).parent.parent.parent.parent.parent
M15_FILE = str(_ROOT / "data/US30_cash_M15_260d.csv")
M1_FILE  = str(_ROOT / "data/US30_cash_M1_260d.csv")


def run(df_m15, df_m1, target_rr: float, label: str):
    params = copy.deepcopy(DEFAULT_PARAMS)
    params["target_rr"] = target_rr

    bt = OrderBlockBacktester(params)
    result = bt.run(df_m15, df_m1)

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

    tp_hits = (df_t["exit_reason"] == "tp").sum()
    sl_hits = (df_t["exit_reason"] == "sl").sum()
    longs   = df_t[df_t["direction"] == "long"]
    shorts  = df_t[df_t["direction"] == "short"]
    days    = max((df_t["entry_time"].iloc[-1] - df_t["entry_time"].iloc[0]).days, 1)

    print(f"  {label}")
    print(f"    Trades:    {len(df_t)}  ({days} dias,  {len(df_t)/days:.2f}/dia)")
    print(f"    Win Rate:  {wr:.1f}%")
    print(f"    Retorno:   {ret:+.2f}%")
    print(f"    Max DD:    {mdd:.2f}%")
    print(f"    TP hits:   {tp_hits}  |  SL hits: {sl_hits}")
    if len(longs):
        print(f"    Long:  {len(longs)} trades  WR {(longs['pnl_usd']>0).mean()*100:.0f}%")
    if len(shorts):
        print(f"    Short: {len(shorts)} trades  WR {(shorts['pnl_usd']>0).mean()*100:.0f}%")
    print()


if __name__ == "__main__":
    print("Cargando datos...")
    df_m15 = load_csv(M15_FILE)
    df_m1  = load_csv(M1_FILE)
    start  = max(df_m15["time"].iloc[0], df_m1["time"].iloc[0])
    end    = min(df_m15["time"].iloc[-1], df_m1["time"].iloc[-1])
    df_m15 = df_m15[(df_m15["time"] >= start) & (df_m15["time"] <= end)].reset_index(drop=True)
    df_m1  = df_m1[ (df_m1["time"]  >= start) & (df_m1["time"]  <= end)].reset_index(drop=True)
    print(f"  Periodo: {start} -> {end}")
    print(f"  M15: {len(df_m15)} velas | M1: {len(df_m1)} velas")
    print()

    print("=" * 58)
    print("  BACKTEST EXPERIMENTAL — M15 OBs + BARRIDO R:R")
    print("  (NO modifica el bot live)")
    print("=" * 58)
    print()

    run(df_m15, df_m1, 2.5, "RR 2.5 (baseline M15)")
    run(df_m15, df_m1, 3.0, "RR 3.0")
    run(df_m15, df_m1, 4.0, "RR 4.0")
    run(df_m15, df_m1, 5.0, "RR 5.0")

    print("=" * 58)
    print("  Mayor RR = menos TP hits pero cada win vale mas")
    print("  Buscar: mejor retorno con DD < 5% (limite FTMO)")
    print("=" * 58)
