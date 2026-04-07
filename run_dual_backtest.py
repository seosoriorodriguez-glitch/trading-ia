# -*- coding: utf-8 -*-
"""
Backtest dual: OB London + FVG con riesgo fijo $50 en cuenta $10k.

OB London:  Recalcula desde CSV existente (params = live)
FVG:        Recalcula desde CSV pre-generado (max_sim=1, look-ahead fix, 3 sesiones)

Riesgo fijo: pnl_real = pnl_r * RISK_USD (sin compounding)
"""
import sys
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

import argparse
import copy
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))

ACCOUNT  = 10_000.0
RISK_USD = 50.0
FTMO_DAILY_LOSS_PCT = 4.0


def analyze_fixed_risk(df: pd.DataFrame, label: str) -> dict:
    df = df.copy()
    df["pnl_real"] = df["pnl_r"] * RISK_USD

    total_trades = len(df)
    wins  = df[df["pnl_real"] > 0]
    losses = df[df["pnl_real"] <= 0]
    wr = len(wins) / total_trades * 100 if total_trades > 0 else 0

    gross_profit = wins["pnl_real"].sum() if len(wins) > 0 else 0
    gross_loss   = abs(losses["pnl_real"].sum()) if len(losses) > 0 else 0
    pf = gross_profit / gross_loss if gross_loss > 0 else float("inf")

    total_pnl = df["pnl_real"].sum()
    total_ret = total_pnl / ACCOUNT * 100

    equity = ACCOUNT + df["pnl_real"].cumsum()
    peak   = equity.cummax()
    dd     = (peak - equity) / peak * 100
    max_dd = dd.max()

    df["entry_time"] = pd.to_datetime(df["entry_time"])
    df["date"] = df["entry_time"].dt.date
    daily = df.groupby("date")["pnl_real"].sum()
    daily_loss_limit = ACCOUNT * FTMO_DAILY_LOSS_PCT / 100
    days_blocked = (daily < -daily_loss_limit).sum()
    worst_day = daily.min()
    worst_day_pct = worst_day / ACCOUNT * 100
    best_day = daily.max()
    best_day_pct = best_day / ACCOUNT * 100

    n_days = len(daily)
    avg_r = df["pnl_r"].mean()
    avg_win_r = wins["pnl_r"].mean() if len(wins) > 0 else 0
    avg_loss_r = losses["pnl_r"].mean() if len(losses) > 0 else 0

    period_start = df["entry_time"].iloc[0].date()
    period_end = df["entry_time"].iloc[-1].date()
    calendar_days = (period_end - period_start).days

    print(f"\n{'='*60}")
    print(f"  {label} -- Riesgo Fijo ${RISK_USD:.0f} / Cuenta ${ACCOUNT:,.0f}")
    print(f"{'='*60}")
    print(f"  Periodo:          {period_start} -> {period_end} ({calendar_days} dias)")
    print(f"  Trades:           {total_trades}")
    print(f"  Win Rate:         {wr:.1f}%")
    print(f"  Profit Factor:    {pf:.2f}")
    print(f"  Total PnL:        ${total_pnl:,.2f}")
    print(f"  Total Return:     {total_ret:+.1f}%")
    print(f"  Retorno mensual:  {total_ret / max(calendar_days/30, 1):+.1f}%/mes")
    print(f"  Max Drawdown:     {max_dd:.2f}%")
    print(f"  Avg R:            {avg_r:+.3f}")
    print(f"  Avg Win R:        {avg_win_r:+.3f}")
    print(f"  Avg Loss R:       {avg_loss_r:+.3f}")
    print(f"  Dias operados:    {n_days}")
    print(f"  Trades/dia:       {total_trades/n_days:.1f}")
    print(f"  Mejor dia:        ${best_day:,.2f} ({best_day_pct:+.2f}%)")
    print(f"  Peor dia:         ${worst_day:,.2f} ({worst_day_pct:+.2f}%)")
    print(f"  Dias FTMO block:  {days_blocked} / {n_days}")

    if "session" in df.columns:
        print(f"\n  Por sesion:")
        for sess in sorted(df["session"].unique()):
            s = df[df["session"] == sess]
            s_pnl = (s["pnl_r"] * RISK_USD).sum()
            s_wr = len(s[s["pnl_r"] > 0]) / len(s) * 100 if len(s) > 0 else 0
            s_pf_w = s[s["pnl_r"] > 0]["pnl_r"].sum() * RISK_USD if len(s[s["pnl_r"] > 0]) > 0 else 0
            s_pf_l = abs(s[s["pnl_r"] <= 0]["pnl_r"].sum()) * RISK_USD if len(s[s["pnl_r"] <= 0]) > 0 else 0
            s_pf = s_pf_w / s_pf_l if s_pf_l > 0 else float("inf")
            print(f"    {sess:12s}: {len(s):4d} trades | WR {s_wr:.1f}% | PF {s_pf:.2f} | PnL ${s_pnl:+,.2f}")

    final_balance = ACCOUNT + total_pnl
    print(f"\n  Balance final:    ${final_balance:,.2f}")
    print(f"{'='*60}")

    return {
        "label": label, "trades": total_trades, "wr": wr, "pf": pf,
        "total_pnl": total_pnl, "total_ret": total_ret, "max_dd": max_dd,
        "days_blocked": days_blocked, "worst_day": worst_day,
        "best_day": best_day, "n_days": n_days,
        "final_balance": final_balance, "calendar_days": calendar_days,
    }


