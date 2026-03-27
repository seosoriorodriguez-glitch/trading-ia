# -*- coding: utf-8 -*-
"""
Monitor y Logger - Dashboard y notificaciones
"""
import csv
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
import asyncio
from telegram import Bot


class TelegramNotifier:
    """Notificador de Telegram"""
    
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.bot = Bot(token=bot_token)
        self.enabled = True
        
    async def send_message(self, message: str):
        """Envía mensaje a Telegram"""
        if not self.enabled:
            return
        
        try:
            await self.bot.send_message(chat_id=self.chat_id, text=message)
        except Exception as e:
            print(f"⚠️  Error enviando Telegram: {e}")
            self.enabled = False
    
    def send_message_sync(self, message: str):
        """Envía mensaje de forma síncrona"""
        try:
            asyncio.run(self.send_message(message))
        except Exception as e:
            print(f"⚠️  Error en Telegram sync: {e}")


class TradingMonitor:
    """Monitor de trading con logging y notificaciones"""
    
    def __init__(self, logs_dir: str = "logs", telegram_token: Optional[str] = None, telegram_chat_id: Optional[str] = None):
        self.logs_dir = Path(logs_dir)
        self.logs_dir.mkdir(exist_ok=True)
        
        # Telegram
        self.telegram = None
        if telegram_token and telegram_chat_id:
            self.telegram = TelegramNotifier(telegram_token, telegram_chat_id)
        
        # Archivos de log
        today = datetime.now(timezone.utc).strftime('%Y%m%d')
        self.trades_file = self.logs_dir / f"trades_{today}.csv"
        self.bot_log_file = self.logs_dir / f"bot_{today}.log"
        self.error_log_file = self.logs_dir / f"errors_{today}.log"
        
        # Inicializar CSV de trades
        self._init_trades_csv()
        
    def _init_trades_csv(self):
        """Inicializa archivo CSV de trades"""
        if not self.trades_file.exists():
            with open(self.trades_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'timestamp', 'ticket', 'type', 'entry_price', 'exit_price',
                    'stop_loss', 'take_profit', 'volume', 'pnl_usd', 'pnl_points',
                    'r_multiple', 'exit_reason', 'duration_minutes'
                ])
    
    def log_trade_opened(self, trade_info: dict):
        """Log cuando se abre un trade"""
        msg = (
            f"🟢 TRADE ABIERTO\n"
            f"Tipo: {trade_info['type']}\n"
            f"Entry: {trade_info['price']:.2f}\n"
            f"SL: {trade_info['sl']:.2f}\n"
            f"TP: {trade_info['tp']:.2f}\n"
            f"Volume: {trade_info['volume']:.2f}\n"
            f"Risk: {abs(trade_info['price'] - trade_info['sl']):.1f} pts\n"
            f"R:R: 1:{abs(trade_info['tp'] - trade_info['price']) / abs(trade_info['price'] - trade_info['sl']):.2f}"
        )
        
        self._log_bot_event(msg)
        
        if self.telegram:
            self.telegram.send_message_sync(msg)
    
    def log_trade_closed(self, trade_info: dict):
        """Log cuando se cierra un trade"""
        pnl_usd = trade_info.get('pnl_usd', 0)
        pnl_points = trade_info.get('pnl_points', 0)
        r_multiple = trade_info.get('r_multiple', 0)
        
        emoji = "🟢" if pnl_usd > 0 else "🔴"
        
        msg = (
            f"{emoji} TRADE CERRADO\n"
            f"Tipo: {trade_info['type']}\n"
            f"Entry: {trade_info['entry_price']:.2f}\n"
            f"Exit: {trade_info['exit_price']:.2f}\n"
            f"PnL: ${pnl_usd:,.2f} ({pnl_points:+.1f} pts)\n"
            f"R-Multiple: {r_multiple:+.2f}R\n"
            f"Razón: {trade_info.get('exit_reason', 'unknown')}"
        )
        
        self._log_bot_event(msg)
        
        if self.telegram:
            self.telegram.send_message_sync(msg)
        
        # Guardar en CSV
        self._save_trade_to_csv(trade_info)
    
    def _save_trade_to_csv(self, trade_info: dict):
        """Guarda trade en CSV"""
        with open(self.trades_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.now(timezone.utc).isoformat(),
                trade_info.get('ticket', ''),
                trade_info.get('type', ''),
                trade_info.get('entry_price', 0),
                trade_info.get('exit_price', 0),
                trade_info.get('stop_loss', 0),
                trade_info.get('take_profit', 0),
                trade_info.get('volume', 0),
                trade_info.get('pnl_usd', 0),
                trade_info.get('pnl_points', 0),
                trade_info.get('r_multiple', 0),
                trade_info.get('exit_reason', ''),
                trade_info.get('duration_minutes', 0)
            ])
    
    def log_risk_alert(self, alert_type: str, message: str):
        """Log alerta de riesgo"""
        msg = f"⚠️  ALERTA: {alert_type}\n{message}"
        
        self._log_bot_event(msg)
        
        if self.telegram:
            self.telegram.send_message_sync(msg)
    
    def log_error(self, error_msg: str):
        """Log error"""
        timestamp = datetime.now(timezone.utc).isoformat()
        
        with open(self.error_log_file, 'a', encoding='utf-8') as f:
            f.write(f"[{timestamp}] {error_msg}\n")
        
        print(f"❌ ERROR: {error_msg}")
    
    def _log_bot_event(self, message: str):
        """Log evento del bot"""
        timestamp = datetime.now(timezone.utc).isoformat()
        
        with open(self.bot_log_file, 'a', encoding='utf-8') as f:
            f.write(f"[{timestamp}] {message}\n")
        
        print(message)
    
    def print_dashboard(self, status: dict, clear_screen: bool = True):
        """Imprime dashboard en consola"""
        if clear_screen:
            os.system('cls' if os.name == 'nt' else 'clear')
        
        print("=" * 50, flush=True)
        print("🤖 FTMO BOT - US30 Pivot Scalping", flush=True)
        print("=" * 50, flush=True)
        print(flush=True)
        
        # Balance
        balance = status['risk']['balance']
        profit_pct = status['risk']['profit_pct']
        profit_target = status['risk']['profit_target']
        
        print(f"💰 Balance: ${balance:,.2f} ({profit_pct:+.2%})", flush=True)
        print(f"🎯 Target: {profit_target:.1%}", flush=True)
        print(flush=True)
        
        # Risk
        daily_dd = status['risk']['daily_dd_pct']
        daily_limit = status['risk']['daily_dd_limit']
        total_dd = status['risk']['total_dd_pct']
        total_limit = status['risk']['total_dd_limit']
        
        print(f"📊 Daily DD: {daily_dd:.2%} / {daily_limit:.1%}", flush=True)
        print(f"📊 Total DD: {total_dd:.2%} / {total_limit:.1%}", flush=True)
        print(flush=True)
        
        # Trades
        trades_today = status['risk']['trades_today']
        open_trades = status['risk']['open_trades']
        
        print(f"📈 Trades Hoy: {trades_today}", flush=True)
        print(f"📈 Trades Abiertos: {open_trades}", flush=True)
        print(flush=True)
        
        # Estrategia
        strategy = status.get('strategy', {})
        pivots = strategy.get('pivots', {})
        
        print(f"🎯 Estrategia: M5/M1 Agresiva", flush=True)
        print(f"🔍 Pivots Activos: {pivots.get('total', 0)} (H:{pivots.get('highs', 0)}, L:{pivots.get('lows', 0)})", flush=True)
        print(flush=True)
        
        # Estado
        trading_enabled = status['risk']['trading_enabled']
        stop_reason = status['risk']['stop_reason']
        
        if trading_enabled:
            print("✅ Trading: ACTIVO", flush=True)
        else:
            print(f"🛑 Trading: DETENIDO ({stop_reason})", flush=True)
        
        print(flush=True)
        print(f"⏰ Última actualización: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}", flush=True)
        print("=" * 50, flush=True)
