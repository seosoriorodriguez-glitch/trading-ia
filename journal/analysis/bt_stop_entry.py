# -*- coding: utf-8 -*-
"""
Backtest FIEL AL LIVE: entrada STOP en el borde (no mercado al cierre como el otro backtest).
Replica lo que hacen los bots en vivo:
  - M5 detecta OBs.
  - M1 cierra dentro de la zona (en sesion) -> se coloca STOP en el borde:
      alcista -> BUY STOP en zone_high ; bajista -> SELL STOP en zone_low.
  - El STOP se LLENA solo si el precio alcanza el borde ANTES de que la zona se destruya
    (M5 cierra al otro lado) o expire. Si no, se cancela (no hay trade).
  - Luego SL/TP (SL primero).
Compara vs el backtest de mercado (ob_multiasset). Uso: python bt_stop_entry.py <asset> [ses] [rr] [spread] [maxsim]
"""
import sys, copy
from pathlib import Path
if sys.platform == "win32":
    import codecs; sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import numpy as np, pandas as pd
from strategies.order_block.backtest.config import DEFAULT_PARAMS
from strategies.order_block.backtest.data_loader import load_csv
from strategies.order_block.backtest.ob_detection import detect_order_blocks

ASSETS = {
    "US30": ("data/US30_icm_M5_518d.csv", "data/US30_icm_M1_500k.csv", 3.0),
    "US30_F": ("data/US30_icm_M5_fresh.csv", "data/US30_icm_M1_fresh.csv", 2.0),
    "XAUUSD_F": ("data/XAUUSD_icm_M5_fresh.csv", "data/XAUUSD_icm_M1_fresh.csv", 0.40),
    "DE40": ("data/DE40_icm_M5.csv", "data/DE40_icm_M1.csv", 1.5),
    "GBPUSD": ("data/GBPUSD_icm_M5.csv", "data/GBPUSD_icm_M1.csv", 0.00015),
}
SESSIONS = {
    "london": [(10, 0, 17, 0)], "ny": [(13, 30, 23, 0)],
    "both": [(10, 0, 17, 0), (13, 30, 23, 0)], "24_7": [(0, 0, 23, 59)],
}
asset = sys.argv[1] if len(sys.argv) > 1 else "US30"
ses = sys.argv[2] if len(sys.argv) > 2 else "both"
RR = float(sys.argv[3]) if len(sys.argv) > 3 else 2.5
m5f, m1f, spread = ASSETS[asset]
if len(sys.argv) > 4: spread = float(sys.argv[4])
MAXSIM = int(sys.argv[5]) if len(sys.argv) > 5 else 1
SKIP = 15  # skip_minutes

df5 = load_csv(m5f); df1 = load_csv(m1f)
df5 = df5[(df5.time >= df1.time.iloc[0]) & (df5.time <= df1.time.iloc[-1])].reset_index(drop=True)
med = float((df5.high - df5.low).median())
P = copy.deepcopy(DEFAULT_PARAMS)
P["min_risk_points"] = round(med * 0.765, 5); P["buffer_points"] = round(med * 1.276, 5)
P["max_risk_points"] = round(med * 15.3, 5); P["target_rr"] = RR
if len(sys.argv) > 6:  # override de buffer (para replicar config live exacta)
    P["buffer_points"] = float(sys.argv[6])
BUF, MINR, MAXR, EXP = P["buffer_points"], P["min_risk_points"], P["max_risk_points"], P["expiry_candles"]

wins = SESSIONS[ses]
def in_sess(t):
    if t.weekday() >= 5 and ses != "24_7": return False
    m = t.hour * 60 + t.minute
    for h0, mi0, h1, mi1 in wins:
        if (h0 * 60 + mi0 + SKIP) <= m < (h1 * 60 + mi1): return True
    return False

obs = detect_order_blocks(df5, P)
m5t = df5.time.values.astype("datetime64[ns]"); m5c = df5.close.values
t1 = df1.time.values.astype("datetime64[ns]"); h1 = df1.high.values; l1 = df1.low.values; c1 = df1.close.values
py1 = pd.to_datetime(df1.time.values)
n1 = len(df1)
trades = []

