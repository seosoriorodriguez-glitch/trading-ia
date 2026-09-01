# -*- coding: utf-8 -*-
"""Carga de exports MT5 (Symbols -> Bars -> Export Bars) en formato TAB."""
from pathlib import Path

import pandas as pd


def load_mt5(path: str) -> pd.DataFrame:
    """Lee un export MT5 y devuelve time,open,high,low,close."""
    d = pd.read_csv(path, sep="\t")
    d.columns = [c.strip("<>").lower() for c in d.columns]
    d["time"] = pd.to_datetime(d["date"] + " " + d["time"], format="%Y.%m.%d %H:%M:%S")
    return d[["time", "open", "high", "low", "close"]].sort_values("time").reset_index(drop=True)


def load_m1_concat(*paths: str) -> pd.DataFrame:
    """Concatena varios M1 solapados, quedandose con el primero en el solape."""
    frames = [load_mt5(p) for p in paths]
    base = frames[0]
    for f in frames[1:]:
        base = pd.concat([base, f[f.time > base.time.max()]])
    return base.sort_values("time").reset_index(drop=True)


def check_timezone(df: pd.DataFrame, m1_for_volume: str = None) -> None:
    """
    Verifica la zona horaria por perfil de actividad.
    El pico de rango debe caer en la apertura del cash del instrumento.
    Para US30/DAX con servidor UTC+3 el pico esta en 16-17h.
    """
    rng = (df["high"] - df["low"]).groupby(df["time"].dt.hour).mean()
    peak = rng.idxmax()
    print(f"Pico de rango horario: {peak:02d}h  "
          f"({'OK, servidor UTC+3' if peak in (16, 17) else 'REVISAR zona horaria'})")
