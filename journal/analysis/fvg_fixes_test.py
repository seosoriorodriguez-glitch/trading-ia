# -*- coding: utf-8 -*-
"""
Compara la estrategia FVG con los 3 fixes vs baseline, sobre 518 dias M5/M1.

Escenarios:
  A) BASELINE      : config live (3 sesiones, sin filtro tendencia, max_sim 1)
  B) +FIX 1+2      : filtro de tendencia (EMA 4H) + max 1 simultaneo
  C) +FIX 1+2+3    : + cierre de fin de semana
  D) +COSTOS REALES: escenario C con spread 6 (prueba acida de ejecucion)

Uso:
  python journal/analysis/fvg_fixes_test.py
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
        return dict(n=0, tpd=0, wr=0, pf=0, ret=0, mdd=0, nl=0, wl=0, ns=0, ws=0)
    wins = df[df.pnl_usd > 0]; losses = df[df.pnl_usd <= 0]
    n = len(df); wr = len(wins) / n * 100
    gl = abs(losses.pnl_usd.sum())
    pf = wins.pnl_usd.sum() / gl if gl > 0 else float("inf")
    ret = (bt.balance - bt.initial_balance) / bt.initial_balance * 100
    bal = [bt.initial_balance] + list(df.balance); peak = bt.initial_balance; mdd = 0.0
    for b in bal:
        peak = max(peak, b); mdd = max(mdd, (peak - b) / peak * 100)
    longs = df[df.direction == "long"]; shorts = df[df.direction == "short"]
    wl = (longs.pnl_usd > 0).mean() * 100 if len(longs) else 0
    ws = (shorts.pnl_usd > 0).mean() * 100 if len(shorts) else 0
    days = max((pd.to_datetime(df.exit_time).max() - pd.to_datetime(df.entry_time).min()).days, 1)
    return dict(n=n, tpd=n / days, wr=wr, pf=pf, ret=ret, mdd=mdd,
                nl=len(longs), wl=wl, ns=len(shorts), ws=ws)


def run(name, overrides):
    p = copy.deepcopy(US30_PARAMS)
    p.update(overrides)
    bt = FVGBacktester(p)
    print(f"\n>>> {name} ...", flush=True)
    df = bt.run(dfh, dfl)
    m = metrics(bt, df)
    m["name"] = name
    return m


if __name__ == "__main__":
    print("Cargando datos 518d (M5 + M1)...", flush=True)
    dfh = load_csv(M5); dfl = load_csv(M1)
    print(f"  M5: {len(dfh):,}  M1: {len(dfl):,}", flush=True)

    scenarios = [
        ("A) BASELINE (live)",       {}),
        ("B) +tendencia +max1",      {"ema_trend_filter": True, "ema_4h_period": 20,
                                      "max_simultaneous_trades": 1}),
        ("C) +cierre finde",         {"ema_trend_filter": True, "ema_4h_period": 20,
                                      "max_simultaneous_trades": 1,
                                      "close_before_weekend": True, "weekend_close_hour": 19}),
        ("D) C +costos reales(sp6)", {"ema_trend_filter": True, "ema_4h_period": 20,
                                      "max_simultaneous_trades": 1,
                                      "close_before_weekend": True, "weekend_close_hour": 19,
                                      "avg_spread_points": 6}),
    ]

    res = [run(n, o) for n, o in scenarios]

    print("\n" + "=" * 92)
    print("  COMPARACION FVG US30 — 518 dias (M5 deteccion / M1 entrada)")
    print("=" * 92)
    hdr = f"  {'Escenario':<26}{'Trades':>7}{'T/dia':>7}{'WR':>7}{'PF':>7}{'Retorno':>10}{'MaxDD':>8}{'WR long':>9}{'WR short':>10}"
    print(hdr)
    print("  " + "-" * 90)
    for m in res:
        print(f"  {m['name']:<26}{m['n']:>7}{m['tpd']:>7.1f}{m['wr']:>6.1f}%{m['pf']:>7.2f}"
              f"{m['ret']:>+9.1f}%{m['mdd']:>7.1f}%{m['wl']:>8.1f}%{m['ws']:>9.1f}%")
    print("=" * 92)
    print("\n  Detalle long/short (n trades):")
    for m in res:
        print(f"  {m['name']:<26} long: {m['nl']:>5} (WR {m['wl']:.1f}%)   short: {m['ns']:>5} (WR {m['ws']:.1f}%)")
    print()
