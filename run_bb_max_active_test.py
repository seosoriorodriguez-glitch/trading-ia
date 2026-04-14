# -*- coding: utf-8 -*-
"""
Compara el backtest BB con distintos max_active_bbs: 3, 5, 10 (actual).
Usa parametros live (3 consecutivas, London+NY).
"""
import sys
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

import copy
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from strategies.breaker_block.backtest.config    import BB_PARAMS
from strategies.breaker_block.backtest.backtester import BBBacktester
from strategies.fair_value_gap.backtest.data_loader import load_csv, validate_alignment

RISK_USD = 50.0
ACCOUNT  = 10_000.0

M5_PATH = "data/US30_icm_M5_518d.csv"
M1_PATH = "data/US30_icm_M1_500k.csv"


def run_variant(params, label):
    bt = BBBacktester(params)
    df = bt.run(df_m5, df_m1)

    if df.empty:
        print(f"\n  {label}: SIN TRADES")
        return None

    df["pnl_fixed"] = df["pnl_r"] * RISK_USD

    n      = len(df)
    wins   = df[df["pnl_fixed"] > 0]
    losses = df[df["pnl_fixed"] < 0]
    wr     = len(wins) / n * 100
    pf     = wins["pnl_fixed"].sum() / abs(losses["pnl_fixed"].sum()) if len(losses) > 0 else 999
    total  = df["pnl_fixed"].sum()
    ret    = total / ACCOUNT * 100

    cumul  = df["pnl_fixed"].cumsum()
    peak   = cumul.cummax()
    dd     = (peak - cumul) / (ACCOUNT + peak) * 100
    max_dd = dd.max()

    days      = (df["exit_time"].iloc[-1] - df["entry_time"].iloc[0]).days
    avg_month = total / max(days / 30, 1)

    tp_n = len(df[df["exit_reason"] == "tp"])
    sl_n = len(df[df["exit_reason"] == "sl"])

    return {
        "label":     label,
        "trades":    n,
        "wins":      len(wins),
        "losses":    len(losses),
        "wr":        wr,
        "pf":        pf,
        "total":     total,
        "ret":       ret,
        "max_dd":    max_dd,
        "avg_month": avg_month,
        "days":      days,
        "tp":        tp_n,
        "sl":        sl_n,
    }


print("=" * 65)
print("  BB BACKTEST — COMPARACION max_active_bbs: 3 vs 5 vs 10")
print("=" * 65)

print("\nCargando datos...")
df_m5 = load_csv(M5_PATH)
df_m1 = load_csv(M1_PATH)
validate_alignment(df_m5, df_m1)
print(f"  M5: {len(df_m5):,} velas ({df_m5['time'].iloc[0].date()} -> {df_m5['time'].iloc[-1].date()})")
print(f"  M1: {len(df_m1):,} velas")

# Parametros base (live)
base = copy.deepcopy(BB_PARAMS)
base["initial_balance"] = ACCOUNT
base["consecutive_candles"] = 3
base["sessions"] = {
    "london":   {"start": "10:00", "end": "19:00", "skip_minutes": 15},
    "new_york": {"start": "16:30", "end": "23:00", "skip_minutes": 15},
}

results = []
for max_bb in [3, 5, 10]:
    p = copy.deepcopy(base)
    p["max_active_bbs"] = max_bb
    print(f"\n--- Corriendo max_active_bbs = {max_bb} ---")
    r = run_variant(p, f"max_bb={max_bb}")
    if r:
        results.append(r)

# Tabla comparativa
print("\n" + "=" * 65)
print("  COMPARACION FINAL")
print("=" * 65)
print(f"\n  {'Variante':<14} {'Trades':>7} {'WR':>7} {'PF':>7} {'Retorno':>9} {'Max DD':>8} {'$/mes':>8}")
print("  " + "-" * 61)
for r in results:
    print(f"  {r['label']:<14} {r['trades']:>7d} {r['wr']:>6.1f}% {r['pf']:>7.2f}"
          f" {r['ret']:>+8.1f}% {r['max_dd']:>7.2f}% ${r['avg_month']:>7,.0f}")

print("\n  Detalle:")
for r in results:
    print(f"\n  {r['label']}:")
    print(f"    {r['trades']} trades ({r['wins']}W / {r['losses']}L) en {r['days']} dias")
    print(f"    PnL total: ${r['total']:+,.2f}  |  TP: {r['tp']}  |  SL: {r['sl']}")
    print(f"    Balance final: ${ACCOUNT + r['total']:,.2f}")

print("\n" + "=" * 65)
