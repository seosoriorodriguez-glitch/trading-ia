# -*- coding: utf-8 -*-
"""
Analisis de regimen por EMA 70 en 4H — Bot 2 London.
SOLO ANALISIS — no modifica ningun bot live.

Metodologia:
  - Calcula EMA(70) sobre velas 4H (resampleadas desde M5)
  - Clasifica cada trade segun si el precio de entrada estaba
    por encima (BULLISH) o por debajo (BEARISH) de la EMA 4H
  - Compara metricas entre ambos regimenes

Uso: python run_regime_ema_analysis.py
"""
import sys
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")

sys.path.insert(0, '.')

import pandas as pd
import numpy as np
from pathlib import Path
from strategies.order_block.backtest.data_loader import load_csv

EMA_PERIOD = 70
TRADES_CSV = Path("strategies/order_block_london/backtest/results/trades.csv")

print("=" * 65)
print("  ANALISIS REGIMEN EMA(70) 4H — Bot 2 London (SOLO ANALISIS)")
print("=" * 65)

# ----------------------------------------------------------------
# 1. Cargar datos
# ----------------------------------------------------------------
print("\nCargando datos...")
df_m5  = load_csv("data/US30_icm_M5_518d.csv")
trades = pd.read_csv(TRADES_CSV, parse_dates=["entry_time", "exit_time"])
print(f"  M5: {len(df_m5):,} velas | Trades: {len(trades)}")

# ----------------------------------------------------------------
# 2. Calcular EMA(70) en 4H desde M5
# ----------------------------------------------------------------
df_4h = (df_m5
         .set_index("time")
         .resample("4h")
         .agg({"open": "first", "high": "max", "low": "min", "close": "last"})
         .dropna()
         .reset_index())

df_4h["ema70"] = df_4h["close"].ewm(span=EMA_PERIOD, adjust=False).mean()

print(f"  4H velas: {len(df_4h):,} | EMA({EMA_PERIOD}) calculada")

# ----------------------------------------------------------------
# 3. Clasificar cada trade segun regimen
# ----------------------------------------------------------------
# Para cada trade, buscar la ultima vela 4H cerrada antes de entry_time
df_4h_times = df_4h["time"].tolist()
df_4h_ema   = df_4h["ema70"].tolist()
df_4h_close = df_4h["close"].tolist()

import bisect

regimes    = []
ema_values = []
h4_closes  = []

for _, row in trades.iterrows():
    entry_t = row["entry_time"]
    idx = bisect.bisect_left(df_4h_times, entry_t) - 1
    if idx < EMA_PERIOD:  # no hay suficiente historia para la EMA
        regimes.append("unknown")
        ema_values.append(np.nan)
        h4_closes.append(np.nan)
        continue
    ema_val   = df_4h_ema[idx]
    close_val = df_4h_close[idx]
    regimes.append("bullish" if close_val > ema_val else "bearish")
    ema_values.append(round(ema_val, 1))
    h4_closes.append(round(close_val, 1))

trades["regime"]    = regimes
trades["ema70_4h"]  = ema_values
trades["h4_close"]  = h4_closes

known = trades[trades["regime"] != "unknown"]
print(f"\n  Trades clasificados: {len(known)} ({len(trades)-len(known)} sin historia EMA suficiente)")
print(f"  Bullish: {(known['regime']=='bullish').sum()} trades")
print(f"  Bearish: {(known['regime']=='bearish').sum()} trades")

# ----------------------------------------------------------------
# 4. Metricas por regimen
# ----------------------------------------------------------------
def metrics(sub):
    if len(sub) == 0:
        return {}
    w = sub[sub["pnl_usd"] > 0]
    l = sub[sub["pnl_usd"] < 0]
    n = len(sub)
    pf  = w["pnl_usd"].sum() / abs(l["pnl_usd"].sum()) if len(l) > 0 else 999
    return dict(
        n=n, wr=len(w)/n*100, pf=pf,
        total=sub["pnl_usd"].sum(),
        exp=sub["pnl_usd"].mean(),
        avg_win=w["pnl_usd"].mean() if len(w)>0 else 0,
        avg_loss=l["pnl_usd"].mean() if len(l)>0 else 0,
    )

bull = known[known["regime"] == "bullish"]
bear = known[known["regime"] == "bearish"]
m_all  = metrics(known)
m_bull = metrics(bull)
m_bear = metrics(bear)

