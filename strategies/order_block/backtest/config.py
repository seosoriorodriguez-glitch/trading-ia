# -*- coding: utf-8 -*-
"""
Parametros de la estrategia Order Block Hibrido V1.
Modificar aqui para re-correr el backtest con distintas configuraciones.
"""

DEFAULT_PARAMS = {
    # --- Deteccion OB (TF mayor) ---
    "consecutive_candles": 4,       # N velas consecutivas del mismo color tras el OB
    "min_impulse_pct": 0.0,         # % minimo de movimiento (0 = desactivado)
    "zone_type": "half_candle",     # "half_candle": [low,open] bull / [open,high] bear
                                    # "full_candle": [low,high] de la vela OB
    "max_atr_mult": 3.5,            # Zona maxima permitida = ATR(14) * max_atr_mult
    "expiry_candles": 100,          # Velas del TF mayor sin toque -> OB expira
    "max_active_obs": 10,           # Maximo OBs activos simultaneos (los mas recientes)

    # --- Entrada (TF menor) ---
    "entry_method": "aggressive",   # Al primer cierre que toca la zona

    # --- Risk Management ---
    "buffer_points": 20,            # Buffer del SL fuera del extremo de la zona
    "min_risk_points": 15,          # Riesgo minimo aceptable (pts)
    "max_risk_points": 300,         # Riesgo maximo aceptable (pts)
    "target_rr": 2.5,               # R:R objetivo para TP
    "min_rr_ratio": 1.2,            # R:R minimo para aceptar el trade
    "risk_per_trade_pct": 0.005,    # 0.5% del balance por trade
    "max_simultaneous_trades": 2,

    # --- Costos ---
    "avg_spread_points": 2,         # Spread simulado (pts)
    "point_value": 1.0,             # US30: 1 punto = $1 por lote

    # --- Filtros horarios (UTC) ---
    # NY completa hasta cierre oficial: 13:30-20:00 UTC (9:30 AM - 4:00 PM EST)
    # skip_minutes=15: evita volatilidad errática de los primeros 15 min post-apertura
    # Backtest 101d: WR 42.7%, retorno +24.4%, DD max 4.07% (vs 19.5% con cierre a 19:30)
    "sessions": {
        "new_york": {"start": "13:30", "end": "20:00", "skip_minutes": 15},
    },

    # --- Filtro de tendencia: EMA 4H ---
    "ema_trend_filter": False,     # Desactivado: bloquea trades ganadores en M5/M1
    "ema_4h_period": 20,          # Reservado, no activo

    # --- Filtro 1: Vela de rechazo ---
    # Desactivado: la zona OB es señal suficiente en NY. Activarlo reduce trades y retorno.
    "require_rejection": False,
    "pin_bar_wick_ratio": 2.0,
    "pin_bar_max_body_pct": 0.40,
    "engulfing_body_ratio": 1.0,

    # --- Filtro 2: BOS — Break of Structure ---
    # Activado: 240 trades en 99d, WR 37.1%, retorno +27.1%
    "require_bos": True,
    "bos_lookback": 20,

    # --- Balance inicial ---
    "initial_balance": 100_000.0,
}
