# -*- coding: utf-8 -*-
"""
FTMO Risk Manager para la estrategia Order Block BTCUSD.
Mismas reglas FTMO: daily DD 5%, total DD 10%, profit target 10%.
"""
from datetime import datetime, timezone
from typing import Tuple


class FTMORiskManager:
    """Protecciones FTMO: daily DD, total DD, profit target, spread."""

    def __init__(self, ftmo_config: dict, initial_balance: float):
        cfg = ftmo_config["ftmo"]

        self.initial_balance     = initial_balance
        self.daily_start_balance = initial_balance
        self.current_balance     = initial_balance

        phase = cfg["phase_1"]
        self.max_daily_dd_pct  = phase["max_daily_loss_pct"]
        self.max_total_dd_pct  = phase["max_total_loss_pct"]
        self.profit_target_pct = phase["profit_target_pct"]

        self.risk_per_trade_pct  = cfg["risk_per_trade_pct"]
        self.risk_usd_per_trade  = initial_balance * self.risk_per_trade_pct
        self.max_simultaneous    = cfg["max_simultaneous_trades"]
        self.max_spread          = cfg["max_spread_points"]
        self.close_before_weekend = cfg["close_before_weekend"]
        self.weekend_close_hour  = cfg["weekend_close_hour"]

        self.open_trades     = 0
        self.trades_today    = 0
        self.trading_enabled = True
        self.stop_reason: str = ""

    def can_take_trade(self, current_price: dict) -> Tuple[bool, str]:
        if not self.trading_enabled:
            return False, f"Trading detenido: {self.stop_reason}"

        daily_dd = (self.daily_start_balance - self.current_balance) / self.daily_start_balance
        if daily_dd >= self.max_daily_dd_pct - 0.005:
            self.trading_enabled = False
            self.stop_reason = f"Daily DD {daily_dd:.2%}"
            return False, self.stop_reason

        total_dd = (self.initial_balance - self.current_balance) / self.initial_balance
        if total_dd >= self.max_total_dd_pct - 0.005:
            self.trading_enabled = False
            self.stop_reason = f"Total DD {total_dd:.2%}"
            return False, self.stop_reason

        profit = (self.current_balance - self.initial_balance) / self.initial_balance
        if profit >= self.profit_target_pct:
            self.trading_enabled = False
            self.stop_reason = f"Profit target {profit:.2%}"
            return False, self.stop_reason

        if self.open_trades >= self.max_simultaneous:
            return False, f"Max trades simultaneos ({self.max_simultaneous})"

        if current_price["spread"] > self.max_spread:
            return False, f"Spread alto ({current_price['spread']:.1f} pts)"

        # BTC: close_before_weekend es false, pero dejamos el chequeo por si se activa
        now = datetime.now(timezone.utc)
        if self.close_before_weekend and now.weekday() == 4 and now.hour >= self.weekend_close_hour:
            return False, "Cierre de fin de semana"

        return True, "OK"

    def update_balance(self, balance: float):
        self.current_balance = balance

    def on_trade_opened(self):
        self.open_trades  += 1
        self.trades_today += 1

    def on_trade_closed(self, pnl_usd: float):
        self.open_trades     = max(0, self.open_trades - 1)
        self.current_balance += pnl_usd

    def reset_daily(self):
        self.daily_start_balance = self.current_balance
        self.trades_today        = 0
        print(f"Reset diario - Balance: ${self.current_balance:,.2f}")

    def emergency_stop(self, reason: str):
        self.trading_enabled = False
        self.stop_reason     = f"EMERGENCY: {reason}"
        print(f"EMERGENCY STOP: {reason}")

    def get_status(self) -> dict:
        daily_dd = (self.daily_start_balance - self.current_balance) / self.daily_start_balance
        total_dd = (self.initial_balance - self.current_balance) / self.initial_balance
        profit   = (self.current_balance - self.initial_balance) / self.initial_balance
        return {
            "balance":         self.current_balance,
            "daily_dd_pct":    max(0.0, daily_dd),
            "daily_dd_limit":  self.max_daily_dd_pct,
            "total_dd_pct":    max(0.0, total_dd),
            "total_dd_limit":  self.max_total_dd_pct,
            "profit_pct":      profit,
            "profit_target":   self.profit_target_pct,
            "trades_today":    self.trades_today,
            "open_trades":     self.open_trades,
            "trading_enabled": self.trading_enabled,
            "stop_reason":     self.stop_reason,
        }
