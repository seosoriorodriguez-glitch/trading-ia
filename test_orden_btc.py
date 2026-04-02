# -*- coding: utf-8 -*-
"""
Test de orden BTC: coloca una BUY STOP minima y la cancela inmediatamente.
Solo para verificar que el bot puede enviar ordenes a MT5.
Uso: python test_orden_btc.py
"""
import sys
import MetaTrader5 as mt5

SYMBOL = "BTCUSD"
MAGIC  = 345679  # Magic del bot BTC

def main():
    # Conectar
    if not mt5.initialize():
        print(f"ERROR: No se pudo inicializar MT5: {mt5.last_error()}")
        return

    print(f"MT5 conectado")

    # Info del simbolo
    info = mt5.symbol_info(SYMBOL)
    if info is None:
        print(f"ERROR: simbolo {SYMBOL} no encontrado")
        mt5.shutdown()
        return

    tick = mt5.symbol_info_tick(SYMBOL)
    if tick is None:
        print(f"ERROR: no se pudo obtener precio de {SYMBOL}")
        mt5.shutdown()
        return

    ask    = tick.ask
    bid    = tick.bid
    spread = ask - bid
    print(f"Precio actual: bid={bid:.2f}  ask={ask:.2f}  spread={spread:.2f} pts")

    # Colocar BUY STOP 200 puntos arriba del ask (no se va a ejecutar)
    entry = round(ask + 200, 2)
    sl    = round(entry - 300, 2)
    tp    = round(entry + 600, 2)  # RR 2.0

    request = {
        "action":       mt5.TRADE_ACTION_PENDING,
        "symbol":       SYMBOL,
        "volume":       0.01,            # minimo posible
        "type":         mt5.ORDER_TYPE_BUY_STOP,
        "price":        entry,
        "sl":           sl,
        "tp":           tp,
        "deviation":    0,
        "magic":        MAGIC,
        "comment":      "TEST_OB_BTC",
        "type_time":    mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_RETURN,
    }

    print(f"\nEnviando BUY STOP de prueba:")
    print(f"  Entry : {entry:.2f}")
    print(f"  SL    : {sl:.2f}")
    print(f"  TP    : {tp:.2f}")
    print(f"  Volume: 0.01 lotes")

    result = mt5.order_send(request)

    if result is None:
        print(f"\nERROR: order_send retorno None")
        print(f"Ultimo error MT5: {mt5.last_error()}")
        mt5.shutdown()
        return

    if result.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"\nERROR al colocar orden:")
        print(f"  retcode : {result.retcode}")
        print(f"  comment : {result.comment}")
        mt5.shutdown()
        return

    ticket = result.order
    print(f"\nORDEN COLOCADA - ticket: {ticket}")

    # Cancelar inmediatamente
    cancel = mt5.order_send({
        "action": mt5.TRADE_ACTION_REMOVE,
        "order":  ticket,
    })

    if cancel and cancel.retcode == mt5.TRADE_RETCODE_DONE:
        print(f"Orden {ticket} CANCELADA correctamente")
        print(f"\nTODO OK - el bot puede colocar y cancelar ordenes en {SYMBOL}")
    else:
        print(f"Orden colocada pero no se pudo cancelar automaticamente")
        print(f"Cancelala manualmente en MT5 (ticket {ticket})")

    mt5.shutdown()

if __name__ == "__main__":
    main()
