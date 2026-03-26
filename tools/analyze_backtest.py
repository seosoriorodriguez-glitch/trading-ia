"""
Análisis de resultados de backtest.

Genera reportes visuales y métricas detalladas.
Ejecutar después de run_backtest.py

Uso:
  python analyze_backtest.py --results data/backtest_US30.csv
  python analyze_backtest.py --results data/backtest_US30.csv --save-report
"""

import sys
import argparse
import logging
from pathlib import Path

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Backend sin GUI — genera archivos
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

sys.path.insert(0, str(Path(__file__).parent))


def load_results(filepath: str) -> pd.DataFrame:
    df = pd.read_csv(filepath, parse_dates=["entry_time", "exit_time"])
    return df


def calculate_metrics(df: pd.DataFrame, initial_balance: float = 100_000) -> dict:
    """Calcula todas las métricas relevantes para FTMO."""

    total = len(df)
    winners = df[df["pnl_points"] > 0]
    losers = df[df["pnl_points"] < 0]
    breakeven = df[df["pnl_points"] == 0]

    win_rate = len(winners) / total if total > 0 else 0

    gross_profit = winners["pnl_points"].sum() if len(winners) > 0 else 0
    gross_loss = abs(losers["pnl_points"].sum()) if len(losers) > 0 else 0
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

    avg_win = winners["pnl_points"].mean() if len(winners) > 0 else 0
    avg_loss = losers["pnl_points"].mean() if len(losers) > 0 else 0

    # Expectancia por trade
    expectancy = (win_rate * avg_win) + ((1 - win_rate) * avg_loss)

    # Max consecutive losses
    is_loss = (df["pnl_points"] < 0).astype(int)
    loss_groups = is_loss.ne(is_loss.shift()).cumsum()
    max_consec_losses = is_loss.groupby(loss_groups).sum().max() if len(is_loss) > 0 else 0

    # Max consecutive wins
    is_win = (df["pnl_points"] > 0).astype(int)
    win_groups = is_win.ne(is_win.shift()).cumsum()
    max_consec_wins = is_win.groupby(win_groups).sum().max() if len(is_win) > 0 else 0

    # Equity curve para drawdown
    risk_per_trade = initial_balance * 0.005  # 0.5%
    df_sorted = df.sort_values("entry_time")
    pnl_usd = []
    for _, row in df_sorted.iterrows():
        if row["direction"] == "LONG":
            planned_risk = row["entry_price"] - row["stop_loss"]
        else:
            planned_risk = row["stop_loss"] - row["entry_price"]
        if planned_risk > 0:
            trade_pnl = (row["pnl_points"] / planned_risk) * risk_per_trade
        else:
            trade_pnl = 0
        pnl_usd.append(trade_pnl)

    equity_curve = [initial_balance]
    for pnl in pnl_usd:
        equity_curve.append(equity_curve[-1] + pnl)

    equity = np.array(equity_curve)
    peaks = np.maximum.accumulate(equity)
    drawdowns = (peaks - equity) / peaks
    max_drawdown = drawdowns.max()

    # Max daily drawdown (simulado)
    df_sorted["pnl_usd"] = pnl_usd
    if "entry_time" in df_sorted.columns:
        df_sorted["date"] = df_sorted["entry_time"].dt.date
        daily_pnl = df_sorted.groupby("date")["pnl_usd"].sum()
        max_daily_dd = abs(daily_pnl.min()) / initial_balance if len(daily_pnl) > 0 else 0
    else:
        max_daily_dd = 0

    final_balance = equity_curve[-1]
    total_return = (final_balance - initial_balance) / initial_balance

    # Trades por mes
    if len(df_sorted) > 0 and "entry_time" in df_sorted.columns:
        months = (df_sorted["entry_time"].max() - df_sorted["entry_time"].min()).days / 30
        trades_per_month = total / months if months > 0 else 0
    else:
        trades_per_month = 0

    # Por tipo de señal
    by_signal = {}
    for stype in df["signal_type"].unique():
        subset = df[df["signal_type"] == stype]
        wins_s = len(subset[subset["pnl_points"] > 0])
        wr_s = wins_s / len(subset) if len(subset) > 0 else 0
        by_signal[stype] = {
            "count": len(subset),
            "win_rate": wr_s,
            "avg_pnl": subset["pnl_points"].mean(),
        }

    # Por dirección
    by_direction = {}
    for d in ["LONG", "SHORT"]:
        subset = df[df["direction"] == d]
        if len(subset) > 0:
            wins_d = len(subset[subset["pnl_points"] > 0])
            by_direction[d] = {
                "count": len(subset),
                "win_rate": wins_d / len(subset),
                "avg_pnl": subset["pnl_points"].mean(),
            }

    return {
        "total_trades": total,
        "winners": len(winners),
        "losers": len(losers),
        "breakeven": len(breakeven),
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "avg_win_pts": avg_win,
        "avg_loss_pts": avg_loss,
        "expectancy_pts": expectancy,
        "max_consecutive_wins": int(max_consec_wins),
        "max_consecutive_losses": int(max_consec_losses),
        "max_drawdown_pct": max_drawdown,
        "max_daily_drawdown_pct": max_daily_dd,
        "initial_balance": initial_balance,
        "final_balance": final_balance,
        "total_return_pct": total_return,
        "trades_per_month": trades_per_month,
        "equity_curve": equity_curve,
        "by_signal_type": by_signal,
        "by_direction": by_direction,
        "pnl_usd_series": pnl_usd,
    }


