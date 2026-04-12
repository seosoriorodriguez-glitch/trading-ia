# -*- coding: utf-8 -*-
"""
Entrypoint — Breaker Block Bot — FTMO Free Trial $100k — US30

Uso:
    python strategies/breaker_block/live/run_bot.py
    python strategies/breaker_block/live/run_bot.py --dry-run
    python strategies/breaker_block/live/run_bot.py --balance 100000

Detener:
    Ctrl+C  o  crear archivo STOP_BB.txt en el directorio de trabajo

MT5:
    Apunta a C:\\Program Files\\MT5_BREAKERBLOCKS\\terminal64.exe
"""
import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from strategies.breaker_block.live.trading_bot import BreakerBlockBot


def main():
    parser = argparse.ArgumentParser(description="Breaker Block Bot — FTMO Free Trial")
    parser.add_argument("--dry-run", action="store_true",
                        help="Modo simulacion (no envia ordenes reales)")
    parser.add_argument("--balance", type=float, default=100_000.0,
                        help="Balance inicial de la cuenta (default: $100,000)")
    args = parser.parse_args()

    bot = BreakerBlockBot(
        symbol          = "US30.cash",
        dry_run         = args.dry_run,
        initial_balance = args.balance,
    )
    bot.start()


if __name__ == "__main__":
    main()
