# -*- coding: utf-8 -*-
"""
Backtester V5 — Order Blocks

Zonas: order blocks detectados en M5.
  Bullish OB: último candle bajista antes de impulso alcista → soporte, entry LONG.
  Bearish OB: último candle alcista antes de impulso bajista → resistencia, entry SHORT.

SL: debajo del low del OB (bullish) o sobre el high del OB (bearish).
Invalidación: cuando precio cierra al otro lado de la zona → OB expirado.

Hereda toda la lógica de entrada/gestión de V3.
"""

import datetime
from typing import List

from ..core.pivot_detection import (
    PivotPoint, PivotStatus, PivotType,
)
from ..core.order_block_detection import detect_order_blocks, OBType

from .scalping_backtester_v3 import ScalpingBacktesterV3


class ScalpingBacktesterV5(ScalpingBacktesterV3):
    """
    V5: zonas = order blocks detectados en M5.

    Hereda toda la lógica de señal/SL/TP/gestión de V3.
    Solo reemplaza la fuente de zonas y la lógica de invalidación.
    """

    # ------------------------------------------------------------------
    # Detección de zonas: order blocks
    # ------------------------------------------------------------------

    def _detect_all_pivots(self, candles_m15):
        """
        Override: detecta order blocks en lugar de fractales.

        Los OBs se convierten a PivotPoint para compatibilidad con el
        generador de señales de V3:
          Bullish OB → PivotType.LOW  (soporte, entry LONG)
            zone = [ob_low, ob_high]  →  SL = ob_low - buffer
          Bearish OB → PivotType.HIGH (resistencia, entry SHORT)
            zone = [ob_low, ob_high]  →  SL = ob_high + buffer

        Los OBs parten como ACTIVE directamente (ya están confirmados
        por el impulso). No necesitan acumular toques previos.
        """
        cfg = self.config['order_blocks']
        obs = detect_order_blocks(
            candles_m15,
            impulse_candles=cfg.get('impulse_candles', 3),
            impulse_points=cfg.get('impulse_points', 50.0),
            max_age_candles=cfg.get('max_age_candles', 200),
        )

        pivots = []
        for ob in obs:
            pivot_type = PivotType.LOW if ob.type == OBType.BULLISH else PivotType.HIGH
            p = PivotPoint(
                type=pivot_type,
                time=ob.time,
                confirmed_at=ob.confirmed_at,
                index=0,
                price_high=ob.ob_high,
                price_low=ob.ob_low,
                status=PivotStatus.ACTIVE,
                touches=1,               # activo desde el inicio
            )
            pivots.append(p)

        self.all_pivots = pivots

    def _update_pivot_touches_incremental(self, candle, candle_idx: int):
        """
        Override: en lugar de acumular toques, verifica invalidación.

        Un OB se invalida cuando el precio cierra al otro lado de su zona:
          Bullish OB (PivotType.LOW):  close < price_low  → EXPIRED
          Bearish OB (PivotType.HIGH): close > price_high → EXPIRED

        También expira por antigüedad (max_age_candles).
        """
        max_age = self.config['order_blocks'].get('max_age_candles', 200)

        for pivot in self.all_pivots:
            if pivot.status == PivotStatus.EXPIRED:
                continue
            if candle.time <= pivot.confirmed_at:
                continue

            # Invalidación por precio
            if pivot.type == PivotType.LOW:    # Bullish OB
                if candle.close < pivot.price_low:
                    pivot.status = PivotStatus.EXPIRED
                    continue
            else:                               # Bearish OB
                if candle.close > pivot.price_high:
                    pivot.status = PivotStatus.EXPIRED
                    continue

            # Antigüedad: contar velas desde confirmed_at
            # (aproximado: usamos candle_idx como proxy)
            # Guardamos el índice de confirmación en touches como workaround
            if pivot.touches == 1:
                pivot.touches = candle_idx      # "inicio" del conteo
            elif candle_idx - pivot.touches > max_age:
                pivot.status = PivotStatus.EXPIRED

    def _get_active_pivots(self, current_time: datetime.datetime) -> List[PivotPoint]:
        """
        OBs activos y confirmados al momento actual.

        A diferencia de V3, no se requiere min_touch_age_hours porque el OB
        ya viene "probado" por el impulso que lo formó.
        """
        max_active = self.config['order_blocks'].get('max_active_zones', 20)

        eligible = [
            p for p in self.all_pivots
            if p.status == PivotStatus.ACTIVE
            and p.confirmed_at <= current_time
        ]

        # Limitar a los N más recientes por tipo
        highs = sorted(
            [p for p in eligible if p.type == PivotType.HIGH],
            key=lambda p: p.confirmed_at, reverse=True
        )[:max_active]

        lows = sorted(
            [p for p in eligible if p.type == PivotType.LOW],
            key=lambda p: p.confirmed_at, reverse=True
        )[:max_active]

        return highs + lows
