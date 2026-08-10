# -*- coding: utf-8 -*-
"""
Convierte un export manual de barras de MT5 (Symbols -> Bars -> Export Bars)
al formato del backtest: time,open,high,low,close,volume

Maneja: separador TAB/coma/;  |  columnas <DATE>/<TIME> separadas o 'time' combinada
        |  fechas con puntos (2024.01.02) o guiones  |  tickvol/vol -> volume

Uso:
    python convert_mt5_export.py <archivo_raw.csv> <salida.csv>
    # ej:
    python convert_mt5_export.py XAUUSD_M1_raw.csv data/XAUUSD_icm_M1.csv
"""
import sys
from pathlib import Path
import pandas as pd

if len(sys.argv) < 3:
    print("Uso: python convert_mt5_export.py <raw.csv> <salida.csv>")
    sys.exit(1)

src, dst = sys.argv[1], sys.argv[2]

# 1) Detectar separador (MT5 suele usar TAB; a veces coma)
with open(src, "r", encoding="utf-8-sig", errors="ignore") as f:
    head = f.readline()
sep = "\t" if head.count("\t") >= head.count(",") else ","
if head.count(";") > head.count(sep):
    sep = ";"

df = pd.read_csv(src, sep=sep, encoding="utf-8-sig")

# 2) Normalizar nombres: quitar <> y espacios, minusculas
df.columns = [c.strip().strip("<>").lower() for c in df.columns]

# 3) Construir columna 'time'
if "date" in df.columns and "time" in df.columns:
    t = df["date"].astype(str).str.strip() + " " + df["time"].astype(str).str.strip()
elif "date" in df.columns:
    t = df["date"].astype(str).str.strip()
elif "time" in df.columns:
    t = df["time"].astype(str).str.strip()
elif "datetime" in df.columns:
    t = df["datetime"].astype(str).str.strip()
else:
    raise SystemExit(f"No encuentro columna de fecha/hora. Columnas: {list(df.columns)}")

# fechas con puntos -> guiones para parseo robusto
t = t.str.replace(".", "-", regex=False)
df["time"] = pd.to_datetime(t, errors="coerce")

# 4) Volumen: tickvol preferido, si no vol/volume
vol_col = next((c for c in ("tickvol", "vol", "volume") if c in df.columns), None)
df["volume"] = df[vol_col] if vol_col else 0

# 5) Validar OHLC presentes
for c in ("open", "high", "low", "close"):
    if c not in df.columns:
        raise SystemExit(f"Falta columna {c}. Columnas: {list(df.columns)}")

out = df[["time", "open", "high", "low", "close", "volume"]].dropna(subset=["time"])
out = out.sort_values("time").drop_duplicates(subset=["time"]).reset_index(drop=True)

Path(dst).parent.mkdir(parents=True, exist_ok=True)
out.to_csv(dst, index=False)
d = (out["time"].iloc[-1] - out["time"].iloc[0]).days
print(f"OK: {len(out):,} velas | {out['time'].iloc[0]} -> {out['time'].iloc[-1]} ({d} dias)")
print(f"Guardado: {dst}")
