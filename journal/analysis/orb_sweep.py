# -*- coding: utf-8 -*-
"""Optimizar ORB: sweep de RR y duracion del rango. 518d M5 (rapido)."""
import sys, copy
from pathlib import Path
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import pandas as pd
from strategies.opening_range_breakout.backtest.config import ORB_PARAMS
from strategies.opening_range_breakout.backtest.backtester import ORBBacktester
from strategies.fair_value_gap.backtest.data_loader import load_csv

dfm5 = load_csv("data/US30_icm_M5_518d.csv")


def pf_of(df):
    gp = df[df.pnl_r > 0].pnl_r.sum(); gl = abs(df[df.pnl_r <= 0].pnl_r.sum())
    return gp / gl if gl > 0 else 99.0


def run(over):
    p = copy.deepcopy(ORB_PARAMS); p.update(over)
    bt = ORBBacktester(p); df = bt.run(dfm5)
    if df.empty: return None
    n = len(df); wr = (df.pnl_r > 0).mean() * 100
    cum = df.pnl_r.cumsum(); mddr = (cum.cummax() - cum).max()
    df = df.sort_values("exit_time").reset_index(drop=True); mid = len(df)//2
    return dict(n=n, wr=wr, pf=pf_of(df), sumr=df.pnl_r.sum(), mddr=mddr,
                pf1=pf_of(df.iloc[:mid]), pf2=pf_of(df.iloc[mid:]))


print("=" * 82)
print("  ORB OPTIMIZACION — 518d. Robusto = PF>1 ambas mitades. Ret/DD a 0.5%")
print("=" * 82)
print("\n  --- Sweep RR (rango 30 min) ---")
print(f"  {'RR':<6}{'Trades':>7}{'WR':>7}{'PF':>7}{'Ret0.5%':>9}{'DD0.5%':>8}{'PF1a':>7}{'PF2a':>7}")
for rr in (1.0, 1.5, 2.0, 2.5, 3.0):
    m = run({"target_rr": rr})
    if m:
        fl = " ROB" if m['pf'] > 1 and m['pf1'] > 1 and m['pf2'] > 1 else ""
        print(f"  {rr:<6}{m['n']:>7}{m['wr']:>6.1f}%{m['pf']:>7.2f}{m['sumr']*0.5:>+8.1f}%"
              f"{m['mddr']*0.5:>7.1f}%{m['pf1']:>7.2f}{m['pf2']:>7.2f}{fl}")

print("\n  --- Sweep duracion rango (RR 1.5) ---")
print(f"  {'OR min':<8}{'Trades':>7}{'WR':>7}{'PF':>7}{'Ret0.5%':>9}{'DD0.5%':>8}{'PF1a':>7}{'PF2a':>7}")
for orm in (15, 30, 45, 60):
    m = run({"or_duration_minutes": orm, "target_rr": 1.5})
    if m:
        fl = " ROB" if m['pf'] > 1 and m['pf1'] > 1 and m['pf2'] > 1 else ""
        print(f"  {orm:<8}{m['n']:>7}{m['wr']:>6.1f}%{m['pf']:>7.2f}{m['sumr']*0.5:>+8.1f}%"
              f"{m['mddr']*0.5:>7.1f}%{m['pf1']:>7.2f}{m['pf2']:>7.2f}{fl}")
print("=" * 82)
