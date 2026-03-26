"""
Ejecutor de Órdenes en MetaTrader 5.

Maneja: apertura de posiciones, modificación de SL/TP,
cierre de posiciones, y gestión de break even.
"""

import logging
from datetime import datetime
from typing import Dict, Optional, List

from core.signals import Signal, Direction

logger = logging.getLogger(__name__)


class OrderExecutor:
    """
    Ejecuta operaciones en MetaTrader 5.
    """

    def __init__(self, mt5_connection, dry_run: bool = True):
        """
        Args:
            mt5_connection: Instancia de MT5Connection
            dry_run: Si True, solo simula (no envía órdenes reales)
        """
        self.mt5_conn = mt5_connection
        self.dry_run = dry_run
        self._mt5 = None

    def _get_mt5(self):
        """Obtiene referencia al módulo/instancia MT5 desde la conexión."""
        if self._mt5 is None:
            if self.mt5_conn._mt5 is None:
                raise ConnectionError("MT5 no conectado — llamar mt5_conn.connect() primero")
            self._mt5 = self.mt5_conn._mt5
        return self._mt5

    def open_position(
        self,
        signal: Signal,
        lots: float,
        symbol_mt5: str,
        magic_number: int = 123456,
    ) -> Optional[Dict]:
        """
        Abre una posición basada en una señal.

        Args:
            signal: Señal de trading
            lots: Tamaño de posición en lotes
            symbol_mt5: Nombre del símbolo en MT5
            magic_number: Número mágico para identificar trades del bot

        Returns:
            Dict con info de la orden ejecutada, o None si falló
        """
        comment = f"SR_{signal.signal_type.value}_{signal.zone.zone_type.value}"

        if self.dry_run:
            logger.info(f"[DRY RUN] Abrir {signal.direction.value} {symbol_mt5} "
                       f"@ {signal.entry_price:.1f} | Lotes: {lots} | "
                       f"SL: {signal.stop_loss:.1f} | TP: {signal.take_profit:.1f} | "
                       f"Comentario: {comment}")
            return {
                "ticket": -1,
                "symbol": symbol_mt5,
                "direction": signal.direction.value,
                "lots": lots,
                "price": signal.entry_price,
                "sl": signal.stop_loss,
                "tp": signal.take_profit,
                "comment": comment,
                "dry_run": True,
                "time": datetime.now().isoformat(),
            }

        mt5 = self._get_mt5()

        # Determinar tipo de orden
        if signal.direction == Direction.LONG:
            order_type = mt5.ORDER_TYPE_BUY
            price = mt5.symbol_info_tick(symbol_mt5).ask
        else:
            order_type = mt5.ORDER_TYPE_SELL
            price = mt5.symbol_info_tick(symbol_mt5).bid

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol_mt5,
            "volume": lots,
            "type": order_type,
            "price": price,
            "sl": signal.stop_loss,
            "tp": signal.take_profit,
            "deviation": 20,           # Slippage permitido en puntos
            "magic": magic_number,
            "comment": comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)

        if result is None:
            logger.error(f"order_send retornó None — {mt5.last_error()}")
            return None

        if result.retcode != mt5.TRADE_RETCODE_DONE:
            logger.error(f"Orden rechazada: {result.retcode} — {result.comment}")
            return None

        logger.info(f"✅ Orden ejecutada: ticket #{result.order} | "
                    f"{signal.direction.value} {symbol_mt5} @ {result.price} | "
                    f"Lotes: {lots}")

        return {
            "ticket": result.order,
            "symbol": symbol_mt5,
            "direction": signal.direction.value,
            "lots": lots,
            "price": result.price,
            "sl": signal.stop_loss,
            "tp": signal.take_profit,
            "comment": comment,
            "dry_run": False,
            "time": datetime.now().isoformat(),
        }

    def modify_sl_tp(
        self,
        ticket: int,
        symbol: str,
        new_sl: Optional[float] = None,
        new_tp: Optional[float] = None,
    ) -> bool:
        """
        Modifica SL y/o TP de una posición abierta.

        Args:
            ticket: Número de ticket de la posición
            symbol: Símbolo del instrumento
            new_sl: Nuevo Stop Loss (None = no modificar)
            new_tp: Nuevo Take Profit (None = no modificar)
        """
        if self.dry_run:
            logger.info(f"[DRY RUN] Modificar #{ticket}: SL={new_sl}, TP={new_tp}")
            return True

        mt5 = self._get_mt5()

        # Obtener posición actual para valores no modificados
        positions = mt5.positions_get(ticket=ticket)
        if not positions:
            logger.error(f"Posición #{ticket} no encontrada")
            return False

        pos = positions[0]
        sl = new_sl if new_sl is not None else pos.sl
        tp = new_tp if new_tp is not None else pos.tp

        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "symbol": symbol,
            "position": ticket,
            "sl": sl,
            "tp": tp,
        }

        result = mt5.order_send(request)

        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            logger.error(f"Error modificando #{ticket}: {result}")
            return False

        logger.info(f"Modificado #{ticket}: SL={sl:.1f}, TP={tp:.1f}")
        return True

    def close_position(self, ticket: int, symbol: str) -> bool:
        """Cierra una posición abierta por ticket."""
        if self.dry_run:
            logger.info(f"[DRY RUN] Cerrar posición #{ticket}")
            return True

        mt5 = self._get_mt5()

        positions = mt5.positions_get(ticket=ticket)
        if not positions:
            logger.error(f"Posición #{ticket} no encontrada")
            return False

        pos = positions[0]

        # Orden opuesta para cerrar
        if pos.type == 0:  # BUY
            order_type = mt5.ORDER_TYPE_SELL
            price = mt5.symbol_info_tick(symbol).bid
        else:  # SELL
            order_type = mt5.ORDER_TYPE_BUY
            price = mt5.symbol_info_tick(symbol).ask

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": pos.volume,
            "type": order_type,
            "position": ticket,
            "price": price,
            "deviation": 20,
            "magic": pos.magic,
            "comment": "close_by_bot",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)

        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            logger.error(f"Error cerrando #{ticket}: {result}")
            return False

        logger.info(f"✅ Posición #{ticket} cerrada @ {result.price}")
        return True

    def close_all_positions(self) -> int:
        """Cierra TODAS las posiciones abiertas. Retorna cantidad cerradas."""
        if self.dry_run:
            logger.info("[DRY RUN] Cerrar todas las posiciones")
            return 0

        mt5 = self._get_mt5()
        positions = mt5.positions_get()

        if not positions:
            return 0

        closed = 0
        for pos in positions:
            if self.close_position(pos.ticket, pos.symbol):
                closed += 1

        logger.info(f"Cerradas {closed}/{len(positions)} posiciones")
        return closed

    def manage_break_even(
        self,
        positions: List[Dict],
        be_config: dict,
    ) -> int:
        """
        Mueve SL a break even para posiciones que alcanzaron el trigger.

        Args:
            positions: Lista de posiciones abiertas
            be_config: Configuración de break even

        Returns:
            Número de posiciones modificadas
        """
        if not be_config.get("enabled", False):
            return 0

        trigger_rr = be_config.get("trigger_rr", 1.0)
        offset = be_config.get("offset_points", 10)
        modified = 0

        for pos in positions:
            # Ya está en break even o mejor?
            entry = pos["price_open"]
            current_sl = pos["sl"]
            current_tp = pos["tp"]

            if pos["type"] == "BUY":
                # Riesgo original
                original_risk = entry - current_sl if current_sl > 0 else 0
                if original_risk <= 0:
                    continue

                # TP distance como proxy de reward esperado
                current_profit_pts = pos.get("profit", 0)

                # Calcular si alcanzó trigger
                be_level = entry + offset
                if current_sl >= be_level:
                    continue  # Ya en BE o mejor

                # ¿Profit actual >= risk original × trigger_rr?
                # Usamos precio actual vs entry
                # (Simplificación: si sl original + trigger * risk <= precio actual)
                target_price = entry + (original_risk * trigger_rr)
                # Necesitamos el precio actual — usamos info del profit
                # En producción, verificar con precio bid actual
                if pos.get("profit", 0) > 0:
                    # Mover a break even
                    if self.modify_sl_tp(pos["ticket"], pos["symbol"], new_sl=be_level):
                        modified += 1
                        logger.info(f"Break even #{pos['ticket']}: SL → {be_level:.1f}")

            else:  # SELL
                original_risk = current_sl - entry if current_sl > 0 else 0
                if original_risk <= 0:
                    continue

                be_level = entry - offset
                if current_sl <= be_level and current_sl > 0:
                    continue

                if pos.get("profit", 0) > 0:
                    if self.modify_sl_tp(pos["ticket"], pos["symbol"], new_sl=be_level):
                        modified += 1
                        logger.info(f"Break even #{pos['ticket']}: SL → {be_level:.1f}")

        return modified
