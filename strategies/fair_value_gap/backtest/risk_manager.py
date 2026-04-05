# -*- coding: utf-8 -*-
"""
Gestion de riesgo: SL, TP, position sizing y P&L normalizado.
(Adaptado de order_block — logica de riesgo identica)
"""

from datetime import datetime, timedelta
from typing import Optional, Tuple
from .fvg_detection import FairValueGap


# --------------------------------------------------------------------------
# SL / TP
# --------------------------------------------------------------------------

def calculate_sl_tp(
    fvg: FairValueGap,
    entry_price: float,
    params: dict,
) -> Tuple[Optional[float], Optional[float]]:
    """
    Calcula SL y TP para un trade dado el FVG y el precio de entrada.

    LONG  (bullish FVG):
      SL = fvg.zone_low  - buffer_points
      TP = entry + risk_points * target_rr

    SHORT (bearish FVG):
      TP = fvg.zone_low  - buffer_points  (debajo de la zona)
      SL = entry + (reward_pts / target_rr)

    Retorna (sl, tp) o (None, None) si no pasa los filtros de riesgo.
    """
    buf       = params["buffer_points"]
    min_risk  = params["min_risk_points"]
    max_risk  = params["max_risk_points"]
    target_rr = params["target_rr"]
    min_rr    = params["min_rr_ratio"]

    if fvg.fvg_type == "bullish":
        # LONG: SL debajo del borde inferior, TP derivado del riesgo
        sl       = fvg.zone_low - buf
        risk_pts = abs(entry_price - sl)
        tp       = entry_price + risk_pts * target_rr
    else:
        # SHORT: SL encima del borde superior, TP derivado del riesgo
        # Simetrico con LONG: siempre funciona sin importar si la entrada
        # es conservadora (close dentro del gap) o agresiva (en zone_low)
        sl       = fvg.zone_high + buf
        risk_pts = abs(sl - entry_price)
        tp       = entry_price - risk_pts * target_rr

    if risk_pts < min_risk:
        return None, None
    if risk_pts > max_risk:
        return None, None

    reward_pts = abs(tp - entry_price)
    rr = reward_pts / risk_pts if risk_pts > 0 else 0
    if rr < min_rr:
        return None, None

    return sl, tp


# --------------------------------------------------------------------------
# P&L normalizado
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

    Formula:
      risk_usd         = balance * risk_per_trade_pct
      planned_risk_pts = abs(entry_price_original - original_sl)
      pnl_points       = exit_price - entry_price  (long)
                       = entry_price - exit_price  (short)
      pnl_points_net   = pnl_points - avg_spread_points
      pnl_usd          = (pnl_points_net / planned_risk_pts) * risk_usd

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
