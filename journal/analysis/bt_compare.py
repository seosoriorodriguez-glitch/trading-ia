# -*- coding: utf-8 -*-
"""
Compara STOP (=live) vs MERCADO con params IDENTICOS, mismo data.
Cruza trade-por-trade por OB (ob_confirmed_at + zone_high) para ver:
 - cuantos trades toma cada uno
 - cuantos OBs comparten
 - si las GANADORAS coinciden (hipotesis del usuario)
Uso: python bt_compare.py <asset> <ses> <rr> <spread> <buffer> <maxsim>
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
from strategies.order_block.backtest.backtester_limit_orders import OrderBlockBacktesterLimitOrders

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
p["min_risk_points"] = round(med * 0.765, 5); p["buffer_points"] = round(med * 1.276, 5)
p["max_risk_points"] = round(med * 15.3, 5); p["slippage_points"] = round(med * 0.10, 5)
p["avg_spread_points"] = spread; p["sessions"] = SESSIONS[ses]; p["target_rr"] = RR
p["initial_balance"] = 100_000.0
if len(sys.argv) > 5: p["buffer_points"] = float(sys.argv[5])
if len(sys.argv) > 6: p["max_simultaneous_trades"] = int(sys.argv[6])

print(f"=== COMPARA {asset} {ses} RR{RR} spread{spread} buf{p['buffer_points']} maxsim{p['max_simultaneous_trades']} ===", flush=True)

def key(row): return (pd.Timestamp(row["ob_confirmed_at"]), round(float(row["ob_zone_high"]), 3))

rs = OrderBlockBacktesterLimitOrders(copy.deepcopy(p)).run(df5, df1)
rm = OrderBlockBacktester(copy.deepcopy(p)).run(df5, df1)

sd = {key(r): r for _, r in rs.iterrows()}   # STOP por OB
md = {key(r): r for _, r in rm.iterrows()}   # MERCADO por OB
sk, mk = set(sd), set(md)
common = sk & mk

def rsum(d, keys): return sum(d[k]["pnl_r"] for k in keys)
print(f"\nSTOP  : {len(sd)} trades  sumaR {rsum(sd, sk):+.0f}  WR {sum(sd[k]['pnl_r']>0 for k in sk)/max(len(sk),1)*100:.1f}%")
print(f"MERCADO: {len(md)} trades  sumaR {rsum(md, mk):+.0f}  WR {sum(md[k]['pnl_r']>0 for k in mk)/max(len(mk),1)*100:.1f}%")
print(f"\nOBs en comun (ambos operaron el mismo OB): {len(common)}")
print(f"OBs SOLO stop   : {len(sk-mk)}  (sumaR stop {rsum(sd, sk-mk):+.0f})")
print(f"OBs SOLO mercado: {len(mk-sk)}  (sumaR mercado {rsum(md, mk-sk):+.0f})")

# En los OBs comunes: coinciden las ganadoras?
both_win = sum(1 for k in common if sd[k]["pnl_r"] > 0 and md[k]["pnl_r"] > 0)
both_los = sum(1 for k in common if sd[k]["pnl_r"] <= 0 and md[k]["pnl_r"] <= 0)
diff = sum(1 for k in common if (sd[k]["pnl_r"] > 0) != (md[k]["pnl_r"] > 0))
print(f"\nEn los {len(common)} OBs comunes:")
print(f"  ambos GANAN : {both_win}")
print(f"  ambos PIERDEN: {both_los}")
print(f"  DIFIEREN (uno gana, otro pierde): {diff}")
sw = {k for k in sk if sd[k]["pnl_r"] > 0}; mw = {k for k in mk if md[k]["pnl_r"] > 0}
print(f"\nGanadoras STOP: {len(sw)}  |  Ganadoras MERCADO: {len(mw)}")
print(f"  ganadoras STOP que TAMBIEN gana mercado: {len(sw & mw)} / {len(sw)}")
print(f"  ganadoras MERCADO que el stop NI OPERO : {len(mw - mk & sk)} (de OBs que stop no toco)")
print("=" * 60, flush=True)
