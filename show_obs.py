"""
Muestra los Order Blocks activos exactamente como los ve el bot live.
Usa LiveOBMonitor con los mismos filtros: expiry, destruccion, mitigados.
Uso: python show_obs.py
"""
import sys
sys.path.insert(0, '.')

import MetaTrader5 as mt5
from datetime import datetime
from strategies.order_block.backtest.config import DEFAULT_PARAMS
from strategies.order_block.live.data_feed import LiveDataFeed
from strategies.order_block.live.ob_monitor import LiveOBMonitor

# Conectar
feed = LiveDataFeed("US30.cash")
mt5.initialize(path=r"C:\Program Files\MT5_US30\terminal64.exe")
if not feed.connect():
    print("No se pudo conectar a MT5")
    sys.exit()

# Usar exactamente el mismo monitor que el bot
monitor = LiveOBMonitor(DEFAULT_PARAMS, feed)
n = monitor.update_obs()

tick = feed.get_current_price()
current_price = tick["bid"] if tick else 0

# OBs con orden pendiente en MT5 (mismo magic que el bot)
import MetaTrader5 as mt5
pending_ob_prices = set()
orders = mt5.orders_get(symbol="US30.cash")
if orders:
    for o in orders:
        if o.magic == 345678:
            pending_ob_prices.add(round(o.price_open, 2))

feed.disconnect()

active = monitor.active_obs
bulls = [ob for ob in active if ob.ob_type == "bullish"]
bears = [ob for ob in active if ob.ob_type == "bearish"]

print(f"\n{'='*65}")
print(f"  US30.cash — OBs activos — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"  Precio actual: {current_price:.2f}")
print(f"{'='*65}")

print(f"\n  BEARISH OBs ({len(bears)}) — zonas de RESISTENCIA / SHORT")
print(f"  {'Zone Low':>10} {'Zone High':>10} {'Tamaño':>8} {'Distancia':>10} {'Confirmado'}")
print(f"  {'-'*63}")
for ob in sorted(bears, key=lambda o: o.confirmed_at, reverse=True):
    size = ob.zone_high - ob.zone_low
    dist = ob.zone_low - current_price
    has_order = round(ob.zone_low, 2) in pending_ob_prices
    arrow = "  << PRECIO DENTRO" if ob.zone_low <= current_price <= ob.zone_high else ""
    tag = "  [ORDEN PENDIENTE]" if has_order else ""
    print(f"  {ob.zone_low:>10.2f} {ob.zone_high:>10.2f} {size:>7.1f}p {dist:>+9.1f}p  {str(ob.confirmed_at)}{arrow}{tag}")

print(f"\n  BULLISH OBs ({len(bulls)}) — zonas de SOPORTE / LONG")
print(f"  {'Zone Low':>10} {'Zone High':>10} {'Tamaño':>8} {'Distancia':>10} {'Confirmado'}")
print(f"  {'-'*63}")
for ob in sorted(bulls, key=lambda o: o.confirmed_at, reverse=True):
    size = ob.zone_high - ob.zone_low
    dist = current_price - ob.zone_high
    has_order = round(ob.zone_high, 2) in pending_ob_prices
    arrow = "  << PRECIO DENTRO" if ob.zone_low <= current_price <= ob.zone_high else ""
    tag = "  [ORDEN PENDIENTE]" if has_order else ""
    print(f"  {ob.zone_low:>10.2f} {ob.zone_high:>10.2f} {size:>7.1f}p {dist:>+9.1f}p  {str(ob.confirmed_at)}{arrow}{tag}")

print(f"\n  Total: {len(active)} OBs activos ({len(bulls)} bull / {len(bears)} bear)")
print(f"{'='*65}\n")
