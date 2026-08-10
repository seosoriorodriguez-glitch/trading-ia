# -*- coding: utf-8 -*-
"""Explorar RAPIDO en 40d: efecto del RR sobre PF y DD. Natural max 3, zona 5, spread 4."""
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

DIAS = 40
dfh = load_csv("data/US30_icm_M5_518d.csv"); dfl = load_csv("data/US30_icm_M1_500k.csv")
cut = dfl["time"].iloc[-1] - pd.Timedelta(days=DIAS)
dfh = dfh[dfh.time >= cut].reset_index(drop=True); dfl = dfl[dfl.time >= cut].reset_index(drop=True)

BASE = {"max_active_fvgs": 3, "max_simultaneous_trades": 3, "min_zone_points": 5,
        "avg_spread_points": 4, "close_before_weekend": True, "weekend_close_hour": 19}

print(f"FVG 40d — efecto del RR (natural 3, zona 5, spread 4)")
print("=" * 64)
print(f"  {'RR':<6}{'Trades':>7}{'WR':>7}{'PF':>7}{'SumaR':>8}{'MaxDD_R':>9}{'DD% (0.5%)':>12}")
for rr in (2.0, 2.5, 3.0, 3.5, 4.0, 5.0):
    p = copy.deepcopy(US30_PARAMS); p.update(BASE); p["target_rr"] = rr
    bt = FVGBacktester(p); df = bt.run(dfh, dfl)
    if df.empty:
        print(f"  {rr:<6}  sin trades"); continue
    w = df[df.pnl_usd > 0]; n = len(df); wr = len(w)/n*100
    gl = abs(df[df.pnl_usd <= 0].pnl_usd.sum()); pf = w.pnl_usd.sum()/gl if gl > 0 else 99
    cum = df.pnl_r.cumsum(); mddr = (cum.cummax() - cum).max()
    print(f"  {rr:<6}{n:>7}{wr:>6.1f}%{pf:>7.2f}{df.pnl_r.sum():>+7.0f}R{mddr:>+8.0f}R{mddr*0.5:>11.1f}%")
print("=" * 64)
