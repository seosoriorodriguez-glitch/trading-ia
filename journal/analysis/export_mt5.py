# -*- coding: utf-8 -*-
"""
Exporta las ultimas N velas (M5 + M1) de un simbolo desde TU MT5 al formato de
nuestros CSV (time,open,high,low,close,volume). Corre en la maquina con MT5 abierto.

Uso (desde la raiz del repo):
  python journal/analysis/export_mt5.py                 # oro, 10 dias, terminal free-trial
  python journal/analysis/export_mt5.py --symbol DE40 --days 10
  python journal/analysis/export_mt5.py --symbol US30.cash --days 10 --terminal "C:\\Program Files\\MT5_BTCUSD\\terminal64.exe" --prefix US30_icm

Salida: data/<PREFIX>_M5_recent.csv  y  data/<PREFIX>_M1_recent.csv
"""
import argparse, sys
from pathlib import Path
import pandas as pd
try:
    import MetaTrader5 as mt5
except ImportError:
    sys.exit("Falta MetaTrader5. Instala:  pip install MetaTrader5   (corre esto en la maquina con MT5)")

ap = argparse.ArgumentParser()
ap.add_argument("--symbol", default="XAUUSD", help="simbolo del broker (XAUUSD, DE40, US30.cash, GER40.cash...)")
ap.add_argument("--days", type=int, default=10, help="cuantos dias hacia atras")
ap.add_argument("--terminal", default=r"C:\Program Files\MT5_FVG\terminal64.exe", help="ruta terminal64.exe")
ap.add_argument("--prefix", default=None, help="prefijo del archivo (default = simbolo sin puntos)")
a = ap.parse_args()
prefix = a.prefix or a.symbol.replace(".", "_").replace("/", "_")
outdir = Path(__file__).resolve().parents[2] / "data"
outdir.mkdir(exist_ok=True)

if not mt5.initialize(path=a.terminal):
    sys.exit(f"ERROR init MT5 ({a.terminal}): {mt5.last_error()}")
info = mt5.symbol_info(a.symbol)
if info is None:
    mt5.shutdown(); sys.exit(f"ERROR: simbolo '{a.symbol}' no existe en este broker. Revisa el nombre exacto en MarketWatch.")
if not info.visible:
    mt5.symbol_select(a.symbol, True)
print(f"MT5 OK  {a.symbol}  point={info.point}  digits={info.digits}  tick_size={info.trade_tick_size}  tick_value={info.trade_tick_value}")

TF = {"M5": (mt5.TIMEFRAME_M5, a.days * 300 + 500), "M1": (mt5.TIMEFRAME_M1, a.days * 1500 + 2000)}
cutoff = None
for tf_name, (tf, count) in TF.items():
    rates = mt5.copy_rates_from_pos(a.symbol, tf, 0, count)
    if rates is None or len(rates) == 0:
        print(f"  {tf_name}: sin datos ({mt5.last_error()})"); continue
    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s")
    if cutoff is None:
        cutoff = df["time"].max() - pd.Timedelta(days=a.days)
    df = df[df["time"] >= cutoff].copy()
    df = df.rename(columns={"tick_volume": "volume"})
    df = df[["time", "open", "high", "low", "close", "volume"]]
    out = outdir / f"{prefix}_{tf_name}_recent.csv"
    df.to_csv(out, index=False)
    print(f"  {tf_name}: {len(df)} velas  {df.time.iloc[0]} -> {df.time.iloc[-1]}  "
          f"precio {df.close.min():.2f}-{df.close.max():.2f}  -> {out.name}")
mt5.shutdown()
print("\nListo. Avisame y corro la estrategia sobre estos datos recientes.")
