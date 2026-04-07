# -*- coding: utf-8 -*-
"""
Trading Bot - Orquestador principal de la estrategia Order Block London.

Loop:
  - Cada ~5 min (nueva vela M5): actualiza OBs activos.
  - Cada ~1 min (nueva vela M1): verifica senales de entrada.
  - Continuamente:               monitorea trades abiertos (cierre por SL/TP).

Para activar: python strategies/order_block_london/live/run_bot.py --balance 10000
"""
import sys
import time
import yaml
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from strategies.order_block_london.live.data_feed      import LiveDataFeed
from strategies.order_block_london.live.ob_monitor     import LiveOBMonitor, _ob_key
from strategies.order_block_london.live.order_executor import OrderExecutor
from strategies.order_block_london.live.risk_manager   import FTMORiskManager
from strategies.order_block.live.monitor               import TradingMonitor
from strategies.order_block_london.backtest.config     import LONDON_PARAMS


class OrderBlockLondonBot:
    """Bot de trading Order Block London para FTMO."""

    def __init__(
        self,
        symbol:           str   = "US30.cash",
        ftmo_config_path: str   = None,
        dry_run:          bool  = False,
        initial_balance:  float = 10_000.0,
    ):
        self.symbol  = symbol
        self.dry_run = dry_run
        self.running = False

        if ftmo_config_path is None:
            ftmo_config_path = str(
                Path(__file__).parent / "config" / "ftmo_rules.yaml"
            )
        with open(ftmo_config_path, "r", encoding="utf-8") as f:
            ftmo_cfg = yaml.safe_load(f)

        self.data_feed    = LiveDataFeed(symbol)
        self.ob_monitor   = LiveOBMonitor(LONDON_PARAMS, self.data_feed)
        self.executor     = OrderExecutor(symbol)
        self.risk_manager = FTMORiskManager(ftmo_cfg, initial_balance)
        self.monitor      = TradingMonitor()

        self.open_trades:    dict = {}
        self.pending_orders: dict = {}
        self.last_m5_update:   Optional[datetime] = None
        self.last_m1_check:    Optional[datetime] = None
        self.last_daily_reset: Optional[datetime] = None
        self.last_dashboard:   Optional[datetime] = None

    def start(self):
        print("Iniciando Order Block London Bot...", flush=True)
        print(f"Sesion: London 10:00-19:00 UTC+3 | RR=2.5 | Buffer=35", flush=True)

        if not self.data_feed.connect():
            print("No se pudo conectar a MT5", flush=True)
            return

        account = self.data_feed.get_account_info()
        if account:
            self.risk_manager.update_balance(account["balance"])
            print(f"Cuenta: ${account['balance']:,.2f}", flush=True)

        n = self.ob_monitor.update_obs()
        print(f"OBs activos iniciales: {n}", flush=True)

        if not self.dry_run:
            existing = self.executor.get_open_positions()
            for pos in existing:
                self.open_trades[pos.ticket] = {
                    "ticket":     pos.ticket,
                    "type":       "LONG" if pos.type == 0 else "SHORT",
                    "price":      pos.price_open,
                    "sl":         pos.sl,
                    "tp":         pos.tp,
                    "volume":     pos.volume,
                    "entry_time": datetime.fromtimestamp(pos.time, tz=timezone.utc),
                }
            self.risk_manager.open_trades = len(existing)
            if existing:
                print(f"{len(existing)} posiciones pre-existentes sincronizadas", flush=True)

            import MetaTrader5 as mt5
            pending = self.executor.get_pending_orders()
            for order in pending:
                self.pending_orders[order.ticket] = {
                    "ticket":     order.ticket,
                    "type":       "LONG" if order.type in (mt5.ORDER_TYPE_BUY_STOP, mt5.ORDER_TYPE_BUY_LIMIT) else "SHORT",
                    "price":      order.price_open,
                    "sl":         order.sl,
                    "tp":         order.tp,
                    "volume":     order.volume_initial,
                    "entry_time": datetime.fromtimestamp(order.time_setup, tz=timezone.utc),
                }
            if pending:
                print(f"{len(pending)} ordenes pendientes sincronizadas", flush=True)

        if self.dry_run:
            print("MODO DRY RUN - no se enviaran ordenes reales", flush=True)

        self.running = True
        print("Bot activo. Ctrl+C para detener.", flush=True)

        try:
            self._main_loop()
        except KeyboardInterrupt:
            print("\nDeteniendo bot...", flush=True)
            self.stop()

    def stop(self):
        self.running = False
        if self.pending_orders:
            print(f"Cancelando {len(self.pending_orders)} ordenes pendientes...", flush=True)
            self.executor.cancel_all_orders(self.dry_run)
        if self.open_trades:
            print(f"Cerrando {len(self.open_trades)} trades abiertos...", flush=True)
            self.executor.close_all_positions(self.dry_run)
        self.data_feed.disconnect()
        print("Bot detenido.", flush=True)

    def _main_loop(self):
        while self.running:
            now = datetime.now(timezone.utc)

            if Path("STOP_LONDON.txt").exists():
                print("STOP_LONDON.txt detectado - deteniendo bot")
                self.stop()
                break

            if self.last_daily_reset is None or now.date() > self.last_daily_reset.date():
                self.risk_manager.reset_daily()
                self.last_daily_reset = now

            account = self.data_feed.get_account_info()
            if account:
                self.risk_manager.update_balance(account["balance"])

            if now.minute % 5 == 0 and now.second < 10:
                if (self.last_m5_update is None
                        or (now - self.last_m5_update).total_seconds() > 290):
                    self._update_obs()
                    self._cancel_invalid_orders()
                    self.last_m5_update = now

            if now.second < 10:
                if (self.last_m1_check is None
                        or (now - self.last_m1_check).total_seconds() > 55):
                    self._check_signals()
                    self.last_m1_check = now

            if now.second % 30 == 0:
                if (self.last_dashboard is None
                        or (now - self.last_dashboard).total_seconds() > 25):
                    self._print_dashboard()
                    self.last_dashboard = now

            if not self.dry_run:
                self._monitor_pending_orders()
                self._monitor_open_trades()

            time.sleep(1)

    def _update_obs(self):
        try:
            self.ob_monitor.update_obs()
        except Exception as e:
            self.monitor.log_error(f"Error actualizando OBs: {e}")

    def _cancel_invalid_orders(self):
        try:
            active_ob_keys = {
                (ob.ob_type, round(ob.zone_high, 2), round(ob.zone_low, 2), ob.confirmed_at)
                for ob in self.ob_monitor.active_obs
                if ob.status == "fresh"
            }
            for ticket, order_info in list(self.pending_orders.items()):
                signal = order_info.get("signal")
                if signal is None:
                    continue
                ob = signal.ob
                ob_key = (ob.ob_type, round(ob.zone_high, 2), round(ob.zone_low, 2), ob.confirmed_at)
                if ob_key not in active_ob_keys:
                    if not self.dry_run:
                        ok, _ = self.executor.cancel_order(ticket, self.dry_run)
                        if ok:
                            print(f"Orden {ticket} cancelada (OB destruido/expirado)", flush=True)
                    del self.pending_orders[ticket]
        except Exception as e:
            self.monitor.log_error(f"Error cancelando ordenes invalidas: {e}")

    def _check_signals(self):
        try:
            if not self.dry_run:
                mt5_positions = self.executor.get_open_positions()
                self.risk_manager.open_trades = len(mt5_positions)

            current_price = self.data_feed.get_current_price()
            if current_price is None:
                return

            can, reason = self.risk_manager.can_take_trade(current_price)
            if not can:
                return

            obs_with_pending = {
                _ob_key(info["signal"].ob)
                for info in self.pending_orders.values()
                if info.get("signal") is not None
            }
            obs_with_open = {
                _ob_key(info["signal"].ob)
                for info in self.open_trades.values()
                if info.get("signal") is not None
            }

            signal = self.ob_monitor.check_for_signal(
                balance      = self.risk_manager.current_balance,
                skip_ob_keys = obs_with_pending | obs_with_open,
            )
            if signal is None:
                return

            self._execute_trade(signal)

        except Exception as e:
            import traceback
            self.monitor.log_error(
                f"Error verificando senales: {e}\n{traceback.format_exc()}"
            )

    def _execute_trade(self, signal):
        try:
            ok, result = self.executor.execute_signal(
                signal   = signal,
                risk_usd = self.risk_manager.risk_usd_per_trade,
                dry_run  = self.dry_run,
            )
            if not ok:
                self.monitor.log_error(f"Error al ejecutar trade: {result.get('error')}")
                return

            entry_price = result.get("price") or result.get("entry_price") or signal.entry_price
            order_info  = {
                "ticket":     result.get("ticket", "DRY_RUN"),
                "type":       result["type"],
                "price":      entry_price,
                "sl":         result["sl"],
                "tp":         result["tp"],
                "volume":     result["volume"],
                "entry_time": datetime.now(timezone.utc),
                "signal":     signal,
                "order_type": result.get("order_type", "STOP"),
            }
            self.pending_orders[order_info["ticket"]] = order_info
            self.monitor.log_trade_opened(order_info)

        except Exception as e:
            self.monitor.log_error(f"Error ejecutando trade: {e}")

    def _monitor_pending_orders(self):
        try:
            pending_tickets  = {o.ticket for o in self.executor.get_pending_orders()}
            positions        = self.executor.get_open_positions()
            position_tickets = {p.ticket for p in positions}

            for ticket, order_info in list(self.pending_orders.items()):
                if ticket in position_tickets:
                    signal = order_info.get("signal")
                    if signal is not None:
                        self.ob_monitor.mark_mitigated(signal.ob)
                    self.risk_manager.on_trade_opened()
                    self.open_trades[ticket] = order_info
                    del self.pending_orders[ticket]
                    print(f"Orden STOP {ticket} ejecutada", flush=True)
                elif ticket not in pending_tickets:
                    del self.pending_orders[ticket]
                    print(f"Orden STOP {ticket} cancelada/expirada", flush=True)
        except Exception as e:
            self.monitor.log_error(f"Error monitoreando ordenes pendientes: {e}")

    def _monitor_open_trades(self):
        try:
            positions    = self.executor.get_open_positions()
            open_tickets = {p.ticket for p in positions}
            for ticket, trade_info in list(self.open_trades.items()):
                if ticket not in open_tickets:
                    self._on_trade_closed(ticket, trade_info)
                    del self.open_trades[ticket]
        except Exception as e:
            self.monitor.log_error(f"Error monitoreando trades: {e}")

    def _on_trade_closed(self, ticket, trade_info):
        try:
            import MetaTrader5 as mt5
            deals = mt5.history_deals_get(ticket=ticket)
            if not deals:
                return

            close_deal  = deals[-1]
            exit_price  = close_deal.price
            pnl_usd     = close_deal.profit
            entry_price = trade_info["price"]
            sl          = trade_info["sl"]
            risk_pts    = abs(entry_price - sl)

            pnl_pts    = (exit_price - entry_price) if trade_info["type"] == "LONG" else (entry_price - exit_price)
            r_multiple = pnl_pts / risk_pts if risk_pts > 0 else 0
            duration   = (datetime.now(timezone.utc) - trade_info["entry_time"]).total_seconds() / 60
            exit_reason = "sl_hit" if abs(exit_price - sl) < 2 else "tp_hit"

            close_info = {
                "ticket":           ticket,
                "type":             trade_info["type"],
                "entry_price":      entry_price,
                "exit_price":       exit_price,
                "sl":               sl,
                "tp":               trade_info["tp"],
                "volume":           trade_info["volume"],
                "pnl_usd":          pnl_usd,
                "pnl_points":       pnl_pts,
                "r_multiple":       r_multiple,
                "exit_reason":      exit_reason,
                "duration_minutes": round(duration, 1),
                "session":          getattr(trade_info.get("signal"), "session", ""),
            }

            self.risk_manager.on_trade_closed(pnl_usd)
            self.monitor.log_trade_closed(close_info)

            status = self.risk_manager.get_status()
            if status["daily_dd_pct"] > 0.03:
                self.monitor.log_risk_alert("Daily DD", f"{status['daily_dd_pct']:.2%}")
            if status["total_dd_pct"] > 0.07:
                self.monitor.log_risk_alert("Total DD", f"{status['total_dd_pct']:.2%}")

        except Exception as e:
            self.monitor.log_error(f"Error procesando cierre: {e}")

    def _print_dashboard(self):
        try:
            self.monitor.print_dashboard({
                "risk":     self.risk_manager.get_status(),
                "strategy": {"obs": self.ob_monitor.get_summary()},
            })
        except Exception as e:
            self.monitor.log_error(f"Error en dashboard: {e}")
