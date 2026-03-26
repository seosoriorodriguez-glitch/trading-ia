"""
Preparación de datos para backtesting.

Soporta múltiples fuentes de datos:
  1. TradingView CSV export
  2. MetaTrader 5 (via Docker o Windows)
  3. Yahoo Finance (yfinance — proxy para índices)
  4. CSV genérico con columnas OHLCV

Uso:
  # Desde TradingView
  python prepare_data.py --source tradingview --file data/US30_tv_export.csv --instrument US30

  # Desde Yahoo Finance (gratis, no requiere broker)
  python prepare_data.py --source yahoo --instrument US30 --days 730

  # Desde MT5
  python prepare_data.py --source mt5 --instrument US30 --days 730

  # Verificar datos existentes
  python prepare_data.py --verify --file data/US30_H4.csv
"""

import sys
import argparse
import logging
from pathlib import Path
from datetime import datetime, timedelta

import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("data_prep")


# ============================================================
# Mapeo de instrumentos a símbolos por fuente
# ============================================================
YAHOO_SYMBOLS = {
    "US30": "^DJI",        # Dow Jones
    "NAS100": "^IXIC",     # Nasdaq Composite (proxy — ^NDX para Nasdaq 100)
    "SPX500": "^GSPC",     # S&P 500
}

MT5_SYMBOLS = {
    "US30": "US30.raw",     # VERIFICAR con tu broker
    "NAS100": "NAS100.raw",
    "SPX500": "SPX500.raw",
}


# ============================================================
# Fuente: TradingView
# ============================================================
def load_tradingview_csv(filepath: str) -> pd.DataFrame:
    """
    Carga CSV exportado desde TradingView.

    TradingView exporta con columnas:
    time, open, high, low, close, Volume (o variantes)
    El formato de time puede variar.
    """
    df = pd.read_csv(filepath)

    # Normalizar nombres de columnas
    df.columns = df.columns.str.strip().str.lower()

    # Renombrar variantes comunes
    rename_map = {}
    for col in df.columns:
        if "time" in col or "date" in col or "fecha" in col:
            rename_map[col] = "time"
        elif col == "vol" or col == "volume" or col == "tick_volume":
            rename_map[col] = "volume"

    df = df.rename(columns=rename_map)

    # Asegurar que time sea datetime
    if "time" in df.columns:
        df["time"] = pd.to_datetime(df["time"])
    else:
        raise ValueError("No se encontró columna de tiempo. "
                        f"Columnas disponibles: {list(df.columns)}")

    # Verificar columnas OHLC
    required = ["time", "open", "high", "low", "close"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Columnas faltantes: {missing}. "
                        f"Disponibles: {list(df.columns)}")

    # Agregar volume si no existe
    if "volume" not in df.columns:
        df["volume"] = 0

    df = df.sort_values("time").reset_index(drop=True)

    # Eliminar duplicados
    df = df.drop_duplicates(subset=["time"], keep="last")

    logger.info(f"TradingView: {len(df)} velas cargadas "
                f"({df['time'].min()} → {df['time'].max()})")

    return df[["time", "open", "high", "low", "close", "volume"]]


# ============================================================
# Fuente: Yahoo Finance
# ============================================================
def load_yahoo_finance(instrument: str, days: int, interval: str = "1h") -> pd.DataFrame:
    """
    Descarga datos de Yahoo Finance.

    Limitaciones:
    - H1 (1h): máximo ~730 días
    - H4: no existe nativo, se resamplea desde H1
    - Los datos son del índice real, no del CFD del broker
      (pueden haber pequeñas diferencias en precio)
    """
    try:
        import yfinance as yf
    except ImportError:
        logger.error("yfinance no instalado. Ejecutar: pip install yfinance")
        sys.exit(1)

    symbol = YAHOO_SYMBOLS.get(instrument)
    if not symbol:
        raise ValueError(f"Instrumento no soportado en Yahoo: {instrument}. "
                        f"Disponibles: {list(YAHOO_SYMBOLS.keys())}")

    logger.info(f"Descargando {symbol} ({instrument}) de Yahoo Finance...")

    # Yahoo limita H1 a 730 días
    end = datetime.now()
    start = end - timedelta(days=min(days, 729))

    ticker = yf.Ticker(symbol)
    df = ticker.history(start=start, end=end, interval=interval)

    if df.empty:
        raise ValueError(f"No se obtuvieron datos para {symbol}")

    df = df.reset_index()
    df.columns = df.columns.str.strip().str.lower()

    # Renombrar
    if "datetime" in df.columns:
        df = df.rename(columns={"datetime": "time"})
    elif "date" in df.columns:
        df = df.rename(columns={"date": "time"})

    df["time"] = pd.to_datetime(df["time"]).dt.tz_localize(None)

    df = df[["time", "open", "high", "low", "close", "volume"]]
    df = df.sort_values("time").reset_index(drop=True)

    logger.info(f"Yahoo Finance: {len(df)} velas {interval} "
                f"({df['time'].min()} → {df['time'].max()})")

    return df


