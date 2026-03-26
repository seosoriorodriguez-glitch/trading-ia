#!/usr/bin/env python3
"""
Descarga datos históricos de MetaTrader 5 y los guarda como CSV.

Conexión directa a MT5 en Windows usando la librería oficial.
Sin Docker, sin HTTP, conexión nativa.

Uso:
    # Descargar M5 y M15 de US30 (60 días)
    python tools/download_mt5_data.py --symbol US30.cash --timeframes M5 M15 --days 60
    
    # Descargar todos los timeframes (730 días)
    python tools/download_mt5_data.py --symbol US30.cash --timeframes M5 M15 H1 H4 --days 730
    
    # Especificar output personalizado
    python tools/download_mt5_data.py --symbol US30.cash --timeframes M5 --days 60 --output data/custom

Requisitos:
    - Windows
    - MetaTrader 5 instalado y ejecutándose
    - pip install MetaTrader5 pandas
"""

import MetaTrader5 as mt5
import pandas as pd
import argparse
from datetime import datetime, timedelta
from pathlib import Path
import sys


# Mapeo de timeframes
TIMEFRAME_MAP = {
    'M1': mt5.TIMEFRAME_M1,
    'M5': mt5.TIMEFRAME_M5,
    'M15': mt5.TIMEFRAME_M15,
    'M30': mt5.TIMEFRAME_M30,
    'H1': mt5.TIMEFRAME_H1,
    'H4': mt5.TIMEFRAME_H4,
    'D1': mt5.TIMEFRAME_D1,
    'W1': mt5.TIMEFRAME_W1,
}

# Velas aproximadas por día para cada timeframe
CANDLES_PER_DAY = {
    'M1': 1440,
    'M5': 288,
    'M15': 96,
    'M30': 48,
    'H1': 24,
    'H4': 6,
    'D1': 1,
    'W1': 0.2,
}


