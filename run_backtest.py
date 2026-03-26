"""
Script para ejecutar backtests.

Uso:
  python run_backtest.py --data datos_us30_h1.csv --data-h4 datos_us30_h4.csv
  python run_backtest.py --from-mt5 US30.raw --days 365

El CSV debe tener columnas: time, open, high, low, close, volume
"""

import sys
import argparse
import logging
from pathlib import Path
from datetime import datetime, timedelta

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))

from core.config_loader import get_config
from core.market_data import candles_from_dataframe
from backtest.backtester import Backtester


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%H:%M:%S",
    )


def load_csv_data(filepath: str, timeframe: str):
    """Carga datos desde CSV."""
    df = pd.read_csv(filepath, parse_dates=["time"])
    df = df.sort_values("time").reset_index(drop=True)
    return candles_from_dataframe(df, timeframe)


def load_from_mt5(symbol: str, timeframe: str, days: int):
    """Carga datos directamente de MT5."""
    from core.market_data import MT5Connection

    config = get_config()
    mt5_config = config.strategy.get("mt5", {})
    mt5 = MT5Connection(
        host=mt5_config.get("host", "localhost"),
        port=mt5_config.get("port", 8001),
    )
    if not mt5.connect():
        print("Error: No se pudo conectar a MT5")
        sys.exit(1)

    # Calcular número de velas
    if timeframe == "H4":
        candles_per_day = 6
    elif timeframe == "H1":
        candles_per_day = 24
    else:
        candles_per_day = 24

    count = days * candles_per_day
    candles = mt5.get_candles(symbol, timeframe, count)
    mt5.disconnect()

    print(f"Cargadas {len(candles)} velas {timeframe} de {symbol}")
    return candles


def export_data_from_mt5(symbol: str, days: int, output_dir: str = "data"):
    """Exporta datos de MT5 a CSV para backtesting offline."""
    from core.market_data import MT5Connection

    config = get_config()
    mt5_config = config.strategy.get("mt5", {})
    mt5 = MT5Connection(
        host=mt5_config.get("host", "localhost"),
        port=mt5_config.get("port", 8001),
    )
    if not mt5.connect():
        print("Error: No se pudo conectar a MT5")
        return

    Path(output_dir).mkdir(exist_ok=True)

    for tf in ["H4", "H1"]:
        candles_per_day = 6 if tf == "H4" else 24
        count = days * candles_per_day
        candles = mt5.get_candles(symbol, tf, count)

        if candles:
            df = pd.DataFrame([{
                "time": c.time.isoformat(),
                "open": c.open,
                "high": c.high,
                "low": c.low,
                "close": c.close,
                "volume": c.volume,
            } for c in candles])

            filename = f"{output_dir}/{symbol.replace('.', '_')}_{tf}_{days}d.csv"
            df.to_csv(filename, index=False)
            print(f"Exportado: {filename} ({len(candles)} velas)")

    mt5.disconnect()


def main():
    parser = argparse.ArgumentParser(description="Backtest de estrategia S/R")

    # Fuente de datos
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--data-h1", help="CSV con datos H1")
    group.add_argument("--from-mt5", help="Símbolo MT5 para cargar datos directos")
    group.add_argument("--export-mt5", help="Exportar datos de MT5 a CSV")

    parser.add_argument("--data-h4", help="CSV con datos H4 (requerido con --data-h1)")
    parser.add_argument("--instrument", default="US30", help="Nombre del instrumento (default: US30)")
    parser.add_argument("--days", type=int, default=365, help="Días de datos (default: 365)")
    parser.add_argument("--balance", type=float, default=100_000, help="Balance inicial (default: 100000)")
    parser.add_argument("--output", help="Guardar trades en CSV")

    args = parser.parse_args()
    setup_logging()
    config = get_config()

    logger = logging.getLogger("backtest")

    # --- Exportar datos ---
    if args.export_mt5:
        symbol = config.get_instrument(args.instrument)["symbol_mt5"]
        export_data_from_mt5(symbol, args.days)
        return

    # --- Cargar datos ---
    if args.from_mt5:
        symbol = config.get_instrument(args.instrument)["symbol_mt5"]
        candles_h4 = load_from_mt5(symbol, "H4", args.days)
        candles_h1 = load_from_mt5(symbol, "H1", args.days)
    else:
        if not args.data_h4:
            print("Error: --data-h4 requerido cuando se usa --data-h1")
            sys.exit(1)
        candles_h4 = load_csv_data(args.data_h4, "H4")
        candles_h1 = load_csv_data(args.data_h1, "H1")

    logger.info(f"Datos cargados: {len(candles_h4)} velas H4, {len(candles_h1)} velas H1")

    # --- Ejecutar backtest ---
    instrument_config = config.get_instrument(args.instrument)

    backtester = Backtester(
        config=config.strategy,
        instrument_config=instrument_config,
        instrument_name=args.instrument,
    )

    result = backtester.run(
        candles_h4=candles_h4,
        candles_h1=candles_h1,
        initial_balance=args.balance,
    )

    # --- Mostrar resultados ---
    print(result.summary())

    # --- Exportar trades ---
    if args.output:
        df = result.to_dataframe()
        df.to_csv(args.output, index=False)
        print(f"\nTrades exportados a: {args.output}")
    else:
        # Mostrar últimos trades
        df = result.to_dataframe()
        if not df.empty:
            print("\n--- Últimos 10 trades ---")
            print(df.tail(10).to_string(index=False))


if __name__ == "__main__":
    main()