def resample_to_h4(df_h1: pd.DataFrame) -> pd.DataFrame:
    """Resamplea datos H1 a H4."""
    df = df_h1.copy()
    df = df.set_index("time")

    df_h4 = df.resample("4h").agg({
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum",
    }).dropna()

    df_h4 = df_h4.reset_index()
    logger.info(f"Resampleado a H4: {len(df_h4)} velas")
    return df_h4


def resample_to_timeframe(df_h1: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    """Resamplea datos H1 a cualquier timeframe superior."""
    tf_map = {
        "H1": "1h",
        "H2": "2h",
        "H4": "4h",
        "D1": "1D",
        "W1": "1W",
    }
    if timeframe not in tf_map:
        raise ValueError(f"Timeframe no soportado: {timeframe}")

    if timeframe == "H1":
        return df_h1.copy()

    df = df_h1.copy()
    df = df.set_index("time")

    df_resampled = df.resample(tf_map[timeframe]).agg({
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum",
    }).dropna()

    df_resampled = df_resampled.reset_index()
    logger.info(f"Resampleado a {timeframe}: {len(df_resampled)} velas")
    return df_resampled


# ============================================================
# Fuente: MetaTrader 5
# ============================================================
def load_from_mt5(instrument: str, timeframe: str, days: int) -> pd.DataFrame:
    """Carga datos desde MT5 (Docker o Windows)."""
    from core.market_data import MT5Connection
    from core.config_loader import get_config

    config = get_config()
    mt5_config = config.strategy.get("mt5", {})

    mt5 = MT5Connection(
        host=mt5_config.get("host", "localhost"),
        port=mt5_config.get("port", 8001),
    )

    if not mt5.connect():
        raise ConnectionError("No se pudo conectar a MT5")

    symbol = MT5_SYMBOLS.get(instrument, instrument)
    candles_per_day = {"H1": 24, "H4": 6, "D1": 1}.get(timeframe, 24)
    count = days * candles_per_day

    candles = mt5.get_candles(symbol, timeframe, count)
    mt5.disconnect()

    if not candles:
        raise ValueError(f"No se obtuvieron datos de MT5 para {symbol}")

    df = pd.DataFrame([{
        "time": c.time,
        "open": c.open,
        "high": c.high,
        "low": c.low,
        "close": c.close,
        "volume": c.volume,
    } for c in candles])

    logger.info(f"MT5: {len(df)} velas {timeframe} de {symbol}")
    return df


# ============================================================
# Verificación de datos
# ============================================================
def verify_data(filepath: str):
    """Verifica que un archivo CSV tenga el formato correcto."""
    df = pd.read_csv(filepath)
    df.columns = df.columns.str.strip().str.lower()

    print(f"\n{'='*50}")
    print(f"VERIFICACIÓN: {filepath}")
    print(f"{'='*50}")
    print(f"Filas:        {len(df)}")
    print(f"Columnas:     {list(df.columns)}")
    print(f"Primeras 3:")
    print(df.head(3).to_string(index=False))
    print(f"\nÚltimas 3:")
    print(df.tail(3).to_string(index=False))

    # Verificar columnas requeridas
    required = ["time", "open", "high", "low", "close"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        print(f"\n❌ COLUMNAS FALTANTES: {missing}")
    else:
        print(f"\n✅ Todas las columnas requeridas presentes")

    # Verificar datos
    df["time"] = pd.to_datetime(df["time"])
    print(f"\nRango: {df['time'].min()} → {df['time'].max()}")

    days = (df["time"].max() - df["time"].min()).days
    print(f"Días cubiertos: {days}")

    # Detectar timeframe
    if len(df) > 1:
        diffs = df["time"].diff().dropna()
        median_diff = diffs.median()
        print(f"Intervalo mediano: {median_diff}")

    # Buscar NaN
    nans = df[["open", "high", "low", "close"]].isna().sum()
    if nans.sum() > 0:
        print(f"\n⚠️ Valores NaN encontrados:")
        print(nans[nans > 0])
    else:
        print(f"✅ Sin valores NaN")

    # Verificar high >= low
    invalid = df[df["high"] < df["low"]]
    if len(invalid) > 0:
        print(f"\n⚠️ {len(invalid)} velas con high < low")
    else:
        print(f"✅ Todos los rangos OHLC válidos")

    print(f"{'='*50}\n")


# ============================================================
# Main
# ============================================================
def main():
    parser = argparse.ArgumentParser(description="Preparación de datos para backtest")

    parser.add_argument("--source", choices=["tradingview", "yahoo", "mt5"],
                       help="Fuente de datos")
    parser.add_argument("--file", help="Archivo CSV de entrada (para tradingview)")
    parser.add_argument("--instrument", default="US30",
                       choices=["US30", "NAS100", "SPX500"])
    parser.add_argument("--days", type=int, default=730, help="Días de datos")
    parser.add_argument("--output-dir", default="data", help="Directorio de salida")
    parser.add_argument("--verify", action="store_true", help="Solo verificar un CSV")
    parser.add_argument("--timeframes", nargs="+", default=["H1", "H4"],
                       help="Timeframes a generar (default: H1 H4)")

    args = parser.parse_args()
    Path(args.output_dir).mkdir(exist_ok=True)

    # --- Modo verificación ---
    if args.verify:
        if not args.file:
            print("Error: --verify requiere --file")
            sys.exit(1)
        verify_data(args.file)
        return

    if not args.source:
        print("Error: --source requerido (tradingview, yahoo, mt5)")
        sys.exit(1)

    # --- Cargar datos H1 base ---
    df_h1 = None

    if args.source == "tradingview":
        if not args.file:
            print("Error: --file requerido para tradingview")
            sys.exit(1)
        df_h1 = load_tradingview_csv(args.file)

    elif args.source == "yahoo":
        df_h1 = load_yahoo_finance(args.instrument, args.days, interval="1h")

    elif args.source == "mt5":
        df_h1 = load_from_mt5(args.instrument, "H1", args.days)

    if df_h1 is None or df_h1.empty:
        print("Error: No se pudieron cargar datos")
        sys.exit(1)

    # --- Generar cada timeframe solicitado ---
    for tf in args.timeframes:
        if tf == "H1":
            df_out = df_h1
        else:
            df_out = resample_to_timeframe(df_h1, tf)

        filename = f"{args.output_dir}/{args.instrument}_{tf}.csv"
        df_out.to_csv(filename, index=False)
        print(f"✅ Guardado: {filename} ({len(df_out)} velas)")

    # --- Resumen ---
    print(f"\n{'='*50}")
    print("DATOS LISTOS PARA BACKTEST")
    print(f"{'='*50}")
    print(f"Instrumento: {args.instrument}")
    print(f"Rango: {df_h1['time'].min()} → {df_h1['time'].max()}")
    print(f"Días: {(df_h1['time'].max() - df_h1['time'].min()).days}")
    print(f"Timeframes: {args.timeframes}")
    print(f"\nPróximo paso:")
    print(f"  python run_backtest.py \\")
    print(f"    --data-h1 {args.output_dir}/{args.instrument}_H1.csv \\")
    print(f"    --data-h4 {args.output_dir}/{args.instrument}_H4.csv \\")
    print(f"    --instrument {args.instrument} \\")
    print(f"    --output {args.output_dir}/backtest_{args.instrument}.csv")


if __name__ == "__main__":
    main()
