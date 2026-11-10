# -*- coding: utf-8 -*-
"""
Prueba de PARIDAD: la logica del bot (estrategia.py + backtest.py, minuto a minuto, viendo solo el pasado) da
exactamente los mismos ordenes y trades que la investigacion (research/pa_lab/estructura_pa/falsa_ruptura_v2.py base,
motor_pa.py) sobre las velas M1 de un periodo.

  1) ordenes: las que arma el bot hora a hora (ventana de 600 velas H1 + la vela en formacion) contra las de la
     investigacion (todas las velas del periodo): mismo nivel, hora, precio, SL y TP.
  2) trades: backtest.py contra motor_pa.correr(fin_semana=False), R sin swap. Ademas se informa la diferencia con
     fin_semana=True (la version de la investigacion, que cierra en la ultima vela de una semana cortada por feriado).

    python papel/estrategias/falsa_ruptura_h1/herramientas/paridad.py                    # 2026-01-01 a 2026-11-01
    python papel/estrategias/falsa_ruptura_h1/herramientas/paridad.py 2025-01-01 2026-01-01
"""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[4]
for p in (RAIZ, RAIZ / "research" / "pa_lab", RAIZ / "research" / "pa_lab" / "repaso",
          RAIZ / "research" / "pa_lab" / "estructura_pa"):
    sys.path.insert(0, str(p))

import numpy as np
import pandas as pd

from datos import m1_periodo, tf
import comun_pa as CP
import falsa_ruptura_v2 as V2
import motor_pa as MP
from papel.estrategias.falsa_ruptura_h1.backtest import VENTANA_H1, simular, velas_h1
from papel.estrategias.falsa_ruptura_h1.estrategia import EstrategiaFR


def main():
    ini = pd.Timestamp(sys.argv[1] if len(sys.argv) > 1 else "2026-01-01")
    fin = pd.Timestamp(sys.argv[2] if len(sys.argv) > 2 else "2026-11-01")
    m1 = m1_periodo(ini, fin, margen_dias=40)[["time", "open", "high", "low", "close"]].reset_index(drop=True)
    est = EstrategiaFR()

    # --- investigacion
    ctx = {"m1": m1, "tf": {60: tf(m1, 60)}, "cache": {}}
    od = CP.con_ref(ctx, V2.ordenes(ctx, V2.BASE))
    inv = od[(od.desde >= ini) & (od.desde < fin)].copy()

    # --- bot: hora a hora con lo que veria en vivo
    h1 = velas_h1(m1)
    h1t = h1.time.values
    vistas = {}
    for hora in pd.date_range(ini, fin, freq="h"):
        k = int(np.searchsorted(h1t, np.datetime64(hora), side="right"))
        for o in est.ordenes(h1.iloc[max(0, k - VENTANA_H1 - 1):k]):
            if o.desde <= hora and (o.clave, o.desde) not in vistas:
                vistas[(o.clave, o.desde)] = o
    bot = pd.DataFrame([dict(clave=o.clave, desde=o.desde, px=o.precio, sl=o.sl, tp=o.tp, nivel=o.nivel,
                             dir=o.dir) for o in vistas.values()])
    bot = bot[(bot.desde >= ini) & (bot.desde < fin)]
    a = inv[["desde", "nivel", "dir", "px", "sl", "tp"]].sort_values(["desde", "nivel"]).reset_index(drop=True)
    b = bot[["desde", "nivel", "dir", "px", "sl", "tp"]].sort_values(["desde", "nivel"]).reset_index(drop=True)
    ok1 = len(a) == len(b) and (a.desde.values == b.desde.values).all() and (a.dir.values == b.dir.values).all() \
        and np.allclose(a[["nivel", "px", "sl", "tp"]].values, b[["nivel", "px", "sl", "tp"]].values, atol=1e-6)
    print(f"1) ordenes: investigacion {len(a)} | bot {len(b)} | identicas: {ok1}")
    if not ok1:
        m = a.merge(b, on=["desde", "nivel"], how="outer", suffixes=("_inv", "_bot"), indicator=True)
        print(m[(m._merge != "both") | ~np.isclose(m.px_inv, m.px_bot)].head(10).to_string())

    # --- trades
    r = MP.correr(m1, od, max_activas=5, fin_semana=False)
    r = r[(r.entry_time >= ini) & (r.entry_time < fin)].reset_index(drop=True)
    s = simular(m1, est, feriados=False)            # la regla de corte del motor de investigacion
    s = s[(s.entry_time >= ini) & (s.entry_time < fin)].reset_index(drop=True)
    print(f"2) trades: investigacion {len(r)} ({r.R.sum():+.2f}R sin swap) | logica del bot {len(s)} ({s.R.sum():+.2f}R)")
    ok2 = len(r) == len(s)
    if ok2:
        cols = ["entry_time", "exit_time", "direction", "exit_reason"]
        num = ["px", "entry_price", "sl", "tp", "exit_price", "R"]
        s2 = s.rename(columns={"orden": "px"})
        iguales = (r[cols].values == s2[cols].values).all(axis=1) & \
            np.isclose(r[num].values.astype(float), s2[num].values.astype(float), atol=1e-6).all(axis=1)
        ok2 = bool(iguales.all())
        print(f"   trades identicos: {iguales.sum()} de {len(r)}")
        if not ok2:
            print(pd.concat([r[~iguales][cols + num].head(5), s2[~iguales][cols + num].head(5)]).to_string())
    else:
        m = r.merge(s, on="entry_time", how="outer", suffixes=("_inv", "_bot"), indicator=True)
        print(m[m._merge != "both"].head(10).to_string())
    rf = MP.correr(m1, od, max_activas=5, fin_semana=True)
    rf = rf[(rf.entry_time >= ini) & (rf.entry_time < fin)]
    dif = rf[rf.exit_reason == "fin_semana"]
    print(f"   referencia: con fin_semana=True (investigacion) {len(rf)} trades {rf.R.sum():+.2f}R; cerrados por semana "
          f"cortada: {len(dif)} ({', '.join(f'{x:%d-%m-%Y}' for x in dif.exit_time)})")
    print("\nPARIDAD OK" if ok1 and ok2 else "\nPARIDAD CON DIFERENCIAS")


if __name__ == "__main__":
    main()
