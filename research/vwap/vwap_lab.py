# -*- coding: utf-8 -*-
"""
Laboratorio VWAP — SOLO INVESTIGACION. No toca nada de strategies/ ni del bot live.

Contiene:
  - load_with_volume(): loader propio que CONSERVA tickvol (el de sr_pivot lo descarta)
  - session_vwap():     VWAP anclado a la apertura de sesion, con bandas
  - filtro_vwap():      evalua VWAP como filtro sobre trades de OB London ya generados
  - VWAPReversion:      estrategia independiente de reversion a bandas

AVISO SOBRE LOS DATOS
  En los CSV de MT5 el campo <VOL> es 0: no hay volumen real, solo <TICKVOL>
  (conteo de actualizaciones de precio). Para un CFD de indice no existe volumen
  centralizado. Eso significa que este VWAP NO es el benchmark institucional
  real, es un promedio ponderado por actividad. El mecanismo causal se debilita.
  Para preservarlo habria que usar volumen del futuro YM.

LOOKAHEAD
  El VWAP en la barra k se calcula acumulando hasta k. Para decidir DURANTE la
  barra k solo se conoce hasta k-1. `shift=True` (default) aplica ese desfase.
  Es exactamente el bug que mato al filtro EMA: comparar contra la vela en curso
  daba t=+6.35 y PASO la validacion out-of-sample, porque el error estaba en las
  dos mitades. Siempre correr ambos y comparar.
"""
import numpy as np
import pandas as pd


# --------------------------------------------------------------------- datos
def load_with_volume(path: str) -> pd.DataFrame:
    """Como el loader de sr_pivot pero conservando tickvol."""
    d = pd.read_csv(path, sep="\t")
    d.columns = [c.strip("<>").lower() for c in d.columns]
    d["time"] = pd.to_datetime(d["date"] + " " + d["time"], format="%Y.%m.%d %H:%M:%S")
    vol = "tickvol" if "tickvol" in d.columns else "vol"
    d = d[["time", "open", "high", "low", "close", vol]].rename(columns={vol: "volume"})
    return d.sort_values("time").reset_index(drop=True)


# ---------------------------------------------------------------------- vwap
def session_vwap(df: pd.DataFrame, anchor_hour: int = 10, shift: bool = True,
                 n_sigma=(1.0, 2.0, 3.0)) -> pd.DataFrame:
    """
    VWAP anclado a `anchor_hour` (hora de servidor), reseteando cada dia.

    anchor_hour=10 -> apertura de Londres, que es el anclaje con sentido para
    una estrategia de sesion londinense. El VWAP diario desde medianoche mezcla
    horas sin flujo institucional.

    Devuelve columnas: vwap, sigma, y las bandas up_N / dn_N.
    Con shift=True cada valor usa solo informacion hasta la barra ANTERIOR.
    """
    out = df.copy()
    tp = (out.high + out.low + out.close) / 3.0          # precio tipico
    v = out.volume.astype(float).clip(lower=1e-9)

    # id de sesion: cambia al cruzar anchor_hour
    h = out.time.dt.hour
    nueva = (h == anchor_hour) & (h.shift(1) != anchor_hour)
    ses = nueva.cumsum()
    out["_ses"] = ses

    pv = (tp * v).groupby(ses).cumsum()
    vv = v.groupby(ses).cumsum()
    vwap = pv / vv

    # desviacion ponderada acumulada
    pv2 = ((tp ** 2) * v).groupby(ses).cumsum()
    var = (pv2 / vv) - vwap ** 2
    sigma = np.sqrt(var.clip(lower=0))

    if shift:
        vwap = vwap.groupby(ses).shift(1)
        sigma = sigma.groupby(ses).shift(1)

    out["vwap"] = vwap
    out["sigma"] = sigma
    for n in n_sigma:
        out[f"up_{n}"] = vwap + n * sigma
        out[f"dn_{n}"] = vwap - n * sigma
    return out


