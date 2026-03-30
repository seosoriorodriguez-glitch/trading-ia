# -*- coding: utf-8 -*-
"""
Punto de entrada del Order Block Bot.

Uso:
    # Demo (sin ordenes reales):
    python strategies/order_block/live/run_bot.py --dry-run

    # Produccion:
    python strategies/order_block/live/run_bot.py --balance 100000

    # Simbolo alternativo:
    python strategies/order_block/live/run_bot.py --symbol NAS100.cash --balance 100000

IMPORTANTE: Este bot NO esta activo aun.
Activar solo despues de validar el backtest final y pasar paper trading.
"""
import sys
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from strategies.order_block.live.trading_bot import OrderBlockBot


def main():
    parser = argparse.ArgumentParser(description="Order Block Bot - US30.cash")
    parser.add_argument("--symbol",   default="US30.cash",
                        help="Simbolo MT5 (default: US30.cash)")
    parser.add_argument("--balance",  type=float, default=100_000.0,
                        help="Balance inicial (default: 100000)")
    parser.add_argument("--ftmo-config", default=None,
                        help="Ruta al YAML de reglas FTMO (default: config/ftmo_rules.yaml)")
    parser.add_argument("--dry-run",  action="store_true",
                        help="Modo simulacion: no envia ordenes reales a MT5")
    args = parser.parse_args()

    bot = OrderBlockBot(
        symbol           = args.symbol,
        ftmo_config_path = args.ftmo_config,
        dry_run          = args.dry_run,
        initial_balance  = args.balance,
    )
    bot.start()


if __name__ == "__main__":
    main()
