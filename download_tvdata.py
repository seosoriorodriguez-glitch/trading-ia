# -*- coding: utf-8 -*-
"""
Descarga datos historicos desde TradingView via tvdatafeed.
Genera CSVs compatibles con data_loader.py (columnas: time,open,high,low,close,volume).

Uso:
    python download_tvdata.py

Requisito:
    pip install tvdatafeed
"""

import sys
import pandas as pd
from pathlib import Path
from datetime import datetime

try:
    from tvDatafeed import TvDatafeed, Interval
except ImportError:
    print("ERROR: instala la libreria primero:")
    print("  git clone https://github.com/rongardF/tvdatafeed.git /tmp/tvdatafeed")
    print("  pip install /tmp/tvdatafeed")
    sys.exit(1)


# ---------------------------------------------------------------------------
# CONFIG — ajusta aqui lo que quieras descargar
# ---------------------------------------------------------------------------
DOWNLOADS = [
    # (symbol, exchange, interval, n_bars, output_filename)
    # US30 M1 — maximo posible (~100k velas = ~70 dias de sesion, mas si hay historia)
    ("US30",    "FOREXCOM",  Interval.in_1_minute,  200_000, "data/US30_tv_M1.csv"),
    # US30 M5 — para deteccion de OBs, mas historia
    ("US30",    "FOREXCOM",  Interval.in_5_minute,  200_000, "data/US30_tv_M5.csv"),
]

# Con login de TradingView obtienes mas historia. Sin login: datos limitados.
# Si tienes cuenta TradingView, pon aqui tus credenciales:
TV_USERNAME = ""   # ej: "mi_usuario"
TV_PASSWORD = ""   # ej: "mi_password"
# ---------------------------------------------------------------------------


def connect() -> TvDatafeed:
    if TV_USERNAME and TV_PASSWORD:
        print(f"Conectando con usuario: {TV_USERNAME}")
        tv = TvDatafeed(TV_USERNAME, TV_PASSWORD)
    else:
        print("Conectando sin login (datos limitados)")
        print("  → Para mas historia: pon TV_USERNAME y TV_PASSWORD arriba")
        tv = TvDatafeed()
    return tv


def download_and_save(tv: TvDatafeed, symbol: str, exchange: str,
                      interval: Interval, n_bars: int, output_path: str) -> bool:
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    interval_name = interval.value if hasattr(interval, "value") else str(interval)
    print(f"\nDescargando {symbol}:{exchange} [{interval_name}] — {n_bars:,} velas...")

    try:
        df = tv.get_hist(
            symbol=symbol,
            exchange=exchange,
            interval=interval,
            n_bars=n_bars,
        )
    except Exception as e:
        print(f"  ERROR al descargar {symbol}: {e}")
        print(f"  Prueba cambiar exchange a: DJ, TVC, CAPITALCOM, CFD")
        return False

    if df is None or df.empty:
        print(f"  ERROR: no se recibieron datos para {symbol}")
        return False

    # tvdatafeed devuelve index=datetime, cols: open,high,low,close,volume
    df = df.reset_index()

    # Renombrar columna de tiempo (puede llamarse 'datetime' o 'index')
    time_col = None
    for candidate in ["datetime", "index", "time", "date"]:
        if candidate in df.columns:
            time_col = candidate
            break
    if time_col is None:
        print(f"  ERROR: no se encontro columna de tiempo. Columnas: {df.columns.tolist()}")
        return False

    df = df.rename(columns={time_col: "time"})

    # Quitar timezone si la hay (data_loader espera UTC-naive)
    if hasattr(df["time"].dtype, "tz") or str(df["time"].dtype) == "datetime64[ns, UTC]":
        df["time"] = pd.to_datetime(df["time"]).dt.tz_localize(None)
    else:
        df["time"] = pd.to_datetime(df["time"])

    # Asegurar columnas necesarias
    required = ["time", "open", "high", "low", "close"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        print(f"  ERROR: faltan columnas: {missing}. Columnas disponibles: {df.columns.tolist()}")
        return False

    if "volume" not in df.columns:
        df["volume"] = 0

    df = df[["time", "open", "high", "low", "close", "volume"]]
    df = df.sort_values("time").reset_index(drop=True)

    # Quitar filas con NaN en OHLC
    before = len(df)
    df = df.dropna(subset=["open", "high", "low", "close"])
    if len(df) < before:
        print(f"  Eliminadas {before - len(df)} filas con NaN")

    df.to_csv(out, index=False)

    t_start = df["time"].iloc[0]
    t_end   = df["time"].iloc[-1]
    days    = (t_end - t_start).days
    print(f"  OK: {len(df):,} velas | {t_start.date()} → {t_end.date()} ({days} dias)")
    print(f"  Guardado en: {out}")
    return True


def print_summary(results: list):
    print("\n" + "=" * 55)
    print("  RESUMEN DE DESCARGA")
    print("=" * 55)
    for symbol, exchange, interval, n_bars, path, ok in results:
        status = "OK " if ok else "FAIL"
        interval_name = interval.value if hasattr(interval, "value") else str(interval)
        print(f"  [{status}] {symbol} {interval_name} → {path}")
    print("=" * 55)

    # Hint para el backtest
    ok_paths = [r[4] for r in results if r[5]]
    if ok_paths:
        print("\nPara usar en el backtest, edita run_backtest.py:")
        for p in ok_paths:
            print(f"  df = load_csv('{p}')")


def main():
    print("=" * 55)
    print("  TradingView Data Downloader")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 55)

    tv = connect()

    results = []
    for symbol, exchange, interval, n_bars, output_path in DOWNLOADS:
        ok = download_and_save(tv, symbol, exchange, interval, n_bars, output_path)
        results.append((symbol, exchange, interval, n_bars, output_path, ok))

    print_summary(results)

    # Si falló, sugerir exchanges alternativos
    failed = [r for r in results if not r[5]]
    if failed:
        print("\nSi fallo la descarga, prueba estos exchanges para US30:")
        exchanges = ["FOREXCOM", "DJ", "TVC", "CAPITALCOM", "CFD", "FRED"]
        for ex in exchanges:
            print(f"  ('US30', '{ex}', ...)")
        print("\nO prueba estos simbolos alternativos:")
        symbols = ["US30USD", "DJI", "DJIA", "WS30", "US30"]
        for s in symbols:
            print(f"  ('{s}', 'FOREXCOM', ...)")


if __name__ == "__main__":
    main()