# ------------------------------------------------- A) VWAP como filtro de OB
def filtro_vwap(trades: pd.DataFrame, m1v: pd.DataFrame, anchor_hour: int = 10,
                shift: bool = True) -> pd.DataFrame:
    """
    Anota cada trade de OB con su posicion relativa al VWAP en el momento de entrada.
    NO re-simula: es un screening rapido. Si algo promete, hay que implementarlo
    dentro del motor (quitar trades libera cupo de concurrencia y eso cambia el set).
    """
    vw = session_vwap(m1v, anchor_hour, shift)[["time", "vwap", "sigma"]]
    t = trades.copy()
    t["entry_time"] = pd.to_datetime(t["entry_time"])
    t = pd.merge_asof(t.sort_values("entry_time"), vw.sort_values("time"),
                      left_on="entry_time", right_on="time", direction="backward")
    t["dist"] = t.entry_price - t.vwap
    t["dist_sig"] = t["dist"] / t.sigma.replace(0, np.nan)
    t["sobre_vwap"] = t["dist"] > 0
    # a favor = long sobre VWAP o short bajo VWAP (continuacion)
    t["a_favor"] = ((t.direction == "long") & t.sobre_vwap) | \
                   ((t.direction == "short") & ~t.sobre_vwap)
    return t


# --------------------------------------- B) estrategia: reversion a las bandas
class VWAPReversion:
    """
    Estrategia independiente. Precio se aleja N sigmas del VWAP de sesion ->
    se opera HACIA el VWAP. Es el juego institucional clasico de reversion.

    Disparador completamente distinto al de OB, asi que deberia ser poco
    correlacionada — que es donde estuvo el valor al sumar NASDAQ (rho 0.096).
    """

    def __init__(self, entrada_sigma=2.0, sl_sigma=3.0, tp="vwap",
                 anchor_hour=10, sesion=(10, 17), cost_pts=4.0,
                 max_sim=1, shift=True, min_barras=30, min_risk_pts=15.0,
                 trigger="fuera"):
        self.e, self.slg, self.tp = entrada_sigma, sl_sigma, tp
        self.anchor, self.sesion = anchor_hour, sesion
        self.cost, self.max_sim, self.shift = cost_pts, max_sim, shift
        # BUG CORREGIDO: al inicio de sesion sigma se calcula con 1-2 barras y vale
        # casi cero. Las bandas colapsan sobre el VWAP, el precio queda "fuera"
        # trivialmente y risk -> 0, con lo que R explota (daba PF 143 y +1.6M%).
        # min_barras exige acumulacion antes de operar; min_risk_pts es la red final.
        self.min_barras = min_barras
        self.min_risk = min_risk_pts
        self.trigger = trigger

    def run(self, m1v: pd.DataFrame) -> pd.DataFrame:
        d = session_vwap(m1v, self.anchor, self.shift, n_sigma=(self.e, self.slg))
        d = d.dropna(subset=["vwap", "sigma"]).reset_index(drop=True)
        # barras transcurridas dentro de la sesion (para exigir acumulacion)
        nbar = d.groupby("_ses").cumcount().values
        hh = d.time.dt.hour.values
        hi, lo, cl = d.high.values, d.low.values, d.close.values
        vw, sg, tt = d.vwap.values, d.sigma.values, d.time.values
        up = vw + self.e * sg
        dn = vw - self.e * sg

        abiertos = []
        out = []
        for k in range(len(d)):
            # salidas
            vivos = []
            for tr in abiertos:
                s = tr["dir"]
                sl_hit = (lo[k] <= tr["sl"]) if s == 1 else (hi[k] >= tr["sl"])
                tp_now = vw[k] if self.tp == "vwap" else tr["tp"]
                tp_hit = (hi[k] >= tp_now) if s == 1 else (lo[k] <= tp_now)
                if sl_hit:
                    r = -1.0 - self.cost / tr["risk"]
                elif tp_hit:
                    r = abs(tp_now - tr["entry"]) / tr["risk"] - self.cost / tr["risk"]
                else:
                    vivos.append(tr); continue
                tr.update(r=r, exit_time=tt[k]); out.append(tr)
            abiertos = vivos

            if not (self.sesion[0] <= hh[k] < self.sesion[1]):
                continue
            if len(abiertos) >= self.max_sim:
                continue
            if nbar[k] < self.min_barras or sg[k] <= 0:
                continue          # sin acumulacion suficiente, sigma no es fiable

            # DISPARADOR
            #  "fuera"     : cierra fuera de la banda (fade de extension, ingenuo)
            #  "reentrada" : ESTUVO fuera y vuelve a cerrar dentro -> rechazo
            #                Es el juego real: no operar porque este extendido,
            #                sino porque el intento de extension fallo.
            if self.trigger == "reentrada":
                if k == 0:
                    continue
                fuera_up = cl[k - 1] >= up[k - 1]
                fuera_dn = cl[k - 1] <= dn[k - 1]
                if fuera_up and cl[k] < up[k]:
                    sl = max(hi[k], hi[k - 1]) + 0.25 * sg[k]
                    risk = abs(sl - cl[k])
                    if risk >= self.min_risk:
                        abiertos.append({"entry_time": tt[k], "dir": -1, "entry": cl[k],
                                         "sl": sl, "tp": vw[k], "risk": risk,
                                         "sigmas": (cl[k] - vw[k]) / sg[k]})
                elif fuera_dn and cl[k] > dn[k]:
                    sl = min(lo[k], lo[k - 1]) - 0.25 * sg[k]
                    risk = abs(cl[k] - sl)
                    if risk >= self.min_risk:
                        abiertos.append({"entry_time": tt[k], "dir": 1, "entry": cl[k],
                                         "sl": sl, "tp": vw[k], "risk": risk,
                                         "sigmas": (cl[k] - vw[k]) / sg[k]})
                continue

            # entradas: cierre fuera de la banda -> operar hacia el VWAP
            if cl[k] >= up[k]:
                sl = vw[k] + self.slg * sg[k]
                risk = abs(sl - cl[k])
                if risk >= self.min_risk:
                    abiertos.append({"entry_time": tt[k], "dir": -1, "entry": cl[k],
                                     "sl": sl, "tp": vw[k], "risk": risk,
                                     "sigmas": (cl[k] - vw[k]) / sg[k]})
            elif cl[k] <= dn[k]:
                sl = vw[k] - self.slg * sg[k]
                risk = abs(cl[k] - sl)
                if risk >= self.min_risk:
                    abiertos.append({"entry_time": tt[k], "dir": 1, "entry": cl[k],
                                     "sl": sl, "tp": vw[k], "risk": risk,
                                     "sigmas": (cl[k] - vw[k]) / sg[k]})
        return pd.DataFrame(out)


