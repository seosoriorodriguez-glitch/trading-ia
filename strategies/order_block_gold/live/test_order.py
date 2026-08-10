# -*- coding: utf-8 -*-
"""
TEST de operativa del bot ORO: pone una orden STOP de prueba en XAUUSD y la cancela.
Diagnostica si el broker acepta el filling mode (sospecha: XAUUSD rechaza RETURN).
Usa magic 999888 (aparte) para NO interferir con el bot en vivo (magic 345682).

Uso (en el VPS):
    python strategies/order_block_gold/live/test_order.py --balance 200000
"""
import sys, time, argparse
from pathlib import Path
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import MetaTrader5 as mt5
from strategies.order_block_gold.live.data_feed import LiveDataFeed
from strategies.order_block_gold.live.order_executor import OrderExecutor

ap = argparse.ArgumentParser()
ap.add_argument("--symbol", default="XAUUSD")
ap.add_argument("--terminal-path", default=None)
a = ap.parse_args()
TEST_MAGIC = 999888

feed = LiveDataFeed(a.symbol, a.terminal_path)
if not feed.connect():
    print("NO conecta. Abre MT5_FVG."); sys.exit(1)
acc = feed.get_account_info()
px = feed.get_current_price()
print(f"Cuenta #{acc['login']}  Balance ${acc['balance']:,.2f}")
print(f"Precio bid={px['bid']} ask={px['ask']} SPREAD={px['spread']:.3f} (limite bot=0.6){'  <-- BLOQUEARIA' if px['spread']>0.6 else ''}")

info = mt5.symbol_info(a.symbol)
fm = info.filling_mode  # bitmask: 1=FOK, 2=IOC
print(f"filling_mode soportado (bitmask)={fm}  (1=FOK, 2=IOC, 3=ambos)")
ex = OrderExecutor(a.symbol)
print(f"_usd_per_point={ex._usd_per_point():.2f}")

# --- orden STOP de prueba: BUY STOP por encima del mercado (no se llena) ---
ask = px['ask']
entry = round(ask + 3.0, 2)
sl = round(entry - 6.0, 2)
tp = round(entry + 15.0, 2)
vol = 0.05  # test chico
print(f"\nProbando BUY STOP {vol} lotes @ {entry}  SL {sl}  TP {tp}")

modes = [("RETURN", mt5.ORDER_FILLING_RETURN), ("FOK", mt5.ORDER_FILLING_FOK), ("IOC", mt5.ORDER_FILLING_IOC)]
ok_mode = None
for name, mode in modes:
    req = {
        "action": mt5.TRADE_ACTION_PENDING, "symbol": a.symbol, "volume": vol,
        "type": mt5.ORDER_TYPE_BUY_STOP, "price": entry, "sl": sl, "tp": tp,
        "deviation": 0, "magic": TEST_MAGIC, "comment": "TEST_GOLD",
        "type_time": mt5.ORDER_TIME_GTC, "type_filling": mode,
    }
    r = mt5.order_send(req)
    rc = r.retcode if r else None
    print(f"  filling {name:7} -> retcode={rc}  {getattr(r,'comment','') if r else mt5.last_error()}")
    if r and r.retcode == mt5.TRADE_RETCODE_DONE:
        ok_mode = name
        print(f"    >>> COLOCADA OK (ticket {r.order}). Cancelando en 2s...")
        time.sleep(2)
        c = mt5.order_send({"action": mt5.TRADE_ACTION_REMOVE, "order": r.order})
        print(f"    cancelacion retcode={c.retcode if c else None}")
        break

print("\n" + "="*60)
if ok_mode == "RETURN":
    print("OPERATIVA OK: XAUUSD acepta RETURN (el que usa el bot). El no-operar es de SEÑAL/sesion, no de ejecucion.")
elif ok_mode:
    print(f"*** ENCONTRADO EL BUG: XAUUSD NO acepta RETURN, pero SI '{ok_mode}'.")
    print(f"    -> Hay que cambiar el filling del executor de oro a {ok_mode}. Avisame y lo hago.")
else:
    print("Ningun filling funciono. Revisar: mercado cerrado?, trading permitido?, stops level? (mira los retcodes arriba)")
feed.disconnect()
