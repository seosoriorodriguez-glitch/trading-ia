# -*- coding: utf-8 -*-
"""
TEST round-trip REAL: abre una posicion a MERCADO y la cierra enseguida.
Prueba que el simbolo abre/cierra sin problemas. Magic 999888 (aislado del bot).
Sirve para oro (XAUUSD) y DAX (GER40.cash) via --symbol.

Uso (VPS):
    python strategies/order_block_gold/live/test_market.py --symbol XAUUSD
    python strategies/order_block_gold/live/test_market.py --symbol GER40.cash
"""
import sys, time, argparse
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
import MetaTrader5 as mt5

ap = argparse.ArgumentParser()
ap.add_argument("--symbol", default="XAUUSD")
ap.add_argument("--lots", type=float, default=0.01)
ap.add_argument("--terminal-path", default=r"C:\Program Files\MT5_FVG\terminal64.exe")
a = ap.parse_args()
TEST_MAGIC = 999888

if not mt5.initialize(path=a.terminal_path):
    print(f"NO conecta: {mt5.last_error()}"); sys.exit(1)
if not mt5.symbol_select(a.symbol, True):
    print(f"No se pudo seleccionar {a.symbol}"); sys.exit(1)

info = mt5.symbol_info(a.symbol)
tick = mt5.symbol_info_tick(a.symbol)
vol = max(a.lots, info.volume_min)
print(f"{a.symbol}  bid={tick.bid} ask={tick.ask}  vol_min={info.volume_min}  probando {vol} lotes")

# --- ABRIR market BUY (probar filling IOC luego FOK) ---
opened = None
for name, mode in [("IOC", mt5.ORDER_FILLING_IOC), ("FOK", mt5.ORDER_FILLING_FOK)]:
    req = {
        "action": mt5.TRADE_ACTION_DEAL, "symbol": a.symbol, "volume": vol,
        "type": mt5.ORDER_TYPE_BUY, "price": mt5.symbol_info_tick(a.symbol).ask,
        "deviation": 20, "magic": TEST_MAGIC, "comment": "TEST_MKT",
        "type_time": mt5.ORDER_TIME_GTC, "type_filling": mode,
    }
    r = mt5.order_send(req)
    rc = r.retcode if r else None
    print(f"  ABRIR filling {name}: retcode={rc} {getattr(r,'comment','') if r else mt5.last_error()}")
    if r and r.retcode == mt5.TRADE_RETCODE_DONE:
        opened = r; print(f"    >>> ABIERTA @ {r.price} (deal {r.deal})"); break

if not opened:
    print("\nNO se pudo abrir. Mira los retcodes (10030=filling, 10018=mercado cerrado, 10019=sin dinero).")
    mt5.shutdown(); sys.exit(1)

time.sleep(2)
# --- CERRAR ---
pos = [p for p in (mt5.positions_get(symbol=a.symbol) or []) if p.magic == TEST_MAGIC]
if not pos:
    print("Posicion no encontrada para cerrar (raro)."); mt5.shutdown(); sys.exit(1)
p = pos[0]
tick = mt5.symbol_info_tick(a.symbol)
for name, mode in [("IOC", mt5.ORDER_FILLING_IOC), ("FOK", mt5.ORDER_FILLING_FOK)]:
    creq = {
        "action": mt5.TRADE_ACTION_DEAL, "symbol": a.symbol, "volume": p.volume,
        "type": mt5.ORDER_TYPE_SELL, "position": p.ticket, "price": tick.bid,
        "deviation": 20, "magic": TEST_MAGIC, "comment": "TEST_CLOSE",
        "type_time": mt5.ORDER_TIME_GTC, "type_filling": mode,
    }
    cr = mt5.order_send(creq)
    print(f"  CERRAR filling {name}: retcode={cr.retcode if cr else None}")
    if cr and cr.retcode == mt5.TRADE_RETCODE_DONE:
        print(f"    >>> CERRADA @ {cr.price} | PnL: {p.profit:.2f}"); break

print("\n" + "="*60)
print(f"ROUND-TRIP OK en {a.symbol}: abre y cierra sin problema -> la operativa esta sana.")
mt5.shutdown()
