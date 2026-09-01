# -*- coding: utf-8 -*-
"""
Motor fiel abierto a cualquier fuente de zonas. SOLO INVESTIGACION.

QUE ES
  Copia de strategies/order_block/backtest/backtester_limit_orders.py — el motor
  del repo que reproduce la referencia de BACKTEST_SPEC.md y queda a 3% del bot
  real — con un solo cambio: en vez de detectar Order Blocks internamente, recibe
  una LISTA DE ZONAS. Todo lo demas (ciclo de la orden, costos, expiracion,
  destruccion, concurrencia) es identico.

  NO se toca el original ni nada de strategies/. Este archivo es solo lectura
  sobre aquel.

POR QUE EXISTE
  Escribi antes un motor generico desde cero (motor_zonas.py) y no logro
  reproducir el original: sobre 2025 daba +17.3% contra +42.5%, con 726
  operaciones contra 663. La causa principal: yo recalculaba las zonas activas en
  cada vela con un filtro, asi que una zona invalidada RESUCITABA si el precio
  volvia. Aca el estado es permanente, como en el original.
  Leccion: no reescribir motores que ya existen y estan validados.

VALIDADO
  `python research/motor/validar_fiel.py` compara trade a trade contra el
  original. Al 2026-08 coinciden EXACTAMENTE en 2024 (600 ops, -61.1R), 2025
  (663 ops, +85.1R) y 2026 (298 ops, +35.4R): misma hora de entrada, de salida,
  precios, motivo y R. Correrlo despues de tocar este archivo.

USO
    from research.motor.motor_fiel import MotorFiel, Zona
    trades = MotorFiel(params).run(df_m5, df_m1, zonas)
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

import pandas as pd

from strategies.order_block.backtest.risk_manager import calc_pnl, is_session_allowed


# --------------------------------------------------------------------- zona
@dataclass
class Zona:
    """Lo unico que un proveedor debe entregar."""
    desde: datetime           # cuando pasa a ser OPERABLE (ya sin lookahead)
    lo: float
    hi: float
    tipo: str                 # "alcista" (demanda, LONG) | "bajista" (oferta, SHORT)
    origen: str = ""
    # estado interno del motor
    estado: str = "fresca"    # fresca | mitigada | destruida | expirada
    velas: int = 0            # velas del TF mayor desde que se activo

    @property
    def altura(self):
        return self.hi - self.lo


@dataclass
class _Pend:
    direccion: str
    entrada: float
    sl: float
    tp: float
    zona: Zona
    creada: datetime
    sesion: str


@dataclass
class _Trade:
    direccion: str
    entrada: float
    sl_orig: float
    sl: float
    tp: float
    hora: datetime
    zona_hi: float
    zona_lo: float
    origen: str
    sesion: str
    balance: float
    salida: float = 0.0
    hora_salida: Optional[datetime] = None
    motivo: str = ""
    pnl_usd: float = 0.0
    pnl_r: float = 0.0
    pnl_pts: float = 0.0


class MotorFiel:
    """Mismo ciclo que backtester_limit_orders, con zonas inyectadas."""

    def __init__(self, params: dict):
        self.p = params
        self.balance = params["initial_balance"]
        self.balance_inicial = params["initial_balance"]
        self._trades: List[_Trade] = []
        self._abiertos: List[_Trade] = []
        self._pend: List[_Pend] = []

    # ------------------------------------------------------------------ run
    def run(self, df_mayor: pd.DataFrame, df_menor: pd.DataFrame,
            zonas: List[Zona]) -> pd.DataFrame:
        p = self.p
        zonas = sorted(zonas, key=lambda z: z.desde)
        for z in zonas:                       # estado limpio entre corridas
            z.estado, z.velas = "fresca", 0

        filas_may = df_mayor.to_dict("records")
        filas_men = df_menor.to_dict("records")
        n_may = len(filas_may)
        ptr = 0
        zi = 0
        activas: List[Zona] = []
        activadas: List[Zona] = []
        max_act = p["max_active_obs"]

        for fila in filas_men:
            t = fila["time"]
            hi, lo = fila["high"], fila["low"]
            cl = fila["close"]

            # --- 1. avanzar TF mayor: activar, destruir, expirar --------------
            while ptr < n_may and filas_may[ptr]["time"] <= t:
                cierre_may = filas_may[ptr]["close"]
                hora_may = filas_may[ptr]["time"]

                while zi < len(zonas) and zonas[zi].desde <= hora_may:
                    activadas.append(zonas[zi]); zi += 1

                # OJO: el original trunca `active_obs` cada vela, pero como vuelve a
                # recorrer TODOS los OBs con `if ob not in active_obs`, las que
                # quedaron fuera REENTRAN en la vela siguiente. El truncado es
                # temporal, no definitivo. Replicarlo con un puntero que avanza una
                # sola vez daba 538 operaciones en vez de 663.
                activas = activadas
                if len(activas) > max_act:
                    activas = sorted(activas, key=lambda z: z.desde, reverse=True)[:max_act]

                for z in activas:
                    if z.estado != "fresca":
                        continue
                    # destruccion: el cierre del TF mayor deja la zona atras
                    if z.tipo == "alcista" and cierre_may < z.lo:
                        z.estado = "destruida"; self._cancelar(z); continue
                    if z.tipo == "bajista" and cierre_may > z.hi:
                        z.estado = "destruida"; self._cancelar(z); continue
                    z.velas += 1
                    if z.velas >= p["expiry_candles"]:
                        z.estado = "expirada"; self._cancelar(z)
                ptr += 1

            # --- 2. salidas ---------------------------------------------------
            vivos = []
            for tr in self._abiertos:
                if not self._salida(tr, hi, lo, t):
                    vivos.append(tr)
            self._abiertos = vivos

            # --- 3. llenado de pendientes -------------------------------------
            self._llenar(hi, lo, t)

            # --- 4. nueva senal -----------------------------------------------
            if not is_session_allowed(t, p):
                continue
            if len(self._abiertos) + len(self._pend) >= p["max_simultaneous_trades"]:
                continue
            sesion = self._sesion(t)
            if sesion is None:
                continue

            frescas = sorted([z for z in activas if z.estado == "fresca"],
                             key=lambda z: z.desde, reverse=True)
            for z in frescas:
                if any(o.zona is z for o in self._pend):
                    continue
                if not (z.lo <= cl <= z.hi):        # cierre DENTRO de la zona
                    continue
                if z.tipo == "alcista":
                    direccion, entrada = "long", z.hi
                else:
                    direccion, entrada = "short", z.lo
                sl, tp = self._sl_tp(z, entrada)
                if sl is None:
                    continue
                self._pend.append(_Pend(direccion, entrada, sl, tp, z, t, sesion))
                break                               # una orden por vela

        # cerrar lo que quede abierto
        if self._abiertos and filas_men:
            ult = filas_men[-1]
            for tr in list(self._abiertos):
                self._cerrar(tr, ult["close"], ult["time"], "end_of_data")
            self._abiertos = []
        self._pend = []
        return self._resultados()

    # --------------------------------------------------------------- helpers
    def _sl_tp(self, z: Zona, entrada: float):
        p = self.p
        if z.tipo == "alcista":
            sl = z.lo - p["buffer_points"]
        else:
            sl = z.hi + p["buffer_points"]
        riesgo = abs(entrada - sl)
        if riesgo < p["min_risk_points"] or riesgo > p["max_risk_points"]:
            return None, None
        rr = p["target_rr"]
        tp = entrada + riesgo * rr if z.tipo == "alcista" else entrada - riesgo * rr
        return sl, tp

    def _cancelar(self, z: Zona):
        self._pend = [o for o in self._pend if o.zona is not z]

    def _llenar(self, hi, lo, t):
        hechas = []
        for o in self._pend:
            toca = (hi >= o.entrada) if o.direccion == "long" else (lo <= o.entrada)
            if not toca:
                continue
            slip = self.p.get("slippage_points", 0)
            eff = o.entrada + slip if o.direccion == "long" else o.entrada - slip
            self._abiertos.append(_Trade(
                direccion=o.direccion, entrada=eff, sl_orig=o.sl, sl=o.sl, tp=o.tp,
                hora=t, zona_hi=o.zona.hi, zona_lo=o.zona.lo,
                origen=o.zona.origen, sesion=o.sesion, balance=self.balance))
            o.zona.estado = "mitigada"
            hechas.append(o)
        for o in hechas:
            self._pend.remove(o)

    def _salida(self, tr: _Trade, hi, lo, t) -> bool:
        if tr.direccion == "long":
            if lo <= tr.sl:
                self._cerrar(tr, tr.sl, t, "sl"); return True
            if hi >= tr.tp:
                self._cerrar(tr, tr.tp, t, "tp"); return True
        else:
            if hi >= tr.sl:
                self._cerrar(tr, tr.sl, t, "sl"); return True
            if lo <= tr.tp:
                self._cerrar(tr, tr.tp, t, "tp"); return True
        return False

    def _cerrar(self, tr: _Trade, precio, t, motivo):
        slip = self.p.get("slippage_points", 0)
        # slippage solo al salir por SL: el TP es orden limite
        if motivo == "sl" and slip > 0:
            precio = precio - slip if tr.direccion == "long" else precio + slip
        pnl_usd, pnl_r, pnl_pts = calc_pnl(
            entry_price=tr.entrada, exit_price=precio, original_sl=tr.sl_orig,
            entry_price_original=tr.entrada, direction=tr.direccion,
            balance=tr.balance, params=self.p)
        tr.salida, tr.hora_salida, tr.motivo = precio, t, motivo
        tr.pnl_usd, tr.pnl_r, tr.pnl_pts = pnl_usd, pnl_r, pnl_pts
        self.balance += pnl_usd
        self._trades.append(tr)
        # NO tocar self._abiertos aca: el paso 2 de run() itera sobre esa lista y
        # la reconstruye con los que siguen vivos. Si _cerrar hacia remove(), la
        # lista mutaba en medio del for y el elemento siguiente se SALTABA: al
        # cerrarse el trade A, el trade B abierto simultaneamente desaparecia sin
        # registrarse. Costaba 13 operaciones en 2 meses (663 -> 538 en 2025).

    def _sesion(self, t):
        from datetime import timedelta
        for nom, s in self.p["sessions"].items():
            hs, ms = s["start"].split(":")
            he, me = s["end"].split(":")
            ini = t.replace(hour=int(hs), minute=int(ms), second=0, microsecond=0)
            fin = t.replace(hour=int(he), minute=int(me), second=0, microsecond=0)
            if ini + timedelta(minutes=s["skip_minutes"]) <= t < fin:
                return nom
        return None

    def _resultados(self) -> pd.DataFrame:
        if not self._trades:
            return pd.DataFrame()
        filas = [{
            "entry_time": t.hora, "exit_time": t.hora_salida, "direction": t.direccion,
            "entry_price": t.entrada, "sl": t.sl_orig, "tp": t.tp,
            "exit_price": t.salida, "exit_reason": t.motivo,
            "riesgo": round(abs(t.entrada - t.sl_orig), 2),
            "altura": round(t.zona_hi - t.zona_lo, 2),
            "zona_lo": t.zona_lo, "zona_hi": t.zona_hi, "origen": t.origen,
            "pnl_r": round(t.pnl_r, 3), "pnl_usd": round(t.pnl_usd, 2),
            "session": t.sesion,
        } for t in self._trades]
        df = pd.DataFrame(filas)
        run = self.balance_inicial
        bal = []
        for t in self._trades:
            run += t.pnl_usd
            bal.append(round(run, 2))
        df["balance"] = bal
        return df
