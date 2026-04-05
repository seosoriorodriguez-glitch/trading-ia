# -*- coding: utf-8 -*-
"""
Carga y validacion de datos OHLCV desde CSV.
(Identico al de order_block — reutilizado sin cambios)
"""

import pandas as pd
from pathlib import Path


REQUIRED_COLS = {"time", "open", "high", "low", "close"}


def load_csv(path: str) -> pd.DataFrame:
    """
    Carga un CSV OHLCV y retorna un DataFrame limpio.

    Espera columnas: time, open, high, low, close, [volume]
    Los timestamps se parsean y convierten a UTC-naive para comparaciones simples.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(
            f"Archivo no encontrado: {path}\n"
            f"Formato esperado: CSV con columnas time,open,high,low,close,volume\n"
            f"Ejemplo de fila: 2024-01-02 08:00:00,37845.0,37852.0,37840.0,37848.0,1234"
        )

    df = pd.read_csv(path)

    missing = REQUIRED_COLS - set(df.columns)
    if missing:
        raise ValueError(f"Faltan columnas en {path}: {missing}")

    df["time"] = pd.to_datetime(df["time"], utc=False)
    if df["time"].dt.tz is not None:
        df["time"] = df["time"].dt.tz_localize(None)

    df = df.sort_values("time").reset_index(drop=True)

    for col in ["open", "high", "low", "close"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    if df[["open", "high", "low", "close"]].isnull().any().any():
        raise ValueError(f"Hay valores nulos en columnas OHLC en {path}")

    if "volume" not in df.columns:
        df["volume"] = 0

    return df


def validate_alignment(df_higher: pd.DataFrame, df_lower: pd.DataFrame) -> None:
    """
    Verifica que el TF menor este contenido dentro del rango del TF mayor.
    """
    h_start, h_end = df_higher["time"].iloc[0],  df_higher["time"].iloc[-1]
    l_start, l_end = df_lower["time"].iloc[0],   df_lower["time"].iloc[-1]

    if l_start < h_start:
        print(f"  AVISO: TF menor comienza antes que TF mayor "
              f"({l_start} < {h_start}). Se usaran solo los datos solapados.")
    if l_end > h_end:
        print(f"  AVISO: TF menor termina despues que TF mayor "
              f"({l_end} > {h_end}). Se usaran solo los datos solapados.")
