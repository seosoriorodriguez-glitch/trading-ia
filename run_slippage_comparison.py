# -*- coding: utf-8 -*-
"""
Comparacion slippage Bot 2 London:
  - Baseline: sin slippage (slippage_points=0)
  - Con costos: con slippage (slippage_points=2)

Genera tabla comparativa + breakdown por trimestre.
Uso: python run_slippage_comparison.py
"""
import sys, copy
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")

sys.path.insert(0, '.')

import pandas as pd
import numpy as np
from pathlib import Path
from strategies.order_block_london.backtest.config import LONDON_PARAMS
from strategies.order_block.backtest.data_loader import load_csv
from strategies.order_block.backtest.backtester_limit_orders import OrderBlockBacktesterLimitOrders

# ----------------------------------------------------------------
# 1. Cargar datos
# ----------------------------------------------------------------
print("Cargando datos US30...")
df_m5 = load_csv("data/US30_icm_M5_518d.csv")
df_m1 = load_csv("data/US30_icm_M1_500k.csv")
print(f"  M5: {len(df_m5):,} | M1: {len(df_m1):,}")

# ----------------------------------------------------------------
# 2. Correr las dos variantes
# ----------------------------------------------------------------
results = {}

for label, slip in [("sin_slippage", 0), ("con_slippage", 2)]:
    params = copy.deepcopy(LONDON_PARAMS)
    params["slippage_points"] = slip
    print(f"\nCorriendo [{label}] slippage={slip} pts...")
    bt = OrderBlockBacktesterLimitOrders(params)
    trades_df = bt.run(df_m5, df_m1)

    # Calcular balance acumulado y drawdown
    running = params["initial_balance"]
    peak    = params["initial_balance"]
    balance_list, dd_list = [], []
    for _, row in trades_df.iterrows():
        running += row["pnl_usd"]
        if running > peak:
            peak = running
        balance_list.append(running)
        dd_list.append((peak - running) / peak * 100)

    trades_df["balance_post"] = balance_list
    trades_df["dd_pct"]       = dd_list

    results[label] = {
        "params":    params,
        "trades_df": trades_df,
        "bt":        bt,
    }
    print(f"  Trades: {len(trades_df)}")

# ----------------------------------------------------------------
# 3. Calcular metricas
# ----------------------------------------------------------------
def calc_metrics(trades_df, initial_balance):
    w = trades_df[trades_df["pnl_usd"] > 0]
    l = trades_df[trades_df["pnl_usd"] < 0]
    n = len(trades_df)
    if n == 0:
        return {}
    wr    = len(w) / n * 100
    pf    = w["pnl_usd"].sum() / abs(l["pnl_usd"].sum()) if len(l) > 0 else 999
    total = trades_df["pnl_usd"].sum()
    exp   = total / n
    ret   = total / initial_balance * 100
    max_dd = trades_df["dd_pct"].max()

    daily_pnl = trades_df.groupby(trades_df["entry_time"].dt.date)["pnl_usd"].sum()
    sharpe = (daily_pnl.mean() / daily_pnl.std() * np.sqrt(252)) if daily_pnl.std() > 0 else 0

    avg_w = w["pnl_usd"].mean() if len(w) > 0 else 0
    avg_l = l["pnl_usd"].mean() if len(l) > 0 else 0

    return {
        "trades": n, "wr": wr, "pf": pf, "expectancy": exp,
        "total_pnl": total, "ret_pct": ret, "max_dd": max_dd,
        "sharpe": sharpe, "avg_win": avg_w, "avg_loss": avg_l,
    }

m_base = calc_metrics(results["sin_slippage"]["trades_df"], LONDON_PARAMS["initial_balance"])
m_slip = calc_metrics(results["con_slippage"]["trades_df"], LONDON_PARAMS["initial_balance"])

# ----------------------------------------------------------------
# 4. Tabla comparativa
# ----------------------------------------------------------------
print("\n")
print("=" * 72)
print("  COMPARACION: SIN SLIPPAGE vs CON SLIPPAGE (spread=2 + slip=2 entrada/SL)")
print("=" * 72)

rows = [
    ("Trades",      f"{m_base['trades']}",              f"{m_slip['trades']}",          f"{m_slip['trades'] - m_base['trades']:+d}"),
    ("Win Rate",    f"{m_base['wr']:.1f}%",             f"{m_slip['wr']:.1f}%",         f"{m_slip['wr'] - m_base['wr']:+.1f}%"),
    ("Profit Factor",f"{m_base['pf']:.3f}",             f"{m_slip['pf']:.3f}",          f"{m_slip['pf'] - m_base['pf']:+.3f}"),
    ("Expectancy",  f"${m_base['expectancy']:+,.2f}",   f"${m_slip['expectancy']:+,.2f}",f"${m_slip['expectancy'] - m_base['expectancy']:+,.2f}"),
    ("Total PnL",   f"${m_base['total_pnl']:+,.0f}",    f"${m_slip['total_pnl']:+,.0f}", f"${m_slip['total_pnl'] - m_base['total_pnl']:+,.0f}"),
    ("Retorno %",   f"{m_base['ret_pct']:+.1f}%",       f"{m_slip['ret_pct']:+.1f}%",   f"{m_slip['ret_pct'] - m_base['ret_pct']:+.1f}%"),
    ("Max DD",      f"{m_base['max_dd']:.2f}%",         f"{m_slip['max_dd']:.2f}%",     f"{m_slip['max_dd'] - m_base['max_dd']:+.2f}%"),
    ("Sharpe",      f"{m_base['sharpe']:.2f}",          f"{m_slip['sharpe']:.2f}",      f"{m_slip['sharpe'] - m_base['sharpe']:+.2f}"),
    ("Avg Win",     f"${m_base['avg_win']:+,.2f}",      f"${m_slip['avg_win']:+,.2f}",  f"${m_slip['avg_win'] - m_base['avg_win']:+,.2f}"),
    ("Avg Loss",    f"${m_base['avg_loss']:+,.2f}",     f"${m_slip['avg_loss']:+,.2f}", f"${m_slip['avg_loss'] - m_base['avg_loss']:+,.2f}"),
]

