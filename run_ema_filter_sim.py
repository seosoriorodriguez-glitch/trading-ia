# -*- coding: utf-8 -*-
"""
Grid de filtro EMA 4H sobre backtest +173.9% (spread=2, sin slippage).
Prueba EMA periods: 20, 35, 50, 70, 100, 200
Filtro: LONG solo en bullish | SHORT solo en bearish

SOLO ANALISIS — no modifica bots live.
Uso: python run_ema_filter_sim.py
"""
import sys, copy
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")

sys.path.insert(0, '.')

import pandas as pd
import numpy as np
import bisect
from strategies.order_block_london.backtest.config import LONDON_PARAMS
from strategies.order_block.backtest.data_loader import load_csv
from strategies.order_block.backtest.backtester_limit_orders import OrderBlockBacktesterLimitOrders

EMA_PERIODS = [20, 35, 50, 70, 100, 200]
INIT_BAL    = 10_000.0

# ----------------------------------------------------------------
# 1. Backtest base una sola vez (spread=2, slippage=0)
# ----------------------------------------------------------------
print("Cargando datos y corriendo backtest base...")
df_m5 = load_csv("data/US30_icm_M5_518d.csv")
df_m1 = load_csv("data/US30_icm_M1_500k.csv")

params = copy.deepcopy(LONDON_PARAMS)
params["slippage_points"]   = 0
params["avg_spread_points"] = 2

bt = OrderBlockBacktesterLimitOrders(params)
trades = bt.run(df_m5, df_m1)
print(f"  {len(trades)} trades | periodo: {trades['entry_time'].min().date()} -> {trades['entry_time'].max().date()}")

# ----------------------------------------------------------------
# 2. Pre-calcular 4H OHLC (sin EMA aun, la calculamos por periodo)
# ----------------------------------------------------------------
df_4h_base = (df_m5.set_index("time")
                    .resample("4h")
                    .agg({"open":"first","high":"max","low":"min","close":"last"})
                    .dropna()
                    .reset_index())
h4_close = df_4h_base["close"].tolist()
h4_times = df_4h_base["time"].tolist()

# ----------------------------------------------------------------
# 3. Metricas
# ----------------------------------------------------------------
def calc_metrics(df):
    if df.empty: return {}
    running = INIT_BAL; peak = INIT_BAL; dd_list = []
    for _, r in df.iterrows():
        running += r["pnl_usd"]
        if running > peak: peak = running
        dd_list.append((peak - running) / peak * 100)
    w = df[df["pnl_usd"] > 0]; l = df[df["pnl_usd"] < 0]; n = len(df)
    pf    = w["pnl_usd"].sum() / abs(l["pnl_usd"].sum()) if len(l) > 0 else 999
    total = df["pnl_usd"].sum()
    daily = df.groupby(df["entry_time"].dt.date)["pnl_usd"].sum()
    sharpe = (daily.mean() / daily.std() * np.sqrt(252)) if daily.std() > 0 else 0
    return dict(n=n, wr=len(w)/n*100, pf=pf, total=total,
                ret=total/INIT_BAL*100, exp=total/n, maxdd=max(dd_list), sharpe=sharpe)

# Base sin filtro
m_base = calc_metrics(trades)

# ----------------------------------------------------------------
# 4. Grid sobre EMA periods
# ----------------------------------------------------------------
print(f"\nProbando EMA periods: {EMA_PERIODS}")
grid_results = {}

for period in EMA_PERIODS:
    # Calcular EMA para este periodo
    df_4h = df_4h_base.copy()
    df_4h["ema"] = df_4h["close"].ewm(span=period, adjust=False).mean()
    h4_ema = df_4h["ema"].tolist()

    # Clasificar trades
    regimes = []
    for _, row in trades.iterrows():
        idx = bisect.bisect_left(h4_times, row["entry_time"]) - 1
        if idx < period:
            regimes.append("unknown")
            continue
        regime = "bullish" if h4_close[idx] > h4_ema[idx] else "bearish"
        regimes.append(regime)

    t = trades.copy()
    t["regime"] = regimes
    t_known = t[t["regime"] != "unknown"].copy()
    t_known["with_trend"] = (
        ((t_known["regime"] == "bullish") & (t_known["direction"] == "long")) |
        ((t_known["regime"] == "bearish") & (t_known["direction"] == "short"))
    )

    m_filt  = calc_metrics(t_known[t_known["with_trend"]])
    m_count = calc_metrics(t_known[~t_known["with_trend"]])
    grid_results[period] = {"filt": m_filt, "count": m_count, "all": calc_metrics(t_known)}
    print(f"  EMA({period:>3}): filtrado={m_filt['n']} trades | PF={m_filt['pf']:.3f} | Ret={m_filt['ret']:+.1f}% | DD={m_filt['maxdd']:.1f}%")

# ----------------------------------------------------------------
# 5. Tabla resumen comparativa
# ----------------------------------------------------------------
print(f"\n")
print("=" * 90)
print("  GRID EMA FILTER — comparacion de periodos (spread=2, sin slippage)")
print("  Filtro: LONG en bullish | SHORT en bearish")
print("=" * 90)
print(f"  {'EMA':>6} {'Trades':>8} {'WR%':>7} {'PF':>7} {'Retorno':>9} {'MaxDD':>8} {'Sharpe':>8} {'Exp$':>8} {'DeltaRet':>10} {'DeltaPF':>9}")
print(f"  {'-'*6} {'-'*8} {'-'*7} {'-'*7} {'-'*9} {'-'*8} {'-'*8} {'-'*8} {'-'*10} {'-'*9}")

