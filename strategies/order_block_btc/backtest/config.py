# -*- coding: utf-8 -*-
"""
Parametros optimizados de la estrategia Order Block para BTCUSD.

Optimizacion sobre 351 dias (Apr 2025 - Apr 2026):
  - RR 2.0  : mejor balance retorno/WR para BTC (vs 3.5 de US30)
  - CC 4    : mejor punto entre calidad de setup y cantidad de trades
  - Buffer 50: ajustado a la volatilidad de BTC
  - Sesion 24/7: BTC opera todos los dias, no hay horario de mercado
  - Spread 10 pts: promedio real en ICMarkets para BTCUSD

Resultado backtest:
  Trades: 2143 (6.11/dia) | WR: 39.1% | Return: +193.3% | DD: 12.7% | PF: 1.13
"""

BTC_PARAMS = {
    # --- Deteccion OB (M5) ---
    "consecutive_candles": 4,        # Optimo validado vs CC=3 (mas ruido) y CC=5 (pocos trades)
    "min_impulse_pct": 0.0,          # Desactivado
    "zone_type": "half_candle",      # [low, open] bull / [open, high] bear
    "max_atr_mult": 3.5,
    "expiry_candles": 100,           # Velas M5 sin toque -> OB expira
    "max_active_obs": 10,

    # --- Entrada (M1) ---
    "entry_method": "aggressive",    # Al primer cierre que toca la zona

    # --- Risk Management ---
    "buffer_points": 50,             # Buffer SL (BTC mas volatil que US30 que usa 25)
    "min_risk_points": 10,           # Minimo riesgo aceptable en puntos BTC
    "max_risk_points": 300,          # Maximo riesgo aceptable en puntos BTC
    "target_rr": 2.0,                # RR objetivo (BTC: 2.0 vs US30: 3.5)
    "min_rr_ratio": 1.2,
    "risk_per_trade_pct": 0.005,     # 0.5% del balance por trade (igual que US30)
    "max_simultaneous_trades": 2,

    # --- Costos ---
    "avg_spread_points": 10,         # Spread real BTC en ICMarkets ~10 pts
    "point_value": 1.0,              # BTCUSD: 1 punto = $1 por lote (igual que US30)

    # --- Sesion: 24/7 sin restriccion horaria ---
    # BTC no tiene horario de mercado. Se opera todos los dias, toda la semana.
    # Nota: si se quiere limitar a London+NY usar:
    #   "sessions": {"london_ny": {"start": "13:30", "end": "23:00", "skip_minutes": 15}}
    # Backtest 24/7: +193.3% / DD 12.7%
    # Backtest London+NY: +91.8% / DD 11.0% (mejor calidad por trade pero menos volumen)
    "sessions": {
        "always": {"start": "00:00", "end": "23:59", "skip_minutes": 0},
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
    "initial_balance": 100_000.0,
}
