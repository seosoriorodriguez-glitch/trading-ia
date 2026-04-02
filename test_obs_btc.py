# -*- coding: utf-8 -*-
"""
Diagnostico de OBs BTC: muestra cuantas velas descarga MT5 y cuantos OBs detecta.
Uso: python test_obs_btc.py
"""
import sys
sys.path.insert(0, '.')

import MetaTrader5 as mt5
import pandas as pd
from strategies.order_block.backtest.ob_detection import detect_order_blocks
from strategies.order_block_btc.backtest.config import BTC_PARAMS

SYMBOL = "BTCUSD"

if not mt5.initialize():
    print(f"ERROR MT5: {mt5.last_error()}")
    sys.exit()

tick = mt5.symbol_info_tick(SYMBOL)
print(f"Precio actual: {tick.bid:.2f}")

for tf_name, tf in [("M1", mt5.TIMEFRAME_M1), ("M5", mt5.TIMEFRAME_M5)]:
    rates = mt5.copy_rates_from_pos(SYMBOL, tf, 0, 400)
    if rates is None or len(rates) == 0:
        print(f"{tf_name}: ERROR - no se obtuvieron velas ({mt5.last_error()})")
    else:
        df = pd.DataFrame(rates)
        df["time"] = pd.to_datetime(df["time"], unit="s")
        print(f"{tf_name}: {len(df)} velas  | desde {df['time'].iloc[0]}  hasta {df['time'].iloc[-1]}")

# Detectar OBs con los parametros BTC
rates_m5 = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_M5, 0, 400)
df_m5 = pd.DataFrame(rates_m5)
df_m5["time"] = pd.to_datetime(df_m5["time"], unit="s")

all_obs = detect_order_blocks(df_m5, BTC_PARAMS)
print(f"\nOBs detectados (sin filtros): {len(all_obs)}  ({sum(1 for o in all_obs if o.ob_type=='bullish')} bull / {sum(1 for o in all_obs if o.ob_type=='bearish')} bear)")

# Mostrar los ultimos 5
if all_obs:
    print("\nUltimos 5 OBs:")
    for ob in all_obs[-5:]:
        print(f"  {ob.ob_type:8s} | zone [{ob.zone_low:.2f} - {ob.zone_high:.2f}] | confirmed: {ob.confirmed_at}")
else:
    print("\nNingún OB detectado - posiblemente pocas velas o CC=4 muy estricto en este período")

mt5.shutdown()
