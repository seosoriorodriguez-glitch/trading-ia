# -*- coding: utf-8 -*-
"""
Parametros de la estrategia Order Block para DAX (DE40 / GER40), sesiones London + NY.

Copia INDEPENDIENTE de order_block_gold, adaptada a DAX. NO comparte nada con
US30 ni oro de produccion. Corre en la MISMA cuenta free-trial que el oro pero con
magic propio (345683) y riesgo bajisimo -> solo para observar ratios en vivo.

Simbolo: DE40 (ICM) / en FTMO suele ser GER40.cash -> VERIFICAR y pasar --symbol si difiere.
Sesiones: London + NY (both). RR 2.5.

Validacion (motor real M5+M1, data ICM DE40 274d, spread 1.5, robustez por mitades):
  both: PF 1.11 (1.17/1.06) +45%/ano DD 14.2% | NY: PF 1.17 +56%/ano DD 12.4% (mejor)
  Robusta en las 3 sesiones. DAX correlaciona con US30 (ambos indices) -> diversificacion leve.
"""

DAX_PARAMS = {
    # --- Deteccion OB (M5) ---
    "consecutive_candles": 4,
    "min_impulse_pct": 0.0,
    "zone_type": "half_candle",
    "max_atr_mult": 3.5,
    "expiry_candles": 100,
    "max_active_obs": 10,

    # --- Entrada (M1) ---
    "entry_method": "aggressive",

    # --- Risk Management (ESCALADO A DAX, rango M5 mediano ~13.5) ---
    "buffer_points": 17.0,
    "min_risk_points": 10.0,
    "max_risk_points": 207.0,
    "target_rr": 2.5,
    "min_rr_ratio": 1.2,
    "risk_per_trade_pct": 0.001,      # 0.1% BAJISIMO (solo observar ratios; live lee el yaml)
    "max_simultaneous_trades": 1,

    # --- Costos (informativo; en vivo el lotaje usa _usd_per_point de MT5) ---
    "avg_spread_points": 1.5,
    "slippage_points": 1.0,
    "point_value": 1.0,

    # --- Sesiones London + NY (both) ---
    "sessions": {
        "london":   {"start": "10:00", "end": "17:00", "skip_minutes": 15},
        "new_york": {"start": "13:30", "end": "23:00", "skip_minutes": 15},
    },

    # --- Filtros (desactivados, igual que US30/oro) ---
    "ema_trend_filter": False,
    "ema_4h_period": 20,
    "require_rejection": False,
    "pin_bar_wick_ratio": 2.0,
    "pin_bar_max_body_pct": 0.40,
    "engulfing_body_ratio": 1.0,
    "require_bos": False,
    "bos_lookback": 20,

    # --- Balance inicial (misma cuenta free-trial $200k que el oro) ---
    "initial_balance": 200_000.0,
}
