# -*- coding: utf-8 -*-
"""
Grid comparison: buffer (25, 35) x RR (2.0, 2.5, 3.0)
Con fix look-ahead aplicado y riesgo fijo $50 sobre $10k.

Corre 6 backtests y genera tabla comparativa.
"""
import sys
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

import copy
import gc
from pathlib import Path
from datetime import timedelta

sys.path.insert(0, str(Path(__file__).parent))

from strategies.fair_value_gap.backtest.config import US30_PARAMS
from strategies.fair_value_gap.backtest.data_loader import load_csv, validate_alignment
from strategies.fair_value_gap.backtest.backtester import FVGBacktester

ACCOUNT = 10_000.0
RISK_USD = 50.0

BUFFERS = [25, 35]
RRS = [2.0, 2.5, 3.0]


def run_one(df_higher, df_lower, buffer, rr):
    params = copy.deepcopy(US30_PARAMS)
    params["initial_balance"] = ACCOUNT
    params["buffer_points"] = buffer
    params["target_rr"] = rr

    bt = FVGBacktester(params)
    df_res = bt.run(df_higher, df_lower)

    if df_res.empty:
        return None

    # Excluir trades con look-ahead
    import pandas as pd
    df_res["fvg_confirmed_at"] = pd.to_datetime(df_res["fvg_confirmed_at"])
    df_res["entry_time"] = pd.to_datetime(df_res["entry_time"])
    df_res["exit_time"] = pd.to_datetime(df_res["exit_time"])
    fvg_close = df_res["fvg_confirmed_at"] + timedelta(minutes=5)
    clean = df_res[df_res["entry_time"] >= fvg_close].copy()

    # Riesgo fijo $50
    clean["pnl_real"] = clean["pnl_r"] * RISK_USD

    total = len(clean)
    if total == 0:
        return None

    wins = (clean["pnl_real"] > 0).sum()
    losses = total - wins
    wr = wins / total * 100
    pnl = clean["pnl_real"].sum()

    gp = clean.loc[clean["pnl_real"] > 0, "pnl_real"].sum()
    gl = abs(clean.loc[clean["pnl_real"] <= 0, "pnl_real"].sum())
    pf = gp / gl if gl > 0 else float("inf")

    avg_win = clean.loc[clean["pnl_real"] > 0, "pnl_real"].mean() if wins > 0 else 0
    avg_loss = clean.loc[clean["pnl_real"] <= 0, "pnl_real"].mean() if losses > 0 else 0

    # Drawdown
    cum = clean["pnl_real"].cumsum()
    peak = cum.cummax()
    dd = (peak - cum).max()

    # Daily
    clean["date"] = clean["exit_time"].dt.date
    daily = clean.groupby("date")["pnl_real"].sum()
    worst_day = daily.min()
    worst_day_pct = abs(worst_day) / ACCOUNT * 100

    ftmo_limit = ACCOUNT * 4.0 / 100.0
    days_over = (daily < -ftmo_limit).sum()

    # Rachas
    is_l = (clean["pnl_real"] <= 0).astype(int)
    streaks = is_l * (is_l.groupby((is_l != is_l.shift()).cumsum()).cumcount() + 1)
    max_streak = int(streaks.max()) if len(streaks) > 0 else 0

    # Monthly
    clean["month"] = clean["exit_time"].dt.to_period("M")
    monthly_pnl = clean.groupby("month")["pnl_real"].sum()
    neg_months = (monthly_pnl < 0).sum()
    total_months = len(monthly_pnl)

    # Avg trades/day
    avg_tpd = clean.groupby("date").size().mean()

    del bt, df_res, clean
    gc.collect()

    return {
        "buffer": buffer,
        "rr": rr,
        "trades": total,
        "wr": wr,
        "pf": pf,
        "pnl": pnl,
        "retorno": pnl / ACCOUNT * 100,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "dd_usd": dd,
        "dd_pct": dd / ACCOUNT * 100,
        "worst_day": worst_day,
        "worst_day_pct": worst_day_pct,
        "days_over_ftmo": days_over,
        "max_losing_streak": max_streak,
        "neg_months": neg_months,
        "total_months": total_months,
        "avg_trades_day": avg_tpd,
    }


