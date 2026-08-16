# -*- coding: utf-8 -*-
"""
CONTRAFACTUAL: ¿que habria pasado con tus operaciones REALES si el SL hubiera
sido adaptativo en vez de fijo en 35?

Para cada trade live: MISMA entrada, MISMO momento (la orden STOP va al borde de
la zona y eso no depende del buffer). Solo se mueve el SL, y con el el TP.
Despues se re-resuelve contra las velas M1 del broker, SL primero.

  zone_low  = sl_real + 35        (long,  porque el live pone sl = zone_low - 35)
  zone_high = sl_real - 35        (short)
  sl_nuevo  = zone_low - buf(dia) / zone_high + buf(dia)
  buf(dia)  = k * mediana de rangos M5 de las ultimas 20 sesiones London (SOLO PASADO)

Los dos escenarios se resuelven con el MISMO codigo, para que la comparacion sea
limpia. Ademas se contrasta el escenario "real re-resuelto" contra el pnl_r que
guardo el colector, como control de que la resolucion es fiel.
"""
import sys, json, urllib.request, statistics as st
from pathlib import Path
from collections import defaultdict

import numpy as np
import pandas as pd

REPO = Path(r"c:\Users\sosor\OneDrive\Escritorio\dev\trading\trading-ia")
VEL = Path(r"C:\Users\sosor\OneDrive\Documentos\velas m1")
BUF_LIVE = 35.0
K = 1.35
WIN = 20
RR = 2.5
COSTE = 2.0          # spread mediano medido del broker
H0, H1 = 10 * 60, 17 * 60


def load_mt5(p):
    d = pd.read_csv(p, sep="\t")
    d.columns = [c.strip("<>").lower() for c in d.columns]
    d["time"] = pd.to_datetime(d["date"] + " " + d["time"], format="%Y.%m.%d %H:%M:%S")
    return d[["time", "open", "high", "low", "close"]].sort_values("time").reset_index(drop=True)


print("Cargando velas del broker...")
m1 = load_mt5(VEL / "US30.cash_M1_202605050553_202608142349.csv")
m5 = load_mt5(VEL / "US30.cash_M5_202601020105_202608142345.csv")
print(f"  M1 {len(m1):,}  {m1.time.min()} -> {m1.time.max()}")

# ---------------------------------------------------------- buffer por dia
t5 = m5.time
mm = t5.dt.hour * 60 + t5.dt.minute
sel = (t5.dt.weekday < 5) & (mm >= H0) & (mm < H1) & ((m5.high - m5.low) > 0)
d5 = m5[sel]
por_dia = defaultdict(list)
for f, r in zip(d5.time.dt.date, (d5.high - d5.low)):
    por_dia[f].append(float(r))
fechas = sorted(por_dia)
BUF = {}
for i, f in enumerate(fechas):
    pool = [x for p in fechas[max(0, i - WIN):i] for x in por_dia[p]]
    BUF[f] = K * float(st.median(pool)) if len(pool) >= 200 else None

vals = [v for v in BUF.values() if v]
print(f"  buffer adaptativo: min {min(vals):.1f}  mediana {st.median(vals):.1f}  max {max(vals):.1f}")

# ---------------------------------------------------------- trades reales
cfg = {}
for l in (REPO / "panel" / "web" / ".env.local").read_text(encoding="utf-8").splitlines():
    l = l.strip()
    if l and not l.startswith("#") and "=" in l:
        k_, v = l.split("=", 1)
        cfg[k_.strip()] = v.strip().strip('"').strip("'")
req = urllib.request.Request(
    cfg["SUPABASE_URL"] + "/rest/v1/trades?select=direction,entry_price,sl,tp,pnl_r,"
    "risk_points,entry_time,exit_time,exit_reason,pnl_usd&symbol=eq.US30.cash"
    "&order=entry_time.asc&limit=2000",
    headers={"apikey": cfg["SUPABASE_SERVICE_KEY"],
             "Authorization": "Bearer " + cfg["SUPABASE_SERVICE_KEY"]})
live = [t for t in json.loads(urllib.request.urlopen(req).read())
        if t.get("pnl_r") is not None and t.get("sl")]
for t in live:
    t["ts"] = pd.Timestamp(t["entry_time"]).tz_convert(None)   # ya es hora servidor

t0, t1 = m1.time.min(), m1.time.max()
L = [t for t in live if t0 <= t["ts"] <= t1]
print(f"  trades reales en la ventana: {len(L)}")

# ---------------------------------------------------------- resolucion M1
tt = m1.time.values.astype("datetime64[ns]")
hi = m1.high.values; lo = m1.low.values; cl = m1.close.values


def resolver(entry, sl, tp, direccion, desde):
    """SL primero (conservador). Devuelve (R, motivo)."""
    risk = abs(entry - sl)
    if risk <= 0:
        return None, "riesgo0"
    i = int(np.searchsorted(tt, np.datetime64(desde)))
    for k in range(i, len(tt)):
        if direccion == "long":
            if lo[k] <= sl: return ((sl - entry) - COSTE) / risk, "sl"
            if hi[k] >= tp: return ((tp - entry) - COSTE) / risk, "tp"
        else:
            if hi[k] >= sl: return ((entry - sl) - COSTE) / risk, "sl"
            if lo[k] <= tp: return ((entry - tp) - COSTE) / risk, "tp"
    return ((cl[-1] - entry) if direccion == "long" else (entry - cl[-1])) - COSTE, "abierto"


