# -*- coding: utf-8 -*-
"""
VWAP con regimen de sesion. SOLO INVESTIGACION.

HIPOTESIS
  La reversion al VWAP no falla "en general": falla en sesiones TENDENCIALES,
  donde el flujo institucional es unidireccional y el VWAP actua como SOPORTE
  en vez de como atractor. En esas sesiones el trade correcto es el opuesto:
  comprar el pullback HACIA el VWAP (continuacion).

MEDIDA CAUSAL DEL REGIMEN
  frac_arriba = fraccion de barras de la sesion TRANSCURRIDA que cerraron sobre
  el VWAP, con ventana expansiva y desfasada una barra. Solo usa pasado.
    > umbral      -> tendencia alcista
    < 1-umbral    -> tendencia bajista
    en el medio   -> equilibrada
"""
import numpy as np
import pandas as pd
from research.vwap.vwap_lab import session_vwap


def con_regimen(m1v, anchor_hour=10, shift=True, umbral=0.70):
    d = session_vwap(m1v, anchor_hour, shift)
    sobre = (d.close > d.vwap).astype(float)
    d["frac_arriba"] = sobre.groupby(d._ses).apply(
        lambda s: s.shift(1).expanding().mean()).reset_index(level=0, drop=True)
    d["regimen"] = np.where(d.frac_arriba > umbral, "alcista",
                    np.where(d.frac_arriba < 1 - umbral, "bajista", "equilibrada"))
    return d


def run(m1v, modo="fade", anchor_hour=10, sesion=(10, 17), entrada_sigma=2.5,
        umbral=0.70, cost=4.0, min_barras=30, min_risk=15.0, tp_fijo=True,
        solo_regimen=None):
    """
    modo="fade"          -> vende arriba de la banda / compra abajo (reversion)
    modo="continuacion"  -> compra el pullback al VWAP en sesion alcista y viceversa
    tp_fijo=True         -> TP = VWAP del momento de ENTRADA (no movil)
    solo_regimen         -> None | "equilibrada" | "tendencial"
    """
    d = con_regimen(m1v, anchor_hour, shift=True, umbral=umbral).dropna(
        subset=["vwap", "sigma", "frac_arriba"]).reset_index(drop=True)
    nbar = d.groupby("_ses").cumcount().values
    hh = d.time.dt.hour.values
    hi, lo, cl = d.high.values, d.low.values, d.close.values
    vw, sg, tt = d.vwap.values, d.sigma.values, d.time.values
    reg = d.regimen.values
    up, dn = vw + entrada_sigma * sg, vw - entrada_sigma * sg

    abierto = None
    out = []
    for k in range(1, len(d)):
        if abierto is not None:
            s = abierto["dir"]
            tp = abierto["tp"] if tp_fijo else vw[k]
            if (lo[k] <= abierto["sl"]) if s == 1 else (hi[k] >= abierto["sl"]):
                abierto["r"] = -1.0 - cost / abierto["risk"]
            elif (hi[k] >= tp) if s == 1 else (lo[k] <= tp):
                abierto["r"] = abs(tp - abierto["entry"]) / abierto["risk"] - cost / abierto["risk"]
            else:
                continue
            abierto["exit_time"] = tt[k]; out.append(abierto); abierto = None

        if abierto is not None or not (sesion[0] <= hh[k] < sesion[1]):
            continue
        if nbar[k] < min_barras or sg[k] <= 0:
            continue
        r = reg[k]
        if solo_regimen == "equilibrada" and r != "equilibrada":
            continue
        if solo_regimen == "tendencial" and r == "equilibrada":
            continue

        if modo == "fade":
            if cl[k - 1] >= up[k - 1] and cl[k] < up[k]:
                sl = max(hi[k], hi[k - 1]) + 0.25 * sg[k]; risk = abs(sl - cl[k])
                if risk >= min_risk:
                    abierto = {"entry_time": tt[k], "dir": -1, "entry": cl[k], "sl": sl,
                               "tp": vw[k], "risk": risk, "regimen": r}
            elif cl[k - 1] <= dn[k - 1] and cl[k] > dn[k]:
                sl = min(lo[k], lo[k - 1]) - 0.25 * sg[k]; risk = abs(cl[k] - sl)
                if risk >= min_risk:
                    abierto = {"entry_time": tt[k], "dir": 1, "entry": cl[k], "sl": sl,
                               "tp": vw[k], "risk": risk, "regimen": r}
        else:  # continuacion: pullback AL vwap y rebote, a favor del regimen
            toco = lo[k] <= vw[k] <= hi[k]
            if not toco:
                continue
            if r == "alcista" and cl[k] > vw[k]:
                sl = min(lo[k], lo[k - 1]) - 0.5 * sg[k]; risk = abs(cl[k] - sl)
                if risk >= min_risk:
                    abierto = {"entry_time": tt[k], "dir": 1, "entry": cl[k], "sl": sl,
                               "tp": cl[k] + entrada_sigma * sg[k], "risk": risk, "regimen": r}
            elif r == "bajista" and cl[k] < vw[k]:
                sl = max(hi[k], hi[k - 1]) + 0.5 * sg[k]; risk = abs(sl - cl[k])
                if risk >= min_risk:
                    abierto = {"entry_time": tt[k], "dir": -1, "entry": cl[k], "sl": sl,
                               "tp": cl[k] - entrada_sigma * sg[k], "risk": risk, "regimen": r}
    return pd.DataFrame(out)
