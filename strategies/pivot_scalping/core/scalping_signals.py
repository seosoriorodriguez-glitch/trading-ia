"""
Generación de señales de scalping basadas en pivots y patrones de rechazo

Este módulo combina:
1. Detección de pivots en M15
2. Patrones de rechazo en M5
3. Validación de zona (segundo toque)
4. Cálculo de SL/TP por estructura
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
from enum import Enum

from .pivot_detection import PivotPoint, PivotType, PivotStatus, Candle as M15Candle
from .rejection_patterns import RejectionPattern, Candle as M5Candle, detect_rejection_patterns


class SignalType(Enum):
    """Tipo de señal"""
    LONG = "long"
    SHORT = "short"


@dataclass
class TradingSignal:
    """
    Señal de trading generada
    
    Attributes:
        type: LONG o SHORT
        time: Tiempo de la señal
        entry_price: Precio de entrada
        stop_loss: Precio de stop loss
        take_profit: Precio de take profit
        risk_reward: Ratio riesgo/recompensa
        pivot: Pivot que generó la señal
        pattern: Patrón de rechazo que confirmó
        confidence: Confianza de la señal (0-1)
        notes: Notas adicionales
    """
    type: SignalType
    time: datetime
    entry_price: float
    stop_loss: float
    take_profit: float
    risk_reward: float
    pivot: PivotPoint
    pattern: RejectionPattern
    confidence: float = 0.5
    notes: str = ""
    
    @property
    def risk_points(self) -> float:
        """Riesgo en puntos"""
        return abs(self.entry_price - self.stop_loss)
    
    @property
    def reward_points(self) -> float:
        """Recompensa en puntos"""
        return abs(self.take_profit - self.entry_price)


class ScalpingSignalGenerator:
    """
    Generador de señales de scalping
    
    Combina pivots de M15 con patrones de rechazo en M5 para generar
    señales de entrada con SL/TP calculados por estructura.
    """
    
    def __init__(self, config: dict):
        """
        Inicializa el generador
        
        Args:
            config: Configuración de la estrategia
        """
        self.config = config
        self.active_pivots: List[PivotPoint] = []
    
    def update_pivots(self, pivots: List[PivotPoint]):
        """Actualiza lista de pivots activos"""
        self.active_pivots = [p for p in pivots if p.status == PivotStatus.ACTIVE]
    
    def check_signal(
        self,
        candle_m5: M5Candle,
        previous_m5: Optional[M5Candle],
        all_pivots: List[PivotPoint],
        current_time: datetime
    ) -> Optional[TradingSignal]:
        """
        Verifica si hay señal de entrada en la vela M5 actual
        
        Args:
            candle_m5: Vela M5 actual
            previous_m5: Vela M5 anterior
            all_pivots: Lista de todos los pivots (para calcular TP)
            current_time: Tiempo actual
        
        Returns:
            TradingSignal si hay señal, None si no
        """
        # Detectar patrones de rechazo
        patterns = detect_rejection_patterns(
            candle_m5,
            previous_m5,
            config={
                'pin_bar': self.config['entry']['pin_bar'],
                'engulfing': self.config['entry']['engulfing']
            }
        )
        
        if not patterns:
            return None
        
        # Verificar cada pivot activo
        for pivot in self.active_pivots:
            # Verificar si la vela toca la zona del pivot
            if not self._touches_zone(candle_m5, pivot):
                continue
            
            # Buscar patrón compatible con el tipo de pivot
            for pattern in patterns:
                signal = self._validate_signal(
                    pivot,
                    pattern,
                    candle_m5,
                    all_pivots,
                    current_time
                )
                
                if signal:
                    return signal
        
        return None
    
    def _touches_zone(self, candle: M5Candle, pivot: PivotPoint) -> bool:
        """Verifica si la vela M5 toca la zona del pivot"""
        if pivot.type == PivotType.HIGH:
            # Para resistencia, verificar si el high toca la zona
            return candle.high >= pivot.price_low
        else:  # PivotType.LOW
            # Para soporte, verificar si el low toca la zona
            return candle.low <= pivot.price_high
    
    def _validate_signal(
        self,
        pivot: PivotPoint,
        pattern: RejectionPattern,
        candle: M5Candle,
        all_pivots: List[PivotPoint],
        current_time: datetime
    ) -> Optional[TradingSignal]:
        """
        Valida si el patrón es compatible con el pivot y genera señal
        
        Args:
            pivot: Pivot que genera la señal
            pattern: Patrón de rechazo detectado
            candle: Vela M5 actual
            all_pivots: Todos los pivots (para TP)
            current_time: Tiempo actual
        
        Returns:
            TradingSignal si es válida, None si no
        """
        # Validar compatibilidad pivot-patrón
        if pivot.type == PivotType.LOW and not pattern.is_bullish:
            return None  # En soporte necesitamos patrón alcista
        
        if pivot.type == PivotType.HIGH and not pattern.is_bearish:
            return None  # En resistencia necesitamos patrón bajista
        
        # Calcular SL y TP
        if pivot.type == PivotType.LOW:
            # LONG
            entry = candle.close
            stop_loss = self._calculate_stop_loss(pivot, SignalType.LONG)
            take_profit = self._calculate_take_profit(
                pivot, entry, stop_loss, SignalType.LONG, all_pivots
            )
            signal_type = SignalType.LONG
        else:
            # SHORT
            entry = candle.close
            stop_loss = self._calculate_stop_loss(pivot, SignalType.SHORT)
            take_profit = self._calculate_take_profit(
                pivot, entry, stop_loss, SignalType.SHORT, all_pivots
            )
            signal_type = SignalType.SHORT
        
        # Calcular R:R
        risk = abs(entry - stop_loss)
        reward = abs(take_profit - entry)
        
        if risk == 0:
            return None
        
        # Validar riesgo mínimo (filtrar trades con SL muy ajustado)
        min_risk = self.config['stop_loss'].get('min_risk_points', 10)
        if risk < min_risk:
            return None  # Descartar trade con riesgo muy pequeño
        
        rr_ratio = reward / risk
        
        # Validar R:R mínimo
        min_rr = self.config['take_profit'].get('min_rr_ratio', 1.5)
        if rr_ratio < min_rr:
            return None
        
        # Filtro direccional (si está habilitado)
        if 'filters' in self.config and 'direction' in self.config['filters']:
            dir_filter = self.config['filters']['direction']
            if dir_filter.get('enabled', False):
                allowed = dir_filter.get('allowed_directions', ['long', 'short'])
                if signal_type.value not in allowed:
                    return None  # Dirección no permitida
        
        # Calcular confianza
        confidence = self._calculate_confidence(pattern, rr_ratio)
        
        # Crear señal
        signal = TradingSignal(
            type=signal_type,
            time=current_time,
            entry_price=entry,
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_reward=rr_ratio,
            pivot=pivot,
            pattern=pattern,
            confidence=confidence,
            notes=f"{pattern.description} en {pivot.type.value}"
        )
        
        return signal
    
    def _calculate_stop_loss(self, pivot: PivotPoint, signal_type: SignalType) -> float:
        """
        Calcula stop loss basado en la zona del pivot
        
        Args:
            pivot: Pivot que genera la señal
            signal_type: LONG o SHORT
        
        Returns:
            Precio de stop loss
        """
        buffer = self.config['stop_loss']['buffer_points']
        
        if signal_type == SignalType.LONG:
            # LONG: SL debajo del soporte
            return pivot.price_low - buffer
        else:
            # SHORT: SL encima de la resistencia
            return pivot.price_high + buffer
    
    def _calculate_take_profit(
        self,
        pivot: PivotPoint,
        entry: float,
        stop_loss: float,
        signal_type: SignalType,
        all_pivots: List[PivotPoint]
    ) -> float:
        """
        Calcula take profit por estructura (siguiente pivot opuesto)
        
        Args:
            pivot: Pivot actual
            entry: Precio de entrada
            stop_loss: Precio de stop loss
            signal_type: LONG o SHORT
            all_pivots: Lista de todos los pivots
        
        Returns:
            Precio de take profit
        """
        tp_config = self.config['take_profit']
        
        # Intentar método por estructura
        if tp_config.get('method') == 'structure':
            opposite_pivot = self._find_opposite_pivot(pivot, all_pivots, signal_type)
            
            if opposite_pivot:
                offset = tp_config['structure']['offset_points']
                
                if signal_type == SignalType.LONG:
                    # LONG: TP antes del siguiente pivot high
                    return opposite_pivot.price_low - offset
                else:
                    # SHORT: TP antes del siguiente pivot low
                    return opposite_pivot.price_high + offset
        
        # Fallback: R:R fijo
        fallback_rr = tp_config.get('fallback_rr', 2.0)
        risk = abs(entry - stop_loss)
        
        if signal_type == SignalType.LONG:
            return entry + (risk * fallback_rr)
        else:
            return entry - (risk * fallback_rr)
    
    def _find_opposite_pivot(
        self,
        current_pivot: PivotPoint,
        all_pivots: List[PivotPoint],
        signal_type: SignalType
    ) -> Optional[PivotPoint]:
        """
        Encuentra el siguiente pivot opuesto para calcular TP
        
        Args:
            current_pivot: Pivot actual
            all_pivots: Lista de todos los pivots
            signal_type: LONG o SHORT
        
        Returns:
            Pivot opuesto más cercano o None
        """
        opposite_type = PivotType.HIGH if signal_type == SignalType.LONG else PivotType.LOW
        
        # Filtrar pivots opuestos
        opposite_pivots = [p for p in all_pivots if p.type == opposite_type]
        
        if signal_type == SignalType.LONG:
            # Para LONGs: buscar pivot high por encima
            candidates = [p for p in opposite_pivots if p.price_low > current_pivot.price_high]
            if candidates:
                return min(candidates, key=lambda p: p.price_low)
        else:
            # Para SHORTs: buscar pivot low por debajo
            candidates = [p for p in opposite_pivots if p.price_high < current_pivot.price_low]
            if candidates:
                return max(candidates, key=lambda p: p.price_high)
        
        return None
    
    def _calculate_confidence(self, pattern: RejectionPattern, rr_ratio: float) -> float:
        """
        Calcula confianza de la señal
        
        Args:
            pattern: Patrón detectado
            rr_ratio: Ratio riesgo/recompensa
        
        Returns:
            Confianza (0-1)
        """
        # Base: fuerza del patrón
        confidence = pattern.strength * 0.6
        
        # Bonus por R:R alto
        if rr_ratio >= 3.0:
            confidence += 0.3
        elif rr_ratio >= 2.0:
            confidence += 0.2
        elif rr_ratio >= 1.5:
            confidence += 0.1
        
        return min(1.0, confidence)
