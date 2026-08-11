# -*- coding: utf-8 -*-
"""
Verifica si el filtro de spread esta bloqueando entradas. Mide el spread REAL de oro
(XAUUSD) y DAX (GER40.cash) desde el terminal MT5_FVG:
 - spread actual (live)
 - distribucion del spread en las ULTIMAS velas M5, SOLO en horario de sesion
 - % de velas de sesion cuyo spread SUPERA el limite del bot (oro 0.6, dax 5.0)

Uso (en el VPS):  python strategies/order_block_gold/live/check_spread.py
"""
import sys
import time
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
import MetaTrader5 as mt5
import pandas as pd

TERMINAL = r"C:\Program Files\MT5_FVG\terminal64.exe"
# (simbolo, limite_del_bot, sesion_horas_servidor)
TARGETS = [("XAUUSD", 0.6, (10, 23)), ("GER40.cash", 5.0, (10, 23))]
N_BARS = 3000  # ~10 dias de M5

if not mt5.initialize(path=TERMINAL):
    print(f"NO conecta: {mt5.last_error()}"); sys.exit(1)

for symbol, gate, (h0, h1) in TARGETS:
    if not mt5.symbol_select(symbol, True):
        print(f"\n{symbol}: no disponible"); continue
    info = mt5.symbol_info(symbol)
    point = info.point  # 0.01 en oro/dax
    print(f"\n===== {symbol}  (limite bot = {gate}) =====")

    # 1) spread live: muestrear ~8s
    lives = []
    for _ in range(8):
        t = mt5.symbol_info_tick(symbol)
        if t:
            lives.append(round(t.ask - t.bid, 3))
        time.sleep(1)
    if lives:
        print(f"  Spread LIVE ahora: min {min(lives)}  max {max(lives)}  (muestras: {lives})")

    # 2) distribucion historica en velas M5, solo sesion
    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M5, 0, N_BARS)
    if rates is None or len(rates) == 0:
        print("  sin velas M5"); continue
    df = pd.DataFrame(rates)
    df["dt"] = pd.to_datetime(df["time"], unit="s")
    df["spread_price"] = df["spread"] * point
    sess = df[(df["dt"].dt.hour >= h0) & (df["dt"].dt.hour < h1)]
    if sess.empty:
        print("  sin velas en sesion"); continue
    s = sess["spread_price"]
    pct_block = (s > gate).mean() * 100
    print(f"  Velas M5 en sesion: {len(sess)}  ({sess['dt'].iloc[0].date()} -> {sess['dt'].iloc[-1].date()})")
    print(f"  Spread precio -> mediana {s.median():.3f}  p90 {s.quantile(0.90):.3f}  max {s.max():.3f}")
    print(f"  *** % de velas de sesion con spread > {gate} (BLOQUEADAS): {pct_block:.1f}% ***")
    if pct_block > 20:
        print(f"      -> El filtro bloquea MUCHO. Subir el limite ayudaria.")
    elif pct_block > 5:
        print(f"      -> Bloquea algo. Un limite un poco mas alto captaria mas entradas.")
    else:
        print(f"      -> El filtro casi no bloquea. El spread NO es el problema aqui.")

mt5.shutdown()
print("\nListo. El % de velas bloqueadas dice si el spread frena las entradas.")
