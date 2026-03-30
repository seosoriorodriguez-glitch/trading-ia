# -*- coding: utf-8 -*-
"""
Analisis avanzado de backtest:
  1. Monte Carlo (1000 simulaciones)
  2. Por condicion de mercado (ADX tendencial vs lateral, ATR volatilidad)
  Siempre comparando contra baseline real.
"""
import numpy as np
import pandas as pd
from pathlib import Path

TRADES_FILE = "strategies/order_block/backtest/results/ob_bos_live_99d.csv"
M5_FILE     = "data/US30_cash_M5_260d.csv"
INITIAL_BAL = 100_000.0
N_SIMS      = 1000

# ============================================================
# CARGA
# ============================================================
df     = pd.read_csv(TRADES_FILE)
df_m5  = pd.read_csv(M5_FILE)
df_m5["time"] = pd.to_datetime(df_m5["time"])
df["entry_time"] = pd.to_datetime(df["entry_time"])

pnl = df["pnl_usd"].values
n   = len(pnl)

wr       = (pnl > 0).mean()
avg_win  = pnl[pnl > 0].mean()
avg_loss = pnl[pnl < 0].mean()
baseline_ret  = (df["balance"].iloc[-1] - INITIAL_BAL) / INITIAL_BAL * 100
baseline_dd   = 0.0
peak = INITIAL_BAL
for b in df["balance"]:
    if b > peak: peak = b
    dd = (peak - b) / peak * 100
    if dd > baseline_dd: baseline_dd = dd

print("=" * 58)
print("  BASELINE REAL (98 trades, 101 dias)")
print("=" * 58)
print(f"  Win Rate:        {wr:.1%}")
print(f"  Avg Win:         ${avg_win:,.0f}")
print(f"  Avg Loss:        ${avg_loss:,.0f}")
print(f"  Total Return:    {baseline_ret:+.2f}%")
print(f"  Max Drawdown:    {baseline_dd:.2f}%")
print()

# ============================================================
# 1. MONTE CARLO
# ============================================================
print("=" * 58)
print("  MONTE CARLO (1,000 simulaciones)")
print("=" * 58)

returns  = []
max_dds  = []
ruin     = 0   # DD > 9.5% (limite FTMO con buffer)

for _ in range(N_SIMS):
    shuffled = np.random.choice(pnl, size=n, replace=True)
    bal  = INITIAL_BAL
    peak = INITIAL_BAL
    mdd  = 0.0
    for p in shuffled:
        bal  += p
        if bal > peak: peak = bal
        dd = (peak - bal) / peak * 100
        if dd > mdd: mdd = dd
    final_ret = (bal - INITIAL_BAL) / INITIAL_BAL * 100
    returns.append(final_ret)
    max_dds.append(mdd)
    if mdd >= 9.5:
        ruin += 1

returns = np.array(returns)
max_dds = np.array(max_dds)

print(f"  Retorno mediano:    {np.median(returns):+.2f}%")
print(f"  Retorno p10 (malo): {np.percentile(returns, 10):+.2f}%")
print(f"  Retorno p90 (bueno):{np.percentile(returns, 90):+.2f}%")
print(f"  DD mediano:         {np.median(max_dds):.2f}%")
print(f"  DD p90 (peor caso): {np.percentile(max_dds, 90):.2f}%")
print(f"  DD p95:             {np.percentile(max_dds, 95):.2f}%")
print(f"  Riesgo ruina FTMO:  {ruin/N_SIMS:.1%}  (DD>=9.5%)")
print(f"  Prob retorno > 0:   {(returns > 0).mean():.1%}")
print(f"  Prob retorno >10%:  {(returns > 10).mean():.1%}")
print()

# ============================================================
# 2. CONDICION DE MERCADO
# ============================================================
print("=" * 58)
print("  CONDICION DE MERCADO")
print("=" * 58)

# ATR 14 en M5
df_m5["tr"] = np.maximum(
    df_m5["high"] - df_m5["low"],
    np.maximum(
        abs(df_m5["high"] - df_m5["close"].shift(1)),
        abs(df_m5["low"]  - df_m5["close"].shift(1))
    )
)
df_m5["atr14"] = df_m5["tr"].rolling(14).mean()

