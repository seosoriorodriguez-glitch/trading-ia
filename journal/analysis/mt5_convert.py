# -*- coding: utf-8 -*-
"""
Convierte un CSV exportado de MT5 (tab-separated, <DATE> <TIME> <OPEN>...) al
formato de nuestros backtests (time,open,high,low,close,volume) en data/.
Uso: python journal/analysis/mt5_convert.py "<ruta_mt5.csv>" [nombre_salida]
"""
import sys
from pathlib import Path
import pandas as pd

src = Path(sys.argv[1])
df = pd.read_csv(src, sep="\t")
df.columns = [c.strip("<>").lower() for c in df.columns]
dt = pd.to_datetime(df["date"].astype(str) + " " + df["time"].astype(str), format="%Y.%m.%d %H:%M:%S")
out_df = pd.DataFrame({
    "time": dt, "open": df["open"], "high": df["high"],
    "low": df["low"], "close": df["close"],
    "volume": df.get("tickvol", 0),
})
name = sys.argv[2] if len(sys.argv) > 2 else src.stem
outdir = Path(__file__).resolve().parents[2] / "data"
out = outdir / f"{name}.csv"
out_df.to_csv(out, index=False)
span_h = (dt.max() - dt.min()).total_seconds() / 3600
print(f"OK -> data/{out.name}")
print(f"  {len(out_df)} velas | {dt.min()} -> {dt.max()} ({span_h:.1f} h / {span_h/24:.1f} d)")
print(f"  precio {out_df.close.min():.2f} - {out_df.close.max():.2f}")
