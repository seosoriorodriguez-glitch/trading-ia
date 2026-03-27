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
        
    def can_take_trade(self, signal, current_price: dict) -> Tuple[bool, str]:
        """
        Verifica si se puede tomar un trade
        
        Args:
            signal: TradingSignal
            current_price: dict con 'bid', 'ask', 'spread'
        
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
        
        return True, "OK"
    
    def update_balance(self, new_balance: float):
        """Actualiza balance actual"""
        self.current_balance = new_balance
    
    def on_trade_opened(self):
        """Callback cuando se abre un trade"""
        self.open_trades += 1
        self.trades_today += 1
    
    def on_trade_closed(self, pnl_usd: float):
        """Callback cuando se cierra un trade"""
        self.open_trades = max(0, self.open_trades - 1)
        self.current_balance += pnl_usd
    
    def reset_daily(self):
        """Reset diario a medianoche UTC"""
        self.daily_start_balance = self.current_balance
        self.trades_today = 0
        print(f"🔄 Daily reset - Balance: ${self.current_balance:,.2f}")
    
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
