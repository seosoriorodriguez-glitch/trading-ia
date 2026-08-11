# -*- coding: utf-8 -*-
"""
Backtest FIEL: usa el backtester OFICIAL de limit orders (OrderBlockBacktesterLimitOrders),
el MISMO que las validaciones canonicas (run_backtest_icm_518d, backtest_final_validacion...)
y que COINCIDE con el live (STOP/limit en el borde). Corrige el error de ob_multiasset que
usaba el backtester de mercado. Uso: python bt_faithful.py <asset> [ses] [rr] [spread] [buffer] [maxsim]
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

ASSETS = {
    "US30": ("data/US30_icm_M5_518d.csv", "data/US30_icm_M1_500k.csv", 3.0),
    "US30_F": ("data/US30_icm_M5_fresh.csv", "data/US30_icm_M1_fresh.csv", 2.0),
    "XAUUSD_F": ("data/XAUUSD_icm_M5_fresh.csv", "data/XAUUSD_icm_M1_fresh.csv", 0.40),
    "DE40": ("data/DE40_icm_M5.csv", "data/DE40_icm_M1.csv", 1.5),
    "GBPUSD": ("data/GBPUSD_icm_M5.csv", "data/GBPUSD_icm_M1.csv", 0.00015),
}
SESSIONS = {
    "london": {"london": {"start": "10:00", "end": "17:00", "skip_minutes": 15}},
    "ny": {"new_york": {"start": "13:30", "end": "23:00", "skip_minutes": 15}},
    "both": {"london": {"start": "10:00", "end": "17:00", "skip_minutes": 15},
             "new_york": {"start": "13:30", "end": "23:00", "skip_minutes": 15}},
    "24_7": {"all": {"start": "00:00", "end": "23:59", "skip_minutes": 0}},
}
asset = sys.argv[1] if len(sys.argv) > 1 else "US30"
ses = sys.argv[2] if len(sys.argv) > 2 else "both"
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

if ses == "24_7":
    import strategies.order_block.backtest.risk_manager as _rm
    _rm.is_session_allowed = lambda dt, params: True

print(f"=== BT FIEL (limit orders, = live) {asset} | {ses} RR{RR} spread {spread} buf {p['buffer_points']} maxsim {p['max_simultaneous_trades']} ===", flush=True)
bt = OrderBlockBacktesterLimitOrders(p)
res = bt.run(df5, df1)
if res is None or res.empty:
    print("  SIN TRADES."); sys.exit()
res = res.sort_values("exit_time").reset_index(drop=True)
n = len(res); wr = (res.pnl_r > 0).mean()*100
def pf(x): g = x[x > 0].sum(); l = abs(x[x <= 0].sum()); return g/l if l > 0 else 99
PF = pf(res.pnl_r); mid = n//2; p1, p2 = pf(res.pnl_r.iloc[:mid]), pf(res.pnl_r.iloc[mid:])
cum = res.pnl_r.cumsum(); ddR = (cum.cummax()-cum).max()
days = max((pd.to_datetime(res.exit_time).max() - pd.to_datetime(res.entry_time).min()).days, 1)
tout = pd.to_datetime(res.exit_time)
best90 = max((res.pnl_r[(tout >= s) & (tout < s + pd.Timedelta(days=90))].sum()*0.5 for s in tout), default=0.0)
rec90 = res.pnl_r[tout >= tout.max() - pd.Timedelta(days=90)].sum()*0.5
print(f"  Trades:{n} ({n/days*30:.1f}/mes) WR:{wr:.1f}% PF:{PF:.2f} | 1a:{p1:.2f} 2a:{p2:.2f} ROBUSTA:{'SI' if PF>1 and p1>1 and p2>1 else 'NO'}")
print(f"  SumaR:{res.pnl_r.sum():+.0f}R  Retorno(0.5%):{res.pnl_r.sum()*0.5:+.1f}%/{days}d  DD:{ddR*0.5:.1f}%  | mejor90d {best90:+.1f}% ult90d {rec90:+.1f}%")
print("=" * 60, flush=True)
