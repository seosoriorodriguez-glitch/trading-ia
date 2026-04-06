# -*- coding: utf-8 -*-
"""
Parametros de la estrategia Fair Value Gap.
Modificar aqui para re-correr el backtest con distintas configuraciones.
"""

# Configuracion base para US30
US30_PARAMS = {
    # --- Deteccion FVG (TF mayor) — logica LuxAlgo ---
    # threshold_pct: tamano minimo del gap como % del precio (0 = sin filtro, igual que LuxAlgo default)
    # Ejemplo: 0.05 significa que el gap debe ser >= 0.05% del precio de referencia
    "threshold_pct": 0.0,          # % minimo de gap (0 = desactivado, LuxAlgo default)
    "min_zone_points": 0.0,        # Tamano minimo absoluto del gap en puntos (0 = desactivado)
    "max_atr_mult": 3.5,           # Gap maximo permitido = ATR(14) * max_atr_mult
    "expiry_candles": 100,         # Velas del TF mayor sin toque -> FVG expira
    "max_active_fvgs": 10,         # Maximo FVGs activos simultaneos (los mas recientes)

    # --- Entrada (TF menor) ---
    # "conservative": vela M1 cerrando DENTRO del gap -> orden stop en extremo de la zona
    # "aggressive":   precio TOCANDO la zona -> entrada inmediata
    "entry_method": "conservative",

    # --- Risk Management ---
    "buffer_points": 25,           # Buffer del SL fuera del extremo del gap (pts)
    "min_risk_points": 15,         # Riesgo minimo aceptable (pts)
    "max_risk_points": 300,        # Riesgo maximo aceptable (pts)
    "target_rr": 2.0,              # R:R objetivo para TP (validado backtest 518d)
    "min_rr_ratio": 1.2,           # R:R minimo para aceptar el trade
    "risk_per_trade_pct": 0.005,   # 0.5% del balance por trade (usar fijo en live)
    "max_simultaneous_trades": 2,

    # --- Costos ---
    "avg_spread_points": 2,        # Spread simulado (pts)
    "slippage_points": 2,          # Slippage en entrada (pts)
    "point_value": 1.0,            # US30: 1 punto = $1 por lote

    # --- Filtros horarios (servidor MT5 = UTC+3 para FTMO) ---
    # Asia:   00:00-09:45 UTC+3  (Tokyo/Sydney — cubre FVGs formados en sesiones anteriores)
    # London: 10:00-19:00 UTC+3 = 07:00-16:00 UTC
    # NY:     16:30-23:00 UTC+3 = 13:30-20:00 UTC
    # Overlap London-NY: 16:30-19:00 UTC+3 (zona mas activa)
    # Lunes a viernes — cobertura 24h
    "sessions": {
        "asia":     {"start": "00:00", "end": "09:45", "skip_minutes": 30},
        "london":   {"start": "10:00", "end": "19:00", "skip_minutes": 15},
        "new_york": {"start": "16:30", "end": "23:00", "skip_minutes": 15},
    },

    # --- Filtros opcionales ---
    "require_rejection": False,    # Vela de rechazo en la zona
    "pin_bar_wick_ratio": 2.0,
    "pin_bar_max_body_pct": 0.40,
    "engulfing_body_ratio": 1.0,

    "require_bos": False,          # Break of Structure antes de entrar
    "bos_lookback": 20,

    "ema_trend_filter": False,     # Filtro de tendencia EMA 4H
    "ema_4h_period": 20,

    # --- Reglas FTMO ---
    # daily_loss_limit_pct: si la perdida del dia llega a este % del balance INICIAL
    #   -> se cierran trades abiertos y no se abren nuevos hasta el dia siguiente
    # max_dd_pct: si el drawdown total supera este % -> pausar estrategia (0 = desactivado)
    #   El usuario opera con colchon, por lo que el DD total es menos critico que el diario
    "ftmo_daily_loss_pct": 4.0,    # 4.0% -> cierra el dia con 1% de margen antes del limite FTMO de 5%
    "ftmo_max_dd_pct": 0.0,        # 0 = desactivado (el usuario gestiona con colchon)

    # --- Balance inicial ---
    "initial_balance": 100_000.0,
    "symbol": "US30",
}

# Configuracion base para NAS100
NAS100_PARAMS = {
    # --- Deteccion FVG (TF mayor) — logica LuxAlgo ---
    "threshold_pct": 0.0,          # % minimo de gap (0 = desactivado, LuxAlgo default)
    "max_atr_mult": 3.5,           # Gap maximo permitido = ATR(14) * max_atr_mult
    "expiry_candles": 100,
    "max_active_fvgs": 10,

    # --- Entrada (TF menor) ---
    "entry_method": "conservative",

    # --- Risk Management ---
    "buffer_points": 20,
    "min_risk_points": 10,
    "max_risk_points": 500,
    "target_rr": 3.0,
    "min_rr_ratio": 1.2,
    "risk_per_trade_pct": 0.005,
    "max_simultaneous_trades": 2,

    # --- Costos ---
    "avg_spread_points": 2,
    "slippage_points": 2,
    "point_value": 1.0,            # NAS100: 1 punto = $1 por lote

    # --- Filtros horarios (servidor MT5 = UTC+3 para FTMO) ---
    "sessions": {
        "london":   {"start": "10:00", "end": "19:00", "skip_minutes": 15},
        "new_york": {"start": "16:30", "end": "23:00", "skip_minutes": 15},
    },

    # --- Filtros opcionales ---
    "require_rejection": False,
    "pin_bar_wick_ratio": 2.0,
    "pin_bar_max_body_pct": 0.40,
    "engulfing_body_ratio": 1.0,

    "require_bos": False,
    "bos_lookback": 20,

    "ema_trend_filter": False,
    "ema_4h_period": 20,

    # --- Reglas FTMO ---
    "ftmo_daily_loss_pct": 4.5,
    "ftmo_max_dd_pct": 0.0,

    # --- Balance inicial ---
    "initial_balance": 100_000.0,
    "symbol": "NAS100",
}

# Alias por defecto
DEFAULT_PARAMS = US30_PARAMS
