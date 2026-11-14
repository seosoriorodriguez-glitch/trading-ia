# -*- coding: utf-8 -*-
"""
SIMULACRO del bot de la falsa ruptura en MODO REAL (bot.py con papel=False) contra un MT5 FALSO alimentado con velas M1
historicas. No conecta a ningun MT5. Copia del simulacro del S/R, con ordenes STOP que vencen a las 8 h.

Prueba lo que la paridad no cubre: que el bot ponga y cancele las STOP, entre a mercado si el precio ya paso la orden,
detecte llenados por el comentario, no repita ordenes (usadas), cancele por noticias y fin de semana, cierre el viernes
y registre los trades. El MT5 falso llena y cierra con las reglas del backtest (backtest.py: velas Bid, Ask = Bid + 2.1,
desliz STOP 0.5, desliz SL 0.7, SL antes que TP, el TP no se mira en la vela de entrada). El bot "despierta" una vez por
minuto, al abrir cada vela M1.

    python papel/estrategias/falsa_ruptura_h1/herramientas/simulacro.py                    # 2026-01-01 a 2026-11-01
    python papel/estrategias/falsa_ruptura_h1/herramientas/simulacro.py 2025-01-01 2026-01-01 --todas

--todas: el MT5 falso llena TODAS las STOP que cruza una vela, como el MT5 real en un gap (el backtest llena una sola,
la mas cercana a la apertura). El bot debe quedarse con la del backtest, cerrar las demas en el minuto siguiente
("sobra") y dejar sus ordenes sin usar: el resto de los trades tiene que salir identico.
"""
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

RAIZ = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "research" / "pa_lab"))

import numpy as np
import pandas as pd

from datos import m1_periodo, tf
from papel.estrategias.falsa_ruptura_h1.backtest import simular
from papel.estrategias.falsa_ruptura_h1.bot import BotFR
from papel.estrategias.falsa_ruptura_h1.estrategia import EstrategiaFR, clave_de_comentario
from papel.estrategias.sr_pivot_h1.estrategia import corte_viernes
from papel.registro import DEF_FR

SPREAD, DESLIZ_SL, DESLIZ_STOP = 2.1, 0.7, 0.5


