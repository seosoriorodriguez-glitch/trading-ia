# -*- coding: utf-8 -*-
"""
Parametros de la estrategia S/R Pivot (LuxAlgo "Support and Resistance Levels with Breaks").

Simbolo validado: US30.cash | Deteccion H1 | Ejecucion resuelta en M1
Datos: US30.cash_H1_202401020100_202608112200.csv + US30_M1 / US30.cash_M1

RESULTADO VALIDADO (2024-01 a 2026-08, 32 meses, riesgo 0.5%, cuenta 10k):
  Operaciones: 511 (16/mes) | WR 39.1% | PF 1.23
  Total +36.6% | +1.14%/mes | ~13.7%/ano | maxDD -6.3%
  Meses ganadores 19/32 (59%) | racha perdedora max 9

  In-sample  2024-2025: n=383  +0.84%/mes  PF 1.16
  Out-sample 2026     : n=128  +2.07%/mes  PF 1.44   <- config sin tocar, aguanto

ADVERTENCIA CRITICA — LOOKAHEAD
  1) El indicador Pine REPINTA. pivothigh(15,15) necesita 15 velas POSTERIORES.
     El nivel NO existe hasta pivote + right + 1 barras. Con lookahead el
     backtest da WR 94.8% y t=+51 (fantasia). Ver levels.py.
  2) Cualquier filtro debe usar la vela CERRADA anterior, nunca la vela en curso.
     Un filtro EMA comparando close[k] vs ema[k] dio +0.700R / t=6.35 y paso
     out-of-sample con +0.657R. Era falso: seleccionaba velas que iban a cerrar
     a favor. Con la vela cerrada anterior el mismo filtro da -0.070R.
     => La validacion OOS NO detecta lookahead (el bug esta en ambas mitades).
"""

SR_PIVOT_PARAMS = {
    # --- Deteccion de niveles ---
    "tf_minutes": 60,          # H1. M15/M30/H2/H4 dieron NEGATIVO
    "left":       15,          # barras a la izquierda del pivote
    "right":      15,          # barras a la derecha (define el retraso de activacion)
    "max_levels": 5,           # ultimos 5 pivotes TOTALES (no 5 de cada tipo)
    "level_life": 0,           # 0 = infinita; solo rota al llegar el 6to
    "cluster_pts": 0,          # 0 = no agrupar niveles cercanos (fallo OOS)

    # --- Zona y entrada ---
    "zone_width": 30,          # pts desde el nivel hasta el borde de entrada
    "entry_mode": "touch",     # al toque de mecha, sin confirmacion
    "one_trade_per_level": True,
    "max_concurrent": 1,
    "session": None,           # 24h. La ventana de London dio NEGATIVO

    # --- Salida ---
    "sl_points": 100,          # pts mas alla del nivel. Riesgo = zone_width + sl_points
    "target_rr": 2.0,
    "tp_mode": "rr",           # "rr" fijo. "next" (siguiente nivel) FALLO OOS
    "min_rr": 1.0,             # solo aplica si tp_mode == "next"
    "trail_start": 0.0,        # 0 = sin trailing. Perjudico en las 9 variantes
    "trail_dist": 0.0,
    "partial_at": 0.0,         # 0 = sin parciales. Neutro o peor
    "partial_pct": 0.5,
    "partial_be": True,

    # --- Costos ---
    "cost_points": 4.0,        # 2 spread + 2 slippage (spread real medido ~2 pts)

    # --- Gestion ---
    "risk_per_trade_pct": 0.005,
    "initial_balance": 10_000.0,
}

# Ventana de validacion: NO optimizar mirando datos posteriores a esta fecha.
IN_SAMPLE_END = "2025-12-31"