# Fila base
print(f"  {'BASE':>6} {m_base['n']:>8} {m_base['wr']:>6.1f}% {m_base['pf']:>7.3f} {m_base['ret']:>+8.1f}% {m_base['maxdd']:>7.2f}% {m_base['sharpe']:>8.2f} {m_base['exp']:>+7.2f} {'---':>10} {'---':>9}")

best_pf  = max(grid_results[p]["filt"]["pf"]  for p in EMA_PERIODS)
best_ret = max(grid_results[p]["filt"]["ret"]  for p in EMA_PERIODS)

for period in EMA_PERIODS:
    m = grid_results[period]["filt"]
    delta_ret = m["ret"] - m_base["ret"]
    delta_pf  = m["pf"]  - m_base["pf"]
    marker = " <-- MEJOR PF" if m["pf"] == best_pf else (" <-- MEJOR RET" if m["ret"] == best_ret else "")
    print(f"  {period:>6} {m['n']:>8} {m['wr']:>6.1f}% {m['pf']:>7.3f} {m['ret']:>+8.1f}% {m['maxdd']:>7.2f}% {m['sharpe']:>8.2f} {m['exp']:>+7.2f} {delta_ret:>+9.1f}% {delta_pf:>+8.3f}{marker}")

print("=" * 90)

# ----------------------------------------------------------------
# 6. Detalle del mejor periodo (mayor PF filtrado)
# ----------------------------------------------------------------
best_period = max(EMA_PERIODS, key=lambda p: grid_results[p]["filt"]["pf"])
print(f"\n  Mejor periodo por PF: EMA({best_period})")

# Reconstruir trades clasificados para el mejor periodo
df_4h_best = df_4h_base.copy()
df_4h_best["ema"] = df_4h_best["close"].ewm(span=best_period, adjust=False).mean()
h4_ema_best = df_4h_best["ema"].tolist()

regimes_best = []
for _, row in trades.iterrows():
    idx = bisect.bisect_left(h4_times, row["entry_time"]) - 1
    if idx < best_period:
        regimes_best.append("unknown")
        continue
    regime = "bullish" if h4_close[idx] > h4_ema_best[idx] else "bearish"
    regimes_best.append(regime)

t_best = trades.copy()
t_best["regime"] = regimes_best
t_best = t_best[t_best["regime"] != "unknown"].copy()
t_best["with_trend"] = (
    ((t_best["regime"] == "bullish") & (t_best["direction"] == "long")) |
    ((t_best["regime"] == "bearish") & (t_best["direction"] == "short"))
)
t_filt = t_best[t_best["with_trend"]]

print(f"\n")
print("=" * 72)
print(f"  DETALLE EMA({best_period}) — Regimen x Direccion")
print("=" * 72)
print(f"  {'Combinacion':<28} {'Trades':>8} {'WR%':>7} {'PF':>8} {'PnL $':>11} {'Exp $':>9}")
print(f"  {'-'*28} {'-'*8} {'-'*7} {'-'*8} {'-'*11} {'-'*9}")
for regime in ["bullish", "bearish"]:
    for direction in ["long", "short"]:
        sub = t_best[(t_best["regime"]==regime) & (t_best["direction"]==direction)]
        if len(sub) == 0: continue
        m = calc_metrics(sub)
        tag = " ✓" if (regime=="bullish" and direction=="long") or (regime=="bearish" and direction=="short") else " ✗"
        print(f"  {regime.upper()+' + '+direction.upper():<28} {m['n']:>8} {m['wr']:>6.1f}% {m['pf']:>8.3f} {m['total']:>+11,.0f} {m['exp']:>+9.2f}{tag}")

# Trimestral para mejor periodo
print(f"\n")
print("=" * 80)
print(f"  TRIMESTRAL EMA({best_period}) — Base vs Filtrado")
print("=" * 80)
print(f"  {'Trim':<10} {'B.Trades':>9} {'B.PF':>7} {'B.Ret':>8} | {'F.Trades':>9} {'F.PF':>7} {'F.Ret':>8} {'F.DD':>8}")
print(f"  {'-'*10} {'-'*9} {'-'*7} {'-'*8}   {'-'*9} {'-'*7} {'-'*8} {'-'*8}")
t_best["quarter"] = t_best["entry_time"].dt.to_period("Q")
t_filt2 = t_best[t_best["with_trend"]].copy()
t_filt2["quarter"] = t_filt2["entry_time"].dt.to_period("Q")
for q in sorted(t_best["quarter"].unique()):
    gb = t_best[t_best["quarter"]==q]
    gf = t_filt2[t_filt2["quarter"]==q] if q in t_filt2["quarter"].values else pd.DataFrame()
    mb = calc_metrics(gb); mf = calc_metrics(gf)
    print(f"  {str(q):<10} {mb['n']:>9} {mb['pf']:>7.3f} {mb['ret']:>+7.1f}%   {mf.get('n',0):>9} {mf.get('pf',0):>7.3f} {mf.get('ret',0):>+7.1f}% {mf.get('maxdd',0):>7.2f}%")

print(f"\n  RECORDATORIO: Analisis 100% in-sample. Validar con live data.")
