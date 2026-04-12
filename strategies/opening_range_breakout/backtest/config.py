# -*- coding: utf-8 -*-
"""
Parametros de la estrategia Opening Range Breakout (ORB) para US30.

Logica (igual que LuxAlgo ORB):
  1. Definir rango de apertura: HIGH y LOW de los primeros N minutos de sesion
  2. Señal LONG: vela M5 cierra SOBRE el ORH
  3. Señal SHORT: vela M5 cierra BAJO el ORL
  4. SL: extremo opuesto del rango + buffer
  5. TP: RR objetivo

Sesion NY: apertura 16:30 UTC+3 (13:30 UTC / 09:30 NY)
"""

ORB_PARAMS = {
    # --- Rango de apertura ---
    "or_duration_minutes": 30,      # Primeros 30 min de sesion para definir el rango
    "session_start": "16:30",       # Hora inicio sesion NY (UTC+3, servidor MT5/FTMO)
    "session_end":   "23:00",       # Hora fin sesion NY

    # --- Entrada ---
    # Breakout: vela M5 cierra sobre ORH (long) o bajo ORL (short)
    "min_range_points": 50,         # Rango minimo valido (evita rangos de ruido)
    "max_range_points": 800,        # Rango maximo valido (evita dias de gap extremo)

    # --- Risk Management ---
    "buffer_points": 10,            # Buffer sobre/bajo el extremo del rango para SL
    "target_rr": 2.0,               # R:R objetivo
    "risk_per_trade_pct": 0.005,    # 0.5% del balance por trade
    "max_simultaneous_trades": 1,   # Max 1 trade por dia (1 señal por sesion)

    # --- Costos ---
    "avg_spread_points": 2,
    "slippage_points": 2,
    "point_value": 1.0,             # US30: 1 punto = $1 por lote

    # --- Filtros ---
    "daily_bias": False,            # Filtro de bias diario (ORM actual vs ORM anterior)
    "max_trades_per_day": 1,        # Solo 1 breakout por sesion (el primero valido)

    # --- FTMO ---
    "ftmo_daily_loss_pct": 4.0,
    "initial_balance": 10_000.0,
}
