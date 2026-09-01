# -*- coding: utf-8 -*-
"""
Deteccion de niveles S/R por pivotes (equivalente Python del LuxAlgo Pine).

Pine original:
    highUsePivot = fixnan(pivothigh(leftBars, rightBars)[1])
    lowUsePivot  = fixnan(pivotlow(leftBars, rightBars)[1])
    plot(..., offset=-(rightBars+1))

EL PUNTO CRITICO — POR QUE EL INDICADOR REPINTA
  pivothigh(15,15) pregunta si el high de la vela i es mayor que las 15 anteriores
  Y las 15 POSTERIORES. Esas 15 posteriores no existen cuando se forma la vela.
  El nivel solo se conoce en la barra i + right (+1 por el [1] del Pine).

  El `offset=-(rightBars+1)` del plot dibuja la linea hacia atras hasta la vela
  del pivote, por eso en el chart PARECE que el nivel estuvo ahi desde el
  principio. En vivo no lo tenias.

  Medido sobre US30 H1 (2024-10 a 2026-03), W=30 SL=100 RR=1.5:
      con lookahead (nivel desde la vela del pivote): WR 94.8%  E=+1.369R  t=+51.4
      sin lookahead (nivel en pivote+16):             WR 42.5%  E=+0.061R  t=+0.88

  Un pivothigh ES por definicion el maximo de las 15 velas siguientes: vender ahi
  con lookahead es dinero gratis. Por eso `activation_index = i + right + 1`.
"""
from typing import List, NamedTuple

import pandas as pd


class Level(NamedTuple):
    activation_time: pd.Timestamp   # cuando el nivel pasa a ser operable
    activation_index: int           # indice de barra de activacion
    price: float                    # high del pivote (res) o low (sup)
    kind: str                       # "sup" | "res"
    pivot_time: pd.Timestamp        # cuando se formo el pivote (solo informativo)


def resample_tf(m1: pd.DataFrame, minutes: int) -> pd.DataFrame:
    """Construye el TF de deteccion desde M1."""
    if minutes == 1:
        return m1.reset_index(drop=True)
    return (m1.set_index("time")
              .resample(f"{minutes}min", label="left", closed="left")
              .agg({"open": "first", "high": "max", "low": "min", "close": "last"})
              .dropna().reset_index())


def find_levels(df: pd.DataFrame, left: int = 15, right: int = 15) -> List[Level]:
    """
    Devuelve los niveles ordenados por hora de ACTIVACION (no de formacion).

    Un pivote en la barra i se activa en la barra i + right + 1. Nunca antes.
    """
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
