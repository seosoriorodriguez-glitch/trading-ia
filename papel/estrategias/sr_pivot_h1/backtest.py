# -*- coding: utf-8 -*-
"""
Backtest de S/R Pivot al toque H1 con la MISMA logica del bot (estrategia.py), sin dependencias de research/.
Reglas de llenado y salida = research/pa_lab/repaso/motor_toque2.py (solo LIMIT): velas M1 Bid, Ask = Bid + spread,
desliz SL, SL antes que TP, el TP no se mira en la vela de entrada, hueco mas alla del SL = salida en la apertura.
herramientas/paridad.py comprueba que da trade por trade lo mismo que motor_toque2 (con feriados=False).

Lo usan tambien papel/fidelidad.py (corre el backtest sobre las velas del broker del periodo en papel y compara) y el
calentamiento del bot.
  spread    un numero o uno por vela (el del broker, para la comparacion diaria).
  feriados  True = corte de fin de semana con feriados y cierres tempranos (papel/calendario.py), como el bot.
  abierta   True = agrega al final la posicion que quedo abierta (exit_reason 'abierta'): el bot la usa al arrancar
            para quedar "ocupado" igual que el backtest.
"""
import numpy as np
import pandas as pd

from .estrategia import EstrategiaSR, bloqueado, corte_viernes, ventanas_de_texto

VENTANA_H1 = 600


def velas_h1(m1: pd.DataFrame) -> pd.DataFrame:
    return (m1.set_index("time").resample("60min", label="left", closed="left")
            .agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna().reset_index())


def simular(m1: pd.DataFrame, est: EstrategiaSR = None, spread=2.1, desliz_sl: float = 0.7,
            noticias=("08:26-08:34",), feriados: bool = True, abierta: bool = False) -> pd.DataFrame:
    """m1: time (hora servidor), open, high, low, close (Bid). Devuelve un trade por fila."""
    est = est or EstrategiaSR(20, 130, 2.5)
    ventanas = ventanas_de_texto(noticias)
    m1 = m1.reset_index(drop=True)
    t = m1.time.values
    o, h, l, c = (m1[k].values.astype(float) for k in ("open", "high", "low", "close"))
    sp = np.full(len(t), float(spread)) if np.isscalar(spread) else np.asarray(spread, float)
    tt = pd.to_datetime(m1.time)
    h1 = velas_h1(m1)
    h1t = h1.time.values
    usados, pos, out = set(), None, []
    hora_actual, niveles = None, []
    DS = desliz_sl

    def cerrar(i, precio, motivo):
        d = pos["dir"]
        out.append(dict(entry_time=pos["t"], exit_time=pd.Timestamp(t[i]), direction="long" if d == 1 else "short",
                        nivel=pos["nivel"], orden=pos["orden"], entry_price=pos["ent"], sl=pos["sl"], tp=pos["tp"],
                        exit_price=precio, exit_reason=motivo, R=d * (precio - pos["ent"]) / pos["riesgo"],
                        clave=pos["clave"]))

    for i in range(1, len(t)):
        ahora = tt.iloc[i]
        SP = sp[i]
        hora = ahora.floor("h")
        if hora != hora_actual:
            k = int(np.searchsorted(h1t, np.datetime64(hora), side="right"))
            niveles = est.niveles(h1.iloc[max(0, k - VENTANA_H1 - 1):k])
            hora_actual = hora
        if pos is not None:
            d = pos["dir"]
            if corte_viernes(ahora, feriados):
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
        if bloqueado(ahora, ventanas, feriados):
            continue
        cand = []
        for od in est.deseadas(est.activos(niveles, ahora), usados, c[i - 1], sp[i - 1]):
            if od.lado == "buy_limit" and l[i] + SP <= od.precio:
                cand.append((abs(o[i] + SP - od.precio), 1, min(od.precio, o[i] + SP), od))
            elif od.lado == "sell_limit" and h[i] >= od.precio:
                cand.append((abs(o[i] - od.precio), -1, max(od.precio, o[i]), od))
        if not cand:
            continue
        _, d, ent, od = min(cand, key=lambda x: x[0])
        usados.add(od.clave)
        pos = dict(dir=d, ent=ent, sl=od.sl, tp=od.tp, riesgo=od.riesgo_pts, t=pd.Timestamp(t[i]), i=i,
                   nivel=od.nivel, orden=od.precio, clave=od.clave)
        if (d == 1 and ent <= od.sl) or (d == -1 and ent >= od.sl):
            cerrar(i, o[i] if d == 1 else o[i] + SP, "sl_hueco"); pos = None
        elif (d == 1 and l[i] <= od.sl) or (d == -1 and h[i] + SP >= od.sl):
            cerrar(i, od.sl - DS if d == 1 else od.sl + DS, "sl"); pos = None
    if abierta and pos is not None:
        cerrar(len(t) - 1, c[-1] if pos["dir"] == 1 else c[-1] + sp[-1], "abierta")
    return pd.DataFrame(out)
