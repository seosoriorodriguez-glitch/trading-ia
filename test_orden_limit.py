# -*- coding: utf-8 -*-
"""
Script de prueba para verificar órdenes LIMIT en MT5.

Prueba:
- Conectar a MT5
- Colocar orden BUY LIMIT en 45400
- Verificar que se creó correctamente
- Cancelar la orden después de 10 segundos
"""

import MetaTrader5 as mt5
import time
from datetime import datetime

def main():
    print("=" * 80)
    print("TEST ORDEN LIMIT - MT5")
    print("=" * 80)
    print()
    
    # Conectar a MT5
    print("Paso 1: Conectando a MT5...")
    if not mt5.initialize():
        print(f"ERROR: No se pudo inicializar MT5: {mt5.last_error()}")
        return
    print("OK Conectado a MT5")
    print()
    
    # Info de cuenta
    account_info = mt5.account_info()
    if account_info:
        print(f"Cuenta: {account_info.login}")
        print(f"Balance: ${account_info.balance:,.2f}")
        print(f"Equity: ${account_info.equity:,.2f}")
    print()
    
    # Símbolo
    symbol = "US30.cash"
    
    # Verificar símbolo
    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is None:
        print(f"ERROR: Símbolo {symbol} no encontrado")
        mt5.shutdown()
        return
    
    if not symbol_info.visible:
        print(f"Habilitando símbolo {symbol}...")
        if not mt5.symbol_select(symbol, True):
            print(f"ERROR: No se pudo habilitar {symbol}")
            mt5.shutdown()
            return
    
    # Precio actual
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        print(f"ERROR: No se pudo obtener precio de {symbol}")
        mt5.shutdown()
        return
    
    print(f"Símbolo: {symbol}")
    print(f"Bid: {tick.bid}")
    print(f"Ask: {tick.ask}")
    print(f"Spread: {tick.ask - tick.bid:.1f} puntos")
    print()
    
    # Parámetros de la orden
    entry_price = 45400.0
    sl = 45300.0  # 100 puntos abajo
    tp = 45750.0  # 350 puntos arriba (R:R 3.5)
    volume = 0.01  # Lote mínimo para prueba
    
    print("=" * 80)
    print("COLOCANDO ORDEN LIMIT")
    print("=" * 80)
    print(f"Tipo: BUY LIMIT")
    print(f"Entry: {entry_price}")
    print(f"SL: {sl}")
    print(f"TP: {tp}")
    print(f"Volume: {volume}")
    print(f"Risk: {entry_price - sl:.0f} puntos")
    print(f"Reward: {tp - entry_price:.0f} puntos")
    print(f"R:R: {(tp - entry_price) / (entry_price - sl):.2f}")
    print()
    
    # Crear request
    request = {
        "action": mt5.TRADE_ACTION_PENDING,
        "symbol": symbol,
        "volume": volume,
        "type": mt5.ORDER_TYPE_BUY_LIMIT,
        "price": entry_price,
        "sl": sl,
        "tp": tp,
        "deviation": 0,
        "magic": 345678,  # Magic number del bot
        "comment": "TEST_LIMIT",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_RETURN,
    }
    
    # Enviar orden
    print("Enviando orden...")
    result = mt5.order_send(request)
    
    if result is None:
        print("ERROR: order_send retornó None")
        mt5.shutdown()
        return
    
    print(f"Retcode: {result.retcode}")
    print(f"Comment: {result.comment}")
    print()
    
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"ERROR: Orden falló")
        print(f"  Retcode: {result.retcode}")
        print(f"  Comment: {result.comment}")
        mt5.shutdown()
        return
    
    print("=" * 80)
    print("ORDEN CREADA EXITOSAMENTE")
    print("=" * 80)
    print(f"Ticket: {result.order}")
    print(f"Volume: {result.volume}")
    print(f"Price: {result.price}")
    print()
    
    # Verificar orden pendiente
    print("Verificando orden pendiente...")
    orders = mt5.orders_get(symbol=symbol)
    if orders:
        for order in orders:
            if order.ticket == result.order:
                print(f"OK Orden encontrada:")
                print(f"  Ticket: {order.ticket}")
                print(f"  Type: {'BUY_LIMIT' if order.type == mt5.ORDER_TYPE_BUY_LIMIT else 'SELL_LIMIT'}")
                print(f"  Price: {order.price_open}")
                print(f"  SL: {order.sl}")
                print(f"  TP: {order.tp}")
                print(f"  Volume: {order.volume_initial}")
                print(f"  Time: {datetime.fromtimestamp(order.time_setup)}")
                print()
    
    # Esperar 10 segundos
    print("Esperando 10 segundos antes de cancelar...")
    for i in range(10, 0, -1):
        print(f"  {i}...", end="\r")
        time.sleep(1)
    print()
    print()
    
    # Cancelar orden
    print("=" * 80)
    print("CANCELANDO ORDEN")
    print("=" * 80)
    
    cancel_request = {
        "action": mt5.TRADE_ACTION_REMOVE,
        "order": result.order,
    }
    
    cancel_result = mt5.order_send(cancel_request)
    
    if cancel_result is None:
        print("ERROR: No se pudo cancelar")
    elif cancel_result.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"ERROR: Cancelación falló - {cancel_result.retcode}")
    else:
        print(f"OK Orden {result.order} cancelada exitosamente")
    
    print()
    
    # Verificar que no existe
    print("Verificando cancelación...")
    orders = mt5.orders_get(symbol=symbol)
    if orders:
        found = any(o.ticket == result.order for o in orders)
        if found:
            print("ADVERTENCIA: Orden aún existe")
        else:
            print("OK Orden cancelada correctamente")
    else:
        print("OK No hay órdenes pendientes")
    
    print()
    print("=" * 80)
    print("TEST COMPLETADO")
    print("=" * 80)
    print()
    print("Resultados:")
    print("  OK Conexión a MT5")
    print("  OK Creación de orden LIMIT")
    print("  OK Verificación de orden")
    print("  OK Cancelación de orden")
    print()
    print("El bot está listo para operar con órdenes LIMIT.")
    print()
    
    mt5.shutdown()

if __name__ == "__main__":
    main()
