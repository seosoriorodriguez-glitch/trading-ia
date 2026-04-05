# -*- coding: utf-8 -*-
"""
Trading Bot - Orquestador principal de la estrategia Fair Value Gap.

Loop:
  - Cada ~5 min (nueva vela M5): actualiza FVGs activos.
  - Cada ~1 min (nueva vela M1): verifica triggers conservative -> genera ordenes STOP.
  - Continuamente:               monitorea ordenes pendientes y trades abiertos.

Entrada conservative:
  1. Vela M1 cierra DENTRO del FVG -> trigger detectado
  2. Se coloca orden STOP en el borde de la zona (zone_high para long, zone_low para short)
  3. MT5 ejecuta la orden cuando el precio alcanza el borde
  4. Si el FVG se destruye/expira -> orden STOP cancelada

Para activar: python strategies/fair_value_gap/live/run_bot.py [--dry-run]
"""
import sys
import time
import yaml
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from strategies.fair_value_gap.live.data_feed       import LiveDataFeed
from strategies.fair_value_gap.live.fvg_monitor     import LiveFVGMonitor, _fvg_key
from strategies.fair_value_gap.live.order_executor  import OrderExecutor
from strategies.fair_value_gap.live.risk_manager    import FTMORiskManager
from strategies.fair_value_gap.live.monitor         import TradingMonitor
from strategies.fair_value_gap.backtest.config      import US30_PARAMS


