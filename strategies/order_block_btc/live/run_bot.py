# -*- coding: utf-8 -*-
"""
Punto de entrada del Order Block Bot - BTCUSD 24/7.

Este bot es COMPLETAMENTE INDEPENDIENTE del bot US30.
Proceso separado, magic number separado (345679), logs separados (logs_ob_btc/).
Para detener sin Ctrl+C: crear archivo STOP_BTC.txt en el directorio raiz.

Uso:
    # Demo (sin ordenes reales):
    python strategies/order_block_btc/live/run_bot.py --dry-run

    # Produccion (balance real de la cuenta):
    python strategies/order_block_btc/live/run_bot.py --balance 10000

    # Simbolo alternativo (verificar nombre exacto en FTMO):
    python strategies/order_block_btc/live/run_bot.py --symbol Bitcoin --balance 10000
"""
import sys
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from strategies.order_block_btc.live.trading_bot import OrderBlockBotBTC


def main():
    parser = argparse.ArgumentParser(description="Order Block Bot - BTCUSD 24/7")
    parser.add_argument("--symbol",     default="BTCUSD",
                        help="Simbolo MT5 (default: BTCUSD). Verificar nombre exacto en FTMO.")
    parser.add_argument("--balance",    type=float, default=100_000.0,
                        help="Balance inicial de la cuenta (default: 100000)")
    parser.add_argument("--ftmo-config", default=None,
                        help="Ruta al YAML de reglas FTMO (default: config/ftmo_rules.yaml)")
    parser.add_argument("--dry-run",    action="store_true",
                        help="Modo simulacion: no envia ordenes reales a MT5")
    args = parser.parse_args()

    bot = OrderBlockBotBTC(
        symbol           = args.symbol,
        ftmo_config_path = args.ftmo_config,
        dry_run          = args.dry_run,
        initial_balance  = args.balance,
    )
    bot.start()


if __name__ == "__main__":
    main()
