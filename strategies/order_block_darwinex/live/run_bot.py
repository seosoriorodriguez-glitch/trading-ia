# -*- coding: utf-8 -*-
"""
Punto de entrada del Order Block DARWINEX Bot (WS30).
Copia independiente de order_block_london/live/run_bot.py — NO afecta a FTMO.

Uso:
    # Demo (sin ordenes reales):
    python strategies/order_block_darwinex/live/run_bot.py --dry-run --balance 100000

    # Produccion:
    python strategies/order_block_darwinex/live/run_bot.py --balance 100000

Para detener: crear archivo STOP_DARWINEX.txt en la raiz del proyecto.

IMPORTANTE:
  - Este bot opera WS30 (Dow Jones en Darwinex) en la instancia MT5_BREAKERBLOCKS
  - Cuenta: Darwinex Zero (virtual $100k)
  - Magic number: 345681 (distinto a FTMO London 345680)
  - Lotaje broker-agnostico: lee el valor por punto de MT5 (WS30 = $0.1/punto)
  - NO comparte archivos con los bots FTMO
"""
import sys
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from strategies.order_block_darwinex.live.trading_bot import OrderBlockDarwinexBot


def main():
    parser = argparse.ArgumentParser(description="Order Block DARWINEX Bot - WS30")
    parser.add_argument("--symbol",   default="WS30",
                        help="Simbolo MT5 (default: WS30)")
    parser.add_argument("--balance",  type=float, default=100_000.0,
                        help="Balance inicial (default: 100000)")
    parser.add_argument("--ftmo-config", default=None,
                        help="Ruta al YAML de reglas de riesgo")
    parser.add_argument("--terminal-path", default=None,
                        help=r"Ruta al terminal64.exe de la instancia MT5 "
                             r"(default: C:\Program Files\MT5_BREAKERBLOCKS\terminal64.exe).")
    parser.add_argument("--dry-run",  action="store_true",
                        help="Modo simulacion: no envia ordenes reales a MT5")
    args = parser.parse_args()

    bot = OrderBlockDarwinexBot(
        symbol           = args.symbol,
        ftmo_config_path = args.ftmo_config,
        dry_run          = args.dry_run,
        initial_balance  = args.balance,
        terminal_path    = args.terminal_path,
    )
    bot.start()


if __name__ == "__main__":
    main()
