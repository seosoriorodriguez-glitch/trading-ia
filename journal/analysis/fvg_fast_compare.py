# -*- coding: utf-8 -*-
"""Compara max_sim 1/2/3 en los ultimos N dias (rapido)."""
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
cutoff = dfl["time"].iloc[-1] - pd.Timedelta(days=DIAS)
dfh = dfh[dfh.time >= cutoff].reset_index(drop=True)
dfl = dfl[dfl.time >= cutoff].reset_index(drop=True)

print(f"FVG ultimos {DIAS}d — comparando max_sim (natural, max_active=3, zona>=5, RR2, spread4)")
print("=" * 58)
print(f"  {'max_sim':<9}{'Trades':>8}{'WR':>7}{'PF':>7}{'SumaR':>9}{'AvgR':>8}")
for ms in (1, 2, 3):
    p = copy.deepcopy(US30_PARAMS)
    p.update({"max_active_fvgs": 3, "max_simultaneous_trades": ms, "min_zone_points": 5,
              "avg_spread_points": 4, "close_before_weekend": True, "weekend_close_hour": 19})
    bt = FVGBacktester(p); df = bt.run(dfh, dfl)
    wins = df[df.pnl_usd > 0]; n = len(df); wr = len(wins)/n*100 if n else 0
    gl = abs(df[df.pnl_usd <= 0].pnl_usd.sum()); pf = wins.pnl_usd.sum()/gl if gl > 0 else 99
    print(f"  {ms:<9}{n:>8}{wr:>6.1f}%{pf:>7.2f}{df.pnl_r.sum():>+8.0f}R{df.pnl_r.mean():>+8.3f}")
print("=" * 58)
