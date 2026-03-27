# -*- coding: utf-8 -*-
"""
Test de Trade Manual - Compra y Venta Rápida
"""
import sys
import io
import time
import MetaTrader5 as mt5
from datetime import datetime, timezone

# Fix encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def test_trade():
    print("=" * 60)
    print("🧪 TEST DE TRADE MANUAL")
    print("=" * 60)
    print()
    
    # Conectar a MT5
    if not mt5.initialize():
        print(f"❌ Error inicializando MT5: {mt5.last_error()}")
        return
    
    print("✅ Conectado a MT5")
    
    # Verificar cuenta
    account = mt5.account_info()
    if account is None:
        print("❌ Error obteniendo info de cuenta")
        mt5.shutdown()
        return
    
    print(f"✅ Cuenta: {account.login}")
    print(f"💰 Balance: ${account.balance:,.2f}")
    print(f"💵 Equity: ${account.equity:,.2f}")
    print()
    
    # Símbolo
    symbol = "US30.cash"
    
    # Verificar símbolo
    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is None:
        print(f"❌ Símbolo {symbol} no encontrado")
        mt5.shutdown()
        return
    
    if not symbol_info.visible:
        if not mt5.symbol_select(symbol, True):
            print(f"❌ Error seleccionando símbolo {symbol}")
            mt5.shutdown()
            return
    
    print(f"✅ Símbolo: {symbol}")
    
    # Obtener precio actual
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        print("❌ Error obteniendo precio")
        mt5.shutdown()
        return
    
    print(f"📊 Precio actual:")
    print(f"   Bid: {tick.bid:.2f}")
    print(f"   Ask: {tick.ask:.2f}")
    print(f"   Spread: {tick.ask - tick.bid:.2f} pts")
    print()
    
    # Parámetros del trade
    volume = 0.01  # Volumen mínimo para test
    entry_price = tick.ask
    sl = entry_price - 50  # SL a 50 puntos
    tp = entry_price + 30  # TP a 30 puntos (cerraremos antes manualmente)
    
    print("🔹 Parámetros del trade de prueba:")
    print(f"   Tipo: COMPRA (LONG)")
    print(f"   Volumen: {volume}")
    print(f"   Entry: {entry_price:.2f}")
    print(f"   SL: {sl:.2f} (-50 pts)")
    print(f"   TP: {tp:.2f} (+30 pts)")
    print()
    
    # Confirmar
    input("⚠️  Presiona ENTER para ejecutar el trade de prueba...")
    print()
    
    # Preparar orden de COMPRA
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": volume,
        "type": mt5.ORDER_TYPE_BUY,
        "price": tick.ask,
        "sl": sl,
        "tp": tp,
        "deviation": 10,
        "magic": 999999,  # Magic number diferente para test
        "comment": "TEST_MANUAL",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    
    print("📤 Enviando orden de COMPRA...")
    result = mt5.order_send(request)
    
    if result is None:
        print("❌ Error: order_send retornó None")
        mt5.shutdown()
        return
    
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"❌ Error en orden: {result.retcode}")
        print(f"   Comentario: {result.comment}")
        mt5.shutdown()
        return
    
    print("✅ TRADE ABIERTO!")
    print(f"   Ticket: {result.order}")
    print(f"   Precio: {result.price:.2f}")
    print(f"   Volumen: {result.volume}")
    print()
    
    ticket = result.order
    
    # Esperar 3 segundos
    print("⏳ Esperando 3 segundos...")
    time.sleep(3)
    print()
    
    # Obtener posición
    position = mt5.positions_get(ticket=ticket)
    
    if position is None or len(position) == 0:
        print("⚠️  Posición ya cerrada o no encontrada")
        mt5.shutdown()
        return
    
    position = position[0]
    
    print("📊 Estado de la posición:")
    print(f"   Ticket: {position.ticket}")
    print(f"   Precio actual: {position.price_current:.2f}")
    print(f"   Profit: ${position.profit:.2f}")
    print()
    
    # Confirmar cierre
    input("⚠️  Presiona ENTER para CERRAR el trade...")
    print()
    
    # Cerrar posición
    close_request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": position.volume,
        "type": mt5.ORDER_TYPE_SELL,  # Cerrar LONG con SELL
        "position": ticket,
        "price": mt5.symbol_info_tick(symbol).bid,
        "deviation": 10,
        "magic": 999999,
        "comment": "CLOSE_TEST",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    
    print("📤 Cerrando posición...")
    close_result = mt5.order_send(close_request)
    
    if close_result is None:
        print("❌ Error: order_send retornó None")
        mt5.shutdown()
        return
    
    if close_result.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"❌ Error cerrando: {close_result.retcode}")
        print(f"   Comentario: {close_result.comment}")
        mt5.shutdown()
        return
    
    print("✅ TRADE CERRADO!")
    print(f"   Precio de cierre: {close_result.price:.2f}")
    print()
    
    # Esperar para que se procese
    time.sleep(2)
    
    # Obtener resultado final del historial
    from_date = datetime(2026, 3, 27)
    deals = mt5.history_deals_get(from_date, datetime.now())
    
    if deals:
        # Buscar nuestro trade
        test_deals = [d for d in deals if d.magic == 999999]
        
        if len(test_deals) >= 2:
            entry_deal = test_deals[-2]
            exit_deal = test_deals[-1]
            
            pnl = exit_deal.profit
            
            print("=" * 60)
            print("📊 RESULTADO DEL TEST")
            print("=" * 60)
            print(f"Entry: {entry_deal.price:.2f}")
            print(f"Exit: {exit_deal.price:.2f}")
            print(f"PnL: ${pnl:.2f}")
            print()
            
            if pnl > 0:
                print("✅ Trade de prueba exitoso - Sistema funcionando correctamente!")
            elif pnl < 0:
                print("✅ Trade de prueba completado - Sistema funcionando correctamente!")
            else:
                print("✅ Trade de prueba completado - Sistema funcionando correctamente!")
    
    print()
    print("✅ Test completado - El bot puede ejecutar trades correctamente")
    
    mt5.shutdown()

if __name__ == '__main__':
    test_trade()
