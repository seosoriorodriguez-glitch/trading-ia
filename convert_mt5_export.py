# -*- coding: utf-8 -*-
"""
Convierte CSVs exportados desde MT5 (formato <DATE> <TIME> <OPEN>...)
al formato esperado por data_loader.py (time, open, high, low, close, volume).

Uso:
    python convert_mt5_export.py
"""

import pandas as pd
from pathlib import Path

CONVERSIONS = [
    (
        r"C:\Users\sosor\OneDrive\Documentos\velas m1\US30_M1_202512162255_202603311830.csv",
        "data/US30_icm_M1_105d.csv",
    ),
    (
        r"C:\Users\sosor\OneDrive\Documentos\velas m1\US30_M5_202410290605_202603311830.csv",
        "data/US30_icm_M5_518d.csv",
    ),
]


def convert(src: str, dst: str):
    src_path = Path(src)
    dst_path = Path(dst)
    dst_path.parent.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(src_path, sep="\t")

    # Renombrar columnas MT5 -> data_loader
    df.columns = [c.strip("<>").lower() for c in df.columns]
    # Ahora: date, time, open, high, low, close, tickvol, vol, spread

    # Combinar date + time en columna time
    df["time"] = pd.to_datetime(df["date"] + " " + df["time"], format="%Y.%m.%d %H:%M:%S")
    df = df.rename(columns={"tickvol": "volume"})
    df = df[["time", "open", "high", "low", "close", "volume"]]
    df = df.sort_values("time").reset_index(drop=True)

    t0   = df["time"].iloc[0]
    t1   = df["time"].iloc[-1]
    days = (t1 - t0).days

    df.to_csv(dst_path, index=False)
    print(f"OK: {src_path.name}")
    print(f"    {len(df):,} velas | {t0.date()} -> {t1.date()} ({days} dias)")
    print(f"    -> {dst_path}")


def main():
    print("=" * 55)
    print("  Convirtiendo exports MT5 -> formato backtest")
    print("=" * 55)
    for src, dst in CONVERSIONS:
        print()
        convert(src, dst)
    print()
    print("Listo. Usa estos archivos en run_backtest.py:")
    for _, dst in CONVERSIONS:
        print(f"  load_csv('{dst}')")


if __name__ == "__main__":
    main()
