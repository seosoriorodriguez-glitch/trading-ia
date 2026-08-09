# -*- coding: utf-8 -*-
"""Prueba el modo REARM (cancelar al llenar + re-poner al cerrar) vs A vs C. 40d rapido."""
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

BASE = {"max_active_fvgs": 3, "min_zone_points": 5, "avg_spread_points": 4,
        "close_before_weekend": True, "weekend_close_hour": 19}


def max_concurrent(df):
    if df.empty: return 0
    m = 0
    for _, r in df.iterrows():
        c = ((df.entry_time < r.exit_time) & (df.exit_time > r.entry_time)).sum()
        m = max(m, c)
    return m


def run(name, extra):
    p = copy.deepcopy(US30_PARAMS); p.update(BASE); p.update(extra)
    bt = FVGBacktester(p); df = bt.run(dfh, dfl)
    if df.empty: return dict(name=name, n=0, wr=0, pf=0, sumr=0, mc=0)
    w = df[df.pnl_usd > 0]; n = len(df); wr = len(w)/n*100
    gl = abs(df[df.pnl_usd <= 0].pnl_usd.sum()); pf = w.pnl_usd.sum()/gl if gl > 0 else 99
    return dict(name=name, n=n, wr=wr, pf=pf, sumr=df.pnl_r.sum(), mc=max_concurrent(df))


configs = [
    ("A (max 1, live)",        {"max_simultaneous_trades": 1, "cap_pending_at_max": True}),
    ("REARM (nueva idea)",     {"max_simultaneous_trades": 1, "cancel_pending_on_fill": True,
                                "rearm_pendings": True}),
    ("C ref (techo, no live)", {"max_simultaneous_trades": 1}),
]
res = [run(n, e) for n, e in configs]
print("\n" + "=" * 68)
print(f"  FVG REARM test — {DIAS}d (max_active 3, zona 5, spread 4)")
print("=" * 68)
print(f"  {'Config':<24}{'Trades':>7}{'WR':>7}{'PF':>7}{'SumaR':>9}{'MaxAbiertas':>12}")
for m in res:
    print(f"  {m['name']:<24}{m['n']:>7}{m['wr']:>6.1f}%{m['pf']:>7.2f}{m['sumr']:>+8.0f}R{m['mc']:>12}")
print("=" * 68)
print("  MaxAbiertas debe ser 1 en A y REARM (seguro). C ref puede ser >1 (no live).")
