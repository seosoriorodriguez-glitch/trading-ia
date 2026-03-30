# -*- coding: utf-8 -*-
"""
Backtester V3 — Pivot Scalping M5/M1 (EXPERIMENTAL)

Cambios respecto al backtester de producción:

PUNTO 2 — Activación correcta del pivot:
  La vela de formación NO cuenta como toque operativo.
  Un pivot es operable desde su primer retorno posterior
  (PivotStatus.FIRST_TOUCH o ACTIVE), no solo desde ACTIVE.
  Esto corrige el bug semántico donde el backtester original
  operaba en zonas sin ningún retorno probado.

PUNTO 3 — Zona simple:
  Sin cambios de código. La zona sigue siendo [low, high] de la
  vela pivot. Los setups de zona ancha se filtran por RR.

PUNTO 4 — Filtro de rechazo real (cierre confirmatorio):
  No basta con que la vela M1 toque la zona. Debe cerrar en el
  lado correcto para confirmar que hubo rechazo real:
    SHORT → close <= pivot.price_high (dentro de zona o por debajo)
    LONG  → close >= pivot.price_low  (dentro de zona o por encima)
  Elimina el caso en que precio rompe la zona, cierra por encima,
  y el backtester generaba señal con SL invertido.

PUNTO 8 — Priorización de zonas:
  Cuando una vela M1 toca múltiples zonas del mismo tipo,
  se selecciona la zona prioritaria antes de generar señal:
    SHORT → zona más alta (price_low más alto)
    LONG  → zona más baja (price_high más bajo)
  Si empate de precio, se usa la zona más reciente.

NO afecta ni modifica el backtester de producción.
"""

from typing import List, Optional
from datetime import datetime

from ..core.pivot_detection import (
    PivotPoint, PivotStatus, PivotType, Candle as M5Candle,
    detect_pivot_highs, detect_pivot_lows,
)
from ..core.scalping_signals import (
    TradingSignal, SignalType, ScalpingSignalGenerator
)
from ..core.rejection_patterns import detect_rejection_patterns

from .scalping_backtester import ScalpingBacktester, Trade


