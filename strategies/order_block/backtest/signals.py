# -*- coding: utf-8 -*-
"""
Generacion de senales de entrada en el timeframe menor.

Filtros aplicados (configurables):
  1. Rejection candle: pin bar o engulfing en la direccion del OB.
  2. BOS (Break of Structure): cierre reciente que rompio la estructura
     en la direccion del OB antes de entrar.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from .ob_detection import OrderBlock, OBStatus
from .risk_manager import calculate_sl_tp, is_session_allowed


@dataclass
class Signal:
    direction:    str
    entry_price:  float
    sl:           float
    tp:           float
    ob:           OrderBlock
    candle_time:  datetime
    session:      str


# --------------------------------------------------------------------------
# Filtro 1: Vela de rechazo
# --------------------------------------------------------------------------

def _is_pin_bar(candle: dict, prev_candle: Optional[dict], direction: str, params: dict) -> bool:
    """
    Pin bar en la direccion correcta.

    Bullish (long): mecha inferior larga, cuerpo pequeno arriba.
    Bearish (short): mecha superior larga, cuerpo pequeno abajo.
    """
    o, h, l, c = candle["open"], candle["high"], candle["low"], candle["close"]
    body        = abs(c - o)
    total_range = h - l
    if total_range == 0:
        return False

    wick_ratio   = params["pin_bar_wick_ratio"]
    max_body_pct = params["pin_bar_max_body_pct"]

    if body > total_range * max_body_pct:
        return False  # cuerpo demasiado grande

    if direction == "long":
        lower_wick = min(o, c) - l
        return lower_wick >= body * wick_ratio
    else:
        upper_wick = h - max(o, c)
        return upper_wick >= body * wick_ratio


def _is_engulfing(candle: dict, prev_candle: Optional[dict], direction: str, params: dict) -> bool:
    """
    Engulfing en la direccion correcta.

    Bullish: vela alcista cuyo cuerpo engloba el cuerpo de la vela anterior bajista.
    Bearish: vela bajista cuyo cuerpo engloba el cuerpo de la vela anterior alcista.
    """
    if prev_candle is None:
        return False

    o,  c  = candle["open"],      candle["close"]
    po, pc = prev_candle["open"], prev_candle["close"]

    body_ratio = params["engulfing_body_ratio"]

    if direction == "long":
        if c <= o:              # vela actual no es alcista
            return False
        if pc >= po:            # vela anterior no es bajista
            return False
        # cuerpo actual engloba cuerpo anterior
        return o <= pc and c >= po and abs(c - o) >= abs(pc - po) * body_ratio

    else:  # short
        if c >= o:              # vela actual no es bajista
            return False
        if pc <= po:            # vela anterior no es alcista
            return False
        return o >= pc and c <= po and abs(o - c) >= abs(po - pc) * body_ratio


def check_rejection(
    candle: dict,
    prev_candle: Optional[dict],
    direction: str,
    params: dict,
) -> bool:
    """Retorna True si la vela muestra pin bar O engulfing en la direccion dada."""
    if not params.get("require_rejection", False):
        return True
    return (
        _is_pin_bar(candle, prev_candle, direction, params)
        or _is_engulfing(candle, prev_candle, direction, params)
    )


# --------------------------------------------------------------------------
# Filtro 2: BOS — Break of Structure
# --------------------------------------------------------------------------

def check_bos(
    recent_candles: List[dict],
    direction: str,
    params: dict,
) -> bool:
    """
    Verifica si hubo un Break of Structure reciente en la direccion dada.

    Algoritmo:
      - Toma las ultimas `bos_lookback` velas del TF menor.
      - Divide en dos mitades: "estructura" (primera mitad) y "reciente" (segunda).
      - BOS bullish: alguna vela de la segunda mitad cerro SOBRE el maximo de la primera.
      - BOS bearish: alguna vela de la segunda mitad cerro BAJO el minimo de la primera.

    Esto confirma que el mercado rompio estructura en la direccion del OB
    antes de regresar a el, dando mayor probabilidad de que el nivel se respete.
    """
    if not params.get("require_bos", False):
        return True

    lb = params["bos_lookback"]
    if len(recent_candles) < lb:
        return False  # no hay suficiente historia

    window    = recent_candles[-lb:]
    half      = lb // 2
    structure = window[:half]   # primera mitad: define la estructura
    recent    = window[half:]   # segunda mitad: el BOS debe ocurrir aqui

    if not structure or not recent:
        return False

    if direction == "long":
        structure_high = max(c["high"] for c in structure)
        return any(c["close"] > structure_high for c in recent)
    else:
        structure_low = min(c["low"] for c in structure)
        return any(c["close"] < structure_low for c in recent)


# --------------------------------------------------------------------------
# Generacion de senales
# --------------------------------------------------------------------------

def _which_session(dt: datetime, params: dict) -> str:
    from datetime import timedelta
    for name, sess in params["sessions"].items():
        h_s, m_s = sess["start"].split(":")
        h_e, m_e = sess["end"].split(":")
        sess_start = dt.replace(hour=int(h_s), minute=int(m_s), second=0, microsecond=0)
        sess_end   = dt.replace(hour=int(h_e), minute=int(m_e), second=0, microsecond=0)
        trade_from = sess_start + timedelta(minutes=sess["skip_minutes"])
        if trade_from <= dt < sess_end:
            return name
    return "unknown"


def check_entry(
    candle:         dict,
    prev_candle:    Optional[dict],
    recent_candles: List[dict],
    active_obs:     List[OrderBlock],
    n_open_trades:  int,
    params:         dict,
    balance:        float,
    trend_bias:     Optional[str] = None,   # "long", "short" o None (sin filtro)
) -> Optional[Signal]:
    """
    Verifica si la vela actual genera una senal de entrada valida.

    Orden de filtros:
      1. Horario de sesion
      2. Max trades abiertos
      3. Zona del OB tocada (close entra en zona)
      4. Vela de rechazo (pin bar / engulfing)
      5. BOS en la direccion del OB
      6. Validacion de SL/TP (riesgo min/max y R:R)
    """
    candle_time  = candle["time"]
    candle_close = candle["close"]

    if n_open_trades >= params["max_simultaneous_trades"]:
        return None
    if not is_session_allowed(candle_time, params):
        return None

    session = _which_session(candle_time, params)

    candidates = sorted(
        [ob for ob in active_obs if ob.status == OBStatus.FRESH],
        key=lambda o: o.confirmed_at,
        reverse=True,
    )

    for ob in candidates:
        if ob.ob_type == "bullish":
            if candle_close > ob.zone_high:
                continue
            direction = "long"
        else:
            if candle_close < ob.zone_low:
                continue
            direction = "short"

        # Filtro de tendencia EMA 4H
        if trend_bias is not None and direction != trend_bias:
            continue

        # Filtro 1: vela de rechazo
        if not check_rejection(candle, prev_candle, direction, params):
            continue

        # Filtro 2: BOS
        if not check_bos(recent_candles, direction, params):
            continue

        # Validar SL/TP
        sl, tp = calculate_sl_tp(ob, candle_close, params)
        if sl is None:
            continue

        return Signal(
            direction   = direction,
            entry_price = candle_close,
            sl          = sl,
            tp          = tp,
            ob          = ob,
            candle_time = candle_time,
            session     = session,
        )

    return None
