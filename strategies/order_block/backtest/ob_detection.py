# -*- coding: utf-8 -*-
"""
Deteccion de Order Blocks en el timeframe mayor.

Bullish OB:
  - Vela bajista (close < open)
  - Siguientes N velas son TODAS alcistas (close > open)
  - Movimiento total >= min_impulse_pct %
  - Zona: [low, open]  si zone_type="half_candle"
          [low, high]  si zone_type="full_candle"
  - Zona size <= ATR(14) * max_atr_mult

Bearish OB:
  - Vela alcista (close > open)
  - Siguientes N velas son TODAS bajistas (close < open)
  - Movimiento total >= min_impulse_pct %
  - Zona: [open, high] si zone_type="half_candle"
          [low, high]  si zone_type="full_candle"

ANTI LOOK-AHEAD:
  confirmed_at = open_time de la vela que sigue al cierre de la ultima vela
  de la secuencia (= cuando el mercado ya conoce que la secuencia completo).
  El backtester solo activa el OB cuando current_time >= confirmed_at.
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


class OBStatus:
    FRESH     = "fresh"       # Confirmado, esperando primer retorno
    MITIGATED = "mitigated"   # Primer retorno ocurrio (se tomo o desecho el trade)
    DESTROYED = "destroyed"   # Precio cerro al otro lado del extremo de la zona
    EXPIRED   = "expired"     # Llego a expiry_candles sin ser tocado


@dataclass
class OrderBlock:
    ob_type:        str           # "bullish" o "bearish"
    zone_high:      float
    zone_low:       float
    confirmed_at:   datetime      # cuando el OB se vuelve operable
    ob_candle_time: datetime      # tiempo de la vela que forma el OB
    ob_candle_idx:  int           # indice en df_higher (para expiry)
    status:         str = field(default=OBStatus.FRESH)
    # Cuantas velas del TF mayor han pasado desde confirmed_at (para expiry)
    candles_since_confirm: int = 0


def _compute_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """ATR(period) clasico."""
    high  = df["high"]
    low   = df["low"]
    prev_close = df["close"].shift(1)

    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low  - prev_close).abs(),
    ], axis=1).max(axis=1)

    return tr.rolling(period, min_periods=1).mean()


def detect_order_blocks(df: pd.DataFrame, params: dict) -> List[OrderBlock]:
    """
    Detecta todos los Order Blocks en df (timeframe mayor).

    Args:
        df:     DataFrame con columnas time,open,high,low,close (TF mayor).
        params: Dict de parametros de la estrategia.

    Returns:
        Lista de OrderBlock ordenados por confirmed_at.
    """
    n          = params["consecutive_candles"]
    min_imp    = params["min_impulse_pct"]
    zone_type  = params["zone_type"]
    max_atr_m  = params["max_atr_mult"]

    atr = _compute_atr(df)
    obs: List[OrderBlock] = []

    # Necesitamos: OB candle (i) + N consecutivas (i+1..i+N) + la siguiente (i+N+1)
    # La siguiente es para obtener confirmed_at sin look-ahead
    limit = len(df) - n - 1

    for i in range(limit):
        ob_candle = df.iloc[i]
        window    = df.iloc[i + 1: i + 1 + n]   # las N velas siguientes
        # confirmed_at = apertura de la vela que abre DESPUES del cierre de la N-esima
        # = df.iloc[i + n + 1]["time"]  (cuando el mercado "sabe" que la secuencia cerro)
        confirmed_at = df.iloc[i + n + 1]["time"]

        atr_val = atr.iloc[i]
        if pd.isna(atr_val) or atr_val == 0:
            continue

        # ----------------------------------------------------------------
        # Bullish OB: vela bajista + N alcistas
        # ----------------------------------------------------------------
        if ob_candle["close"] < ob_candle["open"]:
            if not (window["close"] > window["open"]).all():
                continue

            # Impulso total: desde el close del OB hasta el close de la ultima vela
            impulse_pct = (window.iloc[-1]["close"] - ob_candle["close"]) / ob_candle["close"]
            if impulse_pct < min_imp:
                continue

            if zone_type == "half_candle":
                zone_low  = ob_candle["low"]
                zone_high = ob_candle["open"]
            else:
                zone_low  = ob_candle["low"]
                zone_high = ob_candle["high"]

            if zone_high - zone_low > atr_val * max_atr_m:
                continue

            obs.append(OrderBlock(
                ob_type        = "bullish",
                zone_high      = zone_high,
                zone_low       = zone_low,
                confirmed_at   = confirmed_at,
                ob_candle_time = ob_candle["time"],
                ob_candle_idx  = i,
            ))

        # ----------------------------------------------------------------
        # Bearish OB: vela alcista + N bajistas
        # ----------------------------------------------------------------
        elif ob_candle["close"] > ob_candle["open"]:
            if not (window["close"] < window["open"]).all():
                continue

            impulse_pct = (ob_candle["close"] - window.iloc[-1]["close"]) / ob_candle["close"]
            if impulse_pct < min_imp:
                continue

            if zone_type == "half_candle":
                zone_low  = ob_candle["open"]
                zone_high = ob_candle["high"]
            else:
                zone_low  = ob_candle["low"]
                zone_high = ob_candle["high"]

            if zone_high - zone_low > atr_val * max_atr_m:
                continue

            obs.append(OrderBlock(
                ob_type        = "bearish",
                zone_high      = zone_high,
                zone_low       = zone_low,
                confirmed_at   = confirmed_at,
                ob_candle_time = ob_candle["time"],
                ob_candle_idx  = i,
            ))

    obs.sort(key=lambda o: o.confirmed_at)
    return obs
