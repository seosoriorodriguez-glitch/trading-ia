"""
Backtester para estrategia de Pivot Scalping

Características:
- Break Even automático en 1:1
- Trailing Stop por estructura de velas
- Gestión de múltiples trades simultáneos
- Cálculo de métricas detalladas
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from enum import Enum
import pandas as pd

from ..core.pivot_detection import (
    PivotPoint, detect_pivot_highs, detect_pivot_lows,
    update_pivot_touches, filter_active_pivots, Candle as M15Candle
)
from ..core.scalping_signals import (
    TradingSignal, SignalType, ScalpingSignalGenerator
)
from ..core.rejection_patterns import Candle as M5Candle


class TradeStatus(Enum):
    """Estado del trade"""
    OPEN = "open"
    CLOSED_TP = "closed_tp"
    CLOSED_SL = "closed_sl"
    CLOSED_BE = "closed_be"
    CLOSED_TRAILING = "closed_trailing"


@dataclass
class Trade:
    """
    Trade ejecutado
    
    Attributes:
        id: ID único del trade
        signal: Señal que generó el trade
        entry_time: Tiempo de entrada
        entry_price: Precio de entrada
        stop_loss: Stop loss actual (puede moverse con BE/Trailing)
        original_stop_loss: Stop loss original (para cálculos de BE)
        take_profit: Take profit
        size: Tamaño del trade
        status: Estado actual
        exit_time: Tiempo de salida (si cerrado)
        exit_price: Precio de salida (si cerrado)
        pnl: Profit/Loss en puntos
        pnl_pct: Profit/Loss en porcentaje
        be_activated: Si se activó break even
        trailing_activated: Si se activó trailing stop
        max_favorable: Máximo movimiento favorable
        max_adverse: Máximo movimiento adverso
    """
    id: int
    signal: TradingSignal
    entry_time: datetime
    entry_price: float
    stop_loss: float
    original_stop_loss: float  # Nuevo: SL original para cálculos
    take_profit: float
    size: float = 0.01
    status: TradeStatus = TradeStatus.OPEN
    exit_time: Optional[datetime] = None
    exit_price: Optional[float] = None
    pnl: float = 0.0
    pnl_pct: float = 0.0
    be_activated: bool = False
    trailing_activated: bool = False
    max_favorable: float = 0.0
    max_adverse: float = 0.0
    notes: List[str] = field(default_factory=list)
    
    def update_extremes(self, current_price: float):
        """Actualiza máximos favorables/adversos"""
        if self.signal.type == SignalType.LONG:
            # LONG
            favorable = current_price - self.entry_price
            adverse = self.entry_price - current_price
        else:
            # SHORT
            favorable = self.entry_price - current_price
            adverse = current_price - self.entry_price
        
        self.max_favorable = max(self.max_favorable, favorable)
        self.max_adverse = max(self.max_adverse, adverse)


class ScalpingBacktester:
    """
    Backtester para estrategia de Pivot Scalping
    """
    
    def __init__(self, config: dict, initial_balance: float = 100000.0):
        """
        Inicializa el backtester
        
        NUEVAS PROTECCIONES ANTI-OVERTRADING:
        - Una entrada por zona por sesión
        - Bloqueo permanente de zona después de loss
        
        Args:
            config: Configuración de la estrategia
            initial_balance: Balance inicial
        """
        self.config = config
        self.initial_balance = initial_balance
        self.balance = initial_balance
        
        self.signal_generator = ScalpingSignalGenerator(config)
        
        self.all_pivots: List[PivotPoint] = []
        self.active_trades: List[Trade] = []
        self.closed_trades: List[Trade] = []
        self.trade_counter = 0
        
        self.equity_curve = []
        
        # NUEVAS PROTECCIONES ANTI-OVERTRADING
        self.zone_session_trades = {}  # {zone_id_session: timestamp}
        self.blocked_zones = {}  # {zone_id: "PERMANENT"}
    
    def run(
        self,
        df_m15: pd.DataFrame,
        df_m5: pd.DataFrame,
        instrument: str = "US30"
    ) -> pd.DataFrame:
        """
        Ejecuta el backtest
        
        Args:
            df_m15: DataFrame con datos M15 (time, open, high, low, close, volume)
            df_m5: DataFrame con datos M5 (time, open, high, low, close, volume)
            instrument: Nombre del instrumento
        
        Returns:
            DataFrame con resultados de trades
        """
        print(f"\n{'='*80}")
        print(f"  BACKTEST: {instrument} - Pivot Scalping")
        print(f"{'='*80}\n")
        
        # Convertir a listas de Candle
        candles_m15 = self._df_to_candles(df_m15, is_m15=True)
        candles_m5 = self._df_to_candles(df_m5, is_m15=False)
        
        print(f"📊 Datos cargados:")
        print(f"   M15: {len(candles_m15)} velas")
        print(f"   M5:  {len(candles_m5)} velas")
        print(f"   Período: {candles_m5[0].time} → {candles_m5[-1].time}\n")
        
        # Detectar pivots en M15
        print("🔍 Detectando pivots...")
        self._detect_all_pivots(candles_m15)
        print(f"   Pivot Highs: {len([p for p in self.all_pivots if p.type.value == 'resistance'])}")
        print(f"   Pivot Lows:  {len([p for p in self.all_pivots if p.type.value == 'support'])}\n")
        
        # Simular vela por vela en M5
        print("⚡ Ejecutando backtest...\n")
        
        pending_signal = None  # Señal detectada, esperando siguiente vela para entrar
        current_day = None  # Para detectar cambio de día
        
        for i, candle_m5 in enumerate(candles_m5):
            # Reset diario de zonas por sesión
            candle_day = candle_m5.time.date()
            if current_day != candle_day:
                self.zone_session_trades.clear()
                current_day = candle_day
            
            # Actualizar pivots activos
            active_pivots = self._get_active_pivots(candle_m5.time)
            self.signal_generator.update_pivots(active_pivots)
            
            # Si hay señal pendiente de vela anterior, entrar ahora con open de esta vela
            if pending_signal is not None and i > 0:
                # Entry price = open de esta vela (no close de la anterior)
                new_entry = candle_m5.open
                
                # Recalcular SL y TP basado en el nuevo entry
                # SL se mantiene igual (basado en pivot)
                # TP se ajusta para mantener el mismo R:R
                original_risk = abs(pending_signal.entry_price - pending_signal.stop_loss)
                original_reward = abs(pending_signal.take_profit - pending_signal.entry_price)
                original_rr = original_reward / original_risk if original_risk > 0 else 2.0
                
                # Nuevo TP manteniendo el R:R
                if pending_signal.type.value == 'long':
                    new_tp = new_entry + (original_risk * original_rr)
                else:
                    new_tp = new_entry - (original_risk * original_rr)
                
                pending_signal.entry_price = new_entry
                pending_signal.take_profit = new_tp
                pending_signal.risk_reward = original_rr
                
                self._open_trade(pending_signal, candle_m5.time)
                pending_signal = None
            
            # Actualizar trades abiertos
            self._update_open_trades(candle_m5)
            
            # Verificar señales (solo si hay espacio para más trades)
            max_trades = self.config['sizing']['max_simultaneous_trades']
            if len(self.active_trades) < max_trades and pending_signal is None:
                previous_m5 = candles_m5[i-1] if i > 0 else None
                
                signal = self.signal_generator.check_signal(
                    candle_m5,
                    previous_m5,
                    self.all_pivots,
                    candle_m5.time
                )
                
                if signal:
                    # Filtro de sesión (si está habilitado)
                    if self._is_session_allowed(candle_m5.time):
                        # NUEVAS PROTECCIONES
                        if self._can_take_trade(signal, candle_m5.time):
                            # NO entrar inmediatamente - esperar siguiente vela
                            pending_signal = signal
            
            # Registrar equity
            self._record_equity(candle_m5.time)
        
        # Cerrar trades abiertos al final
        self._close_all_trades(candles_m5[-1])
        
        # Generar resultados
        return self._generate_results()
    
    def _df_to_candles(self, df: pd.DataFrame, is_m15: bool) -> List:
        """Convierte DataFrame a lista de Candle"""
        candles = []
        
        for _, row in df.iterrows():
            if is_m15:
                candle = M15Candle(
                    time=pd.to_datetime(row['time']),
                    open=row['open'],
                    high=row['high'],
                    low=row['low'],
                    close=row['close'],
                    volume=row.get('volume', 0)
                )
            else:
                candle = M5Candle(
                    open=row['open'],
                    high=row['high'],
                    low=row['low'],
                    close=row['close']
                )
                candle.time = pd.to_datetime(row['time'])
            
            candles.append(candle)
        
        return candles
    
    def _detect_all_pivots(self, candles_m15: List[M15Candle]):
        """Detecta todos los pivots en M15"""
        pivot_config = self.config['pivots']
        
        # Detectar pivot highs
        highs = detect_pivot_highs(
            candles_m15,
            swing_strength=pivot_config['swing_strength'],
            min_zone_width=pivot_config['min_zone_width'],
            max_zone_width=pivot_config['max_zone_width']
        )
        
        # Detectar pivot lows
        lows = detect_pivot_lows(
            candles_m15,
            swing_strength=pivot_config['swing_strength'],
            min_zone_width=pivot_config['min_zone_width'],
            max_zone_width=pivot_config['max_zone_width']
        )
        
        # Combinar y actualizar toques
        self.all_pivots = highs + lows
        
        for pivot in self.all_pivots:
            update_pivot_touches(
                pivot,
                candles_m15,
                min_separation=pivot_config['min_touch_separation']
            )
    
    def _get_active_pivots(self, current_time: datetime) -> List[PivotPoint]:
        """
        Obtiene pivots activos en el tiempo actual
        
        CRÍTICO: Solo incluye pivots cuyo confirmed_at <= current_time
        Esto evita hindsight bias (usar pivots antes de que se confirmen)
        """
        # Primero filtrar por confirmación (NO HINDSIGHT)
        confirmed_pivots = [p for p in self.all_pivots if p.confirmed_at <= current_time]
        
        # Luego aplicar filtros normales
        return filter_active_pivots(
            confirmed_pivots,
            current_time,
            expiry_candles=self.config['pivots']['expiry_candles'],
            max_touches=self.config['pivots']['max_touches'],
            max_active=self.config['pivots']['max_active_zones']
        )
    
    def _is_session_allowed(self, time: datetime) -> bool:
        """Verifica si la hora está dentro de las sesiones permitidas"""
        if 'filters' not in self.config or 'time' not in self.config['filters']:
            return True  # Sin filtro, permitir siempre
        
        time_filter = self.config['filters']['time']
        if not time_filter.get('enabled', False):
            return True
        
        # Verificar día de la semana (1=Lunes, 7=Domingo)
        weekday = time.isoweekday()
        allowed_days = time_filter.get('allowed_days', [1, 2, 3, 4, 5])
        if weekday not in allowed_days:
            return False
        
        # Verificar sesiones
        sessions = time_filter.get('sessions', {})
        if not sessions:
            return True  # Sin sesiones definidas, permitir siempre
        
        hour_minute = time.hour * 60 + time.minute
        
        for session_name, session_config in sessions.items():
            start_str = session_config.get('start', '00:00')
            end_str = session_config.get('end', '23:59')
            
            start_hour, start_min = map(int, start_str.split(':'))
            end_hour, end_min = map(int, end_str.split(':'))
            
            start_minutes = start_hour * 60 + start_min
            end_minutes = end_hour * 60 + end_min
            
            if start_minutes <= hour_minute < end_minutes:
                return True
        
        return False  # No está en ninguna sesión permitida
    
    def _get_current_session(self, time: datetime) -> Optional[str]:
        """
        Detecta sesión actual (Londres o NY)
        Londres: 8-16 UTC
        NY: 13-21 UTC
        """
        hour = time.hour
        
        if 8 <= hour < 16:
            return "LONDON"
        elif 13 <= hour < 21:
            return "NY"
        else:
            return None  # Fuera de horario
    
    def _get_zone_id(self, signal: TradingSignal) -> str:
        """Genera ID único para una zona pivot"""
        pivot_type = "HIGH" if signal.type == SignalType.SHORT else "LOW"
        pivot_price = signal.pivot.price_high if signal.type == SignalType.SHORT else signal.pivot.price_low
        return f"{pivot_type}_{pivot_price:.1f}"
    
    def _can_take_trade(self, signal: TradingSignal, current_time: datetime) -> bool:
        """
        Verifica si se puede tomar un trade según las nuevas protecciones
        
        PROTECCIÓN 1: Zona bloqueada permanentemente (después de loss)
        PROTECCIÓN 2: Una entrada por zona por sesión
        """
        zone_id = self._get_zone_id(signal)
        
        # Protección 1: Zona bloqueada
        if zone_id in self.blocked_zones:
            return False
        
        # Protección 2: Una entrada por zona por sesión
        current_session = self._get_current_session(current_time)
        if current_session:
            zone_session_id = f"{zone_id}_{current_session}"
            if zone_session_id in self.zone_session_trades:
                return False
        
        return True
    
    def _open_trade(self, signal: TradingSignal, entry_time: datetime):
        """Abre un nuevo trade"""
        self.trade_counter += 1
        
        # NO calcular size - usaremos normalización por riesgo fijo
        # Cada trade arriesga exactamente risk_per_trade_pct del balance
        
        trade = Trade(
            id=self.trade_counter,
            signal=signal,
            entry_time=entry_time,
            entry_price=signal.entry_price,
            stop_loss=signal.stop_loss,
            original_stop_loss=signal.stop_loss,  # Guardar SL original
            take_profit=signal.take_profit,
            size=1.0  # No usado - solo para compatibilidad
        )
        
        self.active_trades.append(trade)
        
        # Registrar zona operada en esta sesión
        current_session = self._get_current_session(entry_time)
        if current_session:
            zone_id = self._get_zone_id(signal)
            zone_session_id = f"{zone_id}_{current_session}"
            self.zone_session_trades[zone_session_id] = entry_time
        
        risk_pts = abs(signal.entry_price - signal.stop_loss)
        print(f"📈 Trade #{trade.id} - {signal.type.value.upper()}")
        print(f"   Entry: {signal.entry_price:.2f} | SL: {signal.stop_loss:.2f} | TP: {signal.take_profit:.2f}")
        print(f"   Risk: {risk_pts:.1f} pts | R:R: {signal.risk_reward:.2f} | {signal.notes}")
    
    def _update_open_trades(self, candle: M5Candle):
        """
        Actualiza trades abiertos con CONSERVATIVE FILL
        
        CRÍTICO: Evalúa en orden correcto para evitar look-ahead bias.
        Si SL y BE trigger están en la misma vela, asume el peor caso.
        """
        for trade in self.active_trades[:]:  # Copiar lista para poder modificar
            # Actualizar extremos
            trade.update_extremes(candle.close)
            
            # PASO 1: Verificar si SL ORIGINAL se tocó (antes de moverlo)
            # Este es el paso más crítico para evitar look-ahead bias
            original_sl = trade.stop_loss
            sl_hit = self._check_sl_hit(trade, candle)
            
            if sl_hit:
                # CASO AMBIGUO: ¿SL y BE trigger en la misma vela?
                if not trade.be_activated:
                    be_could_activate = self._be_could_activate_in_candle(trade, candle)
                    
                    if be_could_activate:
                        # Ambiguo: precio podría haber alcanzado BE primero
                        # CONSERVATIVE FILL: asumir que SL se tocó PRIMERO
                        # EXCEPCIÓN: si la vela abre por encima/debajo del trigger
                        if self._candle_opens_past_be_trigger(trade, candle):
                            # Vela abre más allá del BE trigger
                            # Sabemos que BE se activó primero
                            self._activate_break_even(trade, candle)
                            # Verificar si el nuevo SL también se tocó
                            if self._check_sl_hit(trade, candle):
                                status = TradeStatus.CLOSED_BE
                                self._close_trade(trade, trade.stop_loss, candle.time, status)
                            continue
                        else:
                            # PEOR CASO: SL hit antes de BE
                            self._close_trade(trade, original_sl, candle.time, TradeStatus.CLOSED_SL)
                            continue
                    else:
                        # SL hit limpio, sin ambigüedad
                        self._close_trade(trade, original_sl, candle.time, TradeStatus.CLOSED_SL)
                        continue
                else:
                    # BE ya estaba activado, SL hit es legítimo
                    status = TradeStatus.CLOSED_BE if abs(trade.stop_loss - trade.entry_price) < 10 else TradeStatus.CLOSED_TRAILING
                    self._close_trade(trade, trade.stop_loss, candle.time, status)
                    continue
            
            # PASO 2: SL no se tocó - ahora sí podemos verificar BE/Trailing/TP
            
            # Verificar Break Even
            if not trade.be_activated:
                self._check_break_even(trade, candle)
            
            # Verificar Trailing Stop
            if trade.be_activated and not trade.trailing_activated:
                self._check_trailing_activation(trade, candle)
            
            # Actualizar Trailing Stop
            if trade.trailing_activated:
                self._update_trailing_stop(trade, candle)
            
            # Verificar TP
            self._check_tp_hit(trade, candle)
    
    def _check_sl_hit(self, trade: Trade, candle: M5Candle) -> bool:
        """Verifica si el SL se tocó en esta vela"""
        if trade.signal.type == SignalType.LONG:
            return candle.low <= trade.stop_loss
        else:
            return candle.high >= trade.stop_loss
    
    def _be_could_activate_in_candle(self, trade: Trade, candle: M5Candle) -> bool:
        """Verifica si el BE trigger pudo alcanzarse en esta vela"""
        if not self.config['break_even']['enabled']:
            return False
        
        trigger_rr = self.config['break_even']['trigger_rr']
        risk = abs(trade.entry_price - trade.original_stop_loss)  # Usar SL original
        
        if trade.signal.type == SignalType.LONG:
            target = trade.entry_price + (risk * trigger_rr)
            return candle.high >= target
        else:
            target = trade.entry_price - (risk * trigger_rr)
            return candle.low <= target
    
    def _candle_opens_past_be_trigger(self, trade: Trade, candle: M5Candle) -> bool:
        """Verifica si la vela abre más allá del BE trigger"""
        trigger_rr = self.config['break_even']['trigger_rr']
        risk = abs(trade.entry_price - trade.original_stop_loss)  # Usar SL original
        
        if trade.signal.type == SignalType.LONG:
            target = trade.entry_price + (risk * trigger_rr)
            return candle.open >= target
        else:
            target = trade.entry_price - (risk * trigger_rr)
            return candle.open <= target
    
    def _activate_break_even(self, trade: Trade, candle: M5Candle):
        """Activa Break Even (mueve SL a entrada + offset)"""
        offset = self.config['break_even']['offset_points']
        
        if trade.signal.type == SignalType.LONG:
            trade.stop_loss = trade.entry_price + offset
        else:
            trade.stop_loss = trade.entry_price - offset
        
        trade.be_activated = True
        trade.notes.append(f"BE activado @ {candle.close:.2f}")
    
    def _check_break_even(self, trade: Trade, candle: M5Candle):
        """Verifica y activa Break Even"""
        if not self.config['break_even']['enabled']:
            return
        
        if self._be_could_activate_in_candle(trade, candle):
            self._activate_break_even(trade, candle)
    
    def _check_trailing_activation(self, trade: Trade, candle: M5Candle):
        """Verifica activación de Trailing Stop"""
        if not self.config['trailing_stop']['enabled']:
            return
        
        # Ya se activó con BE
        trade.trailing_activated = True
    
    def _update_trailing_stop(self, trade: Trade, candle: M5Candle):
        """
        Actualiza Trailing Stop por estructura de velas
        
        Ahora con min_improvement_points: solo mueve el SL si la mejora
        es de al menos N puntos. Esto evita trailing por ruido.
        """
        if self.config['trailing_stop']['method'] != 'candle_structure':
            return
        
        # Obtener min_improvement_points (default: 0 para backward compatibility)
        min_improvement = self.config['trailing_stop'].get('min_improvement_points', 0)
        
        if trade.signal.type == SignalType.LONG:
            # LONG: mover SL al low de la vela si es mayor que SL actual
            new_sl = candle.low
            improvement = new_sl - trade.stop_loss
            
            if improvement > 0 and improvement >= min_improvement:
                trade.stop_loss = new_sl
                trade.notes.append(f"Trailing @ {new_sl:.2f} (+{improvement:.1f}pts)")
        else:
            # SHORT: mover SL al high de la vela si es menor que SL actual
            new_sl = candle.high
            improvement = trade.stop_loss - new_sl
            
            if improvement > 0 and improvement >= min_improvement:
                trade.stop_loss = new_sl
                trade.notes.append(f"Trailing @ {new_sl:.2f} (+{improvement:.1f}pts)")
    
    def _check_tp_hit(self, trade: Trade, candle: M5Candle):
        """Verifica si el TP se alcanzó (solo TP, SL ya se verificó antes)"""
        if trade.signal.type == SignalType.LONG:
            if candle.high >= trade.take_profit:
                self._close_trade(trade, trade.take_profit, candle.time, TradeStatus.CLOSED_TP)
        else:  # SHORT
            if candle.low <= trade.take_profit:
                self._close_trade(trade, trade.take_profit, candle.time, TradeStatus.CLOSED_TP)
    
    def _close_trade(self, trade: Trade, exit_price: float, exit_time: datetime, status: TradeStatus):
        """
        Cierra un trade con normalización por riesgo fijo
        
        Cada trade arriesga exactamente risk_per_trade_pct del balance inicial.
        El PnL se calcula como: R-multiple * RISK_USD
        """
        trade.exit_price = exit_price
        trade.exit_time = exit_time
        trade.status = status
        
        # Calcular PnL en puntos
        if trade.signal.type == SignalType.LONG:
            pnl_points_gross = exit_price - trade.entry_price
        else:
            pnl_points_gross = trade.entry_price - exit_price
        
        # Restar spread
        avg_spread = self.config['costs'].get('avg_spread_points', 2)
        pnl_points_net = pnl_points_gross - avg_spread
        
        # Calcular riesgo planificado
        planned_risk_pts = abs(trade.entry_price - trade.original_stop_loss)
        
        # Calcular R-multiple
        if planned_risk_pts > 0:
            r_multiple = pnl_points_net / planned_risk_pts
        else:
            r_multiple = 0
        
        # Calcular PnL en USD (normalizado por riesgo fijo)
        risk_pct = self.config['sizing']['risk_per_trade_pct']
        risk_usd = self.initial_balance * risk_pct  # Siempre basado en balance inicial
        trade.pnl = r_multiple * risk_usd
        
        trade.pnl_pct = (trade.pnl / self.balance) * 100
        
        # Actualizar balance
        self.balance += trade.pnl
        
        # Mover a cerrados
        self.active_trades.remove(trade)
        self.closed_trades.append(trade)
        
        # Si fue loss, bloquear zona permanentemente
        if trade.pnl < 0:
            zone_id = self._get_zone_id(trade.signal)
            self.blocked_zones[zone_id] = "PERMANENT"
            print(f"   🚫 Zona bloqueada: {zone_id}")
        
        result = "✅ WIN" if trade.pnl > 0 else "❌ LOSS"
        print(f"{result} Trade #{trade.id} - {status.value}")
        print(f"   Exit: {exit_price:.2f} | PnL: {pnl_points_net:.1f}pts ({r_multiple:.2f}R) = ${trade.pnl:.2f}")
    
    def _close_all_trades(self, last_candle):
        """Cierra todos los trades abiertos al final"""
        for trade in self.active_trades[:]:
            self._close_trade(trade, last_candle.close, last_candle.time, TradeStatus.CLOSED_SL)
    
    def _record_equity(self, time: datetime):
        """Registra equity actual"""
        open_pnl = sum([
            (t.signal.entry_price - t.entry_price) * t.size if t.signal.type == SignalType.SHORT
            else (t.entry_price - t.signal.entry_price) * t.size
            for t in self.active_trades
        ])
        
        equity = self.balance + open_pnl
        self.equity_curve.append({'time': time, 'equity': equity})
    
    def _generate_results(self) -> pd.DataFrame:
        """Genera DataFrame con resultados incluyendo métricas detalladas"""
        if not self.closed_trades:
            return pd.DataFrame()
        
        avg_spread = self.config['costs'].get('avg_spread_points', 2)
        
        results = []
        for trade in self.closed_trades:
            # Calcular métricas detalladas
            if trade.signal.type.value == 'long':
                pnl_points_gross = trade.exit_price - trade.entry_price
            else:
                pnl_points_gross = trade.entry_price - trade.exit_price
            
            pnl_points_net = pnl_points_gross - avg_spread
            planned_risk_pts = abs(trade.entry_price - trade.original_stop_loss)
            r_multiple = pnl_points_net / planned_risk_pts if planned_risk_pts > 0 else 0
            
            results.append({
                'trade_id': trade.id,
                'type': trade.signal.type.value,
                'entry_time': trade.entry_time,
                'entry_price': trade.entry_price,
                'exit_time': trade.exit_time,
                'exit_price': trade.exit_price,
                'original_stop_loss': trade.original_stop_loss,
                'stop_loss': trade.stop_loss,
                'take_profit': trade.take_profit,
                'pnl_points_gross': pnl_points_gross,
                'spread_cost': avg_spread,
                'pnl_points_net': pnl_points_net,
                'planned_risk_pts': planned_risk_pts,
                'r_multiple': r_multiple,
                'pnl_usd': trade.pnl,
                'pnl_pct': trade.pnl_pct,
                'status': trade.status.value,
                'be_activated': trade.be_activated,
                'trailing_activated': trade.trailing_activated,
                'rr_ratio': trade.signal.risk_reward,
                'pattern': trade.signal.pattern.type.value,
                'confidence': trade.signal.confidence,
                'max_favorable': trade.max_favorable,
                'max_adverse': trade.max_adverse
            })
        
        return pd.DataFrame(results)
