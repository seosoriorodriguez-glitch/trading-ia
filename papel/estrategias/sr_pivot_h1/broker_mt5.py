# -*- coding: utf-8 -*-
"""
Conexion con MT5 del bot S/R Pivot. Solo toca ordenes y posiciones con SU magic number: puede compartir terminal
con otros bots (cada uno filtra por su magic) sin interferir.
"""
import math
from datetime import datetime, timedelta
from typing import List, Optional, Set, Tuple

import MetaTrader5 as mt5
import pandas as pd

from .estrategia import Orden, clave_de_comentario

TF = {"M1": mt5.TIMEFRAME_M1, "M5": mt5.TIMEFRAME_M5, "H1": mt5.TIMEFRAME_H1}
LLENADO = {"return": mt5.ORDER_FILLING_RETURN, "ioc": mt5.ORDER_FILLING_IOC, "fok": mt5.ORDER_FILLING_FOK}


def _es_compra(lado: str) -> bool:
    return lado.startswith("buy")


class BrokerMT5:
    clave = staticmethod(clave_de_comentario)        # comentario de la orden -> nivel ('SR <clave>'); la FR la cambia
    comentario_cierre = "SR cierre"

    def __init__(self, simbolo: str, terminal: Optional[str], magic: int, valor_punto: Optional[float] = None,
                 llenado: str = "return"):
        self.simbolo = simbolo
        self.terminal = terminal
        self.magic = int(magic)
        self.valor_punto_config = valor_punto
        self.llenado = LLENADO[llenado]
        self.info = None

    # ------------------------------------------------------------------ conexion
    def conectar(self) -> Tuple[bool, str]:
        ok = mt5.initialize(path=self.terminal) if self.terminal else mt5.initialize()
        if not ok:
            return False, f"no se pudo iniciar MT5 ({self.terminal}): {mt5.last_error()}"
        if mt5.symbol_info(self.simbolo) is None:
            return False, f"simbolo {self.simbolo} no existe en esta cuenta"
        if not mt5.symbol_info(self.simbolo).visible and not mt5.symbol_select(self.simbolo, True):
            return False, f"no se pudo seleccionar {self.simbolo}"
        self.info = mt5.symbol_info(self.simbolo)
        return True, "ok"

    def desconectar(self):
        mt5.shutdown()

    def cuenta(self) -> Optional[dict]:
        a = mt5.account_info()
        if a is None:
            return None
        return {"login": a.login, "server": a.server, "balance": a.balance, "equity": a.equity,
                "margen_libre": a.margin_free, "moneda": a.currency, "apalancamiento": a.leverage}

    def valor_punto_mt5(self) -> float:
        i = mt5.symbol_info(self.simbolo)
        return i.trade_tick_value / i.trade_tick_size if i and i.trade_tick_size else float("nan")

    def valor_punto(self) -> float:
        """Dinero por 1.0 de precio y 1 lote. Config si esta puesto (Darwinex WS30: MT5 informa 0.1 pero la P&L
        real es ~1.0, ver memoria del bot OB Darwinex); si no, lo que dice MT5."""
        return float(self.valor_punto_config) if self.valor_punto_config else self.valor_punto_mt5()

    # ------------------------------------------------------------------ mercado
    def tick(self) -> Optional[dict]:
        t = mt5.symbol_info_tick(self.simbolo)
        if t is None or t.time == 0:
            return None
        return {"bid": t.bid, "ask": t.ask, "hora": pd.Timestamp(t.time, unit="s")}   # hora SERVIDOR

    def velas(self, tf: str, n: int) -> Optional[pd.DataFrame]:
        """Ultimas n velas INCLUIDA la que esta en formacion (la ultima fila). time = apertura, hora servidor."""
        r = mt5.copy_rates_from_pos(self.simbolo, TF[tf], 0, n)
        if r is None or len(r) == 0:
            return None
        d = pd.DataFrame(r)
        d["time"] = pd.to_datetime(d["time"], unit="s")
        return d[["time", "open", "high", "low", "close", "spread"]]

    # ------------------------------------------------------------------ ordenes y posiciones (solo este magic)
    def posiciones(self) -> list:
        p = mt5.positions_get(symbol=self.simbolo) or []
        return [x for x in p if x.magic == self.magic]

    def pendientes(self) -> list:
        o = mt5.orders_get(symbol=self.simbolo) or []
        return [x for x in o if x.magic == self.magic]

    def volumen(self, riesgo_dinero: float, riesgo_pts: float) -> float:
        i = self.info
        v = riesgo_dinero / (riesgo_pts * self.valor_punto())
        paso = i.volume_step or 0.01
        v = math.floor(v / paso + 1e-9) * paso
        v = min(v, i.volume_max)
        return round(v, 8) if v >= i.volume_min else 0.0

    def orden_valida(self, o: Orden, bid: float, ask: float) -> bool:
        dist = (self.info.trade_stops_level or 0) * self.info.point
        return (o.precio < ask - dist) if o.lado == "buy_limit" else (o.precio > bid + dist)

    def margen_ok(self, o: Orden, volumen: float) -> Tuple[bool, float]:
        tipo = mt5.ORDER_TYPE_BUY if _es_compra(o.lado) else mt5.ORDER_TYPE_SELL
        m = mt5.order_calc_margin(tipo, self.simbolo, volumen, o.precio)
        a = mt5.account_info()
        if m is None or a is None:
            return True, float("nan")
        return m < a.margin_free * 0.9, m

    def poner_limit(self, o: Orden, volumen: float) -> Tuple[bool, str]:
        req = {"action": mt5.TRADE_ACTION_PENDING, "symbol": self.simbolo, "volume": volumen,
               "type": mt5.ORDER_TYPE_BUY_LIMIT if o.lado == "buy_limit" else mt5.ORDER_TYPE_SELL_LIMIT,
               "price": o.precio, "sl": o.sl, "tp": o.tp, "deviation": 0, "magic": self.magic,
               "comment": o.comentario, "type_time": mt5.ORDER_TIME_GTC, "type_filling": self.llenado}
        r = mt5.order_send(req)
        if r is None:
            return False, f"order_send None {mt5.last_error()}"
        if r.retcode != mt5.TRADE_RETCODE_DONE:
            return False, f"retcode {r.retcode} {r.comment}"
        return True, f"ticket {r.order}"

    def abrir_mercado(self, o: Orden, volumen: float) -> Tuple[bool, str]:
        """Entrada a mercado con el SL/TP de la orden: cuando al abrir la vela el precio ya paso la LIMIT (el backtest
        la llena en la apertura, como una limite que ya estaba puesta)."""
        t = mt5.symbol_info_tick(self.simbolo)
        compra = _es_compra(o.lado)
        req = {"action": mt5.TRADE_ACTION_DEAL, "symbol": self.simbolo, "volume": volumen,
               "type": mt5.ORDER_TYPE_BUY if compra else mt5.ORDER_TYPE_SELL, "price": t.ask if compra else t.bid,
               "sl": o.sl, "tp": o.tp, "deviation": 20, "magic": self.magic, "comment": o.comentario,
               "type_time": mt5.ORDER_TIME_GTC, "type_filling": mt5.ORDER_FILLING_IOC}
        r = mt5.order_send(req)
        if r is None:
            return False, f"order_send None {mt5.last_error()}"
        if r.retcode != mt5.TRADE_RETCODE_DONE:
            return False, f"retcode {r.retcode} {r.comment}"
        return True, f"a mercado {r.price}"

    def cancelar(self, ticket: int) -> Tuple[bool, str]:
        r = mt5.order_send({"action": mt5.TRADE_ACTION_REMOVE, "order": ticket})
        if r is None or r.retcode != mt5.TRADE_RETCODE_DONE:
            return False, f"no se pudo cancelar {ticket}: {None if r is None else (r.retcode, r.comment)}"
        return True, "ok"

    def cerrar(self, p) -> Tuple[bool, str]:
        t = mt5.symbol_info_tick(self.simbolo)
        compra = p.type == mt5.POSITION_TYPE_BUY
        req = {"action": mt5.TRADE_ACTION_DEAL, "symbol": self.simbolo, "volume": p.volume,
               "type": mt5.ORDER_TYPE_SELL if compra else mt5.ORDER_TYPE_BUY, "position": p.ticket,
               "price": t.bid if compra else t.ask, "deviation": 20, "magic": self.magic,
               "comment": self.comentario_cierre,
               "type_time": mt5.ORDER_TIME_GTC, "type_filling": mt5.ORDER_FILLING_IOC}
        r = mt5.order_send(req)
        if r is None or r.retcode != mt5.TRADE_RETCODE_DONE:
            return False, f"no se pudo cerrar {p.ticket}: {None if r is None else (r.retcode, r.comment)}"
        return True, f"cerrada a {r.price}"

    # ------------------------------------------------------------------ historial
    def _deals(self, dias: Optional[int] = None) -> list:
        desde = datetime.now() - timedelta(days=dias) if dias else datetime(2020, 1, 1)
        d = mt5.history_deals_get(desde, datetime.now() + timedelta(days=3))
        return [x for x in (d or []) if x.magic == self.magic and x.symbol == self.simbolo]

    def claves_usadas(self, dias: Optional[int] = None, excluir=()) -> Set[str]:
        """Niveles ya operados segun el historial (deals de entrada con comentario 'SR <clave>'). Cubre tambien las
        posiciones que se abrieron y cerraron entre dos vueltas del bot. `excluir`: posiciones que no cuentan (las que
        el bot cerro porque un gap lleno dos ordenes a la vez: en el backtest ese nivel sigue sin usar)."""
        out = set()
        for x in self._deals(dias):
            if x.entry == mt5.DEAL_ENTRY_IN and x.position_id not in excluir:
                k = self.clave(x.comment)
                if k:
                    out.add(k)
        return out

    def cerradas_recientes(self, dias: int = 10) -> Set[int]:
        return {x.position_id for x in self._deals(dias) if x.entry in (mt5.DEAL_ENTRY_OUT, mt5.DEAL_ENTRY_OUT_BY)}

    def resumen_posicion(self, position_id: int) -> Optional[dict]:
        """Entrada y salida de una posicion ya cerrada (para el registro de trades)."""
        ds = mt5.history_deals_get(position=position_id) or []
        ent = [x for x in ds if x.entry == mt5.DEAL_ENTRY_IN]
        sal = [x for x in ds if x.entry in (mt5.DEAL_ENTRY_OUT, mt5.DEAL_ENTRY_OUT_BY)]
        if not ent or not sal:
            return None
        e, s = ent[0], sal[-1]
        ords = mt5.history_orders_get(position=position_id) or []
        o0 = min(ords, key=lambda x: x.time_setup_msc) if ords else None
        return {"entrada_hora": pd.Timestamp(e.time, unit="s"), "salida_hora": pd.Timestamp(s.time, unit="s"),
                "lado": "long" if e.type == mt5.DEAL_TYPE_BUY else "short", "volumen": e.volume,
                "entrada": e.price, "salida": s.price, "comentario_entrada": e.comment, "comentario_salida": s.comment,
                "sl": o0.sl if o0 else None, "tp": o0.tp if o0 else None, "orden": o0.price_open if o0 else None,
                "profit": sum(x.profit for x in sal), "comision": sum(x.commission for x in ds),
                "swap": sum(x.swap for x in ds)}
