# -*- coding: utf-8 -*-
"""
FTMO Risk Manager - Gestión de riesgo según reglas FTMO
"""
from datetime import datetime, timezone
from typing import Tuple, Optional


class FTMORiskManager:
    """Risk Manager para FTMO Challenge"""
    
    def __init__(self, config: dict, initial_balance: float):
        self.config = config['ftmo']
        self.initial_balance = initial_balance
        self.daily_start_balance = initial_balance
        self.current_balance = initial_balance
        
        # Límites
        self.max_daily_dd_pct = self.config['phase_1']['max_daily_loss_pct']
        self.max_total_dd_pct = self.config['phase_1']['max_total_loss_pct']
        self.profit_target_pct = self.config['phase_1']['profit_target_pct']
        
        # Risk per trade
        self.risk_per_trade_pct = self.config['risk_per_trade_pct']
        self.risk_usd_per_trade = initial_balance * self.risk_per_trade_pct
        
        # Contadores
        self.trades_today = 0
        self.open_trades = 0
        self.max_simultaneous = self.config['max_simultaneous_trades']
        self.max_spread = self.config['max_spread_points']
        
        # Estado
        self.trading_enabled = True
        self.stop_reason = None
        
        # NUEVAS PROTECCIONES
        self.zone_session_trades = {}  # {zone_id_session: timestamp}
        self.blocked_zones = {}  # {zone_id: "PERMANENT"}
        self.current_session = None
        
    def can_take_trade(self, signal, current_price: dict, current_session: str = None) -> Tuple[bool, str]:
        """
        Verifica si se puede tomar un trade
        
        Args:
            signal: TradingSignal
            current_price: dict con 'bid', 'ask', 'spread'
            current_session: str "LONDON" o "NY"
        
        Returns:
            (puede_operar, razón)
        """
        # Check 0: Trading habilitado
        if not self.trading_enabled:
            return False, f"Trading deshabilitado: {self.stop_reason}"
        
        # Check 1: Daily DD
        daily_dd_pct = (self.daily_start_balance - self.current_balance) / self.daily_start_balance
        buffer = 0.005  # 0.5% buffer
        
        if daily_dd_pct >= (self.max_daily_dd_pct - buffer):
            self.trading_enabled = False
            self.stop_reason = f"Daily DD limit ({daily_dd_pct:.2%})"
            return False, self.stop_reason
        
        # Check 2: Total DD
        total_dd_pct = (self.initial_balance - self.current_balance) / self.initial_balance
        
        if total_dd_pct >= (self.max_total_dd_pct - buffer):
            self.trading_enabled = False
            self.stop_reason = f"Total DD limit ({total_dd_pct:.2%})"
            return False, self.stop_reason
        
        # Check 3: Max simultaneous trades
        if self.open_trades >= self.max_simultaneous:
            return False, f"Max simultaneous trades ({self.max_simultaneous})"
        
        # Check 4: Spread filter
        spread_points = current_price['spread']
        if spread_points > self.max_spread:
            return False, f"Spread too high ({spread_points:.1f} pts)"
        
        # Check 5: Weekend close
        now = datetime.now(timezone.utc)
        if self.config['close_before_weekend']:
            # Viernes después de 21:00 UTC
            if now.weekday() == 4 and now.hour >= self.config['weekend_close_hour']:
                return False, "Weekend close time"
        
        # Check 6: Profit target alcanzado
        profit_pct = (self.current_balance - self.initial_balance) / self.initial_balance
        if profit_pct >= self.profit_target_pct:
            self.trading_enabled = False
            self.stop_reason = f"Profit target reached ({profit_pct:.2%})"
            return False, self.stop_reason
        
        # PROTECCIONES DESACTIVADAS - Alineado con backtest baseline
        # Las protecciones de zona por sesión y bloqueo permanente
        # reducían el rendimiento de 81.8% WR / PF 4.60 a 66.7% WR / PF 2.39
        
        return True, "OK"
    
    def update_balance(self, new_balance: float):
        """Actualiza balance actual"""
        self.current_balance = new_balance
    
    def on_trade_opened(self, signal=None, current_session: str = None):
        """Callback cuando se abre un trade"""
        self.open_trades += 1
        self.trades_today += 1
        
        # Protecciones desactivadas - alineado con backtest baseline
    
    def on_trade_closed(self, signal=None, pnl_usd: float = 0, is_loss: bool = False):
        """Callback cuando se cierra un trade"""
        self.open_trades = max(0, self.open_trades - 1)
        self.current_balance += pnl_usd
        
        # Protecciones desactivadas - alineado con backtest baseline
    
    def _get_zone_id(self, signal) -> str:
        """Genera ID único para una zona pivot"""
        pivot_type = "HIGH" if signal.signal_type == "SHORT" else "LOW"
        pivot_price = signal.pivot_price
        return f"{pivot_type}_{pivot_price:.1f}"
    
    def reset_daily(self):
        """Reset diario a medianoche UTC"""
        self.daily_start_balance = self.current_balance
        self.trades_today = 0
        
        # Limpiar registros de zonas por sesión (nuevo día = nuevas sesiones)
        self.zone_session_trades.clear()
        
        print(f"🔄 Daily reset - Balance: ${self.current_balance:,.2f}")
    
    def get_current_session(self) -> Optional[str]:
        """
        Detecta sesión actual (Londres o NY)
        Londres: 08:00-16:00 UTC
        NY: 13:00-21:00 UTC
        """
        now = datetime.now(timezone.utc)
        hour = now.hour
        
        if 8 <= hour < 16:
            return "LONDON"
        elif 13 <= hour < 21:
            return "NY"
        else:
            return None  # Fuera de horario
    
    def get_status(self) -> dict:
        """Retorna estado actual del risk manager"""
        daily_dd_pct = (self.daily_start_balance - self.current_balance) / self.daily_start_balance
        total_dd_pct = (self.initial_balance - self.current_balance) / self.initial_balance
        profit_pct = (self.current_balance - self.initial_balance) / self.initial_balance
        
        return {
            'balance': self.current_balance,
            'daily_dd_pct': daily_dd_pct,
            'daily_dd_limit': self.max_daily_dd_pct,
            'total_dd_pct': total_dd_pct,
            'total_dd_limit': self.max_total_dd_pct,
            'profit_pct': profit_pct,
            'profit_target': self.profit_target_pct,
            'trades_today': self.trades_today,
            'open_trades': self.open_trades,
            'trading_enabled': self.trading_enabled,
            'stop_reason': self.stop_reason
        }
    
    def emergency_stop(self, reason: str):
        """Detención de emergencia"""
        self.trading_enabled = False
        self.stop_reason = f"EMERGENCY: {reason}"
        print(f"🚨 EMERGENCY STOP: {reason}")
