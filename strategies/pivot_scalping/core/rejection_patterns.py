"""
Patrones de rechazo para scalping en M5

Este módulo detecta patrones de velas que indican rechazo de una zona:
- Pin Bar (vela con mecha larga)
- Engulfing (vela que envuelve la anterior)

Estos patrones se usan para confirmar entradas en zonas de pivot.
"""

from dataclasses import dataclass
from typing import Optional
from enum import Enum


class PatternType(Enum):
    """Tipo de patrón detectado"""
    PIN_BAR_BULLISH = "pin_bar_bullish"
    PIN_BAR_BEARISH = "pin_bar_bearish"
    ENGULFING_BULLISH = "engulfing_bullish"
    ENGULFING_BEARISH = "engulfing_bearish"


@dataclass
class Candle:
    """Vela OHLC simple"""
    open: float
    high: float
    low: float
    close: float
    
    @property
    def body_size(self) -> float:
        """Tamaño del cuerpo"""
        return abs(self.close - self.open)
    
    @property
    def full_size(self) -> float:
        """Tamaño completo (high - low)"""
        return self.high - self.low
    
    @property
    def upper_wick(self) -> float:
        """Mecha superior"""
        return self.high - max(self.open, self.close)
    
    @property
    def lower_wick(self) -> float:
        """Mecha inferior"""
        return min(self.open, self.close) - self.low
    
    @property
    def is_bullish(self) -> bool:
        """Vela alcista (cierre > apertura)"""
        return self.close > self.open
    
    @property
    def is_bearish(self) -> bool:
        """Vela bajista (cierre < apertura)"""
        return self.close < self.open


@dataclass
class RejectionPattern:
    """
    Patrón de rechazo detectado
    
    Attributes:
        type: Tipo de patrón
        candle: Vela que forma el patrón
        strength: Fuerza del patrón (0-1)
        description: Descripción del patrón
    """
    type: PatternType
    candle: Candle
    strength: float
    description: str
    
    @property
    def is_bullish(self) -> bool:
        """Patrón alcista (señal de compra)"""
        return self.type in [PatternType.PIN_BAR_BULLISH, PatternType.ENGULFING_BULLISH]
    
    @property
    def is_bearish(self) -> bool:
        """Patrón bajista (señal de venta)"""
        return self.type in [PatternType.PIN_BAR_BEARISH, PatternType.ENGULFING_BEARISH]


def detect_pin_bar(
    candle: Candle,
    min_wick_to_body_ratio: float = 2.0,
    max_body_pct: float = 0.35
) -> Optional[RejectionPattern]:
    """
    Detecta Pin Bar (vela con mecha larga)
    
    Pin Bar Alcista (señal de compra):
    - Mecha inferior larga (>= 2x cuerpo)
    - Cuerpo pequeño (<= 35% de vela completa)
    - Cierre en mitad superior de la vela
    
    Pin Bar Bajista (señal de venta):
    - Mecha superior larga (>= 2x cuerpo)
    - Cuerpo pequeño (<= 35% de vela completa)
    - Cierre en mitad inferior de la vela
    
    Args:
        candle: Vela a analizar
        min_wick_to_body_ratio: Ratio mínimo mecha/cuerpo
        max_body_pct: Porcentaje máximo del cuerpo
    
    Returns:
        RejectionPattern si se detecta pin bar, None si no
    """
    # Validar que la vela tenga tamaño
    if candle.full_size == 0:
        return None
    
    body_pct = candle.body_size / candle.full_size
    
    # Verificar que el cuerpo sea pequeño
    if body_pct > max_body_pct:
        return None
    
    # Verificar Pin Bar Alcista (mecha inferior larga)
    if candle.lower_wick > 0 and candle.body_size > 0:
        wick_to_body = candle.lower_wick / candle.body_size
        
        if wick_to_body >= min_wick_to_body_ratio:
            # Verificar que cierre en mitad superior
            mid_point = (candle.high + candle.low) / 2
            if candle.close >= mid_point:
                strength = min(1.0, wick_to_body / (min_wick_to_body_ratio * 2))
                return RejectionPattern(
                    type=PatternType.PIN_BAR_BULLISH,
                    candle=candle,
                    strength=strength,
                    description=f"Pin Bar alcista (mecha/cuerpo: {wick_to_body:.1f}x)"
                )
    
    # Verificar Pin Bar Bajista (mecha superior larga)
    if candle.upper_wick > 0 and candle.body_size > 0:
        wick_to_body = candle.upper_wick / candle.body_size
        
        if wick_to_body >= min_wick_to_body_ratio:
            # Verificar que cierre en mitad inferior
            mid_point = (candle.high + candle.low) / 2
            if candle.close <= mid_point:
                strength = min(1.0, wick_to_body / (min_wick_to_body_ratio * 2))
                return RejectionPattern(
                    type=PatternType.PIN_BAR_BEARISH,
                    candle=candle,
                    strength=strength,
                    description=f"Pin Bar bajista (mecha/cuerpo: {wick_to_body:.1f}x)"
                )
    
    return None