for ob in obs:
    bull = ob.ob_type == "bullish"; zl, zh = ob.zone_low, ob.zone_high
    entry = zh if bull else zl; sl = (zl - BUF) if bull else (zh + BUF)
    risk = abs(entry - sl)
    if risk < MINR or risk > MAXR: continue
    tp = entry + RR * risk if bull else entry - RR * risk
    conf = np.datetime64(pd.to_datetime(ob.confirmed_at))
    # destruccion (M5 cierra al otro lado) o expiry
    j0 = int(np.searchsorted(m5t, conf)); dest = np.datetime64('2999-01-01')
    for j in range(j0, len(m5c)):
        if (bull and m5c[j] < zl) or ((not bull) and m5c[j] > zh) or (j - j0 >= EXP):
            dest = m5t[j]; break
    # colocacion: primera M1 que cierra dentro, en sesion, antes de destruccion
    k0 = int(np.searchsorted(t1, conf)); place = None
    for k in range(k0, n1):
        if t1[k] >= dest: break
        if zl <= c1[k] <= zh and in_sess(py1[k]): place = k; break
    if place is None: continue
    # fill: primera M1 que alcanza el borde, antes de destruccion
    fill = None
    for k in range(place + 1, n1):
        if t1[k] >= dest: break
        if (bull and h1[k] >= entry) or ((not bull) and l1[k] <= entry): fill = k; break
    if fill is None: continue
    # SL/TP (SL primero)
    ex = None
    for k in range(fill, n1):
        if bull:
            if l1[k] <= sl: ex = (sl, 'sl', t1[k]); break
            if h1[k] >= tp: ex = (tp, 'tp', t1[k]); break
        else:
            if h1[k] >= sl: ex = (sl, 'sl', t1[k]); break
            if l1[k] <= tp: ex = (tp, 'tp', t1[k]); break
    if ex is None: ex = (c1[-1], 'end', t1[-1])
    pnl = ((ex[0] - entry) if bull else (entry - ex[0])) - spread
    trades.append({"in": t1[fill], "out": ex[2], "r": pnl / risk, "reason": ex[1]})

td = pd.DataFrame(trades).sort_values("in").reset_index(drop=True)
# max simultaneos
if not td.empty and MAXSIM >= 1:
    keep = []; openq = []
    for _, r in td.iterrows():
        openq = [o for o in openq if o > r["in"]]
        if len(openq) < MAXSIM:
            keep.append(True); openq.append(r["out"])
        else:
            keep.append(False)
    td = td[keep].reset_index(drop=True)

print(f"=== BACKTEST STOP (fiel al live) {asset} | {ses} RR{RR} spread {spread} maxsim {MAXSIM} ===")
print(f"  M5:{len(df5)} M1:{len(df1)} med {med:.3f} | OBs {len(obs)}")
if td.empty:
    print("  SIN TRADES."); sys.exit()
n = len(td); wr = (td.r > 0).mean() * 100
def pf(x): g = x[x > 0].sum(); ll = abs(x[x <= 0].sum()); return g / ll if ll > 0 else 99
PF = pf(td.r); mid = n // 2; p1, p2 = pf(td.r.iloc[:mid]), pf(td.r.iloc[mid:])
cum = td.r.cumsum(); ddR = (cum.cummax() - cum).max()
days = max((pd.to_datetime(td["out"]).max() - pd.to_datetime(td["in"]).min()).days, 1)
ret = td.r.sum() * 0.5
print(f"  Trades:{n} ({n/days*30:.1f}/mes) WR:{wr:.1f}% PF:{PF:.2f} | 1a:{p1:.2f} 2a:{p2:.2f} ROBUSTA:{'SI' if PF>1 and p1>1 and p2>1 else 'NO'}")
print(f"  SumaR:{td.r.sum():+.0f}R  Retorno(0.5%):{ret:+.1f}%/{days}d  DD:{ddR*0.5:.1f}%")
# mejor ventana de 90 dias (para ver la varianza vs un trimestre bueno)
tout = pd.to_datetime(td["out"])
best90 = 0.0
for start in tout:
    w = td[(tout >= start) & (tout < start + pd.Timedelta(days=90))]
    best90 = max(best90, w.r.sum() * 0.5)
rec = td[tout >= tout.max() - pd.Timedelta(days=90)]
print(f"  MEJOR ventana 90d: {best90:+.1f}%  |  ultimos 90d: {rec.r.sum()*0.5:+.1f}%  (un trimestre bueno != promedio)")
print("=" * 60)