filas = []
for t in L:
    e, slr, d = float(t["entry_price"]), float(t["sl"]), t["direction"]
    bd = BUF.get(t["ts"].date())
    if bd is None:
        continue
    # zona implicita a partir del SL real
    if d == "long":
        zl = slr + BUF_LIVE
        sl_new = zl - bd
    else:
        zh = slr - BUF_LIVE
        sl_new = zh + bd
    rr_real = abs(e - slr); rr_new = abs(e - sl_new)
    if rr_new < 15 or rr_new > 300:      # filtros de riesgo del live
        continue
    tp_real = e + rr_real * RR if d == "long" else e - rr_real * RR
    tp_new = e + rr_new * RR if d == "long" else e - rr_new * RR
    r_real, mo_real = resolver(e, slr, tp_real, d, t["ts"])
    r_new, mo_new = resolver(e, sl_new, tp_new, d, t["ts"])
    if r_real is None or r_new is None:
        continue
    filas.append({"ts": t["ts"], "dir": d, "buf": round(bd, 1),
                  "r_bd": t["pnl_r"], "r_real": r_real, "r_new": r_new,
                  "mo_real": mo_real, "mo_new": mo_new,
                  "risk_real": rr_real, "risk_new": rr_new})

df = pd.DataFrame(filas)
print(f"  evaluados: {len(df)}\n")

# --------------------------------------------------- control de fidelidad
ok = ((df.r_bd > 0) == (df.r_real > 0)).mean() * 100
print("=" * 78)
print("CONTROL — mi resolucion vs lo que registro el colector")
print("=" * 78)
print(f"  mismo desenlace: {ok:.0f}%   R colector {df.r_bd.mean():+.3f}  "
      f"R re-resuelto {df.r_real.mean():+.3f}")
if ok < 90:
    print("  ⚠ por debajo de 90%: la comparacion de abajo es menos fiable")


def stats(col, et):
    w = (df[col] > 0).sum(); n = len(df)
    g = df[col][df[col] > 0].sum(); p = abs(df[col][df[col] <= 0].sum())
    print(f"  {et:<26} WR={w/n*100:>5.1f}%  PF={g/p if p else 99:>5.2f}  "
          f"R/trade={df[col].mean():>+6.3f}  sumaR={df[col].sum():>+7.1f}  "
          f"USD={df[col].sum()*50:>+9.0f}")


print("\n" + "=" * 78)
print(f"COMPARACION  ({len(df)} operaciones reales, riesgo $50/trade)")
print("=" * 78)
stats("r_real", "SL FIJO 35 (lo que pasó)")
stats("r_new", f"SL ADAPTATIVO (k={K})")
print(f"\n  buffer adaptativo usado: {df.buf.min():.0f} a {df.buf.max():.0f} "
      f"(mediana {df.buf.median():.0f})   vs 35 fijo")
print(f"  riesgo mediano: {df.risk_real.median():.1f} -> {df.risk_new.median():.1f} pts")

# --------------------------------------------------- quien cambia de signo
gg = df[(df.r_real > 0) & (df.r_new > 0)]
gp = df[(df.r_real > 0) & (df.r_new <= 0)]
pg = df[(df.r_real <= 0) & (df.r_new > 0)]
pp = df[(df.r_real <= 0) & (df.r_new <= 0)]
print("\n" + "=" * 78)
print("QUE PASA CON CADA OPERACION")
print("=" * 78)
print(f"  ganadoras que SIGUEN ganando   {len(gg):>4}   R {gg.r_real.sum():+7.1f} -> {gg.r_new.sum():+7.1f}")
print(f"  ganadoras que SE PIERDEN       {len(gp):>4}   R {gp.r_real.sum():+7.1f} -> {gp.r_new.sum():+7.1f}   <- coste")
print(f"  perdedoras que SE SALVAN       {len(pg):>4}   R {pg.r_real.sum():+7.1f} -> {pg.r_new.sum():+7.1f}   <- beneficio")
print(f"  perdedoras que SIGUEN perdiendo{len(pp):>4}   R {pp.r_real.sum():+7.1f} -> {pp.r_new.sum():+7.1f}")
print(f"\n  NETO: {df.r_new.sum() - df.r_real.sum():+.1f}R  "
      f"= {(df.r_new.sum() - df.r_real.sum())*50:+.0f} USD")

print("\n" + "=" * 78)
print("POR MES")
print("=" * 78)
df["mes"] = df.ts.dt.strftime("%Y-%m")
for m, g in df.groupby("mes"):
    print(f"  {m}  n={len(g):>3}  buf~{g.buf.median():>4.0f}  "
          f"fijo {g.r_real.sum():>+7.1f}R   adaptativo {g.r_new.sum():>+7.1f}R   "
          f"delta {g.r_new.sum()-g.r_real.sum():>+6.1f}R")

print("\n" + "=" * 78)
print("POR DIRECCION")
print("=" * 78)
for d, g in df.groupby("dir"):
    print(f"  {d:<6} n={len(g):>3}   fijo {g.r_real.sum():>+7.1f}R   "
          f"adaptativo {g.r_new.sum():>+7.1f}R   delta {g.r_new.sum()-g.r_real.sum():>+6.1f}R")

df.to_csv(Path(__file__).parent / "contrafactual.csv", index=False)
print(f"\ndetalle por operacion -> contrafactual.csv")