class ScalpingSignalGeneratorV3(ScalpingSignalGenerator):
    """
    Generador de señales V3.

    Cambios respecto al original:
    - Acepta pivots con FIRST_TOUCH (1 retorno posterior) además de ACTIVE (2+).
    - Cuando hay múltiples señales válidas, aplica priorización por zona.
    - SL estructural: SL = max/min(sl_zona, sl_swing_reciente).
    """

    def __init__(self, config: dict):
        super().__init__(config)
        self._recent_candles: List = []  # Velas M5 recientes para SL estructural

    def set_recent_candles(self, candles: List):
        """Actualiza el contexto de velas recientes para el cálculo de SL estructural."""
        self._recent_candles = candles

    def update_pivots(self, pivots: List[PivotPoint]):
        # PUNTO 2: incluir pivots con al menos 1 toque posterior a la formación.
        # FIRST_TOUCH = 1 retorno confirmado. ACTIVE = 2+ retornos.
        self.active_pivots = [
            p for p in pivots
            if p.status in (PivotStatus.FIRST_TOUCH, PivotStatus.ACTIVE)
        ]

    def check_signal(
        self,
        candle_m5: M5Candle,
        previous_m5: Optional[M5Candle],
        all_pivots: List[PivotPoint],
        current_time: datetime
    ) -> Optional[TradingSignal]:
        """
        Verifica señales con priorización de zonas (Punto 8).

        Recopila TODOS los candidatos válidos antes de elegir,
        en lugar de retornar el primero encontrado.
        """
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

        # Recopilar todos los candidatos válidos
        short_candidates: List[TradingSignal] = []
        long_candidates: List[TradingSignal] = []

        for pivot in self.active_pivots:
            if not self._touches_zone(candle_m5, pivot):
                continue

            for pattern in patterns:
                signal = self._validate_signal(
                    pivot, pattern, candle_m5, all_pivots, current_time
                )
                if signal is None:
                    continue

                if signal.type == SignalType.SHORT:
                    short_candidates.append(signal)
                else:
                    long_candidates.append(signal)

        # PUNTO 8: priorización de zonas
        best_short = self._pick_best_short(short_candidates)
        best_long = self._pick_best_long(long_candidates)

        # Si hay candidatos de ambas direcciones, elegir el de mayor R:R
        if best_short and best_long:
            return best_short if best_short.risk_reward >= best_long.risk_reward else best_long

        return best_short or best_long

    def _calculate_stop_loss(self, pivot: PivotPoint, signal_type) -> float:
        """
        PUNTO SL ESTRUCTURAL:
        SL = max/min(sl_zona, sl_swing_reciente)

        Para SHORT: SL = max(zone_high + buffer, swing_high + structure_buffer)
        Para LONG:  SL = min(zone_low  - buffer, swing_low  - structure_buffer)

        Garantiza que el SL nunca sea más ajustado que el de zona,
        y respeta la estructura real del mercado cuando hay un swing
        reciente más extremo que el borde de la zona.
        """
        buffer           = self.config['stop_loss']['buffer_points']
        struct_buffer    = self.config['stop_loss'].get('structure_buffer', 5)

        if signal_type.value == 'short':
            sl_zone = pivot.price_high + buffer

            # Swing estructural: highest high de las últimas N velas M5
            if self._recent_candles:
                swing_high = max(c.high for c in self._recent_candles)
                sl_structure = swing_high + struct_buffer
                sl = max(sl_zone, sl_structure)
                if sl > sl_zone:
                    pass  # estructura más amplia — se usa sl_structure
            else:
                sl = sl_zone

            return sl

        else:  # long
            sl_zone = pivot.price_low - buffer

            # Swing estructural: lowest low de las últimas N velas M5
            if self._recent_candles:
                swing_low = min(c.low for c in self._recent_candles)
                sl_structure = swing_low - struct_buffer
                sl = min(sl_zone, sl_structure)
            else:
                sl = sl_zone

            return sl

    def _calculate_take_profit(
        self,
        pivot: PivotPoint,
        entry: float,
        stop_loss: float,
        signal_type,
        all_pivots: List[PivotPoint]
    ) -> float:
        """
        PUNTO TP — Pivot opuesto activo más cercano al entry.

        Mejoras respecto al original:
        - Solo pivots activos (FIRST_TOUCH o ACTIVE) como candidatos.
        - Referencia: entry price (no el borde de la zona).
          SHORT: pivot LOW más cercano por debajo del entry (price_high más alto).
          LONG:  pivot HIGH más cercano por encima del entry (price_low más bajo).
        - Desempate: pivot más reciente.
        - Fallback: entry ± risk × fallback_rr si no hay candidatos.
        """
        tp_config = self.config['take_profit']
        offset    = tp_config.get('structure', {}).get('offset_points', 3)
        risk      = abs(entry - stop_loss)

        active_statuses = (PivotStatus.FIRST_TOUCH, PivotStatus.ACTIVE)

        if signal_type.value == 'short':
            # Buscar pivot LOW activo cuyo price_high esté por debajo del entry
            candidates = [
                p for p in all_pivots
                if p.type == PivotType.LOW
                and p.status in active_statuses
                and p.price_high < entry
            ]
            if candidates:
                # El más cercano = mayor price_high; desempate = más reciente
                best = max(candidates, key=lambda p: (p.price_high, p.time))
                tp = best.price_high + offset
                # Validar R:R mínimo
                if risk > 0 and abs(tp - entry) / risk >= tp_config.get('min_rr_ratio', 1.2):
                    return tp

            # Fallback: R:R fijo
            fallback_rr = tp_config.get('fallback_rr', 1.5)
            return entry - (risk * fallback_rr)

        else:  # long
            # Buscar pivot HIGH activo cuyo price_low esté por encima del entry
            candidates = [
                p for p in all_pivots
                if p.type == PivotType.HIGH
                and p.status in active_statuses
                and p.price_low > entry
            ]
            if candidates:
                # El más cercano = menor price_low; desempate = más reciente
                best = min(candidates, key=lambda p: (p.price_low, -p.time.timestamp()))
                tp = best.price_low - offset
                if risk > 0 and abs(tp - entry) / risk >= tp_config.get('min_rr_ratio', 1.2):
                    return tp

            # Fallback: R:R fijo
            fallback_rr = tp_config.get('fallback_rr', 1.5)
            return entry + (risk * fallback_rr)

    def _touches_zone(self, candle: M5Candle, pivot: PivotPoint) -> bool:
        """
        PUNTO 4 — Filtro de rechazo real.

        Además del overlap con la zona, exige que el cierre confirme
        que el precio fue rechazado en la dirección correcta:
          SHORT: close <= price_high  (cerró dentro de zona o por debajo)
          LONG:  close >= price_low   (cerró dentro de zona o por encima)
        """
        if pivot.type == PivotType.HIGH:  # SHORT
            overlaps = (candle.low <= pivot.price_high and
                        candle.high >= pivot.price_low)
            closes_correctly = candle.close <= pivot.price_high
            return overlaps and closes_correctly
        else:  # PivotType.LOW → LONG
            overlaps = (candle.high >= pivot.price_low and
                        candle.low <= pivot.price_high)
            closes_correctly = candle.close >= pivot.price_low
            return overlaps and closes_correctly

    def _pick_best_short(self, candidates: List[TradingSignal]) -> Optional[TradingSignal]:
        """
        SHORT: zona más alta = mayor resistencia.
        Criterio: price_low del pivot más alto.
        Desempate: pivot más reciente.
        """
        if not candidates:
            return None
        return max(
            candidates,
            key=lambda s: (s.pivot.price_low, s.pivot.time)
        )

    def _pick_best_long(self, candidates: List[TradingSignal]) -> Optional[TradingSignal]:
        """
        LONG: zona más baja = mayor soporte.
        Criterio: price_high del pivot más bajo.
        Desempate: pivot más reciente.
        """
        if not candidates:
            return None
        return min(
            candidates,
            key=lambda s: (s.pivot.price_high, -s.pivot.time.timestamp())
        )


