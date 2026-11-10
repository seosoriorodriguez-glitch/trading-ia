# -*- coding: utf-8 -*-
"""
Backtest de la FALSA RUPTURA con la MISMA logica del bot (estrategia.py), sin dependencias de research/.
Reglas de llenado y salida = research/pa_lab/estructura_pa/motor_pa.py (orden STOP): velas M1 Bid, Ask = Bid + spread;
VENTA STOP si el cierre anterior > orden y el minimo llega -> se llena a min(orden, apertura) - desliz_stop; COMPRA
STOP al reves con Ask; desliz SL; SL antes que TP; el TP no se mira en la vela de entrada; hueco mas alla del SL =
salida en la apertura; con una posicion abierta (o cerrada en esa vela) no entra nada; si en una vela se pueden llenar
varias, la mas cercana a la apertura.
Diferencia declarada con motor_pa: no cierra en la "ultima vela de una semana cortada" (feriado de viernes: el bot en
vivo no lo sabe); la paridad se mide contra motor_pa con fin_semana=False.

Lo usa tambien papel/fidelidad.py (comparacion diaria papel vs backtest) y el calentamiento del bot.
"""
import numpy as np
import pandas as pd

from .estrategia import EstrategiaFR, bloqueado, corte_viernes, ventanas_de_texto

VENTANA_H1 = 600


def velas_h1(m1: pd.DataFrame) -> pd.DataFrame:
    return (m1.set_index("time").resample("60min", label="left", closed="left")
            .agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna().reset_index())


def simular(m1: pd.DataFrame, est: EstrategiaFR = None, spread: float = 2.1, desliz_sl: float = 0.7,
            desliz_stop: float = 0.5, noticias=("08:26-08:34",), abierta: bool = False) -> pd.DataFrame:
    """m1: time (hora servidor), open, high, low, close (Bid). Un trade por fila. abierta=True agrega al final la
    posicion que quedo abierta (exit_reason 'abierta')."""
    est = est or EstrategiaFR()
    ventanas = ventanas_de_texto(noticias)
    m1 = m1.reset_index(drop=True)
    t = m1.time.values
    o, h, l, c = (m1[k].values.astype(float) for k in ("open", "high", "low", "close"))
    tt = pd.to_datetime(m1.time)
    h1 = velas_h1(m1)
    h1t = h1.time.values
    usados, pos, out = set(), None, []
    hora_actual, ordenes = None, []
    SP, DS, DT = spread, desliz_sl, desliz_stop

    def cerrar(i, precio, motivo):
        d = pos["dir"]
        out.append(dict(entry_time=pos["t"], exit_time=pd.Timestamp(t[i]), direction="long" if d == 1 else "short",
                        nivel=pos["nivel"], orden=pos["orden"], entry_price=pos["ent"], sl=pos["sl"], tp=pos["tp"],
                        exit_price=precio, exit_reason=motivo, R=d * (precio - pos["ent"]) / pos["riesgo"],
                        clave=pos["clave"], desde=pos["desde"]))

    for i in range(1, len(t)):
        ahora = tt.iloc[i]
        hora = ahora.floor("h")
        if hora != hora_actual:
            k = int(np.searchsorted(h1t, np.datetime64(hora), side="right"))      # incluye la vela en formacion
            ordenes = est.ordenes(h1.iloc[max(0, k - VENTANA_H1 - 1):k])
            hora_actual = hora
        if pos is not None:
            d = pos["dir"]
            if corte_viernes(ahora):
                cerrar(i, o[i] if d == 1 else o[i] + SP, "viernes"); pos = None
                continue
            if d == 1:
                if l[i] <= pos["sl"]:
                    cerrar(i, o[i] if o[i] <= pos["sl"] else pos["sl"] - DS, "sl"); pos = None
                elif h[i] >= pos["tp"] and pos["i"] < i:
                    cerrar(i, o[i] if o[i] >= pos["tp"] else pos["tp"], "tp"); pos = None
            else:
                if h[i] + SP >= pos["sl"]:
                    cerrar(i, o[i] + SP if o[i] + SP >= pos["sl"] else pos["sl"] + DS, "sl"); pos = None
                elif l[i] + SP <= pos["tp"] and pos["i"] < i:
                    cerrar(i, o[i] + SP if o[i] + SP <= pos["tp"] else pos["tp"], "tp"); pos = None
            continue
        if bloqueado(ahora, ventanas):
            continue
        cand = []
        for od in est.vigentes(ordenes, ahora, usados):
            if od.lado == "sell_stop":
                if c[i - 1] > od.precio and l[i] <= od.precio:
                    cand.append((abs(o[i] - od.precio), -1, min(od.precio, o[i]) - DT, od))
            elif c[i - 1] + SP < od.precio and h[i] + SP >= od.precio:
                cand.append((abs(o[i] + SP - od.precio), 1, max(od.precio, o[i] + SP) + DT, od))
        if not cand:
            continue
        _, d, ent, od = min(cand, key=lambda x: x[0])
        usados.add(od.clave)
        pos = dict(dir=d, ent=ent, sl=od.sl, tp=od.tp, riesgo=od.riesgo_pts, t=pd.Timestamp(t[i]), i=i,
                   nivel=od.nivel, orden=od.precio, clave=od.clave, desde=od.desde)
        if (d == 1 and ent <= od.sl) or (d == -1 and ent >= od.sl):
            cerrar(i, o[i] if d == 1 else o[i] + SP, "sl_hueco"); pos = None
        elif (d == 1 and l[i] <= od.sl) or (d == -1 and h[i] + SP >= od.sl):
            cerrar(i, od.sl - DS if d == 1 else od.sl + DS, "sl"); pos = None
    if abierta and pos is not None:
        cerrar(len(t) - 1, c[-1] if pos["dir"] == 1 else c[-1] + SP, "abierta")
    return pd.DataFrame(out)
