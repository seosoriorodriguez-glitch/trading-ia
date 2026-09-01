# -*- coding: utf-8 -*-
"""
Backtest S/R Pivot con particion in-sample / out-of-sample.

Uso:
  python strategies/sr_pivot/backtest/run_backtest.py
  python strategies/sr_pivot/backtest/run_backtest.py --risk 0.004
  python strategies/sr_pivot/backtest/run_backtest.py --set sl_points=80 --set target_rr=2.5

REGLA DE TRABAJO: optimizar SOLO mirando in-sample. Cada vez que se mira el
out-of-sample se gasta muestra. Ya se uso 4 veces (ver README).
"""
import argparse
import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import pandas as pd

from strategies.sr_pivot.backtest.backtester import SRPivotBacktester, summarize
from strategies.sr_pivot.backtest.config import SR_PIVOT_PARAMS, IN_SAMPLE_END
from strategies.sr_pivot.backtest.data_loader import load_m1_concat, check_timezone

VELAS = Path(r"C:\Users\sosor\OneDrive\Documentos\velas m1")
M1_FILES = [
    VELAS / "US30_M1_202401020100_202605201838.csv",
    VELAS / "US30.cash_M1_202604301025_202608112222.csv",
]


def coerce(v: str):
    for cast in (int, float):
        try:
            return cast(v)
        except ValueError:
            pass
    return {"true": True, "false": False, "none": None}.get(v.lower(), v)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--risk", type=float, default=SR_PIVOT_PARAMS["risk_per_trade_pct"])
    ap.add_argument("--balance", type=float, default=SR_PIVOT_PARAMS["initial_balance"])
    ap.add_argument("--set", action="append", default=[], metavar="CLAVE=VALOR")
    ap.add_argument("--oos", action="store_true", help="mostrar out-of-sample (gasta muestra)")
    args = ap.parse_args()

    p = copy.deepcopy(SR_PIVOT_PARAMS)
    for kv in args.set:
        k, v = kv.split("=", 1)
        if k not in p:
            sys.exit(f"Parametro desconocido: {k}\nValidos: {sorted(p)}")
        p[k] = coerce(v)

    print("Cargando M1...")
    m1 = load_m1_concat(*[str(f) for f in M1_FILES])
    print(f"  {len(m1)} velas M1  ({m1.time.iloc[0]} -> {m1.time.iloc[-1]})")
    check_timezone(m1)

    cambios = {k: v for k, v in p.items() if v != SR_PIVOT_PARAMS[k]}
    print(f"\nConfig: TF={p['tf_minutes']}min pivote={p['left']}/{p['right']} "
          f"W={p['zone_width']} SL={p['sl_points']} RR={p['target_rr']} "
          f"N={p['max_levels']} riesgo={args.risk:.3%}")
    if cambios:
        print(f"  MODIFICADO vs config validada: {cambios}")

    bt = SRPivotBacktester(p)
    IS = m1[m1.time <= IN_SAMPLE_END].reset_index(drop=True)
    mo_is = len(IS) / (60 * 24 * 21)

    print("\n" + "=" * 96)
    print(f"IN-SAMPLE  ({IS.time.iloc[0].date()} -> {IS.time.iloc[-1].date()})")
    print("=" * 96)
    summarize(bt.run(IS), "in-sample", mo_is, args.balance, args.risk)

    if args.oos:
        OS = m1[m1.time > IN_SAMPLE_END].reset_index(drop=True)
        mo_os = len(OS) / (60 * 24 * 21)
        print("\n" + "#" * 96)
        print(f"# OUT-OF-SAMPLE ({OS.time.iloc[0].date()} -> {OS.time.iloc[-1].date()})")
        print("#" * 96)
        summarize(bt.run(OS), "out-of-sample", mo_os, args.balance, args.risk)

        mo_all = len(m1) / (60 * 24 * 21)
        print()
        df = bt.run(m1)
        summarize(df, "TOTAL 2024-2026", mo_all, args.balance, args.risk)
        out = Path(__file__).parent / "results" / "trades.csv"
        out.parent.mkdir(exist_ok=True)
        df.to_csv(out, index=False)
        print(f"\nOperaciones guardadas en {out}")
    else:
        print("\n(usar --oos para validar en 2026; gasta muestra, ver README)")


if __name__ == "__main__":
    main()
