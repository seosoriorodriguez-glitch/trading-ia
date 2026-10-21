# -*- coding: utf-8 -*-
"""
¿Cuanto de la diferencia motor vs live se explica con las reglas del live que el motor no tenia?
Compara 4 motores contra el 10k live (jun-oct 2026): el actual, + cupo como el live, + noticias, + ambas.
Verificacion: MotorLive(cupo_live=False, noticias=False) debe dar exactamente lo mismo que MotorTF cerrada.

    python research/ob_racha/reglas_live.py
"""
import sys
from pathlib import Path

AQUI = Path(__file__).parent
sys.path.insert(0, str(AQUI))

import pandas as pd

import racha_vs_motor as RV
from motor_live import MotorLive
from research.motor.motor_fiel import Zona
from strategies.order_block.backtest.ob_detection import detect_order_blocks
from strategies.order_block_london.backtest.config import LONDON_PARAMS
from verificar_tf import tf

TRAMOS = [("jun-24sep", "2026-06-02", "2026-09-25"), ("racha", "2026-09-25", "2026-10-17"),
          ("total", "2026-06-02", "2026-10-17")]


def correr(m1, **kw):
    p = {k: (dict(v) if isinstance(v, dict) else v) for k, v in LONDON_PARAMS.items()}
    m5 = tf(m1, 5)
    zs = [Zona(o.confirmed_at, o.zone_low, o.zone_high, "alcista" if o.ob_type == "bullish" else "bajista", "OB")
          for o in detect_order_blocks(m5, p)]
    mot = MotorLive(p, **kw)
    t = mot.run(m5, m1, zs)
    t["R"] = t.pnl_r + (2 + (t.exit_reason == "sl")) / t.riesgo
    return t, mot.max_abiertas


def main():
    m1 = RV.velas()
    lv = pd.read_pickle(RV.LIVE)
    lv = lv[lv.bot_id == "us30_live_10k"].copy()
    for c in ("entry_time", "exit_time"):
        lv[c] = pd.to_datetime(lv[c]).dt.tz_localize(None)
    lv["R"] = lv.pnl_usd / 50

    base = RV.motor(m1, 35)
    chk, _ = correr(m1, cupo_live=False, noticias=False)
    igual = len(base) == len(chk) and (base.entry_time.values == chk.entry_time.values).all() and \
        abs(base.R.sum() - chk.R.sum()) < 1e-6
    print(f"verificacion MotorLive(sin reglas) == MotorTF cerrada: {'OK' if igual else 'DISTINTO'} ({len(base)} vs {len(chk)})")

    variantes = {"motor actual": dict(cupo_live=False, noticias=False),
                 "+ noticias": dict(cupo_live=False, noticias=True),
                 "+ cupo como live": dict(cupo_live=True, noticias=False),
                 "+ cupo + noticias": dict(cupo_live=True, noticias=True)}
    filas = []
    for nom, kw in variantes.items():
        bt, mx = correr(m1, **kw)
        for tr, d, h in TRAMOS:
            real = lv[(lv.entry_time >= d) & (lv.entry_time < h)].reset_index(drop=True)
            b = bt[(bt.entry_time >= d) & (bt.entry_time < h)].reset_index(drop=True)
            emp, sobra = RV.emparejar(b, real)
            ok = emp[emp.par]
            filas.append(dict(motor=nom, tramo=tr, live_tr=len(real), live_R=round(real.R.sum(), 1),
                              motor_tr=len(b), motor_R=round(b.R.sum(), 1),
                              coinciden=f"{len(ok)}/{len(real)} ({len(ok) / len(real) * 100:.0f}%)",
                              solo_live=f"{(~emp.par).sum()} ({emp[~emp.par].real_R.sum():+.1f}R)",
                              solo_motor=f"{len(sobra)} ({sobra.R.sum():+.1f}R)",
                              max_abiertas=mx))
    pd.set_option("display.width", 250)
    print(pd.DataFrame(filas).to_string(index=False))


if __name__ == "__main__":
    main()