# ADX 14 simplificado
df_m5["up"]   = df_m5["high"] - df_m5["high"].shift(1)
df_m5["down"] = df_m5["low"].shift(1) - df_m5["low"]
df_m5["pdm"]  = np.where((df_m5["up"] > df_m5["down"]) & (df_m5["up"] > 0), df_m5["up"], 0)
df_m5["ndm"]  = np.where((df_m5["down"] > df_m5["up"]) & (df_m5["down"] > 0), df_m5["down"], 0)
df_m5["pdi"]  = (df_m5["pdm"].rolling(14).mean() / df_m5["atr14"]) * 100
df_m5["ndi"]  = (df_m5["ndm"].rolling(14).mean() / df_m5["atr14"]) * 100
df_m5["dx"]   = (abs(df_m5["pdi"] - df_m5["ndi"]) / (df_m5["pdi"] + df_m5["ndi"])) * 100
df_m5["adx"]  = df_m5["dx"].rolling(14).mean()

atr_median = df_m5["atr14"].median()

# Merge por tiempo mas cercano
df_m5_idx = df_m5.set_index("time").sort_index()

def get_market_cond(entry_time):
    idx = df_m5_idx.index.searchsorted(entry_time)
    if idx == 0 or idx >= len(df_m5_idx):
        return None, None
    row = df_m5_idx.iloc[idx - 1]
    return row.get("adx", None), row.get("atr14", None)

adx_vals = []
atr_vals = []
for et in df["entry_time"]:
    adx, atr = get_market_cond(et)
    adx_vals.append(adx)
    atr_vals.append(atr)

df["adx"] = adx_vals
df["atr"] = atr_vals
df = df.dropna(subset=["adx", "atr"])

adx_median = df["adx"].median()
atr_med    = df["atr"].median()

# --- ADX: Tendencial vs Lateral ---
trend   = df[df["adx"] >= adx_median]
lateral = df[df["adx"] <  adx_median]

print(f"  ADX mediano en trades: {adx_median:.1f}")
print()
print(f"  TENDENCIAL (ADX >= {adx_median:.0f})  — {len(trend)} trades:")
if len(trend) > 0:
    wr_t  = (trend["pnl_usd"] > 0).mean()
    ret_t = trend["pnl_usd"].sum() / INITIAL_BAL * 100
    print(f"    Win Rate:   {wr_t:.1%}")
    print(f"    PnL total:  {ret_t:+.2f}%")
    print(f"    Avg PnL:    ${trend['pnl_usd'].mean():,.0f}")
print()
print(f"  LATERAL (ADX < {adx_median:.0f})  — {len(lateral)} trades:")
if len(lateral) > 0:
    wr_l  = (lateral["pnl_usd"] > 0).mean()
    ret_l = lateral["pnl_usd"].sum() / INITIAL_BAL * 100
    print(f"    Win Rate:   {wr_l:.1%}")
    print(f"    PnL total:  {ret_l:+.2f}%")
    print(f"    Avg PnL:    ${lateral['pnl_usd'].mean():,.0f}")

print()
# --- ATR: Alta vs Baja volatilidad ---
high_vol = df[df["atr"] >= atr_med]
low_vol  = df[df["atr"] <  atr_med]

print(f"  ATR mediano en trades: {atr_med:.1f} pts")
print()
print(f"  ALTA VOLATILIDAD (ATR >= {atr_med:.0f})  — {len(high_vol)} trades:")
if len(high_vol) > 0:
    wr_hv  = (high_vol["pnl_usd"] > 0).mean()
    ret_hv = high_vol["pnl_usd"].sum() / INITIAL_BAL * 100
    print(f"    Win Rate:   {wr_hv:.1%}")
    print(f"    PnL total:  {ret_hv:+.2f}%")
    print(f"    Avg PnL:    ${high_vol['pnl_usd'].mean():,.0f}")
print()
print(f"  BAJA VOLATILIDAD (ATR < {atr_med:.0f})  — {len(low_vol)} trades:")
if len(low_vol) > 0:
    wr_lv  = (low_vol["pnl_usd"] > 0).mean()
    ret_lv = low_vol["pnl_usd"].sum() / INITIAL_BAL * 100
    print(f"    Win Rate:   {wr_lv:.1%}")
    print(f"    PnL total:  {ret_lv:+.2f}%")
    print(f"    Avg PnL:    ${low_vol['pnl_usd'].mean():,.0f}")

print()
# --- Por hora NY ---
print("  POR HORA (UTC):")
df["hour"] = df["entry_time"].dt.hour
for h in sorted(df["hour"].unique()):
    grp = df[df["hour"] == h]
    wr_h = (grp["pnl_usd"] > 0).mean()
    pnl_h = grp["pnl_usd"].sum()
    print(f"    {h:02d}:00  {len(grp):3d} trades  WR {wr_h:.0%}  PnL ${pnl_h:+,.0f}")

print()
print("=" * 58)
