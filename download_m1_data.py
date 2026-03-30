# -*- coding: utf-8 -*-
"""
Descarga datos M1 y M5 de MT5 para backtest de Order Block.

Uso (con MT5 abierto y cuenta conectada):
    python download_m1_data.py

Genera:
    data/US30_cash_M1_260d.csv   (~260 dias de velas M1)
    data/US30_cash_M5_260d.csv   (reemplaza/confirma el existente)
"""
import sys
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

import MetaTrader5 as mt5
import pandas as pd
from pathlib import Path

SYMBOL   = "US30.cash"
DATA_DIR = Path("data")

# 260 dias de trading (~5 dias/semana, ~23h/dia)
# M1:  260 * 5/7 dias * 23h * 60min = ~257k velas -> pedimos 300k por margen
# M5:  260 * 5/7 dias * 23h * 12    =  ~51k velas -> pedimos 60k
M1_COUNT = 300_000
M5_COUNT =  60_000


def download(timeframe_name: str, mt5_tf, count: int, output_file: str, chunk: int = 99_000):
    """Descarga en chunks para evitar el limite de MT5 (~100k velas por request)."""
    print(f"Descargando {timeframe_name} ({count:,} velas en chunks de {chunk:,})...", flush=True)

    all_frames = []
    pos = 0
    remaining = count

    while remaining > 0:
        batch = min(chunk, remaining)
        rates = mt5.copy_rates_from_pos(SYMBOL, mt5_tf, pos, batch)

        if rates is None or len(rates) == 0:
            print(f"  Stop en pos={pos}: {mt5.last_error()}")
            break

        all_frames.append(pd.DataFrame(rates))
        fetched = len(rates)
        pos += fetched
        remaining -= fetched
        print(f"  chunk: {fetched:,} velas (total acumulado: {pos:,})", flush=True)

        if fetched < batch:
            break  # MT5 no tiene mas datos disponibles

    if not all_frames:
        print(f"ERROR: no se obtuvieron datos para {timeframe_name}")
        return False

    df = pd.concat(all_frames, ignore_index=True)
    df = df.drop_duplicates(subset=["time"]).sort_values("time").reset_index(drop=True)
    df["time"] = pd.to_datetime(df["time"], unit="s")
    df = df[["time", "open", "high", "low", "close", "tick_volume"]].rename(
        columns={"tick_volume": "volume"}
    )

    # Solo lunes-viernes
    df = df[df["time"].dt.weekday < 5].reset_index(drop=True)

    path = DATA_DIR / output_file
    df.to_csv(path, index=False)

    dias = (df["time"].iloc[-1] - df["time"].iloc[0]).days
    print(f"  Guardado: {path}")
    print(f"  Velas:    {len(df):,}")
    print(f"  Desde:    {df['time'].iloc[0]}")
    print(f"  Hasta:    {df['time'].iloc[-1]}")
    print(f"  Dias:     {dias}")
    return True


def main():
    print(f"Conectando a MT5...", flush=True)
    if not mt5.initialize():
        print(f"ERROR: no se pudo inicializar MT5: {mt5.last_error()}")
        print("Asegurate de que MT5 este abierto con la cuenta conectada.")
        sys.exit(1)

    info = mt5.symbol_info(SYMBOL)
    if info is None:
        print(f"ERROR: simbolo {SYMBOL} no encontrado. Verifica el nombre exacto en MT5.")
        mt5.shutdown()
        sys.exit(1)

    account = mt5.account_info()
    print(f"Cuenta: {account.login} | Balance: ${account.balance:,.2f}", flush=True)
    print()

    DATA_DIR.mkdir(exist_ok=True)

    ok_m1 = download("M1", mt5.TIMEFRAME_M1, M1_COUNT, "US30_cash_M1_260d.csv")
    print()
    ok_m5 = download("M5", mt5.TIMEFRAME_M5, M5_COUNT, "US30_cash_M5_260d_new.csv")

    mt5.shutdown()

    if ok_m1 and ok_m5:
        print()
        print("Datos listos. Ahora puedes correr:")
        print("  python strategies/order_block/backtest/run_backtest.py \\")
        print("      --data-higher data/US30_cash_M5_260d_new.csv \\")
        print("      --data-lower  data/US30_cash_M1_260d.csv \\")
        print("      --tf-higher M5 --tf-lower M1 \\")
        print("      --consecutive 4 --target-rr 2.5 --ema-period 0 \\")
        print("      --output strategies/order_block/backtest/results/ob_optimal_260d.csv")
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
