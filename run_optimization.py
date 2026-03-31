# -*- coding: utf-8 -*-
"""
Optimizacion de parametros — US30 ICM 518 dias
Testea variaciones de 6 parametros clave en paralelo.
"""
import sys, copy, time
from pathlib import Path
from multiprocessing import Pool, cpu_count

sys.path.insert(0, str(Path(__file__).parent))

from strategies.order_block.backtest.config import DEFAULT_PARAMS
from strategies.order_block.backtest.data_loader import load_csv, validate_alignment
from strategies.order_block.backtest.backtester_limit_orders import OrderBlockBacktesterLimitOrders

M5_FILE = "data/US30_icm_M5_518d.csv"
M1_FILE = "data/US30_icm_M1_500k.csv"

# ---------------------------------------------------------------------------
# Variaciones a testear (una a la vez respecto a DEFAULT)
# ---------------------------------------------------------------------------
VARIATIONS = []

# 1. target_rr
for v in [2.0, 2.5, 3.0, 3.5]:
    p = copy.deepcopy(DEFAULT_PARAMS)
    p["target_rr"] = v
    VARIATIONS.append((f"target_rr={v}", p))

# 2. consecutive_candles
for v in [2, 3, 4, 5]:
    p = copy.deepcopy(DEFAULT_PARAMS)
    p["consecutive_candles"] = v
    VARIATIONS.append((f"consec_candles={v}", p))

# 3. expiry_candles
for v in [40, 60, 80, 100]:
    p = copy.deepcopy(DEFAULT_PARAMS)
    p["expiry_candles"] = v
    VARIATIONS.append((f"expiry={v}", p))

# 4. require_bos
for v in [False, True]:
    p = copy.deepcopy(DEFAULT_PARAMS)
    p["require_bos"] = v
    VARIATIONS.append((f"bos={v}", p))

# 5. buffer_points
for v in [15, 20, 25, 30]:
    p = copy.deepcopy(DEFAULT_PARAMS)
    p["buffer_points"] = v
    VARIATIONS.append((f"buffer={v}", p))

# 6. sessions
sessions_variants = {
    "ny_only":   {"new_york":  {"start": "13:30", "end": "20:00", "skip_minutes": 15}},
    "lon_ny":    {"london":    {"start": "08:00", "end": "12:00", "skip_minutes": 0},
                  "new_york":  {"start": "13:30", "end": "20:00", "skip_minutes": 15}},
    "london":    {"london":    {"start": "08:00", "end": "12:00", "skip_minutes": 0}},
    "ny_tight":  {"new_york":  {"start": "14:00", "end": "18:30", "skip_minutes": 0}},
}
for name, sess in sessions_variants.items():
    p = copy.deepcopy(DEFAULT_PARAMS)
    p["sessions"] = sess
    VARIATIONS.append((f"session={name}", p))


