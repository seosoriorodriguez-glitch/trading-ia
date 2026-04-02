# -*- coding: utf-8 -*-
"""
Diagnostico profundo: replica EXACTAMENTE lo que hace _build_active_obs del bot.
Muestra por que cada OB es rechazado.
Uso: python test_obs_debug.py
"""
import sys, bisect
sys.path.insert(0, '.')

import MetaTrader5 as mt5
import pandas as pd
from strategies.order_block.backtest.ob_detection import detect_order_blocks, OBStatus
from strategies.order_block_btc.backtest.config import BTC_PARAMS

SYMBOL = "BTCUSD"

# --- Verificar error log ---
from pathlib import Path
from datetime import datetime, timezone
today = datetime.now(timezone.utc).strftime("%Y%m%d")
err_log = Path(f"logs_ob_btc/errors_{today}.log")
if err_log.exists():
    content = err_log.read_text(encoding="utf-8")
    if content.strip():
        print("=== ERRORES EN EL LOG DEL BOT ===")
        print(content[-2000:])  # ultimas 2000 chars
        print("=================================\n")
    else:
        print("Log de errores: vacio (sin errores)\n")
else:
    print(f"Log de errores no existe aun ({err_log})\n")

# --- Conectar MT5 ---
if not mt5.initialize():
    print(f"ERROR MT5: {mt5.last_error()}")
    sys.exit()

# --- Descargar M5 igual que el bot (350 velas) ---
rates = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_M5, 0, 350)
df_m5 = pd.DataFrame(rates)
df_m5["time"] = pd.to_datetime(df_m5["time"], unit="s")
print(f"M5: {len(df_m5)} velas | {df_m5['time'].iloc[0]} -> {df_m5['time'].iloc[-1]}")

now = df_m5.iloc[-1]["time"].to_pydatetime()
print(f"now (ultima vela M5): {now}\n")

# --- Detectar OBs ---
all_obs = detect_order_blocks(df_m5, BTC_PARAMS)
print(f"OBs detectados total: {len(all_obs)}")

# --- Replicar _build_active_obs con razon de rechazo ---
m5_times  = df_m5["time"].tolist()
m5_closes = df_m5["close"].tolist()
n_m5      = len(m5_times)
expiry    = BTC_PARAMS["expiry_candles"]

active = []
rejected = {"lookahead": 0, "mitigated": 0, "no_index": 0, "destroyed": 0, "expired": 0, "ok": 0}

for ob in all_obs:
    ob_conf = ob.confirmed_at
    if isinstance(ob_conf, pd.Timestamp):
        ob_conf = ob_conf.to_pydatetime()

    if ob_conf > now:
        rejected["lookahead"] += 1
        continue

    idx_start = bisect.bisect_left(m5_times, ob_conf)
    if idx_start >= n_m5:
        rejected["no_index"] += 1
        continue

    alive = True
    candles_since = 0
    reason = "ok"
    for j in range(idx_start, n_m5):
        c = m5_closes[j]
        if ob.ob_type == "bullish" and c < ob.zone_low:
            alive = False
            reason = f"destroyed (close={c:.2f} < zone_low={ob.zone_low:.2f})"
            break
        if ob.ob_type == "bearish" and c > ob.zone_high:
            alive = False
            reason = f"destroyed (close={c:.2f} > zone_high={ob.zone_high:.2f})"
            break
        candles_since += 1
        if candles_since >= expiry:
            alive = False
            reason = f"expired ({candles_since} velas)"
            break

    if alive:
        ob.status = OBStatus.FRESH
        active.append(ob)
        rejected["ok"] += 1
        print(f"  ACTIVO  {ob.ob_type:8s} [{ob.zone_low:.2f}-{ob.zone_high:.2f}] conf={ob_conf}")
    else:
        key = reason.split()[0]
        rejected[key if key in rejected else "destroyed"] += 1
        print(f"  RECHAZ  {ob.ob_type:8s} [{ob.zone_low:.2f}-{ob.zone_high:.2f}] conf={ob_conf} -> {reason}")

print(f"\nResumen:")
print(f"  Activos   : {len(active)}")
print(f"  Lookahead : {rejected['lookahead']}")
print(f"  Sin index : {rejected['no_index']}")
print(f"  Destroyed : {rejected['destroyed']}")
print(f"  Expired   : {rejected['expired']}")

mt5.shutdown()