class FVGBot:
    """Bot de trading FVG para FTMO Challenge $10k."""

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
        self.fvg_monitor  = LiveFVGMonitor(US30_PARAMS, self.data_feed)
        self.executor     = OrderExecutor(symbol)
        self.risk_manager = FTMORiskManager(ftmo_cfg, initial_balance)
        self.monitor      = TradingMonitor()

        self.open_trades: dict    = {}   # ticket -> trade_info
        self.pending_orders: dict = {}   # ticket -> order_info (ordenes STOP)
        self.last_m5_update:   Optional[datetime] = None
        self.last_m1_check:    Optional[datetime] = None
        self.last_daily_reset: Optional[datetime] = None
        self.last_dashboard:   Optional[datetime] = None

    # ------------------------------------------------------------------
    # Inicio / parada
    # ------------------------------------------------------------------

    def start(self):
        print("Iniciando FVG Bot...", flush=True)

        if not self.data_feed.connect():
            print("No se pudo conectar a MT5", flush=True)
            return

        account = self.data_feed.get_account_info()
        if account:
            self.risk_manager.update_balance(account["balance"])
            print(f"Cuenta: ${account['balance']:,.2f}", flush=True)

        n = self.fvg_monitor.update_fvgs()
        print(f"FVGs activos iniciales: {n}", flush=True)

        if not self.dry_run:
            import MetaTrader5 as mt5
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

    # ------------------------------------------------------------------
    # Loop principal
    # ------------------------------------------------------------------

    def _main_loop(self):
        while self.running:
            now = datetime.now(timezone.utc)

            if Path("STOP_FVG.txt").exists():
                print("STOP_FVG.txt detectado - deteniendo bot")
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
                    self._update_fvgs()
                    self._cancel_invalid_orders()
                    self.last_m5_update = now

            if now.second < 10:
                if (self.last_m1_check is None
                        or (now - self.last_m1_check).total_seconds() > 55):
                    self._check_triggers()
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

    # ------------------------------------------------------------------
    # Acciones internas
    # ------------------------------------------------------------------

    def _update_fvgs(self):
        try:
            n = self.fvg_monitor.update_fvgs()
        except Exception as e:
            self.monitor.log_error(f"Error actualizando FVGs: {e}")

    def _cancel_invalid_orders(self):
        """Cancela ordenes pendientes cuyos FVGs ya no estan activos."""
        try:
            active_fvg_keys = {
                _fvg_key(fvg)
                for fvg in self.fvg_monitor.active_fvgs
                if fvg.status == "fresh"
            }

            for ticket, order_info in list(self.pending_orders.items()):
                pending_stop = order_info.get("pending_stop")
                if pending_stop is None:
                    continue

                fvg = pending_stop.fvg
                key = _fvg_key(fvg)

                if key not in active_fvg_keys:
                    if not self.dry_run:
                        ok, _ = self.executor.cancel_order(ticket, self.dry_run)
                        if ok:
                            print(f"Orden {ticket} cancelada (FVG destruido/expirado)", flush=True)
                    del self.pending_orders[ticket]

        except Exception as e:
            self.monitor.log_error(f"Error cancelando ordenes invalidas: {e}")

    def _check_triggers(self):
        """Detecta triggers conservative y envia ordenes STOP a MT5."""
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

            fvgs_with_pending = {
                _fvg_key(info["pending_stop"].fvg)
                for info in self.pending_orders.values()
                if info.get("pending_stop") is not None
            }

            pending_stop = self.fvg_monitor.check_for_trigger(
                balance        = self.risk_manager.current_balance,
                skip_fvg_keys  = fvgs_with_pending,
            )
            if pending_stop is None:
                return

            self._send_stop_order(pending_stop)

        except Exception as e:
            import traceback
            self.monitor.log_error(
                f"Error verificando triggers: {e}\n{traceback.format_exc()}"
            )

    def _send_stop_order(self, pending_stop):
        """Convierte un PendingStop del monitor en una orden STOP real en MT5."""
        try:
            from strategies.fair_value_gap.backtest.signals import Signal

            signal = Signal(
                direction    = pending_stop.direction,
                entry_price  = pending_stop.entry_price,
                sl           = pending_stop.sl,
                tp           = pending_stop.tp,
                fvg          = pending_stop.fvg,
                candle_time  = pending_stop.trigger_time,
                session      = pending_stop.session,
                entry_method = "conservative",
            )

            ok, result = self.executor.execute_signal(
                signal   = signal,
                risk_usd = self.risk_manager.risk_usd_per_trade,
                dry_run  = self.dry_run,
            )
            if not ok:
                self.monitor.log_error(f"Error al enviar orden STOP: {result.get('error')}")
                return

            entry_price = result.get("price") or result.get("entry_price") or signal.entry_price
            order_info = {
                "ticket":       result.get("ticket", "DRY_RUN"),
                "type":         result["type"],
                "price":        entry_price,
                "sl":           result["sl"],
                "tp":           result["tp"],
                "volume":       result["volume"],
                "entry_time":   datetime.now(timezone.utc),
                "pending_stop": pending_stop,
                "order_type":   result.get("order_type", "STOP"),
            }

            self.pending_orders[order_info["ticket"]] = order_info
            self.monitor.log_trade_opened(order_info)

        except Exception as e:
            self.monitor.log_error(f"Error enviando orden STOP: {e}")

    def _monitor_pending_orders(self):
        """
        Monitorea ordenes pendientes:
        - Si se ejecutaron (ahora son posiciones) -> moverlas a open_trades
        - Si fueron canceladas -> eliminarlas
        """
        try:
            pending_tickets = {o.ticket for o in self.executor.get_pending_orders()}
            positions = self.executor.get_open_positions()
            position_tickets = {p.ticket for p in positions}

            for ticket, order_info in list(self.pending_orders.items()):
                if ticket in position_tickets:
                    pending_stop = order_info.get("pending_stop")
                    if pending_stop is not None:
                        self.fvg_monitor.mark_mitigated(pending_stop.fvg)
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

    def _on_trade_closed(self, ticket: int, trade_info: dict):
        try:
            import MetaTrader5 as mt5
            deals = mt5.history_deals_get(ticket=ticket)
            if not deals:
                return

            close_deal   = deals[-1]
            exit_price   = close_deal.price
            pnl_usd      = close_deal.profit
            entry_price  = trade_info["price"]
            sl           = trade_info["sl"]
            risk_pts     = abs(entry_price - sl)

            pnl_pts   = (exit_price - entry_price) if trade_info["type"] == "LONG" else (entry_price - exit_price)
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
                "session":          getattr(trade_info.get("pending_stop"), "session", ""),
            }

            self.risk_manager.on_trade_closed(pnl_usd)
            self.monitor.log_trade_closed(close_info)

            status = self.risk_manager.get_status()
            if status["daily_dd_pct"] > 0.02:
                self.monitor.log_risk_alert("Daily DD", f"{status['daily_dd_pct']:.2%}")
            if status["total_dd_pct"] > 0.07:
                self.monitor.log_risk_alert("Total DD", f"{status['total_dd_pct']:.2%}")

        except Exception as e:
            self.monitor.log_error(f"Error procesando cierre: {e}")

    def _print_dashboard(self):
        try:
            self.monitor.print_dashboard({
                "risk":     self.risk_manager.get_status(),
                "strategy": {"fvgs": self.fvg_monitor.get_summary()},
            })
        except Exception as e:
            self.monitor.log_error(f"Error en dashboard: {e}")
