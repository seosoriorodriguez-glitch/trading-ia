# -*- coding: utf-8 -*-
"""
MOTOR GENERICO DE ZONAS — solo investigacion. No toca strategies/ ni el bot live.

IDEA
  La mecanica de entrada de OB London esta validada: 3.297 operaciones, 7 anios,
  y contra 126 trades reales da +0.352R vs +0.363R del live (3% de diferencia).
  Entonces se deja FIJA y se varia una sola cosa: DE DONDE SALEN LAS ZONAS.

  Asi cada concepto (OB, FVG, VWAP, POC/VAH/VAL, breaker, ...) se vuelve un
  "proveedor" enchufable, y todos compiten en igualdad: mismo motor, mismo
  periodo, misma metrica. Solo se compara la calidad de las zonas.

MECANICA (copiada de backtester_limit_orders.py, que es la fiel al live)
  Zona [lo, hi] + tipo:

    ALCISTA (demanda)                  BAJISTA (oferta)
    el precio CAE dentro                el precio SUBE dentro
    ────────────────────────            ────────────────────────
    hi   ← BUY STOP                     hi + buffer  ← SL
    lo                                  hi           ← SELL STOP  (ojo: ver abajo)
    lo - buffer  ← SL                   lo

  Precision:
    alcista: entrada = hi        SL = lo - buffer
    bajista: entrada = lo        SL = hi + buffer
    riesgo  = (hi - lo) + buffer      <- FIJO por zona, no depende de donde cerro
    TP      = entrada +/- riesgo * rr

  La entrada va en el borde POR DONDE EL PRECIO ENTRO. La orden se llena solo si
  el precio vuelve a salir por ahi: eso es el rechazo confirmado.

REGLAS QUE NO SE NEGOCIAN (ver BACKTEST_SPEC.md)
  - Una orden STOP va MAS ALLA del precio actual. Si queda del otro lado seria una
    LIMIT y se llenaria a mejor precio que el de mercado (error #6 del spec).
  - Ejecucion en M1. Con M5 la estrategia se ve perdedora (PF 0.98 vs 1.30).
  - Nada puede usar la vela en curso ni informacion posterior a la barra evaluada.
"""
from dataclasses import dataclass
from typing import List, Optional

import numpy as np
import pandas as pd


@dataclass
class Zona:
    """Una zona de precio operable. Es todo lo que un proveedor debe entregar."""
    desde: np.datetime64      # a partir de cuando es OPERABLE (sin lookahead)
    hasta: np.datetime64      # cuando expira
    lo: float
    hi: float
    tipo: str                 # "alcista" (demanda, se compra) | "bajista" (oferta)
    origen: str = ""          # etiqueta del proveedor, para diagnostico

    @property
    def altura(self) -> float:
        return self.hi - self.lo


PARAMS = dict(
    buffer_pts=35.0,        # separacion del SL respecto al borde lejano
    rr=2.5,                 # take profit como multiplo del riesgo
    min_risk=15.0,          # descarta zonas que dan menos riesgo que esto
    max_risk=300.0,         # y las que dan mas
    # Modelo de costos identico a backtester_limit_orders + calc_pnl del repo:
    #   slippage al entrar (empeora el llenado) y al salir SOLO por SL (el TP es
    #   orden limite y no sufre); el spread se resta de los PUNTOS, no del R.
    spread_pts=2.0,
    slip_pts=2.0,
    cost_pts=0.0,           # legado; si >0 se descuenta del R al viejo estilo
    max_sim=2,              # posiciones simultaneas (el live usa 2)
    sesion=(10, 17),        # hora de servidor; None = 24h
    skip_min=15,            # minutos muertos tras la apertura (is_session_allowed)
    solo_habiles=True,      # lunes a viernes, como is_session_allowed
    expiry_min=0,           # minutos de vida de la pendiente; 0 = hasta que muera la zona
    una_por_zona=True,      # la zona se mitiga al operarla
    # Una zona muere cuando el precio CIERRA del otro lado: la premisa quedo
    # invalidada. Sin esto sobreviven zonas rotas y sobran operaciones.
    #   alcista muere si cierre < lo   |   bajista muere si cierre > hi
    # buffer_frac: si se define, el buffer es una FRACCION de la altura de zona en
    # vez de puntos fijos. Para zonas chicas (FVG mediana 14 pts) un buffer fijo de
    # 35 domina el riesgo y la zona deja de aportar informacion.
    buffer_frac=None,
    invalidar_por_cierre=True,
    # La invalidacion se evalua al cierre del TF de deteccion, no en cada M1: un
    # cierre M1 cruza el borde mucho mas seguido y mata zonas que siguen vivas.
    tf_invalidacion=5,
    max_activas=10,         # zonas vivas simultaneas (OB usa max_active_obs=10)
)