def download_timeframe(symbol: str, timeframe: str, days: int, output_dir: Path) -> bool:
    """
    Descarga datos de un timeframe específico
    
    Args:
        symbol: Nombre del símbolo en MT5
        timeframe: Timeframe (M5, M15, H1, etc.)
        days: Número de días hacia atrás
        output_dir: Directorio de salida
    
    Returns:
        True si la descarga fue exitosa
    """
    if timeframe not in TIMEFRAME_MAP:
        print(f"❌ Timeframe '{timeframe}' no válido")
        print(f"   Timeframes disponibles: {list(TIMEFRAME_MAP.keys())}")
        return False
    
    tf_const = TIMEFRAME_MAP[timeframe]
    
    # Calcular número de velas a descargar
    # Añadir 20% extra para compensar fines de semana/festivos
    candles_needed = int(days * CANDLES_PER_DAY[timeframe] * 1.2)
    
    print(f"\n📥 Descargando {timeframe}...")
    print(f"   Símbolo:  {symbol}")
    print(f"   Días:     {days}")
    print(f"   Velas:    ~{candles_needed}")
    
    # Descargar velas desde la posición 0 (más reciente)
    rates = mt5.copy_rates_from_pos(symbol, tf_const, 0, candles_needed)
    
    if rates is None or len(rates) == 0:
        error = mt5.last_error()
        print(f"❌ Error descargando datos: {error}")
        print(f"   Verifica que el símbolo '{symbol}' sea correcto")
        return False
    
    # Convertir a DataFrame
    df = pd.DataFrame(rates)
    
    # Convertir timestamp a datetime
    df['time'] = pd.to_datetime(df['time'], unit='s')
    
    # Renombrar columnas
    df = df.rename(columns={
        'tick_volume': 'volume'
    })
    
    # Seleccionar columnas en orden estándar
    df = df[['time', 'open', 'high', 'low', 'close', 'volume']]
    
    # Filtrar por rango de fechas real
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    df = df[df['time'] >= start_date]
    
    # Información de los datos
    print(f"✅ {len(df)} velas descargadas")
    print(f"   Rango: {df['time'].iloc[0]} → {df['time'].iloc[-1]}")
    print(f"   Último precio: {df['close'].iloc[-1]:.2f}")
    
    # Verificar calidad de datos
    gaps = 0
    nans = df.isnull().sum().sum()
    
    if nans > 0:
        print(f"⚠️  {nans} valores NaN encontrados")
    
    # Guardar CSV
    output_file = output_dir / f"{symbol.replace('.', '_')}_{timeframe}_{days}d.csv"
    df.to_csv(output_file, index=False)
    print(f"💾 {output_file}")
    
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Descarga datos históricos de MT5",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  # Descargar M5 y M15 de US30 (60 días)
  python tools/download_mt5_data.py --symbol US30.cash --timeframes M5 M15 --days 60
  
  # Descargar todos los timeframes (2 años)
  python tools/download_mt5_data.py --symbol US30.cash --timeframes M5 M15 H1 H4 --days 730
  
  # Output personalizado
  python tools/download_mt5_data.py --symbol US30.cash --timeframes M5 --days 60 --output custom_data
        """
    )
    
    parser.add_argument('--symbol', required=True,
                       help='Símbolo en MT5 (ej: US30.cash, US30.raw)')
    parser.add_argument('--timeframes', nargs='+', required=True,
                       choices=list(TIMEFRAME_MAP.keys()),
                       help='Timeframes a descargar (M5, M15, H1, H4, etc.)')
    parser.add_argument('--days', type=int, default=60,
                       help='Días hacia atrás (default: 60)')
    parser.add_argument('--output', default='data',
                       help='Directorio de salida (default: data)')
    
    args = parser.parse_args()
    
    # Crear directorio de salida
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("="*80)
    print("  DESCARGA DE DATOS MT5")
    print("="*80)
    
    # Conectar a MT5
    print("\n📡 Conectando a MetaTrader 5...")
    if not mt5.initialize():
        error = mt5.last_error()
        print(f"❌ Error conectando a MT5: {error}")
        print(f"\n💡 SOLUCIONES:")
        print(f"   1. Verifica que MT5 esté ejecutándose")
        print(f"   2. Verifica que estés logueado en una cuenta")
        print(f"   3. Ejecuta: python tools/verify_connection.py")
        return 1
    
    account_info = mt5.account_info()
    if account_info:
        print(f"✅ Conectado — Cuenta: {account_info.login}, Broker: {account_info.company}")
    else:
        print("✅ Conectado (sin cuenta activa)")
    
    # Verificar que el símbolo existe
    symbol_info = mt5.symbol_info(args.symbol)
    if symbol_info is None:
        print(f"\n❌ Símbolo '{args.symbol}' no encontrado")
        print(f"   Ejecuta: python tools/verify_connection.py")
        print(f"   Para descubrir los nombres correctos de símbolos")
        mt5.shutdown()
        return 1
    
    print(f"\n✅ Símbolo verificado: {args.symbol}")
    print(f"   Descripción: {symbol_info.description}")
    
    # Descargar cada timeframe
    success_count = 0
    for timeframe in args.timeframes:
        if download_timeframe(args.symbol, timeframe, args.days, output_dir):
            success_count += 1
    
    # Desconectar
    mt5.shutdown()
    
    # Resumen
    print(f"\n{'='*80}")
    print(f"✅ DESCARGA COMPLETADA")
    print(f"{'='*80}")
    print(f"Timeframes descargados: {success_count}/{len(args.timeframes)}")
    print(f"Directorio: {output_dir.absolute()}")
    
    if success_count == len(args.timeframes):
        print(f"\n🚀 PRÓXIMO PASO:")
        print(f"   Ejecutar backtest de scalping:")
        print(f"   python run_scalping_backtest.py \\")
        print(f"     --data-m5 {output_dir}/{args.symbol.replace('.', '_')}_M5_{args.days}d.csv \\")
        print(f"     --data-m15 {output_dir}/{args.symbol.replace('.', '_')}_M15_{args.days}d.csv \\")
        print(f"     --instrument US30")
    
    return 0 if success_count == len(args.timeframes) else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Descarga interrumpida por el usuario")
        mt5.shutdown()
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR INESPERADO: {e}")
        import traceback
        traceback.print_exc()
        mt5.shutdown()
        sys.exit(1)
