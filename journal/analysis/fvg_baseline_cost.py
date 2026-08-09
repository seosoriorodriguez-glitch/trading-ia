# -*- coding: utf-8 -*-
"""
Seguimiento: el filtro de tendencia RESULTO PEOR (FVG es mean-reversion).
Aqui probamos el BASELINE (sin filtro de tendencia) con costos REALES medidos
de los trades live (~4 pts) y pesimista (6 pts), + max 1 + cierre de finde.
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

M5 = "data/US30_icm_M5_518d.csv"
M1 = "data/US30_icm_M1_500k.csv"


def metrics(bt, df):
    if df.empty:
        return dict(n=0, tpd=0, wr=0, pf=0, ret=0, mdd=0)
    wins = df[df.pnl_usd > 0]; losses = df[df.pnl_usd <= 0]
    n = len(df); wr = len(wins) / n * 100
    gl = abs(losses.pnl_usd.sum())
    pf = wins.pnl_usd.sum() / gl if gl > 0 else float("inf")
    ret = (bt.balance - bt.initial_balance) / bt.initial_balance * 100
    bal = [bt.initial_balance] + list(df.balance); peak = bt.initial_balance; mdd = 0.0
    for b in bal:
        peak = max(peak, b); mdd = max(mdd, (peak - b) / peak * 100)
    days = max((pd.to_datetime(df.exit_time).max() - pd.to_datetime(df.entry_time).min()).days, 1)
    return dict(n=n, tpd=n / days, wr=wr, pf=pf, ret=ret, mdd=mdd)


def run(name, overrides):
    p = copy.deepcopy(US30_PARAMS); p.update(overrides)
    bt = FVGBacktester(p)
    print(f"\n>>> {name} ...", flush=True)
    df = bt.run(dfh, dfl)
    m = metrics(bt, df); m["name"] = name
    return m


if __name__ == "__main__":
    print("Cargando datos 518d...", flush=True)
    dfh = load_csv(M5); dfl = load_csv(M1)
    W = {"close_before_weekend": True, "weekend_close_hour": 19}
    scenarios = [
        ("E) baseline sp2 (ref)",        {}),
        ("F) baseline +finde +sp4",      {**W, "avg_spread_points": 4}),
        ("G) baseline +finde +sp6",      {**W, "avg_spread_points": 6}),
    ]
    res = [run(n, o) for n, o in scenarios]
    print("\n" + "=" * 74)
    print("  FVG BASELINE (sin filtro tendencia) con costos reales — 518d")
    print("=" * 74)
    print(f"  {'Escenario':<26}{'Trades':>7}{'T/dia':>7}{'WR':>7}{'PF':>7}{'Retorno':>11}{'MaxDD':>8}")
    print("  " + "-" * 72)
    for m in res:
        print(f"  {m['name']:<26}{m['n']:>7}{m['tpd']:>7.1f}{m['wr']:>6.1f}%{m['pf']:>7.2f}"
              f"{m['ret']:>+10.1f}%{m['mdd']:>7.1f}%")
    print("=" * 74)
