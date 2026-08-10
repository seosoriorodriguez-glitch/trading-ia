# -*- coding: utf-8 -*-
"""
Parametros de la estrategia Order Block para ORO (XAUUSD), sesion LONDON.

Copia INDEPENDIENTE de order_block_london (US30.cash), adaptada a XAUUSD.
NO comparte nada con el bot de produccion US30.

Simbolo: XAUUSD
Sesion:  London + NY (AMBAS) — 10:00-23:00 servidor. Modo free-trial para juntar
         data de las dos. Para cuenta real -> volver a London solo (DD mas bajo).

Params de ESCALA recalibrados al rango M5 del oro (mediano ~3.0-3.6 pts) — el motor
es R-normalizado, pero buffer/min/max_risk son absolutos y deben escalar al instrumento.
Ratios calibrados vs US30 (mismos que la validacion multi-activo: journal/analysis/ob_multiasset.py).

Validacion oro (motor real M5+M1, data ICM, spread real 0.40, robustez por mitades):
  London RR 2.5: fresca(280d) PF 1.36 (1.62/1.14) +89%/ano DD 9.0% |
                 larga(517d) PF 1.20 (1.22/1.18) +50%/ano DD 12.8%
  Robusta en AMBAS muestras = no overfit. RR 2.5 elegido (igual que US30 London;
  mas retorno que 3.0/3.5, DD ~9-13% aceptable con colchon).
"""

GOLD_PARAMS = {
    # --- Deteccion OB (M5) ---
    "consecutive_candles": 4,
    "min_impulse_pct": 0.0,
    "zone_type": "half_candle",       # [low, open] bull / [open, high] bear
    "max_atr_mult": 3.5,
    "expiry_candles": 100,            # 100 velas M5 sin toque -> OB expira
    "max_active_obs": 10,

    # --- Entrada (M1) ---
    "entry_method": "aggressive",     # Al primer cierre que toca la zona

    # --- Risk Management (ESCALADO A ORO) ---
    "buffer_points": 4.5,             # ~1.28x rango M5 mediano del oro
    "min_risk_points": 2.5,           # descarta zonas diminutas (< costo)
    "max_risk_points": 55.0,          # descarta zonas gigantes
    "target_rr": 2.5,                 # elegido: igual que US30 London, robusto en oro
    "min_rr_ratio": 1.2,
    "risk_per_trade_pct": 0.005,      # 0.5% (challenge rapido; funded -> 0.4%)
    "max_simultaneous_trades": 1,     # como la validacion (mas conservador que US30=2)

    # --- Costos (informativo; en vivo el lotaje usa _usd_per_point de MT5) ---
    "avg_spread_points": 0.4,         # spread real oro all-in
    "slippage_points": 0.2,
    "point_value": 100.0,             # XAUUSD: 1 lote = 100 oz -> $100 por 1.0 de precio

    # --- Sesiones London + NY (AMBAS) — para juntar data en el Free Trial ---
    # London 10:00-17:00 + NY 13:30-23:00 (servidor UTC+3). Cobertura ~10:00-23:00.
    # Cada trade se etiqueta por sesion -> luego se separa London vs NY.
    # both a RR 2.5: fresca +122%/ano DD 15%. DD mas alto que London solo (ok en free trial).
    "sessions": {
        "london":   {"start": "10:00", "end": "17:00", "skip_minutes": 15},
        "new_york": {"start": "13:30", "end": "23:00", "skip_minutes": 15},
    },

    # --- Filtros (desactivados, igual que US30) ---
    "ema_trend_filter": False,
    "ema_4h_period": 20,
    "require_rejection": False,
    "pin_bar_wick_ratio": 2.0,
    "pin_bar_max_body_pct": 0.40,
    "engulfing_body_ratio": 1.0,
    "require_bos": False,
    "bos_lookback": 20,

    # --- Balance inicial (Free Trial $200k donde estaba el FVG) ---
    "initial_balance": 200_000.0,
}
