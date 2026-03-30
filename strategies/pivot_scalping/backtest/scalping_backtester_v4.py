# -*- coding: utf-8 -*-
"""
Backtester V4 — Previous Day H/L + Market Structure

Zonas: High y Low del día anterior (2 zonas/día, objetivas, bien separadas).
Dirección: estructura de mercado en tiempo real (HH+HL = long, LH+LL = short).
Entrada: misma lógica V3 (pin bar / engulfing en M1).

Sin look-ahead bias: las zonas del día D se calculan con datos hasta D-1.
La estructura se calcula solo con swings confirmados hasta el momento actual.
"""

import datetime
from typing import List, Optional

from ..core.pivot_detection import (
    PivotPoint, PivotStatus, PivotType,
    detect_pivot_highs, detect_pivot_lows,
)
from ..core.scalping_signals import TradingSignal, SignalType

from .scalping_backtester_v3 import ScalpingBacktesterV3


class ScalpingBacktesterV4(ScalpingBacktesterV3):
    """
    V4: zonas = prev-day H/L + filtro de estructura de mercado.

    Hereda toda la lógica de entrada/SL/TP de V3.
    Solo reemplaza la fuente de zonas y agrega filtro direccional.
    """

    def __init__(self, config: dict, initial_balance: float = 100000.0):
        super().__init__(config, initial_balance)
        self._daily_levels: dict = {}         # date → {'high': float, 'low': float}
        self._struct_highs: list = []          # [(confirmed_at, price_high), ...]
        self._struct_lows:  list = []          # [(confirmed_at, price_low),  ...]
        self._structure_candles: list = []     # candles externos para estructura (ej. M15)

    def set_structure_data(self, candles):
        """
        Inyecta candles externos (ej. M15) para la detección de estructura.
        Debe llamarse antes de run(). Si no se llama, se usa el mismo
        dataset que las zonas (M5).
        """
        self._structure_candles = candles

    # ------------------------------------------------------------------
    # Detección de zonas: prev-day H/L
    # ------------------------------------------------------------------

    def _detect_all_pivots(self, candles_m15):
        """
        Override: no pivots tradicionales.

        Pre-calcula:
          1. H/L diario de cada día del dataset (para zonas).
          2. Swings estructurales con swing_strength mayor (para dirección).
        Las zonas se inyectan dinámicamente en _get_active_pivots.
        """
        # --- 1. H/L diario ---
        from collections import defaultdict
        daily = defaultdict(lambda: {'high': -999999.0, 'low': 999999.0})
        for c in candles_m15:
            d = c.time.date()
            if c.high > daily[d]['high']:
                daily[d]['high'] = c.high
            if c.low < daily[d]['low']:
                daily[d]['low'] = c.low
        self._daily_levels = dict(daily)

        # --- 2. Swings estructurales (solo para dirección, no para zonas) ---
        # Usa candles externos (M15) si se inyectaron, si no usa el mismo dataset
        struct_src = self._structure_candles if self._structure_candles else candles_m15
        s = self.config['pivots'].get('structure_swing_strength', 10)
        sh = detect_pivot_highs(struct_src, swing_strength=s,
                                min_zone_width=0, max_zone_width=999999)
        sl = detect_pivot_lows(struct_src,  swing_strength=s,
                               min_zone_width=0, max_zone_width=999999)
        self._struct_highs = [(p.confirmed_at, p.price_high) for p in sh]
        self._struct_lows  = [(p.confirmed_at, p.price_low)  for p in sl]

        self.all_pivots = []   # se rellena en _get_active_pivots

    def _get_active_pivots(self, current_time: datetime.datetime) -> List[PivotPoint]:
        """
        Retorna exactamente 2 zonas: prev-day high (resistencia) y prev-day low (soporte).
        """
        zone_buffer = self.config['pivots'].get('zone_buffer', 20)
        today    = current_time.date()
        prev_day = today - datetime.timedelta(days=1)
        while prev_day.weekday() >= 5:          # saltar fin de semana
            prev_day -= datetime.timedelta(days=1)

        if prev_day not in self._daily_levels:
            return []

        levels   = self._daily_levels[prev_day]
        ph_price = levels['high']
        pl_price = levels['low']
        day_start = datetime.datetime.combine(today, datetime.time(0, 0))

        resistance = PivotPoint(
            type=PivotType.HIGH,
            time=day_start,
            confirmed_at=day_start,
            index=0,
            price_high=ph_price,
            price_low=ph_price - zone_buffer,
            status=PivotStatus.ACTIVE,
            touches=1,
        )
        support = PivotPoint(
            type=PivotType.LOW,
            time=day_start,
            confirmed_at=day_start,
            index=0,
            price_high=pl_price + zone_buffer,
            price_low=pl_price,
            status=PivotStatus.ACTIVE,
            touches=1,
        )
        return [resistance, support]

    def _update_pivot_touches_incremental(self, candle, candle_idx: int):
        """Override: las zonas diarias no acumulan toques incrementales."""
        pass

    # ------------------------------------------------------------------
    # Filtro de dirección: estructura de mercado
    # ------------------------------------------------------------------

    def _get_market_bias(self, current_time: datetime.datetime) -> Optional[str]:
        """
        Determina la dirección del mercado usando los últimos swings confirmados.

        Necesita al menos 2 swing highs y 2 swing lows confirmados.
          LH + LL → 'short'
          HH + HL → 'long'
          mixto   → None (lateral, no operar)
        """
        recent_h = [(t, p) for t, p in self._struct_highs if t <= current_time][-2:]
        recent_l = [(t, p) for t, p in self._struct_lows  if t <= current_time][-2:]

        if len(recent_h) < 2 or len(recent_l) < 2:
            return None

        lower_highs = recent_h[-1][1] < recent_h[-2][1]
        lower_lows  = recent_l[-1][1] < recent_l[-2][1]
        higher_highs = recent_h[-1][1] > recent_h[-2][1]
        higher_lows  = recent_l[-1][1] > recent_l[-2][1]

        if lower_highs and lower_lows:
            return 'short'
        if higher_highs and higher_lows:
            return 'long'
        return None   # lateral

    def _can_take_trade(self, signal: TradingSignal, current_time: datetime.datetime) -> bool:
        """
        Solo operar en la dirección que confirma la estructura de mercado.
        Si el mercado está lateral (bias=None), no operar.
        """
        bias = self._get_market_bias(current_time)
        if bias is None:
            return False
        return signal.type.value == bias
