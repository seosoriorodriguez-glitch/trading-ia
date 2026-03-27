# -*- coding: utf-8 -*-
"""
Order Executor - Ejecución de órdenes en MT5
"""
import MetaTrader5 as mt5
from typing import Optional, Tuple
from datetime import datetime, timezone


class OrderExecutor:
    """Ejecutor de órdenes en MT5"""
    
    def __init__(self, symbol: str, magic_number: int = 234567):
        self.symbol = symbol
        self.magic_number = magic_number
        self.contract_size = 1.0  # US30 = 1 USD por punto
        
    def calculate_volume(self, signal, risk_usd: float) -> float:
        """
        Calcula volumen (lotes) basado en riesgo
        
        Args:
            signal: TradingSignal con entry_price y stop_loss
            risk_usd: Riesgo en USD (ej: $500)
        
        Returns:
            Volumen en lotes
        """
        risk_points = abs(signal.entry_price - signal.stop_loss)
        
        if risk_points == 0:
            return 0.01
        
        # US30: 1 lote = 1 USD por punto
        # Si riesgo = 30 pts y queremos arriesgar $500
        # Volume = $500 / 30 = 16.67 lotes
        volume = risk_usd / risk_points
        
        # Límites MT5
        volume = max(0.01, min(volume, 100.0))
        
        # Redondear a 2 decimales
        volume = round(volume, 2)
        
        return volume
    
    def execute_signal(self, signal, risk_usd: float, dry_run: bool = False) -> Tuple[bool, Optional[dict]]:
        """
        Ejecuta una señal de trading
        
        Args:
            signal: TradingSignal
            risk_usd: Riesgo en USD
            dry_run: Si True, simula sin ejecutar
        
        Returns:
            (success, result_dict)
        """
        # Calcular volumen
        volume = self.calculate_volume(signal, risk_usd)
        
        if volume < 0.01:
            return False, {'error': 'Volume too small'}
        
        # Obtener precio actual
        tick = mt5.symbol_info_tick(self.symbol)
        if tick is None:
            return False, {'error': 'Cannot get current price'}
        
        # Determinar tipo de orden y precio
        from strategies.pivot_scalping.core.scalping_signals import SignalType
        
        if signal.type == SignalType.LONG:
            order_type = mt5.ORDER_TYPE_BUY
            entry_price = tick.ask
        else:
            order_type = mt5.ORDER_TYPE_SELL
            entry_price = tick.bid
        
        # Preparar request
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": self.symbol,
            "volume": volume,
            "type": order_type,
            "price": entry_price,
            "sl": signal.stop_loss,
            "tp": signal.take_profit,
            "deviation": 10,  # Slippage máximo en puntos
            "magic": self.magic_number,
            "comment": f"PivotScalp_{signal.type.name}",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        # Dry run
        if dry_run:
            return True, {
                'dry_run': True,
                'order_type': signal.type.name,
                'volume': volume,
                'entry_price': entry_price,
                'stop_loss': signal.stop_loss,
                'take_profit': signal.take_profit,
                'risk_points': abs(entry_price - signal.stop_loss),
                'risk_usd': risk_usd
            }
        
        # Ejecutar orden
        result = mt5.order_send(request)
        
        if result is None:
            return False, {'error': 'order_send returned None'}
        
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            return False, {
                'error': f"Order failed: {result.retcode}",
                'comment': result.comment
            }
        
        # Éxito
        return True, {
            'ticket': result.order,
            'volume': result.volume,
            'price': result.price,
            'sl': signal.stop_loss,
            'tp': signal.take_profit,
            'type': signal.type.name,
            'time': datetime.now(timezone.utc)
        }
    
    def get_open_positions(self) -> list:
        """Obtiene posiciones abiertas del bot (por magic number)"""
        positions = mt5.positions_get(symbol=self.symbol)
        
        if positions is None:
            return []
        
        # Filtrar por magic number
        bot_positions = [p for p in positions if p.magic == self.magic_number]
        
        return bot_positions
    
    def close_position(self, ticket: int, dry_run: bool = False) -> Tuple[bool, Optional[dict]]:
        """
        Cierra una posición por ticket
        
        Args:
            ticket: Ticket de la posición
            dry_run: Si True, simula sin ejecutar
        
        Returns:
            (success, result_dict)
        """
        # Obtener posición
        position = mt5.positions_get(ticket=ticket)
        
        if position is None or len(position) == 0:
            return False, {'error': f'Position {ticket} not found'}
        
        position = position[0]
        
        # Determinar tipo de cierre
        if position.type == mt5.POSITION_TYPE_BUY:
            order_type = mt5.ORDER_TYPE_SELL
            price = mt5.symbol_info_tick(self.symbol).bid
        else:
            order_type = mt5.ORDER_TYPE_BUY
            price = mt5.symbol_info_tick(self.symbol).ask
        
        # Dry run
        if dry_run:
            pnl = position.profit
            return True, {
                'dry_run': True,
                'ticket': ticket,
                'pnl': pnl
            }
        
        # Preparar request de cierre
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": self.symbol,
            "volume": position.volume,
            "type": order_type,
            "position": ticket,
            "price": price,
            "deviation": 10,
            "magic": self.magic_number,
            "comment": "Close by bot",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        # Ejecutar cierre
        result = mt5.order_send(request)
        
        if result is None:
            return False, {'error': 'order_send returned None'}
        
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            return False, {
                'error': f"Close failed: {result.retcode}",
                'comment': result.comment
            }
        
        # Éxito
        return True, {
            'ticket': ticket,
            'close_price': result.price,
            'pnl': position.profit,
            'time': datetime.now(timezone.utc)
        }
    
    def close_all_positions(self, dry_run: bool = False) -> int:
        """
        Cierra todas las posiciones del bot
        
        Returns:
            Número de posiciones cerradas
        """
        positions = self.get_open_positions()
        closed = 0
        
        for pos in positions:
            success, _ = self.close_position(pos.ticket, dry_run)
            if success:
                closed += 1
        
        return closed
