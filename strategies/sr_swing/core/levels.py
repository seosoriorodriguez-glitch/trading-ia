"""
Detección de Zonas de Soporte y Resistencia.

Lógica:
1. Encontrar swing highs/lows en H4 con rechazo fuerte (mecha significativa)
2. Agrupar swings cercanos en zonas
3. Validar zonas con mínimo 2 toques
4. La zona se define por el rango completo (high-low) de la vela con mayor rechazo
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Tuple
from enum import Enum

from core.market_data import Candle

logger = logging.getLogger(__name__)


class ZoneType(Enum):
    SUPPORT = "support"
    RESISTANCE = "resistance"


@dataclass
class Zone:
    """Zona de soporte o resistencia."""
    zone_type: ZoneType
    upper: float                       # Borde superior de la zona
    lower: float                       # Borde inferior de la zona
    origin_candle_time: datetime       # Timestamp de la vela que creó la zona
    touches: int = 1                   # Número de toques
    last_touch_time: Optional[datetime] = None
    is_active: bool = True
    strength: float = 0.0              # Fuerza del rechazo (wick ratio)

    @property
    def midpoint(self) -> float:
        return (self.upper + self.lower) / 2

    @property
    def width(self) -> float:
        return self.upper - self.lower

    def contains_price(self, price: float) -> bool:
        """Verifica si un precio está dentro de la zona."""
        return self.lower <= price <= self.upper

    def price_beyond_zone(self, price: float) -> bool:
        """Verifica si un precio ha perforado más allá de la zona."""
        if self.zone_type == ZoneType.SUPPORT:
            return price < self.lower
        else:
            return price > self.upper

    def distance_to(self, price: float) -> float:
        """Distancia del precio al borde más cercano de la zona."""
        if price > self.upper:
            return price - self.upper
        elif price < self.lower:
            return self.lower - price
        return 0  # Dentro de la zona

    def __repr__(self) -> str:
        return (f"Zone({self.zone_type.value}: {self.lower:.1f}-{self.upper:.1f}, "
                f"touches={self.touches}, width={self.width:.1f})")


def detect_swing_points(
    candles: List[Candle],
    strength: int = 3,
    min_wick_ratio: float = 0.40
) -> Tuple[List[Tuple[int, Candle]], List[Tuple[int, Candle]]]:
    """
    Detecta swing highs y swing lows con rechazo fuerte.

    Un swing high: high mayor que los highs de las N velas a cada lado.
    Un swing low: low menor que los lows de las N velas a cada lado.
    Filtro: la vela debe tener mecha significativa (rechazo fuerte).

    Args:
        candles: Lista de velas H4
        strength: Número de velas a cada lado (N)
        min_wick_ratio: Mínimo ratio de mecha para considerar rechazo fuerte

    Returns:
        (swing_highs, swing_lows) — listas de tuplas (índice, vela)
    """
    swing_highs = []
    swing_lows = []

    if len(candles) < (2 * strength + 1):
        return swing_highs, swing_lows

    for i in range(strength, len(candles) - strength):
        candle = candles[i]

        # Skip velas sin rango (doji perfecto)
        if candle.range_size == 0:
            continue

        # --- Swing High ---
        is_swing_high = True
        for j in range(1, strength + 1):
            if candles[i - j].high >= candle.high or candles[i + j].high >= candle.high:
                is_swing_high = False
                break

        if is_swing_high:
            # Filtro de rechazo fuerte: mecha superior significativa
            # O bien: es una vela con cuerpo pequeño y mechas largas (doji de rechazo)
            has_strong_rejection = (
                candle.upper_wick_ratio >= min_wick_ratio
                or (candle.is_bearish and candle.body_ratio >= 0.50)  # Envolvente bajista fuerte
            )
            if has_strong_rejection:
                swing_highs.append((i, candle))

        # --- Swing Low ---
        is_swing_low = True
        for j in range(1, strength + 1):
            if candles[i - j].low <= candle.low or candles[i + j].low <= candle.low:
                is_swing_low = False
                break

        if is_swing_low:
            has_strong_rejection = (
                candle.lower_wick_ratio >= min_wick_ratio
                or (candle.is_bullish and candle.body_ratio >= 0.50)  # Envolvente alcista fuerte
            )
            if has_strong_rejection:
                swing_lows.append((i, candle))

    logger.debug(f"Detectados {len(swing_highs)} swing highs, {len(swing_lows)} swing lows")
    return swing_highs, swing_lows


def cluster_into_zones(
    swing_points: List[Tuple[int, Candle]],
    zone_type: ZoneType,
    merge_distance: float,
    min_zone_width: float = 0,
    max_zone_width: float = float("inf"),
) -> List[Zone]:
    """
    Agrupa swing points cercanos en zonas.

    Si dos swings están a menos de merge_distance, forman parte de la misma zona.
    La zona usa el rango (high-low) de la vela con mayor rechazo.

    Args:
        swing_points: Lista de (índice, vela) — swing highs o lows
        zone_type: SUPPORT o RESISTANCE
        merge_distance: Distancia máxima para agrupar en misma zona
        min_zone_width: Ancho mínimo de zona válida
        max_zone_width: Ancho máximo de zona válida
    """
    if not swing_points:
        return []

    # Ordenar por precio (high para resistencia, low para soporte)
    if zone_type == ZoneType.RESISTANCE:
        sorted_points = sorted(swing_points, key=lambda x: x[1].high)
    else:
        sorted_points = sorted(swing_points, key=lambda x: x[1].low)

    clusters: List[List[Tuple[int, Candle]]] = []
    current_cluster = [sorted_points[0]]

    for i in range(1, len(sorted_points)):
        prev_candle = sorted_points[i - 1][1]
        curr_candle = sorted_points[i][1]

        if zone_type == ZoneType.RESISTANCE:
            distance = abs(curr_candle.high - prev_candle.high)
        else:
            distance = abs(curr_candle.low - prev_candle.low)

        if distance <= merge_distance:
            current_cluster.append(sorted_points[i])
        else:
            clusters.append(current_cluster)
            current_cluster = [sorted_points[i]]

    clusters.append(current_cluster)

    # Convertir clusters a zonas
    zones = []
    for cluster in clusters:
        # Encontrar la vela con el rechazo más fuerte (mayor mecha)
        if zone_type == ZoneType.RESISTANCE:
            strongest = max(cluster, key=lambda x: x[1].upper_wick_ratio)
        else:
            strongest = max(cluster, key=lambda x: x[1].lower_wick_ratio)

        strongest_candle = strongest[1]

        zone = Zone(
            zone_type=zone_type,
            upper=strongest_candle.high,
            lower=strongest_candle.low,
            origin_candle_time=strongest_candle.time,
            touches=len(cluster),  # Cada swing en el cluster cuenta como toque
            last_touch_time=max(c[1].time for c in cluster),
            strength=strongest_candle.upper_wick_ratio if zone_type == ZoneType.RESISTANCE
                     else strongest_candle.lower_wick_ratio,
        )

        # Filtrar por ancho
        if min_zone_width <= zone.width <= max_zone_width:
            zones.append(zone)
        else:
            logger.debug(f"Zona descartada por ancho ({zone.width:.1f}): {zone}")

    return zones


def count_additional_touches(
    zone: Zone,
    candles: List[Candle],
    min_separation: int = 5
) -> Zone:
    """
    Cuenta toques adicionales a una zona que no fueron swing points.
    Un toque = una vela cuyo high o low entra en la zona,
    separada por al menos min_separation velas del toque anterior.

    Modifica la zona in-place y la retorna.
    """
    last_touch_idx = -min_separation  # Permitir primer toque

    for i, candle in enumerate(candles):
        if candle.time <= zone.origin_candle_time:
            continue  # Solo contar toques posteriores a la creación

        if i - last_touch_idx < min_separation:
            continue  # Muy cerca del toque anterior

        # ¿La vela toca la zona?
        touches_zone = (
            zone.contains_price(candle.high) or
            zone.contains_price(candle.low) or
            (candle.low <= zone.lower and candle.high >= zone.upper)  # Atraviesa la zona
        )

        if touches_zone:
            zone.touches += 1
            zone.last_touch_time = candle.time
            last_touch_idx = i

    return zone


def detect_zones(
    candles_h4: List[Candle],
    config: dict,
    instrument_config: dict,
) -> List[Zone]:
    """
    Pipeline completo de detección de zonas.

    Args:
        candles_h4: Velas H4 (últimas 200)
        config: zone_detection config del YAML
        instrument_config: Config específica del instrumento

    Returns:
        Lista de zonas válidas (>= min_touches), ordenadas por precio
    """
    # 1. Detectar swing points
    swing_highs, swing_lows = detect_swing_points(
        candles=candles_h4,
        strength=config["swing_strength"],
        min_wick_ratio=config["min_wick_ratio"],
    )

    merge_dist = instrument_config.get("zone_merge_distance", 150)
    min_width = instrument_config.get("min_zone_width", 0)
    max_width = instrument_config.get("max_zone_width", float("inf"))

    # 2. Agrupar en zonas de resistencia
    resistance_zones = cluster_into_zones(
        swing_highs, ZoneType.RESISTANCE, merge_dist, min_width, max_width
    )

    # 3. Agrupar en zonas de soporte
    support_zones = cluster_into_zones(
        swing_lows, ZoneType.SUPPORT, merge_dist, min_width, max_width
    )

    all_zones = resistance_zones + support_zones

    # 4. Contar toques adicionales
    for zone in all_zones:
        count_additional_touches(
            zone, candles_h4,
            min_separation=config["min_touch_separation"]
        )

    # 5. Filtrar por mínimo de toques
    min_touches = config["min_touches"]
    valid_zones = [z for z in all_zones if z.touches >= min_touches]

    # 6. Limitar cantidad de zonas activas
    max_zones = config["max_zones_active"]
    if len(valid_zones) > max_zones:
        # Priorizar por: más toques, luego por más reciente
        valid_zones.sort(key=lambda z: (z.touches, z.last_touch_time or z.origin_candle_time),
                        reverse=True)
        valid_zones = valid_zones[:max_zones]

    # 7. Ordenar por precio (de menor a mayor)
    valid_zones.sort(key=lambda z: z.midpoint)

    logger.info(f"Zonas detectadas: {len(valid_zones)} "
                f"({sum(1 for z in valid_zones if z.zone_type == ZoneType.SUPPORT)} soporte, "
                f"{sum(1 for z in valid_zones if z.zone_type == ZoneType.RESISTANCE)} resistencia)")

    for z in valid_zones:
        logger.debug(f"  {z}")

    return valid_zones


def find_next_opposite_zone(
    current_zone: Zone,
    all_zones: List[Zone],
    direction: str,
) -> Optional[Zone]:
    """
    Encuentra la siguiente zona opuesta para calcular el TP.

    Args:
        current_zone: La zona donde estamos entrando
        all_zones: Todas las zonas activas
        direction: "LONG" o "SHORT"

    Returns:
        La zona opuesta más cercana, o None si no hay
    """
    if direction == "LONG":
        # Buscar la resistencia más cercana por encima
        candidates = [
            z for z in all_zones
            if z.zone_type == ZoneType.RESISTANCE and z.lower > current_zone.upper
        ]
        if candidates:
            return min(candidates, key=lambda z: z.lower)
    else:
        # Buscar el soporte más cercano por debajo
        candidates = [
            z for z in all_zones
            if z.zone_type == ZoneType.SUPPORT and z.upper < current_zone.lower
        ]
        if candidates:
            return max(candidates, key=lambda z: z.upper)

    return None
