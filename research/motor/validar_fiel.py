# -*- coding: utf-8 -*-
"""
Comprueba que MotorFiel reproduce EXACTAMENTE backtester_limit_orders.

Correr esto antes de creerle cualquier numero al motor abierto. Compara trade a
trade (hora de entrada, hora de salida, precios, motivo de salida, R) sobre
2024, 2025 y 2026. Si algo difiere, el motor abierto no sirve como referencia.

    python research/motor/validar_fiel.py
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd

from research.motor.motor_fiel import MotorFiel, Zona
from research.vwap.vwap_lab import load_with_volume
from strategies.order_block.backtest.backtester_limit_orders import (
    OrderBlockBacktesterLimitOrders,
)
from strategies.order_block.backtest.ob_detection import detect_order_blocks
from strategies.order_block_london.backtest.config import LONDON_PARAMS

CSV = os.path.join(r"C:\Users\sosor\OneDrive\Documentos\velas m1",
                   "US30_M1_202401020100_202605201838.csv")
COLS = ["entry_time", "exit_time", "direction", "entry_price", "sl", "tp",
        "exit_price", "exit_reason", "pnl_r"]
TRAMOS = [("2024-01-01", "2025-01-01", "2024"),
          ("2025-01-01", "2026-01-01", "2025"),
          ("2026-01-01", "2026-05-20", "2026")]


def m5(plain):
    return (plain.set_index("time").resample("5min", label="left", closed="left")
            .agg({"open": "first", "high": "max", "low": "min", "close": "last"})
            .dropna().reset_index())


def main():
    full = load_with_volume(CSV)
    todo_ok = True
    for ini, fin, etiqueta in TRAMOS:
        m1 = full[(full.time >= ini) & (full.time < fin)].reset_index(drop=True)
        plain = m1[["time", "open", "high", "low", "close"]]
        h5 = m5(plain)

        orig = OrderBlockBacktesterLimitOrders(LONDON_PARAMS).run(h5, plain)
        zonas = [Zona(o.confirmed_at, o.zone_low, o.zone_high,
                      "alcista" if o.ob_type == "bullish" else "bajista", "OB")
                 for o in detect_order_blocks(h5, LONDON_PARAMS)]
        abierto = MotorFiel(LONDON_PARAMS).run(h5, plain, zonas)

        igual = len(orig) == len(abierto) and all(
            orig[c].reset_index(drop=True).equals(abierto[c].reset_index(drop=True))
            for c in COLS)
        todo_ok &= igual
        print(f"  {etiqueta}  n={len(orig):4d}  R={orig.pnl_r.sum():+7.1f}  "
              f"identico: {'SI' if igual else 'NO'}")

    print("\nOK: el motor abierto es fiel." if todo_ok
          else "\nFALLO: el motor abierto NO reproduce el original.")
    return 0 if todo_ok else 1


if __name__ == "__main__":
    sys.exit(main())
