# -*- coding: utf-8 -*-
"""
Descarga datos historicos desde MT5 (IC Markets Demo).
Genera CSVs compatibles con data_loader.py.

Uso:
    python download_mt5_icmarkets.py

MT5 debe estar abierto y conectado antes de ejecutar.
"""

import sys
import pandas as pd
from pathlib import Path
from datetime import datetime

try:
    import MetaTrader5 as mt5
except ImportError:
    print("ERROR: pip install MetaTrader5")
    sys.exit(1)

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
DOWNLOADS = [
    # (symbol, timeframe, max_bars, output_filename)
    ("US30",   mt5.TIMEFRAME_M1,  2_000_000, "data/US30_icm_M1.csv"),
    ("US30",   mt5.TIMEFRAME_M5,  2_000_000, "data/US30_icm_M5.csv"),
    ("NAS100", mt5.TIMEFRAME_M1,  2_000_000, "data/NAS100_icm_M1.csv"),
    ("NAS100", mt5.TIMEFRAME_M5,  2_000_000, "data/NAS100_icm_M5.csv"),
]

TF_NAMES = {
    mt5.TIMEFRAME_M1:  "M1",
    mt5.TIMEFRAME_M5:  "M5",
    mt5.TIMEFRAME_M15: "M15",
    mt5.TIMEFRAME_H1:  "H1",
}
# ---------------------------------------------------------------------------


ICM_PATH  = r"C:\Program Files\MetaTrader 5 IC Markets Global\terminal64.exe"
FTMO_PATH = r"C:\Program Files\FTMO MetaTrader 5\terminal64.exe"

def connect() -> bool:
    # Intentar IC Markets primero, luego FTMO como fallback
    for label, path in [("IC Markets", ICM_PATH), ("FTMO", FTMO_PATH), ("default", None)]:
        kwargs = {"path": path} if path else {}
        if mt5.initialize(**kwargs):
            info = mt5.account_info()
            broker = info.company if info else "?"
            login  = info.login  if info else "?"
            print(f"MT5 conectado via {label} | Cuenta: {login} | Broker: {broker}")
            return True
        mt5.shutdown()
    print(f"ERROR: no se pudo conectar a ningun terminal MT5")
    return False


def check_symbol(symbol: str) -> str:
    """Verifica el simbolo exacto disponible en el broker."""
    # Intentar nombre exacto y variantes comunes
    candidates = [symbol, f"{symbol}.cash", f"{symbol}USD", f"US.30"]
    for s in candidates:
        info = mt5.symbol_info(s)
        if info is not None:
            if not info.visible:
                mt5.symbol_select(s, True)
            return s
    return None


def download(symbol: str, timeframe: int, max_bars: int, output_path: str) -> bool:
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    tf_name = TF_NAMES.get(timeframe, str(timeframe))

    # Verificar símbolo disponible
    real_symbol = check_symbol(symbol)
    if real_symbol is None:
        print(f"  ERROR: simbolo {symbol} no encontrado en este broker")
        print(f"  Simbolos disponibles con '{symbol}':")
        all_symbols = mt5.symbols_get(f"*{symbol}*")
        if all_symbols:
            for s in all_symbols[:10]:
                print(f"    {s.name}")
        return False

    print(f"\nDescargando {real_symbol} [{tf_name}] ...")

    # MT5 limita a ~99,999 barras por llamada — pedimos en bloques
    CHUNK = 99_000
    all_rates = []
    start_pos = 0
    while True:
        chunk = mt5.copy_rates_from_pos(real_symbol, timeframe, start_pos, CHUNK)
        if chunk is None or len(chunk) == 0:
            break
        all_rates.extend(chunk)
        if len(chunk) < CHUNK:
            break  # ultima porcion, no hay mas
        start_pos += CHUNK
        if start_pos >= max_bars:
            break

    if not all_rates:
        print(f"  ERROR: {mt5.last_error()}")
        return False

    import numpy as np
    rates = np.array(all_rates)

    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s")

    # Renombrar tick_volume -> volume si existe
    if "tick_volume" in df.columns and "volume" not in df.columns:
        df = df.rename(columns={"tick_volume": "volume"})

    df = df[["time", "open", "high", "low", "close", "volume"]]
    df = df.sort_values("time").reset_index(drop=True)

    # Stats
    t_start = df["time"].iloc[0]
    t_end   = df["time"].iloc[-1]
    days    = (t_end - t_start).days

    df.to_csv(out, index=False)

    print(f"  OK: {len(df):,} velas | {t_start.date()} -> {t_end.date()} ({days} dias / {days//365} anios)")
    print(f"  Guardado: {out}")
    return True


def probe_max_history(symbol: str):
    """Muestra cuanta historia tiene cada TF para orientar la descarga."""
    real_symbol = check_symbol(symbol)
    if real_symbol is None:
        print(f"Simbolo {symbol} no disponible")
        return

    print(f"\n{'='*55}")
    print(f"  Historia disponible en IC Markets para: {real_symbol}")
    print(f"{'='*55}")

    tfs = [
        (mt5.TIMEFRAME_M1,  "M1",  500_000),
        (mt5.TIMEFRAME_M5,  "M5",  500_000),
        (mt5.TIMEFRAME_M15, "M15", 200_000),
        (mt5.TIMEFRAME_H1,  "H1",  100_000),
        (mt5.TIMEFRAME_D1,  "D1",  10_000),
    ]
    for tf, name, n in tfs:
        rates = mt5.copy_rates_from_pos(real_symbol, tf, 0, n)
        if rates is None or len(rates) == 0:
            print(f"  {name:5s}: sin datos")
            continue
        df = pd.DataFrame(rates)
        df["time"] = pd.to_datetime(df["time"], unit="s")
        t0 = df["time"].iloc[0]
        t1 = df["time"].iloc[-1]
        days = (t1 - t0).days
        print(f"  {name:5s}: {len(df):>8,} velas | {t0.date()} -> {t1.date()} ({days} dias)")


def main():
    print("=" * 55)
    print("  MT5 Historical Data Downloader — IC Markets")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 55)

    if not connect():
        sys.exit(1)

    # Primero mostrar historia disponible
    probe_max_history("US30")
    probe_max_history("NAS100")

    print(f"\n{'='*55}")
    print("  Iniciando descargas...")
    print(f"{'='*55}")

    results = []
    for symbol, timeframe, max_bars, output_path in DOWNLOADS:
        ok = download(symbol, timeframe, max_bars, output_path)
        results.append((symbol, TF_NAMES.get(timeframe), output_path, ok))

    mt5.shutdown()

    # Resumen
    print(f"\n{'='*55}")
    print("  RESUMEN")
    print(f"{'='*55}")
    for symbol, tf, path, ok in results:
        status = "OK  " if ok else "FAIL"
        print(f"  [{status}] {symbol} {tf} -> {path}")

    ok_paths = [(s, tf, p) for s, tf, p, ok in results if ok]
    if ok_paths:
        print("\nPara usar en backtest, edita run_backtest.py:")
        for s, tf, p in ok_paths:
            print(f"  # {s} {tf}: load_csv('{p}')")


if __name__ == "__main__":
    main()
