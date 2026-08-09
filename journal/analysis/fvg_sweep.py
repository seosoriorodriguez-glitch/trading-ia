# -*- coding: utf-8 -*-
"""
Sweep de afinacion FVG sobre 518d (baseline sin filtro tendencia, cierre finde, spread 4):
  - min_zone_points: 5 / 15 / 20 / 25
  - DD diario:       2% / 3% / 4%
  - Sesiones:        breakdown del run base (Asia / London / NY)
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


def metrics(bt, df):
    if df.empty:
        return dict(n=0, tpd=0, wr=0, pf=0, ret=0, mdd=0, sumr=0)
    wins = df[df.pnl_usd > 0]; losses = df[df.pnl_usd <= 0]
    n = len(df); wr = len(wins) / n * 100
    gl = abs(losses.pnl_usd.sum()); pf = wins.pnl_usd.sum() / gl if gl > 0 else 99
    ret = (bt.balance - bt.initial_balance) / bt.initial_balance * 100
    bal = [bt.initial_balance] + list(df.balance); peak = bt.initial_balance; mdd = 0.0
    for b in bal:
        peak = max(peak, b); mdd = max(mdd, (peak - b) / peak * 100)
    days = max((pd.to_datetime(df.exit_time).max() - pd.to_datetime(df.entry_time).min()).days, 1)
    return dict(n=n, tpd=n / days, wr=wr, pf=pf, ret=ret, mdd=mdd, sumr=df.pnl_r.sum())


def run(over):
    p = copy.deepcopy(US30_PARAMS); p.update(BASE); p.update(over)
    bt = FVGBacktester(p); df = bt.run(dfh, dfl)
    return bt, df, metrics(bt, df)


if __name__ == "__main__":
    print("Cargando datos...", flush=True)
    dfh = load_csv("data/US30_icm_M5_518d.csv"); dfl = load_csv("data/US30_icm_M1_500k.csv")

    print("\n### MIN_ZONE_POINTS ###", flush=True)
    mz_res = []
    base_df = None
    for mz in (5, 15, 20, 25):
        print(f"  min_zone={mz}...", flush=True)
        bt, df, m = run({"min_zone_points": mz}); m["mz"] = mz
        mz_res.append(m)
        if mz == 5:
            base_df = df.copy()

    print("\n### DD DIARIO (min_zone=5) ###", flush=True)
    dd_res = []
    for dd in (2.0, 3.0, 4.0):
        print(f"  dd={dd}%...", flush=True)
        bt, df, m = run({"ftmo_daily_loss_pct": dd}); m["dd"] = dd
        dd_res.append(m)

    print("\n" + "=" * 70)
    print("  SWEEP FVG — 518d (spread 4 real, sin filtro tendencia, max 1, finde)")
    print("=" * 70)
    print("\n  min_zone_points | Trades | T/dia |   WR  |  PF  | Ret(comp) | MaxDD | SumaR")
    for m in mz_res:
        print(f"       {m['mz']:>3} pts     | {m['n']:>5} | {m['tpd']:>4.1f} | {m['wr']:>4.1f}% | {m['pf']:.2f} | "
              f"{m['ret']:>+8.0f}% | {m['mdd']:>4.1f}% | {m['sumr']:>+6.0f}R")
    print("\n  DD diario | Trades |   WR  |  PF  | Ret(comp) | MaxDD | SumaR")
    for m in dd_res:
        print(f"     {m['dd']:.0f}%    | {m['n']:>5} | {m['wr']:>4.1f}% | {m['pf']:.2f} | "
              f"{m['ret']:>+8.0f}% | {m['mdd']:>4.1f}% | {m['sumr']:>+6.0f}R")

    print("\n### SESIONES (breakdown del run min_zone=5) ###")
    if base_df is not None and "session" in base_df.columns:
        g = base_df.groupby("session")
        print("  Sesion       | Trades |   WR  |  SumaR  | PnL$(comp)")
        for name, s in g:
            wr = (s.pnl_usd > 0).mean() * 100
            print(f"  {name:12s} | {len(s):>5} | {wr:>4.1f}% | {s.pnl_r.sum():>+6.0f}R | {s.pnl_usd.sum():>+10.0f}")
    print("=" * 70)
