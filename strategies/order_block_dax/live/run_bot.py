# -*- coding: utf-8 -*-
"""
Punto de entrada del Order Block ORO (DE40) Bot.

Uso:
    # Demo / observacion (sin ordenes reales):
    python strategies/order_block_dax/live/run_bot.py --dry-run --balance 200000

    # Free Trial $200k (terminal MT5_FVG por defecto):
    python strategies/order_block_dax/live/run_bot.py --balance 200000

Para detener: crear archivo STOP_DAX.txt en la raiz del proyecto.

IMPORTANTE:
  - Este bot opera DE40 en la instancia MT5_FVG (donde estaba el FVG)
  - Sesion: London 10:00-17:00 UTC+3 | RR 2.5 | riesgo 0.5%
  - Magic number: 345683 (unico; NY=345678, BTC=345679, London US30=345680, Darwinex=345681)
  - 100% INDEPENDIENTE: no toca ni interfiere con el bot US30 London de produccion
"""
import sys
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from strategies.order_block_dax.live.trading_bot import OrderBlockDaxBot


def main():
    parser = argparse.ArgumentParser(description="Order Block ORO Bot - DE40")
    parser.add_argument("--symbol",   default="DE40",
                        help="Simbolo MT5 (default: DE40)")
    parser.add_argument("--balance",  type=float, default=200_000.0,
                        help="Balance inicial (default: 200000)")
    parser.add_argument("--ftmo-config", default=None,
                        help="Ruta al YAML de reglas FTMO")
    parser.add_argument("--terminal-path", default=None,
                        help=r"Ruta al terminal64.exe de la instancia MT5 "
                             r"(default: C:\Program Files\MT5_FVG\terminal64.exe). "
                             r"Usar otra para correr en otra cuenta.")
    parser.add_argument("--dry-run",  action="store_true",
                        help="Modo simulacion: no envia ordenes reales a MT5")
    args = parser.parse_args()

    bot = OrderBlockDaxBot(
        symbol           = args.symbol,
        ftmo_config_path = args.ftmo_config,
        dry_run          = args.dry_run,
        initial_balance  = args.balance,
        terminal_path    = args.terminal_path,
    )
    bot.start()


if __name__ == "__main__":
    main()
