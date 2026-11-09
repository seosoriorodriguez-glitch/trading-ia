# -*- coding: utf-8 -*-
"""
SIMULACRO del bot completo (bot.py) contra un MT5 FALSO alimentado con velas M1 historicas. No conecta a ningun MT5.

Prueba lo que la paridad no cubre: que el bot ponga y cancele las ordenes LIMIT, detecte llenados por el comentario,
no repita niveles (usados), cancele por noticias y fin de semana, cierre el viernes y registre los trades.
El MT5 falso llena y cierra con las reglas del backtest (velas Bid, Ask = Bid + 2.1, desliz SL 0.7, SL antes que TP,
el TP no se mira en la vela de entrada). El bot "despierta" una vez por minuto, al abrir cada vela M1.

    python papel/estrategias/sr_pivot_h1/herramientas/simulacro.py                 # 2026-01-01 a 2026-11-01
    python papel/estrategias/sr_pivot_h1/herramientas/simulacro.py 2026-09-01 2026-10-01
"""
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

RAIZ = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "research" / "pa_lab"))
sys.path.insert(0, str(RAIZ / "research" / "pa_lab" / "repaso"))

import numpy as np
import pandas as pd
import yaml

from datos import m1_periodo, tf
import motor_toque2 as MT
from papel.estrategias.sr_pivot_h1.bot import BotSR
from papel.estrategias.sr_pivot_h1.estrategia import clave_de_comentario
from papel.estrategias.sr_pivot_h1.niveles import find_levels

SPREAD, DESLIZ_SL = 2.1, 0.7


class MT5Falso:
    def __init__(self, m1):
        self.m1 = m1.reset_index(drop=True)
        self.t = self.m1.time.values
        self.o, self.h, self.l, self.c = (self.m1[k].values.astype(float) for k in ("open", "high", "low", "close"))
        self.h1 = tf(self.m1, 60)
        self.h1t = self.h1.time.values
        self.i = 1
        self.magic, self.simbolo = 345690, "US30.cash"
        self.info = SimpleNamespace(digits=2, point=0.01, trade_tick_size=0.01, volume_min=0.01, volume_step=0.01,
                                    volume_max=100.0, trade_stops_level=0)
        self.pend, self.pos, self.hist = {}, {}, {}
        self.n = 1000
        self.trades = []

    # interfaz de BrokerMT5 --------------------------------------------------------------------------------
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

    def tick(self):
        return {"bid": self.o[self.i], "ask": self.o[self.i] + SPREAD, "hora": pd.Timestamp(self.t[self.i])}

    def velas(self, tf_, n):
        if tf_ == "M1":
            d = self.m1.iloc[max(0, self.i - n + 1):self.i + 1].copy()
            d.iloc[-1, d.columns.get_loc("close")] = self.o[self.i]       # vela en formacion: solo su apertura
            return d.assign(spread=210)
        k = int(np.searchsorted(self.h1t, np.datetime64(pd.Timestamp(self.t[self.i]).floor("h")), side="right"))
        return self.h1.iloc[max(0, k - n):k].assign(spread=210)

    def posiciones(self):
        return list(self.pos.values())

    def pendientes(self):
        return list(self.pend.values())

    def volumen(self, riesgo, pts):
        return round(max(0.01, riesgo / pts), 2)

    def orden_valida(self, o, bid, ask):
        return o.precio < ask if o.lado == "buy_limit" else o.precio > bid

    def margen_ok(self, o, v):
        return True, 0.0

    def poner_limit(self, o, vol):
        self.n += 1
        self.pend[self.n] = SimpleNamespace(ticket=self.n, comment=o.comentario, lado=o.lado, price_open=o.precio,
                                            sl=o.sl, tp=o.tp, volume=vol)
        return True, f"ticket {self.n}"

    def cancelar(self, ticket):
        self.pend.pop(ticket, None)
        return True, "ok"

    def abrir_mercado(self, o, vol):
        compra = o.lado == "buy_limit"
        ent = self.o[self.i] + SPREAD if compra else self.o[self.i]
        self.n += 1
        p = SimpleNamespace(identifier=self.n, ticket=self.n, type=0 if compra else 1, comment=o.comentario, sl=o.sl,
                            tp=o.tp, price_open=ent, volume=vol, time_msc=self.i, t=pd.Timestamp(self.t[self.i]),
                            i=self.i, orden=o.precio)
        self.pos[p.identifier] = p
        self.recien = p                                  # el SL se mira en esta misma vela (procesar_vela)
        return True, f"a mercado {ent}"

    def cerrar(self, p):
        precio = self.o[self.i] if p.type == 0 else self.o[self.i] + SPREAD
        self._salir(p, precio, "viernes")
        return True, f"cerrada a {precio}"

    def claves_usadas(self, dias=None):
        return {clave_de_comentario(x["comentario_entrada"]) for x in self.hist.values()}

    def cerradas_recientes(self, dias=10):
        return set(self.hist)

    def resumen_posicion(self, pid):
        return self.hist.get(pid)

    # mercado -----------------------------------------------------------------------------------------------
    def _salir(self, p, precio, motivo):
        self.pos.pop(p.identifier, None)
        d = 1 if p.type == 0 else -1
        self.hist[p.identifier] = {"entrada_hora": p.t, "salida_hora": pd.Timestamp(self.t[self.i]),
                                   "lado": "long" if d == 1 else "short", "volumen": p.volume,
                                   "entrada": p.price_open, "salida": precio, "comentario_entrada": p.comment,
                                   "comentario_salida": motivo, "profit": d * (precio - p.price_open) * p.volume,
                                   "sl": p.sl, "tp": p.tp, "comision": 0.0, "swap": 0.0}
        self.trades.append(dict(entry_time=p.t, exit_time=pd.Timestamp(self.t[self.i]),
                                direction="long" if d == 1 else "short", orden=p.orden, entry_price=p.price_open,
                                sl=p.sl, tp=p.tp, exit_price=precio, exit_reason=motivo,
                                R=d * (precio - p.price_open) / abs(p.orden - p.sl)))

    def procesar_vela(self):
        """Lo que pasa DENTRO de la vela i despues de que el bot actuo al abrirla."""
        i, o, h, l = self.i, self.o[self.i], self.h[self.i], self.l[self.i]
        for p in list(self.pos.values()):
            if p.i == i:                                 # abierta a mercado al abrir esta vela: solo el SL
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
        if self.pos:
            return
        cand = []
        for x in self.pend.values():
            if x.lado == "buy_limit" and l + SPREAD <= x.price_open:
                cand.append((abs(o + SPREAD - x.price_open), x, min(x.price_open, o + SPREAD)))
            elif x.lado == "sell_limit" and h >= x.price_open:
                cand.append((abs(o - x.price_open), x, max(x.price_open, o)))
        if not cand:
            return
        _, x, ent = min(cand, key=lambda z: z[0])
        self.pend.pop(x.ticket)
        self.n += 1
        p = SimpleNamespace(identifier=self.n, ticket=self.n, type=0 if x.lado == "buy_limit" else 1, comment=x.comment,
                            sl=x.sl, tp=x.tp, price_open=ent, volume=x.volume, time_msc=i, t=pd.Timestamp(self.t[i]),
                            i=i, orden=x.price_open)
        self.pos[p.identifier] = p
        if (p.type == 0 and ent <= p.sl) or (p.type == 1 and ent >= p.sl):
            self._salir(p, o if p.type == 0 else o + SPREAD, "sl_hueco")
        elif (p.type == 0 and l <= p.sl) or (p.type == 1 and h + SPREAD >= p.sl):
            self._salir(p, p.sl - DESLIZ_SL if p.type == 0 else p.sl + DESLIZ_SL, "sl")