print(f"\n")
print("=" * 72)
print(f"  METRICAS POR REGIMEN EMA(70) 4H")
print("=" * 72)
print(f"  {'Metrica':<20} {'TOTAL':>12} {'BULLISH':>12} {'BEARISH':>12}")
print(f"  {'-'*20} {'-'*12} {'-'*12} {'-'*12}")
print(f"  {'Trades':<20} {m_all['n']:>12} {m_bull['n']:>12} {m_bear['n']:>12}")
print(f"  {'Win Rate':<20} {m_all['wr']:>11.1f}% {m_bull['wr']:>11.1f}% {m_bear['wr']:>11.1f}%")
print(f"  {'Profit Factor':<20} {m_all['pf']:>12.3f} {m_bull['pf']:>12.3f} {m_bear['pf']:>12.3f}")
print(f"  {'Total PnL':<20} ${m_all['total']:>+10,.0f} ${m_bull['total']:>+10,.0f} ${m_bear['total']:>+10,.0f}")
print(f"  {'Expectancy':<20} ${m_all['exp']:>+10.2f} ${m_bull['exp']:>+10.2f} ${m_bear['exp']:>+10.2f}")
print(f"  {'Avg Win':<20} ${m_all['avg_win']:>+10.2f} ${m_bull['avg_win']:>+10.2f} ${m_bear['avg_win']:>+10.2f}")
print(f"  {'Avg Loss':<20} ${m_all['avg_loss']:>+10.2f} ${m_bull['avg_loss']:>+10.2f} ${m_bear['avg_loss']:>+10.2f}")
print("=" * 72)

# ----------------------------------------------------------------
# 5. Breakdown por direccion de trade dentro de cada regimen
# ----------------------------------------------------------------
print(f"\n  LONG vs SHORT por regimen:")
print(f"  {'':30} {'Trades':>8} {'WR%':>8} {'PF':>8} {'PnL $':>10}")
print(f"  {'-'*30} {'-'*8} {'-'*8} {'-'*8} {'-'*10}")

for regime_label, subset in [("BULLISH", bull), ("BEARISH", bear)]:
    for direction in ["long", "short"]:
        col = "direction" if "direction" in subset.columns else "tipo"
        val = direction if "direction" in subset.columns else direction.upper()
        sub = subset[subset[col] == val]
        if len(sub) == 0:
            continue
        m = metrics(sub)
        label = f"  {regime_label} + {direction.upper()}"
        print(f"  {label:<30} {m['n']:>8} {m['wr']:>7.1f}% {m['pf']:>8.3f} {m['total']:>+10,.0f}")

# ----------------------------------------------------------------
# 6. Evolucion trimestral del regimen
# ----------------------------------------------------------------
print(f"\n")
print("=" * 80)
print(f"  TRIMESTRAL: distribucion de regimen y PF")
print("=" * 80)
print(f"  {'Trimestre':<12} {'Bull%':>7} {'Bear%':>7} {'PF Bull':>9} {'PF Bear':>9} {'PF Total':>9}")
print(f"  {'-'*12} {'-'*7} {'-'*7} {'-'*9} {'-'*9} {'-'*9}")

known["quarter"] = known["entry_time"].dt.to_period("Q")
for q, g in known.groupby("quarter"):
    gb = g[g["regime"]=="bullish"]
    gr = g[g["regime"]=="bearish"]
    mb = metrics(gb)
    mr = metrics(gr)
    mt = metrics(g)
    pct_bull = len(gb)/len(g)*100
    pct_bear = len(gr)/len(g)*100
    pf_b = f"{mb['pf']:.3f}" if mb else "-"
    pf_r = f"{mr['pf']:.3f}" if mr else "-"
    print(f"  {str(q):<12} {pct_bull:>6.0f}% {pct_bear:>6.0f}% {pf_b:>9} {pf_r:>9} {mt['pf']:>9.3f}")

# ----------------------------------------------------------------
# 7. Veredicto
# ----------------------------------------------------------------
print(f"\n")
print("=" * 65)
print("  VEREDICTO")
print("=" * 65)

diff_pf = m_bull['pf'] - m_bear['pf']
diff_wr = m_bull['wr'] - m_bear['wr']

print(f"\n  Delta PF  (Bullish - Bearish): {diff_pf:+.3f}")
print(f"  Delta WR  (Bullish - Bearish): {diff_wr:+.1f}%")
print(f"  Delta Exp (Bullish - Bearish): ${m_bull['exp']-m_bear['exp']:+.2f}")

if abs(diff_pf) < 0.05:
    verdict = "SIN DIFERENCIA significativa entre regimenes."
elif m_bull['pf'] > m_bear['pf']:
    if diff_pf > 0.15:
        verdict = f"BULLISH claramente superior (PF {m_bull['pf']:.3f} vs {m_bear['pf']:.3f}). Filtrar trades en regimen bajista podria mejorar el PF."
    else:
        verdict = f"BULLISH levemente superior (PF {m_bull['pf']:.3f} vs {m_bear['pf']:.3f}). Diferencia marginal."
else:
    if diff_pf < -0.15:
        verdict = f"BEARISH claramente superior (PF {m_bear['pf']:.3f} vs {m_bull['pf']:.3f}). Estrategia funciona mejor contra tendencia."
    else:
        verdict = f"BEARISH levemente superior (PF {m_bear['pf']:.3f} vs {m_bull['pf']:.3f}). Diferencia marginal."

print(f"\n  {verdict}")
print(f"\n  RECORDATORIO: Analisis in-sample. Validar con datos live")
print(f"  antes de aplicar cualquier filtro de regimen.")
print("=" * 65)
