# -*- coding: utf-8 -*-
"""
Test Bot 2 London — verifica conexion a MT5_BTCUSD, cuenta correcta,
y coloca/cancela una orden minima de US30.cash con magic 345680.
Uso: python test_london_bot.py
"""
import MetaTrader5 as mt5

PATH   = r"C:\Program Files\MT5_BTCUSD\terminal64.exe"
SYMBOL = "US30.cash"
MAGIC  = 345680
OFFSET = 200   # BUY STOP 200 pts arriba del ask
SL_PTS = 300
TP_PTS = 600

print("=" * 55)
print("  TEST BOT 2 LONDON — US30.cash en MT5_BTCUSD")
print("=" * 55)

# Conectar
if not mt5.initialize(path=PATH):
    print(f"  ERROR: No se pudo conectar - {mt5.last_error()}")
    exit(1)

# Info cuenta
account = mt5.account_info()
print(f"  Cuenta   : {account.login}")
print(f"  Nombre   : {account.name}")
print(f"  Balance  : ${account.balance:,.2f}")
print(f"  Servidor : {account.server}")

# Verificar que US30.cash esta disponible
info = mt5.symbol_info(SYMBOL)
if info is None:
    mt5.symbol_select(SYMBOL, True)
    info = mt5.symbol_info(SYMBOL)
if info is None:
    print(f"  ERROR: {SYMBOL} no disponible en esta cuenta")
    mt5.shutdown()
    exit(1)

# Precio actual
tick = mt5.symbol_info_tick(SYMBOL)
ask   = tick.ask
entry = round(ask + OFFSET, 2)
sl    = round(entry - SL_PTS, 2)
tp    = round(entry + TP_PTS, 2)

print(f"\n  Simbolo  : {SYMBOL} | Ask: {ask:.2f}")
print(f"  Orden    : BUY STOP entry={entry:.2f} sl={sl:.2f} tp={tp:.2f}")
print(f"  Magic    : {MAGIC} (Bot 2 London)")

# Colocar orden
request = {
    "action":       mt5.TRADE_ACTION_PENDING,
    "symbol":       SYMBOL,
    "volume":       0.01,
    "type":         mt5.ORDER_TYPE_BUY_STOP,
    "price":        entry,
    "sl":           sl,
    "tp":           tp,
    "magic":        MAGIC,
    "comment":      "TEST_BOT2_LONDON",
    "type_time":    mt5.ORDER_TIME_GTC,
    "type_filling": mt5.ORDER_FILLING_RETURN,
}

result = mt5.order_send(request)

if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
    code    = result.retcode if result else "None"
    comment = result.comment if result else mt5.last_error()
    print(f"\n  ERROR al colocar orden: {code} - {comment}")
    mt5.shutdown()
    exit(1)

ticket = result.order
print(f"\n  ORDEN COLOCADA - ticket: {ticket}")

# Cancelar
cancel = mt5.order_send({
    "action": mt5.TRADE_ACTION_REMOVE,
    "order":  ticket,
})

if cancel and cancel.retcode == mt5.TRADE_RETCODE_DONE:
    print(f"  ORDEN CANCELADA - ticket: {ticket}")
    print(f"\n  RESULTADO: OK — Bot 2 London operativo en {account.name}")
else:
    print(f"  ADVERTENCIA: orden colocada pero no cancelada (cancelar manualmente ticket {ticket})")

mt5.shutdown()
print("=" * 55)
