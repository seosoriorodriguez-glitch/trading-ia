# -*- coding: utf-8 -*-
"""
Corre TU estrategia (STOP fiel = live) en un activo NUEVO, escalando los params al
rango M5 mediano (mismo criterio calibrado vs US30/DAX/oro). Stats + desglose mensual.
Uso: python bt_newasset.py <m5> <m1> <NOMBRE> [london|both] [rr]
"""
import sys, copy
from pathlib import Path
if sys.platform == "win32":
    import codecs; sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import pandas as pd
from strategies.order_block.backtest.config import DEFAULT_PARAMS
from strategies.order_block.backtest.data_loader import load_csv
from strategies.order_block.backtest.backtester_limit_orders import OrderBlockBacktesterLimitOrders

m5f, m1f, NAME = sys.argv[1], sys.argv[2], sys.argv[3]
ses = sys.argv[4] if len(sys.argv) > 4 else "london"
RR = float(sys.argv[5]) if len(sys.argv) > 5 else 2.5
SES = {"london": {"london": {"start": "10:00", "end": "17:00", "skip_minutes": 15}},
       "both": {"london": {"start": "10:00", "end": "17:00", "skip_minutes": 15},
                "new_york": {"start": "13:30", "end": "23:00", "skip_minutes": 15}}}

df5 = load_csv(m5f); df1 = load_csv(m1f)
df5 = df5[(df5.time >= df1.time.iloc[0]) & (df5.time <= df1.time.iloc[-1])].reset_index(drop=True)
med = float((df5.high - df5.low).median())
p = copy.deepcopy(DEFAULT_PARAMS)
p["min_risk_points"] = round(med*0.765, 5); p["buffer_points"] = round(med*1.276, 5)
p["max_risk_points"] = round(med*15.3, 5); p["slippage_points"] = round(med*0.10, 5)
p["avg_spread_points"] = round(med*0.11, 5); p["sessions"] = SES[ses]
p["target_rr"] = RR; p["initial_balance"] = 100_000.0
def pf(x): g=x[x>0].sum(); l=abs(x[x<=0].sum()); return g/l if l>0 else 99

print(f"=== {NAME} FRESCO (STOP=live) {df1.time.iloc[0]:%Y-%m-%d} -> {df1.time.iloc[-1]:%Y-%m-%d}  RR{RR} sesion={ses} ===")
print(f"    rango M5 med={med:.2f} -> buffer={p['buffer_points']} min={p['min_risk_points']} max={p['max_risk_points']} spread={p['avg_spread_points']}")
res = OrderBlockBacktesterLimitOrders(p).run(df5, df1)
if res is None or res.empty:
    print("  SIN TRADES."); sys.exit()
res = res.sort_values("exit_time").reset_index(drop=True)
n=len(res); wr=(res.pnl_r>0).mean()*100; PF=pf(res.pnl_r)
mid=n//2; p1,p2=pf(res.pnl_r.iloc[:mid]),pf(res.pnl_r.iloc[mid:])
cum=res.pnl_r.cumsum(); dd=(cum.cummax()-cum).max()*0.5
rob="SI" if PF>1 and p1>1 and p2>1 else "no"
print(f"  {n} trades | WR {wr:.1f}% | PF {PF:.2f} ({p1:.2f}/{p2:.2f}) ROBUSTA:{rob} | "
      f"ret(0.5%) {res.pnl_r.sum()*0.5:+.1f}% | DD {dd:.1f}%")
res["mes"]=pd.to_datetime(res.exit_time).dt.to_period("M").astype(str)
print("   mes:  " + "   ".join(f"{m} {g.pnl_r.sum()*0.5:+.1f}% (n{len(g)}, {(g.pnl_r>0).mean()*100:.0f}%WR)"
                               for m,g in res.groupby("mes")))
print(" breakeven RR2.5 = WR 28.6%", flush=True)