# ---------------------------------------------------------------------------
# Funcion que corre un backtest y devuelve metricas
# ---------------------------------------------------------------------------
def run_one(args):
    label, params, df_m5_dict, df_m1_dict = args
    import pandas as pd
    import numpy as np

    df_m5 = pd.DataFrame(df_m5_dict)
    df_m5["time"] = pd.to_datetime(df_m5["time"])
    df_m1 = pd.DataFrame(df_m1_dict)
    df_m1["time"] = pd.to_datetime(df_m1["time"])

    try:
        bt = OrderBlockBacktesterLimitOrders(params)
        df_r = bt.run(df_m5, df_m1)
    except Exception as e:
        return {"label": label, "error": str(e)}

    if df_r.empty:
        return {"label": label, "trades": 0, "wr": 0, "ret": 0, "dd": 0, "pf": 0,
                "exp": 0, "long_wr": 0, "short_wr": 0, "tp": 0, "sl": 0,
                "avg_win": 0, "avg_loss": 0}

    n       = len(df_r)
    wins    = df_r[df_r["pnl_usd"] > 0]
    losses  = df_r[df_r["pnl_usd"] < 0]
    n_long  = len(df_r[df_r["direction"] == "long"])
    n_short = len(df_r[df_r["direction"] == "short"])

    wr      = len(wins) / n * 100
    total   = df_r["pnl_usd"].sum()
    ret     = total / params["initial_balance"] * 100
    exp     = df_r["pnl_usd"].mean()
    pf_num  = wins["pnl_usd"].sum() if len(wins) > 0 else 0
    pf_den  = abs(losses["pnl_usd"].sum()) if len(losses) > 0 else 1
    pf      = pf_num / pf_den if pf_den > 0 else float("inf")

    peak = params["initial_balance"]; max_dd = 0; running = params["initial_balance"]
    for p_ in df_r["pnl_usd"]:
        running += p_
        if running > peak: peak = running
        dd = (peak - running) / peak * 100
        if dd > max_dd: max_dd = dd

    long_w  = len(df_r[(df_r["direction"]=="long")  & (df_r["pnl_usd"]>0)])
    short_w = len(df_r[(df_r["direction"]=="short") & (df_r["pnl_usd"]>0)])

    return {
        "label":    label,
        "trades":   n,
        "wr":       round(wr, 1),
        "ret":      round(ret, 2),
        "dd":       round(max_dd, 2),
        "pf":       round(pf, 2),
        "exp":      round(exp, 0),
        "long_wr":  round(long_w  / n_long  * 100, 1) if n_long  > 0 else 0,
        "short_wr": round(short_w / n_short * 100, 1) if n_short > 0 else 0,
        "tp":       len(df_r[df_r["exit_reason"] == "tp"]),
        "sl":       len(df_r[df_r["exit_reason"] == "sl"]),
        "avg_win":  round(wins["pnl_usd"].mean(),  0) if len(wins)   > 0 else 0,
        "avg_loss": round(losses["pnl_usd"].mean(), 0) if len(losses) > 0 else 0,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("=" * 70)
    print("  OPTIMIZACION DE PARAMETROS — US30 ICM 518 dias")
    print(f"  {len(VARIATIONS)} variaciones | {cpu_count()} CPUs disponibles")
    print("=" * 70)

    print("\nCargando datos una sola vez...")
    df_m5 = load_csv(M5_FILE)
    df_m1 = load_csv(M1_FILE)

    # Serializar como dicts para pasar a subprocesos
    m5_dict = df_m5.to_dict("list")
    m1_dict = df_m1.to_dict("list")
    print(f"  M5: {len(df_m5):,} velas | M1: {len(df_m1):,} velas")

    args = [(label, params, m5_dict, m1_dict) for label, params in VARIATIONS]

    t0 = time.time()
    print(f"\nEjecutando {len(args)} backtests secuencialmente...\n")

    results = []
    for i, arg in enumerate(args, 1):
        label = arg[0]
        print(f"  [{i:2d}/{len(args)}] {label}...", end=" ", flush=True)
        r = run_one(arg)
        results.append(r)
        if "error" in r:
            print(f"ERROR: {r['error']}")
        else:
            print(f"ret={r['ret']:+.1f}%  dd={r['dd']:.1f}%  wr={r['wr']:.1f}%")

    elapsed = time.time() - t0
    print(f"Completado en {elapsed:.0f}s\n")

    # Separar por grupo
    groups = {
        "target_rr":        [r for r in results if r["label"].startswith("target_rr")],
        "consec_candles":   [r for r in results if r["label"].startswith("consec")],
        "expiry":           [r for r in results if r["label"].startswith("expiry")],
        "bos":              [r for r in results if r["label"].startswith("bos")],
        "buffer":           [r for r in results if r["label"].startswith("buffer")],
        "session":          [r for r in results if r["label"].startswith("session")],
    }

    HDR = f"{'Parametro':<22} {'Trades':>6} {'WR%':>6} {'Ret%':>7} {'DD%':>6} {'PF':>5} {'Exp$':>7} {'AvgW':>7} {'AvgL':>7}"
    SEP = "-" * len(HDR)

    for group_name, rows in groups.items():
        print(f"\n{'='*70}")
        print(f"  {group_name.upper()}")
        print(f"{'='*70}")
        print(HDR)
        print(SEP)
        for r in rows:
            if "error" in r:
                print(f"  {r['label']:<20} ERROR: {r['error']}")
                continue
            flag = " <-- BASE" if r["label"] in ("target_rr=3.5", "consec_candles=4",
                                                   "expiry=100", "bos=False",
                                                   "buffer=25", "session=ny_only") else ""
            print(f"{r['label']:<22} {r['trades']:>6} {r['wr']:>5.1f}% {r['ret']:>+7.1f}% "
                  f"{r['dd']:>5.1f}% {r['pf']:>5.2f} {r['exp']:>+7.0f} "
                  f"{r['avg_win']:>+7.0f} {r['avg_loss']:>+7.0f}{flag}")

    # Ranking global por score compuesto: ret/dd (solo resultados positivos)
    print(f"\n{'='*70}")
    print("  RANKING GLOBAL (ret% / dd% — mayor es mejor, solo ret > 0)")
    print(f"{'='*70}")
    scored = []
    for r in results:
        if "error" in r or r["trades"] == 0 or r["ret"] <= 0 or r["dd"] == 0:
            continue
        r["score"] = r["ret"] / r["dd"]
        scored.append(r)
    scored.sort(key=lambda x: x["score"], reverse=True)

    print(HDR + f"  {'Score':>6}")
    print(SEP + "--------")
    for r in scored[:15]:
        print(f"{r['label']:<22} {r['trades']:>6} {r['wr']:>5.1f}% {r['ret']:>+7.1f}% "
              f"{r['dd']:>5.1f}% {r['pf']:>5.2f} {r['exp']:>+7.0f} "
              f"{r['avg_win']:>+7.0f} {r['avg_loss']:>+7.0f}  {r['score']:>5.2f}")

    # Guardar CSV
    import pandas as pd
    out = "strategies/order_block/backtest/results/optimization_results.csv"
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([r for r in results if "error" not in r]).to_csv(out, index=False)
    print(f"\nResultados guardados en: {out}")


if __name__ == "__main__":
    main()