def print_report(metrics: dict):
    """Imprime reporte en consola."""

    print("\n" + "=" * 65)
    print("              REPORTE DE BACKTEST")
    print("=" * 65)

    print(f"\n--- Rendimiento General ---")
    print(f"  Balance Inicial:       ${metrics['initial_balance']:>12,.2f}")
    print(f"  Balance Final:         ${metrics['final_balance']:>12,.2f}")
    print(f"  Retorno Total:          {metrics['total_return_pct']:>11.2%}")
    print(f"  Trades por Mes:         {metrics['trades_per_month']:>11.1f}")

    print(f"\n--- Estadísticas de Trades ---")
    print(f"  Total Operaciones:      {metrics['total_trades']:>11d}")
    print(f"  Ganadoras:              {metrics['winners']:>11d}  ({metrics['win_rate']:.1%})")
    print(f"  Perdedoras:             {metrics['losers']:>11d}")
    print(f"  Break Even:             {metrics['breakeven']:>11d}")
    print(f"  Profit Factor:          {metrics['profit_factor']:>11.2f}")
    print(f"  Expectancia/Trade:      {metrics['expectancy_pts']:>11.1f} pts")

    print(f"\n--- Promedios ---")
    print(f"  Ganancia Promedio:      {metrics['avg_win_pts']:>11.1f} pts")
    print(f"  Pérdida Promedio:       {metrics['avg_loss_pts']:>11.1f} pts")
    print(f"  Ratio W/L:              {abs(metrics['avg_win_pts']/metrics['avg_loss_pts']) if metrics['avg_loss_pts'] != 0 else 0:>11.2f}")

    print(f"\n--- Rachas ---")
    print(f"  Max Wins Consecutivas:  {metrics['max_consecutive_wins']:>11d}")
    print(f"  Max Losses Consecutivas:{metrics['max_consecutive_losses']:>11d}")

    print(f"\n--- Drawdown ---")
    print(f"  Max Drawdown Total:     {metrics['max_drawdown_pct']:>11.2%}")
    print(f"  Max Drawdown Diario:    {metrics['max_daily_drawdown_pct']:>11.2%}")

    # FTMO Compliance
    print(f"\n{'='*65}")
    print("              COMPLIANCE FTMO")
    print(f"{'='*65}")

    checks = [
        ("Max DD Total < 8%", metrics["max_drawdown_pct"] < 0.08),
        ("Max DD Diario < 4%", metrics["max_daily_drawdown_pct"] < 0.04),
        ("Profit Factor > 1.0", metrics["profit_factor"] > 1.0),
        ("Win Rate > 40%", metrics["win_rate"] > 0.40),
        ("Trades suficientes (>50)", metrics["total_trades"] > 50),
    ]

    all_pass = True
    for name, passed in checks:
        icon = "✅" if passed else "❌"
        print(f"  {icon} {name}")
        if not passed:
            all_pass = False

    if all_pass:
        print(f"\n  🏆 ESTRATEGIA VIABLE PARA FTMO")
    else:
        print(f"\n  ⚠️  Algunos criterios no se cumplen — ajustar parámetros")

    # Por tipo de señal
    print(f"\n{'='*65}")
    print("              POR TIPO DE SEÑAL")
    print(f"{'='*65}")
    for stype, data in metrics["by_signal_type"].items():
        print(f"  {stype:25s}  {data['count']:3d} trades  "
              f"WR: {data['win_rate']:.1%}  Avg: {data['avg_pnl']:+.1f} pts")

    # Por dirección
    print(f"\n{'='*65}")
    print("              POR DIRECCIÓN")
    print(f"{'='*65}")
    for direction, data in metrics["by_direction"].items():
        print(f"  {direction:25s}  {data['count']:3d} trades  "
              f"WR: {data['win_rate']:.1%}  Avg: {data['avg_pnl']:+.1f} pts")

    print(f"\n{'='*65}\n")


