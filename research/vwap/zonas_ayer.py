# -*- coding: utf-8 -*-
"""
Estrategia: zonas VWAP del dia anterior proyectadas a hoy. SOLO INVESTIGACION.

Arquitectura identica a OB London, cambiando el origen de la zona:
  zona ROJA  de ayer (sobrecompra) -> se busca REVERSION -> SHORT
      entrada: SELL STOP en el borde INFERIOR (confirma rechazo al caer)
      SL:      borde SUPERIOR (+buffer)
  zona VERDE de ayer (sobreventa)  -> LONG, espejo.

Definicion de zona (dos variantes, la banda se mueve durante el dia):
  "cierre"  -> bandas al cierre de ayer
  "maximo"  -> extension maxima que alcanzo la zona en todo el dia (mas ancha)
"""
import numpy as np
import pandas as pd


def zonas_previas(m1v, s_int=1.28, s_ext=4.01, modo="cierre", cap_sigma=None, ventana=20, s_sl=None):
    d = m1v.copy()
    d["dia"] = d.time.dt.date
    hl2 = (d.high + d.low) / 2.0
    v = d.volume.astype(float).clip(lower=1e-9)
    pv = (hl2 * v).groupby(d.dia).cumsum(); vv = v.groupby(d.dia).cumsum()
    v2 = (v * hl2 * hl2).groupby(d.dia).cumsum()
    vw = pv / vv
    dev = np.sqrt(np.maximum(v2 / vv - vw * vw, 0))
    nb = d.groupby(d.dia).cumcount()
    ok = nb >= 30                                  # ignorar sigma inestable del arranque
    t = pd.DataFrame({"dia": d.dia, "vw": vw, "dev": dev, "ok": ok})
    g = t[t.ok].groupby("dia")
    if modo == "cierre":
        z = pd.DataFrame({"vw": g.vw.last(), "dev": g.dev.last()})
        z["rojo_lo"] = z.vw + s_int * z.dev; z["rojo_hi"] = z.vw + s_ext * z.dev
        z["verde_hi"] = z.vw - s_int * z.dev; z["verde_lo"] = z.vw - s_ext * z.dev
    else:
        z = pd.DataFrame({"vw": g.vw.last()})
        z["rojo_lo"] = g.apply(lambda x: (x.vw + s_int * x.dev).min())
        z["rojo_hi"] = g.apply(lambda x: (x.vw + s_ext * x.dev).max())
        z["verde_hi"] = g.apply(lambda x: (x.vw - s_int * x.dev).max())
        z["verde_lo"] = g.apply(lambda x: (x.vw - s_ext * x.dev).min())
    if cap_sigma is not None:
        # OPCION 1: acotar sigma a cap_sigma x la mediana movil de las ultimas `ventana`
        # sesiones. Evita que un dia excepcional deje una zona desproporcionada.
        med = z.dev.rolling(ventana, min_periods=5).median()
        lim = (cap_sigma * med).fillna(z.dev)
        z["dev"] = np.minimum(z.dev, lim)
        z["rojo_lo"] = z.vw + s_int * z.dev; z["rojo_hi"] = z.vw + s_ext * z.dev
        z["verde_hi"] = z.vw - s_int * z.dev; z["verde_lo"] = z.vw - s_ext * z.dev
    if s_sl is not None:                            # banda externa para el SL
        z["rojo_sl"] = z.vw + s_sl * z.dev
        z["verde_sl"] = z.vw - s_sl * z.dev
    return z.shift(1)                              # las de AYER, para hoy


