# -*- coding: utf-8 -*-
"""Validacion 518d del lead: max 2 DESPLEGABLE (cap) + RR. Robusto = PF>1 ambas mitades.
Muestra DD% a 0.5% y 0.25% para ver a que riesgo el DD se vuelve usable."""
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

BASE = {"max_active_fvgs": 3, "min_zone_points": 5, "avg_spread_points": 4,
        "close_before_weekend": True, "weekend_close_hour": 19, "cap_pending_at_max": True}


def pf_of(df):
    if df.empty: return 0.0
    gp = df[df.pnl_usd > 0].pnl_usd.sum(); gl = abs(df[df.pnl_usd <= 0].pnl_usd.sum())
    return gp / gl if gl > 0 else 99.0


def run(name, ms, rr):
    p = copy.deepcopy(US30_PARAMS); p.update(BASE)
    p["max_simultaneous_trades"] = ms; p["target_rr"] = rr
    bt = FVGBacktester(p); df = bt.run(dfh, dfl)
    if df.empty: return dict(name=name, n=0, wr=0, pf=0, sumr=0, mddr=0, pf1=0, pf2=0)
    n = len(df); wr = (df.pnl_usd > 0).mean() * 100
    cum = df.pnl_r.cumsum(); mddr = (cum.cummax() - cum).max()
    df = df.sort_values("exit_time").reset_index(drop=True); mid = len(df)//2
    return dict(name=name, n=n, wr=wr, pf=pf_of(df), sumr=df.pnl_r.sum(), mddr=mddr,
                pf1=pf_of(df.iloc[:mid]), pf2=pf_of(df.iloc[mid:]))


if __name__ == "__main__":
    print("Cargando 518d...", flush=True)
    dfh = load_csv("data/US30_icm_M5_518d.csv"); dfl = load_csv("data/US30_icm_M1_500k.csv")
    configs = [
        ("max2 RR2", 2, 2.0), ("max2 RR3", 2, 3.0), ("max2 RR4", 2, 4.0),
        ("max3 RR3 (ref)", 3, 3.0),
    ]
    res = []
    for name, ms, rr in configs:
        print(f">>> {name} ...", flush=True)
        res.append(run(name, ms, rr))
    print("\n" + "=" * 88)
    print("  FVG MAX2 VALIDACION — 518d desplegable (cap). Robusto = PF>1 ambas mitades")
    print("=" * 88)
    print(f"  {'Config':<16}{'Trades':>7}{'WR':>7}{'PF':>7}{'SumaR':>8}{'PF1a':>7}{'PF2a':>7}"
          f"{'DD@0.5%':>9}{'DD@0.25%':>10}")
    for m in res:
        flag = " ROBUSTA" if (m['pf'] > 1 and m['pf1'] > 1 and m['pf2'] > 1) else ""
        print(f"  {m['name']:<16}{m['n']:>7}{m['wr']:>6.1f}%{m['pf']:>7.2f}{m['sumr']:>+7.0f}R"
              f"{m['pf1']:>7.2f}{m['pf2']:>7.2f}{m['mddr']*0.5:>8.1f}%{m['mddr']*0.25:>9.1f}%{flag}")
    print("=" * 88)
