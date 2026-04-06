# -*- coding: utf-8 -*-
"""
Deteccion de Fair Value Gaps (FVG) — logica identica a LuxAlgo FVG indicator.

Referencia Pine Script (LuxAlgo):
  bull_fvg = low > high[2] and close[1] > high[2] and (low - high[2]) / high[2] > threshold
  bear_fvg = high < low[2] and close[1] < low[2]  and (low[2] - high)  / high   > threshold

Donde en Pine Script, barra actual = [0], barra anterior = [1], 2 barras atras = [2].

Traducido a Python (iterando con `i` = indice de la vela CENTRAL/impulsiva):
  - ref   = df.iloc[i-1]   # barra [2] de Pine (la mas antigua)
  - mid   = df.iloc[i]     # barra [1] de Pine (vela central / impulsiva)
  - curr  = df.iloc[i+1]   # barra [0] de Pine (la que confirma el gap)

Bullish FVG (gap alcista):
  - curr.low  > ref.high                          (hay espacio = gap)
  - mid.close > ref.high                          (vela central cierra por encima)
  - (curr.low - ref.high) / ref.high > threshold  (tamano del gap supera umbral %)
  - zone_high = curr.low   (borde superior del gap)
  - zone_low  = ref.high   (borde inferior del gap)

Bearish FVG (gap bajista):
  - curr.high < ref.low                           (hay espacio = gap)
  - mid.close < ref.low                           (vela central cierra por debajo)
  - (ref.low - curr.high) / curr.high > threshold (tamano del gap supera umbral %)
  - zone_high = ref.low    (borde superior del gap)
  - zone_low  = curr.high  (borde inferior del gap)

Mitigacion (igual que LuxAlgo):
  - Bullish mitigado: close < zone_low  (precio cierra por DEBAJO del borde inferior)
  - Bearish mitigado: close > zone_high (precio cierra por ENCIMA del borde superior)

ANTI LOOK-AHEAD:
  confirmed_at = time de `curr` (la tercera vela del patron).
  El backtester activa el FVG cuando current_time >= confirmed_at,
  es decir, a partir del SIGUIENTE tick/vela despues de que el patron se forma.
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List


class FVGStatus:
    FRESH     = "fresh"       # Confirmado, esperando primer retorno al gap
    MITIGATED = "mitigated"   # Precio regreso al gap (trade tomado o descartado)
    DESTROYED = "destroyed"   # Precio cerro al otro lado del extremo del gap
    EXPIRED   = "expired"     # Llego a expiry_candles sin ser tocado


@dataclass
class FairValueGap:
    fvg_type:        str       # "bullish" o "bearish"
    zone_high:       float     # Borde SUPERIOR del gap
    zone_low:        float     # Borde INFERIOR del gap
    confirmed_at:    datetime  # Cuando el FVG es operable (tiempo de la 3ra vela)
    fvg_candle_time: datetime  # Tiempo de la vela central/impulsiva
    fvg_candle_idx:  int       # Indice de la vela central en df_higher
    status:          str = field(default=FVGStatus.FRESH)
    candles_since_confirm: int = 0


def _compute_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """ATR(period) clasico."""
    high       = df["high"]
    low        = df["low"]
    prev_close = df["close"].shift(1)

    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low  - prev_close).abs(),
    ], axis=1).max(axis=1)

    return tr.rolling(period, min_periods=1).mean()


def detect_fvgs(df: pd.DataFrame, params: dict) -> List[FairValueGap]:
    """
    Detecta todos los Fair Value Gaps en df (timeframe mayor).
    Logica exactamente igual al indicador LuxAlgo FVG.

    Args:
        df:     DataFrame con columnas time,open,high,low,close (TF mayor).
        params: Dict de parametros de la estrategia.

    Returns:
        Lista de FairValueGap ordenados por confirmed_at.
    """
    threshold     = params.get("threshold_pct",   0.0) / 100.0   # 0 = sin filtro (default LuxAlgo)
    max_atr_m     = params.get("max_atr_mult",    3.5)            # Filtro adicional de tamano maximo
    min_zone_pts  = params.get("min_zone_points", 0.0)            # Tamano minimo absoluto del gap (pts)

    atr  = _compute_atr(df)
    fvgs: List[FairValueGap] = []

    # Inferir duracion de 1 vela del TF mayor para calcular el cierre
    if len(df) >= 2:
        dt0 = pd.Timestamp(df.iloc[0]["time"])
        dt1 = pd.Timestamp(df.iloc[1]["time"])
        candle_duration = dt1 - dt0
    else:
        candle_duration = timedelta(minutes=5)

    # Patron de 3 velas: ref=[i-1], mid=[i], curr=[i+1]
    # Necesitamos curr=[i+1], asi que iteramos hasta len-2
    limit = len(df) - 1

    for i in range(1, limit):
        ref  = df.iloc[i - 1]   # barra [2] de Pine: referencia
        mid  = df.iloc[i]       # barra [1] de Pine: vela impulsiva central
        curr = df.iloc[i + 1]   # barra [0] de Pine: confirma el gap

        # confirmed_at = CIERRE de curr (la 3ra vela del patron).
        # El FVG solo es operable DESPUES de que la vela confirmadora cierra,
        # porque zone_high/zone_low dependen del high/low final de curr.
        confirmed_at = curr["time"] + candle_duration

        atr_val = atr.iloc[i]
        if pd.isna(atr_val) or atr_val == 0:
            continue

        # ----------------------------------------------------------------
        # Bullish FVG
        # ----------------------------------------------------------------
        if (curr["low"] > ref["high"]                              # gap existe
                and mid["close"] > ref["high"]                     # vela central confirma
                and (curr["low"] - ref["high"]) / ref["high"] > threshold):  # threshold %

            zone_low  = ref["high"]    # borde inferior = high de la vela de referencia
            zone_high = curr["low"]    # borde superior = low de la vela confirmadora

            gap_size = zone_high - zone_low
            if gap_size > atr_val * max_atr_m:   # filtro tamano maximo
                continue
            if gap_size < min_zone_pts:           # filtro tamano minimo absoluto
                continue

            fvgs.append(FairValueGap(
                fvg_type        = "bullish",
                zone_high       = zone_high,
                zone_low        = zone_low,
                confirmed_at    = confirmed_at,
                fvg_candle_time = mid["time"],
                fvg_candle_idx  = i,
            ))

        # ----------------------------------------------------------------
        # Bearish FVG
        # ----------------------------------------------------------------
        elif (curr["high"] < ref["low"]                             # gap existe
                and mid["close"] < ref["low"]                       # vela central confirma
                and (ref["low"] - curr["high"]) / curr["high"] > threshold):  # threshold %

            zone_low  = curr["high"]   # borde inferior = high de la vela confirmadora
            zone_high = ref["low"]     # borde superior = low de la vela de referencia

            gap_size = zone_high - zone_low
            if gap_size > atr_val * max_atr_m:
                continue
            if gap_size < min_zone_pts:
                continue

            fvgs.append(FairValueGap(
                fvg_type        = "bearish",
                zone_high       = zone_high,
                zone_low        = zone_low,
                confirmed_at    = confirmed_at,
                fvg_candle_time = mid["time"],
                fvg_candle_idx  = i,
            ))

    fvgs.sort(key=lambda f: f.confirmed_at)
    return fvgs
