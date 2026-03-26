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
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    
    print("=" * 60)
    print("  DESCARGA DE DATOS - YAHOO FINANCE")
    print("=" * 60)
    print(f"\nTicker: {args.ticker}")
    print(f"Días: {args.days}\n")
    
    # Descargar H1
    print("📥 Descargando datos H1 (1 hora)...")
    end_date = datetime.now()
    start_date = end_date - timedelta(days=args.days)
    
    data = yf.download(args.ticker, start=start_date, end=end_date, 
                       interval="1h", progress=False)
    
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
    
    print(f"✅ {len(data)} registros H1")
    print(f"   Rango: {data['time'].iloc[0]} → {data['time'].iloc[-1]}")
    print(f"   Precio: {data['close'].iloc[-1]:.2f}")
    
    # Guardar H1
    data['time'] = pd.to_datetime(data['time']).dt.strftime('%Y-%m-%d %H:%M:%S')
    filepath_h1 = data_dir / f"{args.output}_H1_{args.days}d.csv"
    data.to_csv(filepath_h1, index=False)
    print(f"💾 {filepath_h1}")
    
    # Generar H4
    print("\n📥 Generando H4 desde H1...")
    data['time'] = pd.to_datetime(data['time'])
    df_h4 = data.set_index('time').resample('4h').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna().reset_index()
    
    df_h4['time'] = df_h4['time'].dt.strftime('%Y-%m-%d %H:%M:%S')
    filepath_h4 = data_dir / f"{args.output}_H4_{args.days}d.csv"
    df_h4.to_csv(filepath_h4, index=False)
    
    print(f"✅ {len(df_h4)} registros H4")
    print(f"💾 {filepath_h4}")
    
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
