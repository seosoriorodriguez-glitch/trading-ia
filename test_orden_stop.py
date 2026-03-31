# -*- coding: utf-8 -*-
"""
Test: Colocar una SELL STOP en 45430 y verificar que funciona.
Luego cancelarla automaticamente.
"""
import MetaTrader5 as mt5
import time

SYMBOL = "US30.cash"
PRICE = 45430.0
SL = 45480.0      # 50 pts arriba (para SHORT)
TP = 45330.0      # 100 pts abajo
VOLUME = 0.01     # Minimo para test
MAGIC = 999999    # Magic diferente al bot

def main():
    print("=" * 60)
    print("TEST: SELL STOP en US30.cash a 45430")
    print("=" * 60)
    print()

    if not mt5.initialize():
        print(f"ERROR: No se pudo inicializar MT5: {mt5.last_error()}")
        return

    tick = mt5.symbol_info_tick(SYMBOL)
    if tick is None:
        print(f"ERROR: No se pudo obtener tick de {SYMBOL}")
        mt5.shutdown()
        return

    print(f"Precio actual: Bid={tick.bid:.2f} Ask={tick.ask:.2f}")
    print(f"SELL STOP en:  {PRICE:.2f}")
    print(f"SL:            {SL:.2f}")
    print(f"TP:            {TP:.2f}")
    print()

    if tick.bid <= PRICE:
        print(f"ADVERTENCIA: Precio actual ({tick.bid:.2f}) <= SELL STOP ({PRICE:.2f})")
        print("La orden se ejecutaria inmediatamente. Abortando test.")
        mt5.shutdown()
        return

    print(f"OK: Precio actual ({tick.bid:.2f}) > SELL STOP ({PRICE:.2f})")
    print("La orden quedara pendiente hasta que el precio BAJE a 45430")
    print()

    # Colocar SELL STOP
    request = {
        "action":       mt5.TRADE_ACTION_PENDING,
        "symbol":       SYMBOL,
        "volume":       VOLUME,
        "type":         mt5.ORDER_TYPE_SELL_STOP,
        "price":        PRICE,
        "sl":           SL,
        "tp":           TP,
        "deviation":    0,
        "magic":        MAGIC,
        "comment":      "TEST_SELL_STOP",
        "type_time":    mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_RETURN,
    }

    print("Enviando SELL STOP...")
    result = mt5.order_send(request)

    if result is None:
        print(f"ERROR: order_send retorno None. Error: {mt5.last_error()}")
        mt5.shutdown()
        return

    if result.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"ERROR: Orden rechazada. Codigo: {result.retcode}")
        print(f"Comentario: {result.comment}")
        mt5.shutdown()
        return

    order_ticket = result.order
    print(f"SELL STOP colocada exitosamente!")
    print(f"  Ticket: {order_ticket}")
    print(f"  Precio: {PRICE}")
    print(f"  SL:     {SL}")
    print(f"  TP:     {TP}")
    print(f"  Vol:    {VOLUME}")
    print()

    # Verificar que aparece en ordenes pendientes
    orders = mt5.orders_get(symbol=SYMBOL)
    found = False
    if orders:
        for o in orders:
            if o.ticket == order_ticket:
                found = True
                print(f"Verificacion: Orden {order_ticket} encontrada en pendientes")
                print(f"  Tipo: {'SELL_STOP' if o.type == mt5.ORDER_TYPE_SELL_STOP else 'OTRO'}")
                print(f"  Precio: {o.price_open}")
                break

    if not found:
        print(f"ADVERTENCIA: Orden {order_ticket} NO encontrada en pendientes")
        print("Puede haberse ejecutado inmediatamente (precio ya estaba debajo)")

    # Esperar 3 segundos y cancelar
    print()
    print("Esperando 3 segundos antes de cancelar...")
    time.sleep(3)

    cancel_request = {
        "action": mt5.TRADE_ACTION_REMOVE,
        "order":  order_ticket,
    }

    print(f"Cancelando orden {order_ticket}...")
    cancel_result = mt5.order_send(cancel_request)

    if cancel_result and cancel_result.retcode == mt5.TRADE_RETCODE_DONE:
        print(f"Orden {order_ticket} cancelada exitosamente!")
    else:
        code = cancel_result.retcode if cancel_result else "None"
        print(f"ERROR al cancelar: {code}")

    print()
    print("=" * 60)
    print("TEST COMPLETADO")
    print("=" * 60)

    mt5.shutdown()

if __name__ == "__main__":
    main()
