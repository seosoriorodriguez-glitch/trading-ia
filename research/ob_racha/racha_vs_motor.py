# -*- coding: utf-8 -*-
"""
La racha de sep-oct 2026: ¿el bot hizo lo que el motor dice (es el mercado) o se desvio (es ejecucion)?
Y en el mismo tramo live, ¿el buffer sugerido por el panel (~40) habria rendido distinto que el 35?
SOLO INVESTIGACION: no toca strategies/ ni el bot.

Velas: M1 FTMO US30.cash (mismo feed del live), may-oct 2026, hora servidor.
Motor: MotorTF cerrada=True (119/126 trades reales reproducidos en la validacion de jun-ago).
Emparejado igual que research/ob_m1/validar_vs_live.py: mismo lado y entrada a <=3 min, o mismo
precio (+-3 pts) dentro de 2 h.

    python research/ob_racha/racha_vs_motor.py
"""
import sys
from pathlib import Path

AQUI = Path(__file__).parent
RAIZ = AQUI.parents[1]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "research" / "ob_tf"))

import numpy as np
import pandas as pd

from motor_tf import MotorTF
from research.motor.motor_fiel import Zona
from strategies.order_block.backtest.ob_detection import detect_order_blocks
from strategies.order_block_london.backtest.config import LONDON_PARAMS
from verificar_tf import tf

M1_MAY_AGO = Path(r"C:\Users\sosor\OneDrive\Documentos\velas m1\US30.cash_M1_202605050553_202608142349.csv")
M1_AGO_OCT = AQUI / "_data" / "us30_m1_ago_oct.pkl"
LIVE = AQUI / "_data" / "trades_live.pkl"
TRAMOS = [("jun - 24 sep (buena)", "2026-06-02", "2026-09-25"), ("25 sep - hoy (racha)", "2026-09-25", "2026-10-17")]
TOL_MIN, TOL_PX, TOL_H = 3, 3.0, 2


def velas():
    d = pd.read_csv(M1_MAY_AGO, sep="\t")
    d.columns = [c.strip("<>").lower() for c in d.columns]
    d["time"] = pd.to_datetime(d["date"] + " " + d["time"], format="%Y.%m.%d %H:%M:%S")
    a = d[["time", "open", "high", "low", "close"]]
    b = pd.read_pickle(M1_AGO_OCT)[["time", "open", "high", "low", "close"]]
    m1 = pd.concat([a[a.time < b.time.min()], b]).sort_values("time").drop_duplicates("time")
    return m1[m1.high > m1.low].reset_index(drop=True)          # fuera velas planas de relleno


def motor(m1, buffer):
    p = {k: (dict(v) if isinstance(v, dict) else v) for k, v in LONDON_PARAMS.items()}
    p["buffer_points"] = buffer
    m5 = tf(m1, 5)
    zs = [Zona(o.confirmed_at, o.zone_low, o.zone_high, "alcista" if o.ob_type == "bullish" else "bajista", "OB")
          for o in detect_order_blocks(m5, p)]
    t = MotorTF(p, 5, 1, cerrada=True).run(m5, m1, zs)
    t["R"] = t.pnl_r + (2 + (t.exit_reason == "sl")) / t.riesgo     # costo realista medido en el live
    return t


def emparejar(bt, real):
    bt = bt.copy(); bt["usado"] = False
    filas = []
    for _, r in real.iterrows():
        c = bt[(~bt.usado) & (bt.direction == r.direction)]
        dt = (c.entry_time - r.entry_time).abs()
        c = c[(dt <= pd.Timedelta(minutes=TOL_MIN)) |
              ((dt <= pd.Timedelta(hours=TOL_H)) & ((c.entry_price - r.entry_price).abs() <= TOL_PX))]
        if len(c):
            k = (c.entry_time - r.entry_time).abs().idxmin(); bt.loc[k, "usado"] = True
            filas.append(dict(t=r.entry_time, lado=r.direction, real_R=r.R, bt_R=bt.loc[k, "R"], par=True))
        else:
            filas.append(dict(t=r.entry_time, lado=r.direction, real_R=r.R, bt_R=np.nan, par=False))
    return pd.DataFrame(filas), bt[~bt.usado]


def main():
    m1 = velas()
    print(f"velas M1: {m1.time.min()} -> {m1.time.max()} ({len(m1):,})")
    lv = pd.read_pickle(LIVE)
    lv = lv[lv.bot_id == "us30_live_10k"].copy()
    for c in ("entry_time", "exit_time"):
        lv[c] = pd.to_datetime(lv[c]).dt.tz_localize(None)        # el panel guarda hora servidor
    lv["R"] = lv.pnl_usd / 50

    bts = {b: motor(m1, b) for b in (30, 35, 40, 45)}
    bt = bts[35]

    print("\n=== 1) ¿El bot hizo lo que el motor dice?  (buffer 35, LONDON_PARAMS)")
    filas = []
    for nom, d, h in TRAMOS:
        real = lv[(lv.entry_time >= d) & (lv.entry_time < h)].reset_index(drop=True)
        b = bt[(bt.entry_time >= d) & (bt.entry_time < h)].reset_index(drop=True)
        emp, sobra = emparejar(b, real)
        ok = emp[emp.par]
        filas.append(dict(tramo=nom, live_trades=len(real), live_WR=round((real.R > 0).mean() * 100, 1),
                          live_R=round(real.R.sum(), 1), motor_trades=len(b), motor_WR=round((b.R > 0).mean() * 100, 1),
                          motor_R=round(b.R.sum(), 1), emparejados=f"{len(ok)}/{len(real)}",
                          mismo_resultado=f"{((ok.real_R > 0) == (ok.bt_R > 0)).mean() * 100:.0f}%",
                          motor_sin_pareja=len(sobra)))
    pd.set_option("display.width", 250)
    print(pd.DataFrame(filas).to_string(index=False))

    print("\n=== 2) Buffer en el live: R total por tramo (costo realista)")
    filas = []
    for b, t in bts.items():
        fila = dict(buffer=b)
        for nom, d, h in [("jun-24sep", "2026-06-02", "2026-09-25"), ("racha 25sep-hoy", "2026-09-25", "2026-10-17"),
                          ("todo jun-hoy", "2026-06-02", "2026-10-17")]:
            x = t[(t.entry_time >= d) & (t.entry_time < h)]
            fila[f"{nom} R"] = round(x.R.sum(), 1)
            fila[f"{nom} WR"] = round((x.R > 0).mean() * 100, 1)
        fila["trades"] = len(t[(t.entry_time >= "2026-06-02")])
        filas.append(fila)
    print(pd.DataFrame(filas).to_string(index=False))


if __name__ == "__main__":
    main()
