# -*- coding: utf-8 -*-
"""
Trading Bot - Orquestador principal
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import time
import yaml
from datetime import datetime, timezone
from typing import Optional

from strategies.pivot_scalping.live.data_feed import LiveDataFeed
from strategies.pivot_scalping.live.signal_monitor import LiveSignalMonitor
from strategies.pivot_scalping.live.risk_manager import FTMORiskManager
from strategies.pivot_scalping.live.order_executor import OrderExecutor
from strategies.pivot_scalping.live.monitor import TradingMonitor


class TradingBot:
    """Bot de trading automático para FTMO"""
    
    def __init__(
        self,
        symbol: str = "US30.cash",
        strategy_config_path: str = None,
        ftmo_config_path: str = None,
        initial_balance: float = 100000,
        dry_run: bool = False,
        telegram_token: Optional[str] = None,
        telegram_chat_id: Optional[str] = None
    ):
        self.symbol = symbol
        self.dry_run = dry_run
        self.running = False
        
        # Cargar configuraciones
        self.strategy_config = self._load_config(strategy_config_path)
        self.ftmo_config = self._load_config(ftmo_config_path)
        
        # Inicializar módulos
        self.data_feed = LiveDataFeed(symbol)
        self.signal_monitor = LiveSignalMonitor(self.strategy_config, self.data_feed)
        self.risk_manager = FTMORiskManager(self.ftmo_config, initial_balance)
        self.order_executor = OrderExecutor(symbol)
        self.monitor = TradingMonitor(
            logs_dir="logs",
            telegram_token=telegram_token,
            telegram_chat_id=telegram_chat_id
        )
        
        # Estado
        self.last_m1_check = None
        self.last_m5_check = None
        self.last_daily_reset = None
        self.open_trades = {}  # ticket -> trade_info
        
    def _load_config(self, path: str) -> dict:
        """Carga archivo YAML de configuración"""
        with open(path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def start(self):
        """Inicia el bot"""
        print("🚀 Iniciando Trading Bot...")
        
        # Conectar a MT5
        if not self.data_feed.connect():
            print("❌ No se pudo conectar a MT5")
            return
        
        if self.dry_run:
            print("⚠️  Modo DRY RUN - No se ejecutarán órdenes reales")
        
        # Log inicial
        account = self.data_feed.get_account_info()
        if account:
            print(f"✅ Cuenta conectada - Balance: ${account['balance']:,.2f}")
            self.risk_manager.update_balance(account['balance'])
        
        # Actualizar pivots inicial
        print("🔍 Actualizando pivots iniciales...")
        num_pivots = self.signal_monitor.update_pivots()
        print(f"✅ {num_pivots} pivots activos")
        
        # Iniciar loop
        self.running = True
        print("✅ Bot iniciado - Presiona Ctrl+C para detener")
        print()
        
        try:
            self._main_loop()
        except KeyboardInterrupt:
            print("\n⚠️  Deteniendo bot...")
            self.stop()
    
    def stop(self):
        """Detiene el bot"""
        self.running = False
        
        # Cerrar trades abiertos (opcional)
        if len(self.open_trades) > 0:
            print(f"⚠️  Cerrando {len(self.open_trades)} trades abiertos...")
            self.order_executor.close_all_positions(self.dry_run)
        
        # Desconectar
        self.data_feed.disconnect()
        print("✅ Bot detenido")
    
    def _main_loop(self):
        """Loop principal del bot"""
        while self.running:
            now = datetime.now(timezone.utc)
            
            # Check 1: Emergency stop file
            if Path("STOP.txt").exists():
                print("🛑 Archivo STOP.txt detectado - Deteniendo bot")
                self.stop()
                break
            
            # Check 2: Daily reset (medianoche UTC)
            if self.last_daily_reset is None or now.date() > self.last_daily_reset.date():
                self.risk_manager.reset_daily()
                self.last_daily_reset = now
            
            # Check 3: Actualizar balance
            account = self.data_feed.get_account_info()
            if account:
                self.risk_manager.update_balance(account['balance'])
            
            # Check 4: Actualizar pivots cada 5 minutos
            if now.minute % 5 == 0 and now.second < 10:
                if self.last_m5_check is None or (now - self.last_m5_check).total_seconds() > 290:
                    self._update_pivots()
                    self.last_m5_check = now
            
            # Check 5: Revisar señales cada 1 minuto
            if now.second < 10:
                if self.last_m1_check is None or (now - self.last_m1_check).total_seconds() > 55:
                    self._check_signals()
                    self.last_m1_check = now
            
            # Check 6: Actualizar dashboard cada 30 segundos
            if now.second % 30 == 0:
                self._update_dashboard()
            
            # Check 7: Monitorear trades abiertos
            self._monitor_open_trades()
            
            # Esperar 1 segundo
            time.sleep(1)
    
    def _update_pivots(self):
        """Actualiza pivots"""
        try:
            num_pivots = self.signal_monitor.update_pivots()
            # print(f"🔍 Pivots actualizados: {num_pivots}")
        except Exception as e:
            self.monitor.log_error(f"Error actualizando pivots: {e}")
    
    def _check_signals(self):
        """Verifica señales de entrada"""
        try:
            # Obtener señal
            signal = self.signal_monitor.check_for_signal()
            
            if signal is None:
                return
            
            # Obtener precio actual
            current_price = self.data_feed.get_current_price()
            if current_price is None:
                return
            
            # Verificar con risk manager
            can_trade, reason = self.risk_manager.can_take_trade(signal, current_price)
            
            if not can_trade:
                # print(f"⚠️  Señal rechazada: {reason}")
                return
            
            # Ejecutar trade
            self._execute_trade(signal)
            
        except Exception as e:
            self.monitor.log_error(f"Error verificando señales: {e}")
    
    def _execute_trade(self, signal):
        """Ejecuta un trade"""
        try:
            # Ejecutar orden
            success, result = self.order_executor.execute_signal(
                signal,
                self.risk_manager.risk_usd_per_trade,
                self.dry_run
            )
            
            if not success:
                self.monitor.log_error(f"Error ejecutando trade: {result.get('error', 'unknown')}")
                return
            
            # Actualizar risk manager
            self.risk_manager.on_trade_opened()
            
            # Guardar trade
            trade_info = {
                'ticket': result.get('ticket', 'DRY_RUN'),
                'type': result['type'],
                'price': result.get('price', result.get('entry_price')),
                'sl': result['sl'],
                'tp': result['tp'],
                'volume': result['volume'],
                'entry_time': datetime.now(timezone.utc)
            }
            
            self.open_trades[trade_info['ticket']] = trade_info
            
            # Log
            self.monitor.log_trade_opened(trade_info)
            
        except Exception as e:
            self.monitor.log_error(f"Error ejecutando trade: {e}")
    
    def _monitor_open_trades(self):
        """Monitorea trades abiertos"""
        if self.dry_run:
            return
        
        try:
            # Obtener posiciones de MT5
            positions = self.order_executor.get_open_positions()
            
            # Verificar trades cerrados
            open_tickets = {p.ticket for p in positions}
            
            for ticket, trade_info in list(self.open_trades.items()):
                if ticket not in open_tickets:
                    # Trade cerrado
                    self._on_trade_closed(ticket, trade_info)
                    del self.open_trades[ticket]
        
        except Exception as e:
            self.monitor.log_error(f"Error monitoreando trades: {e}")
    
    def _on_trade_closed(self, ticket: int, trade_info: dict):
        """Callback cuando un trade se cierra"""
        try:
            # Obtener resultado del trade (de history)
            import MetaTrader5 as mt5
            
            deals = mt5.history_deals_get(ticket=ticket)
            if deals and len(deals) > 0:
                # Último deal es el cierre
                close_deal = deals[-1]
                
                exit_price = close_deal.price
                pnl_usd = close_deal.profit
                
                # Calcular métricas
                entry_price = trade_info['price']
                stop_loss = trade_info['sl']
                
                pnl_points = (exit_price - entry_price) if trade_info['type'] == 'LONG' else (entry_price - exit_price)
                risk_points = abs(entry_price - stop_loss)
                r_multiple = pnl_points / risk_points if risk_points > 0 else 0
                
                # Duración
                entry_time = trade_info['entry_time']
                duration_minutes = (datetime.now(timezone.utc) - entry_time).total_seconds() / 60
                
                # Info completa
                close_info = {
                    'ticket': ticket,
                    'type': trade_info['type'],
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'stop_loss': stop_loss,
                    'take_profit': trade_info['tp'],
                    'volume': trade_info['volume'],
                    'pnl_usd': pnl_usd,
                    'pnl_points': pnl_points,
                    'r_multiple': r_multiple,
                    'exit_reason': 'sl_hit' if abs(exit_price - stop_loss) < 1 else 'tp_hit',
                    'duration_minutes': duration_minutes
                }
                
                # Actualizar risk manager
                self.risk_manager.on_trade_closed(pnl_usd)
                
                # Log
                self.monitor.log_trade_closed(close_info)
                
                # Alertas de DD
                status = self.risk_manager.get_status()
                if status['daily_dd_pct'] > 0.03:
                    self.monitor.log_risk_alert("Daily DD", f"Daily DD: {status['daily_dd_pct']:.2%}")
                if status['total_dd_pct'] > 0.07:
                    self.monitor.log_risk_alert("Total DD", f"Total DD: {status['total_dd_pct']:.2%}")
        
        except Exception as e:
            self.monitor.log_error(f"Error procesando cierre de trade: {e}")
    
    def _update_dashboard(self):
        """Actualiza dashboard en consola"""
        try:
            status = {
                'risk': self.risk_manager.get_status(),
                'strategy': {
                    'pivots': self.signal_monitor.get_pivot_summary()
                }
            }
            
            # NUNCA limpiar pantalla - causa problemas en Windows
            self.monitor.print_dashboard(status, clear_screen=False)
        
        except Exception as e:
            self.monitor.log_error(f"Error actualizando dashboard: {e}")
