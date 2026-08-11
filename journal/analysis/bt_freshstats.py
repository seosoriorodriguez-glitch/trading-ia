# -*- coding: utf-8 -*-
"""Stats FRESCO (STOP fiel) + desglose mensual. Uso: python bt_freshstats.py <m5> <m1> <oro|dax|us30> <buf1,buf2>"""
import sys, copy
from pathlib import Path
if sys.platform == "win32":
    import codecs; sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import pandas as pd
from strategies.order_block.backtest.data_loader import load_csv
from strategies.order_block_gold.backtest.config import GOLD_PARAMS
from strategies.order_block_dax.backtest.config import DAX_PARAMS
from strategies.order_block_london.backtest.config import LONDON_PARAMS
from strategies.order_block.backtest.backtester_limit_orders import OrderBlockBacktesterLimitOrders
from strategies.order_block.backtest.backtester import OrderBlockBacktester

m5f = sys.argv[1] if len(sys.argv) > 1 else "data/XAUUSD_freshAUG_M5.csv"
m1f = sys.argv[2] if len(sys.argv) > 2 else "data/XAUUSD_freshAUG_M1.csv"
cfg = (sys.argv[3] if len(sys.argv) > 3 else "oro").lower()
PARAMS = {"oro": GOLD_PARAMS, "dax": DAX_PARAMS, "us30": LONDON_PARAMS}[cfg]
NAME = {"oro": "ORO", "dax": "DAX", "us30": "US30 London"}[cfg]
bufs = [float(b) for b in sys.argv[4].split(",")] if len(sys.argv) > 4 else [PARAMS["buffer_points"], PARAMS["buffer_points"]*2]
ses = sys.argv[5] if len(sys.argv) > 5 else None   # london | both (override)
SES = {"london": {"london": {"start": "10:00", "end": "17:00", "skip_minutes": 15}},
       "both": {"london": {"start": "10:00", "end": "17:00", "skip_minutes": 15},
                "new_york": {"start": "13:30", "end": "23:00", "skip_minutes": 15}}}

df5 = load_csv(m5f); df1 = load_csv(m1f)
df5 = df5[(df5.time >= df1.time.iloc[0]) & (df5.time <= df1.time.iloc[-1])].reset_index(drop=True)
def pf(x): g=x[x>0].sum(); l=abs(x[x<=0].sum()); return g/l if l>0 else 99

entry = sys.argv[6] if len(sys.argv) > 6 else "stop"   # stop (=live) | market
BT = OrderBlockBacktester if entry == "market" else OrderBlockBacktesterLimitOrders
seslabel = ses if ses else "+".join(PARAMS["sessions"].keys())
print(f"=== {NAME} FRESCO ({'MERCADO' if entry=='market' else 'STOP=live'}) {df1.time.iloc[0]:%Y-%m-%d} -> {df1.time.iloc[-1]:%Y-%m-%d}  RR2.5  sesion={seslabel} ===")
for buf in bufs:
    p = copy.deepcopy(PARAMS); p["buffer_points"] = buf
    if ses: p["sessions"] = SES[ses]
    res = BT(p).run(df5, df1)
    if res is None or res.empty:
        print(f"\n buffer {buf}: SIN TRADES"); continue
    res = res.sort_values("exit_time").reset_index(drop=True)
    n=len(res); wr=(res.pnl_r>0).mean()*100; PF=pf(res.pnl_r)
    mid=n//2; p1,p2=pf(res.pnl_r.iloc[:mid]),pf(res.pnl_r.iloc[mid:])
    cum=res.pnl_r.cumsum(); dd=(cum.cummax()-cum).max()*0.5
    print(f"\n buffer {buf}: {n} trades | WR {wr:.1f}% | PF {PF:.2f} ({p1:.2f}/{p2:.2f}) | "
          f"SumaR {res.pnl_r.sum():+.1f} | ret(0.5%) {res.pnl_r.sum()*0.5:+.1f}% | DD {dd:.1f}%")
    res["mes"] = pd.to_datetime(res.exit_time).dt.to_period("M").astype(str)
    print("   mes:  " + "   ".join(f"{m} {g.pnl_r.sum()*0.5:+.1f}% (n{len(g)}, {(g.pnl_r>0).mean()*100:.0f}%WR)"
                                   for m, g in res.groupby("mes")))
print("\n breakeven RR2.5 = WR 28.6%", flush=True)
