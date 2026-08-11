# -*- coding: utf-8 -*-
"""
Mide el ANCHO real de las zonas OB y el riesgo (zone_high-zone_low+buffer) por activo,
y cuantas se rechazan por min_risk/max_risk. Prueba la hipotesis: 'el oro tiene zonas
mucho mas amplias que su limite -> se rechazan -> no toma entradas'.
Uso: python bt_riskdist.py
"""
import sys, copy
from pathlib import Path
if sys.platform == "win32":
    import codecs; sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import numpy as np
from strategies.order_block.backtest.config import DEFAULT_PARAMS
from strategies.order_block.backtest.data_loader import load_csv
from strategies.order_block.backtest.ob_detection import detect_order_blocks

# activo -> (m5, buffer, min_risk, max_risk)  usando la config REAL de cada bot
CFG = {
    "ORO   (XAUUSD)": ("data/XAUUSD_icm_M5_fresh.csv", 4.5, 2.5, 55.0),
    "DAX   (DE40)":   ("data/DE40_icm_M5.csv",         17.0, 10.0, 207.0),
    "US30  (fresh)":  ("data/US30_icm_M5_fresh.csv",   35.0, 15.0, 300.0),
}

for name, (m5f, buf, minr, maxr) in CFG.items():
    df5 = load_csv(m5f)
    p = copy.deepcopy(DEFAULT_PARAMS)
    obs = detect_order_blocks(df5, p)
    price = float(df5.close.median())
    m5rng = float((df5.high - df5.low).median())
    widths = np.array([o.zone_high - o.zone_low for o in obs])
    risks = widths + buf                      # riesgo del STOP: ancho zona + buffer
    too_big = float((risks > maxr).mean() * 100)
    too_small = float((risks < minr).mean() * 100)
    ok = 100 - too_big - too_small
    print(f"=== {name} ===")
    print(f"  precio~{price:.1f}  rangoM5 med={m5rng:.2f}  OBs={len(obs)}")
    print(f"  ancho zona: med={np.median(widths):.2f}  p90={np.percentile(widths,90):.2f}  max={widths.max():.2f}")
    print(f"  RIESGO(zona+buf): med={np.median(risks):.2f}  p90={np.percentile(risks,90):.2f}   limites[{minr}, {maxr}]")
    print(f"  -> ACEPTADAS {ok:.0f}%  |  rechazadas por GRANDE {too_big:.0f}%  |  por CHICA {too_small:.0f}%")
    print(f"  ratio med_riesgo/max_risk = {np.median(risks)/maxr:.2f}  (mientras mas bajo, mas holgura)")
    print("=" * 60)