def run(m1v, s_int=1.28, s_ext=4.01, modo="cierre", tp="vwap_ayer",
        rr=2.0, buffer_pts=0.0, cost=4.0, sesion=(10, 17), max_sim=1,
        expiry_min=60, max_por_dia=1, max_risk_pts=None, sl_frac=1.0,
        sl_pts=None, cap_sigma=None, pen=0.0, ent=0.0, max_ancho=None,
        tf=1, s_sl=None):
    """expiry_min: la pendiente se cancela si no se llena (sin esto bloquea el dia).
    max_por_dia: senales permitidas por zona y dia (1 = se mitiga tras operarla).
    max_risk_pts: descarta la zona si su ancho supera esto (como max_risk_points de OB).
    sl_frac: fraccion del ancho de zona que se usa para el SL (1.0 = borde opuesto).
    sl_pts:  OPCION 2 - SL a distancia FIJA en puntos, desacoplado del ancho de zona.
             La zona decide DONDE operar; el riesgo lo fija este parametro.
    cap_sigma: acota la sigma de ayer a N veces su mediana movil.
    pen:  penetracion exigida antes de armar la orden, como fraccion del ancho.
          0 = basta con tocar el borde | 0.5 = el cierre debe pasar la mitad
    ent:  donde va el STOP dentro de la zona, como fraccion desde el borde lejano.
          0 = borde lejano (el precio recorre toda la zona) | 0.5 = mitad
    max_ancho: descarta zonas mas anchas que esto en puntos.
    tf:   timeframe del disparador. 1 = cierre M1 | 5 = cierre M5
    s_sl: si se define, el SL va en esa banda sigma de AYER en vez del borde de zona.
    """
    z = zonas_previas(m1v, s_int, s_ext, modo, cap_sigma, s_sl=s_sl)
    d = m1v.copy(); d["dia"] = d.time.dt.date
    cols = ["vw", "rojo_lo", "rojo_hi", "verde_hi", "verde_lo"]
    if s_sl is not None: cols += ["rojo_sl", "verde_sl"]
    for c in cols:
        d[c] = d.dia.map(z[c])
    d = d.dropna(subset=["rojo_lo", "verde_hi"]).reset_index(drop=True)
    hh = d.time.dt.hour.values
    hi, lo, cl = d.high.values, d.low.values, d.close.values
    RL, RH = d.rojo_lo.values, d.rojo_hi.values
    GH, GL = d.verde_hi.values, d.verde_lo.values
    VW = d.vw.values; tt = d.time.values; dias = d.dia.values
    RSL = d.rojo_sl.values if s_sl is not None else None
    GSL = d.verde_sl.values if s_sl is not None else None
    minu = d.time.dt.minute.values

    pend = None; abierto = None; cuenta = {}; out = []; pend_k = -1
    for k in range(len(d)):
        if abierto is not None:
            s = abierto["dir"]
            if (lo[k] <= abierto["sl"]) if s == 1 else (hi[k] >= abierto["sl"]):
                abierto["r"] = -1.0 - cost / abierto["risk"]
            elif (hi[k] >= abierto["tp"]) if s == 1 else (lo[k] <= abierto["tp"]):
                abierto["r"] = abs(abierto["tp"] - abierto["entry"]) / abierto["risk"] - cost / abierto["risk"]
            else:
                continue
            abierto["exit_time"] = tt[k]; out.append(abierto); abierto = None

        if not (sesion[0] <= hh[k] < sesion[1]):
            continue

        # llenado / expiracion de la orden pendiente
        if pend is not None and abierto is None:
            s = pend["dir"]
            lleno = (hi[k] >= pend["entry"]) if s == 1 else (lo[k] <= pend["entry"])
            if lleno:
                pend["entry_time"] = tt[k]; abierto = pend; pend = None
            elif k - pend_k >= expiry_min:
                pend = None
            continue

        if abierto is not None or pend is not None:
            continue

        # el disparador solo se evalua al cierre de la vela del TF elegido
        if tf > 1 and (minu[k] % tf) != tf - 1:
            continue
        # senal: cierre dentro de la zona de ayer
        for nom, zlo, zhi, s in (("rojo", RL[k], RH[k], -1), ("verde", GL[k], GH[k], 1)):
            clave = (dias[k], nom)
            if cuenta.get(clave, 0) >= max_por_dia or not (zlo <= cl[k] <= zhi):
                continue
            ancho = abs(zhi - zlo)
            lim = max_ancho if max_ancho is not None else max_risk_pts
            if lim is not None and ancho > lim:
                continue                              # zona impracticable
            # penetracion: el precio entra por el borde CERCANO (zlo en roja, zhi en verde)
            if pen > 0:
                if s == -1 and cl[k] < zlo + pen * ancho:
                    continue
                if s == 1 and cl[k] > zhi - pen * ancho:
                    continue
            # entrada: STOP desplazado desde el borde lejano hacia adentro
            entry = (zlo + ent * ancho) if s == -1 else (zhi - ent * ancho)
            # UNA ORDEN STOP VA MAS ALLA DEL PRECIO ACTUAL. Si el nivel de entrada
            # queda del otro lado, seria una orden LIMIT y se llenaria a mejor precio
            # que el de mercado -> dinero inventado (daba PF 10.31 y t=29).
            if (s == -1 and cl[k] <= entry) or (s == 1 and cl[k] >= entry):
                continue
            if s_sl is not None:
                base_sl = RSL[k] if s == -1 else GSL[k]
            else:
                base_sl = zhi if s == -1 else zlo
            sl = (base_sl + buffer_pts) if s == -1 else (base_sl - buffer_pts)
            if sl_pts is not None:
                sl = entry - s * (sl_pts + buffer_pts)
            risk = abs(sl - entry)
            if risk <= 0:
                continue
            if tp == "vwap_ayer":
                tgt = VW[k]
            elif tp == "zona_opuesta":
                tgt = GH[k] if s == -1 else RL[k]
            else:
                tgt = entry + s * risk * rr
            if s * (tgt - entry) <= 0:
                continue
            cuenta[clave] = cuenta.get(clave, 0) + 1
            pend = {"dir": s, "entry": entry, "sl": sl, "tp": tgt, "risk": risk,
                    "zona": nom, "senal": tt[k], "rr_impl": abs(tgt - entry) / risk}
            pend_k = k
            break
    return pd.DataFrame(out)