class ScalpingBacktesterV3(ScalpingBacktester):
    """
    Backtester V3 — implementa Puntos 2, 3, 4 y 8.

    Hereda de ScalpingBacktester y sobreescribe únicamente
    los métodos afectados por los cambios v3.
    """

    def __init__(self, config: dict, initial_balance: float = 100000.0):
        super().__init__(config, initial_balance)
        # Reemplazar el generador de señales con la versión V3
        self.signal_generator = ScalpingSignalGeneratorV3(config)

        # V3: sin protecciones de zona por sesión ni bloqueo permanente.
        # Se evaluará el rendimiento base con las mejoras estructurales.
        self.zone_session_trades = {}
        self.blocked_zones = {}

        # FIX look-ahead bias: rastreo incremental de toques por pivot.
        # Clave: id(pivot), Valor: índice en candles_m15 del último toque.
        self._pivot_last_touch_idx: dict = {}

    # ------------------------------------------------------------------
    # FIX: status de pivots calculado incrementalmente (sin look-ahead)
    # ------------------------------------------------------------------

    def _detect_all_pivots(self, candles_m15):
        """
        Override: zona estrecha alrededor del nivel exacto del pivot.

        En lugar del cuerpo completo de la vela (50-150 pts en US30),
        la zona queda definida como nivel exacto ± zone_buffer:
          HIGH (resistencia): [candle.high - zone_buffer, candle.high]
          LOW  (soporte):     [candle.low,  candle.low  + zone_buffer]

        Reproduce cómo TradingView marca los pivots: nivel preciso con
        margen mínimo, no una zona de ancho variable.
        Los toques se calculan incrementalmente para evitar look-ahead bias.
        """
        pivot_config = self.config['pivots']
        zone_buffer  = pivot_config.get('zone_buffer', 20)

        highs = detect_pivot_highs(
            candles_m15,
            swing_strength=pivot_config['swing_strength'],
            min_zone_width=0,
            max_zone_width=999999,
        )
        lows = detect_pivot_lows(
            candles_m15,
            swing_strength=pivot_config['swing_strength'],
            min_zone_width=0,
            max_zone_width=999999,
        )

        # Redefinir zona: nivel exacto ± zone_buffer
        for p in highs:
            level        = p.price_high  # candle.high — el nivel del swing
            p.price_high = level
            p.price_low  = level - zone_buffer

        for p in lows:
            level        = p.price_low   # candle.low — el nivel del swing
            p.price_high = level + zone_buffer
            p.price_low  = level

        self.all_pivots = highs + lows
        # Todos parten como CREATED — los toques se acumulan en tiempo real.

    def _update_pivot_touches_incremental(self, candle, candle_idx: int):
        """
        Actualiza el status de todos los pivots usando UNA sola vela nueva.

        Garantías:
        - La vela de formación nunca cuenta (candle.time > pivot.time).
        - Solo pivots ya confirmados (confirmed_at <= candle.time).
        - Separación mínima medida por índice en candles_m15 (igual que base).
        - Máximo de toques respetado; pasa a EXPIRED al superarlo.
        """
        min_sep    = self.config['pivots']['min_touch_separation']
        max_touches = self.config['pivots']['max_touches']

        for pivot in self.all_pivots:
            if candle.time <= pivot.time:       # vela de formación o anterior
                continue
            if pivot.confirmed_at > candle.time:  # pivot aún no confirmado
                continue
            if pivot.status == PivotStatus.EXPIRED:
                continue
            if pivot.touches >= max_touches:
                pivot.status = PivotStatus.EXPIRED
                continue

            # Separación mínima entre toques (en índice de candles_m15)
            pid      = id(pivot)
            last_idx = self._pivot_last_touch_idx.get(pid, -min_sep)
            if candle_idx - last_idx < min_sep:
                continue

            if pivot.touches_zone(candle):
                pivot.touches += 1
                pivot.touch_times.append(candle.time)
                self._pivot_last_touch_idx[pid] = candle_idx

                if pivot.touches == 1:
                    pivot.status = PivotStatus.FIRST_TOUCH
                elif pivot.touches >= 2:
                    pivot.status = PivotStatus.ACTIVE

    def _open_trade_if_valid(self, pending_signal, candle_time: datetime, next_open: float) -> bool:
        """
        Re-valida min_risk_points con el entry real (next open) antes de abrir.

        El backtester base valida el riesgo al close de la señal, pero la
        entrada real ocurre al open de la siguiente vela. Si el precio abre
        más cerca del SL, el riesgo real puede caer por debajo del mínimo.

        Returns True si el trade se abrió, False si fue descartado.
        """
        min_risk = self.config['stop_loss'].get('min_risk_points', 20)
        actual_risk = abs(next_open - pending_signal.stop_loss)

        if actual_risk < min_risk:
            print(f"   ⚠️  Trade descartado: riesgo real {actual_risk:.1f} pts < min {min_risk} pts (entry ajustado al open)")
            return False

        # Ajustar entry y TP al open real
        original_risk = abs(pending_signal.entry_price - pending_signal.stop_loss)
        original_reward = abs(pending_signal.take_profit - pending_signal.entry_price)
        original_rr = original_reward / original_risk if original_risk > 0 else 2.0

        if pending_signal.type.value == 'long':
            new_tp = next_open + (original_risk * original_rr)
        else:
            new_tp = next_open - (original_risk * original_rr)

        pending_signal.entry_price = next_open
        pending_signal.take_profit = new_tp
        pending_signal.risk_reward = original_rr

        self._open_trade(pending_signal, candle_time)
        return True

    def run(self, df_m15, df_m5, instrument: str = "US30"):
        """
        Override del loop principal para usar _open_trade_if_valid
        en lugar de abrir directamente al next open.
        """
        import pandas as pd

        print(f"\n{'='*80}")
        print(f"  BACKTEST: {instrument} - Pivot Scalping")
        print(f"{'='*80}\n")

        from ..core.pivot_detection import Candle as M15Candle
        from ..core.rejection_patterns import Candle as M5Candle

        candles_m15 = self._df_to_candles(df_m15, is_m15=True)
        candles_m5  = self._df_to_candles(df_m5,  is_m15=False)

        print(f"📊 Datos cargados:")
        print(f"   M15: {len(candles_m15)} velas")
        print(f"   M5:  {len(candles_m5)} velas")
        print(f"   Período: {candles_m5[0].time} → {candles_m5[-1].time}\n")

        print("🔍 Detectando pivots...")
        self._detect_all_pivots(candles_m15)
        print(f"   Pivot Highs: {len([p for p in self.all_pivots if p.type.value == 'resistance'])}")
        print(f"   Pivot Lows:  {len([p for p in self.all_pivots if p.type.value == 'support'])}\n")

        print("⚡ Ejecutando backtest...\n")

        pending_signal = None
        current_day    = None
        m15_ptr        = 0   # puntero incremental sobre candles_m15

        for i, candle_m5 in enumerate(candles_m5):
            candle_day = candle_m5.time.date()
            if current_day != candle_day:
                self.zone_session_trades.clear()
                current_day = candle_day

            # Avanzar el puntero M15: procesar todas las velas M15 cuyo tiempo
            # sea <= tiempo actual de la vela M1.  Esto actualiza el status de
            # los pivots usando solo información disponible hasta ahora.
            while (m15_ptr < len(candles_m15) and
                   candles_m15[m15_ptr].time <= candle_m5.time):
                self._update_pivot_touches_incremental(candles_m15[m15_ptr], m15_ptr)
                m15_ptr += 1

            active_pivots = self._get_active_pivots(candle_m5.time)
            self.signal_generator.update_pivots(active_pivots)

            # Señal pendiente: re-validar riesgo con el open real antes de abrir
            if pending_signal is not None and i > 0:
                self._open_trade_if_valid(pending_signal, candle_m5.time, candle_m5.open)
                pending_signal = None

            self._update_open_trades(candle_m5)

            max_trades = self.config['sizing']['max_simultaneous_trades']
            if len(self.active_trades) < max_trades and pending_signal is None:
                previous_m5 = candles_m5[i - 1] if i > 0 else None

                # SL estructural: pasar las últimas N velas M5 ANTES de la señal
                lookback = self.config['stop_loss'].get('swing_lookback', 10)
                recent = candles_m5[max(0, i - lookback):i]
                self.signal_generator.set_recent_candles(recent)

                # Solo pasar pivots ya confirmados hasta este momento.
                # Evita look-ahead en el cálculo de TP (que busca el pivot
                # opuesto más cercano para definir el target estructural).
                confirmed_for_tp = [
                    p for p in self.all_pivots
                    if p.confirmed_at <= candle_m5.time
                ]
                signal = self.signal_generator.check_signal(
                    candle_m5, previous_m5, confirmed_for_tp, candle_m5.time
                )

                if (signal
                        and self._is_session_allowed(candle_m5.time)
                        and self._can_take_trade(signal, candle_m5.time)):
                    pending_signal = signal

            self._record_equity(candle_m5.time)

        self._close_all_trades(candles_m5[-1])
        return self._generate_results()

    def _get_active_pivots(self, current_time: datetime) -> List[PivotPoint]:
        """
        Pivots elegibles con filtro de antigüedad del primer toque.

        Un pivot solo es operable si su primer toque ocurrió al menos
        min_touch_age_hours antes del momento actual. Esto le da tiempo
        a la zona de "probarse" con datos reales sin usar información futura.
        """
        from datetime import timedelta

        min_age_h = self.config['pivots'].get('min_touch_age_hours', 0)
        min_age   = timedelta(hours=min_age_h)

        confirmed = [
            p for p in self.all_pivots
            if p.confirmed_at <= current_time
        ]

        eligible = []
        for p in confirmed:
            if p.status not in (PivotStatus.FIRST_TOUCH, PivotStatus.ACTIVE):
                continue
            if p.touches >= self.config['pivots']['max_touches']:
                continue
            if p.status == PivotStatus.EXPIRED:
                continue
            # Filtro de antigüedad: primer toque debe tener al menos min_age
            if min_age_h > 0 and p.touch_times:
                if current_time - p.touch_times[0] < min_age:
                    continue
            eligible.append(p)

        eligible.sort(key=lambda p: p.time, reverse=True)
        max_zones = self.config['pivots']['max_active_zones']
        return eligible[:max_zones]

    def _can_take_trade(self, signal: TradingSignal, current_time: datetime) -> bool:
        """
        V3: sin protecciones de zona por sesión ni bloqueo permanente.
        El filtrado de calidad lo hacen RR y risk_points.
        """
        return True
