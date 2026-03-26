#!/usr/bin/env python3
"""
Descarga datos históricos de Dukascopy (broker suizo de calidad institucional)

Dukascopy proporciona datos de alta calidad para backtesting profesional.
Soporta M1, M5, M15, H1, H4, D1 con histórico extenso.

Uso:
    python3 tools/download_dukascopy_data.py \\
        --instrument US30 \\
        --timeframe M5 \\
        --start 2024-01-01 \\
        --end 2024-03-26 \\
        --output data/US30_M5_dukascopy.csv

Nota: Dukascopy usa nombres diferentes para instrumentos.
      US30 = USA30 o US30.IDX en Dukascopy
"""

import pandas as pd
import requests
from datetime import datetime, timedelta
from pathlib import Path
import argparse
import time
from typing import Optional


# Mapeo de nombres de instrumentos a formato Dukascopy
INSTRUMENT_MAPPING = {
    'US30': 'USA30.IDX/USD',
    'NAS100': 'NAS100.IDX/USD',
    'SPX500': 'SPX500.IDX/USD',
    'EURUSD': 'EURUSD',
    'GBPUSD': 'GBPUSD',
    'USDJPY': 'USDJPY',
    'GBPJPY': 'GBPJPY',
}

# Mapeo de timeframes
TIMEFRAME_MAPPING = {
    'M1': '1',
    'M5': '5',
    'M15': '15',
    'M30': '30',
    'H1': '60',
    'H4': '240',
    'D1': '1440'
}


def download_dukascopy_data(
    instrument: str,
    timeframe: str,
    start_date: datetime,
    end_date: datetime,
    output_path: str
) -> bool:
    """
    Descarga datos de Dukascopy
    
    Args:
        instrument: Nombre del instrumento (ej: 'US30')
        timeframe: Timeframe (ej: 'M5', 'M15', 'H1')
        start_date: Fecha de inicio
        end_date: Fecha de fin
        output_path: Path para guardar el CSV
        
    Returns:
        True si la descarga fue exitosa
    """
    
    # Convertir nombre de instrumento
    if instrument not in INSTRUMENT_MAPPING:
        print(f"❌ Instrumento '{instrument}' no soportado")
        print(f"   Instrumentos disponibles: {list(INSTRUMENT_MAPPING.keys())}")
        return False
    
    dukascopy_instrument = INSTRUMENT_MAPPING[instrument]
    
    # Convertir timeframe
    if timeframe not in TIMEFRAME_MAPPING:
        print(f"❌ Timeframe '{timeframe}' no soportado")
        print(f"   Timeframes disponibles: {list(TIMEFRAME_MAPPING.keys())}")
        return False
    
    dukascopy_tf = TIMEFRAME_MAPPING[timeframe]
    
    print(f"\n{'='*80}")
    print(f"DESCARGA DE DATOS DUKASCOPY")
    print(f"{'='*80}")
    print(f"Instrumento:  {instrument} ({dukascopy_instrument})")
    print(f"Timeframe:    {timeframe}")
    print(f"Período:      {start_date.strftime('%Y-%m-%d')} → {end_date.strftime('%Y-%m-%d')}")
    print(f"Días:         {(end_date - start_date).days}")
    print(f"")
    
    # NOTA: Dukascopy requiere una implementación más compleja
    # ya que no tiene una API REST simple como Yahoo Finance.
    # 
    # Opciones:
    # 1. Usar librería 'dukascopy-node' (requiere Node.js)
    # 2. Usar web scraping del sitio de Dukascopy
    # 3. Descargar manualmente desde su sitio web
    # 4. Usar API no oficial
    
    print("⚠️  IMPLEMENTACIÓN PENDIENTE")
    print("")
    print("Dukascopy no tiene una API REST pública simple.")
    print("Opciones para obtener datos:")
    print("")
    print("1. **Descarga Manual** (Recomendado para ahora):")
    print("   - Visitar: https://www.dukascopy.com/swiss/english/marketwatch/historical/")
    print(f"   - Seleccionar: {dukascopy_instrument}")
    print(f"   - Timeframe: {timeframe}")
    print(f"   - Rango: {start_date.strftime('%Y-%m-%d')} a {end_date.strftime('%Y-%m-%d')}")
    print("   - Descargar CSV")
    print(f"   - Renombrar a: {output_path}")
    print("")
    print("2. **Usar librería Python**:")
    print("   pip install dukascopy")
    print("   (Requiere implementación adicional)")
    print("")
    print("3. **Alternativa: MetaTrader 5**:")
    print("   - Una vez MT5 esté conectado, usar download_mt5_data.py")
    print("")
    
    return False


def resample_m1_to_m5(m1_file: str, output_file: str):
    """
    Resamplea datos M1 a M5
    
    Args:
        m1_file: Path al archivo M1
        output_file: Path para guardar M5
    """
    print(f"\n📊 Resampling M1 → M5...")
    
    df = pd.read_csv(m1_file)
    df['time'] = pd.to_datetime(df['time'])
    df = df.set_index('time')
    
    # Resample a 5 minutos
    df_m5 = df.resample('5T').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna()
    
    df_m5 = df_m5.reset_index()
    df_m5.to_csv(output_file, index=False)
    
    print(f"✅ {len(df_m5)} velas M5 guardadas en {output_file}")


def main():
    parser = argparse.ArgumentParser(description="Descargar datos de Dukascopy")
    parser.add_argument("--instrument", required=True, help="Instrumento (US30, NAS100, etc.)")
    parser.add_argument("--timeframe", required=True, help="Timeframe (M1, M5, M15, H1, H4, D1)")
    parser.add_argument("--start", help="Fecha inicio (YYYY-MM-DD)")
    parser.add_argument("--end", help="Fecha fin (YYYY-MM-DD)")
    parser.add_argument("--days", type=int, help="Días hacia atrás desde hoy")
    parser.add_argument("--output", required=True, help="Archivo de salida (sin extensión)")
    
    args = parser.parse_args()
    
    # Calcular fechas
    if args.days:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=args.days)
    elif args.start and args.end:
        start_date = datetime.strptime(args.start, "%Y-%m-%d")
        end_date = datetime.strptime(args.end, "%Y-%m-%d")
    else:
        print("❌ Error: Debes especificar --days O (--start Y --end)")
        return
    
    # Crear directorio de salida
    output_path = Path(args.output + ".csv")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Descargar
    success = download_dukascopy_data(
        args.instrument,
        args.timeframe,
        start_date,
        end_date,
        str(output_path)
    )
    
    if not success:
        print(f"\n{'='*80}")
        print("⚠️  DESCARGA NO COMPLETADA")
        print(f"{'='*80}")
        print("")
        print("**ALTERNATIVA TEMPORAL**: Usar Yahoo Finance para timeframes disponibles")
        print("")
        print("Para M15, H1, H4:")
        print(f"  python3 tools/download_yahoo_data.py \\")
        print(f"    --ticker \"^DJI\" \\")
        print(f"    --days {(end_date - start_date).days} \\")
        print(f"    --interval 15m \\")  # o 1h, 4h
        print(f"    --output {args.output}")
        print("")
        print("**LIMITACIÓN**: Yahoo Finance NO tiene M5")
        print("**SOLUCIÓN**: Necesitamos MT5 o descarga manual de Dukascopy")
        print("")


if __name__ == "__main__":
    main()
