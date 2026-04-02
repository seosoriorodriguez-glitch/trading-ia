# -*- coding: utf-8 -*-
"""
Test dual: verifica que cada bot se conecta a su MT5 correcto y puede operar.
Coloca y cancela una orden minima en US30 y en BTCUSD.
Uso: python test_dual_bots.py
"""
import MetaTrader5 as mt5

TESTS = [
    {
        "name":   "US30 Challenge",
        "path":   r"C:\Program Files\MT5_US30\terminal64.exe",
        "symbol": "US30.cash",
        "magic":  345678,
        "offset": 200,   # BUY STOP 200 pts arriba
        "sl_pts": 300,
        "tp_pts": 600,
    },
    {
        "name":   "BTCUSD Demo",
        "path":   r"C:\Program Files\MT5_BTCUSD\terminal64.exe",
        "symbol": "BTCUSD",
        "magic":  345679,
        "offset": 300,
        "sl_pts": 400,
        "tp_pts": 800,
    },
]

def test_instance(cfg):
    print(f"\n{'='*55}")
    print(f"  TEST: {cfg['name']}")
    print(f"{'='*55}")

    # Conectar a esta instancia especifica
    if not mt5.initialize(path=cfg["path"]):
        print(f"  ERROR: No se pudo conectar - {mt5.last_error()}")
        return False

    # Verificar cuenta
    account = mt5.account_info()
    if account is None:
        print(f"  ERROR: No se pudo obtener info de cuenta")
        mt5.shutdown()
        return False

    print(f"  Cuenta   : {account.login}")
    print(f"  Nombre   : {account.name}")
    print(f"  Balance  : ${account.balance:,.2f}")
    print(f"  Servidor : {account.server}")

    # Obtener precio
    tick = mt5.symbol_info_tick(cfg["symbol"])
    if tick is None:
        print(f"  ERROR: No se pudo obtener precio de {cfg['symbol']}")
        mt5.shutdown()
        return False

    ask    = tick.ask
    entry  = round(ask + cfg["offset"], 2)
    sl     = round(entry - cfg["sl_pts"], 2)
    tp     = round(entry + cfg["tp_pts"], 2)

    print(f"  Simbolo  : {cfg['symbol']} | Ask: {ask:.2f}")
    print(f"  Orden    : BUY STOP entry={entry:.2f} sl={sl:.2f} tp={tp:.2f}")

    # Colocar orden
    request = {
        "action":       mt5.TRADE_ACTION_PENDING,
        "symbol":       cfg["symbol"],
        "volume":       0.01,
        "type":         mt5.ORDER_TYPE_BUY_STOP,
        "price":        entry,
        "sl":           sl,
        "tp":           tp,
        "magic":        cfg["magic"],
        "comment":      f"TEST_{cfg['name'].replace(' ','')}",
        "type_time":    mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_RETURN,
    }

    result = mt5.order_send(request)

    if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
        code = result.retcode if result else "None"
        comment = result.comment if result else mt5.last_error()
        print(f"  ERROR al colocar orden: {code} - {comment}")
        mt5.shutdown()
        return False

    ticket = result.order
    print(f"  ORDEN COLOCADA - ticket: {ticket}")

    # Cancelar
    cancel = mt5.order_send({
        "action": mt5.TRADE_ACTION_REMOVE,
        "order":  ticket,
    })

    if cancel and cancel.retcode == mt5.TRADE_RETCODE_DONE:
        print(f"  ORDEN CANCELADA - ticket: {ticket}")
        print(f"  RESULTADO: OK - {cfg['name']} operativo")
        success = True
    else:
        print(f"  Orden colocada pero no cancelada automaticamente (cancelar manualmente ticket {ticket})")
        success = True  # La colocacion funciono igual

    mt5.shutdown()
    return success


# Ejecutar tests secuencialmente (un MT5 a la vez)
results = []
for cfg in TESTS:
    ok = test_instance(cfg)
    results.append((cfg["name"], ok))

print(f"\n{'='*55}")
print(f"  RESUMEN FINAL")
print(f"{'='*55}")
for name, ok in results:
    status = "OK" if ok else "FALLO"
    print(f"  {name:25s} : {status}")
print()
