# -*- coding: utf-8 -*-
"""
Cuantos trades del backtester de MERCADO entran FUERA de la zona OB
(long con entry < zone_low  |  short con entry > zone_high) y cuanto R aportan.
Eso mide la 'permisividad' que el STOP (=live) no tiene.
"""
import sys, copy
from pathlib import Path
if sys.platform == "win32":
    import codecs; sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import pandas as pd
from strategies.order_block.backtest.config import DEFAULT_PARAMS
from strategies.order_block.backtest.data_loader import load_csv
from strategies.order_block.backtest.backtester import OrderBlockBacktester

ASSETS = {
    "US30_F": ("data/US30_icm_M5_fresh.csv", "data/US30_icm_M1_fresh.csv", 2.0),
    "XAUUSD_F": ("data/XAUUSD_icm_M5_fresh.csv", "data/XAUUSD_icm_M1_fresh.csv", 0.40),
    "DE40": ("data/DE40_icm_M5.csv", "data/DE40_icm_M1.csv", 1.5),
}
SESSIONS = {
    "london": {"london": {"start": "10:00", "end": "17:00", "skip_minutes": 15}},
    "both": {"london": {"start": "10:00", "end": "17:00", "skip_minutes": 15},
             "new_york": {"start": "13:30", "end": "23:00", "skip_minutes": 15}},
}
asset = sys.argv[1] if len(sys.argv) > 1 else "US30_F"
ses = sys.argv[2] if len(sys.argv) > 2 else "london"
RR = float(sys.argv[3]) if len(sys.argv) > 3 else 2.5
m5f, m1f, spread = ASSETS[asset]
if len(sys.argv) > 4: spread = float(sys.argv[4])
df5 = load_csv(m5f); df1 = load_csv(m1f)
df5 = df5[(df5.time >= df1.time.iloc[0]) & (df5.time <= df1.time.iloc[-1])].reset_index(drop=True)
med = float((df5.high - df5.low).median())
p = copy.deepcopy(DEFAULT_PARAMS)
p["min_risk_points"] = round(med*0.765,5); p["buffer_points"] = round(med*1.276,5)
p["max_risk_points"] = round(med*15.3,5); p["slippage_points"] = round(med*0.10,5)
p["avg_spread_points"] = spread; p["sessions"] = SESSIONS[ses]; p["target_rr"] = RR
p["initial_balance"] = 100_000.0
if len(sys.argv) > 5: p["buffer_points"] = float(sys.argv[5])
if len(sys.argv) > 6: p["max_simultaneous_trades"] = int(sys.argv[6])

r = OrderBlockBacktester(copy.deepcopy(p)).run(df5, df1)
r = r.copy()
r["outside"] = ((r.direction=="long") & (r.entry_price < r.ob_zone_low)) | \
               ((r.direction=="short") & (r.entry_price > r.ob_zone_high))
ins = r[~r.outside]; out = r[r.outside]
def wr(x): return (x.pnl_r>0).mean()*100 if len(x) else 0
print(f"=== {asset} {ses} RR{RR} buf{p['buffer_points']} maxsim{p['max_simultaneous_trades']} (MERCADO) ===")
print(f"TOTAL   : {len(r):4d} trades  sumaR {r.pnl_r.sum():+7.0f}  WR {wr(r):.1f}%")
print(f"DENTRO  : {len(ins):4d} trades  sumaR {ins.pnl_r.sum():+7.0f}  WR {wr(ins):.1f}%")
print(f"FUERA   : {len(out):4d} trades  sumaR {out.pnl_r.sum():+7.0f}  WR {wr(out):.1f}%   <- el STOP NO los toma")
if len(out):
    print(f"   de los FUERA: ganan {int((out.pnl_r>0).sum())}, pierden {int((out.pnl_r<=0).sum())}")
print("="*60, flush=True)
