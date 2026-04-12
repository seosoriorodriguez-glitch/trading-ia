# -*- coding: utf-8 -*-
"""
Parametros de la estrategia Breaker Block para US30.

Logica (igual que LuxAlgo Breaker Blocks with Signals):
  1. Detectar MSS (Market Structure Shift) con ZigZag
  2. Identificar la primera vela verde/roja antes del impulso que rompio estructura
  3. Esperar pullback a esa zona → entrada conservadora (STOP en borde)
  4. SL: extremo opuesto del BB + buffer
  5. TP: RR objetivo

Diferencia vs OB:
  - OB: zona de impulso original
  - BB: OB que fue roto por la estructura → pullback post-ruptura
"""

BB_PARAMS = {
    # --- Deteccion OB (M5) — mismos params que ob_detection.py ---
    "consecutive_candles": 4,      # Velas consecutivas para confirmar OB (igual que bot live)
    "zone_type":          "half_candle",  # "half_candle" o "full_candle"
    "min_impulse_pct":    0.0,     # Filtro impulso minimo (0 = desactivado)
    "max_atr_mult":       999.0,   # Filtro ATR maximo (999 = desactivado)
    "expiry_candles":     100,     # Velas M5 sin toque → BB expira
    "max_active_obs":     10,      # Max OBs activos en deteccion
    "max_active_bbs":     10,      # Max BBs activos en backtest

    # --- Entrada (M1) conservadora ---
    # Vela M1 cierra DENTRO del BB → orden STOP en borde
    # LONG:  stop BUY  en zone_high
    # SHORT: stop SELL en zone_low
    "entry_method":       "conservative",

    # --- Risk Management ---
    "buffer_points":      25,      # Buffer SL fuera del BB
    "min_risk_points":    15,      # Riesgo minimo aceptable
    "max_risk_points":    300,     # Riesgo maximo aceptable
    "target_rr":          2.0,     # R:R objetivo
    "min_rr_ratio":       1.2,
    "risk_per_trade_pct": 0.005,   # 0.5% del balance
    "max_simultaneous_trades": 1,

    # --- Costos ---
    "avg_spread_points":  2,
    "slippage_points":    2,
    "point_value":        1.0,     # US30: 1 punto = $1

    # --- Filtros horarios (UTC+3 servidor MT5) ---
    "sessions": {
        "asia":     {"start": "00:00", "end": "09:45", "skip_minutes": 30},
        "london":   {"start": "10:00", "end": "19:00", "skip_minutes": 15},
        "new_york": {"start": "16:30", "end": "23:00", "skip_minutes": 15},
    },

    # --- FTMO ---
    "ftmo_daily_loss_pct": 4.0,
    "ftmo_max_dd_pct":     0.0,

    # --- Balance inicial ---
    "initial_balance":    10_000.0,
    "symbol":             "US30",
}
