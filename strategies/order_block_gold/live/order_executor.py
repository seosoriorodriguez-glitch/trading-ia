# -*- coding: utf-8 -*-
"""
Order Executor - Ejecucion de ordenes en MT5 para el bot ORO (XAUUSD).
Copia INDEPENDIENTE del order_executor de order_block_london (FTMO US30).

Diferencia clave: `calculate_volume` es BROKER-AGNOSTICO — lee el valor por punto
directo de MT5 (`symbol_info`) en vez de asumir $1/punto. Asi el lotaje sale
correcto en XAUUSD ($100 por 1.0 de precio) y en cualquier otro simbolo.
"""
import MetaTrader5 as mt5
from datetime import datetime, timezone
from typing import Tuple, Optional


class OrderExecutor:
    """Ejecuta ordenes de mercado en MT5 a partir de senales del OB Monitor."""

    MAGIC = 345682  # NY=345678 | BTC=345679 | London FTMO=345680 | Darwinex=345681 | ORO=345682

    def __init__(self, symbol: str = "XAUUSD"):
        self.symbol = symbol

    def _usd_per_point(self) -> float:
        """USD que gana/pierde 1 lote por cada 1.0 de movimiento de precio.
        Para XAUUSD ~= 100; para US30.cash FTMO = 1.0.

        ORDEN de fuentes (robusto contra tick_value=0 que reporta algun broker):
          1) tick_value / tick_size  (si AMBOS son > 0)
          2) order_calc_profit de 1 lote moviendo 1.0  (verdad del broker)
          3) trade_contract_size      (XAUUSD USD = 100)
          4) 1.0 (ultimo recurso)
        """
        info = mt5.symbol_info(self.symbol)
        # 1) tick_value / tick_size
        if info is not None and info.trade_tick_size and info.trade_tick_value:
            return info.trade_tick_value / info.trade_tick_size
        # 2) order_calc_profit: profit de 1 lote LONG moviendose +1.0 de precio
        tick = mt5.symbol_info_tick(self.symbol)
        if tick is not None:
            price = tick.ask or tick.bid
            if price:
                prof = mt5.order_calc_profit(mt5.ORDER_TYPE_BUY, self.symbol, 1.0, price, price + 1.0)
                if prof:
                    return abs(prof)
        # 3) contract_size (para XAUUSD en USD = 100 oz -> $100 por 1.0)
        if info is not None and info.trade_contract_size:
            return float(info.trade_contract_size)
        return 1.0

    def calculate_volume(self, entry_price: float, sl: float, risk_usd: float) -> float:
        """
        Calcula el volumen (lotes) para arriesgar exactamente `risk_usd`,
        usando el valor por punto REAL del simbolo (leido de MT5).
        """
        risk_points = abs(entry_price - sl)
        if risk_points == 0:
            return 0.01
        usd_per_point = self._usd_per_point()
        if usd_per_point <= 0:
            usd_per_point = 1.0
        volume = risk_usd / (risk_points * usd_per_point)
        volume = max(0.01, min(volume, 100.0))
        return round(volume, 2)

    def execute_signal(self, signal, risk_usd: float, dry_run: bool = False) -> Tuple[bool, dict]:
        """Ejecuta una senal de trading con ORDEN STOP PENDIENTE."""
        volume = self.calculate_volume(signal.entry_price, signal.sl, risk_usd)
        if volume < 0.01:
            return False, {"error": "Volume too small"}

        tick = mt5.symbol_info_tick(self.symbol)
        if tick is None:
            return False, {"error": "No se pudo obtener precio actual"}

        if signal.direction == "long":
            order_type   = mt5.ORDER_TYPE_BUY_STOP
            entry_price  = signal.entry_price
            trade_type   = "LONG"
        else:
            order_type   = mt5.ORDER_TYPE_SELL_STOP
            entry_price  = signal.entry_price
            trade_type   = "SHORT"

        if dry_run:
            return True, {
                "dry_run":     True,
                "type":        trade_type,
                "volume":      volume,
                "entry_price": entry_price,
                "sl":          signal.sl,
                "tp":          signal.tp,
                "risk_points": abs(entry_price - signal.sl),
                "risk_usd":    risk_usd,
                "order_type":  "STOP",
            }

        request = {
            "action":      mt5.TRADE_ACTION_PENDING,
            "symbol":      self.symbol,
            "volume":      volume,
            "type":        order_type,
            "price":       entry_price,
            "sl":          signal.sl,
            "tp":          signal.tp,
            "deviation":   0,
            "magic":       self.MAGIC,
            "comment":     f"OBG_{trade_type}_STOP",  # OBG = Order Block Gold
            "type_time":   mt5.ORDER_TIME_GTC,
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
            "price":  entry_price,
            "sl":     signal.sl,
            "tp":     signal.tp,
            "type":   trade_type,
            "time":   datetime.now(timezone.utc),
            "order_type": "STOP",
        }

    def get_open_positions(self) -> list:
        """Posiciones abiertas de esta estrategia (filtradas por magic number)."""
        positions = mt5.positions_get(symbol=self.symbol)
        if positions is None:
            return []
        return [p for p in positions if p.magic == self.MAGIC]

    def get_pending_orders(self) -> list:
        """Ordenes pendientes de esta estrategia (filtradas por magic number)."""
        orders = mt5.orders_get(symbol=self.symbol)
        if orders is None:
            return []
        return [o for o in orders if o.magic == self.MAGIC]

    def cancel_order(self, ticket: int, dry_run: bool = False) -> Tuple[bool, dict]:
        """Cancela una orden pendiente."""
        if dry_run:
            return True, {"dry_run": True, "ticket": ticket}

        request = {
            "action": mt5.TRADE_ACTION_REMOVE,
            "order": ticket,
        }

        result = mt5.order_send(request)
        if result is None:
            return False, {"error": "order_send returned None"}
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            return False, {"error": f"Cancel failed: {result.retcode}"}

        return True, {"ticket": ticket}

    def cancel_all_orders(self, dry_run: bool = False) -> int:
        """Cancela todas las ordenes pendientes de esta estrategia."""
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
            "action":      mt5.TRADE_ACTION_DEAL,
            "symbol":      self.symbol,
            "volume":      position.volume,
            "type":        order_type,
            "position":    ticket,
            "price":       price,
            "deviation":   10,
            "magic":       self.MAGIC,
            "comment":     "OBG_close",
            "type_time":   mt5.ORDER_TIME_GTC,
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
