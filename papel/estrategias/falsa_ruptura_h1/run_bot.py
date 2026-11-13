# -*- coding: utf-8 -*-
"""
Arranque del bot de la FALSA RUPTURA H1 en cuenta real (en papel lo corre papel/runner.py).

    # ver que haria, sin enviar ordenes:
    python papel/estrategias/falsa_ruptura_h1/run_bot.py --config papel/estrategias/falsa_ruptura_h1/config/darwinex.yaml --dry-run
    # operar:
    python papel/estrategias/falsa_ruptura_h1/run_bot.py --config papel/estrategias/falsa_ruptura_h1/config/darwinex.yaml

Para detener: crear el archivo indicado en el config (STOP_FALSA_RUPTURA.txt en la raiz del proyecto) o Ctrl+C.
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

from papel.estrategias.falsa_ruptura_h1.bot import BotFR


def main():
    p = argparse.ArgumentParser(description="Bot falsa ruptura H1 (cuenta real)")
    p.add_argument("--config", required=True, help="YAML de la cuenta (config/darwinex.yaml)")
    p.add_argument("--dry-run", action="store_true", help="calcula y muestra las ordenes sin enviarlas")
    a = p.parse_args()
    with open(a.config, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    BotFR(cfg, papel=False, dry_run=a.dry_run).iniciar()


if __name__ == "__main__":
    main()
