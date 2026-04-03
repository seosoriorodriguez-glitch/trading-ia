# -*- coding: utf-8 -*-
"""
Punto de entrada del Order Block London Bot.

Uso:
    # Demo (sin ordenes reales):
    python strategies/order_block_london/live/run_bot.py --dry-run --balance 10000

    # Produccion:
    python strategies/order_block_london/live/run_bot.py --balance 10000

Para detener: crear archivo STOP_LONDON.txt en la raiz del proyecto.

IMPORTANTE:
  - Este bot opera US30.cash en la instancia MT5_BTCUSD
  - Sesion: London 10:00-19:00 UTC+3
  - Magic number: 345680 (distinto al Bot 1 NY: 345678)
  - NO interferiere con el Bot 1 NY que usa magic 345678
"""
import sys
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from strategies.order_block_london.live.trading_bot import OrderBlockLondonBot


def main():
    parser = argparse.ArgumentParser(description="Order Block London Bot - US30.cash")
    parser.add_argument("--symbol",   default="US30.cash",
                        help="Simbolo MT5 (default: US30.cash)")
    parser.add_argument("--balance",  type=float, default=10_000.0,
                        help="Balance inicial (default: 10000)")
    parser.add_argument("--ftmo-config", default=None,
                        help="Ruta al YAML de reglas FTMO")
    parser.add_argument("--dry-run",  action="store_true",
                        help="Modo simulacion: no envia ordenes reales a MT5")
    args = parser.parse_args()

    bot = OrderBlockLondonBot(
        symbol           = args.symbol,
        ftmo_config_path = args.ftmo_config,
        dry_run          = args.dry_run,
        initial_balance  = args.balance,
    )
    bot.start()


if __name__ == "__main__":
    main()