# ------------------------------------------------------------------ metricas
def resumen(df: pd.DataFrame, lab: str, dias: float, riesgo=0.005, bal=10_000.0):
    import math
    if df is None or len(df) == 0:
        print(f"{lab:36s} sin operaciones"); return None
    r = df["r"].values
    w, l = r[r > 0], r[r <= 0]
    pf = w.sum() / abs(l.sum()) if len(l) and l.sum() != 0 else 99.0
    eq = pk = mdd = 0.0
    for v in r:
        eq += v; pk = max(pk, eq); mdd = min(mdd, eq - pk)
    se = r.std(ddof=1) / math.sqrt(len(r)) if len(r) > 1 else float("nan")
    meses = dias / 21
    print(f"{lab:36s} n={len(r):4d} ({len(r)/dias:4.2f}/dia) WR={len(w)/len(r)*100:5.1f}% "
          f"PF={pf:5.2f} sumaR={r.sum():+7.1f} {r.sum()*riesgo*100:+6.1f}% "
          f"({r.sum()*riesgo*100/meses:+5.2f}%/mes) DD={abs(mdd)*riesgo*100:5.1f}% t={r.mean()/se:+5.2f}")
    return {"n": len(r), "pf": pf, "sumaR": r.sum(), "t": r.mean() / se}
