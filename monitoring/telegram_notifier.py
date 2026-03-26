"""
Notificaciones por Telegram.

Envía alertas sobre: señales, trades abiertos/cerrados,
estados de riesgo, y resúmenes diarios.
"""

import logging
import requests
from typing import Optional, Dict

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Envía mensajes a Telegram vía Bot API."""

    def __init__(self, bot_token: str, chat_id: str, enabled: bool = True):
        """
        Args:
            bot_token: Token del bot de Telegram (@BotFather)
            chat_id: ID del chat/grupo donde enviar mensajes
            enabled: Si False, solo loguea sin enviar
        """
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.enabled = enabled
        self.base_url = f"https://api.telegram.org/bot{bot_token}"

    def send_message(self, text: str, parse_mode: str = "HTML") -> bool:
        """Envía un mensaje de texto."""
        if not self.enabled:
            logger.info(f"[Telegram disabled] {text}")
            return True

        try:
            response = requests.post(
                f"{self.base_url}/sendMessage",
                json={
                    "chat_id": self.chat_id,
                    "text": text,
                    "parse_mode": parse_mode,
                },
                timeout=10,
            )
            if response.status_code == 200:
                return True
            else:
                logger.error(f"Telegram error: {response.status_code} — {response.text}")
                return False
        except Exception as e:
            logger.error(f"Error enviando Telegram: {e}")
            return False

    # --- Mensajes específicos ---

    def notify_signal(self, signal_info: Dict):
        """Notifica una nueva señal detectada."""
        msg = (
            f"📊 <b>SEÑAL {signal_info['direction']}</b>\n"
            f"Instrumento: <b>{signal_info['instrument']}</b>\n"
            f"Tipo: {signal_info['signal_type']}\n"
            f"Entrada: {signal_info['entry_price']:.1f}\n"
            f"SL: {signal_info['stop_loss']:.1f}\n"
            f"TP: {signal_info['take_profit']:.1f}\n"
            f"R:R: {signal_info['risk_reward']:.2f}\n"
            f"Confianza: {signal_info.get('confidence', 'N/A')}"
        )
        self.send_message(msg)

    def notify_trade_opened(self, trade_info: Dict):
        """Notifica un trade abierto."""
        emoji = "🟢" if trade_info["direction"] == "LONG" else "🔴"
        msg = (
            f"{emoji} <b>TRADE ABIERTO</b>\n"
            f"{trade_info['direction']} <b>{trade_info['symbol']}</b>\n"
            f"Precio: {trade_info['price']:.1f}\n"
            f"Lotes: {trade_info['lots']}\n"
            f"SL: {trade_info['sl']:.1f}\n"
            f"TP: {trade_info['tp']:.1f}\n"
            f"Riesgo: 0.5%"
        )
        self.send_message(msg)

    def notify_trade_closed(self, trade_info: Dict):
        """Notifica un trade cerrado."""
        pnl = trade_info.get("pnl", 0)
        emoji = "✅" if pnl >= 0 else "❌"
        msg = (
            f"{emoji} <b>TRADE CERRADO</b>\n"
            f"{trade_info['symbol']} | {trade_info['direction']}\n"
            f"Entrada: {trade_info['entry']:.1f} → Salida: {trade_info['exit']:.1f}\n"
            f"P&L: {pnl:+.1f} pts | ${trade_info.get('pnl_usd', 0):+.2f}\n"
            f"Razón: {trade_info.get('reason', 'N/A')}"
        )
        self.send_message(msg)

    def notify_break_even(self, symbol: str, ticket: int, new_sl: float):
        """Notifica movimiento a break even."""
        msg = f"🔄 <b>BREAK EVEN</b> — {symbol} #{ticket}\nSL → {new_sl:.1f}"
        self.send_message(msg)

    def notify_risk_alert(self, risk_info: Dict):
        """Alerta de riesgo."""
        msg = (
            f"⚠️ <b>ALERTA DE RIESGO</b>\n"
            f"DD Diario: {risk_info['daily_dd']}\n"
            f"DD Total: {risk_info['total_dd']}\n"
            f"Posiciones: {risk_info['positions']}"
        )
        self.send_message(msg)

    def notify_emergency_stop(self, reason: str):
        """Alerta de emergencia — bot detenido."""
        msg = (
            f"🚨🚨🚨 <b>EMERGENCIA — BOT DETENIDO</b> 🚨🚨🚨\n\n"
            f"Razón: {reason}\n\n"
            f"Todas las posiciones cerradas.\n"
            f"Se requiere intervención manual para reactivar."
        )
        self.send_message(msg)

    def notify_daily_summary(self, summary: Dict):
        """Resumen diario."""
        msg = (
            f"📋 <b>RESUMEN DIARIO</b>\n"
            f"{'─' * 25}\n"
            f"Balance: ${summary['balance']:,.2f}\n"
            f"Equity: ${summary['equity']:,.2f}\n"
            f"P&L Hoy: ${summary.get('daily_pnl', 0):+,.2f}\n"
            f"Trades Hoy: {summary.get('trades_today', 0)}\n"
            f"DD Diario: {summary['daily_dd']}\n"
            f"DD Total: {summary['total_dd']}\n"
            f"Posiciones Abiertas: {summary['positions']}"
        )
        self.send_message(msg)
