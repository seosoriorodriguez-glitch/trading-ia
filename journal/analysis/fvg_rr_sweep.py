# -*- coding: utf-8 -*-
"""Sweep de RR (target) sobre 518d. La pista: RR alto mejora. Busca robusto (PF>1 ambas mitades)."""
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

BASE = {"max_active_fvgs": 3, "max_simultaneous_trades": 3, "min_zone_points": 5,
        "avg_spread_points": 4, "close_before_weekend": True, "weekend_close_hour": 19}


def pf_of(df):
    if df.empty: return 0.0
    gp = df[df.pnl_usd > 0].pnl_usd.sum(); gl = abs(df[df.pnl_usd <= 0].pnl_usd.sum())
    return gp / gl if gl > 0 else 99.0


def run(rr):
    p = copy.deepcopy(US30_PARAMS); p.update(BASE); p["target_rr"] = rr
    bt = FVGBacktester(p); df = bt.run(dfh, dfl)
    if df.empty: return dict(rr=rr, n=0, wr=0, pf=0, sumr=0, mddr=0, pf1=0, pf2=0)
    n = len(df); wr = (df.pnl_usd > 0).mean() * 100
    cum = df.pnl_r.cumsum(); mddr = (cum.cummax() - cum).max()
    df = df.sort_values("exit_time").reset_index(drop=True); mid = len(df)//2
    return dict(rr=rr, n=n, wr=wr, pf=pf_of(df), sumr=df.pnl_r.sum(), mddr=mddr,
                pf1=pf_of(df.iloc[:mid]), pf2=pf_of(df.iloc[mid:]))


if __name__ == "__main__":
    print("Cargando 518d...", flush=True)
    dfh = load_csv("data/US30_icm_M5_518d.csv"); dfl = load_csv("data/US30_icm_M1_500k.csv")
    res = []
    for rr in (2.0, 3.0, 3.5, 4.0, 4.5, 5.0):
        print(f">>> RR {rr} ...", flush=True)
        res.append(run(rr))
    print("\n" + "=" * 76)
    print("  FVG SWEEP RR — 518d (natural 3, zona 5). Robusto = PF>1 en AMBAS mitades")
    print("=" * 76)
    print(f"  {'RR':<6}{'Trades':>7}{'WR':>7}{'PF':>7}{'SumaR':>8}{'MaxDD_R':>9}{'PF 1a':>8}{'PF 2a':>8}")
    for m in res:
        flag = "  <-- ROBUSTA" if (m['pf'] > 1 and m['pf1'] > 1 and m['pf2'] > 1) else ""
        print(f"  {m['rr']:<6}{m['n']:>7}{m['wr']:>6.1f}%{m['pf']:>7.2f}{m['sumr']:>+7.0f}R"
              f"{m['mddr']:>+8.0f}R{m['pf1']:>8.2f}{m['pf2']:>8.2f}{flag}")
    print("=" * 76)
