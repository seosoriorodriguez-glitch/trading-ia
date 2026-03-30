# -*- coding: utf-8 -*-
"""
Parametros Order Block para pares Forex (EURUSD, GBPJPY).
Escala completamente diferente a US30 — NO mezclar.

EURUSD: precios ~1.16, buffer en pips (0.0001)
GBPJPY: precios ~211,  buffer en pips (0.01)
"""

EURUSD_PARAMS = {
    # --- Deteccion OB (M5) ---
    "consecutive_candles": 4,
    "min_impulse_pct":     0.0,
    "zone_type":           "half_candle",
    "max_atr_mult":        3.5,
    "expiry_candles":      100,
    "max_active_obs":      10,

    # --- Entrada (M1) ---
    "entry_method": "aggressive",

    # --- Risk Management ---
    # EURUSD: 1 pip = 0.0001. Buffer 15 pips = 0.0015
    "buffer_points":    0.0015,   # 15 pips
    "min_risk_points":  0.0010,   # 10 pips minimo
    "max_risk_points":  0.0150,   # 150 pips maximo
    "target_rr":        2.5,
    "min_rr_ratio":     1.2,
    "risk_per_trade_pct": 0.005,  # 0.5% balance
    "max_simultaneous_trades": 2,

    # --- Costos ---
    "avg_spread_points": 0.0002,  # ~2 pips spread EURUSD
    "point_value":       1.0,

    # --- Sesion NY ---
    "sessions": {
        "new_york": {"start": "13:30", "end": "19:30", "skip_minutes": 15},
    },

    # --- Filtros desactivados (igual que US30 validado) ---
    "ema_trend_filter":    False,
    "ema_4h_period":       20,
    "require_rejection":   False,
    "pin_bar_wick_ratio":  2.0,
    "pin_bar_max_body_pct": 0.40,
    "engulfing_body_ratio": 1.0,
    "require_bos":         False,
    "bos_lookback":        20,

    "initial_balance": 100_000.0,
}


GBPJPY_PARAMS = {
    # --- Deteccion OB (M5) ---
    "consecutive_candles": 4,
    "min_impulse_pct":     0.0,
    "zone_type":           "half_candle",
    "max_atr_mult":        3.5,
    "expiry_candles":      100,
    "max_active_obs":      10,

    # --- Entrada (M1) ---
    "entry_method": "aggressive",

    # --- Risk Management ---
    # GBPJPY: 1 pip = 0.01. Buffer 20 pips = 0.20
    "buffer_points":    0.20,     # 20 pips
    "min_risk_points":  0.15,     # 15 pips minimo
    "max_risk_points":  3.00,     # 300 pips maximo
    "target_rr":        2.5,
    "min_rr_ratio":     1.2,
    "risk_per_trade_pct": 0.005,
    "max_simultaneous_trades": 2,

    # --- Costos ---
    "avg_spread_points": 0.03,    # ~3 pips spread GBPJPY
    "point_value":       1.0,

    # --- Sesion NY ---
    "sessions": {
        "new_york": {"start": "13:30", "end": "19:30", "skip_minutes": 15},
    },

    # --- Filtros desactivados ---
    "ema_trend_filter":    False,
    "ema_4h_period":       20,
    "require_rejection":   False,
    "pin_bar_wick_ratio":  2.0,
    "pin_bar_max_body_pct": 0.40,
    "engulfing_body_ratio": 1.0,
    "require_bos":         False,
    "bos_lookback":        20,

    "initial_balance": 100_000.0,
}
