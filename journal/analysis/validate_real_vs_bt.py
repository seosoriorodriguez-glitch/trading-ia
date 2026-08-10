# -*- coding: utf-8 -*-
"""
VALIDACION DEFINITIVA: re-juega las operaciones REALES (entry/SL/TP exactos del broker)
sobre nuestras velas M1 y compara el resultado (ganó/perdió) contra la realidad.
Si coincide en ~todas -> el motor resuelve SL/TP fiel a MT5 = backtest confiable.
"""
import sys
from pathlib import Path
if sys.platform == "win32":
    import codecs; sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import numpy as np, pandas as pd

# --- velas M1 ---
m1 = pd.read_csv("data/US30_icm_M1_fresh.csv")
m1["time"] = pd.to_datetime(m1["time"])
mt = m1["time"].values.astype("datetime64[ns]")
mh = m1["high"].values; ml = m1["low"].values
N = len(m1)

# --- trades reales US30 dentro de ventana ---
R = pd.read_csv("journal/analysis/_real_us30_trades.csv")
R["Abrir"] = pd.to_datetime(R["Abrir"]); R["Cierre"] = pd.to_datetime(R["Cierre"])
R = R[(R["Abrir"] >= m1["time"].iloc[0]) & (R["Abrir"] <= m1["time"].iloc[-1])].reset_index(drop=True)
ecol, ccol = "Precio", "Precio.1"   # entry price, close price (2da col 'Precio')

# --- offset horario: chequear que el precio de entrada cae en la vela de entrada ---
def entry_idx(t):
    return int(np.searchsorted(mt, np.datetime64(t)))

def simulate(row, offset_h=0):
    t = row["Abrir"] + pd.Timedelta(hours=offset_h)
    i0 = entry_idx(t)
    if i0 >= N: return None
    buy = str(row["Tipo"]).lower() == "buy"
    sl = float(row["SL"]); tp = float(row["TP"])
    for i in range(i0, min(i0 + 4000, N)):
        if buy:
            if ml[i] <= sl: return 0      # SL primero
            if mh[i] >= tp: return 1
        else:
            if mh[i] >= sl: return 0
            if ml[i] <= tp: return 1
    return None  # no resuelto

# detectar mejor offset (0, +1, -1 h) por cobertura de la vela de entrada
def entry_in_candle(offset_h):
    ok = 0; tot = 0
    for _, r in R.iterrows():
        i = entry_idx(r["Abrir"] + pd.Timedelta(hours=offset_h))
        if 0 < i < N:
            tot += 1
            lo = min(ml[i-1], ml[i]); hi = max(mh[i-1], mh[i])
            if lo - 5 <= float(r[ecol]) <= hi + 5: ok += 1
    return ok / tot if tot else 0

offs = {h: entry_in_candle(h) for h in (-1, 0, 1)}
best = max(offs, key=offs.get)
print(f"Cobertura precio-entrada por offset horario: {[(h, round(v,2)) for h,v in offs.items()]} -> uso {best}h")

R["real_win"] = (R["Beneficio"] > 0).astype(int)
R["sim"] = [simulate(r, best) for _, r in R.iterrows()]
res = R.dropna(subset=["sim"]).copy(); res["sim"] = res["sim"].astype(int)

# clean = cierre real pegado a SL o TP (no cierre manual/tiempo)
def clean(r):
    d_tp = abs(float(r[ccol]) - float(r["TP"])); d_sl = abs(float(r[ccol]) - float(r["SL"]))
    return min(d_tp, d_sl) <= 5
res["clean"] = res.apply(clean, axis=1)

match = (res["sim"] == res["real_win"]).mean()
cl = res[res["clean"]]
match_cl = (cl["sim"] == cl["real_win"]).mean()
print(f"\nTrades reales validados: {len(res)} (de {len(R)}) | resueltos por sim")
print(f"  MATCH global (sim==real): {match*100:.1f}%")
print(f"  MATCH en cierres LIMPIOS (SL/TP puro, n={len(cl)}): {match_cl*100:.1f}%")
print(f"  Cierres limpios: {res['clean'].mean()*100:.0f}% | manuales/tiempo: {(1-res['clean'].mean())*100:.0f}%")
# desglose de discrepancias
mis = res[res["sim"] != res["real_win"]]
print(f"\n  Discrepancias: {len(mis)} ({len(mis)/len(res)*100:.1f}%)")
print(f"    real GANO / sim perdio: {len(mis[mis.real_win==1])}")
print(f"    real PERDIO / sim gano: {len(mis[mis.real_win==0])}")
print(f"    de las discrepancias, cuantas son cierre manual: {(~mis['clean']).sum()}/{len(mis)}")