def run_ob_london():
    csv_path = "strategies/order_block_london/backtest/results/trades.csv"
    print(f"\n[OB London] Cargando CSV: {csv_path}")
    df = pd.read_csv(csv_path, parse_dates=["entry_time", "exit_time"])
    print(f"  {len(df)} trades, sessions: {list(df.session.unique())}")

    from strategies.order_block_london.backtest.config import LONDON_PARAMS
    print(f"\n  Parametros live OB London:")
    print(f"    consecutive_candles: {LONDON_PARAMS['consecutive_candles']}")
    print(f"    zone_type:          {LONDON_PARAMS['zone_type']}")
    print(f"    buffer_points:      {LONDON_PARAMS['buffer_points']}")
    print(f"    target_rr:          {LONDON_PARAMS['target_rr']}")
    print(f"    max_sim_trades:     {LONDON_PARAMS['max_simultaneous_trades']}")
    print(f"    sessions:           {list(LONDON_PARAMS['sessions'].keys())}")
    print(f"    risk_per_trade_pct: {LONDON_PARAMS['risk_per_trade_pct']}")
    print(f"    entry_method:       {LONDON_PARAMS['entry_method']}")

    return analyze_fixed_risk(df, "OB London (Bot 2)")


def run_fvg():
    csv_path = "strategies/fair_value_gap/backtest/results/fvg_live_exact.csv"
    print(f"\n[FVG] Cargando CSV: {csv_path}")
    df = pd.read_csv(csv_path, parse_dates=["entry_time", "exit_time"])
    print(f"  {len(df)} trades, sessions: {df.session.value_counts().to_dict()}")

    from strategies.fair_value_gap.backtest.config import US30_PARAMS
    params = copy.deepcopy(US30_PARAMS)
    print(f"\n  Parametros live FVG:")
    print(f"    entry_method:       {params['entry_method']}")
    print(f"    buffer_points:      {params['buffer_points']}")
    print(f"    target_rr:          {params['target_rr']}")
    print(f"    max_sim_trades:     {params['max_simultaneous_trades']}")
    print(f"    ftmo_daily_loss:    {params['ftmo_daily_loss_pct']}%")
    print(f"    sessions:           {list(params['sessions'].keys())}")
    print(f"    min_zone_points:    {params.get('min_zone_points', 'NOT SET')}")
    print(f"    threshold_pct:      {params['threshold_pct']}")
    print(f"    risk_per_trade_pct: {params['risk_per_trade_pct']}")

    return analyze_fixed_risk(df, "FVG (Bot reemplazo)")


def print_comparison(ob_result, fvg_result):
    print(f"\n{'='*60}")
    print(f"  COMPARATIVA FINAL — Riesgo Fijo ${RISK_USD:.0f} / Cuenta ${ACCOUNT:,.0f}")
    print(f"{'='*60}")
    fmt = "  {:<22s} {:>15s} {:>15s}"
    print(fmt.format("Metrica", "OB London", "FVG"))
    print(f"  {'-'*52}")
    print(fmt.format("Trades", str(ob_result["trades"]), str(fvg_result["trades"])))
    print(fmt.format("Win Rate", f"{ob_result['wr']:.1f}%", f"{fvg_result['wr']:.1f}%"))
    print(fmt.format("Profit Factor", f"{ob_result['pf']:.2f}", f"{fvg_result['pf']:.2f}"))
    print(fmt.format("Total PnL", f"${ob_result['total_pnl']:+,.0f}", f"${fvg_result['total_pnl']:+,.0f}"))
    print(fmt.format("Total Return", f"{ob_result['total_ret']:+.1f}%", f"{fvg_result['total_ret']:+.1f}%"))
    print(fmt.format("Ret mensual",
                      f"{ob_result['total_ret']/max(ob_result['calendar_days']/30,1):+.1f}%/mes",
                      f"{fvg_result['total_ret']/max(fvg_result['calendar_days']/30,1):+.1f}%/mes"))
    print(fmt.format("Max Drawdown", f"{ob_result['max_dd']:.2f}%", f"{fvg_result['max_dd']:.2f}%"))
    print(fmt.format("Mejor dia", f"${ob_result['best_day']:+,.0f}", f"${fvg_result['best_day']:+,.0f}"))
    print(fmt.format("Peor dia", f"${ob_result['worst_day']:+,.0f}", f"${fvg_result['worst_day']:+,.0f}"))
    print(fmt.format("Dias FTMO block",
                      f"{ob_result['days_blocked']}/{ob_result['n_days']}",
                      f"{fvg_result['days_blocked']}/{fvg_result['n_days']}"))
    print(fmt.format("Balance final",
                      f"${ob_result['final_balance']:,.0f}",
                      f"${fvg_result['final_balance']:,.0f}"))
    print(f"{'='*60}")

    winner = "OB London" if ob_result["total_pnl"] > fvg_result["total_pnl"] else "FVG"
    print(f"\n  >>> Ganador en retorno total: {winner}")
    winner_dd = "OB London" if ob_result["max_dd"] < fvg_result["max_dd"] else "FVG"
    print(f"  >>> Menor drawdown: {winner_dd}")
    winner_pf = "OB London" if ob_result["pf"] > fvg_result["pf"] else "FVG"
    print(f"  >>> Mejor profit factor: {winner_pf}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ob",  action="store_true", help="Solo OB London")
    parser.add_argument("--fvg", action="store_true", help="Solo FVG")
    args = parser.parse_args()

    run_both = not args.ob and not args.fvg

    print("=" * 60)
    print("  BACKTEST DUAL -- Parametros Exactos del Live")
    print(f"  Cuenta: ${ACCOUNT:,.0f} | Riesgo fijo: ${RISK_USD:.0f}/trade")
    print("=" * 60)

    ob_result = fvg_result = None

    if args.ob or run_both:
        ob_result = run_ob_london()

    if args.fvg or run_both:
        fvg_result = run_fvg()

    if ob_result and fvg_result:
        print_comparison(ob_result, fvg_result)


if __name__ == "__main__":
    main()
