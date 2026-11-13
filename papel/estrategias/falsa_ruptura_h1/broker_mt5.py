# -*- coding: utf-8 -*-
"""
Conexion con MT5 de la FALSA RUPTURA en cuenta real (13-nov-2026). Es el broker del S/R (sr_pivot_h1/broker_mt5.py:
conexion, velas, volumen, mercado, cierre, historial) con ordenes STOP en vez de LIMIT y comentario 'FR <clave>'.
Solo toca ordenes y posiciones con SU magic: comparte la terminal de Darwinex con el OB y el S/R sin interferir.

  STOP      VENTA STOP bajo el Bid, COMPRA STOP sobre el Ask (mas la distancia minima del broker).
  vigencia  cada orden vale 8 h (`hasta`). Si el simbolo acepta fecha de vencimiento, la orden se manda con ella y el
            servidor la borra a la hora exacta aunque el bot este apagado; si no, va GTC y la cancela el bot al empezar
            cada minuto (vigentes() ya no la incluye).
"""
from typing import Tuple

import MetaTrader5 as mt5
import pandas as pd

from papel.estrategias.sr_pivot_h1.broker_mt5 import BrokerMT5

from .estrategia import OrdenFR, clave_de_comentario

VENCE_ESPECIFICA = 4          # SYMBOL_EXPIRATION_SPECIFIED (bit de symbol_info.expiration_mode)
RETCODE_VENCIMIENTO = 10022   # TRADE_RETCODE_INVALID_EXPIRATION


def segundos_servidor(t) -> int:
    """Hora servidor (sin zona) -> segundos como los usa MT5 (la hora del servidor contada como si fuera UTC)."""
    return int((pd.Timestamp(t) - pd.Timestamp("1970-01-01")) // pd.Timedelta(seconds=1))


class BrokerMT5FR(BrokerMT5):
    clave = staticmethod(clave_de_comentario)
    comentario_cierre = "FR cierre"

    def orden_valida(self, o: OrdenFR, bid: float, ask: float) -> bool:
        dist = (self.info.trade_stops_level or 0) * self.info.point
        return (o.precio < bid - dist) if o.lado == "sell_stop" else (o.precio > ask + dist)

    def _vence_especifica(self) -> bool:
        i = mt5.symbol_info(self.simbolo)
        return bool(i is not None and (i.expiration_mode & VENCE_ESPECIFICA))

    def poner_orden(self, o: OrdenFR, volumen: float) -> Tuple[bool, str]:
        req = {"action": mt5.TRADE_ACTION_PENDING, "symbol": self.simbolo, "volume": volumen,
               "type": mt5.ORDER_TYPE_SELL_STOP if o.lado == "sell_stop" else mt5.ORDER_TYPE_BUY_STOP,
               "price": o.precio, "sl": o.sl, "tp": o.tp, "deviation": 0, "magic": self.magic,
               "comment": o.comentario, "type_time": mt5.ORDER_TIME_GTC, "type_filling": self.llenado}
        if self._vence_especifica():
            req.update(type_time=mt5.ORDER_TIME_SPECIFIED, expiration=segundos_servidor(o.hasta))
        r = mt5.order_send(req)
        if r is not None and r.retcode == RETCODE_VENCIMIENTO and req["type_time"] != mt5.ORDER_TIME_GTC:
            req.pop("expiration")
            req["type_time"] = mt5.ORDER_TIME_GTC                 # el broker no acepto la fecha: la vence el bot
            r = mt5.order_send(req)
        if r is None:
            return False, f"order_send None {mt5.last_error()}"
        if r.retcode != mt5.TRADE_RETCODE_DONE:
            return False, f"retcode {r.retcode} {r.comment}"
        vence = "vence sola" if req["type_time"] != mt5.ORDER_TIME_GTC else "GTC, la vence el bot"
        return True, f"ticket {r.order} ({vence})"
