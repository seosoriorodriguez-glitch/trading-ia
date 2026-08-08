# -*- coding: utf-8 -*-
"""
Risk Manager para el bot DARWINEX (copia independiente del de order_block_london).
Mantiene protecciones propias (daily DD, total DD) y un profit target alto para
que el track record sea continuo. Darwinex Zero NO tiene las reglas FTMO, pero
las protecciones no hacen dano.
"""
from datetime import datetime, timezone, timedelta
from typing import Tuple, List


def us_eastern_now() -> datetime:
    """Hora actual en Nueva York (ET), calculada a mano desde UTC para no depender
    de la base de zonas horarias del sistema (Windows). EDT (UTC-4) del 2do domingo
    de marzo al 1er domingo de noviembre; EST (UTC-5) el resto."""
    utc = datetime.now(timezone.utc).replace(tzinfo=None)
    y = utc.year
    mar1 = datetime(y, 3, 1)
    dst_start = mar1 + timedelta(days=(6 - mar1.weekday()) % 7 + 7, hours=7)   # 2do dom mar, 07:00 UTC
    nov1 = datetime(y, 11, 1)
    dst_end = nov1 + timedelta(days=(6 - nov1.weekday()) % 7, hours=6)         # 1er dom nov, 06:00 UTC
    offset = -4 if dst_start <= utc < dst_end else -5
    return utc + timedelta(hours=offset)


class FTMORiskManager:
    """Protecciones de riesgo: daily DD, total DD, profit target, spread, weekend."""

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

        # Filtro de noticias (ventanas en minutos-del-dia, hora ET)
        self.news_filter = cfg.get("news_filter", False)
        self.news_windows: List[Tuple[int, int]] = []
        for w in cfg.get("news_blackout_et", []):
            a, b = w.split("-")
            ah, am = a.split(":")
            bh, bm = b.split(":")
            self.news_windows.append((int(ah) * 60 + int(am), int(bh) * 60 + int(bm)))

        self.open_trades    = 0
        self.trades_today   = 0
        self.trading_enabled = True
        self.stop_reason: str = ""

    def in_news_window(self) -> bool:
        """True si la hora ET actual cae en una ventana de noticias bloqueada."""
        if not self.news_filter or not self.news_windows:
            return False
        et = us_eastern_now()
        if et.weekday() >= 5:            # fin de semana, sin noticias
            return False
        m = et.hour * 60 + et.minute
        return any(lo <= m <= hi for lo, hi in self.news_windows)

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

        if self.in_news_window():
            return False, "Ventana de noticias"

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
