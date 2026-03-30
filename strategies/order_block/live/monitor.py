# -*- coding: utf-8 -*-
"""
Monitor y Logger - Dashboard en consola y log de trades.
"""
import csv
import os
import threading
import urllib.request
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


class TelegramNotifier:
    """Envia notificaciones a Telegram via HTTP (sin dependencias externas)."""

    def __init__(self, token: str, chat_id: str):
        self.token   = token
        self.chat_id = chat_id
        self._base   = f"https://api.telegram.org/bot{token}/sendMessage"

    def send(self, text: str):
        """Envia mensaje en background (no bloquea el bot)."""
        threading.Thread(target=self._send_sync, args=(text,), daemon=True).start()

    def _send_sync(self, text: str):
        try:
            data = urllib.parse.urlencode({
                "chat_id":    self.chat_id,
                "text":       text,
                "parse_mode": "HTML",
            }).encode()
            req = urllib.request.Request(self._base, data=data, method="POST")
            urllib.request.urlopen(req, timeout=10)
        except Exception as e:
            print(f"[Telegram] Error: {e}", flush=True)


class TradingMonitor:
    """Logging de eventos, trades y dashboard de consola."""

    TELEGRAM_TOKEN   = "8577007615:AAHy31IegzvbezCpyNfIlaZh_IsKuV-4M9A"
    TELEGRAM_CHAT_ID = "6265548967"

    def __init__(self, logs_dir: str = "logs_ob",
                 telegram_token: str = None, telegram_chat_id: str = None):
        self.logs_dir = Path(logs_dir)
        self.logs_dir.mkdir(exist_ok=True)

        today = datetime.now(timezone.utc).strftime("%Y%m%d")
        self.trades_file   = self.logs_dir / f"trades_{today}.csv"
        self.bot_log_file  = self.logs_dir / f"bot_{today}.log"
        self.error_log_file = self.logs_dir / f"errors_{today}.log"

        token   = telegram_token   or self.TELEGRAM_TOKEN
        chat_id = telegram_chat_id or self.TELEGRAM_CHAT_ID
        self.telegram = TelegramNotifier(token, chat_id) if token and chat_id else None

        self._init_trades_csv()

    def _init_trades_csv(self):
        if not self.trades_file.exists():
            with open(self.trades_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "timestamp", "ticket", "type", "entry_price", "exit_price",
                    "sl", "tp", "volume", "pnl_usd", "pnl_points",
                    "r_multiple", "exit_reason", "duration_minutes", "session",
                ])

    def log_trade_opened(self, trade_info: dict):
        rr = abs(trade_info["tp"] - trade_info["price"]) / max(abs(trade_info["price"] - trade_info["sl"]), 0.01)
        msg = (
            f"TRADE ABIERTO | {trade_info['type']}"
            f" | Entry: {trade_info['price']:.2f}"
            f" | SL: {trade_info['sl']:.2f}"
            f" | TP: {trade_info['tp']:.2f}"
            f" | Vol: {trade_info['volume']:.2f}"
            f" | Risk: {abs(trade_info['price'] - trade_info['sl']):.1f} pts"
            f" | R:R 1:{rr:.2f}"
        )
        self._log_event(msg)
        if self.telegram:
            direction = "🟢 LONG" if trade_info['type'] == "LONG" else "🔴 SHORT"
            tg = (
                f"<b>📈 TRADE ABIERTO — OB Bot</b>\n"
                f"{direction} US30.cash\n"
                f"Entry: <b>{trade_info['price']:.2f}</b>\n"
                f"SL: {trade_info['sl']:.2f}  |  TP: {trade_info['tp']:.2f}\n"
                f"Vol: {trade_info['volume']:.2f} lotes  |  R:R 1:{rr:.2f}"
            )
            self.telegram.send(tg)

    def log_trade_closed(self, trade_info: dict):
        pnl_usd   = trade_info.get("pnl_usd", 0)
        pnl_pts   = trade_info.get("pnl_points", 0)
        r_mult    = trade_info.get("r_multiple", 0)
        sign      = "+" if pnl_usd >= 0 else ""
        msg = (
            f"TRADE CERRADO | {trade_info['type']}"
            f" | Entry: {trade_info['entry_price']:.2f}"
            f" | Exit: {trade_info['exit_price']:.2f}"
            f" | PnL: {sign}${pnl_usd:,.2f} ({pnl_pts:+.1f} pts)"
            f" | R: {r_mult:+.2f}R"
            f" | Razon: {trade_info.get('exit_reason', '?')}"
        )
        self._log_event(msg)
        self._save_trade_csv(trade_info)
        if self.telegram:
            pnl_usd = trade_info.get("pnl_usd", 0)
            r_mult  = trade_info.get("r_multiple", 0)
            reason  = trade_info.get("exit_reason", "?")
            sign    = "+" if pnl_usd >= 0 else ""
            emoji   = "✅" if pnl_usd >= 0 else "❌"
            tg = (
                f"<b>{emoji} TRADE CERRADO — OB Bot</b>\n"
                f"{trade_info['type']} US30.cash\n"
                f"Entry: {trade_info['entry_price']:.2f}  →  Exit: {trade_info['exit_price']:.2f}\n"
                f"PnL: <b>{sign}${pnl_usd:,.2f}</b>  ({r_mult:+.2f}R)\n"
                f"Razón: {reason}  |  Duración: {trade_info.get('duration_minutes', 0):.0f} min"
            )
            self.telegram.send(tg)

    def log_risk_alert(self, alert_type: str, message: str):
        self._log_event(f"ALERTA {alert_type}: {message}")
        if self.telegram:
            self.telegram.send(f"⚠️ <b>ALERTA RIESGO — OB Bot</b>\n{alert_type}: {message}")

    def log_error(self, error_msg: str):
        ts = datetime.now(timezone.utc).isoformat()
        with open(self.error_log_file, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {error_msg}\n")
        print(f"ERROR: {error_msg}", flush=True)

    def _log_event(self, message: str):
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}] {message}"
        with open(self.bot_log_file, "a", encoding="utf-8") as f:
            f.write(line + "\n")
        print(line, flush=True)

    def _save_trade_csv(self, t: dict):
        with open(self.trades_file, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.now(timezone.utc).isoformat(),
                t.get("ticket", ""),
                t.get("type", ""),
                t.get("entry_price", 0),
                t.get("exit_price", 0),
                t.get("sl", 0),
                t.get("tp", 0),
                t.get("volume", 0),
                t.get("pnl_usd", 0),
                t.get("pnl_points", 0),
                t.get("r_multiple", 0),
                t.get("exit_reason", ""),
                t.get("duration_minutes", 0),
                t.get("session", ""),
            ])

    def print_dashboard(self, status: dict):
        risk  = status["risk"]
        strat = status.get("strategy", {})
        obs   = strat.get("obs", {})

        print("=" * 55, flush=True)
        print("  ORDER BLOCK BOT - US30.cash  M5 deteccion / M1 entrada", flush=True)
        print("=" * 55, flush=True)

        bal     = risk["balance"]
        profit  = risk["profit_pct"]
        target  = risk["profit_target"]
        print(f"  Balance:      ${bal:,.2f}  ({profit:+.2%})", flush=True)
        print(f"  Objetivo:     {target:.1%}", flush=True)

        daily_dd = risk["daily_dd_pct"]
        total_dd = risk["total_dd_pct"]
        print(f"  Daily DD:     {daily_dd:.2%} / {risk['daily_dd_limit']:.1%}", flush=True)
        print(f"  Total DD:     {total_dd:.2%} / {risk['total_dd_limit']:.1%}", flush=True)

        print(f"  Trades hoy:   {risk['trades_today']}", flush=True)
        print(f"  Abiertos:     {risk['open_trades']}", flush=True)

        bias = obs.get("trend_bias") or "sin filtro"
        print(f"  OBs activos:  {obs.get('total', 0)}"
              f"  (bull:{obs.get('bullish', 0)} / bear:{obs.get('bearish', 0)})"
              f"  | Bias: {bias}", flush=True)

        if risk["trading_enabled"]:
            print("  Estado:       ACTIVO", flush=True)
        else:
            print(f"  Estado:       DETENIDO ({risk['stop_reason']})", flush=True)

        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        print(f"  Actualizado:  {ts}", flush=True)
        print("=" * 55, flush=True)
        print(flush=True)
