# -*- coding: utf-8 -*-
"""
Investigacion FVG 100% FIEL AL LIVE: max_active_fvgs=3, min_zone=5, cierre finde,
spread 4 real. Metricas risk-agnosticas (en R) -> derivo 0.3% y 0.5% sobre $200k.

Variantes de concurrencia (todas con max_active_fvgs=3 -> tope 3 pendientes):
  1 open (cap)   : cap_pending -> solo 1 pendiente -> 1 abierta (= bot live actual)
  2 open (cap)   : hasta 2 pendientes -> hasta 2 abiertas
  3 open (cap)   : hasta 3 pendientes -> hasta 3 abiertas (PROPUESTA, live-safe)
  C ref (no live): cola sin cap, fill gateado a 1 -> techo, NO replicable en live
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

# BASE FIEL AL LIVE
MA3 = {"max_active_fvgs": 3, "min_zone_points": 5,
       "close_before_weekend": True, "weekend_close_hour": 19, "avg_spread_points": 4}


def run(name, extra):
    p = copy.deepcopy(US30_PARAMS); p.update(MA3); p.update(extra)
    bt = FVGBacktester(p)
    print(f">>> {name} ...", flush=True)
    df = bt.run(dfh, dfl)
    wins = df[df.pnl_usd > 0]; n = len(df); wr = len(wins) / n * 100 if n else 0
    gl = abs(df[df.pnl_usd <= 0].pnl_usd.sum()); pf = wins.pnl_usd.sum() / gl if gl > 0 else 99
    sumr = df.pnl_r.sum(); avgr = df.pnl_r.mean() if n else 0
    cum = df.pnl_r.cumsum(); mddr = (cum.cummax() - cum).max() if n else 0
    return dict(name=name, n=n, wr=wr, pf=pf, avgr=avgr, sumr=sumr, mddr=mddr)


if __name__ == "__main__":
    print("Cargando datos (fiel al live: max_active_fvgs=3)...", flush=True)
    dfh = load_csv("data/US30_icm_M5_518d.csv"); dfl = load_csv("data/US30_icm_M1_500k.csv")

    configs = [
        ("1 open (cap) = LIVE ACTUAL", {"max_simultaneous_trades": 1, "cap_pending_at_max": True}),
        ("2 open (cap)",              {"max_simultaneous_trades": 2, "cap_pending_at_max": True}),
        ("3 open (cap) PROPUESTA",    {"max_simultaneous_trades": 3, "cap_pending_at_max": True}),
        ("C ref cola+1open (NO live)",{"max_simultaneous_trades": 1}),
    ]
    res = [run(n, e) for n, e in configs]

    print("\n" + "=" * 82)
    print("  FVG FIEL AL LIVE (max_active_fvgs=3, min_zone 5, spread 4, finde)")
    print("=" * 82)
    print(f"  {'Config':<28}{'Trades':>7}{'WR':>7}{'PF':>7}{'AvgR':>8}{'SumaR':>9}{'MaxDD_R':>9}")
    print("  " + "-" * 78)
    for m in res:
        print(f"  {m['name']:<28}{m['n']:>7}{m['wr']:>6.1f}%{m['pf']:>7.2f}"
              f"{m['avgr']:>+8.3f}{m['sumr']:>+8.0f}R{m['mddr']:>+8.0f}R")
    print("  " + "-" * 78)
    print("  Retorno LINEAL y DD en $200k (derivado de R):")
    print(f"  {'Config':<28}{'Ret 0.3%':>11}{'DD 0.3%':>11}{'Ret 0.5%':>11}{'DD 0.5%':>11}")
    for m in res:
        for rp, tag in [(0.003, '03'), (0.005, '05')]:
            pass
        r3 = m['sumr'] * 0.003 * 100; d3 = m['mddr'] * 200000 * 0.003
        r5 = m['sumr'] * 0.005 * 100; d5 = m['mddr'] * 200000 * 0.005
        print(f"  {m['name']:<28}{r3:>+10.0f}%{d3:>+10.0f}${r5:>+10.0f}%{d5:>+10.0f}$")
    print("=" * 82)
    print("  1 open = bot live actual | 3 open = propuesta (live-safe, max 3) | C ref = techo no replicable")