def main():
    print(f"\nCargando datos...", flush=True)
    df_higher = load_csv("data/US30_icm_M5_518d.csv")
    df_lower  = load_csv("data/US30_icm_M1_500k.csv")
    validate_alignment(df_higher, df_lower)
    print(f"  M5: {len(df_higher)} velas | M1: {len(df_lower)} velas", flush=True)

    results = []
    total_combos = len(BUFFERS) * len(RRS)
    i = 0
    for buf in BUFFERS:
        for rr in RRS:
            i += 1
            print(f"\n[{i}/{total_combos}] Buffer={buf} RR={rr} ...", flush=True)
            r = run_one(df_higher, df_lower, buf, rr)
            if r:
                results.append(r)
                print(f"  -> {r['trades']} trades | WR {r['wr']:.1f}% | PF {r['pf']:.2f} | PnL ${r['pnl']:+,.0f} | DD {r['dd_pct']:.1f}%", flush=True)
            else:
                print(f"  -> SIN RESULTADOS", flush=True)

    # Tabla comparativa
    print(f"\n\n{'='*100}", flush=True)
    print(f"  COMPARACION GRID: Buffer x RR — Cuenta $10k, Riesgo $50 fijo — 518 dias — Fix look-ahead", flush=True)
    print(f"{'='*100}", flush=True)
    print(f"  {'Buf':>3s} {'RR':>4s} | {'Trades':>6s} {'WR':>6s} {'PF':>5s} | {'PnL':>10s} {'Ret%':>7s} | {'AvgWin':>7s} {'AvgLoss':>8s} | {'MaxDD':>8s} {'DD%':>5s} | {'WorstDay':>9s} {'WD%':>5s} {'FTMO':>4s} | {'Streak':>6s} {'NegMo':>5s} {'T/d':>4s}", flush=True)
    print(f"  {'-'*96}", flush=True)
    for r in results:
        print(
            f"  {r['buffer']:>3d} {r['rr']:>4.1f} | "
            f"{r['trades']:>6d} {r['wr']:>5.1f}% {r['pf']:>5.2f} | "
            f"${r['pnl']:>+9,.0f} {r['retorno']:>+6.1f}% | "
            f"${r['avg_win']:>6.0f} ${r['avg_loss']:>7.0f} | "
            f"${r['dd_usd']:>7,.0f} {r['dd_pct']:>4.1f}% | "
            f"${r['worst_day']:>8,.0f} {r['worst_day_pct']:>4.1f}% {r['days_over_ftmo']:>4d} | "
            f"{r['max_losing_streak']:>6d} {r['neg_months']:>3d}/{r['total_months']:<2d} {r['avg_trades_day']:>3.1f}",
            flush=True,
        )
    print(f"{'='*100}\n", flush=True)

    # Mejor combo
    best = max(results, key=lambda x: x["pnl"])
    print(f"  MEJOR PnL:     Buffer={best['buffer']} RR={best['rr']} -> ${best['pnl']:+,.0f} ({best['retorno']:+.1f}%)", flush=True)
    best_pf = max(results, key=lambda x: x["pf"])
    print(f"  MEJOR PF:      Buffer={best_pf['buffer']} RR={best_pf['rr']} -> PF {best_pf['pf']:.2f}", flush=True)
    best_dd = min(results, key=lambda x: x["dd_pct"])
    print(f"  MENOR DD:      Buffer={best_dd['buffer']} RR={best_dd['rr']} -> DD {best_dd['dd_pct']:.1f}%", flush=True)
    best_wd = min(results, key=lambda x: abs(x["worst_day"]))
    print(f"  MENOR WORST DAY: Buffer={best_wd['buffer']} RR={best_wd['rr']} -> ${best_wd['worst_day']:+,.0f}", flush=True)
    print(flush=True)


if __name__ == "__main__":
    main()
