# -*- coding: utf-8 -*-
"""
MODO PAPEL de la falsa ruptura: igual que el del S/R (papel/estrategias/sr_pivot_h1/broker_papel.py, que NO se toca:
se hereda), con ordenes STOP:
  - VENTA STOP se llena con el primer tick cuyo Bid <= orden, al Bid de ese tick (min(orden, Bid): si el precio salto,
    al precio del salto). COMPRA STOP con Ask >= orden, a max(orden, Ask).
  - Entrada a mercado (orden ya cruzada al abrir la vela): venta al Bid, compra al Ask.
  - Niveles usados por comentario 'FR <clave>'.
Precios en vivo de la terminal; NO envia nada al broker. Este bot solo existe en modo papel.
"""
from types import SimpleNamespace

import pandas as pd

from papel.estrategias.sr_pivot_h1.broker_papel import BrokerPapel

from .estrategia import clave_de_comentario


def _es_compra(lado: str) -> bool:
    return lado.startswith("buy")


class BrokerPapelFR(BrokerPapel):
    def _procesar(self, ms: int, bid: float, ask: float):
        hora = pd.Timestamp(ms, unit="ms")
        if self.ultimo_msc:
            antes = pd.Timestamp(self.ultimo_msc, unit="ms")
            for dia in pd.date_range(antes.normalize(), hora.normalize(), freq="D")[:-1]:
                self._swap(dia, bid, ask)
        previo = self.ultimo_tick or (bid, ask)
        self.ultimo_tick = (bid, ask)
        for p in list(self.pos.values()):
            if p.type == 0:
                if bid <= p.sl:
                    self._salir(p, bid, "sl", hora)
                elif bid >= p.tp:
                    self._salir(p, p.tp, "tp", hora)
            else:
                if ask >= p.sl:
                    self._salir(p, ask, "sl", hora)
                elif ask <= p.tp:
                    self._salir(p, p.tp, "tp", hora)
        # si un salto cruza varias STOP en el mismo tick, se llena la que el precio toco primero (la mas cercana al
        # tick anterior), como el backtest (la mas cercana a la apertura)
        cand = []
        for o in self.pend.values():
            if o.lado == "sell_stop" and bid <= o.price_open:
                cand.append((abs(previo[0] - o.price_open), o, min(o.price_open, bid)))
            elif o.lado == "buy_stop" and ask >= o.price_open:
                cand.append((abs(previo[1] - o.price_open), o, max(o.price_open, ask)))
        if cand:
            _, o, precio = min(cand, key=lambda x: x[0])
            self._abrir(o, precio, hora)

    def _abrir(self, o, precio: float, hora: pd.Timestamp):
        if self.pos:                                       # 1 posicion a la vez
            return
        self.pend.pop(o.ticket, None)
        self.n += 1
        p = SimpleNamespace(identifier=self.n, ticket=self.n, type=0 if _es_compra(o.lado) else 1,
                            comment=o.comment, sl=o.sl, tp=o.tp, price_open=precio, volume=o.volume,
                            time_msc=int(hora.value // 10 ** 6), hora=str(hora), orden=o.price_open,
                            swap_pts=0.0, swap_dinero=0.0, noches=0)
        self.pos[p.identifier] = p
        self.avisos.append(f"[papel] llenada {o.comment} a {precio} ({hora:%d-%m %H:%M:%S})")

    def orden_valida(self, o, bid: float, ask: float) -> bool:
        dist = (self.info.trade_stops_level or 0) * self.info.point
        return (o.precio < bid - dist) if o.lado == "sell_stop" else (o.precio > ask + dist)

    def poner_orden(self, o, volumen):
        return self.poner_limit(o, volumen)                # en papel una pendiente es una pendiente (guarda el lado)

    def abrir_mercado(self, o, volumen):
        b, a = self.ultimo_tick or (None, None)
        if b is None:
            return False, "sin precio"
        compra = _es_compra(o.lado)
        o_ = SimpleNamespace(ticket=-1, comment=o.comentario, lado=o.lado, price_open=o.precio, sl=o.sl, tp=o.tp,
                             volume=volumen)
        self._abrir(o_, a if compra else b, pd.Timestamp(self.ultimo_msc, unit="ms"))
        self._guardar()
        return True, f"papel a mercado {a if compra else b}"

    def claves_usadas(self, dias=None):
        return {clave_de_comentario(h["comentario_entrada"]) for h in self.hist.values()} - {None}
