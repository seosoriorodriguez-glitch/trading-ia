# -*- coding: utf-8 -*-
"""
Generacion de senales de entrada en el timeframe menor.

Dos metodos de entrada (configurables via params["entry_method"]):

  "conservative":
      PASO 1 — Trigger: vela M1 cierra DENTRO del FVG (confirma que precio entro al gap).
      PASO 2 — Stop order: se coloca una orden stop en el BORDE de la zona:
               Bullish FVG (long): stop BUY  en zone_high (espera rebote hacia arriba)
               Bearish FVG (short): stop SELL en zone_low  (espera rechazo hacia abajo)
      PASO 3 — Fill: la orden se llena cuando el precio alcanza ese borde en velas siguientes.
      Si el FVG expira o se destruye antes del fill → orden cancelada.

  "aggressive":
      Precio TOCA la zona → entrada inmediata al borde.
      Bullish FVG: candle.low  <= zone_high → entry = zone_high
      Bearish FVG: candle.high >= zone_low  → entry = zone_low

Filtros adicionales opcionales: rechazo, BOS, EMA tendencia.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional

from .fvg_detection import FairValueGap, FVGStatus
from .risk_manager import calculate_sl_tp, is_session_allowed


@dataclass
class Signal:
    direction:    str
    entry_price:  float
    sl:           float
    tp:           float
    fvg:          FairValueGap
    candle_time:  datetime
    session:      str
    entry_method: str


@dataclass
class PendingStop:
    """
    Orden stop pendiente generada por el trigger conservative.
    Se llena cuando precio alcanza entry_price en velas posteriores.
    """
    direction:    str
    entry_price:  float    # zone_high (long) o zone_low (short)
    sl:           float
    tp:           float
    fvg:          FairValueGap
    trigger_time: datetime
    session:      str


# --------------------------------------------------------------------------
# Filtro 1: Vela de rechazo
# --------------------------------------------------------------------------

def _is_pin_bar(candle: dict, prev_candle: Optional[dict], direction: str, params: dict) -> bool:
    o, h, l, c = candle["open"], candle["high"], candle["low"], candle["close"]
    body        = abs(c - o)
    total_range = h - l
    if total_range == 0:
        return False
    if body > total_range * params["pin_bar_max_body_pct"]:
        return False
    if direction == "long":
        return (min(o, c) - l) >= body * params["pin_bar_wick_ratio"]
    else:
        return (h - max(o, c)) >= body * params["pin_bar_wick_ratio"]


def _is_engulfing(candle: dict, prev_candle: Optional[dict], direction: str, params: dict) -> bool:
    if prev_candle is None:
        return False
    o, c   = candle["open"],      candle["close"]
    po, pc = prev_candle["open"], prev_candle["close"]
    br     = params["engulfing_body_ratio"]
    if direction == "long":
        if c <= o or pc >= po: return False
        return o <= pc and c >= po and abs(c - o) >= abs(pc - po) * br
    else:
        if c >= o or pc <= po: return False
        return o >= pc and c <= po and abs(o - c) >= abs(po - pc) * br


def check_rejection(candle, prev_candle, direction, params) -> bool:
    if not params.get("require_rejection", False):
        return True
    return _is_pin_bar(candle, prev_candle, direction, params) \
        or _is_engulfing(candle, prev_candle, direction, params)


# --------------------------------------------------------------------------
# Filtro 2: BOS
# --------------------------------------------------------------------------

def check_bos(recent_candles: List[dict], direction: str, params: dict) -> bool:
    if not params.get("require_bos", False):
        return True
    lb = params["bos_lookback"]
    if len(recent_candles) < lb:
        return False
    window    = recent_candles[-lb:]
    half      = lb // 2
    structure = window[:half]
    recent    = window[half:]
    if not structure or not recent:
        return False
    if direction == "long":
        return any(c["close"] > max(s["high"] for s in structure) for c in recent)
    else:
        return any(c["close"] < min(s["low"] for s in structure) for c in recent)


# --------------------------------------------------------------------------
# Sesion
# --------------------------------------------------------------------------

def _which_session(dt: datetime, params: dict) -> str:
    for name, sess in params["sessions"].items():
        h_s, m_s = sess["start"].split(":")
        h_e, m_e = sess["end"].split(":")
        sess_start = dt.replace(hour=int(h_s), minute=int(m_s), second=0, microsecond=0)
        sess_end   = dt.replace(hour=int(h_e), minute=int(m_e), second=0, microsecond=0)
        trade_from = sess_start + timedelta(minutes=sess["skip_minutes"])
        if trade_from <= dt < sess_end:
            return name
    return "unknown"


# --------------------------------------------------------------------------
# Conservative: PASO 1 — detectar trigger (M1 cierra dentro del gap)
# --------------------------------------------------------------------------

def check_conservative_trigger(
    candle:         dict,
    prev_candle:    Optional[dict],
    recent_candles: List[dict],
    active_fvgs:    List[FairValueGap],
    params:         dict,
    trend_bias:     Optional[str] = None,
) -> Optional[PendingStop]:
    """
    Detecta si una vela M1 cierra dentro de un FVG activo.
    Si es asi, crea una PendingStop en el borde de la zona (stop order).

    Entry price:
      Bullish FVG (long):  stop BUY  en zone_high
      Bearish FVG (short): stop SELL en zone_low

    Solo crea el pending si el FVG esta FRESH y en sesion permitida.
    """
    candle_time  = candle["time"]
    candle_close = candle["close"]

    if not is_session_allowed(candle_time, params):
        return None

    session = _which_session(candle_time, params)

    candidates = sorted(
        [fvg for fvg in active_fvgs if fvg.status == FVGStatus.FRESH],
        key=lambda f: f.confirmed_at,
        reverse=True,
    )

    for fvg in candidates:
        direction = "long" if fvg.fvg_type == "bullish" else "short"

        if trend_bias is not None and direction != trend_bias:
            continue

        # Trigger: M1 cierra DENTRO del gap
        if not (fvg.zone_low <= candle_close <= fvg.zone_high):
            continue

        # Filtros opcionales en el candle trigger
        if not check_rejection(candle, prev_candle, direction, params):
            continue
        if not check_bos(recent_candles, direction, params):
            continue

        # Precio de la orden stop: borde de la zona
        if direction == "long":
            entry_price = fvg.zone_high   # stop BUY en tope del gap
        else:
            entry_price = fvg.zone_low    # stop SELL en fondo del gap

        # Validar SL/TP con la entry del stop (no la del trigger)
        sl, tp = calculate_sl_tp(fvg, entry_price, params)
        if sl is None:
            continue

        return PendingStop(
            direction    = direction,
            entry_price  = entry_price,
            sl           = sl,
            tp           = tp,
            fvg          = fvg,
            trigger_time = candle_time,
            session      = session,
        )

    return None


# --------------------------------------------------------------------------
# Aggressive: entrada directa al tocar la zona
# --------------------------------------------------------------------------

def check_aggressive_entry(
    candle:         dict,
    prev_candle:    Optional[dict],
    recent_candles: List[dict],
    active_fvgs:    List[FairValueGap],
    n_open_trades:  int,
    params:         dict,
    trend_bias:     Optional[str] = None,
) -> Optional[Signal]:
    """
    Precio toca el borde de la zona → entrada inmediata.
    Bullish FVG: candle.low  <= zone_high → entry = zone_high
    Bearish FVG: candle.high >= zone_low  → entry = zone_low
    """
    candle_time = candle["time"]

    if n_open_trades >= params["max_simultaneous_trades"]:
        return None
    if not is_session_allowed(candle_time, params):
        return None

    session = _which_session(candle_time, params)

    candidates = sorted(
        [fvg for fvg in active_fvgs if fvg.status == FVGStatus.FRESH],
        key=lambda f: f.confirmed_at,
        reverse=True,
    )

    for fvg in candidates:
        direction = "long" if fvg.fvg_type == "bullish" else "short"

        if trend_bias is not None and direction != trend_bias:
            continue

        if direction == "long":
            if candle["low"] > fvg.zone_high:
                continue
            entry_price = fvg.zone_high
        else:
            if candle["high"] < fvg.zone_low:
                continue
            entry_price = fvg.zone_low

        if not check_rejection(candle, prev_candle, direction, params):
            continue
        if not check_bos(recent_candles, direction, params):
            continue

        sl, tp = calculate_sl_tp(fvg, entry_price, params)
        if sl is None:
            continue

        return Signal(
            direction    = direction,
            entry_price  = entry_price,
            sl           = sl,
            tp           = tp,
            fvg          = fvg,
            candle_time  = candle_time,
            session      = session,
            entry_method = "aggressive",
        )

    return None


# --------------------------------------------------------------------------
# Wrapper unificado (mantiene compatibilidad con backtester)
# --------------------------------------------------------------------------

def check_entry(
    candle:         dict,
    prev_candle:    Optional[dict],
    recent_candles: List[dict],
    active_fvgs:    List[FairValueGap],
    n_open_trades:  int,
    params:         dict,
    balance:        float,
    trend_bias:     Optional[str] = None,
) -> Optional[Signal]:
    """Solo para aggressive. Conservative usa check_conservative_trigger + fill en backtester."""
    if params.get("entry_method", "conservative") == "aggressive":
        return check_aggressive_entry(
            candle, prev_candle, recent_candles, active_fvgs,
            n_open_trades, params, trend_bias,
        )
    return None
