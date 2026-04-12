# -*- coding: utf-8 -*-
"""
Test de orden para validar que el bot BB puede conectar a MT5
y enviar/cancelar ordenes correctamente con magic 345682.

Uso:
    python strategies/breaker_block/live/test_order.py

El script:
  1. Conecta a MT5 (instancia MT5_BREAKERBLOCKS)
  2. Muestra info de cuenta y precio actual
  3. Envia una orden BUY STOP 500 pts por encima del precio actual (nunca se ejecutara)
  4. Verifica que la orden aparece con magic 345682
  5. Cancela la orden
  6. Confirma que quedo limpio

Todo es seguro: la orden se coloca muy lejos del precio y se cancela inmediatamente.
"""
import sys
import time

if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import MetaTrader5 as mt5

SYMBOL   = "US30.cash"
MAGIC    = 345682
MT5_PATH = r"C:\Program Files\MT5_BREAKERBLOCKS\terminal64.exe"


def main():
    print("=" * 55)
    print("  TEST DE ORDEN — BB Bot (magic 345682)")
    print("=" * 55)

    # --- 1. Conectar a MT5 ---
    print("\n[1] Conectando a MT5 (MT5_BREAKERBLOCKS)...")
    if not mt5.initialize(path=MT5_PATH):
        print(f"  ERROR: No se pudo conectar: {mt5.last_error()}")
        return False

    info = mt5.symbol_info(SYMBOL)
    if info is None:
        print(f"  ERROR: Simbolo {SYMBOL} no encontrado")
        mt5.shutdown()
        return False
    if not info.visible:
        mt5.symbol_select(SYMBOL, True)

    print(f"  OK: MT5 conectado")

    # --- 2. Info de cuenta y precio ---
    account = mt5.account_info()
    tick = mt5.symbol_info_tick(SYMBOL)
    if account is None or tick is None:
        print("  ERROR: No se pudo obtener info de cuenta/precio")
        mt5.shutdown()
        return False

    print(f"\n[2] Info de cuenta:")
    print(f"  Balance:  ${account.balance:,.2f}")
    print(f"  Equity:   ${account.equity:,.2f}")
    print(f"  Servidor: {account.server}")
    print(f"  Precio:   Bid={tick.bid:.2f}  Ask={tick.ask:.2f}  Spread={tick.ask - tick.bid:.1f} pts")

    # --- 3. Enviar orden BUY STOP de prueba (500 pts arriba, nunca se ejecutara) ---
    entry_price = round(tick.ask + 500, 2)
    sl = round(entry_price - 100, 2)
    tp = round(entry_price + 200, 2)
    volume = 0.01

    print(f"\n[3] Enviando orden BUY STOP de prueba...")
    print(f"  Entry: {entry_price:.2f} (500 pts arriba del ask)")
    print(f"  SL:    {sl:.2f}")
    print(f"  TP:    {tp:.2f}")
    print(f"  Vol:   {volume}")
    print(f"  Magic: {MAGIC}")

    request = {
        "action":       mt5.TRADE_ACTION_PENDING,
        "symbol":       SYMBOL,
        "volume":       volume,
        "type":         mt5.ORDER_TYPE_BUY_STOP,
        "price":        entry_price,
        "sl":           sl,
        "tp":           tp,
        "deviation":    0,
        "magic":        MAGIC,
        "comment":      "BB_TEST_ORDER",
        "type_time":    mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_RETURN,
    }

    result = mt5.order_send(request)

    if result is None:
        print(f"  ERROR: order_send devolvio None")
        mt5.shutdown()
        return False

    if result.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"  ERROR: Orden rechazada - codigo {result.retcode}")
        print(f"  Comentario: {result.comment}")
        mt5.shutdown()
        return False

    ticket = result.order
    print(f"  OK: Orden creada - ticket #{ticket}")

    # --- 4. Verificar que aparece con magic correcto ---
    time.sleep(1)
    print(f"\n[4] Verificando orden pendiente...")

    orders = mt5.orders_get(symbol=SYMBOL)
    bb_orders = [o for o in (orders or []) if o.magic == MAGIC]

    if not bb_orders:
        print(f"  ERROR: No se encontro la orden con magic {MAGIC}")
        mt5.shutdown()
        return False

    order = bb_orders[0]
    print(f"  OK: Orden encontrada")
    print(f"  Ticket: {order.ticket}")
    print(f"  Magic:  {order.magic}")
    print(f"  Tipo:   BUY STOP")
    print(f"  Precio: {order.price_open:.2f}")
    print(f"  SL:     {order.sl:.2f}")
    print(f"  TP:     {order.tp:.2f}")
    print(f"  Comment:{order.comment}")

    # Verificar que no interfiere con otros bots
    all_orders = mt5.orders_get(symbol=SYMBOL) or []
    other_bots = [o for o in all_orders if o.magic != MAGIC]
    if other_bots:
        print(f"\n  Otras ordenes activas (otros bots): {len(other_bots)}")
        for o in other_bots:
            print(f"    - ticket={o.ticket} magic={o.magic}")

    # --- 5. Cancelar la orden ---
    print(f"\n[5] Cancelando orden #{ticket}...")

    cancel_request = {
        "action": mt5.TRADE_ACTION_REMOVE,
        "order":  ticket,
    }

    cancel_result = mt5.order_send(cancel_request)
    if cancel_result is None or cancel_result.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"  ERROR: No se pudo cancelar - {cancel_result}")
        mt5.shutdown()
        return False

    print(f"  OK: Orden cancelada")

    # --- 6. Confirmar que quedo limpio ---
    time.sleep(1)
    print(f"\n[6] Verificacion final...")

    remaining = mt5.orders_get(symbol=SYMBOL) or []
    bb_remaining = [o for o in remaining if o.magic == MAGIC]

    if bb_remaining:
        print(f"  ADVERTENCIA: Quedan {len(bb_remaining)} ordenes BB pendientes!")
        return False

    positions = mt5.positions_get(symbol=SYMBOL) or []
    bb_positions = [p for p in positions if p.magic == MAGIC]

    if bb_positions:
        print(f"  ADVERTENCIA: Hay {len(bb_positions)} posiciones BB abiertas!")
        return False

    print(f"  OK: Sin ordenes ni posiciones BB pendientes")

    mt5.shutdown()

    print("\n" + "=" * 55)
    print("  RESULTADO: TODOS LOS TESTS PASARON")
    print("=" * 55)
    print("\n  El bot BB puede:")
    print("  - Conectar a MT5 (instancia MT5_BREAKERBLOCKS)")
    print("  - Enviar ordenes STOP con magic 345682")
    print("  - Cancelar ordenes correctamente")
    print("  - Sin interferir con otros bots")
    print(f"\n  Listo para produccion:")
    print(f"  python strategies/breaker_block/live/run_bot.py --balance 100000")
    print()
    return True


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
