# -*- coding: utf-8 -*-
"""Script para cerrar todos los trades abiertos en MT5"""
import sys
import io
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import MetaTrader5 as mt5

# Conectar
if not mt5.initialize():
    print("❌ No se pudo conectar a MT5")
    exit(1)

print("✅ Conectado a MT5")

# Obtener todas las posiciones
positions = mt5.positions_get()

if positions is None or len(positions) == 0:
    print("✅ No hay trades abiertos")
    mt5.shutdown()
    exit(0)

print(f"🔍 {len(positions)} trades abiertos. Cerrando...")

# Cerrar cada posición
for pos in positions:
    # Determinar tipo de orden de cierre
    if pos.type == mt5.POSITION_TYPE_BUY:
        order_type = mt5.ORDER_TYPE_SELL
        price = mt5.symbol_info_tick(pos.symbol).bid
    else:
        order_type = mt5.ORDER_TYPE_BUY
        price = mt5.symbol_info_tick(pos.symbol).ask
    
    # Request de cierre
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": pos.symbol,
        "volume": pos.volume,
        "type": order_type,
        "position": pos.ticket,
        "price": price,
        "deviation": 20,
        "magic": pos.magic,
        "comment": "Close all",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    
    # Ejecutar
    result = mt5.order_send(request)
    
    if result.retcode == mt5.TRADE_RETCODE_DONE:
        print(f"✅ Cerrado: {pos.ticket} ({pos.type}) - PnL: ${pos.profit:.2f}")
    else:
        print(f"❌ Error cerrando {pos.ticket}: {result.retcode}")

print(f"\n✅ Proceso completado")
mt5.shutdown()
