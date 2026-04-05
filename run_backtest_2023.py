# -*- coding: utf-8 -*-
"""
Backtest Bot 2 London sobre datos 2023 (Jun-Dic).
Convierte formato MT5 al vuelo y corre el backtest con LONDON_PARAMS.
TF mayor: M5 2023 | TF menor: M2 2023 (desde junio)
Uso: python run_backtest_2023.py
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
from strategies.order_block.backtest.backtester_limit_orders import OrderBlockBacktesterLimitOrders

# ----------------------------------------------------------------
# Convertir formato MT5 (tab-separado, DATE+TIME separados)
# ----------------------------------------------------------------
def load_mt5_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, sep="\t")
    df.columns = [c.strip("<>").lower() for c in df.columns]
    df["time"] = pd.to_datetime(df["date"] + " " + df["time"])
    df = df[["time", "open", "high", "low", "close"]].copy()
    df = df.sort_values("time").reset_index(drop=True)
    for col in ["open", "high", "low", "close"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna()
    return df

# ----------------------------------------------------------------
# Cargar datos
# ----------------------------------------------------------------
print("Cargando datos 2023...")
df_m5 = load_mt5_csv("data/us30 2023 m5.csv")
df_m2 = load_mt5_csv("data/us30 m2 2023.csv")

# Alinear M5 al rango del M2 (desde junio)
cutoff = df_m2["time"].min()
df_m5  = df_m5[df_m5["time"] >= cutoff].reset_index(drop=True)

print(f"  M5: {len(df_m5):,} velas | {df_m5['time'].min().date()} -> {df_m5['time'].max().date()}")
print(f"  M2: {len(df_m2):,} velas | {df_m2['time'].min().date()} -> {df_m2['time'].max().date()}")

# ----------------------------------------------------------------
# Correr backtest
# ----------------------------------------------------------------
params = copy.deepcopy(LONDON_PARAMS)
print(f"\nCorriendo backtest 2023 con LONDON_PARAMS...")
print(f"  RR={params['target_rr']} | Buffer={params['buffer_points']} | Spread={params['avg_spread_points']} | Slip={params.get('slippage_points',0)}")

bt = OrderBlockBacktesterLimitOrders(params)
trades_df = bt.run(df_m5, df_m2)

# ----------------------------------------------------------------
# Metricas
# ----------------------------------------------------------------
if trades_df.empty:
    print("Sin trades generados.")
else:
    running = params["initial_balance"]
    peak    = params["initial_balance"]
    dd_list = []
    for _, row in trades_df.iterrows():
        running += row["pnl_usd"]
        if running > peak:
            peak = running
        dd_list.append((peak - running) / peak * 100)
    trades_df["dd_pct"] = dd_list

    w = trades_df[trades_df["pnl_usd"] > 0]
    l = trades_df[trades_df["pnl_usd"] < 0]
    n = len(trades_df)
    wr    = len(w) / n * 100
    pf    = w["pnl_usd"].sum() / abs(l["pnl_usd"].sum()) if len(l) > 0 else 999
    total = trades_df["pnl_usd"].sum()
    ret   = total / params["initial_balance"] * 100
    maxdd = trades_df["dd_pct"].max()
    exp   = total / n

    daily = trades_df.groupby(trades_df["entry_time"].dt.date)["pnl_usd"].sum()
    sharpe = (daily.mean() / daily.std() * np.sqrt(252)) if daily.std() > 0 else 0

    print(f"\n{'='*55}")
    print(f"  RESULTADO 2023 (Jun-Dic) — Bot 2 London")
    print(f"{'='*55}")
    print(f"  Trades:     {n}")
    print(f"  Win Rate:   {wr:.1f}%")
    print(f"  PF:         {pf:.3f}")
    print(f"  Expectancy: ${exp:+,.2f}")
    print(f"  Total PnL:  ${total:+,.0f}")
    print(f"  Retorno:    {ret:+.1f}%")
    print(f"  Max DD:     {maxdd:.2f}%")
    print(f"  Sharpe:     {sharpe:.2f}")

    # Breakdown mensual
    trades_df["month"] = trades_df["entry_time"].dt.to_period("M")
    print(f"\n  {'Mes':<10} {'Trades':>8} {'WR%':>8} {'PF':>7} {'PnL $':>10}")
    print(f"  {'-'*10} {'-'*8} {'-'*8} {'-'*7} {'-'*10}")
    for m, g in trades_df.groupby("month"):
        wm = g[g["pnl_usd"] > 0]
        lm = g[g["pnl_usd"] < 0]
        pf_m = wm["pnl_usd"].sum() / abs(lm["pnl_usd"].sum()) if len(lm) > 0 else 999
        print(f"  {str(m):<10} {len(g):>8} {len(wm)/len(g)*100:>7.1f}% {pf_m:>7.3f} {g['pnl_usd'].sum():>+10,.0f}")

    # Comparacion vs backtest 2024-2026
    print(f"\n{'='*55}")
    print(f"  COMPARACION vs BACKTEST PRINCIPAL")
    print(f"{'='*55}")
    print(f"  {'':20} {'2023 (M2)':>12} {'2024-26 (M1)':>14}")
    print(f"  {'Trades/mes':<20} {n/7:>12.0f} {1182/18:>14.0f}")
    print(f"  {'Win Rate':<20} {wr:>11.1f}% {'34.7%':>14}")
    print(f"  {'Profit Factor':<20} {pf:>12.3f} {'1.159':>14}")
    print(f"  {'Max DD':<20} {maxdd:>11.2f}% {'12.46%':>14}")
    print(f"  {'Retorno anualiz.':<20} {ret/7*12:>10.1f}% {'88.4%':>13}%")
    print(f"{'='*55}")
    print(f"\n  NOTA: M2 usado como TF menor (vs M1 en backtest principal).")
    print(f"  Diferencia esperada en timing de entrada: ~1 min.")
