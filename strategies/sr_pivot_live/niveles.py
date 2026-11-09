# -*- coding: utf-8 -*-
"""
Niveles S/R por pivotes (LuxAlgo "Support and Resistance Levels with Breaks", 15/15).

COPIA de strategies/sr_pivot/backtest/levels.py:find_levels (la misma que usa el backtest), para que el bot no dependa
de archivos de investigacion que se puedan editar. herramientas/paridad.py comprueba que ambas dan lo mismo.

Un pivote en la vela i (maximo o minimo de las velas i-15 .. i+15) recien se conoce cuando cerraron las 15 velas de la
derecha: el nivel se activa en la APERTURA de la vela i+16. Nunca antes (con adelanto el backtest da WR 95 %).
"""
from typing import List, NamedTuple

import pandas as pd


class Level(NamedTuple):
    activation_time: pd.Timestamp   # cuando el nivel pasa a ser operable (apertura de la vela i+16)
    activation_index: int
    price: float                    # high del pivote (res) o low (sup)
    kind: str                       # "sup" | "res"
    pivot_time: pd.Timestamp        # apertura de la vela del pivote


def find_levels(df: pd.DataFrame, left: int = 15, right: int = 15) -> List[Level]:
    """Niveles ordenados por hora de ACTIVACION. `df` puede traer al final la vela en formacion: solo se usa su hora
    (como activacion), nunca su maximo/minimo."""
    hi = df["high"].values
    lo = df["low"].values
    t = df["time"].values
    n = len(df)
    out: List[Level] = []
    for i in range(left, n - right):
        j = i + right + 1
        if j >= n:
            continue
        w = hi[i - left:i + right + 1]
        if hi[i] == w.max() and w.argmax() == left:
            out.append(Level(t[j], j, float(hi[i]), "res", t[i]))
        w = lo[i - left:i + right + 1]
        if lo[i] == w.min() and w.argmin() == left:
            out.append(Level(t[j], j, float(lo[i]), "sup", t[i]))
    out.sort(key=lambda x: x.activation_time)
    return out
