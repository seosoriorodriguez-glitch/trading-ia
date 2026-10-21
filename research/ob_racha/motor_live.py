# -*- coding: utf-8 -*-
"""
MotorTF (velas cerradas) + las dos reglas del bot live que el motor no tenia. SOLO INVESTIGACION.

  cupo_live  el limite de 2 cuenta SOLO posiciones abiertas, como risk_manager.can_take_trade
             (open_trades = len(mt5_positions)). Las pendientes no ocupan cupo y una pendiente
             puede llenarse aunque ya haya 2 abiertas (el live no la cancela por cupo).
  noticias   ventana 08:26-08:34 ET (dias habiles): no hay senales nuevas y se cancelan TODAS las
             pendientes (trading_bot._check_news_blackout). La zona no queda mitigada: puede volver
             a dar senal despues de la ventana.

Hora servidor = ET + 7 h (FTMO cambia de horario en las fechas de EE.UU.; 16:30 servidor = apertura NY).
"""
import sys
from pathlib import Path
from typing import List

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "research" / "ob_tf"))

import pandas as pd

from motor_tf import MotorTF
from research.motor.motor_fiel import Zona, _Pend
from strategies.order_block.backtest.risk_manager import is_session_allowed

DESFASE_ET = pd.Timedelta(hours=7)


def en_noticia(t):
    et = t - DESFASE_ET
    m = et.hour * 60 + et.minute
    return et.weekday() < 5 and 8 * 60 + 26 <= m <= 8 * 60 + 34


class MotorLive(MotorTF):
    def __init__(self, params, cupo_live=True, noticias=True):
        super().__init__(params, 5, 1, cerrada=True)
        self.cupo_live = cupo_live
        self.noticias = noticias
        self.max_abiertas = 0

    def run(self, df_mayor: pd.DataFrame, df_menor: pd.DataFrame, zonas: List[Zona]) -> pd.DataFrame:
        p = self.p
        zonas = sorted(zonas, key=lambda z: z.desde)
        for z in zonas:
            z.estado, z.velas = "fresca", 0
        filas_may = df_mayor.to_dict("records")
        filas_men = df_menor.to_dict("records")
        n_may = len(filas_may)
        ptr = zi = 0
        activas: List[Zona] = []
        activadas: List[Zona] = []
        max_act = p["max_active_obs"]

        for fila in filas_men:
            t = fila["time"]
            hi, lo, cl = fila["high"], fila["low"], fila["close"]

            nueva = False
            while zi < len(zonas) and zonas[zi].desde <= t:
                activadas.append(zonas[zi]); zi += 1; nueva = True
            if nueva:
                activas = activadas if len(activadas) <= max_act else \
                    sorted(activadas, key=lambda z: z.desde, reverse=True)[:max_act]

            while ptr < n_may and filas_may[ptr]["time"] + self.tf_mayor <= t:
                cierre_may = filas_may[ptr]["close"]
                activas = activadas
                if len(activas) > max_act:
                    activas = sorted(activas, key=lambda z: z.desde, reverse=True)[:max_act]
                for z in activas:
                    if z.estado != "fresca":
                        continue
                    if z.tipo == "alcista" and cierre_may < z.lo:
                        z.estado = "destruida"; self._cancelar(z); continue
                    if z.tipo == "bajista" and cierre_may > z.hi:
                        z.estado = "destruida"; self._cancelar(z); continue
                    z.velas += 1
                    if z.velas >= p["expiry_candles"]:
                        z.estado = "expirada"; self._cancelar(z)
                ptr += 1

            noticia = self.noticias and en_noticia(t)
            if noticia:
                self._pend = []                      # el live cancela todas las pendientes

            vivos = []
            for tr in self._abiertos:
                if not self._salida(tr, hi, lo, t):
                    vivos.append(tr)
            self._abiertos = vivos

            self._llenar(hi, lo, t)
            self.max_abiertas = max(self.max_abiertas, len(self._abiertos))

            if noticia or not is_session_allowed(t, p):
                continue
            ocupado = len(self._abiertos) if self.cupo_live else len(self._abiertos) + len(self._pend)
            if ocupado >= p["max_simultaneous_trades"]:
                continue
            sesion = self._sesion(t)
            if sesion is None:
                continue
            frescas = sorted([z for z in activas if z.estado == "fresca"], key=lambda z: z.desde, reverse=True)
            for z in frescas:
                if any(o.zona is z for o in self._pend):
                    continue
                if not (z.lo <= cl <= z.hi):
                    continue
                direccion, entrada = ("long", z.hi) if z.tipo == "alcista" else ("short", z.lo)
                sl, tp = self._sl_tp(z, entrada)
                if sl is None:
                    continue
                self._pend.append(_Pend(direccion, entrada, sl, tp, z, t, sesion))
                break

        if self._abiertos and filas_men:
            ult = filas_men[-1]
            for tr in list(self._abiertos):
                self._cerrar(tr, ult["close"], ult["time"], "end_of_data")
            self._abiertos = []
        self._pend = []
        return self._resultados()
