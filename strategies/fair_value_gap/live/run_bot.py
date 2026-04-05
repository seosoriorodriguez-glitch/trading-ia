# -*- coding: utf-8 -*-
"""
Punto de entrada del FVG Bot.

Uso:
    # Demo (sin ordenes reales):
    python strategies/fair_value_gap/live/run_bot.py --dry-run

    # Produccion ($10k FTMO Challenge):
    python strategies/fair_value_gap/live/run_bot.py --balance 10000

    # Simbolo alternativo:
    python strategies/fair_value_gap/live/run_bot.py --symbol NAS100.cash --balance 10000
"""
import sys
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from strategies.fair_value_gap.live.trading_bot import FVGBot


def main():
    parser = argparse.ArgumentParser(description="FVG Bot - US30.cash")
    parser.add_argument("--symbol",   default="US30.cash",
                        help="Simbolo MT5 (default: US30.cash)")
    parser.add_argument("--balance",  type=float, default=10_000.0,
                        help="Balance inicial (default: 10000)")
    parser.add_argument("--ftmo-config", default=None,
                        help="Ruta al YAML de reglas FTMO (default: config/ftmo_rules.yaml)")
    parser.add_argument("--dry-run",  action="store_true",
                        help="Modo simulacion: no envia ordenes reales a MT5")
    args = parser.parse_args()

    bot = FVGBot(
        symbol           = args.symbol,
        ftmo_config_path = args.ftmo_config,
        dry_run          = args.dry_run,
        initial_balance  = args.balance,
    )
    bot.start()


if __name__ == "__main__":
    main()
