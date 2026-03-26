"""
Detección de Señales de Entrada.

Evalúa velas H1 contra zonas activas para generar señales de trading.
Tipos de señal:
  - Tipo A: Pin bar o envolvente en zona (estándar)
  - Tipo B1: Falso quiebre intra-vela (premium, mayor probabilidad)
  - Tipo B2: Falso quiebre en 2 velas (respaldo)
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
from enum import Enum

from core.market_data import Candle
from core.levels import Zone, ZoneType, find_next_opposite_zone

logger = logging.getLogger(__name__)


class SignalType(Enum):
    PIN_BAR = "pin_bar"
    ENGULFING = "engulfing"
    FALSE_BREAKOUT_B1 = "false_breakout_b1"
    FALSE_BREAKOUT_B2 = "false_breakout_b2"


class Direction(Enum):
    LONG = "LONG"
    SHORT = "SHORT"


@dataclass
class Signal:
    """Señal de trading generada."""
    timestamp: datetime
    instrument: str
    direction: Direction
    signal_type: SignalType
    zone: Zone
    entry_price: float
    stop_loss: float
    take_profit: float
    risk_reward_ratio: float
    confidence: float                  # 0-1, basado en tipo de señal y fuerza de zona

    def __repr__(self) -> str:
        return (f"Signal({self.direction.value} {self.instrument} @ {self.entry_price:.1f} | "
                f"SL: {self.stop_loss:.1f} | TP: {self.take_profit:.1f} | "
                f"R:R {self.risk_reward_ratio:.2f} | {self.signal_type.value})")


# ============================================================
# Detección de patrones de velas H1
# ============================================================

def is_pin_bar_bullish(candle: Candle, config: dict) -> bool:
    """
    Pin bar alcista (martillo): mecha inferior larga, cierre en mitad superior.
    Señal de compra en soporte.
    """
    if candle.range_size == 0:
        return False

    min_ratio = config.get("min_wick_to_body_ratio", 2.0)

    # Mecha inferior >= 2x el cuerpo
    if candle.body_size == 0:
        has_wick_ratio = candle.lower_wick > 0
    else:
        has_wick_ratio = candle.lower_wick / candle.body_size >= min_ratio

    # Cierre en mitad superior del rango
    mid = (candle.high + candle.low) / 2
    close_in_upper = candle.close >= mid

    return has_wick_ratio and close_in_upper


def is_pin_bar_bearish(candle: Candle, config: dict) -> bool:
    """
    Pin bar bajista (estrella fugaz): mecha superior larga, cierre en mitad inferior.
    Señal de venta en resistencia.
    """
    if candle.range_size == 0:
        return False

    min_ratio = config.get("min_wick_to_body_ratio", 2.0)

    if candle.body_size == 0:
        has_wick_ratio = candle.upper_wick > 0
    else:
        has_wick_ratio = candle.upper_wick / candle.body_size >= min_ratio

    mid = (candle.high + candle.low) / 2
    close_in_lower = candle.close <= mid

    return has_wick_ratio and close_in_lower


def is_bullish_engulfing(current: Candle, previous: Candle) -> bool:
    """
    Envolvente alcista: vela verde cuyo cuerpo envuelve el cuerpo de la roja anterior.
    """
    if not current.is_bullish or not previous.is_bearish:
        return False

    current_body_low = min(current.open, current.close)
    current_body_high = max(current.open, current.close)
    prev_body_low = min(previous.open, previous.close)
    prev_body_high = max(previous.open, previous.close)

    return current_body_low <= prev_body_low and current_body_high >= prev_body_high


def is_bearish_engulfing(current: Candle, previous: Candle) -> bool:
    """
    Envolvente bajista: vela roja cuyo cuerpo envuelve el cuerpo de la verde anterior.
    """
    if not current.is_bearish or not previous.is_bullish:
        return False

    current_body_low = min(current.open, current.close)
    current_body_high = max(current.open, current.close)
    prev_body_low = min(previous.open, previous.close)
    prev_body_high = max(previous.open, previous.close)

    return current_body_low <= prev_body_low and current_body_high >= prev_body_high


def is_false_breakout_b1_support(candle: Candle, zone: Zone, config: dict) -> bool:
    """
    Falso quiebre B1 alcista (intra-vela):
    - La mecha perfora por debajo del soporte
    - El cierre queda dentro de la zona o por encima
    - Cuerpo fuerte en dirección alcista
    - Penetración mínima para confirmar barrido de liquidez
    """
    min_body = config.get("b1_min_body_ratio", 0.40)
    min_penetration = config.get("b1_min_penetration_points", 0)

    # Mecha penetra por debajo
    penetrates = candle.low < zone.lower
    
    # Verificar penetración mínima
    penetration_distance = zone.lower - candle.low
    has_min_penetration = penetration_distance >= min_penetration

    # Cierre dentro o por encima de la zona
    closes_inside = candle.close >= zone.lower

    # Vela alcista con cuerpo fuerte
    is_strong = candle.is_bullish and candle.body_ratio >= min_body

    return penetrates and has_min_penetration and closes_inside and is_strong


def is_false_breakout_b1_resistance(candle: Candle, zone: Zone, config: dict) -> bool:
    """
    Falso quiebre B1 bajista (intra-vela):
    - La mecha perfora por encima de la resistencia
    - El cierre queda dentro de la zona o por debajo
    - Cuerpo fuerte en dirección bajista
    - Penetración mínima para confirmar barrido de liquidez
    """
    min_body = config.get("b1_min_body_ratio", 0.40)
    min_penetration = config.get("b1_min_penetration_points", 0)

    penetrates = candle.high > zone.upper
    
    # Verificar penetración mínima
    penetration_distance = candle.high - zone.upper
    has_min_penetration = penetration_distance >= min_penetration
    
    closes_inside = candle.close <= zone.upper
    is_strong = candle.is_bearish and candle.body_ratio >= min_body

    return penetrates and has_min_penetration and closes_inside and is_strong


def is_false_breakout_b2_support(
    candles: List[Candle], zone: Zone, config: dict
) -> bool:
    """
    Falso quiebre B2 alcista (2 velas):
    - Primera vela penetra el soporte
    - Segunda vela cierra con fuerza de vuelta por encima
    """
    if len(candles) < 2:
        return False

    prev = candles[-2]
    current = candles[-1]
    min_body = config.get("b2_min_body_ratio", 0.50)

    # Primera vela penetra (mecha o cierre por debajo)
    prev_penetrates = prev.low < zone.lower

    # Segunda vela cierra por encima con fuerza
    current_recovers = current.close >= zone.lower
    current_strong = current.is_bullish and current.body_ratio >= min_body

    return prev_penetrates and current_recovers and current_strong


def is_false_breakout_b2_resistance(
    candles: List[Candle], zone: Zone, config: dict
) -> bool:
    """
    Falso quiebre B2 bajista (2 velas):
    - Primera vela penetra la resistencia
    - Segunda vela cierra con fuerza de vuelta por debajo
    """
    if len(candles) < 2:
        return False

    prev = candles[-2]
    current = candles[-1]
    min_body = config.get("b2_min_body_ratio", 0.50)

    prev_penetrates = prev.high > zone.upper
    current_recovers = current.close <= zone.upper
    current_strong = current.is_bearish and current.body_ratio >= min_body

    return prev_penetrates and current_recovers and current_strong


# ============================================================
# Pipeline de detección de señales
# ============================================================

def evaluate_zone_for_signal(
    zone: Zone,
    candles_h1: List[Candle],
    entry_config: dict,
) -> Optional[tuple]:
    """
    Evalúa si hay señal de entrada en una zona específica.

    Returns:
        (Direction, SignalType, confidence) o None
    """
    if len(candles_h1) < 2:
        return None

    current = candles_h1[-1]  # Última vela H1 cerrada
    previous = candles_h1[-2]
    pin_config = entry_config.get("pin_bar", {})
    fb_config = entry_config.get("false_breakout", {})

    # --- SOPORTE: buscar señales LONG ---
    if zone.zone_type == ZoneType.SUPPORT:
        # ¿El precio está en la zona o cerca?
        price_in_range = (
            zone.contains_price(current.low) or
            zone.contains_price(current.close) or
            current.low < zone.lower  # Perforó
        )

        if not price_in_range:
            return None

        valid_patterns = entry_config.get("valid_patterns", [])

        # Pin bar alcista (PRIORIDAD 1 - mejor WR: 60%)
        if "pin_bar" in valid_patterns:
            if is_pin_bar_bullish(current, pin_config) and zone.contains_price(current.low):
                return (Direction.LONG, SignalType.PIN_BAR, 0.90)

        # B1 (PRIORIDAD 2)
        if "false_breakout_b1" in valid_patterns:
            if is_false_breakout_b1_support(current, zone, fb_config):
                return (Direction.LONG, SignalType.FALSE_BREAKOUT_B1, 0.85)

        # B2
        if "false_breakout_b2" in valid_patterns:
            if is_false_breakout_b2_support(candles_h1[-2:], zone, fb_config):
                return (Direction.LONG, SignalType.FALSE_BREAKOUT_B2, 0.75)

        # Envolvente alcista
        if "engulfing" in valid_patterns:
            if is_bullish_engulfing(current, previous) and zone.contains_price(current.low):
                return (Direction.LONG, SignalType.ENGULFING, 0.65)

    # --- RESISTENCIA: buscar señales SHORT ---
    elif zone.zone_type == ZoneType.RESISTANCE:
        price_in_range = (
            zone.contains_price(current.high) or
            zone.contains_price(current.close) or
            current.high > zone.upper
        )

        if not price_in_range:
            return None

        valid_patterns = entry_config.get("valid_patterns", [])

        # Pin bar bajista (PRIORIDAD 1 - mejor WR: 60%)
        if "pin_bar" in valid_patterns:
            if is_pin_bar_bearish(current, pin_config) and zone.contains_price(current.high):
                return (Direction.SHORT, SignalType.PIN_BAR, 0.90)

        # B1 (PRIORIDAD 2)
        if "false_breakout_b1" in valid_patterns:
            if is_false_breakout_b1_resistance(current, zone, fb_config):
                return (Direction.SHORT, SignalType.FALSE_BREAKOUT_B1, 0.85)

        # B2
        if "false_breakout_b2" in valid_patterns:
            if is_false_breakout_b2_resistance(candles_h1[-2:], zone, fb_config):
                return (Direction.SHORT, SignalType.FALSE_BREAKOUT_B2, 0.75)

        # Envolvente bajista
        if "engulfing" in valid_patterns:
            if is_bearish_engulfing(current, previous) and zone.contains_price(current.high):
                return (Direction.SHORT, SignalType.ENGULFING, 0.65)

    return None


def calculate_sl_tp(
    direction: Direction,
    zone: Zone,
    all_zones: List[Zone],
    entry_price: float,
    instrument_config: dict,
    tp_config: dict,
) -> Optional[tuple]:
    """
    Calcula Stop Loss y Take Profit.

    Returns:
        (stop_loss, take_profit, risk_reward_ratio) o None si R:R insuficiente
    """
    sl_buffer = instrument_config.get("sl_buffer_points", 80)
    tp_offset = instrument_config.get("tp_offset_points", 20)
    min_rr = tp_config.get("min_rr_ratio", 1.5)

    if direction == Direction.LONG:
        stop_loss = zone.lower - sl_buffer

        # TP en siguiente resistencia
        next_zone = find_next_opposite_zone(zone, all_zones, "LONG")
        if next_zone:
            take_profit = next_zone.lower - tp_offset
        else:
            # Sin zona opuesta: usar R:R mínimo como fallback
            risk = entry_price - stop_loss
            take_profit = entry_price + (risk * min_rr)

    else:  # SHORT
        stop_loss = zone.upper + sl_buffer

        next_zone = find_next_opposite_zone(zone, all_zones, "SHORT")
        if next_zone:
            take_profit = next_zone.upper + tp_offset
        else:
            risk = stop_loss - entry_price
            take_profit = entry_price - (risk * min_rr)

    # Calcular R:R
    if direction == Direction.LONG:
        risk = entry_price - stop_loss
        reward = take_profit - entry_price
    else:
        risk = stop_loss - entry_price
        reward = entry_price - take_profit

    if risk <= 0:
        logger.warning(f"Riesgo inválido ({risk:.1f}) — SL mal calculado")
        return None

    rr_ratio = reward / risk

    if rr_ratio < min_rr:
        logger.debug(f"R:R insuficiente ({rr_ratio:.2f} < {min_rr}) — trade descartado")
        return None

    return (stop_loss, take_profit, rr_ratio)


def scan_for_signals(
    candles_h1: List[Candle],
    zones: List[Zone],
    all_zones: List[Zone],
    instrument: str,
    instrument_config: dict,
    entry_config: dict,
    tp_config: dict,
) -> List[Signal]:
    """
    Escanea todas las zonas activas buscando señales de entrada.

    Args:
        candles_h1: Últimas velas H1 (mínimo 2)
        zones: Zonas activas de S/R
        all_zones: Todas las zonas (para calcular TP)
        instrument: Nombre del instrumento
        instrument_config: Config del instrumento
        entry_config: Config de entrada
        tp_config: Config de take profit

    Returns:
        Lista de señales válidas encontradas
    """
    signals = []

    for zone in zones:
        if not zone.is_active:
            continue

        result = evaluate_zone_for_signal(zone, candles_h1, entry_config)

        if result is None:
            continue

        direction, signal_type, confidence = result
        entry_price = candles_h1[-1].close

        # Calcular SL/TP
        sl_tp = calculate_sl_tp(
            direction, zone, all_zones,
            entry_price, instrument_config, tp_config
        )

        if sl_tp is None:
            continue

        stop_loss, take_profit, rr_ratio = sl_tp

        signal = Signal(
            timestamp=candles_h1[-1].time,
            instrument=instrument,
            direction=direction,
            signal_type=signal_type,
            zone=zone,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_reward_ratio=rr_ratio,
            confidence=confidence,
        )

        signals.append(signal)
        logger.info(f"SEÑAL: {signal}")

    # Si hay múltiples señales, priorizar por confianza
    signals.sort(key=lambda s: s.confidence, reverse=True)

    return signals
