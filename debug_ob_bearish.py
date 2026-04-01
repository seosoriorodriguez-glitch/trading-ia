# -*- coding: utf-8 -*-
"""
Script de DIAGNOSTICO TEMPORAL - NO modifica el bot live.
Descarga las mismas velas M5 que usa el bot y analiza por qué no hay OBs bearish.
"""
import sys
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timezone

from strategies.order_block.backtest.ob_detection import detect_order_blocks, OrderBlock
from strategies.order_block.backtest.config import DEFAULT_PARAMS

if not mt5.initialize():
    print("ERROR: No se pudo conectar a MT5")
    sys.exit(1)

symbol = "US30.cash"
rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M5, 0, 350)
if rates is None or len(rates) == 0:
    print("ERROR: No se pudieron obtener velas M5")
    mt5.shutdown()
    sys.exit(1)

df_m5 = pd.DataFrame(rates)
df_m5["time"] = pd.to_datetime(df_m5["time"], unit="s")

print(f"Velas M5 descargadas: {len(df_m5)}")
print(f"Rango: {df_m5['time'].iloc[0]} -> {df_m5['time'].iloc[-1]}")
print()

all_obs = detect_order_blocks(df_m5, DEFAULT_PARAMS)

n_bull = sum(1 for ob in all_obs if ob.ob_type == "bullish")
n_bear = sum(1 for ob in all_obs if ob.ob_type == "bearish")
print(f"Total OBs detectados: {len(all_obs)} (bull: {n_bull}, bear: {n_bear})")
print()

if n_bear > 0:
    print("=" * 70)
    print("  BEARISH OBs DETECTADOS")
    print("=" * 70)
    for ob in all_obs:
        if ob.ob_type == "bearish":
            print(f"  confirmed_at: {ob.confirmed_at}")
            print(f"  zone: [{ob.zone_low:.2f}, {ob.zone_high:.2f}]  (size: {ob.zone_high - ob.zone_low:.1f} pts)")
            print(f"  ob_candle_time: {ob.ob_candle_time}")
            print()
else:
    print("*** NINGUN OB BEARISH DETECTADO ***")
    print()

now = df_m5.iloc[-1]["time"]
if isinstance(now, pd.Timestamp):
    now = now.to_pydatetime()

print("=" * 70)
print("  BUSCANDO MANUALMENTE VELAS ALCISTAS + 4 BAJISTAS CONSECUTIVAS")
print("  (alrededor de precio 46700-46800)")
print("=" * 70)

n = DEFAULT_PARAMS["consecutive_candles"]  # 4
for i in range(len(df_m5) - n - 1):
    ob_candle = df_m5.iloc[i]
    
    if not (ob_candle["close"] > ob_candle["open"]):
        continue
    
    if ob_candle["high"] < 46600 or ob_candle["high"] > 46900:
        continue
    
    window = df_m5.iloc[i + 1: i + 1 + n]
    all_bearish = (window["close"] < window["open"]).all()
    
    candle_details = []
    for j in range(n):
        c = df_m5.iloc[i + 1 + j]
        is_bear = c["close"] < c["open"]
        candle_details.append(f"    Vela {j+1}: O={c['open']:.2f} H={c['high']:.2f} L={c['low']:.2f} C={c['close']:.2f} {'BEAR' if is_bear else 'BULL/DOJI'} (diff={c['close']-c['open']:.2f})")
    
    print(f"\nVela OB candidata [{i}]: {ob_candle['time']}")
    print(f"  O={ob_candle['open']:.2f} H={ob_candle['high']:.2f} L={ob_candle['low']:.2f} C={ob_candle['close']:.2f}")
    print(f"  Zone seria: [{ob_candle['open']:.2f}, {ob_candle['high']:.2f}] (half_candle)")
    print(f"  4 consecutivas todas bajistas? {'SI' if all_bearish else 'NO'}")
    for cd in candle_details:
        print(cd)
    
    if all_bearish:
        zone_low = ob_candle["open"]
        zone_high = ob_candle["high"]
        zone_size = zone_high - zone_low
        
        atr_col = df_m5["high"] - df_m5["low"]
        prev_close = df_m5["close"].shift(1)
        tr = pd.concat([
            df_m5["high"] - df_m5["low"],
            (df_m5["high"] - prev_close).abs(),
            (df_m5["low"] - prev_close).abs(),
        ], axis=1).max(axis=1)
        atr = tr.rolling(14, min_periods=1).mean()
        atr_val = atr.iloc[i]
        max_zone = atr_val * DEFAULT_PARAMS["max_atr_mult"]
        
        print(f"  ATR(14) = {atr_val:.2f}, max_zone = {max_zone:.2f}")
        print(f"  Zone size = {zone_size:.2f}")
        print(f"  Pasa filtro ATR? {'SI' if zone_size <= max_zone else 'NO (RECHAZADO)'}")
        
        confirmed_at = df_m5.iloc[i + n + 1]["time"]
        print(f"  confirmed_at: {confirmed_at}")
        print(f"  now: {now}")
        print(f"  Confirmado? {'SI' if confirmed_at <= now else 'NO (AUN NO)'}")
        
        if confirmed_at <= now and zone_size <= max_zone:
            m5_closes = df_m5["close"].tolist()
            m5_times = df_m5["time"].tolist()
            import bisect
            idx_start = bisect.bisect_left(m5_times, confirmed_at)
            destroyed = False
            for j in range(idx_start, len(m5_closes)):
                if m5_closes[j] > zone_high:
                    print(f"  DESTRUIDO en vela {j}: {df_m5.iloc[j]['time']} close={m5_closes[j]:.2f} > zone_high={zone_high:.2f}")
                    destroyed = True
                    break
            if not destroyed:
                print(f"  VIVO - deberia estar activo!")

print()
print("=" * 70)
print("  OBs ACTIVOS SEGUN LA MISMA LOGICA DEL BOT")
print("=" * 70)

from strategies.order_block.live.ob_monitor import LiveOBMonitor

class FakeDataFeed:
    def __init__(self, df):
        self._df = df
    def get_latest_candles(self, tf, n):
        return self._df

fake_feed = FakeDataFeed(df_m5)
monitor = LiveOBMonitor(DEFAULT_PARAMS, fake_feed)
n_active = monitor.update_obs()

print(f"OBs activos: {n_active}")
for ob in monitor.active_obs:
    print(f"  {ob.ob_type}: zone=[{ob.zone_low:.2f}, {ob.zone_high:.2f}] confirmed={ob.confirmed_at}")

mt5.shutdown()
print("\nDiagnostico completado.")