print(f"  {'Metrica':<18} {'Sin Slippage':>16} {'Con Slippage':>16} {'Diferencia':>16}")
print(f"  {'-'*18} {'-'*16} {'-'*16} {'-'*16}")
for label, v1, v2, diff in rows:
    print(f"  {label:<18} {v1:>16} {v2:>16} {diff:>16}")

print("=" * 72)
print(f"\n  Costos totales estimados: ${m_base['total_pnl'] - m_slip['total_pnl']:,.0f}")
print(f"  Costo promedio por trade: ${(m_base['total_pnl'] - m_slip['total_pnl']) / m_slip['trades']:,.2f}")

# ----------------------------------------------------------------
# 5. Breakdown por trimestre (con slippage)
# ----------------------------------------------------------------
print("\n")
print("=" * 82)
print("  BREAKDOWN TRIMESTRAL — CON SLIPPAGE (slippage=2 + spread=2)")
print("=" * 82)

tdf = results["con_slippage"]["trades_df"].copy()
tdf["quarter"] = tdf["entry_time"].dt.to_period("Q")

q_groups = tdf.groupby("quarter")

print(f"  {'Trimestre':<12} {'Trades':>8} {'WR%':>8} {'PF':>7} {'PnL $':>12} {'Retorno':>10} {'MaxDD':>8}")
print(f"  {'-'*12} {'-'*8} {'-'*8} {'-'*7} {'-'*12} {'-'*10} {'-'*8}")

for q, g in q_groups:
    n_q  = len(g)
    w_q  = g[g["pnl_usd"] > 0]
    l_q  = g[g["pnl_usd"] < 0]
    wr_q = len(w_q) / n_q * 100 if n_q > 0 else 0
    pf_q = w_q["pnl_usd"].sum() / abs(l_q["pnl_usd"].sum()) if len(l_q) > 0 and l_q["pnl_usd"].sum() != 0 else 999

    pnl_q = g["pnl_usd"].sum()
    # Balance al inicio del trimestre (balance_post del trade anterior)
    # Aproximacion: usar initial_balance + PnL acumulado hasta este trimestre
    bal_start_idx = tdf.index[tdf["quarter"] == q][0]
    if bal_start_idx == 0:
        bal_start = LONDON_PARAMS["initial_balance"]
    else:
        bal_start = tdf.loc[bal_start_idx - 1, "balance_post"]
    ret_q = pnl_q / bal_start * 100

    # Max DD del trimestre
    dd_q = g["dd_pct"].max()

    marker = " <-- MEJOR" if pf_q == max(q_groups.apply(lambda x: x[x["pnl_usd"] > 0]["pnl_usd"].sum() / abs(x[x["pnl_usd"] < 0]["pnl_usd"].sum()) if len(x[x["pnl_usd"] < 0]) > 0 else 999).values) else ""
    print(f"  {str(q):<12} {n_q:>8} {wr_q:>7.1f}% {pf_q:>7.2f} {pnl_q:>+12,.0f} {ret_q:>+9.1f}% {dd_q:>7.2f}%{marker}")

print("=" * 82)

# Guardar resultados con slippage
OUT_DIR = Path("strategies/order_block_london/backtest/results")
OUT_DIR.mkdir(parents=True, exist_ok=True)

tdf_export = results["con_slippage"]["trades_df"]
tdf_export.to_csv(OUT_DIR / "trades.csv", index=False)

# Equity curve con slippage
eq = results["con_slippage"]["bt"]._equity_curve
eq_df = pd.DataFrame(eq, columns=["timestamp", "balance"])
running_peak = LONDON_PARAMS["initial_balance"]
dd_vals = []
for _, row in eq_df.iterrows():
    if row["balance"] > running_peak:
        running_peak = row["balance"]
    dd_vals.append(round((running_peak - row["balance"]) / running_peak * 100, 4))
eq_df["drawdown_pct"] = dd_vals
eq_df.to_csv(OUT_DIR / "equity.csv", index=False)

print(f"\n  Archivos actualizados con slippage:")
print(f"    trades.csv  — {len(tdf_export)} trades")
print(f"    equity.csv  — {len(eq_df):,} puntos")
print(f"\n  RESULTADO FINAL con costos completos (spread=2 + slip=2):")
print(f"    WR={m_slip['wr']:.1f}% | PF={m_slip['pf']:.3f} | Retorno={m_slip['ret_pct']:+.1f}% | DD={m_slip['max_dd']:.1f}%")
