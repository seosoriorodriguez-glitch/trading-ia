# -*- coding: utf-8 -*-
"""
Logica PURA de la FALSA RUPTURA de pivotes H1 (sin MT5). La usan el bot (bot.py), el backtest (backtest.py) y la
prueba de paridad (herramientas/paridad.py).

Replica la "base" congelada de research/pa_lab/estructura_pa/falsa_ruptura_v2.py (motor_pa.py), nov-2026:
  niveles   pivotes H1 15/15 (los mismos del S/R, niveles.find_levels), activos desde la apertura de la vela i+16.
            Un nivel se puede ROMPER mientras esta entre los 5 ultimos activados (deja de poder romperse cuando se
            activa el 5o nivel siguiente).
  lado      el del precio al activarse: nivel ARRIBA del cierre anterior a la activacion -> la ruptura es hacia
            arriba (+1); si no, hacia abajo (-1).
  ruptura   la PRIMERA vela H1 (abierta desde la activacion, cerrada antes de que el nivel rote) que CIERRA mas alla
            del nivel. Una sola por nivel: si esa orden no se llena, el nivel queda terminado.
  orden     al cierre de esa vela, STOP en CONTRA en nivel + lado x W (ruptura alcista -> VENTA STOP en nivel + 20).
            Vale `vig_h` horas (8). W y BUF en puntos "a precio 47 000", escalados x nivel / 47 000.
            Rotacion: solo cuentan las ultimas `max_ordenes` (5) ordenes por hora de nacimiento (las vencidas tambien
            ocupan lugar), como motor_pa.
  SL espejo distancia de la orden al extremo CONTRARIO de las 4 ultimas velas H1 hasta la de ruptura (el minimo si la
            ruptura es alcista; o el nivel si esta mas lejos) + BUF, puesta del OTRO lado de la orden.
  TP        RR (3) x riesgo desde la orden.
  llenado   solo si el precio esta del lado de afuera: VENTA STOP si el cierre M1 anterior (Bid) > orden; COMPRA STOP si
            cierre anterior + spread < orden. Si no, la orden espera (no se consume).
  usados    una orden se opera UNA vez (queda usada al llenarse).
  bloqueos  los del S/R (sr_pivot_h1.estrategia.bloqueado): fin de semana, noticias 08:26-08:34 ET, corte del viernes
            (que ademas cierra la posicion). 1 posicion a la vez.
Hora: todo en hora SERVIDOR (= Nueva York + 7 h).
"""
from dataclasses import dataclass
from typing import List, Optional, Set

import numpy as np
import pandas as pd

from papel.estrategias.sr_pivot_h1.estrategia import (bloqueado, corte_viernes, en_noticias,  # noqa: F401
                                                      ultimo_corte, ventanas_de_texto, verano_eeuu)
from papel.estrategias.sr_pivot_h1.niveles import find_levels

PREFIJO = "FR "
H = pd.Timedelta(hours=1)


@dataclass(frozen=True)
class OrdenFR:
    clave: str                 # nivel: tipo + hora del pivote ("r2611021700"); una orden por nivel
    lado: str                  # "sell_stop" | "buy_stop"
    precio: float
    sl: float
    tp: float
    nivel: float
    riesgo_pts: float
    desde: pd.Timestamp        # cierre de la vela de ruptura
    hasta: pd.Timestamp        # desde + vig_h
    t_vela: pd.Timestamp       # apertura de la vela de ruptura
    cierre_ruptura: float

    @property
    def comentario(self) -> str:
        return f"{PREFIJO}{self.clave}"

    @property
    def dir(self) -> int:
        return 1 if self.lado == "buy_stop" else -1


def clave_de_comentario(comentario: str) -> Optional[str]:
    c = (comentario or "").strip()
    if c.startswith(PREFIJO) and len(c) >= len(PREFIJO) + 11:
        return c[len(PREFIJO):len(PREFIJO) + 11]
    return None


