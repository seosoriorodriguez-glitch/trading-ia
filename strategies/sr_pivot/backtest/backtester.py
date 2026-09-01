# -*- coding: utf-8 -*-
"""
Motor de backtest S/R Pivot.

Arquitectura:
  - Niveles y disparo de entrada en el TF de deteccion (H1 por defecto).
  - Orden de SL/TP, trailing y parciales resueltos vela a vela en M1.

Por que M1 importa: si una vela del TF de deteccion contiene SL y TP a la vez,
el motor tiene que adivinar. Medido con SL=50: asumir SL da E=+0.038R y asumir
TP da +0.192R sobre los mismos trades — el resultado no significa nada. Con M1
la ambiguedad es cero.
"""
import math
from typing import List, Optional, Tuple

import numpy as np
import pandas as pd

from strategies.sr_pivot.backtest.levels import Level, find_levels, resample_tf


class SRPivotBacktester:
    def __init__(self, params: dict):
        self.p = params

    # ------------------------------------------------------------------ run
    def run(self, m1: pd.DataFrame) -> pd.DataFrame:
        p = self.p
        det = resample_tf(m1, p["tf_minutes"])
        levels = find_levels(det, p["left"], p["right"])

        tt = det["time"].values
        H = det["high"].values
        L = det["low"].values
        hours = pd.DatetimeIndex(det["time"]).hour.values

        mt = m1["time"].values
        mh = m1["high"].values
        ml = m1["low"].values

        W, S, RR = p["zone_width"], p["sl_points"], p["target_rr"]
        active: List[dict] = []
        used = set()
        li = 0
        open_trades = 0
        busy_until = np.datetime64("1970-01-01")
        out = []

        for k in range(len(det)):
            now, hk, lk = tt[k], H[k], L[k]

            while li < len(levels) and levels[li].activation_time <= now:
                lv = levels[li]
                merged = False
                if p["cluster_pts"] > 0:
                    for d in active:
                        if d["kind"] == lv.kind and abs(d["price"] - lv.price) <= p["cluster_pts"]:
                            d["born"] = k
                            merged = True
                            break
                if not merged:
                    active.append({"price": lv.price, "kind": lv.kind, "id": li, "born": k})
                    if len(active) > p["max_levels"]:
                        active.pop(0)
                li += 1

            if p["level_life"] > 0:
                active = [d for d in active if k - d["born"] <= p["level_life"]]

            if now < busy_until:
                continue
            if p["session"] and not (p["session"][0] <= hours[k] < p["session"][1]):
                continue

            for d in active:
                if p["one_trade_per_level"] and d["id"] in used:
                    continue
                sgn = 1 if d["kind"] == "sup" else -1
                trig = d["price"] + sgn * W
                if not (lk <= trig <= hk):
                    continue

                sl = d["price"] - sgn * S
                risk = abs(trig - sl)
                if p["tp_mode"] == "rr":
                    tp = trig + sgn * risk * RR
                else:
                    opp = [x["price"] for x in active
                           if x["kind"] != d["kind"] and sgn * (x["price"] - trig) > 0]
                    if not opp:
                        continue
                    tp = min(opp) if sgn == 1 else max(opp)
                    if abs(tp - trig) / risk < p["min_rr"]:
                        continue

                used.add(d["id"])
                res = self._resolve(mt, mh, ml, now, sgn, trig, sl, tp, risk)
                if res is None:
                    break
                r, xt = res
                out.append({"entry_time": now, "direction": "long" if sgn == 1 else "short",
                            "level": d["price"], "entry": trig, "sl": sl, "tp": tp,
                            "r": r, "exit_time": xt})
                busy_until = xt
                break

        return pd.DataFrame(out)

    # -------------------------------------------------------------- resolve
    def _resolve(self, mt, mh, ml, now, sgn, entry, sl, tp, risk
                 ) -> Optional[Tuple[float, np.datetime64]]:
        """Recorre M1 desde la entrada. Devuelve (R_neto, hora_salida)."""
        p = self.p
        cost_r = p["cost_points"] / risk
        i0 = int(np.searchsorted(mt, now))
        end = min(i0 + 60 * 24 * 20, len(mt))

        entered = False
        peak = entry
        booked = 0.0
        remaining = 1.0
        cur_sl = sl

        for i in range(i0, end):
            if not entered:
                if ml[i] <= entry <= mh[i]:
                    entered = True
                continue

            hi, lo = mh[i], ml[i]
            fav = (hi - entry) if sgn == 1 else (entry - lo)
            rmul = fav / risk

            if p["partial_at"] > 0 and remaining == 1.0 and rmul >= p["partial_at"]:
                booked += p["partial_pct"] * p["partial_at"]
                remaining = 1.0 - p["partial_pct"]
                if p["partial_be"]:
                    cur_sl = entry

            if p["trail_start"] > 0 and rmul >= p["trail_start"]:
                peak = max(peak, hi) if sgn == 1 else min(peak, lo)
                nsl = peak - sgn * p["trail_dist"]
                cur_sl = max(cur_sl, nsl) if sgn == 1 else min(cur_sl, nsl)

            hit_sl = (lo <= cur_sl) if sgn == 1 else (hi >= cur_sl)
            hit_tp = (hi >= tp) if sgn == 1 else (lo <= tp)
            if hit_sl:
                return booked + remaining * (sgn * (cur_sl - entry) / risk) - cost_r, mt[i]
            if hit_tp:
                return booked + remaining * (sgn * (tp - entry) / risk) - cost_r, mt[i]

        return None


# ------------------------------------------------------------------ metricas
def summarize(df: pd.DataFrame, label: str, months: float,
              balance: float = 10_000.0, risk_pct: float = 0.005) -> Optional[dict]:
    if df is None or len(df) == 0:
        print(f"{label:32s} sin operaciones")
        return None

    r = df["r"].values
    n = len(r)
    w, l = r[r > 0], r[r <= 0]
    usd = balance * risk_pct
    pf = w.sum() / abs(l.sum()) if len(l) and l.sum() != 0 else float("inf")

    eq = pk = balance
    mdd = 0.0
    for v in r:
        eq += v * usd
        pk = max(pk, eq)
        mdd = max(mdd, (pk - eq) / pk * 100)

    total = r.sum() * usd
    se = r.std(ddof=1) / math.sqrt(n) if n > 1 else float("nan")

    print(f"{label:32s} n={n:4d} WR={len(w)/n*100:5.1f}% PF={pf:5.2f} "
          f"tot={total/balance*100:+6.1f}% mes={total/months/balance*100:+5.2f}% "
          f"DD={mdd:5.2f}% t={r.mean()/se:+5.2f}")

    return {"n": n, "wr": len(w) / n * 100, "pf": pf, "total_pct": total / balance * 100,
            "monthly_pct": total / months / balance * 100, "max_dd_pct": mdd,
            "t": r.mean() / se}