class MT5Falso:
    def __init__(self, m1, todas=False):
        self.todas = todas
        self.m1 = m1.reset_index(drop=True)
        self.t = self.m1.time.values
        self.o, self.h, self.l, self.c = (self.m1[k].values.astype(float) for k in ("open", "high", "low", "close"))
        self.h1 = tf(self.m1, 60)
        self.h1t = self.h1.time.values
        self.i = 1
        self.magic, self.simbolo = 345691, "US30.cash"
        self.info = SimpleNamespace(digits=2, point=0.01, trade_tick_size=0.01, volume_min=0.01, volume_step=0.01,
                                    volume_max=100.0, trade_stops_level=0)
        self.pend, self.pos, self.hist = {}, {}, {}
        self.n = 1000
        self.trades = []

    # interfaz de BrokerMT5FR ------------------------------------------------------------------------------
    def conectar(self):
        return True, "ok"

    def desconectar(self):
        pass

    def cuenta(self):
        return {"login": 0, "server": "falso", "balance": 100000.0, "equity": 100000.0, "margen_libre": 1e9,
                "moneda": "USD", "apalancamiento": 100}

    def valor_punto_mt5(self):
        return 1.0

    def valor_punto(self):
        return 1.0

    def ahora(self):
        return pd.Timestamp(self.t[self.i])

    def tick(self):
        return {"bid": self.o[self.i], "ask": self.o[self.i] + SPREAD, "hora": self.ahora()}

    def velas(self, tf_, n):
        if tf_ == "M1":
            d = self.m1.iloc[max(0, self.i - n + 1):self.i + 1].copy()
            d.iloc[-1, d.columns.get_loc("close")] = self.o[self.i]       # vela en formacion: solo su apertura
            return d.assign(spread=210)
        k = int(np.searchsorted(self.h1t, np.datetime64(self.ahora().floor("h")), side="right"))
        return self.h1.iloc[max(0, k - n):k].assign(spread=210)

    def posiciones(self):
        return list(self.pos.values())

    def pendientes(self):
        return list(self.pend.values())

    def volumen(self, riesgo, pts):
        return round(max(0.01, riesgo / pts), 2)

    def orden_valida(self, o, bid, ask):
        return o.precio < bid if o.lado == "sell_stop" else o.precio > ask

    def margen_ok(self, o, v):
        return True, 0.0

    def poner_orden(self, o, vol, vence=None):
        self.n += 1
        self.pend[self.n] = SimpleNamespace(ticket=self.n, comment=o.comentario, lado=o.lado, price_open=o.precio,
                                            sl=o.sl, tp=o.tp, volume=vol, hasta=pd.Timestamp(o.hasta))
        return True, f"ticket {self.n}"

    def cancelar(self, ticket):
        self.pend.pop(ticket, None)
        return True, "ok"

    def _nueva(self, x_lado, comment, sl, tp, ent, vol, orden, k=0, extra=False):
        self.n += 1
        p = SimpleNamespace(identifier=self.n, ticket=self.n, type=0 if x_lado == "buy_stop" else 1, comment=comment,
                            sl=sl, tp=tp, price_open=ent, volume=vol,
                            time_msc=int(self.ahora().value // 10 ** 6) + k, t=self.ahora(), i=self.i, orden=orden,
                            extra=extra)
        self.pos[p.identifier] = p
        return p

    def abrir_mercado(self, o, vol):
        # el backtest la llena en la apertura con el desliz de la STOP
        ent = self.o[self.i] + SPREAD + DESLIZ_STOP if o.lado == "buy_stop" else self.o[self.i] - DESLIZ_STOP
        self._nueva(o.lado, o.comentario, o.sl, o.tp, ent, vol, o.precio)
        return True, f"a mercado {ent}"

    def cerrar(self, p):
        precio = self.o[self.i] if p.type == 0 else self.o[self.i] + SPREAD
        self._salir(p, precio, "viernes" if corte_viernes(self.ahora(), False) else "sobra")
        return True, f"cerrada a {precio}"

    def claves_usadas(self, dias=None, excluir=(), mapa=None):
        return {clave_de_comentario(x["comentario_entrada"]) for k, x in self.hist.items() if k not in excluir}

    def cerradas_recientes(self, dias=10):
        return set(self.hist)

    def resumen_posicion(self, pid):
        return self.hist.get(pid)

    # mercado -----------------------------------------------------------------------------------------------
    def _salir(self, p, precio, motivo):
        self.pos.pop(p.identifier, None)
        d = 1 if p.type == 0 else -1
        self.hist[p.identifier] = {"entrada_hora": p.t, "salida_hora": self.ahora(),
                                   "lado": "long" if d == 1 else "short", "volumen": p.volume,
                                   "entrada": p.price_open, "salida": precio, "comentario_entrada": p.comment,
                                   "comentario_salida": motivo, "profit": d * (precio - p.price_open) * p.volume,
                                   "sl": p.sl, "tp": p.tp, "orden": p.orden, "comision": 0.0, "swap": 0.0}
        self.trades.append(dict(entry_time=p.t, exit_time=self.ahora(), direction="long" if d == 1 else "short",
                                orden=p.orden, entry_price=p.price_open, sl=p.sl, tp=p.tp, exit_price=precio,
                                exit_reason=motivo, R=d * (precio - p.price_open) / abs(p.orden - p.sl),
                                clave=clave_de_comentario(p.comment), extra=p.extra))

    def procesar_vela(self):
        """Lo que pasa DENTRO de la vela i despues de que el bot actuo al abrirla."""
        i, o, h, l = self.i, self.o[self.i], self.h[self.i], self.l[self.i]
        for p in list(self.pos.values()):
            if p.i == i:
                # abierta a mercado al abrir esta vela: solo el SL (el backtest no mira el TP en la vela de entrada)
                if (p.type == 0 and l <= p.sl) or (p.type == 1 and h + SPREAD >= p.sl):
                    self._salir(p, p.sl - DESLIZ_SL if p.type == 0 else p.sl + DESLIZ_SL, "sl")
                continue
            if p.type == 0:
                if l <= p.sl:
                    self._salir(p, o if o <= p.sl else p.sl - DESLIZ_SL, "sl")
                elif h >= p.tp and p.i < i:
                    self._salir(p, o if o >= p.tp else p.tp, "tp")
            else:
                if h + SPREAD >= p.sl:
                    self._salir(p, o + SPREAD if o + SPREAD >= p.sl else p.sl + DESLIZ_SL, "sl")
                elif l + SPREAD <= p.tp and p.i < i:
                    self._salir(p, o + SPREAD if o + SPREAD <= p.tp else p.tp, "tp")
        ahora = self.ahora()
        for k in [k for k, x in self.pend.items() if ahora >= x.hasta]:      # vencidas (el servidor las borra)
            self.pend.pop(k)
        if self.pos:
            return
        cand = []
        for x in self.pend.values():
            if x.lado == "sell_stop" and l <= x.price_open:
                cand.append((abs(o - x.price_open), x, min(x.price_open, o) - DESLIZ_STOP))
            elif x.lado == "buy_stop" and h + SPREAD >= x.price_open:
                cand.append((abs(o + SPREAD - x.price_open), x, max(x.price_open, o + SPREAD) + DESLIZ_STOP))
        if not cand:
            return
        cand.sort(key=lambda z: z[0])                  # el primero es el del backtest (el mas cercano a la apertura)
        for k, (_, x, ent) in enumerate(cand if self.todas else cand[:1]):
            self.pend.pop(x.ticket)
            p = self._nueva(x.lado, x.comment, x.sl, x.tp, ent, x.volume, x.price_open, k=k, extra=k > 0)
            if (p.type == 0 and ent <= p.sl) or (p.type == 1 and ent >= p.sl):
                self._salir(p, o if p.type == 0 else o + SPREAD, "sl_hueco")
            elif (p.type == 0 and l <= p.sl) or (p.type == 1 and h + SPREAD >= p.sl):
                self._salir(p, p.sl - DESLIZ_SL if p.type == 0 else p.sl + DESLIZ_SL, "sl")


def main():
    todas = "--todas" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    ini = pd.Timestamp(args[0] if len(args) > 0 else "2026-01-01")
    fin = pd.Timestamp(args[1] if len(args) > 1 else "2026-11-01")
    m1 = m1_periodo(ini, fin, margen_dias=40)[["time", "open", "high", "low", "close"]].reset_index(drop=True)
    cfg = {"cuenta": {"balance_esperado": 100000, "riesgo_pct": 0.005, "riesgo_fijo": 500},
           "mt5": {"terminal": None, "simbolo": "US30.cash", "magic": 345691, "llenado": "return",
                   "valor_punto_lote": 1.0},
           "estrategia": dict(DEF_FR),
           "horario": {"noticias_et": ["08:26-08:34"], "feriados": False},   # se compara con el backtest sin feriados
           "archivos": {"stop": "STOP_FALSA_RUPTURA_SIMULACRO_NO_EXISTE.txt", "logs": "logs_falsa_ruptura"}}
    bot = BotFR(cfg, papel=False)
    falso = MT5Falso(m1, todas=todas)
    bot.broker = falso
    bot.verbose = False
    with tempfile.TemporaryDirectory() as tmp:
        bot.preparar(dir_logs=tmp)
        for i in range(1, len(m1)):
            falso.i = i
            bot.ciclo()
            falso.procesar_vela()
        reg = pd.read_csv(Path(tmp) / "trades.csv") if (Path(tmp) / "trades.csv").exists() else pd.DataFrame()
        eventos = (Path(tmp) / "eventos.log").read_text(encoding="utf-8").splitlines()
    s = pd.DataFrame(falso.trades)
    s = s[(s.entry_time >= ini) & (s.entry_time < fin)].reset_index(drop=True)
    if len(s) and todas:
        ex = s[s.extra]
        print(f"--todas: {len(ex)} llenados de mas (gap); el bot cerro {(ex.exit_reason == 'sobra').sum()} en el minuto "
              f"siguiente, {(ex.exit_reason != 'sobra').sum()} tocaron SL/TP en la misma vela; costo {ex.R.sum():+.2f}R")
        s = s[~s.extra].reset_index(drop=True)
    est = EstrategiaFR(**{k: v for k, v in DEF_FR.items() if k not in ("pivote_izq", "pivote_der")},
                       izq=DEF_FR["pivote_izq"], der=DEF_FR["pivote_der"])
    r = simular(m1, est, spread=SPREAD, feriados=False)
    r = r[(r.entry_time >= ini) & (r.entry_time < fin)].reset_index(drop=True)
    print(f"backtest {len(r)} trades {r.R.sum():+.2f}R | bot en MT5 falso {len(s)} trades {s.R.sum():+.2f}R "
          f"| registrados en trades.csv {len(reg)} | lineas de log {len(eventos)}")
    m = r.merge(s, on="entry_time", how="outer", suffixes=("_bt", "_bot"), indicator=True)
    ambos = m[m._merge == "both"]
    igual = (ambos.direction_bt == ambos.direction_bot) & (ambos.exit_time_bt == ambos.exit_time_bot) & \
        np.isclose(ambos.orden_bt, ambos.orden_bot, atol=0.011) & np.isclose(ambos.R_bt, ambos.R_bot, atol=0.002)
    print(f"mismo trade (entrada, salida, orden, R): {igual.sum()} | distintos {(~igual).sum()} | "
          f"solo backtest {(m._merge == 'left_only').sum()} | solo bot {(m._merge == 'right_only').sum()}")
    cols = ["entry_time", "direction_bt", "orden_bt", "orden_bot", "exit_time_bt", "exit_time_bot", "R_bt", "R_bot",
            "exit_reason_bt", "_merge"]
    malos = pd.concat([ambos[~igual], m[m._merge != "both"]])
    if len(malos):
        print(malos[cols].head(15).to_string(index=False))
    rep = s.groupby("clave").size()
    print(f"ordenes operadas dos veces: {(rep > 1).sum()}")
    print("\nSIMULACRO OK" if len(malos) == 0 else "\nSIMULACRO CON DIFERENCIAS (ver arriba)")


if __name__ == "__main__":
    main()
