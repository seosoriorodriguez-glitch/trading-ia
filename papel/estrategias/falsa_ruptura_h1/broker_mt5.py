# -*- coding: utf-8 -*-
"""
Conexion con MT5 de la FALSA RUPTURA en cuenta real (13-nov-2026). Es el broker del S/R (sr_pivot_h1/broker_mt5.py:
conexion y reconexion, velas, volumen, pendientes con vencimiento, mercado, cierre, historial) con ordenes STOP en vez
de LIMIT y comentario 'FR <clave>'. Solo toca ordenes y posiciones con SU magic: comparte la terminal de Darwinex con el
OB y el S/R sin interferir.

  STOP      VENTA STOP bajo el Bid, COMPRA STOP sobre el Ask (mas la distancia minima del broker).
  vigencia  cada orden vale 8 h (`hasta`); se manda con vencimiento en la hora mas temprana entre `hasta` y el corte de
            fin de semana, asi el servidor la borra aunque el bot este apagado. Si el broker no acepta la fecha, va GTC y
            la cancela el bot al empezar cada minuto (vigentes() ya no la incluye).
"""
from typing import Tuple

from papel.estrategias.sr_pivot_h1.broker_mt5 import (BrokerMT5, PRECIO_INVALIDO, VENCE_ESPECIFICA,  # noqa: F401
                                                      segundos_servidor)

from .estrategia import OrdenFR, clave_de_comentario


class BrokerMT5FR(BrokerMT5):
    clave = staticmethod(clave_de_comentario)
    comentario_cierre = "FR cierre"

    def orden_valida(self, o: OrdenFR, bid: float, ask: float) -> bool:
        dist = (self.info.trade_stops_level or 0) * self.info.point
        return (o.precio < bid - dist) if o.lado == "sell_stop" else (o.precio > ask + dist)

    def poner_orden(self, o: OrdenFR, volumen: float, vence=None) -> Tuple[bool, str]:
        hasta = o.hasta if vence is None else min(o.hasta, vence)
        return self.poner_pendiente(o, volumen, hasta)
