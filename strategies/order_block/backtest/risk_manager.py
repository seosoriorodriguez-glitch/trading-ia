# -*- coding: utf-8 -*-
"""
Gestion de riesgo: SL, TP, position sizing y P&L normalizado.
"""

from datetime import datetime, time as dtime
from typing import Optional, Tuple
from .ob_detection import OrderBlock


# --------------------------------------------------------------------------
# SL / TP
# --------------------------------------------------------------------------

def calculate_sl_tp(
    ob: OrderBlock,
    entry_price: float,
    params: dict,
) -> Tuple[Optional[float], Optional[float]]:
    """
    Calcula SL y TP para un trade dado el OB y el precio de entrada.

    SL:
      LONG:  ob.zone_low  - buffer_points (debajo del entry)
      SHORT: entry + risk_points * target_rr (arriba del entry)

    TP:
      LONG:  entry + risk_points * target_rr (arriba del entry)
      SHORT: ob.zone_high + buffer_points (debajo del entry)

    Retorna (sl, tp) o (None, None) si no pasa los filtros de riesgo.
    """
    buf         = params["buffer_points"]
    min_risk    = params["min_risk_points"]
    max_risk    = params["max_risk_points"]
    target_rr   = params["target_rr"]
    min_rr      = params["min_rr_ratio"]

    if ob.ob_type == "bullish":
        # LONG: SL debajo, TP arriba
        sl = ob.zone_low - buf
        risk_pts = abs(entry_price - sl)
        tp = entry_price + risk_pts * target_rr
    else:
        # SHORT: TP debajo, SL arriba (CORREGIDO)
        tp = ob.zone_low - buf  # TP debajo de la zona
        reward_pts = abs(entry_price - tp)
        risk_pts = reward_pts / target_rr  # Risk para lograr el target_rr deseado
        sl = entry_price + risk_pts

    # Validar filtros de riesgo
    if risk_pts < min_risk:
        return None, None
    if risk_pts > max_risk:
        return None, None

    # Validar R:R mínimo
    reward_pts = abs(tp - entry_price)
    rr = reward_pts / risk_pts if risk_pts > 0 else 0
    if rr < min_rr:
        return None, None

    return sl, tp


# --------------------------------------------------------------------------
# P&L normalizado (CRITICO)
# --------------------------------------------------------------------------

def calc_pnl(
    entry_price: float,
    exit_price: float,
    original_sl: float,
    entry_price_original: float,
    direction: str,
    balance: float,
    params: dict,
) -> Tuple[float, float, float]:
    """
    Calcula P&L normalizado.

    Formula (de la especificacion):
      risk_usd         = balance * risk_per_trade_pct
      planned_risk_pts = abs(entry_price_original - original_sl)
      pnl_points       = exit_price - entry_price  (long)
                       = entry_price - exit_price  (short)
      pnl_points_net   = pnl_points - avg_spread_points
      pnl_usd          = (pnl_points_net / planned_risk_pts) * risk_usd

    NUNCA usar lot_size * points directamente.

    Returns:
        (pnl_usd, pnl_r, pnl_points_net)
    """
    risk_usd         = balance * params["risk_per_trade_pct"]
    planned_risk_pts = abs(entry_price_original - original_sl)

    if planned_risk_pts == 0:
        return 0.0, 0.0, 0.0

    if direction == "long":
        pnl_pts = exit_price - entry_price
    else:
        pnl_pts = entry_price - exit_price

    pnl_pts_net = pnl_pts - params["avg_spread_points"]
    pnl_usd     = (pnl_pts_net / planned_risk_pts) * risk_usd
    pnl_r       = pnl_pts_net / planned_risk_pts

    return pnl_usd, pnl_r, pnl_pts_net


# --------------------------------------------------------------------------
# Filtro horario
# --------------------------------------------------------------------------

def is_session_allowed(dt: datetime, params: dict) -> bool:
    """
    Retorna True si dt cae en una sesion permitida (y no en los primeros skip_minutes).
    Solo lunes-viernes (weekday 0-4).
    """
    from datetime import timedelta

    if dt.weekday() >= 5:
        return False

    for sess in params["sessions"].values():
        h_start, m_start = sess["start"].split(":")
        h_end,   m_end   = sess["end"].split(":")

        sess_start = dt.replace(hour=int(h_start), minute=int(m_start), second=0, microsecond=0)
        sess_end   = dt.replace(hour=int(h_end),   minute=int(m_end),   second=0, microsecond=0)
        trade_from = sess_start + timedelta(minutes=sess["skip_minutes"])

        if trade_from <= dt < sess_end:
            return True

    return False
