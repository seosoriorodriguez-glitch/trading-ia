# -*- coding: utf-8 -*-
"""
Runner CLI — Opening Range Breakout — US30 M5 — 518 dias

Uso:
    python strategies/opening_range_breakout/backtest/run_backtest.py \
        --data data/US30_icm_M5_518d.csv

    # Probar distintas duraciones de rango:
    python ... --or-minutes 15
    python ... --or-minutes 30
    python ... --or-minutes 60

    # Probar RR:
    python ... --target-rr 2.0
    python ... --target-rr 3.0
"""
import sys
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

import argparse
import copy
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from strategies.opening_range_breakout.backtest.config import ORB_PARAMS
from strategies.opening_range_breakout.backtest.backtester import ORBBacktester
from strategies.fair_value_gap.backtest.data_loader import load_csv

RISK_USD = 50.0
ACCOUNT  = 10_000.0


def main():
    parser = argparse.ArgumentParser(description="ORB Backtester - US30")
    parser.add_argument("--data",       required=True, help="CSV M5 de US30")
    parser.add_argument("--or-minutes", type=int,   default=None, help="Duracion del rango (min)")
    parser.add_argument("--target-rr",  type=float, default=None, help="R:R objetivo")
    parser.add_argument("--buffer",     type=int,   default=None, help="Buffer SL en puntos")
    parser.add_argument("--min-range",  type=int,   default=None, help="Rango minimo en puntos")
    parser.add_argument("--output",     default=None, help="CSV de salida")
    args = parser.parse_args()

    params = copy.deepcopy(ORB_PARAMS)
    params["initial_balance"] = ACCOUNT
    if args.or_minutes: params["or_duration_minutes"] = args.or_minutes
    if args.target_rr:  params["target_rr"]           = args.target_rr
    if args.buffer:     params["buffer_points"]        = args.buffer
    if args.min_range:  params["min_range_points"]     = args.min_range

    print("=" * 55)
    print("  OPENING RANGE BREAKOUT — US30 M5")
    print("=" * 55)
    print(f"\nParametros:")
    print(f"  session:      {params['session_start']}-{params['session_end']} UTC+3 (NY)")
    print(f"  or_duration:  {params['or_duration_minutes']} minutos")
    print(f"  target_rr:    {params['target_rr']}")
    print(f"  buffer:       {params['buffer_points']} pts")
    print(f"  min_range:    {params['min_range_points']} pts")
    print(f"  max_range:    {params['max_range_points']} pts")
    print(f"  riesgo fijo:  ${RISK_USD}")

    print(f"\nCargando datos...")
    df = load_csv(args.data)
    print(f"  {len(df):,} velas M5 ({df['time'].iloc[0].date()} -> {df['time'].iloc[-1].date()})")

    print(f"\nEjecutando backtest...")
    bt = ORBBacktester(params)
    df_results = bt.run(df)

    if df_results.empty:
        print("\nSIN TRADES generados.")
        return

    # Metricas con riesgo fijo $50
    df_results["pnl_fixed"] = df_results["pnl_r"] * RISK_USD

    n      = len(df_results)
    wins   = df_results[df_results["pnl_fixed"] > 0]
    losses = df_results[df_results["pnl_fixed"] < 0]
    wr     = len(wins) / n * 100
    pf     = wins["pnl_fixed"].sum() / abs(losses["pnl_fixed"].sum()) if len(losses) > 0 else 999
    total  = df_results["pnl_fixed"].sum()
    ret    = total / ACCOUNT * 100

    cumul  = df_results["pnl_fixed"].cumsum()
    peak   = cumul.cummax()
    dd     = (peak - cumul) / (ACCOUNT + peak) * 100
    max_dd = dd.max()

    days   = (df_results["exit_time"].iloc[-1] - df_results["entry_time"].iloc[0]).days
    avg_month = total / (days / 30)

    df_results["month"] = df_results["exit_time"].dt.to_period("M")
    monthly = df_results.groupby("month").agg(
        trades=("pnl_fixed", "count"),
        pnl=("pnl_fixed", "sum"),
        wr=("pnl_fixed", lambda x: (x > 0).sum() / len(x) * 100),
    ).round(2)
    neg_months = (monthly["pnl"] < 0).sum()

    tp_n = len(df_results[df_results["exit_reason"] == "tp"])
    sl_n = len(df_results[df_results["exit_reason"] == "sl"])
    eos_n= len(df_results[df_results["exit_reason"].isin(["end_of_session","end_of_data"])])

    avg_range = df_results["or_range"].mean()

    # FTMO
    df_results["date"] = df_results["exit_time"].dt.date
    daily = df_results.groupby("date")["pnl_fixed"].sum()
    blocked = (daily < -(ACCOUNT * params["ftmo_daily_loss_pct"] / 100)).sum()

    print("\n" + "=" * 55)
    print("  RESULTADOS — ORB US30")
    print("=" * 55)
    print(f"  Periodo:       {days} dias")
    print(f"  Trades:        {n}  ({len(wins)}W / {len(losses)}L)")
    print(f"  Win Rate:      {wr:.1f}%")
    print(f"  Profit Factor: {pf:.2f}")
    print(f"  Retorno:       {ret:+.1f}%")
    print(f"  Balance final: ${ACCOUNT + total:,.2f}")
    print(f"  Max DD:        {max_dd:.2f}%")
    print(f"  Gan/mes:       ${avg_month:,.0f}")
    print(f"  Meses neg:     {neg_months} de {len(monthly)}")
    print(f"  Trades/dia:    {n/days:.2f}")
    print(f"  Avg OR range:  {avg_range:.0f} pts")
    print(f"")
    print(f"  TP hits:       {tp_n}")
    print(f"  SL hits:       {sl_n}")
    print(f"  Fin sesion:    {eos_n}")
    print(f"  FTMO bloq:     {blocked} dias")
    print()
    print("  POR MES:")
    for month, row in monthly.iterrows():
        m = " <--" if row["pnl"] < 0 else ""
        print(f"  {str(month):10s}: {int(row['trades']):3d} trades | PnL ${row['pnl']:+,.0f} | WR {row['wr']:.1f}%{m}")
    print("=" * 55)

    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        df_results.to_csv(args.output, index=False)
        print(f"\nTrades guardados en: {args.output}")


if __name__ == "__main__":
    main()
