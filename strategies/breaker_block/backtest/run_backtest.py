# -*- coding: utf-8 -*-
"""
Runner CLI — Breaker Block Backtest — US30 M5/M1 — 518 dias

Uso:
    python strategies/breaker_block/backtest/run_backtest.py \
        --data-m5 data/US30_icm_M5_518d.csv \
        --data-m1 data/US30_icm_M1_500k.csv

    # Probar pivot length:
    python ... --pivot-length 3
    python ... --pivot-length 5

    # Probar RR:
    python ... --target-rr 2.5

    # Probar buffer:
    python ... --buffer 35
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

from strategies.breaker_block.backtest.config    import BB_PARAMS
from strategies.breaker_block.backtest.backtester import BBBacktester
from strategies.fair_value_gap.backtest.data_loader import load_csv, validate_alignment

RISK_USD = 50.0
ACCOUNT  = 10_000.0


def main():
    parser = argparse.ArgumentParser(description="Breaker Block Backtester - US30")
    parser.add_argument("--data-m5",      required=True)
    parser.add_argument("--data-m1",      required=True)
    parser.add_argument("--consecutive",   type=int,   default=None)
    parser.add_argument("--target-rr",   type=float, default=None)
    parser.add_argument("--buffer",       type=int,   default=None)
    parser.add_argument("--output",       default=None)
    args = parser.parse_args()

    params = copy.deepcopy(BB_PARAMS)
    params["initial_balance"] = ACCOUNT
    if args.consecutive:  params["consecutive_candles"] = args.consecutive
    if args.target_rr:    params["target_rr"]     = args.target_rr
    if args.buffer:       params["buffer_points"] = args.buffer

    print("=" * 55)
    print("  BREAKER BLOCK BACKTEST — US30 M5/M1")
    print("=" * 55)
    print(f"\nParametros:")
    print(f"  consecutive:   {params['consecutive_candles']}")
    print(f"  target_rr:     {params['target_rr']}")
    print(f"  buffer:        {params['buffer_points']} pts")
    print(f"  max_sim:       {params['max_simultaneous_trades']}")
    print(f"  sessions:      {list(params['sessions'].keys())}")
    print(f"  riesgo fijo:   ${RISK_USD}")

    print(f"\nCargando datos...")
    df_m5 = load_csv(args.data_m5)
    df_m1 = load_csv(args.data_m1)
    validate_alignment(df_m5, df_m1)
    print(f"  M5: {len(df_m5):,} velas ({df_m5['time'].iloc[0].date()} -> {df_m5['time'].iloc[-1].date()})")
    print(f"  M1: {len(df_m1):,} velas")

    print(f"\nEjecutando backtest...")
    bt = BBBacktester(params)
    df = bt.run(df_m5, df_m1)

    if df.empty:
        print("\nSIN TRADES generados.")
        return

    # Metricas riesgo fijo $50
    df["pnl_fixed"] = df["pnl_r"] * RISK_USD

    n      = len(df)
    wins   = df[df["pnl_fixed"] > 0]
    losses = df[df["pnl_fixed"] < 0]
    wr     = len(wins) / n * 100
    pf     = wins["pnl_fixed"].sum() / abs(losses["pnl_fixed"].sum()) if len(losses) > 0 else 999
    total  = df["pnl_fixed"].sum()
    ret    = total / ACCOUNT * 100

    cumul  = df["pnl_fixed"].cumsum()
    peak   = cumul.cummax()
    dd     = (peak - cumul) / (ACCOUNT + peak) * 100
    max_dd = dd.max()

    days      = (df["exit_time"].iloc[-1] - df["entry_time"].iloc[0]).days
    avg_month = total / (days / 30)

    df["month"] = df["exit_time"].dt.to_period("M")
    monthly = df.groupby("month").agg(
        trades=("pnl_fixed", "count"),
        pnl=("pnl_fixed", "sum"),
        wr=("pnl_fixed", lambda x: (x > 0).sum() / len(x) * 100),
    ).round(2)
    neg_months = (monthly["pnl"] < 0).sum()

    # Por sesion
    session_stats = df.groupby("session").agg(
        trades=("pnl_fixed", "count"),
        pnl=("pnl_fixed", "sum"),
        wr=("pnl_fixed", lambda x: (x > 0).sum() / len(x) * 100),
    ).round(2)

    # FTMO
    df["date"] = df["exit_time"].dt.date
    daily = df.groupby("date")["pnl_fixed"].sum()
    blocked = (daily < -(ACCOUNT * params["ftmo_daily_loss_pct"] / 100)).sum()

    tp_n  = len(df[df["exit_reason"] == "tp"])
    sl_n  = len(df[df["exit_reason"] == "sl"])
    eod_n = len(df[df["exit_reason"] == "end_of_data"])

    print("\n" + "=" * 55)
    print("  RESULTADOS — BREAKER BLOCK US30")
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
    print(f"")
    print(f"  TP hits:       {tp_n}")
    print(f"  SL hits:       {sl_n}")
    print(f"  End of data:   {eod_n}")
    print(f"  FTMO bloq:     {blocked} dias")
    print()
    print("  POR SESION:")
    for sess, row in session_stats.iterrows():
        print(f"  {sess:12s}: {int(row['trades']):4d} trades | PnL ${row['pnl']:+,.0f} | WR {row['wr']:.1f}%")
    print()
    print("  POR MES:")
    for month, row in monthly.iterrows():
        m = " <--" if row["pnl"] < 0 else ""
        print(f"  {str(month):10s}: {int(row['trades']):3d} trades | PnL ${row['pnl']:+,.0f} | WR {row['wr']:.1f}%{m}")
    print("=" * 55)

    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(args.output, index=False)
        print(f"\nTrades guardados en: {args.output}")


if __name__ == "__main__":
    main()
