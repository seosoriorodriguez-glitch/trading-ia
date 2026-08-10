# -*- coding: utf-8 -*-
"""
Corre la estrategia OB de ORO sobre los ULTIMOS ~60 dias de XAUUSD tomados del
PROPIO terminal FVG (mismo feed que usa el bot en vivo). Sirve para confirmar que
la logica dispara trades en oro al ritmo esperado (~1.6/dia) — sin esperar dias.

Uso (en el VPS):
    python strategies/order_block_gold/live/recent_backtest.py
"""
import sys, argparse
from pathlib import Path
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import MetaTrader5 as mt5
import pandas as pd
from strategies.order_block_gold.live.data_feed import LiveDataFeed
from strategies.order_block_gold.backtest.config import GOLD_PARAMS
from strategies.order_block.backtest.backtester import OrderBlockBacktester

ap = argparse.ArgumentParser()
ap.add_argument("--symbol", default="XAUUSD")
ap.add_argument("--terminal-path", default=None)
ap.add_argument("--days", type=int, default=60)
a = ap.parse_args()

feed = LiveDataFeed(a.symbol, a.terminal_path)
if not feed.connect():
    print("NO conecta. Abre MT5_FVG."); sys.exit(1)

n_m5 = a.days * 300      # ~288 velas M5/dia
n_m1 = a.days * 1500     # ~1440 velas M1/dia
df5 = feed.get_latest_candles("M5", min(n_m5, 99000))
df1 = feed.get_latest_candles("M1", min(n_m1, 99000))
feed.disconnect()
if df5 is None or df1 is None:
    print("No se pudieron descargar velas."); sys.exit(1)
for d in (df5, df1):
    d["time"] = pd.to_datetime(d["time"])
print(f"XAUUSD del terminal FVG: M5={len(df5)} velas, M1={len(df1)} velas")
print(f"Rango: {df1.time.iloc[0]} -> {df1.time.iloc[-1]}")

params = dict(GOLD_PARAMS)
bt = OrderBlockBacktester(params)
res = bt.run(df5, df1)
if res.empty:
    print("\n*** 0 trades en 60 dias — SOSPECHOSO, revisar logica/params."); sys.exit()

n = len(res); wr = (res.pnl_r > 0).mean()*100
gp = res[res.pnl_r > 0].pnl_r.sum(); gl = abs(res[res.pnl_r <= 0].pnl_r.sum())
pf = gp/gl if gl > 0 else 99
days = max((pd.to_datetime(res.exit_time).max() - pd.to_datetime(res.entry_time).min()).days, 1)
print(f"\n{'='*60}")
print(f"OB ORO sobre data REAL del terminal FVG (ultimos {days} dias):")
print(f"  Trades: {n}  ({n/days:.2f}/dia)   WR: {wr:.1f}%   PF: {pf:.2f}")
print(f"  SumaR: {res.pnl_r.sum():+.1f}R   Retorno(0.5%): {res.pnl_r.sum()*0.5:+.1f}%")
print(f"{'='*60}")
print("Ultimos trades (fecha, direccion, R):")
for _, t in res.tail(10).iterrows():
    print(f"  {t.entry_time}  {t.direction:5}  {t.pnl_r:+.2f}R  ({t.exit_reason})")
print("\nSi hay trades a ~1-2/dia -> la logica de oro DISPARA bien. Hoy solo no se alineo.")
