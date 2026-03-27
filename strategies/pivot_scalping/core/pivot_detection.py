"""
Detección de Pivot Points puros (High/Low) en M15

Este módulo implementa la detección de Pivot Points usando la definición
estándar de TradingView: un pivot es un high/low que es mayor/menor que
N velas a cada lado.

NO hay filtros de mecha, cuerpo, o tipo de vela. Son pivots puros.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
from enum import Enum


class PivotType(Enum):
    """Tipo de pivot"""
    HIGH = "resistance"  # Resistencia
    LOW = "support"      # Soporte


class PivotStatus(Enum):
    """Estado del pivot"""
    CREATED = "created"          # Recién detectado
    FIRST_TOUCH = "first_touch"  # Primer toque registrado
    ACTIVE = "active"            # Segundo toque, listo para operar
    EXPIRED = "expired"          # Expirado por tiempo o toques


@dataclass
class Candle:
    """Vela OHLCV"""
    time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0


@dataclass
class PivotPoint:
    """
    Pivot Point detectado en M15
    
    Attributes:
        type: Tipo de pivot (HIGH o LOW)
        time: Tiempo de la vela que formó el pivot
        confirmed_at: Tiempo cuando el pivot se confirma (time + swing_strength velas)
        index: Índice de la vela en el array
        price_high: High de la vela pivote (tope de zona)
        price_low: Low de la vela pivote (base de zona)
        touches: Número de toques a la zona
        touch_times: Lista de tiempos de cada toque
        status: Estado actual del pivot
        created_at: Tiempo de creación
        expires_at: Tiempo de expiración (en número de velas)
    """
    type: PivotType
    time: datetime
    confirmed_at: datetime  # NUEVO: cuándo se confirma el pivot
    index: int
    price_high: float
    price_low: float
    touches: int = 0
    touch_times: List[datetime] = None
    status: PivotStatus = PivotStatus.CREATED
    created_at: datetime = None
    expires_at: int = None  # Número de velas desde creación
    
    def __post_init__(self):
        if self.touch_times is None:
            self.touch_times = []
        if self.created_at is None:
            self.created_at = self.time
    
    @property
    def zone_width(self) -> float:
        """Ancho de la zona en puntos"""
        return self.price_high - self.price_low
    
    @property
    def zone_center(self) -> float:
        """Centro de la zona"""
        return (self.price_high + self.price_low) / 2.0
    
    def is_in_zone(self, price: float) -> bool:
        """Verifica si un precio está dentro de la zona"""
        return self.price_low <= price <= self.price_high
    
    def touches_zone(self, candle: Candle) -> bool:
        """Verifica si una vela toca la zona"""
        if self.type == PivotType.HIGH:
            # Para resistencia, verificar si el high toca la zona
            return candle.high >= self.price_low
        else:  # PivotType.LOW
            # Para soporte, verificar si el low toca la zona
            return candle.low <= self.price_high


def detect_pivot_highs(
    candles: List[Candle],
    swing_strength: int = 3,
    min_zone_width: float = 10.0,
    max_zone_width: float = 200.0
) -> List[PivotPoint]:
    """
    Detecta Pivot Highs (resistencias) en una lista de velas
    
    Un Pivot High es una vela cuyo high es mayor que los highs de
    N velas antes y N velas después.
    
    Args:
        candles: Lista de velas M15
        swing_strength: Número de velas a cada lado (N)
        min_zone_width: Ancho mínimo de zona en puntos
        max_zone_width: Ancho máximo de zona en puntos
    
    Returns:
        Lista de PivotPoint detectados
    """
    pivots = []
    
    # Necesitamos al menos (2 * swing_strength + 1) velas
    if len(candles) < (2 * swing_strength + 1):
        return pivots
    
    # Iterar desde swing_strength hasta len - swing_strength
    for i in range(swing_strength, len(candles) - swing_strength):
        candle = candles[i]
        
        # Verificar que el high sea mayor que N velas antes y después
        is_pivot = True
        
        # Verificar velas antes
        for j in range(1, swing_strength + 1):
            if candles[i - j].high >= candle.high:
                is_pivot = False
                break
        
        if not is_pivot:
            continue
        
        # Verificar velas después
        for j in range(1, swing_strength + 1):
            if candles[i + j].high >= candle.high:
                is_pivot = False
                break
        
        if is_pivot:
            # Validar ancho de zona
            zone_width = candle.high - candle.low
            if zone_width < min_zone_width or zone_width > max_zone_width:
                continue
            
            # CRÍTICO: El pivot se confirma DESPUÉS de swing_strength velas
            # Solo se puede usar en backtest después de confirmed_at
            pivot = PivotPoint(
                type=PivotType.HIGH,
                time=candle.time,
                confirmed_at=candles[i + swing_strength].time,  # Confirmado N velas después
                index=i,
                price_high=candle.high,
                price_low=candle.low,
                status=PivotStatus.CREATED
            )
            pivots.append(pivot)
    
    return pivots


def detect_pivot_lows(
    candles: List[Candle],
    swing_strength: int = 3,
    min_zone_width: float = 10.0,
    max_zone_width: float = 200.0
) -> List[PivotPoint]:
    """
    Detecta Pivot Lows (soportes) en una lista de velas
    
    Un Pivot Low es una vela cuyo low es menor que los lows de
    N velas antes y N velas después.
    
    Args:
        candles: Lista de velas M15
        swing_strength: Número de velas a cada lado (N)
        min_zone_width: Ancho mínimo de zona en puntos
        max_zone_width: Ancho máximo de zona en puntos
    
    Returns:
        Lista de PivotPoint detectados
    """
    pivots = []
    
    if len(candles) < (2 * swing_strength + 1):
        return pivots
    
    for i in range(swing_strength, len(candles) - swing_strength):
        candle = candles[i]
        
        is_pivot = True
        
        # Verificar velas antes
        for j in range(1, swing_strength + 1):
            if candles[i - j].low <= candle.low:
                is_pivot = False
                break
        
        if not is_pivot:
            continue
        
        # Verificar velas después
        for j in range(1, swing_strength + 1):
            if candles[i + j].low <= candle.low:
                is_pivot = False
                break
        
        if is_pivot:
            # Validar ancho de zona
            zone_width = candle.high - candle.low
            if zone_width < min_zone_width or zone_width > max_zone_width:
                continue
            
            # CRÍTICO: El pivot se confirma DESPUÉS de swing_strength velas
            # Solo se puede usar en backtest después de confirmed_at
            pivot = PivotPoint(
                type=PivotType.LOW,
                time=candle.time,
                confirmed_at=candles[i + swing_strength].time,  # Confirmado N velas después
                index=i,
                price_high=candle.high,
                price_low=candle.low,
                status=PivotStatus.CREATED
            )
            pivots.append(pivot)
    
    return pivots


def update_pivot_touches(
    pivot: PivotPoint,
    candles_m15: List[Candle],
    min_separation: int = 4
) -> PivotPoint:
    """
    Actualiza el conteo de toques de un pivot
    
    Args:
        pivot: Pivot a actualizar
        candles_m15: Velas M15 para verificar toques
        min_separation: Mínimo de velas entre toques
    
    Returns:
        Pivot actualizado
    """
    # Obtener velas después de la creación del pivot
    candles_after = [c for c in candles_m15 if c.time > pivot.time]
    
    last_touch_index = -min_separation  # Para permitir primer toque inmediato
    
    for i, candle in enumerate(candles_after):
        # Verificar separación mínima
        if i - last_touch_index < min_separation:
            continue
        
        # Verificar si toca la zona
        if pivot.touches_zone(candle):
            pivot.touches += 1
            pivot.touch_times.append(candle.time)
            last_touch_index = i
            
            # Actualizar estado
            if pivot.touches == 1:
                pivot.status = PivotStatus.FIRST_TOUCH
            elif pivot.touches >= 2:
                pivot.status = PivotStatus.ACTIVE
    
    return pivot


def filter_active_pivots(
    pivots: List[PivotPoint],
    current_time: datetime,
    expiry_candles: int = 200,
    max_touches: int = 6,
    max_active: int = 6
) -> List[PivotPoint]:
    """
    Filtra pivots activos (no expirados)
    
    Args:
        pivots: Lista de pivots
        current_time: Tiempo actual
        expiry_candles: Número de velas antes de expirar
        max_touches: Máximo de toques antes de expirar
        max_active: Máximo de zonas activas simultáneas
    
    Returns:
        Lista de pivots activos
    """
    active = []
    
    for pivot in pivots:
        # Verificar si expiró por toques
        if pivot.touches >= max_touches:
            pivot.status = PivotStatus.EXPIRED
            continue
        
        # Verificar si expiró por tiempo
        # (esto requeriría calcular velas transcurridas, simplificado aquí)
        if pivot.status == PivotStatus.EXPIRED:
            continue
        
        active.append(pivot)
    
    # Limitar a max_active más recientes
    if len(active) > max_active:
        active = sorted(active, key=lambda p: p.time, reverse=True)[:max_active]
    
    return active


def find_next_opposite_pivot(
    current_pivot: PivotPoint,
    all_pivots: List[PivotPoint],
    direction: str  # "above" o "below"
) -> Optional[PivotPoint]:
    """
    Encuentra el siguiente pivot opuesto para calcular TP
    
    Args:
        current_pivot: Pivot actual (donde entramos)
        all_pivots: Lista de todos los pivots
        direction: "above" (para LONGs) o "below" (para SHORTs)
    
    Returns:
        Pivot opuesto más cercano o None
    """
    opposite_type = PivotType.HIGH if current_pivot.type == PivotType.LOW else PivotType.LOW
    
    # Filtrar pivots opuestos
    opposite_pivots = [p for p in all_pivots if p.type == opposite_type]
    
    if direction == "above":
        # Para LONGs: buscar pivot high por encima
        candidates = [p for p in opposite_pivots if p.price_low > current_pivot.price_high]
        if candidates:
            return min(candidates, key=lambda p: p.price_low)
    else:  # "below"
        # Para SHORTs: buscar pivot low por debajo
        candidates = [p for p in opposite_pivots if p.price_high < current_pivot.price_low]
        if candidates:
            return max(candidates, key=lambda p: p.price_high)
    
    return None
