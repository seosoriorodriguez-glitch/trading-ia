# -*- coding: utf-8 -*-
"""
Prueba de PARIDAD: la logica del bot (estrategia.py) da exactamente los mismos trades que el backtest
(research/pa_lab/repaso/motor_toque2.py, solo LIMIT, W 20, S 130, RR 2.5) sobre las velas M1 de un periodo.

Como lo haria el bot en vivo: en cada minuto ve solo el pasado. Las velas H1 que recibe son las ultimas 600 MAS la
vela en formacion (de ella solo se usa la hora), los niveles se recalculan al empezar cada hora, los activos y
usados salen de estrategia.py y los bloqueos (noticias, viernes, fin de semana) de sus funciones de horario.
El llenado y las salidas los simula papel/estrategias/sr_pivot_h1/backtest.py (reglas del motor: velas Bid,
Ask = Bid + 2.1, desliz SL 0.7); el bot en papel y papel/fidelidad.py usan ese mismo archivo.

    python papel/estrategias/sr_pivot_h1/herramientas/paridad.py                    # 2026-01-01 a 2026-11-01
    python papel/estrategias/sr_pivot_h1/herramientas/paridad.py 2025-01-01 2026-01-01
"""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "research" / "pa_lab"))
sys.path.insert(0, str(RAIZ / "research" / "pa_lab" / "repaso"))

import numpy as np
import pandas as pd

from datos import es_cierre_viernes, es_noticia, m1_periodo, tf
import motor_toque2 as MT
from strategies.sr_pivot.backtest.levels import find_levels as find_levels_backtest
from papel.estrategias.sr_pivot_h1.estrategia import EstrategiaSR, bloqueado, ventanas_de_texto
from papel.estrategias.sr_pivot_h1.niveles import find_levels
from papel.estrategias.sr_pivot_h1.backtest import simular as simular_bot

SPREAD, DESLIZ_SL = 2.1, 0.7
VENTANAS = ventanas_de_texto(["08:26-08:34"])
VENTANA_H1 = 600


def simular(m1, est):
    return simular_bot(m1, est, spread=SPREAD, desliz_sl=DESLIZ_SL)


def main():
    ini = pd.Timestamp(sys.argv[1] if len(sys.argv) > 1 else "2026-01-01")
    fin = pd.Timestamp(sys.argv[2] if len(sys.argv) > 2 else "2026-11-01")
    m1 = m1_periodo(ini, fin, margen_dias=40)
    h1 = tf(m1, 60)

    # 1) la copia de find_levels da lo mismo que la del backtest
    a, b = find_levels(h1, 15, 15), find_levels_backtest(h1, 15, 15)
    print(f"1) niveles: copia {len(a)} | backtest {len(b)} | identicos: {a == b}")

    # 2) bloqueos del bot == los del backtest
    tt = pd.to_datetime(m1.time)
    mio = np.array([bloqueado(x, VENTANAS) for x in tt])
    ref = es_noticia(m1.time) | es_cierre_viernes(m1.time) | (tt.dt.weekday.values >= 5)
    print(f"2) minutos bloqueados: bot {mio.sum()} | backtest {ref.sum()} | distintos {(mio != ref).sum()}")

    # 3) trades
    nv = [(pd.Timestamp(x.activation_time), x.price, x.kind, k) for k, x in enumerate(b)]
    r = MT.correr(m1, nv, 20, 130, 2.5, solo_limit=True, escala=True)
    r = r[(r.entry_time >= ini) & (r.entry_time < fin)].reset_index(drop=True)
    s = simular(m1, EstrategiaSR(20, 130, 2.5))
    s = s[(s.entry_time >= ini) & (s.entry_time < fin)].reset_index(drop=True)
    print(f"3) trades: backtest {len(r)} ({r.R.sum():+.2f}R) | logica del bot {len(s)} ({s.R.sum():+.2f}R)")
    cols = ["entry_time", "exit_time", "direction", "exit_reason"]
    num = ["nivel", "orden", "entry_price", "sl", "tp", "exit_price", "R"]
    if len(r) == len(s):
        iguales = (r[cols].values == s[cols].values).all(axis=1) & \
            np.isclose(r[num].values.astype(float), s[num].values.astype(float), atol=1e-6).all(axis=1)
        print(f"   trades identicos: {iguales.sum()} de {len(r)}")
        if not iguales.all():
            print(pd.concat([r[~iguales].head(5), s[~iguales].head(5)]).to_string())
    else:
        m = r.merge(s, on="entry_time", how="outer", suffixes=("_bt", "_bot"), indicator=True)
        print(m[m._merge != "both"].head(10).to_string())
    print("\nPARIDAD OK" if len(r) == len(s) and iguales.all() and a == b and (mio == ref).all() else "\nPARIDAD CON DIFERENCIAS")


if __name__ == "__main__":
    main()
