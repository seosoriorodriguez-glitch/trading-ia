# -*- coding: utf-8 -*-
"""
Script para descargar datos históricos de NAS100 desde MT5
"""
import sys
import io
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timezone
from pathlib import Path


def download_nas100_data():
    """Descarga datos de NAS100 en M1 y M5"""
    
    print("📡 Conectando a MT5...")
    if not mt5.initialize():
        print("❌ Error conectando a MT5")
        return False
    
    print("✅ Conectado a MT5\n")
    
    # Intentar diferentes nombres de símbolo para NAS100
    possible_symbols = [
        "NAS100.cash",
        "NAS100",
        "US100.cash",
        "US100",
        "USTEC",
        "USTEC.cash"
    ]
    
    symbol = None
    for s in possible_symbols:
        if mt5.symbol_select(s, True):
            symbol = s
            print(f"✅ Símbolo encontrado: {symbol}")
            break
    
    if symbol is None:
        print("❌ No se encontró símbolo de NAS100")
        print("Símbolos disponibles con 'NAS' o 'US':")
        symbols = mt5.symbols_get()
        for s in symbols:
            if 'NAS' in s.name or 'US100' in s.name or 'USTEC' in s.name:
                print(f"  - {s.name}")
        mt5.shutdown()
        return False
    
    # Crear carpeta data si no existe
    data_dir = Path(__file__).parent / 'data'
    data_dir.mkdir(exist_ok=True)
    
    # Descargar M5 (260 días = ~52,000 velas M5)
    print(f"\n📥 Descargando datos M5 de {symbol}...")
    print("   Período: ~260 días (últimas 75,000 velas)")
    
    rates_m5 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M5, 0, 75000)
    
    if rates_m5 is None or len(rates_m5) == 0:
        print("❌ Error descargando datos M5")
        mt5.shutdown()
        return False
    
    # Convertir a DataFrame
    df_m5 = pd.DataFrame(rates_m5)
    df_m5['time'] = pd.to_datetime(df_m5['time'], unit='s', utc=True)
    
    # Renombrar columnas para consistencia
    df_m5 = df_m5.rename(columns={'tick_volume': 'volume'})
    df_m5 = df_m5[['time', 'open', 'high', 'low', 'close', 'volume']]
    
    # Guardar M5
    output_m5 = data_dir / 'NAS100_M5_260d.csv'
    df_m5.to_csv(output_m5, index=False)
    
    print(f"✅ M5 guardado: {output_m5}")
    print(f"   Velas: {len(df_m5)}")
    print(f"   Período: {df_m5['time'].iloc[0]} → {df_m5['time'].iloc[-1]}")
    
    # Descargar M1 (30 días = ~30,000 velas M1)
    print(f"\n📥 Descargando datos M1 de {symbol}...")
    print("   Período: ~30 días (últimas 45,000 velas)")
    
    rates_m1 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, 45000)
    
    if rates_m1 is None or len(rates_m1) == 0:
        print("❌ Error descargando datos M1")
        mt5.shutdown()
        return False
    
    # Convertir a DataFrame
    df_m1 = pd.DataFrame(rates_m1)
    df_m1['time'] = pd.to_datetime(df_m1['time'], unit='s', utc=True)
    
    # Renombrar columnas
    df_m1 = df_m1.rename(columns={'tick_volume': 'volume'})
    df_m1 = df_m1[['time', 'open', 'high', 'low', 'close', 'volume']]
    
    # Guardar M1
    output_m1 = data_dir / 'NAS100_M1_30d.csv'
    df_m1.to_csv(output_m1, index=False)
    
    print(f"✅ M1 guardado: {output_m1}")
    print(f"   Velas: {len(df_m1)}")
    print(f"   Período: {df_m1['time'].iloc[0]} → {df_m1['time'].iloc[-1]}")
    
    # Información del símbolo
    symbol_info = mt5.symbol_info(symbol)
    print(f"\n📊 Información del símbolo:")
    print(f"   Nombre: {symbol_info.name}")
    print(f"   Descripción: {symbol_info.description}")
    print(f"   Punto: {symbol_info.point}")
    print(f"   Dígitos: {symbol_info.digits}")
    print(f"   Spread actual: {symbol_info.spread} puntos")
    
    mt5.shutdown()
    print("\n✅ Descarga completada")
    return True


if __name__ == '__main__':
    download_nas100_data()
