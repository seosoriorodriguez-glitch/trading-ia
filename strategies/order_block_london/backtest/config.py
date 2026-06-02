# -*- coding: utf-8 -*-
"""
Parametros optimizados de la estrategia Order Block para SESION LONDON.

Simbolo: US30.cash (misma cuenta MT5_BTCUSD, challenge FTMO $10,000)
Sesion:  London 10:00-17:00 UTC+3 (hora servidor MT5/FTMO) = 03:00-10:00 NY
         (ANTES 10:00-19:00; cortado a las 10:00 NY el 2026-06-01 — ver nota abajo)

Optimizacion sobre 518 dias (Oct 2024 - Apr 2026):
  - RR 2.5  : mejor balance retorno/WR/DD para Londres
  - Buffer 35: mas holgura en apertura London donde el spread puede ser mayor
  - Zone half_candle: [low, open] bull / [open, high] bear — igual que Bot 1
  - Sesion 10:00-19:00 UTC+3: London completo (captura early + overlap con NY)

Resultado backtest (518 dias, $10,000):
  Trades: 1182 | WR: 34.7% | PF: 1.26 | Retorno: +173.9% | DD: 11.6%

Comparacion vs Bot 1 (NY 13:30-23:00):
  Bot 1: trades=1313 | WR=25.4% | PF=1.13 | ret=+87.6% | DD=17.1%
  Bot 2: trades=1182 | WR=34.7% | PF=1.26 | ret=+173.9% | DD=11.6%  <- MEJOR

NOTA (2026-06-01): el backtest de 518 dias arriba se calculo con la ventana
10:00-19:00. La sesion se acorto a 10:00-17:00 (corte 10:00 NY) tras observar en
real ~2 meses que la cola NY 10:00-12:00 devolvia lo ganado (-777, WR ~9%).
Muestra real US30: corte 12:00 NY -> -159 USD ; corte 10:00 NY -> +618 USD.
PENDIENTE: re-correr backtest 518d con end=17:00 para validar fuera de muestra.
"""

LONDON_PARAMS = {
    # --- Deteccion OB (M5) ---
    "consecutive_candles": 4,         # Igual que Bot 1
    "min_impulse_pct": 0.0,           # Desactivado
    "zone_type": "half_candle",       # [low, open] bull / [open, high] bear
    "max_atr_mult": 3.5,
    "expiry_candles": 100,            # 100 velas M5 sin toque -> OB expira
    "max_active_obs": 10,

    # --- Entrada (M1) ---
    "entry_method": "aggressive",     # Al primer cierre que toca la zona

    # --- Risk Management ---
    "buffer_points": 35,              # Optimizado para London (vs 25 del Bot 1)
    "min_risk_points": 15,            # Igual que Bot 1
    "max_risk_points": 300,           # Igual que Bot 1
    "target_rr": 2.5,                 # Optimizado para London (vs 3.5 del Bot 1)
    "min_rr_ratio": 1.2,
    "risk_per_trade_pct": 0.005,      # 0.5% del balance por trade
    "max_simultaneous_trades": 2,

    # --- Costos ---
    "avg_spread_points": 2,           # Igual que Bot 1 (spread simulado)
    "slippage_points": 2,             # Slippage en entrada + salida SL (pts); TP no tiene slippage
    "point_value": 1.0,               # US30: 1 punto = $1 por lote

    # --- Sesion London: 10:00-17:00 UTC+3 (servidor) = 03:00-10:00 NY ---
    # Equivalente: 07:00-14:00 UTC
    # Captura: London early + NY open (hasta 09:59 NY, incluye la vela del open 09:00)
    # CORTE 10:00 NY: se elimina la cola post-apertura NY 10:00-12:00 (chop, WR ~9%,
    #   -777 en muestra real ~2 meses): post-apertura devolviamos lo ganado antes.
    "sessions": {
        "london": {"start": "10:00", "end": "17:00", "skip_minutes": 15},
    },

    # --- Filtro EMA (desactivado) ---
    "ema_trend_filter": False,
    "ema_4h_period": 20,

    # --- Filtro rechazo (desactivado) ---
    "require_rejection": False,
    "pin_bar_wick_ratio": 2.0,
    "pin_bar_max_body_pct": 0.40,
    "engulfing_body_ratio": 1.0,

    # --- Filtro BOS (desactivado) ---
    "require_bos": False,
    "bos_lookback": 20,

    # --- Balance inicial ---
    "initial_balance": 10_000.0,
}