def generate_charts(metrics: dict, df: pd.DataFrame, output_dir: str = "data"):
    """Genera gráficos de análisis."""
    Path(output_dir).mkdir(exist_ok=True)

    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle("Análisis de Backtest — Estrategia S/R Índices", fontsize=14, fontweight="bold")

    # --- 1. Equity Curve ---
    ax1 = axes[0, 0]
    equity = metrics["equity_curve"]
    ax1.plot(equity, color="#2196F3", linewidth=1.5)
    ax1.axhline(y=metrics["initial_balance"], color="gray", linestyle="--", alpha=0.5)
    ax1.fill_between(range(len(equity)), metrics["initial_balance"], equity,
                     where=[e >= metrics["initial_balance"] for e in equity],
                     alpha=0.15, color="green")
    ax1.fill_between(range(len(equity)), metrics["initial_balance"], equity,
                     where=[e < metrics["initial_balance"] for e in equity],
                     alpha=0.15, color="red")
    ax1.set_title("Equity Curve")
    ax1.set_ylabel("Balance ($)")
    ax1.set_xlabel("Trade #")
    ax1.grid(True, alpha=0.3)

    # --- 2. Distribución de P&L ---
    ax2 = axes[0, 1]
    pnl = df["pnl_points"].dropna()
    colors = ["#4CAF50" if x > 0 else "#F44336" for x in pnl]
    ax2.bar(range(len(pnl)), pnl, color=colors, alpha=0.7, width=1.0)
    ax2.axhline(y=0, color="white", linewidth=0.5)
    ax2.set_title("P&L por Trade (puntos)")
    ax2.set_xlabel("Trade #")
    ax2.set_ylabel("Puntos")
    ax2.grid(True, alpha=0.3)

    # --- 3. Win Rate por Tipo de Señal ---
    ax3 = axes[1, 0]
    signal_types = list(metrics["by_signal_type"].keys())
    win_rates = [metrics["by_signal_type"][s]["win_rate"] * 100 for s in signal_types]
    counts = [metrics["by_signal_type"][s]["count"] for s in signal_types]

    bars = ax3.bar(signal_types, win_rates, color=["#2196F3", "#FF9800", "#4CAF50", "#9C27B0"][:len(signal_types)])

    # Agregar conteo encima de cada barra
    for bar, count in zip(bars, counts):
        ax3.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 1,
                f'n={count}', ha='center', va='bottom', fontsize=9)

    ax3.axhline(y=50, color="gray", linestyle="--", alpha=0.5, label="50%")
    ax3.set_title("Win Rate por Tipo de Señal")
    ax3.set_ylabel("Win Rate (%)")
    ax3.set_ylim(0, 100)
    ax3.grid(True, alpha=0.3)
    ax3.tick_params(axis='x', rotation=15)

    # --- 4. Drawdown ---
    ax4 = axes[1, 1]
    equity_arr = np.array(metrics["equity_curve"])
    peaks = np.maximum.accumulate(equity_arr)
    dd_pct = ((peaks - equity_arr) / peaks) * 100

    ax4.fill_between(range(len(dd_pct)), 0, dd_pct, color="#F44336", alpha=0.4)
    ax4.axhline(y=8, color="red", linestyle="--", linewidth=2, label="Límite FTMO (8%)")
    ax4.axhline(y=4, color="orange", linestyle="--", linewidth=1, label="Alerta (4%)")
    ax4.set_title("Drawdown (%)")
    ax4.set_xlabel("Trade #")
    ax4.set_ylabel("Drawdown (%)")
    ax4.legend()
    ax4.invert_yaxis()
    ax4.grid(True, alpha=0.3)

    plt.tight_layout()

    chart_path = f"{output_dir}/backtest_analysis.png"
    fig.savefig(chart_path, dpi=150, bbox_inches="tight", facecolor="#1a1a2e")
    plt.close()

    logger.info(f"Gráficos guardados: {chart_path}")
    return chart_path


def generate_monthly_breakdown(df: pd.DataFrame) -> pd.DataFrame:
    """Genera tabla de rendimiento mensual."""
    df_copy = df.copy()
    df_copy["month"] = df_copy["entry_time"].dt.to_period("M")

    monthly = df_copy.groupby("month").agg(
        trades=("pnl_points", "count"),
        wins=("pnl_points", lambda x: (x > 0).sum()),
        total_pts=("pnl_points", "sum"),
        avg_pts=("pnl_points", "mean"),
        best_trade=("pnl_points", "max"),
        worst_trade=("pnl_points", "min"),
    ).reset_index()

    monthly["win_rate"] = (monthly["wins"] / monthly["trades"] * 100).round(1)

    print(f"\n{'='*80}")
    print("RENDIMIENTO MENSUAL")
    print(f"{'='*80}")
    print(monthly.to_string(index=False))
    print(f"{'='*80}\n")

    return monthly


# ============================================================
# Main
# ============================================================

logger = logging.getLogger("analysis")

def main():
    parser = argparse.ArgumentParser(description="Análisis de backtest")
    parser.add_argument("--results", required=True, help="CSV de resultados del backtest")
    parser.add_argument("--balance", type=float, default=100_000)
    parser.add_argument("--save-report", action="store_true", help="Guardar gráficos")
    parser.add_argument("--output-dir", default="data")
    args = parser.parse_args()

    df = load_results(args.results)

    if df.empty:
        print("Error: CSV vacío o sin trades")
        sys.exit(1)

    metrics = calculate_metrics(df, args.balance)
    print_report(metrics)
    generate_monthly_breakdown(df)

    if args.save_report:
        chart_path = generate_charts(metrics, df, args.output_dir)
        print(f"📊 Gráficos guardados en: {chart_path}")


if __name__ == "__main__":
    main()
