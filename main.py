"""
SR Trading Bot — Loop Principal

Este es el punto de entrada del bot.
Ejecuta el ciclo: verificar riesgo → gestionar posiciones →
detectar zonas → buscar señales → ejecutar trades.
"""

import os
import sys
import time
import logging
import signal as os_signal
from datetime import datetime, timedelta
from pathlib import Path

# Agregar directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent))

from core.config_loader import get_config
from core.market_data import MT5Connection
from core.levels import detect_zones
from core.signals import scan_for_signals
from core.risk_manager import RiskManager
from core.executor import OrderExecutor
from monitoring.telegram_notifier import TelegramNotifier
from monitoring.trade_logger import TradeLogger


# --- Logging Setup ---
def setup_logging(level: str = "INFO"):
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    log_file = log_dir / f"bot_{datetime.now().strftime('%Y%m%d')}.log"

    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout),
        ],
    )


logger = logging.getLogger("main")


# --- Graceful Shutdown ---
_running = True

def shutdown_handler(signum, frame):
    global _running
    logger.info("Señal de shutdown recibida — cerrando bot...")
    _running = False

os_signal.signal(os_signal.SIGINT, shutdown_handler)
os_signal.signal(os_signal.SIGTERM, shutdown_handler)


# --- Bot Principal ---
class TradingBot:
    """Orquesta todos los componentes del bot."""

    def __init__(self, dry_run: bool = True):
        self.config = get_config()
        self.dry_run = dry_run

        # Componentes
        mt5_config = self.config.strategy.get("mt5", {})
        self.mt5 = MT5Connection(
            host=mt5_config.get("host", "localhost"),
            port=mt5_config.get("port", 8001),
        )
        self.executor = OrderExecutor(self.mt5, dry_run=dry_run)
        self.risk_mgr = RiskManager(self.config.ftmo, self.config.position_sizing)
        self.trade_logger = TradeLogger()

        # Telegram (configurar via env vars)
        self.telegram = TelegramNotifier(
            bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
            chat_id=os.getenv("TELEGRAM_CHAT_ID", ""),
            enabled=bool(os.getenv("TELEGRAM_BOT_TOKEN")),
        )

        # Estado
        self._last_h1_candle_time = None
        self._zones_cache = {}         # {instrument: [zones]}
        self._last_zone_update = {}    # {instrument: datetime}

    def initialize(self) -> bool:
        """Inicializa conexiones y estado."""
        logger.info("=" * 60)
        logger.info("SR TRADING BOT — Inicializando")
        logger.info(f"Modo: {'DRY RUN (simulación)' if self.dry_run else '⚡ LIVE TRADING ⚡'}")
        logger.info("=" * 60)

        # Conectar a MT5
        if not self.dry_run:
            if not self.mt5.connect():
                logger.error("No se pudo conectar a MT5")
                return False

            # Obtener info de cuenta
            account = self.mt5.get_account_info()
            if not account:
                logger.error("No se pudo obtener info de cuenta")
                return False

            self.risk_mgr.initialize(
                initial_balance=account["balance"],  # TODO: usar balance real del inicio del Challenge
                current_balance=account["balance"],
                current_equity=account["equity"],
            )

            logger.info(f"Cuenta: Balance=${account['balance']:,.2f}, "
                       f"Equity=${account['equity']:,.2f}")
        else:
            # Dry run: balance simulado
            self.risk_mgr.initialize(
                initial_balance=100_000,
                current_balance=100_000,
                current_equity=100_000,
            )
            logger.info("Dry run: Balance simulado $100,000")

        # Verificar instrumentos
        instruments = self.config.get_enabled_instruments()
        logger.info(f"Instrumentos habilitados: {list(instruments.keys())}")

        self.telegram.send_message(
            f"🤖 <b>Bot Iniciado</b>\n"
            f"Modo: {'Simulación' if self.dry_run else 'LIVE'}\n"
            f"Instrumentos: {', '.join(instruments.keys())}"
        )

        return True

    def run_cycle(self):
        """Ejecuta un ciclo completo del bot."""
        try:
            # --- 1. Actualizar estado de cuenta ---
            if not self.dry_run:
                account = self.mt5.get_account_info()
                positions = self.mt5.get_open_positions()
                if account:
                    total_risk = len(positions) * self.config.position_sizing["risk_per_trade_pct"]
                    floating_pnl = sum(p["profit"] for p in positions)

                    self.risk_mgr.update_state(
                        balance=account["balance"],
                        equity=account["equity"],
                        floating_pnl=floating_pnl,
                        open_positions=len(positions),
                        total_risk_pct=total_risk,
                    )

            # --- 2. Verificar guardarraíles ---
            if self.risk_mgr.account.is_globally_blocked:
                logger.critical("Bot bloqueado globalmente — cerrando todo")
                if not self.dry_run:
                    self.executor.close_all_positions()
                self.telegram.notify_emergency_stop(self.risk_mgr.account.block_reason)
                return

            if self.risk_mgr.account.daily_state and self.risk_mgr.account.daily_state.is_blocked:
                logger.warning("Día bloqueado — no se abren nuevas operaciones")
                return

            # --- 3. Gestionar posiciones abiertas (break even) ---
            if not self.dry_run:
                positions = self.mt5.get_open_positions()
                self.executor.manage_break_even(positions, self.config.break_even)

            # --- 4. Para cada instrumento habilitado ---
            for name, inst_config in self.config.get_enabled_instruments().items():
                self._process_instrument(name, inst_config)

        except Exception as e:
            logger.exception(f"Error en ciclo del bot: {e}")
            self.telegram.send_message(f"❌ Error en bot: {e}")

    def _process_instrument(self, name: str, inst_config: dict):
        """Procesa un instrumento: detectar zonas y buscar señales."""
        symbol = inst_config["symbol_mt5"]

        # Obtener velas
        if not self.dry_run:
            candles_h4 = self.mt5.get_candles(symbol, "H4",
                                               self.config.zone_detection["lookback_candles"])
            candles_h1 = self.mt5.get_candles(symbol, "H1", 10)  # Últimas 10 H1

            if not candles_h4 or not candles_h1:
                return

            self.risk_mgr.record_server_request(2)  # 2 requests a MT5
        else:
            return  # En dry run, usar backtester

        # ¿Nueva vela H1? (evitar procesar la misma vela dos veces)
        latest_h1_time = candles_h1[-1].time
        cache_key = f"{name}_{latest_h1_time}"
        if cache_key == self._last_h1_candle_time:
            return  # Misma vela, skip

        # Detectar zonas
        zones = detect_zones(candles_h4, self.config.zone_detection, inst_config)

        if not zones:
            return

        # Buscar señales
        signals = scan_for_signals(
            candles_h1=candles_h1[-2:],  # Últimas 2 velas H1
            zones=zones,
            all_zones=zones,
            instrument=name,
            instrument_config=inst_config,
            entry_config=self.config.entry,
            tp_config=self.config.take_profit,
        )

        if not signals:
            return

        # Tomar la mejor señal
        signal = signals[0]

        # Verificar con risk manager
        can_trade, reason = self.risk_mgr.can_open_trade(signal)
        if not can_trade:
            logger.info(f"Trade rechazado por risk manager: {reason}")
            return

        # Verificar spread
        if not self.dry_run:
            price_info = self.mt5.get_current_price(symbol)
            if price_info and price_info["spread"] > inst_config.get("max_spread_points", 30):
                logger.info(f"Spread demasiado alto: {price_info['spread']:.1f}")
                return

        # Calcular tamaño de posición
        if not self.dry_run:
            symbol_info = self.mt5.get_symbol_info(symbol)
            lots = self.risk_mgr.calculate_position_size(signal, symbol_info)
        else:
            lots = 0.01

        if lots <= 0:
            return

        # ¡EJECUTAR!
        result = self.executor.open_position(signal, lots, symbol)

        if result:
            self._last_h1_candle_time = cache_key

            # Notificar
            self.telegram.notify_trade_opened({
                "direction": signal.direction.value,
                "symbol": symbol,
                "price": signal.entry_price,
                "lots": lots,
                "sl": signal.stop_loss,
                "tp": signal.take_profit,
            })

            # Registrar
            risk_usd = self.risk_mgr.account.current_balance * self.config.position_sizing["risk_per_trade_pct"]
            self.trade_logger.log_entry(signal, lots, risk_usd)

            logger.info(f"✅ Trade ejecutado: {signal}")

    def run(self):
        """Loop principal del bot."""
        if not self.initialize():
            logger.error("Fallo en inicialización — bot no arranca")
            return

        interval = self.config.bot_settings.get("check_interval_seconds", 60)
        logger.info(f"Bot corriendo — intervalo: {interval}s")

        global _running
        while _running:
            self.run_cycle()
            time.sleep(interval)

        # Shutdown
        logger.info("Bot detenido")
        self.telegram.send_message("🛑 <b>Bot Detenido</b>")
        if not self.dry_run:
            self.mt5.disconnect()


# --- Entry Point ---
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="SR Trading Bot")
    parser.add_argument("--live", action="store_true", help="Ejecutar en modo LIVE (¡cuidado!)")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING"])
    args = parser.parse_args()

    setup_logging(args.log_level)

    dry_run = not args.live

    if not dry_run:
        logger.warning("⚡ MODO LIVE ACTIVADO — Las operaciones son REALES ⚡")
        logger.warning("¿Estás seguro? Ctrl+C para cancelar en 5 segundos...")
        time.sleep(5)

    bot = TradingBot(dry_run=dry_run)
    bot.run()
