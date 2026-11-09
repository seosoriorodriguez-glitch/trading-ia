# -*- coding: utf-8 -*-
"""
Arranque del bot S/R Pivot al toque H1.

    # ver que haria, sin enviar ordenes:
    python papel/estrategias/sr_pivot_h1/run_bot.py --config papel/estrategias/sr_pivot_h1/config/demo.yaml --dry-run
    # operar:
    python papel/estrategias/sr_pivot_h1/run_bot.py --config papel/estrategias/sr_pivot_h1/config/demo.yaml

Para detener: crear el archivo indicado en el config (STOP_SR_PIVOT.txt en la raiz del proyecto).
"""
import sys

if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

import argparse
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from papel.estrategias.sr_pivot_h1.bot import BotSR


def main():
    p = argparse.ArgumentParser(description="Bot S/R Pivot al toque H1")
    p.add_argument("--config", required=True, help="YAML de la cuenta (config/demo.yaml, config/darwinex.yaml)")
    p.add_argument("--dry-run", action="store_true", help="calcula y muestra las ordenes sin enviarlas")
    p.add_argument("--papel", action="store_true",
                   help="paper trading: precios reales de la terminal, ordenes y posiciones virtuales (no envia nada)")
    a = p.parse_args()
    with open(a.config, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    BotSR(cfg, dry_run=a.dry_run, papel=a.papel).iniciar()


if __name__ == "__main__":
    main()
