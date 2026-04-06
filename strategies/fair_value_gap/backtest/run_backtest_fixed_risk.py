# -*- coding: utf-8 -*-
"""
Recalcula resultados del backtest FVG con riesgo FIJO $50 (sin compounding).
Usa pnl_r (R-multiple) del backtest original para escalar a cuenta de $10k.

pnl_r es invariante al balance: 1R = ganas 1x tu riesgo, -1R = pierdes 1x tu riesgo.
Con riesgo fijo $50: PnL real = pnl_r * $50
"""
import sys
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

import pandas as pd
import numpy as np

ACCOUNT = 10_000.0
RISK_USD = 50.0  # 0.5% de $10k
FTMO_DAILY_LOSS_PCT = 4.0  # 4% = $400

def main():
    df = pd.read_csv("strategies/fair_value_gap/backtest/results/fvg_live_validation.csv",
                      parse_dates=["entry_time", "exit_time"])

    # Recalcular PnL con riesgo fijo $50
    df["pnl_real"] = df["pnl_r"] * RISK_USD

    total_trades = len(df)
    wins = df[df["pnl_real"] > 0]
    losses = df[df["pnl_real"] <= 0]
    wr = len(wins) / total_trades * 100

    total_pnl = df["pnl_real"].sum()
    avg_win = wins["pnl_real"].mean() if len(wins) > 0 else 0
    avg_loss = losses["pnl_real"].mean() if len(losses) > 0 else 0
    max_win = wins["pnl_real"].max() if len(wins) > 0 else 0
    max_loss = losses["pnl_real"].min() if len(losses) > 0 else 0

    gross_profit = wins["pnl_real"].sum() if len(wins) > 0 else 0
    gross_loss = abs(losses["pnl_real"].sum()) if len(losses) > 0 else 1
    pf = gross_profit / gross_loss if gross_loss > 0 else float("inf")

    # Analisis diario
    df["date"] = df["exit_time"].dt.date
    daily_pnl = df.groupby("date")["pnl_real"].sum()
    total_days = len(daily_pnl)
    profitable_days = (daily_pnl > 0).sum()
    losing_days = (daily_pnl < 0).sum()
    flat_days = (daily_pnl == 0).sum()

    worst_day = daily_pnl.min()
    worst_day_date = daily_pnl.idxmin()
    best_day = daily_pnl.max()
    best_day_date = daily_pnl.idxmax()

    ftmo_limit = ACCOUNT * FTMO_DAILY_LOSS_PCT / 100.0
    days_over_limit = (daily_pnl < -ftmo_limit).sum()

    # Trades por dia
    trades_per_day = df.groupby("date").size()
    avg_trades_day = trades_per_day.mean()
    max_trades_day = trades_per_day.max()

    # Rachas
    is_loss = (df["pnl_real"] <= 0).astype(int)
    streaks = is_loss * (is_loss.groupby((is_loss != is_loss.shift()).cumsum()).cumcount() + 1)
    max_consec_losses = int(streaks.max())

    is_win = (df["pnl_real"] > 0).astype(int)
    streaks_w = is_win * (is_win.groupby((is_win != is_win.shift()).cumsum()).cumcount() + 1)
    max_consec_wins = int(streaks_w.max())

    # Drawdown
    cumulative = df["pnl_real"].cumsum()
    peak = cumulative.cummax()
    dd_series = peak - cumulative
    dd_usd = dd_series.max()

    # Drawdown % sobre balance corriente
    balance_series = ACCOUNT + cumulative
    dd_pct_series = dd_series / (ACCOUNT + peak) * 100
    max_dd_pct = dd_pct_series.max()

    # Curva de balance
    balance_final = ACCOUNT + total_pnl
    retorno = total_pnl / ACCOUNT * 100

    # Analisis por sesion
    session_stats = df.groupby("session").agg(
        trades=("pnl_real", "count"),
        pnl=("pnl_real", "sum"),
        wr=("pnl_real", lambda x: (x > 0).sum() / len(x) * 100),
        avg_r=("pnl_r", "mean"),
    ).round(2)

    # Por mes
    df["month"] = df["exit_time"].dt.to_period("M")
    monthly = df.groupby("month").agg(
        trades=("pnl_real", "count"),
        pnl=("pnl_real", "sum"),
        wr=("pnl_real", lambda x: (x > 0).sum() / len(x) * 100),
    ).round(2)

    # Top 5 peores dias
    worst_5 = daily_pnl.nsmallest(5)

    # ============= OUTPUT =============
    print(f"\n{'='*65}")
    print(f"  BACKTEST FVG US30 — RIESGO FIJO $50 — CUENTA $10,000")
    print(f"{'='*65}")
    print(f"  Periodo:           {df['entry_time'].iloc[0].date()} -> {df['exit_time'].iloc[-1].date()} (518 dias)")
    print(f"  Trades totales:    {total_trades}")
    print(f"  Win Rate:          {wr:.1f}%")
    print(f"  Profit Factor:     {pf:.2f}")
    print(f"")
    print(f"  {'─'*50}")
    print(f"  RESULTADOS EN USD (riesgo $50 fijo por trade)")
    print(f"  {'─'*50}")
    print(f"  PnL total:         ${total_pnl:+,.2f}")
    print(f"  Balance final:     ${balance_final:,.2f}")
    print(f"  Retorno:           {retorno:+.1f}%")
    print(f"")
    print(f"  Avg win:           ${avg_win:+.2f}")
    print(f"  Avg loss:          ${avg_loss:+.2f}")
    print(f"  Max win (1 trade): ${max_win:+.2f}")
    print(f"  Max loss (1 trade):${max_loss:+.2f}")
    print(f"")
    print(f"  {'─'*50}")
    print(f"  ANALISIS DIARIO")
    print(f"  {'─'*50}")
    print(f"  Dias operados:     {total_days}")
    print(f"  Dias positivos:    {profitable_days} ({profitable_days/total_days*100:.0f}%)")
    print(f"  Dias negativos:    {losing_days} ({losing_days/total_days*100:.0f}%)")
    print(f"  Avg trades/dia:    {avg_trades_day:.1f}")
    print(f"  Max trades/dia:    {max_trades_day}")
    print(f"")
    print(f"  Mejor dia:         ${best_day:+.2f} ({best_day_date})")
    print(f"  Peor dia:          ${worst_day:+.2f} ({worst_day_date})")
    print(f"  Peor dia % cuenta: {abs(worst_day)/ACCOUNT*100:.2f}%")
    print(f"")
    print(f"  {'─'*50}")
    print(f"  FTMO RISK CHECK")
    print(f"  {'─'*50}")
    print(f"  Limite diario:     ${ftmo_limit:.0f} (4% de $10k)")
    print(f"  Dias sobre limite: {days_over_limit} de {total_days}")
    if days_over_limit > 0:
        print(f"  *** ALERTA: {days_over_limit} dias habrian violado el limite FTMO ***")
    else:
        print(f"  *** NUNCA se habria violado el limite FTMO diario ***")
    print(f"")
    print(f"  Top 5 peores dias:")
    for date, pnl in worst_5.items():
        pct = abs(pnl) / ACCOUNT * 100
        over = " <-- SOBRE LIMITE!" if pnl < -ftmo_limit else ""
        print(f"    {date}: ${pnl:+.2f} ({pct:.2f}%){over}")
    print(f"")
    print(f"  {'─'*50}")
    print(f"  DRAWDOWN Y RACHAS")
    print(f"  {'─'*50}")
    print(f"  Max drawdown:      ${dd_usd:,.2f} ({max_dd_pct:.2f}%)")
    print(f"  Max racha perdedora: {max_consec_losses} trades")
    print(f"  Max racha ganadora:  {max_consec_wins} trades")
    print(f"")
    print(f"  {'─'*50}")
    print(f"  POR SESION")
    print(f"  {'─'*50}")
    for session, row in session_stats.iterrows():
        print(f"  {session:12s}: {int(row['trades']):5d} trades | PnL ${row['pnl']:+,.2f} | WR {row['wr']:.1f}% | Avg R {row['avg_r']:+.3f}")
    print(f"")
    print(f"  {'─'*50}")
    print(f"  POR MES")
    print(f"  {'─'*50}")
    for month, row in monthly.iterrows():
        print(f"  {str(month):10s}: {int(row['trades']):4d} trades | PnL ${row['pnl']:+,.2f} | WR {row['wr']:.1f}%")
    print(f"")
    print(f"  {'─'*50}")
    print(f"  CONTEXTO FTMO CHALLENGE $10k")
    print(f"  {'─'*50}")
    print(f"  Meta de profit:    $1,000 (10% de $10k)")
    cumul = df["pnl_real"].cumsum()
    target_hit = cumul[cumul >= 1000]
    if len(target_hit) > 0:
        first_hit_idx = target_hit.index[0]
        first_hit_date = df.loc[first_hit_idx, "exit_time"]
        trades_to_target = first_hit_idx + 1
        days_to_target = (first_hit_date - df["entry_time"].iloc[0]).days
        print(f"  1er hit del target: Trade #{trades_to_target} ({first_hit_date.date()})")
        print(f"  Dias para target:   {days_to_target} dias")
    else:
        print(f"  NUNCA se alcanzo el target de $1,000")

    times_target_hit = (cumul >= 1000).sum()
    print(f"  Trades sobre $1k:  {times_target_hit} (de {total_trades})")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    main()
