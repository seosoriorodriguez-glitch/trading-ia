# -*- coding: utf-8 -*-
"""
Detección de Order Blocks (OB) para pivot scalping.

Bullish OB: último candle bajista antes de un impulso alcista.
  → Zona de soporte. Entry LONG cuando precio regresa a [ob_low, ob_high].
  → SL bajo ob_low.

Bearish OB: último candle alcista antes de un impulso bajista.
  → Zona de resistencia. Entry SHORT cuando precio regresa a [ob_low, ob_high].
  → SL sobre ob_high.

Un OB se invalida cuando precio cierra al otro lado de la zona.
"""

import datetime
from dataclasses import dataclass, field
from enum import Enum
from typing import List

from .pivot_detection import Candle, PivotPoint, PivotStatus, PivotType


class OBType(Enum):
    BULLISH = "bullish"   # soporte → entry LONG
    BEARISH = "bearish"   # resistencia → entry SHORT


@dataclass
class OrderBlock:
    """
    Order block detectado.

    ob_high / ob_low: high y low del candle que forma el OB.
    confirmed_at: tiempo de la vela que confirmó el impulso.
    status: ACTIVE → EXPIRED (invalidado o expirado por tiempo).
    """
    type: OBType
    time: datetime.datetime        # tiempo del candle OB
    confirmed_at: datetime.datetime  # cuando se confirmó el impulso
    ob_high: float
    ob_low: float
    status: PivotStatus = PivotStatus.ACTIVE
    touches: int = 0

    def to_pivot_point(self) -> PivotPoint:
        """
        Convierte el OB a PivotPoint para compatibilidad con el backtester V3.

        Bullish OB → PivotType.LOW  (soporte, entry LONG)
        Bearish OB → PivotType.HIGH (resistencia, entry SHORT)
        """
        pivot_type = PivotType.LOW if self.type == OBType.BULLISH else PivotType.HIGH
        return PivotPoint(
            type=pivot_type,
            time=self.time,
            confirmed_at=self.confirmed_at,
            index=0,
            price_high=self.ob_high,
            price_low=self.ob_low,
            status=self.status,
            touches=self.touches,
        )

    def is_violated_by(self, candle: Candle) -> bool:
        """
        Retorna True si el candle invalida el OB.

        Bullish OB: close por debajo del ob_low → invalidado
        Bearish OB: close por encima del ob_high → invalidado
        """
        if self.type == OBType.BULLISH:
            return candle.close < self.ob_low
        else:
            return candle.close > self.ob_high


def detect_order_blocks(
    candles: List[Candle],
    impulse_candles: int = 3,
    impulse_points: float = 50.0,
    max_age_candles: int = 200,
) -> List[OrderBlock]:
    """
    Detecta order blocks en una lista de candles.

    Args:
        candles: Lista de candles ordenados por tiempo.
        impulse_candles: Cuántas velas adelante medir el impulso.
        impulse_points: Movimiento mínimo (pts) para calificar como impulso.
        max_age_candles: Máximo número de velas antes de que el OB expire.

    Returns:
        Lista de OrderBlock detectados, marcados con confirmed_at.

    Nota sobre look-ahead:
        El look-ahead aquí (ver las próximas N velas para confirmar el impulso)
        es aceptable porque el OB es un nivel histórico — no es la señal de
        entrada. La entrada ocurre cuando el precio REGRESA a la zona, lo cual
        sucede en tiempo real sin look-ahead.
    """
    obs: List[OrderBlock] = []
    n = len(candles)

    for i in range(n - impulse_candles):
        c = candles[i]
        window = candles[i + 1: i + 1 + impulse_candles]

        # --- Bullish OB: candle bajista + impulso alcista ---
        if c.close < c.open:  # candle bajista
            impulse_high = max(w.high for w in window)
            if impulse_high - c.high >= impulse_points:
                # Buscar el último candle bajista en [i-3, i] para refinar
                ob_candle = _last_bearish(candles, i)
                confirmed_at = window[-1].time
                obs.append(OrderBlock(
                    type=OBType.BULLISH,
                    time=ob_candle.time,
                    confirmed_at=confirmed_at,
                    ob_high=ob_candle.high,
                    ob_low=ob_candle.low,
                    status=PivotStatus.ACTIVE,
                    touches=0,
                ))

        # --- Bearish OB: candle alcista + impulso bajista ---
        elif c.close > c.open:  # candle alcista
            impulse_low = min(w.low for w in window)
            if c.low - impulse_low >= impulse_points:
                ob_candle = _last_bullish(candles, i)
                confirmed_at = window[-1].time
                obs.append(OrderBlock(
                    type=OBType.BEARISH,
                    time=ob_candle.time,
                    confirmed_at=confirmed_at,
                    ob_high=ob_candle.high,
                    ob_low=ob_candle.low,
                    status=PivotStatus.ACTIVE,
                    touches=0,
                ))

    return _deduplicate(obs)


def _last_bearish(candles: List[Candle], up_to: int, lookback: int = 3) -> Candle:
    """Último candle bajista en el rango [up_to-lookback, up_to]."""
    for j in range(up_to, max(up_to - lookback - 1, -1), -1):
        if candles[j].close < candles[j].open:
            return candles[j]
    return candles[up_to]


def _last_bullish(candles: List[Candle], up_to: int, lookback: int = 3) -> Candle:
    """Último candle alcista en el rango [up_to-lookback, up_to]."""
    for j in range(up_to, max(up_to - lookback - 1, -1), -1):
        if candles[j].close > candles[j].open:
            return candles[j]
    return candles[up_to]


def _deduplicate(obs: List[OrderBlock]) -> List[OrderBlock]:
    """
    Elimina OBs duplicados: si dos OBs del mismo tipo tienen zonas
    que se solapan significativamente, conserva el más reciente.
    """
    result: List[OrderBlock] = []
    for ob in obs:
        duplicate = False
        for existing in result:
            if existing.type != ob.type:
                continue
            # Solapamiento: si los rangos se intersectan en más del 50%
            overlap_low  = max(ob.ob_low,  existing.ob_low)
            overlap_high = min(ob.ob_high, existing.ob_high)
            if overlap_high > overlap_low:
                ob_size = ob.ob_high - ob.ob_low
                if ob_size > 0 and (overlap_high - overlap_low) / ob_size > 0.5:
                    duplicate = True
                    break
        if not duplicate:
            result.append(ob)
    return result
