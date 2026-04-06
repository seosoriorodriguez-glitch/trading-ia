# -*- coding: utf-8 -*-
"""
Analiza cuantos trades del backtest original tenian look-ahead
(entrada durante la vela M5 de confirmacion, antes de que cierre).

Luego recalcula los resultados excluyendo esos trades,
con riesgo fijo $50 para simular la cuenta real de $10k.
"""
import sys
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

import pandas as pd
from datetime import timedelta

ACCOUNT = 10_000.0
RISK_USD = 50.0
FTMO_DAILY_LOSS_PCT = 4.0

def main():
    df = pd.read_csv(
        "strategies/fair_value_gap/backtest/results/fvg_live_validation.csv",
        parse_dates=["entry_time", "exit_time", "fvg_confirmed_at"],
    )

    # fvg_confirmed_at en el CSV original = apertura de vela 3 (el bug)
    # El FVG solo deberia estar disponible despues del CIERRE de vela 3
    # = confirmed_at + 5 minutos
    fvg_close_time = df["fvg_confirmed_at"] + timedelta(minutes=5)

    # Trade con look-ahead = entry_time < cierre de vela 3
    df["has_lookahead"] = df["entry_time"] < fvg_close_time

    n_total = len(df)
    n_lookahead = df["has_lookahead"].sum()
    n_clean = n_total - n_lookahead

    print(f"\n{'='*60}")
    print(f"  ANALISIS DE LOOK-AHEAD EN BACKTEST FVG")
    print(f"{'='*60}")
    print(f"  Trades totales:      {n_total}")
    print(f"  Trades con look-ahead (entrada antes del cierre de vela 3): {n_lookahead} ({n_lookahead/n_total*100:.1f}%)")
    print(f"  Trades limpios:      {n_clean} ({n_clean/n_total*100:.1f}%)")
    print()

    # Desglose de los trades con look-ahead
    la = df[df["has_lookahead"]]
    la_wins = (la["pnl_r"] > 0).sum()
    la_losses = (la["pnl_r"] <= 0).sum()
    la_wr = la_wins / len(la) * 100 if len(la) > 0 else 0
    la_avg_r = la["pnl_r"].mean()
    print(f"  --- Trades look-ahead ({n_lookahead}) ---")
    print(f"  Win Rate:  {la_wr:.1f}%")
    print(f"  Avg R:     {la_avg_r:+.3f}")
    print(f"  Wins:      {la_wins}")
    print(f"  Losses:    {la_losses}")

    # Cuantos entraron en los primeros minutos
    time_diff = (df.loc[df["has_lookahead"], "entry_time"] - df.loc[df["has_lookahead"], "fvg_confirmed_at"]).dt.total_seconds() / 60
    print(f"  Tiempo promedio entre confirmed_at y entry: {time_diff.mean():.1f} min")
    print(f"  Max: {time_diff.max():.1f} min")
    print()

    # =====================================================================
    # RESULTADOS SIN LOOK-AHEAD (trades limpios) con riesgo fijo $50
    # =====================================================================
    clean = df[~df["has_lookahead"]].copy()
    clean["pnl_real"] = clean["pnl_r"] * RISK_USD

    total_trades = len(clean)
    wins = clean[clean["pnl_real"] > 0]
    losses = clean[clean["pnl_real"] <= 0]
    wr = len(wins) / total_trades * 100 if total_trades > 0 else 0
    total_pnl = clean["pnl_real"].sum()

    gross_profit = wins["pnl_real"].sum() if len(wins) > 0 else 0
    gross_loss = abs(losses["pnl_real"].sum()) if len(losses) > 0 else 1
    pf = gross_profit / gross_loss if gross_loss > 0 else float("inf")

    avg_win = wins["pnl_real"].mean() if len(wins) > 0 else 0
    avg_loss = losses["pnl_real"].mean() if len(losses) > 0 else 0

    # Diario
    clean["date"] = clean["exit_time"].dt.date
    daily_pnl = clean.groupby("date")["pnl_real"].sum()
    total_days = len(daily_pnl)
    profitable_days = (daily_pnl > 0).sum()
    losing_days = (daily_pnl < 0).sum()
    worst_day = daily_pnl.min()
    worst_day_date = daily_pnl.idxmin()
    best_day = daily_pnl.max()
    best_day_date = daily_pnl.idxmax()

    ftmo_limit = ACCOUNT * FTMO_DAILY_LOSS_PCT / 100.0
    days_over_limit = (daily_pnl < -ftmo_limit).sum()

    # Drawdown
    cumulative = clean["pnl_real"].cumsum()
    peak = cumulative.cummax()
    dd_usd = (peak - cumulative).max()

    # Rachas
    is_loss = (clean["pnl_real"] <= 0).astype(int)
    streaks = is_loss * (is_loss.groupby((is_loss != is_loss.shift()).cumsum()).cumcount() + 1)
    max_consec_losses = int(streaks.max()) if len(streaks) > 0 else 0

    # Mensual
    clean["month"] = clean["exit_time"].dt.to_period("M")
    monthly = clean.groupby("month").agg(
        trades=("pnl_real", "count"),
        pnl=("pnl_real", "sum"),
        wr=("pnl_real", lambda x: (x > 0).sum() / len(x) * 100),
    ).round(2)

    print(f"{'='*60}")
    print(f"  RESULTADOS CORREGIDOS (SIN LOOK-AHEAD)")
    print(f"  Cuenta $10k, Riesgo $50 fijo por trade")
    print(f"{'='*60}")
    print(f"  Trades totales:    {total_trades}")
    print(f"  Win Rate:          {wr:.1f}%")
    print(f"  Profit Factor:     {pf:.2f}")
    print(f"")
    print(f"  PnL total:         ${total_pnl:+,.2f}")
    print(f"  Balance final:     ${ACCOUNT + total_pnl:,.2f}")
    print(f"  Retorno:           {total_pnl/ACCOUNT*100:+.1f}%")
    print(f"")
    print(f"  Avg win:           ${avg_win:+.2f}")
    print(f"  Avg loss:          ${avg_loss:+.2f}")
    print(f"")
    print(f"  {'_'*50}")
    print(f"  ANALISIS DIARIO")
    print(f"  {'_'*50}")
    print(f"  Dias operados:     {total_days}")
    print(f"  Dias positivos:    {profitable_days} ({profitable_days/total_days*100:.0f}%)")
    print(f"  Dias negativos:    {losing_days} ({losing_days/total_days*100:.0f}%)")
    print(f"  Mejor dia:         ${best_day:+.2f} ({best_day_date})")
    print(f"  Peor dia:          ${worst_day:+.2f} ({worst_day_date})")
    print(f"  Peor dia % cuenta: {abs(worst_day)/ACCOUNT*100:.2f}%")
    print(f"")
    print(f"  Limite FTMO diario: ${ftmo_limit:.0f} (4% de $10k)")
    print(f"  Dias sobre limite:  {days_over_limit} de {total_days}")
    print(f"")
    print(f"  Max drawdown:       ${dd_usd:,.2f} ({dd_usd/ACCOUNT*100:.2f}%)")
    print(f"  Max racha perdedora: {max_consec_losses} trades")
    print(f"")
    print(f"  {'_'*50}")
    print(f"  POR MES")
    print(f"  {'_'*50}")
    for month, row in monthly.iterrows():
        print(f"  {str(month):10s}: {int(row['trades']):4d} trades | PnL ${row['pnl']:+,.2f} | WR {row['wr']:.1f}%")
    print()

    # =====================================================================
    # COMPARACION: ORIGINAL vs CORREGIDO
    # =====================================================================
    df["pnl_real_orig"] = df["pnl_r"] * RISK_USD
    orig_pnl = df["pnl_real_orig"].sum()
    orig_wr = (df["pnl_r"] > 0).sum() / len(df) * 100

    orig_gp = df.loc[df["pnl_real_orig"] > 0, "pnl_real_orig"].sum()
    orig_gl = abs(df.loc[df["pnl_real_orig"] <= 0, "pnl_real_orig"].sum())
    orig_pf = orig_gp / orig_gl if orig_gl > 0 else float("inf")

    print(f"{'='*60}")
    print(f"  COMPARACION: ORIGINAL vs CORREGIDO (sin look-ahead)")
    print(f"{'='*60}")
    print(f"  {'Metrica':<25s} {'Original':>12s} {'Corregido':>12s} {'Diff':>10s}")
    print(f"  {'-'*60}")
    print(f"  {'Trades':<25s} {n_total:>12d} {total_trades:>12d} {total_trades-n_total:>+10d}")
    print(f"  {'Win Rate':<25s} {orig_wr:>11.1f}% {wr:>11.1f}%")
    print(f"  {'Profit Factor':<25s} {orig_pf:>12.2f} {pf:>12.2f}")
    print(f"  {'PnL total':<25s} {'${:+,.0f}'.format(orig_pnl):>12s} {'${:+,.0f}'.format(total_pnl):>12s} {'${:+,.0f}'.format(total_pnl-orig_pnl):>10s}")
    print(f"  {'Retorno':<25s} {orig_pnl/ACCOUNT*100:>+11.1f}% {total_pnl/ACCOUNT*100:>+11.1f}%")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