def correr(m1: pd.DataFrame, zonas: List[Zona], p: dict = None) -> pd.DataFrame:
    """Aplica la mecanica de entrada sobre cualquier lista de zonas."""
    q = dict(PARAMS)
    if p:
        q.update(p)

    zonas = sorted(zonas, key=lambda z: z.desde)
    t = m1["time"].values
    hi_, lo_, cl_ = m1["high"].values, m1["low"].values, m1["close"].values
    hh = m1["time"].dt.hour.values
    mn_ = m1["time"].dt.minute.values
    wd_ = m1["time"].dt.dayofweek.values
    n = len(m1)

    activas: List[Zona] = []
    zi = 0
    usadas = set()
    pend = []       # ordenes pendientes
    abiertos = []
    out = []
    bloqueadas = [0]

    for k in range(n):
        ahora = t[k]

        while zi < len(zonas) and zonas[zi].desde <= ahora:
            activas.append(zonas[zi]); zi += 1
        activas = [z for z in activas if z.hasta >= ahora]
        tfi = q.get("tf_invalidacion", 1)
        if q["invalidar_por_cierre"] and (tfi <= 1 or mn_[k] % tfi == tfi - 1):
            activas = [z for z in activas
                       if not ((z.tipo == "alcista" and cl_[k] < z.lo) or
                               (z.tipo == "bajista" and cl_[k] > z.hi))]
        if q["max_activas"] and len(activas) > q["max_activas"]:
            activas = activas[-q["max_activas"]:]      # las mas recientes
        vivas = {id(z) for z in activas}

        # --- salidas -------------------------------------------------------
        for o in list(abiertos):
            s = o["dir"]
            toca_sl = (lo_[k] <= o["sl"]) if s == 1 else (hi_[k] >= o["sl"])
            toca_tp = (hi_[k] >= o["tp"]) if s == 1 else (lo_[k] <= o["tp"])
            if toca_sl:
                salida = o["sl"] - s * q["slip_pts"]      # SL sufre slippage
            elif toca_tp:
                salida = o["tp"]                          # TP es limite: no sufre
            else:
                continue
            pts = (salida - o["entrada_ef"]) * s - q["spread_pts"]
            o["r"] = pts / o["riesgo"] - (q["cost_pts"] / o["riesgo"] if q["cost_pts"] else 0.0)
            o["salida"] = ahora
            out.append(o); abiertos.remove(o)

        # --- pendientes: cancelar o llenar ---------------------------------
        for o in list(pend):
            if id(o["zona"]) not in vivas:
                pend.remove(o); continue      # la zona murio -> se cancela
            if q["expiry_min"] and (k - o["k0"]) >= q["expiry_min"]:
                pend.remove(o); continue
            if len(abiertos) >= q["max_sim"]:
                continue
            s = o["dir"]
            lleno = (hi_[k] >= o["entrada"]) if s == 1 else (lo_[k] <= o["entrada"])
            if lleno:
                o["hora"] = ahora
                # slippage de entrada: el llenado siempre es peor que el nivel
                o["entrada_ef"] = o["entrada"] + s * q["slip_pts"]
                abiertos.append(o); pend.remove(o)

        # --- nueva senal ---------------------------------------------------
        if q.get("solo_habiles") and wd_[k] >= 5:
            continue
        if q["sesion"]:
            ini = q["sesion"][0] * 60 + q.get("skip_min", 0)
            fin_s = q["sesion"][1] * 60
            if not (ini <= hh[k] * 60 + mn_[k] < fin_s):
                continue
        if len(abiertos) + len(pend) >= q["max_sim"]:
            # habia zona con el precio dentro pero no habia cupo -> senal perdida
            for z in activas:
                if (not (q["una_por_zona"] and id(z) in usadas)) and z.lo <= cl_[k] <= z.hi:
                    bloqueadas[0] += 1
                    break
            continue

        # el motor fiel evalua de mas RECIENTE a mas antigua
        for z in sorted(activas, key=lambda x: x.desde, reverse=True):
            if q["una_por_zona"] and id(z) in usadas:
                continue
            if any(o["zona"] is z for o in pend):
                continue
            if not (z.lo <= cl_[k] <= z.hi):          # cierre DENTRO, ambos lados
                continue

            s = 1 if z.tipo == "alcista" else -1
            entrada = z.hi if s == 1 else z.lo
            buf = (z.altura * q["buffer_frac"]) if q.get("buffer_frac") else q["buffer_pts"]
            sl = (z.lo - buf) if s == 1 else (z.hi + buf)
            riesgo = abs(entrada - sl)
            if not (q["min_risk"] <= riesgo <= q["max_risk"]):
                continue
            # una STOP va mas alla del precio actual (error #6 del spec)
            if (s == 1 and cl_[k] >= entrada) or (s == -1 and cl_[k] <= entrada):
                continue

            pend.append({"zona": z, "dir": s, "entrada": entrada, "sl": sl,
                         "tp": entrada + s * riesgo * q["rr"], "riesgo": riesgo,
                         "origen": z.origen, "senal": ahora, "k0": k,
                         "altura": z.altura})
            usadas.add(id(z))
            break

    df = pd.DataFrame(out)
    df.attrs['bloqueadas'] = bloqueadas[0]
    return df


def resumen(df: pd.DataFrame, etiqueta: str, dias: int,
            riesgo_pct: float = 0.005, balance: float = 10_000.0) -> Optional[dict]:
    import math
    if df is None or len(df) == 0:
        print(f"{etiqueta:34s} sin operaciones")
        return None
    r = df["r"].values
    w, l = r[r > 0], r[r <= 0]
    pf = w.sum() / abs(l.sum()) if len(l) and l.sum() != 0 else float("inf")
    eq = pk = mdd = 0.0
    for v in r:
        eq += v; pk = max(pk, eq); mdd = min(mdd, eq - pk)
    se = r.std(ddof=1) / math.sqrt(len(r)) if len(r) > 1 else float("nan")
    meses = dias / 21
    print(f"{etiqueta:34s} n={len(r):4d} ({len(r)/dias:4.2f}/dia) WR={len(w)/len(r)*100:5.1f}% "
          f"PF={pf:5.2f} {r.sum()*riesgo_pct*100:+6.1f}% ({r.sum()*riesgo_pct*100/meses:+5.2f}%/mes) "
          f"DD={abs(mdd)*riesgo_pct*100:5.1f}% t={r.mean()/se:+5.2f}")
    return {"n": len(r), "pf": pf, "sumaR": r.sum(), "t": r.mean() / se}
