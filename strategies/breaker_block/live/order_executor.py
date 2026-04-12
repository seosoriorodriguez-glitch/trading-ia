# -*- coding: utf-8 -*-
"""
Order Executor - Ejecucion de ordenes en MT5 para la estrategia Breaker Block.
"""
import MetaTrader5 as mt5
from datetime import datetime, timezone
from typing import Tuple, Optional


class OrderExecutor:
    """Ejecuta STOP orders en MT5 a partir de senales del BB Monitor."""

    MAGIC = 345682  # Bot BB=345682 | Bot FVG=345681 | Bot 2 London=345680 | Bot BTC=345679 | Bot 1 NY=345678

    def __init__(self, symbol: str = "US30.cash"):
        self.symbol = symbol

    def calculate_volume(self, entry_price: float, sl: float, risk_usd: float) -> float:
        """
        Calcula el volumen (lotes) para arriesgar exactamente `risk_usd`.
        US30.cash: 1 lote = 1 USD por punto.
        """
        risk_points = abs(entry_price - sl)
        if risk_points == 0:
            return 0.01
        volume = risk_usd / risk_points
        volume = max(0.01, min(volume, 100.0))
        return round(volume, 2)

    def execute_signal(self, signal, risk_usd: float, dry_run: bool = False) -> Tuple[bool, dict]:
        """Ejecuta una senal con ORDEN STOP PENDIENTE."""
        volume = self.calculate_volume(signal.entry_price, signal.sl, risk_usd)
        if volume < 0.01:
            return False, {"error": "Volume too small"}

        tick = mt5.symbol_info_tick(self.symbol)
        if tick is None:
            return False, {"error": "No se pudo obtener precio actual"}

        if signal.direction == "long":
            order_type = mt5.ORDER_TYPE_BUY_STOP
            trade_type = "LONG"
        else:
            order_type = mt5.ORDER_TYPE_SELL_STOP
            trade_type = "SHORT"

        if dry_run:
            return True, {
                "dry_run":     True,
                "type":        trade_type,
                "volume":      volume,
                "entry_price": signal.entry_price,
                "sl":          signal.sl,
                "tp":          signal.tp,
                "risk_points": abs(signal.entry_price - signal.sl),
                "risk_usd":    risk_usd,
                "order_type":  "STOP",
            }

        request = {
            "action":       mt5.TRADE_ACTION_PENDING,
            "symbol":       self.symbol,
            "volume":       volume,
            "type":         order_type,
            "price":        signal.entry_price,
            "sl":           signal.sl,
            "tp":           signal.tp,
            "deviation":    0,
            "magic":        self.MAGIC,
            "comment":      f"BB_{trade_type}_STOP",
            "type_time":    mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_RETURN,
        }

        result = mt5.order_send(request)

        if result is None:
            return False, {"error": "order_send returned None"}
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            return False, {"error": f"Order failed: {result.retcode}", "comment": result.comment}

        return True, {
            "ticket": result.order,
            "volume": result.volume,
            "price":  signal.entry_price,
            "sl":     signal.sl,
            "tp":     signal.tp,
            "type":   trade_type,
            "time":   datetime.now(timezone.utc),
            "order_type": "STOP",
        }

    def get_open_positions(self) -> list:
        positions = mt5.positions_get(symbol=self.symbol)
        if positions is None:
            return []
        return [p for p in positions if p.magic == self.MAGIC]

    def get_pending_orders(self) -> list:
        orders = mt5.orders_get(symbol=self.symbol)
        if orders is None:
            return []
        return [o for o in orders if o.magic == self.MAGIC]

    def cancel_order(self, ticket: int, dry_run: bool = False) -> Tuple[bool, dict]:
        if dry_run:
            return True, {"dry_run": True, "ticket": ticket}
        request = {
            "action": mt5.TRADE_ACTION_REMOVE,
            "order":  ticket,
        }
        result = mt5.order_send(request)
        if result is None:
            return False, {"error": "order_send returned None"}
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            return False, {"error": f"Cancel failed: {result.retcode}"}
        return True, {"ticket": ticket}

    def cancel_all_orders(self, dry_run: bool = False) -> int:
        cancelled = 0
        for order in self.get_pending_orders():
            ok, _ = self.cancel_order(order.ticket, dry_run)
            if ok:
                cancelled += 1
        return cancelled

    def close_position(self, ticket: int, dry_run: bool = False) -> Tuple[bool, dict]:
        position = mt5.positions_get(ticket=ticket)
        if not position:
            return False, {"error": f"Posicion {ticket} no encontrada"}
        position = position[0]

        tick = mt5.symbol_info_tick(self.symbol)
        if position.type == mt5.POSITION_TYPE_BUY:
            order_type = mt5.ORDER_TYPE_SELL
            price      = tick.bid
        else:
            order_type = mt5.ORDER_TYPE_BUY
            price      = tick.ask

        if dry_run:
            return True, {"dry_run": True, "ticket": ticket, "pnl": position.profit}

        request = {
            "action":       mt5.TRADE_ACTION_DEAL,
            "symbol":       self.symbol,
            "volume":       position.volume,
            "type":         order_type,
            "position":     ticket,
            "price":        price,
            "deviation":    10,
            "magic":        self.MAGIC,
            "comment":      "BB_close",
            "type_time":    mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)
        if result is None:
            return False, {"error": "order_send returned None"}
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            return False, {"error": f"Close failed: {result.retcode}"}

        return True, {"ticket": ticket, "close_price": result.price, "pnl": position.profit}

    def close_all_positions(self, dry_run: bool = False) -> int:
        closed = 0
        for pos in self.get_open_positions():
            ok, _ = self.close_position(pos.ticket, dry_run)
            if ok:
                closed += 1
        return closed
