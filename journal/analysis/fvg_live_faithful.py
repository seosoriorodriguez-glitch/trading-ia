# -*- coding: utf-8 -*-
"""
Compara los 3 comportamientos de concurrencia del FVG (config F, spread 4 real):
  C) ORIGINAL   : encola varias STOP, las llena 1 a la vez segun se liberan slots
                  (es el +305% del backtest; NO seguro en live: MT5 llena solo).
  A) SOLO-1-PEND: solo 1 STOP pendiente a la vez (cap_pending_at_max). Mas conservador.
  B) CANCEL-RESTO: varias STOP (max 3 por max_active_fvgs), la 1a que entra cancela
                   el resto (cancel_pending_on_fill). Punto medio, captura mas.
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

BASE = {"close_before_weekend": True, "weekend_close_hour": 19, "avg_spread_points": 4}


def run(name, extra):
    p = copy.deepcopy(US30_PARAMS); p.update(BASE); p.update(extra)
    bt = FVGBacktester(p); df = bt.run(dfh, dfl)
    wins = df[df.pnl_usd > 0]; losses = df[df.pnl_usd <= 0]
    n = len(df); wr = len(wins) / n * 100
    gl = abs(losses.pnl_usd.sum()); pf = wins.pnl_usd.sum() / gl if gl > 0 else 99
    sumr = df.pnl_r.sum()
    bal = [bt.initial_balance] + list(df.balance); peak = bt.initial_balance; mdd = 0.0
    for b in bal:
        peak = max(peak, b); mdd = max(mdd, (peak - b) / peak * 100)
    return dict(name=name, n=n, wr=wr, pf=pf, sumr=sumr, mdd=mdd, avgr=df.pnl_r.mean())


if __name__ == "__main__":
    print("Cargando datos...", flush=True)
    dfh = load_csv("data/US30_icm_M5_518d.csv"); dfl = load_csv("data/US30_icm_M1_500k.csv")

    res = []
    print(">>> C) ORIGINAL...", flush=True)
    res.append(run("C) original (encola)", {}))
    print(">>> A) SOLO-1-PENDIENTE...", flush=True)
    res.append(run("A) solo-1-pendiente", {"cap_pending_at_max": True}))
    print(">>> B) CANCEL-RESTO...", flush=True)
    res.append(run("B) cancel-resto", {"cancel_pending_on_fill": True}))

    print("\n" + "=" * 78)
    print("  FVG config F (spread 4) — 3 comportamientos de concurrencia (max 1 abierta)")
    print("=" * 78)
    print(f"  {'Comportamiento':<22}{'Trades':>8}{'WR':>7}{'PF':>7}{'AvgR':>8}{'SumaR':>9}{'MaxDD':>8}")
    print("  " + "-" * 68)
    for m in res:
        print(f"  {m['name']:<22}{m['n']:>8}{m['wr']:>6.1f}%{m['pf']:>7.2f}"
              f"{m['avgr']:>+8.3f}{m['sumr']:>+8.0f}R{m['mdd']:>7.1f}%")
    print("  " + "-" * 68)
    print("  Retorno LINEAL (sin compounding):")
    for m in res:
        print(f"    {m['name']:<22} 0.5%: {m['sumr']*0.005*100:>+7.0f}%   0.25%: {m['sumr']*0.0025*100:>+7.0f}%")
    print("=" * 78)
    print("  A = mas seguro/conservador | B = punto medio (max 3, raro) | C = solo backtest (no seguro en live)")
