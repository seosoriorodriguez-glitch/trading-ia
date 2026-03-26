"""
Análisis de tendencia para filtrado de señales.

Implementa EMA y otros indicadores de tendencia.
"""

import logging
from typing import List, Optional
from core.market_data import Candle

logger = logging.getLogger(__name__)


def calculate_ema(candles: List[Candle], period: int) -> Optional[float]:
    """
    Calcula la EMA (Exponential Moving Average) para un período dado.
    
    Args:
        candles: Lista de velas ordenadas cronológicamente
        period: Período de la EMA (ej: 200)
    
    Returns:
        Valor actual de la EMA o None si no hay suficientes datos
    """
    if len(candles) < period:
        return None
    
    # Calcular SMA inicial (primeros 'period' valores)
    closes = [c.close for c in candles]
    sma = sum(closes[:period]) / period
    
    # Calcular EMA desde el período en adelante
    multiplier = 2.0 / (period + 1)
    ema = sma
    
    for i in range(period, len(closes)):
        ema = (closes[i] - ema) * multiplier + ema
    
    return ema


def is_price_above_ema(price: float, ema: float, neutral_zone_pct: float = 0.005) -> Optional[bool]:
    """
    Determina si el precio está por encima, por debajo, o en zona neutral de la EMA.
    
    Args:
        price: Precio actual
        ema: Valor de la EMA
        neutral_zone_pct: Porcentaje de zona neutral (default: 0.5%)
    
    Returns:
        True si está por encima, False si está por debajo, None si está en zona neutral
    """
    upper_bound = ema * (1 + neutral_zone_pct)
    lower_bound = ema * (1 - neutral_zone_pct)
    
    if price > upper_bound:
        return True
    elif price < lower_bound:
        return False
    else:
        return None  # Zona neutral


def should_allow_signal(
    direction: str,
    price: float,
    ema_200: Optional[float],
    zone_touches: int,
    trend_config: dict
) -> tuple[bool, str]:
    """
    Determina si una señal debe permitirse basado en el filtro de tendencia.
    
    Args:
        direction: "LONG" o "SHORT"
        price: Precio actual
        ema_200: Valor de EMA 200 (None si no disponible)
        zone_touches: Número de toques de la zona
        trend_config: Configuración del filtro de tendencia
    
    Returns:
        (permitido: bool, razón: str)
    """
    if not trend_config.get("enabled", False):
        return (True, "trend_filter_disabled")
    
    if ema_200 is None:
        return (True, "ema_not_available")
    
    neutral_zone_pct = trend_config.get("neutral_zone_pct", 0.005)
    counter_trend_min_touches = trend_config.get("counter_trend_min_touches", 3)
    
    price_position = is_price_above_ema(price, ema_200, neutral_zone_pct)
    
    # Zona neutral - permitir ambas direcciones
    if price_position is None:
        return (True, "neutral_zone")
    
    # Precio por encima de EMA (tendencia alcista)
    if price_position:
        if direction == "LONG":
            return (True, "with_trend")
        else:  # SHORT
            if zone_touches >= counter_trend_min_touches:
                return (True, "counter_trend_strong_zone")
            else:
                return (False, "counter_trend_weak_zone")
    
    # Precio por debajo de EMA (tendencia bajista)
    else:
        if direction == "SHORT":
            return (True, "with_trend")
        else:  # LONG
            if zone_touches >= counter_trend_min_touches:
                return (True, "counter_trend_strong_zone")
            else:
                return (False, "counter_trend_weak_zone")


def get_trend_summary(price: float, ema_200: Optional[float]) -> str:
    """
    Retorna un resumen legible de la tendencia actual.
    
    Returns:
        "ALCISTA", "BAJISTA", "NEUTRAL", o "DESCONOCIDA"
    """
    if ema_200 is None:
        return "DESCONOCIDA"
    
    position = is_price_above_ema(price, ema_200)
    
    if position is None:
        return "NEUTRAL"
    elif position:
        return "ALCISTA"
    else:
        return "BAJISTA"
