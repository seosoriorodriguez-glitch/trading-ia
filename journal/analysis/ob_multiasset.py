# -*- coding: utf-8 -*-
"""
Valida la OB (motor REAL dual M5+M1) en OTROS activos.
Params de escala (buffer/min/max_risk/spread) se RE-ESCALAN por instrumento
segun su rango M5 mediano (el motor es R-normalizado; la escala de puntos no).
Robustez por mitades (PF>1 en 1a Y 2a) + DD. Uso: python ob_multiasset.py <asset> [session]
"""
import sys, copy
from pathlib import Path
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import pandas as pd
from strategies.order_block.backtest.config import DEFAULT_PARAMS
from strategies.order_block.backtest.data_loader import load_csv
from strategies.order_block.backtest.backtester import OrderBlockBacktester

# activo -> (csv_M5, csv_M1, spread_real_en_puntos_precio)
ASSETS = {
    "XAUUSD": ("data/XAUUSD_icm_M5.csv", "data/XAUUSD_icm_M1.csv", 0.20),
    "BTCUSD": ("data/BTCUSD_icm_M5.csv", "data/BTCUSD_icm_M1.csv", 20.0),
    "USDJPY": ("data/USDJPY_icm_M5.csv", "data/USDJPY_icm_M1.csv", 0.012),
    "CADJPY": ("data/CADJPY_icm_M5.csv", "data/CADJPY_icm_M1.csv", 0.018),
    "EURCHF": ("data/EURCHF_icm_M5.csv", "data/EURCHF_icm_M1.csv", 0.00015),
    "US2000": ("data/US2000_icm_M5.csv", "data/US2000_icm_M1.csv", 0.15),
    "US30":   ("data/US30_icm_M5_518d.csv", "data/US30_icm_M1_500k.csv", 3.0),
    "XAUUSD_F": ("data/XAUUSD_icm_M5_fresh.csv", "data/XAUUSD_icm_M1_fresh.csv", 0.40),
    "US30_F":   ("data/US30_icm_M5_fresh.csv",   "data/US30_icm_M1_fresh.csv",   2.0),
}
SESSIONS = {
    "london": {"london":   {"start": "10:00", "end": "17:00", "skip_minutes": 15}},
    "ny":     {"new_york":  {"start": "13:30", "end": "23:00", "skip_minutes": 15}},
    "both":   {"london":    {"start": "10:00", "end": "17:00", "skip_minutes": 15},
               "new_york":  {"start": "13:30", "end": "23:00", "skip_minutes": 15}},
}

asset = sys.argv[1] if len(sys.argv) > 1 else "XAUUSD"
sess  = sys.argv[2] if len(sys.argv) > 2 else "both"
m5f, m1f, spread = ASSETS[asset]
if len(sys.argv) > 3:                       # override costo all-in (spread+comision+slippage)
    spread = float(sys.argv[3])

df5 = load_csv(m5f); df1 = load_csv(m1f)
# recortar M5 al rango del M1 (para que la entrada exista siempre)
df5 = df5[(df5.time >= df1.time.iloc[0]) & (df5.time <= df1.time.iloc[-1])].reset_index(drop=True)
med = float((df5.high - df5.low).median())

p = copy.deepcopy(DEFAULT_PARAMS)
p["min_risk_points"]  = round(med * 0.765, 5)   # ratios calibrados vs US30 (med 19.6)
p["buffer_points"]    = round(med * 1.276, 5)
p["max_risk_points"]  = round(med * 15.3, 5)
p["avg_spread_points"]= spread
p["slippage_points"]  = round(med * 0.10, 5)
p["sessions"]         = SESSIONS[sess]
p["target_rr"]        = 3.5
p["initial_balance"]  = 100_000.0

print(f"=== OB {asset} | sesion={sess} | M5+M1 (motor real) ===")
print(f"  rango M5 med={med:.4f} -> min_risk={p['min_risk_points']} buffer={p['buffer_points']} "
      f"max_risk={p['max_risk_points']} spread={spread}")
print(f"  M5:{len(df5)}  M1:{len(df1)}  {df1.time.iloc[0]} -> {df1.time.iloc[-1]}", flush=True)

bt = OrderBlockBacktester(p)
res = bt.run(df5, df1)
if res.empty:
    print("  SIN TRADES."); sys.exit()

res = res.sort_values("exit_time").reset_index(drop=True)
n = len(res); wr = (res.pnl_r > 0).mean()*100
def pf(x): g=x[x>0].sum(); l=abs(x[x<=0].sum()); return g/l if l>0 else 99
PF = pf(res.pnl_r); mid = n//2
p1 = pf(res.pnl_r.iloc[:mid]); p2 = pf(res.pnl_r.iloc[mid:])
sumR = res.pnl_r.sum()
ret = (bt.balance - bt.initial_balance)/bt.initial_balance*100
cum = res.pnl_r.cumsum(); ddR = (cum.cummax()-cum).max()
days = max((pd.to_datetime(res.exit_time).max() - pd.to_datetime(res.entry_time).min()).days, 1)
rob = "SI" if PF>1 and p1>1 and p2>1 else "NO"
print(f"  Trades:{n} ({n/days*30:.1f}/mes) WR:{wr:.1f}% PF:{PF:.2f} | 1a:{p1:.2f} 2a:{p2:.2f} ROBUSTA:{rob}")
print(f"  SumaR:{sumR:+.0f}R  Retorno(0.5%):{ret:+.1f}%/{days}d (~{ret/days*365:+.0f}%/ano)  DD:{ddR*0.5:.1f}%")
print("="*60, flush=True)
