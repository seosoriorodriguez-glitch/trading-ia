"""
Descarga datos históricos de Yahoo Finance para backtesting.

Uso:
    python download_yahoo_data.py --ticker ^DJI --days 730 --output US30
"""

import argparse
from pathlib import Path
from datetime import datetime, timedelta
import yfinance as yf
import pandas as pd


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", required=True)
    parser.add_argument("--days", type=int, default=730)
    parser.add_argument("--interval", default="1h", 
                       help="Interval: 1m,2m,5m,15m,30m,60m,90m,1h,1d,5d,1wk,1mo,3mo")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    
    # Crear directorio del output si es necesario
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Mapeo de intervalos a nombres legibles
    interval_names = {
        '1m': 'M1', '2m': 'M2', '5m': 'M5', '15m': 'M15', '30m': 'M30',
        '60m': 'H1', '90m': 'H1.5', '1h': 'H1', '1d': 'D1', '5d': 'W1',
        '1wk': 'W1', '1mo': 'MN1', '3mo': 'Q1'
    }
    
    interval_name = interval_names.get(args.interval, args.interval)
    
    print("=" * 60)
    print("  DESCARGA DE DATOS - YAHOO FINANCE")
    print("=" * 60)
    print(f"\nTicker: {args.ticker}")
    print(f"Intervalo: {interval_name} ({args.interval})")
    print(f"Días: {args.days}\n")
    
    # Descargar datos
    print(f"📥 Descargando datos {interval_name}...")
    end_date = datetime.now()
    start_date = end_date - timedelta(days=args.days)
    
    data = yf.download(args.ticker, start=start_date, end=end_date, 
                       interval=args.interval, progress=False)
    
    if data.empty:
        print("❌ No se obtuvieron datos")
        return
    
    # Aplanar columnas multi-índice si existen
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = [col[0] if isinstance(col, tuple) else col for col in data.columns]
    
    # Reset index
    data = data.reset_index()
    
    # Renombrar columnas
    data.columns = [c.lower() if isinstance(c, str) else str(c).lower() for c in data.columns]
    
    # Mapear nombres
    if 'datetime' in data.columns:
        data = data.rename(columns={'datetime': 'time'})
    elif 'date' in data.columns:
        data = data.rename(columns={'date': 'time'})
    
    # Seleccionar columnas
    cols = ['time', 'open', 'high', 'low', 'close', 'volume']
    data = data[cols]
    
    # Limpiar datos
    for col in ['open', 'high', 'low', 'close', 'volume']:
        data[col] = pd.to_numeric(data[col], errors='coerce')
    data = data.dropna()
    
    print(f"✅ {len(data)} registros {interval_name}")
    print(f"   Rango: {data['time'].iloc[0]} → {data['time'].iloc[-1]}")
    print(f"   Precio: {data['close'].iloc[-1]:.2f}")
    
    # Guardar datos
    data['time'] = pd.to_datetime(data['time']).dt.strftime('%Y-%m-%d %H:%M:%S')
    filepath = f"{args.output}_{interval_name}_{args.days}d.csv"
    data.to_csv(filepath, index=False)
    print(f"💾 {filepath}")
    
    print("\n" + "=" * 60)
    print("✅ COMPLETADO")
    print("=" * 60)
    print(f"\n🚀 Ejecutar backtest:")
    print(f"python run_backtest.py \\")
    print(f"  --data-h1 data/{args.output}_H1_{args.days}d.csv \\")
    print(f"  --data-h4 data/{args.output}_H4_{args.days}d.csv \\")
    print(f"  --instrument US30 \\")
    print(f"  --output data/backtest_{args.output}.csv")


if __name__ == "__main__":
    main()
