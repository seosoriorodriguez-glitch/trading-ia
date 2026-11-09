# -*- coding: utf-8 -*-
"""
Logica PURA de S/R Pivot al toque H1 (sin MT5). La usan el bot (bot.py) y la prueba de paridad (herramientas/paridad.py).

Replica research/pa_lab/repaso/motor_toque2.py con solo_limit=True y escala=True, config elegida nov-2026:
  niveles   pivotes H1 15/15 (niveles.find_levels), operables desde la apertura de la vela i+16.
  activos   los ultimos `max_niveles` (5) activados; un nivel nuevo saca al mas antiguo (usado o no).
  orden     soporte -> BUY LIMIT en nivel + W ; resistencia -> SELL LIMIT en nivel - W.
            W y S en puntos "a precio 47 000", escalados con el precio del nivel (x nivel / 47 000).
            Solo si el precio esta del lado de afuera: cierre M1 anterior (Bid) + spread > orden en la compra,
            cierre M1 anterior < orden en la venta. Si no, no hay orden y el nivel NO se consume.
  SL / TP   SL = nivel -/+ S ; riesgo = |orden - SL| ; TP = orden +/- RR x riesgo.
  usados    un nivel se opera UNA vez: queda usado cuando su orden se llena.
  bloqueos  sin entradas sabado/domingo, en la ventana de noticias 08:26-08:34 ET ni desde el corte del viernes
            (19:00 UTC = 22:00 servidor con horario de verano de EE.UU., 21:00 sin), que ademas cierra la posicion.
  1 posicion a la vez: con una posicion abierta no hay ordenes pendientes.
Hora: todo en hora SERVIDOR (FTMO y Darwinex = Nueva York + 7 h, verificado).
"""
from dataclasses import dataclass
from typing import List, Optional, Sequence, Set, Tuple

import numpy as np
import pandas as pd

from .niveles import find_levels

SERVIDOR_MENOS_ET = pd.Timedelta(hours=7)


@dataclass(frozen=True)
class Nivel:
    clave: str                 # tipo + hora del pivote, p.ej. "s2512301200": estable entre reinicios
    tipo: str                  # "sup" | "res"
    precio: float
    activo_desde: pd.Timestamp
    pivote: pd.Timestamp


@dataclass(frozen=True)
class Orden:
    clave: str
    lado: str                  # "buy_limit" | "sell_limit"
    precio: float
    sl: float
    tp: float
    nivel: float
    riesgo_pts: float

    @property
    def comentario(self) -> str:
        return f"SR {self.clave}"


def clave_de_comentario(comentario: str) -> Optional[str]:
    c = (comentario or "").strip()
    if c.startswith("SR ") and len(c) >= 14:
        return c[3:14]
    return None


# ---------------------------------------------------------------------------------------------- horarios
def verano_eeuu(t: pd.Timestamp) -> bool:
    mar1 = pd.Timestamp(t.year, 3, 1)
    nov1 = pd.Timestamp(t.year, 11, 1)
    ini = mar1 + pd.Timedelta(days=(6 - mar1.weekday()) % 7 + 7)
    fin = nov1 + pd.Timedelta(days=(6 - nov1.weekday()) % 7)
    return ini <= t.normalize() < fin


def en_noticias(ahora: pd.Timestamp, ventanas: Sequence[Tuple[int, int]]) -> bool:
    et = ahora - SERVIDOR_MENOS_ET
    if et.weekday() >= 5:
        return False
    m = et.hour * 60 + et.minute
    return any(a <= m <= b for a, b in ventanas)


def corte_viernes(ahora: pd.Timestamp) -> bool:
    return ahora.weekday() == 4 and ahora.hour >= (22 if verano_eeuu(ahora) else 21)


def bloqueado(ahora: pd.Timestamp, ventanas: Sequence[Tuple[int, int]]) -> bool:
    return ahora.weekday() >= 5 or en_noticias(ahora, ventanas) or corte_viernes(ahora)


def ventanas_de_texto(textos: Sequence[str]) -> List[Tuple[int, int]]:
    out = []
    for w in textos:
        a, b = w.split("-")
        out.append((int(a[:2]) * 60 + int(a[3:5]), int(b[:2]) * 60 + int(b[3:5])))
    return out


# ---------------------------------------------------------------------------------------------- estrategia
class EstrategiaSR:
    def __init__(self, W=20.0, S=130.0, RR=2.5, max_niveles=5, izq=15, der=15, precio_ref=47000.0,
                 paso_precio: Optional[float] = None):
        self.W, self.S, self.RR = float(W), float(S), float(RR)
        self.max_niveles, self.izq, self.der = int(max_niveles), int(izq), int(der)
        self.precio_ref = float(precio_ref)
        self.paso = paso_precio            # tamano de tick del simbolo (None = sin redondear, como el backtest)

    def _r(self, x: float) -> float:
        if not self.paso:
            return float(x)
        return float(round(round(x / self.paso) * self.paso, 10))

    def niveles(self, h1: pd.DataFrame) -> List[Nivel]:
        """h1: velas H1 (time = apertura, hora servidor); puede incluir la vela en formacion al final."""
        out = []
        for lv in find_levels(h1, self.izq, self.der):
            piv = pd.Timestamp(lv.pivot_time)
            clave = ("s" if lv.kind == "sup" else "r") + piv.strftime("%y%m%d%H%M")
            out.append(Nivel(clave, lv.kind, lv.price, pd.Timestamp(lv.activation_time), piv))
        return out

    def activos(self, niveles: List[Nivel], ahora: pd.Timestamp) -> List[Nivel]:
        ya = [n for n in niveles if n.activo_desde <= ahora]
        return ya[-self.max_niveles:]

    def orden(self, n: Nivel) -> Orden:
        k = n.precio / self.precio_ref
        d = 1 if n.tipo == "sup" else -1
        precio = self._r(n.precio + d * self.W * k)
        sl = self._r(n.precio - d * self.S * k)
        riesgo = abs(precio - sl)
        tp = self._r(precio + d * riesgo * self.RR)
        return Orden(n.clave, "buy_limit" if d == 1 else "sell_limit", precio, sl, tp, n.precio, riesgo)

    def deseadas(self, activos: List[Nivel], usados: Set[str], cierre_ant: float, spread: float) -> List[Orden]:
        """Ordenes LIMIT que deberian estar puestas ahora (sin posicion abierta y sin bloqueo)."""
        out = []
        for n in activos:
            if n.clave in usados:
                continue
            o = self.orden(n)
            if o.lado == "buy_limit" and cierre_ant + spread > o.precio:
                out.append(o)
            elif o.lado == "sell_limit" and cierre_ant < o.precio:
                out.append(o)
        return out


def r_de_trade(lado: str, entrada: float, salida: float, sl_nominal_riesgo: float) -> float:
    d = 1 if lado in ("buy_limit", "long") else -1
    return d * (salida - entrada) / sl_nominal_riesgo if sl_nominal_riesgo else np.nan