def main():
    ini = pd.Timestamp(sys.argv[1] if len(sys.argv) > 1 else "2026-01-01")
    fin = pd.Timestamp(sys.argv[2] if len(sys.argv) > 2 else "2026-11-01")
    m1 = m1_periodo(ini, fin, margen_dias=40)
    cfg = yaml.safe_load((RAIZ / "papel" / "estrategias" / "sr_pivot_h1" / "config" / "demo.yaml").read_text(encoding="utf-8"))
    falso = MT5Falso(m1)
    bot = BotSR(cfg)
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
    nv = [(pd.Timestamp(x.activation_time), x.price, x.kind, k) for k, x in enumerate(find_levels(tf(m1, 60), 15, 15))]
    r = MT.correr(m1, nv, 20, 130, 2.5, solo_limit=True, escala=True)
    r = r[(r.entry_time >= ini) & (r.entry_time < fin)].reset_index(drop=True)
    print(f"backtest {len(r)} trades {r.R.sum():+.2f}R | bot en MT5 falso {len(s)} trades {s.R.sum():+.2f}R "
          f"| registrados en trades.csv {len(reg)} | lineas de log {len(eventos)}")
    m = r.merge(s, on="entry_time", how="outer", suffixes=("_bt", "_bot"), indicator=True)
    ambos = m[m._merge == "both"]
    igual = (ambos.direction_bt == ambos.direction_bot) & (ambos.exit_time_bt == ambos.exit_time_bot) & \
        np.isclose(ambos.orden_bt, ambos.orden_bot, atol=0.011) & np.isclose(ambos.R_bt, ambos.R_bot, atol=0.002)
    print(f"mismo trade (entrada, salida, orden, R): {igual.sum()} | distintos {(~igual).sum()} | "
          f"solo backtest {(m._merge == 'left_only').sum()} | solo bot {(m._merge == 'right_only').sum()}")
    cols = ["entry_time", "direction_bt", "orden_bt", "orden_bot", "exit_time_bt", "exit_time_bot", "R_bt", "R_bot", "_merge"]
    malos = pd.concat([ambos[~igual], m[m._merge != "both"]])
    if len(malos):
        print(malos[cols].head(15).to_string(index=False))
    usados_rep = s.groupby(s.orden.round(1)).size()
    print(f"niveles operados dos veces: {(usados_rep > 1).sum()}")
    print("\nSIMULACRO OK" if len(malos) == 0 else "\nSIMULACRO CON DIFERENCIAS (ver arriba)")


if __name__ == "__main__":
    main()
