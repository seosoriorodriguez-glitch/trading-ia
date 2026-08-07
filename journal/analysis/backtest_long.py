# -*- coding: utf-8 -*-
"""
Backtest largo de OB London (corte 10:00 NY) sobre historial descargado de MT5.

Uso (en el VPS, con un MT5 abierto que tenga US30.cash):
    python journal/analysis/backtest_long.py --terminal-path "C:\\Program Files\\MT5_US30\\terminal64.exe"

Descarga el maximo de M5 + M1 disponible del broker, guarda CSVs en data/,
y corre el backtester con LONDON_PARAMS (end=17:00 = corte 10:00 NY).
No envia ordenes: solo LEE historial, no interfiere con los bots corriendo.
"""
import sys, argparse, copy
from pathlib import Path
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd


def download(terminal_path, symbol, m5_count, m1_count):
    import MetaTrader5 as mt5
    if not mt5.initialize(path=terminal_path):
        print("ERROR inicializando MT5:", mt5.last_error()); sys.exit(1)
    paths = {}
    for name, tf, count in [("M5", mt5.TIMEFRAME_M5, m5_count),
                            ("M1", mt5.TIMEFRAME_M1, m1_count)]:
        rates = mt5.copy_rates_from_pos(symbol, tf, 0, count)
        if rates is None or len(rates) == 0:
            print(f"ERROR: sin datos {name}:", mt5.last_error()); mt5.shutdown(); sys.exit(1)
        df = pd.DataFrame(rates)
        df["time"] = pd.to_datetime(df["time"], unit="s")
        df = df[["time", "open", "high", "low", "close", "tick_volume"]].rename(
            columns={"tick_volume": "volume"})
        path = f"data/US30_cash_{name}_long.csv"
        df.to_csv(path, index=False)
        dias = (df["time"].iloc[-1] - df["time"].iloc[0]).days
        print(f"  {name}: {len(df):>8,} velas  ({df['time'].iloc[0]} -> {df['time'].iloc[-1]}, ~{dias} dias)")
        paths[name] = path
    mt5.shutdown()
    return paths["M5"], paths["M1"]


def run_backtest(m5_path, lower_path, tf_lower_name, titulo):
    from strategies.order_block_london.backtest.config import LONDON_PARAMS
    from strategies.order_block.backtest.data_loader import load_csv
    from strategies.order_block.backtest.backtester import OrderBlockBacktester

    dfh = load_csv(m5_path); dfl = load_csv(lower_path)
    print("\n" + "=" * 70)
    print(titulo)
    print("=" * 70)
    print(f"  Periodo (solape): {max(dfh['time'].iloc[0], dfl['time'].iloc[0])}"
          f"  ->  {min(dfh['time'].iloc[-1], dfl['time'].iloc[-1])}")

    bt = OrderBlockBacktester(copy.deepcopy(LONDON_PARAMS))
    df = bt.run(dfh, dfl)
    bt.print_summary(df, "M5", tf_lower_name)

    if not df.empty:
        df = df.copy()
        df["ny"] = pd.to_datetime(df["entry_time"]).dt.hour - 7   # NY = servidor - 7
        print("\n  PnL por hora NY de apertura (confirma el corte 10:00 NY):")
        for ny in sorted(df["ny"].unique()):
            sub = df[df["ny"] == ny]; wr = (sub.pnl_usd > 0).mean() * 100
            print(f"    NY {ny:02d}:00 -> n={len(sub):4d}  WR={wr:5.1f}%  PnL={sub.pnl_usd.sum():+11.2f}")
        df["mes"] = pd.to_datetime(df["exit_time"]).dt.to_period("M")
        print("\n  PnL por mes (consistencia en distintos regimenes):")
        for m, g in df.groupby("mes"):
            print(f"    {m}: n={len(g):4d}  WR={(g.pnl_usd>0).mean()*100:5.1f}%  PnL={g.pnl_usd.sum():+11.2f}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--terminal-path", required=True,
                    help="Ruta al terminal64.exe con US30.cash (ej. MT5_US30 o MT5_BTCUSD)")
    ap.add_argument("--symbol", default="US30.cash")
    ap.add_argument("--m5-count", type=int, default=250000)
    ap.add_argument("--m1-count", type=int, default=1000000)
    a = ap.parse_args()
    print("Descargando historial de MT5 (solo lectura, no interfiere con los bots)...")
    m5, m1 = download(a.terminal_path, a.symbol, a.m5_count, a.m1_count)

    # 1) LARGO: M5 deteccion + M5 entrada -> usa todo el historial M5 (1-2 anos).
    #    Entrada mas gruesa que M1, pero valida el edge y el comportamiento por regimen.
    run_backtest(m5, m5, "M5",
                 "BACKTEST LARGO  (M5 deteccion / M5 entrada)  <- validacion de regimen")

    # 2) PRECISO: M5 + M1 -> solo el periodo que el broker tenga de M1 (corto pero exacto).
    run_backtest(m5, m1, "M1",
                 "BACKTEST PRECISO  (M5 deteccion / M1 entrada)  <- solo donde hay M1")