class EstrategiaFR:
    def __init__(self, W=20.0, vig_h=8.0, buf=20.0, n_ext=4, RR=3.0, max_niveles=5, max_ordenes=5, izq=15, der=15,
                 precio_ref=47000.0, paso_precio: Optional[float] = None):
        self.W, self.vig = float(W), pd.Timedelta(hours=float(vig_h))
        self.buf, self.n_ext, self.RR = float(buf), int(n_ext), float(RR)
        self.max_niveles, self.max_ordenes = int(max_niveles), int(max_ordenes)
        self.izq, self.der, self.precio_ref = int(izq), int(der), float(precio_ref)
        self.paso = paso_precio                 # tick del simbolo (None = sin redondear, como el backtest)

    def _r(self, x: float) -> float:
        if not self.paso:
            return float(x)
        return float(round(round(x / self.paso) * self.paso, 10))

    def ordenes(self, h1: pd.DataFrame) -> List[OrdenFR]:
        """Todas las ordenes nacidas segun las velas H1 dadas (time = apertura, hora servidor). `h1` puede traer al
        final la vela en formacion: para los niveles solo se usa su hora (como en el S/R) y para la ruptura y el SL
        solo cuentan las velas CERRADAS. Ordenadas por nacimiento."""
        if h1 is None or len(h1) < self.izq + self.der + 2:
            return []
        lv = find_levels(h1, self.izq, self.der)
        if not lv:
            return []
        t = h1.time.values
        hh, ll, cc = h1.high.values, h1.low.values, h1.close.values
        n_cerradas = len(h1) - 1                # la ultima fila es la vela en formacion
        act = [np.datetime64(x.activation_time) for x in lv]
        out = []
        for k, x in enumerate(lv):
            j_act = int(np.searchsorted(t, act[k]))           # vela de activacion
            if j_act < 1 or j_act >= len(t):
                continue
            ref = cc[j_act - 1]                                # cierre anterior a la activacion
            L = float(x.price)
            d = 1 if L > ref else -1
            # velas candidatas: abiertas desde la activacion, cerradas, y cerradas antes de que el nivel rote
            fin_j = n_cerradas
            if k + self.max_niveles < len(lv):
                fin_t = act[k + self.max_niveles] - np.timedelta64(1, "h")
                fin_j = min(fin_j, int(np.searchsorted(t, fin_t, side="right")))
            if fin_j <= j_act:
                continue
            seg = cc[j_act:fin_j]
            cruza = np.flatnonzero(seg > L) if d == 1 else np.flatnonzero(seg < L)
            if not len(cruza):
                continue
            j = j_act + int(cruza[0])
            lo = max(0, j - self.n_ext + 1)
            ext = ll[lo:j + 1].min() if d == 1 else hh[lo:j + 1].max()
            kk = L / self.precio_ref
            px = L + d * self.W * kk
            lim = min(ext, L) if d == 1 else max(ext, L)
            r = abs(px - (lim - d * self.buf * kk))
            sl = px + d * r
            tp = px - d * self.RR * r
            clave = ("s" if x.kind == "sup" else "r") + pd.Timestamp(x.pivot_time).strftime("%y%m%d%H%M")
            desde = pd.Timestamp(t[j]) + H
            out.append(OrdenFR(clave, "sell_stop" if d == 1 else "buy_stop", self._r(px), self._r(sl), self._r(tp), L,
                               abs(self._r(px) - self._r(sl)), desde, desde + self.vig, pd.Timestamp(t[j]),
                               float(cc[j])))
        out.sort(key=lambda o: o.desde)       # estable: a igual hora, el orden de los niveles
        return out

    def vigentes(self, ordenes: List[OrdenFR], ahora: pd.Timestamp, usados: Set[str]) -> List[OrdenFR]:
        """Las ultimas `max_ordenes` nacidas hasta ahora (rotacion), no vencidas y no usadas."""
        nacidas = [o for o in ordenes if o.desde <= ahora][-self.max_ordenes:]
        return [o for o in nacidas if ahora < o.hasta and o.clave not in usados]

    @staticmethod
    def deseadas(vigentes: List[OrdenFR], cierre_ant: float, spread: float) -> List[OrdenFR]:
        """Las que deberian estar puestas: el precio esta del lado de afuera (si no, la orden espera)."""
        out = []
        for o in vigentes:
            if o.lado == "sell_stop" and cierre_ant > o.precio:
                out.append(o)
            elif o.lado == "buy_stop" and cierre_ant + spread < o.precio:
                out.append(o)
        return out