def detect_engulfing(
    current: Candle,
    previous: Candle,
    min_body_ratio: float = 1.0
) -> Optional[RejectionPattern]:
    """
    Detecta Engulfing (vela que envuelve la anterior)
    
    Engulfing Alcista (señal de compra):
    - Vela anterior bajista (roja)
    - Vela actual alcista (verde)
    - Cuerpo actual envuelve cuerpo anterior
    
    Engulfing Bajista (señal de venta):
    - Vela anterior alcista (verde)
    - Vela actual bajista (roja)
    - Cuerpo actual envuelve cuerpo anterior
    
    Args:
        current: Vela actual
        previous: Vela anterior
        min_body_ratio: Ratio mínimo cuerpo_actual/cuerpo_anterior
    
    Returns:
        RejectionPattern si se detecta engulfing, None si no
    """
    # Validar que ambas velas tengan cuerpo
    if current.body_size == 0 or previous.body_size == 0:
        return None
    
    # Engulfing Alcista
    if previous.is_bearish and current.is_bullish:
        # Verificar que el cuerpo actual envuelva el anterior
        if (current.open <= previous.close and 
            current.close >= previous.open):
            
            body_ratio = current.body_size / previous.body_size
            if body_ratio >= min_body_ratio:
                strength = min(1.0, body_ratio / 2.0)
                return RejectionPattern(
                    type=PatternType.ENGULFING_BULLISH,
                    candle=current,
                    strength=strength,
                    description=f"Engulfing alcista (ratio: {body_ratio:.1f}x)"
                )
    
    # Engulfing Bajista
    if previous.is_bullish and current.is_bearish:
        # Verificar que el cuerpo actual envuelva el anterior
        if (current.open >= previous.close and 
            current.close <= previous.open):
            
            body_ratio = current.body_size / previous.body_size
            if body_ratio >= min_body_ratio:
                strength = min(1.0, body_ratio / 2.0)
                return RejectionPattern(
                    type=PatternType.ENGULFING_BEARISH,
                    candle=current,
                    strength=strength,
                    description=f"Engulfing bajista (ratio: {body_ratio:.1f}x)"
                )
    
    return None


def detect_rejection_patterns(
    current: Candle,
    previous: Optional[Candle] = None,
    config: dict = None
) -> list[RejectionPattern]:
    """
    Detecta todos los patrones de rechazo en una vela
    
    Args:
        current: Vela actual
        previous: Vela anterior (para engulfing)
        config: Configuración de patrones (opcional)
    
    Returns:
        Lista de patrones detectados
    """
    patterns = []
    
    # Configuración por defecto
    if config is None:
        config = {
            'pin_bar': {
                'min_wick_to_body_ratio': 2.0,
                'max_body_pct': 0.35
            },
            'engulfing': {
                'min_body_ratio': 1.0
            }
        }
    
    # Detectar Pin Bar
    pin_bar = detect_pin_bar(
        current,
        min_wick_to_body_ratio=config['pin_bar']['min_wick_to_body_ratio'],
        max_body_pct=config['pin_bar']['max_body_pct']
    )
    if pin_bar:
        patterns.append(pin_bar)
    
    # Detectar Engulfing (solo si hay vela anterior)
    if previous is not None:
        engulfing = detect_engulfing(
            current,
            previous,
            min_body_ratio=config['engulfing']['min_body_ratio']
        )
        if engulfing:
            patterns.append(engulfing)
    
    return patterns
