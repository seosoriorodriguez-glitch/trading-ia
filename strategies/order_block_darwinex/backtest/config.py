# -*- coding: utf-8 -*-
"""
Parametros de la estrategia Order Block para DARWINEX (cuenta Zero, simbolo WS30).

Copia independiente de order_block_london/backtest/config.py.
MISMA estrategia (deteccion OB, entrada, RR, sesion) — solo cambian los parametros
que dependen del broker/cuenta Darwinex.

Diferencias clave vs FTMO:
  - Simbolo:  WS30 (Dow Jones en Darwinex) — el valor por punto es $0.1/lote
              (vs $1/lote en FTMO US30.cash). En LIVE el lotaje se calcula
              leyendo el tick value de MT5 (broker-agnostico), no de aqui.
  - Leverage: 20:1 (Darwinex es FCA/ESMA -> indices topados a 20:1) vs ~100:1 FTMO.
              El margen por lote de WS30 es ~$2,702, asi que a 0.5% muchos trades
              no entrarian por margen. Por eso el riesgo se baja a 0.1% (ver YAML).
  - Balance:  $100,000 (cuenta virtual Darwinex Zero).

La estrategia (entradas/salidas/horario) es IDENTICA a la de FTMO — el edge es el
mismo; solo cambia el tamano por las caracteristicas del broker.
"""

DARWINEX_PARAMS = {
    # --- Deteccion OB (M5) --- (identico a FTMO)
    "consecutive_candles": 4,
    "min_impulse_pct": 0.0,
    "zone_type": "half_candle",
    "max_atr_mult": 3.5,
    "expiry_candles": 100,
    "max_active_obs": 10,

    # --- Entrada (M1) --- (identico a FTMO)
    "entry_method": "aggressive",

    # --- Risk Management ---
    "buffer_points": 35,
    "min_risk_points": 15,
    "max_risk_points": 300,
    "target_rr": 2.5,
    "min_rr_ratio": 1.2,
    "risk_per_trade_pct": 0.001,      # 0.1% — bajado por leverage 20:1 de Darwinex
                                      #        (a 0.5% no entraria por margen).
                                      #        LIVE usa el valor del YAML, no este.
    "max_simultaneous_trades": 1,     # 1 en Darwinex (margen ajustado por 20:1)

    # --- Costos ---
    "avg_spread_points": 2,
    "slippage_points": 2,
    "point_value": 0.1,               # WS30 Darwinex: 1 punto = $0.1 por lote
                                      # (LIVE lo lee de MT5; esto es para backtest)

    # --- Sesion London: 10:00-17:00 (hora SERVIDOR de Darwinex) = 03:00-10:00 NY ---
    # OJO: verificar el offset del servidor Darwinex (puede diferir de FTMO UTC+3).
    "sessions": {
        "london": {"start": "10:00", "end": "17:00", "skip_minutes": 15},
    },

    # --- Filtros (desactivados, igual que FTMO) ---
    "ema_trend_filter": False,
    "ema_4h_period": 20,
    "require_rejection": False,
    "pin_bar_wick_ratio": 2.0,
    "pin_bar_max_body_pct": 0.40,
    "engulfing_body_ratio": 1.0,
    "require_bos": False,
    "bos_lookback": 20,

    # --- Balance inicial ---
    "initial_balance": 100_000.0,
}
