# -*- coding: utf-8 -*-
"""
Config F (baseline + cierre finde + spread 4 real): retorno CON vs SIN compounding.
Sin compounding = riesgo fijo por trade -> retorno lineal = sum(R) * risk_pct.
"""
import sys, copy
from pathlib import Path
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd
from strategies.fair_value_gap.backtest.config import US30_PARAMS
from strategies.fair_value_gap.backtest.data_loader import load_csv
from strategies.fair_value_gap.backtest.backtester import FVGBacktester

dfh = load_csv("data/US30_icm_M5_518d.csv")
dfl = load_csv("data/US30_icm_M1_500k.csv")

p = copy.deepcopy(US30_PARAMS)
p.update({"close_before_weekend": True, "weekend_close_hour": 19, "avg_spread_points": 4})
bt = FVGBacktester(p)
print("Corriendo config F (spread 4 real)...", flush=True)
df = bt.run(dfh, dfl)

n = len(df)
sum_r = df.pnl_r.sum()
avg_r = df.pnl_r.mean()
wins = (df.pnl_usd > 0).sum()
comp_ret = (bt.balance - bt.initial_balance) / bt.initial_balance * 100

# Max DD sin compounding (curva lineal en R)
cum = df.pnl_r.cumsum()
peak = cum.cummax()
dd_r = (peak - cum).max()

print("\n" + "=" * 60)
print("  FVG config F — CON vs SIN compounding (518d, spread 4)")
print("=" * 60)
print(f"  Trades: {n} | WR: {wins/n*100:.1f}% | Avg R/trade: {avg_r:+.3f}")
print(f"  Suma total de R: {sum_r:+.1f}R")
print("-" * 60)
print(f"  CON compounding:   {comp_ret:+.0f}%")
print("-" * 60)
print("  SIN compounding (riesgo fijo, retorno lineal):")
for rp in (0.005, 0.0025):
    ret = sum_r * rp * 100
    usd200 = sum_r * (200000 * rp)
    dd_usd = dd_r * (200000 * rp)
    print(f"    riesgo {rp*100:.2f}%: retorno {ret:+.0f}%  |  ${usd200:+,.0f} en $200k  |  maxDD ~${dd_usd:,.0f}")
print("=" * 60)
