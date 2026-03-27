#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verifica conexión a MetaTrader 5 en Windows y descubre nombres de símbolos.

Este script:
1. Conecta a MT5 local
2. Muestra info de cuenta
3. Busca variantes de símbolos (US30, NAS100, etc.)
4. Muestra características de cada símbolo
5. Descarga velas de prueba de cada timeframe

Uso:
    python tools/verify_connection.py
    
Requisitos:
    - Windows
    - MetaTrader 5 instalado y ejecutándose
    - Cuenta demo o real logueada en MT5
"""

import MetaTrader5 as mt5
from datetime import datetime
import sys
import os

# Configurar encoding para Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')


def print_section(title):
    """Imprime sección con formato"""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")


def verify_connection():
    """Verifica conexión y muestra información completa"""
    
    print_section("VERIFICACIÓN DE CONEXIÓN MT5")
    
    # 1. Inicializar MT5
    print("📡 Intentando conectar a MetaTrader 5...")
    if not mt5.initialize():
        error = mt5.last_error()
        print(f"\n❌ ERROR: No se pudo conectar a MT5")
        print(f"   Código: {error[0]}")
        print(f"   Mensaje: {error[1]}")
        print(f"\n💡 SOLUCIONES:")
        print(f"   1. Verifica que MetaTrader 5 esté instalado")
        print(f"   2. Abre MetaTrader 5 y loguéate con una cuenta")
        print(f"   3. Verifica que 'Algo Trading' esté habilitado:")
        print(f"      Tools → Options → Expert Advisors → Allow automated trading")
        return False
    
    print("✅ Conectado a MetaTrader 5\n")
    
    # 2. Info de cuenta
    print_section("INFORMACIÓN DE CUENTA")
    
    account_info = mt5.account_info()
    if account_info:
        print(f"Cuenta:        {account_info.login}")
        print(f"Broker:        {account_info.company}")
        print(f"Servidor:      {account_info.server}")
        print(f"Balance:       ${account_info.balance:,.2f}")
        print(f"Equity:        ${account_info.equity:,.2f}")
        print(f"Margen:        ${account_info.margin:,.2f}")
        print(f"Margen Libre:  ${account_info.margin_free:,.2f}")
        print(f"Leverage:      1:{account_info.leverage}")
        print(f"Profit:        ${account_info.profit:,.2f}")
    else:
        print("⚠️  No se pudo obtener información de cuenta")
    
    # 3. Buscar símbolos
    print_section("BÚSQUEDA DE SÍMBOLOS")
    
    # Símbolos a buscar con variantes
    symbols_to_find = {
        'US30': ['US30', 'US30.cash', 'US30.raw', 'US30Cash', 'US30_raw', 'DJI30', 'USA30', 'DOWJONES'],
        'NAS100': ['NAS100', 'NAS100.cash', 'NAS100.raw', 'NAS100Cash', 'NASDAQ', 'US100'],
        'SPX500': ['SPX500', 'SPX500.cash', 'SPX500.raw', 'SP500', 'US500', 'S&P500'],
        'EURUSD': ['EURUSD', 'EURUSD.raw', 'EURUSDm'],
        'GBPUSD': ['GBPUSD', 'GBPUSD.raw', 'GBPUSDm'],
        'GBPJPY': ['GBPJPY', 'GBPJPY.raw', 'GBPJPYm'],
    }
    
    found_symbols = {}
    
    for instrument, variants in symbols_to_find.items():
        print(f"\n🔍 Buscando {instrument}...")
        found = False
        
        for variant in variants:
            symbol_info = mt5.symbol_info(variant)
            if symbol_info is not None:
                print(f"   ✅ Encontrado: {variant}")
                found_symbols[instrument] = variant
                
                # Mostrar info del símbolo
                print(f"      Descripción:    {symbol_info.description}")
                print(f"      Point:          {symbol_info.point}")
                print(f"      Digits:         {symbol_info.digits}")
                print(f"      Spread:         {symbol_info.spread} puntos")
                print(f"      Contract Size:  {symbol_info.trade_contract_size}")
                print(f"      Volume Min:     {symbol_info.volume_min}")
                print(f"      Volume Max:     {symbol_info.volume_max}")
                
                # Obtener precio actual
                tick = mt5.symbol_info_tick(variant)
                if tick:
                    print(f"      Bid:            {tick.bid}")
                    print(f"      Ask:            {tick.ask}")
                    print(f"      Spread Real:    {tick.ask - tick.bid:.5f}")
                
                found = True
                break
        
        if not found:
            print(f"   ❌ No encontrado (probadas: {', '.join(variants)})")
    
    # 4. Probar descarga de velas
    if found_symbols:
        print_section("PRUEBA DE DESCARGA DE VELAS")
        
        # Usar el primer símbolo encontrado
        test_symbol = list(found_symbols.values())[0]
        test_instrument = list(found_symbols.keys())[0]
        
        print(f"Probando con: {test_instrument} ({test_symbol})\n")
        
        timeframes = {
            'M5': mt5.TIMEFRAME_M5,
            'M15': mt5.TIMEFRAME_M15,
            'H1': mt5.TIMEFRAME_H1,
            'H4': mt5.TIMEFRAME_H4,
        }
        
        for tf_name, tf_const in timeframes.items():
            rates = mt5.copy_rates_from_pos(test_symbol, tf_const, 0, 10)
            
            if rates is not None and len(rates) > 0:
                last_candle = rates[-1]
                last_time = datetime.utcfromtimestamp(last_candle['time'])
                print(f"✅ {tf_name:4s}: {len(rates)} velas | Última: {last_time} | "
                      f"Close: {last_candle['close']:.2f}")
            else:
                print(f"❌ {tf_name:4s}: No se pudieron obtener velas")
    
    # 5. Resumen para configuración
    if found_symbols:
        print_section("RESUMEN PARA CONFIGURACIÓN")
        
        print("Copia estos nombres de símbolos a tu configuración:\n")
        print("```yaml")
        print("instruments:")
        for instrument, symbol in found_symbols.items():
            print(f"  {instrument}:")
            print(f"    symbol_mt5: \"{symbol}\"")
        print("```")
        
        print(f"\n💡 PRÓXIMO PASO:")
        print(f"   Descargar datos históricos:")
        print(f"   python tools/download_mt5_data.py --symbol {list(found_symbols.values())[0]} --timeframes M5 M15 --days 60")
    
    # 6. Desconectar
    mt5.shutdown()
    print(f"\n✅ Desconectado de MT5")
    
    return True


if __name__ == "__main__":
    try:
        success = verify_connection()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ ERROR INESPERADO: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
