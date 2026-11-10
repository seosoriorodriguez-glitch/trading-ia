# -*- coding: utf-8 -*-
"""
MODO PAPEL: el bot corre conectado a una terminal MT5 real (precios en vivo del broker), pero NO envia ninguna orden.
Las ordenes, posiciones e historial son virtuales y se llenan con los ticks reales (bid/ask) del simbolo.

  - Lee TODOS los ticks desde la ultima vuelta (copy_ticks_from), no solo el precio cada 2 s: un toque rapido de la
    orden, el SL o el TP entre dos vueltas tambien cuenta. Al reiniciar el bot, procesa los ticks del tiempo apagado.
  - Llenados: BUY LIMIT si Ask <= orden (al Ask si salto por debajo), SELL LIMIT si Bid >= orden; SELL STOP si
    Bid <= orden (al Bid), BUY STOP si Ask >= orden (al Ask). Si un mismo tick cruza varias, se llena la que el precio
    toco primero (la mas cercana al tick anterior), como el backtest (la mas cercana a la apertura).
    SL de una compra con Bid <= SL, al Bid de ese tick (deslizamiento real); TP con Bid >= TP, al TP. Ventas con Ask.
  - Reglas que aplica el broker AUNQUE el bot no corra (auditoria 10-nov-2026: al relanzar tras una caida, el bot
    reprocesaba ticks sin sus reglas): `reglas(hora)` -> (bloqueado, corte) que pone el bot: en el corte de fin de
    semana cierra la posicion y cancela las pendientes; con bloqueo (noticias, fin de semana, corte) no llena
    pendientes; una pendiente con `hasta` vence sola; al llenarse una, se cancelan las demas (1 posicion a la vez).
  - SWAP real: en cada cambio de dia del servidor de lunes a viernes con la posicion abierta, con los datos del simbolo
    (swap_long / swap_short, modo de calculo y dia del swap triple). Sabado y domingo no cobran (el triple ya los
    cubre).
  - Estado en papel_estado.json (ordenes, posicion, historial, balance virtual, ultimo tick): sobrevive reinicios.
No toca la cuenta: puede leer la misma terminal que otro bot (como el collector del panel).
"""
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Optional

import MetaTrader5 as mt5
import pandas as pd

from .broker_mt5 import BrokerMT5


def _es_compra(lado: str) -> bool:
    return lado.startswith("buy")


class BrokerPapel(BrokerMT5):
    def __init__(self, *a, balance_inicial: float = 100000.0, **kw):
        super().__init__(*a, **kw)
        self.balance_inicial = float(balance_inicial)
        self.archivo: Optional[Path] = None
        self.pend, self.pos, self.hist = {}, {}, {}
        self.balance = self.balance_inicial
        self.n = 0
        self.ultimo_msc = None
        self.ultimo_tick = None
        self.avisos = []                                  # mensajes para el log del bot
        self.reglas = None                                # hora -> (bloqueado, corte); la pone el bot

    # ------------------------------------------------------------------ estado
    def abrir_estado(self, carpeta: Path):
        self.archivo = Path(carpeta) / "papel_estado.json"
        if self.archivo.exists():
            d = json.loads(self.archivo.read_text())
            self.pend = {int(k): SimpleNamespace(**v) for k, v in d["pend"].items()}
            self.pos = {int(k): SimpleNamespace(**v) for k, v in d["pos"].items()}
            self.hist = {int(k): v for k, v in d["hist"].items()}
            self.balance, self.n, self.ultimo_msc = d["balance"], d["n"], d["ultimo_msc"]

    def _guardar(self):
        if self.archivo is None:
            return
        self.archivo.write_text(json.dumps({
            "pend": {k: vars(v) for k, v in self.pend.items()}, "pos": {k: vars(v) for k, v in self.pos.items()},
            "hist": self.hist, "balance": self.balance, "n": self.n, "ultimo_msc": self.ultimo_msc}, indent=1,
            default=str))

    # ------------------------------------------------------------------ cuenta virtual
    def cuenta(self) -> Optional[dict]:
        real = super().cuenta()
        if real is None:
            return None
        flot = sum(self._flotante(p) for p in self.pos.values())
        return {**real, "login": f"papel_{real['login']}", "balance": self.balance, "equity": self.balance + flot,
                "margen_libre": 1e12}

    def _flotante(self, p) -> float:
        if self.ultimo_tick is None:
            return 0.0
        b, a = self.ultimo_tick
        px = b if p.type == 0 else a
        d = 1 if p.type == 0 else -1
        return d * (px - p.price_open) * p.volume * self.valor_punto() + p.swap_dinero

    # ------------------------------------------------------------------ ticks reales -> llenados virtuales
    desfase_s = 0          # segundos a restar al pedir ticks si el terminal espera la hora en otro huso (se calibra)

    def _pedir_ticks(self, desde_ms: int):
        return mt5.copy_ticks_from(self.simbolo, desde_ms // 1000 - self.desfase_s, 200000, mt5.COPY_TICKS_ALL)

    def tick(self) -> Optional[dict]:
        t = super().tick()
        if t is None:
            return None
        ahora_ms = int(t["hora"].value // 10 ** 6)
        if self.ultimo_msc is None:                       # primera vez: se empieza desde ahora
            self.ultimo_msc, self.ultimo_tick = ahora_ms, (t["bid"], t["ask"])
            self._guardar()
            return t
        desde = self.ultimo_msc + 1
        while True:
            ticks = self._pedir_ticks(desde)
            if (ticks is None or not len(ticks)) and ahora_ms > self.ultimo_msc + 5000 and self.desfase_s == 0:
                # el terminal trae ticks nuevos pero la consulta no: espera la hora en UTC -> calibrar una vez
                import time as _t
                self.desfase_s = int(round((t["hora"].value / 1e9 - _t.time()) / 3600) * 3600)
                self.avisos.append(f"[papel] consulta de ticks calibrada: desfase {self.desfase_s / 3600:+.0f} h")
                ticks = self._pedir_ticks(desde)
            if ticks is None or not len(ticks):
                break
            for x in ticks:
                ms = int(x["time_msc"])
                if self.ultimo_msc and ms <= self.ultimo_msc:
                    continue
                if x["bid"] > 0 and x["ask"] > 0:
                    self._procesar(ms, float(x["bid"]), float(x["ask"]))
                self.ultimo_msc = ms
            if len(ticks) < 200000:                       # al dia; si no, sigue (bot apagado mucho tiempo)
                break
            desde = self.ultimo_msc + 1
        if self.ultimo_tick is None:
            self.ultimo_tick = (t["bid"], t["ask"])
        self._guardar()
        return t

    def _procesar(self, ms: int, bid: float, ask: float):
        hora = pd.Timestamp(ms, unit="ms")
        if self.ultimo_msc:
            antes = pd.Timestamp(self.ultimo_msc, unit="ms")
            for dia in pd.date_range(antes.normalize(), hora.normalize(), freq="D")[:-1]:
                self._swap(dia, bid, ask)                 # rollover al pasar la medianoche del servidor
        previo = self.ultimo_tick or (bid, ask)
        self.ultimo_tick = (bid, ask)
        bloq, corte = self.reglas(hora) if self.reglas else (False, False)
        if corte:
            for p in list(self.pos.values()):
                self._salir(p, bid if p.type == 0 else ask, "viernes", hora)
            if self.pend:
                self.avisos.append(f"[papel] corte de fin de semana: canceladas {len(self.pend)} pendientes")
                self.pend.clear()
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
        for k, o in list(self.pend.items()):
            vence = getattr(o, "hasta_ms", None)
            if vence is not None and ms >= vence:
                self.pend.pop(k, None)
                self.avisos.append(f"[papel] vencio {o.comment}")
        if bloq or self.pos or not self.pend:
            return
        cand = []
        for o in self.pend.values():
            px = o.price_open
            if o.lado == "buy_limit" and ask <= px:
                cand.append((abs(previo[1] - px), o, min(px, ask)))
            elif o.lado == "sell_limit" and bid >= px:
                cand.append((abs(previo[0] - px), o, max(px, bid)))
            elif o.lado == "sell_stop" and bid <= px:
                cand.append((abs(previo[0] - px), o, min(px, bid)))
            elif o.lado == "buy_stop" and ask >= px:
                cand.append((abs(previo[1] - px), o, max(px, ask)))
        if cand:
            _, o, precio = min(cand, key=lambda x: x[0])
            self._abrir(o, precio, hora)

    def _swap(self, dia: pd.Timestamp, bid: float, ask: float):
        if not self.pos or dia.weekday() >= 5:            # sabado y domingo: sin rollover (el triple los cubre)
            return
        i = mt5.symbol_info(self.simbolo)
        triple = 3 if (dia.weekday() + 1) % 7 == i.swap_rollover3days else 1   # MT5: 0 = domingo
        for p in self.pos.values():
            v = i.swap_long if p.type == 0 else i.swap_short
            px = p.price_open
            if i.swap_mode == 1:                                  # puntos
                pts = v * i.point
            elif i.swap_mode in (2, 3, 4):                        # dinero por lote (simbolo/margen/cuenta, todo USD)
                pts = v / self.valor_punto()
            elif i.swap_mode in (5, 6):                           # % anual sobre precio actual / de apertura
                ref = (bid if p.type == 0 else ask) if i.swap_mode == 5 else px
                pts = ref * v / 100 / 360
            else:
                self.avisos.append(f"swap modo {i.swap_mode} no soportado en papel: no se descuenta")
                pts = 0.0
            pts *= triple
            p.swap_pts += pts
            p.swap_dinero += pts * p.volume * self.valor_punto()
            p.noches += 1
            self.avisos.append(f"swap {dia:%a %d-%m} {'x3 ' if triple == 3 else ''}{p.comment}: {pts:+.2f} pts "
                               f"({pts * p.volume * self.valor_punto():+.2f})")

    def _abrir(self, o, precio: float, hora: pd.Timestamp):
        if self.pos:                                       # 1 posicion a la vez
            return
        self.pend.pop(o.ticket, None)
        if self.pend:                                      # el bot cancela las demas: el broker no espera al bot
            self.pend.clear()
        self.n += 1
        p = SimpleNamespace(identifier=self.n, ticket=self.n, type=0 if _es_compra(o.lado) else 1,
                            comment=o.comment, sl=o.sl, tp=o.tp, price_open=precio, volume=o.volume,
                            time_msc=int(hora.value // 10 ** 6), hora=str(hora), orden=o.price_open,
                            swap_pts=0.0, swap_dinero=0.0, noches=0)
        self.pos[p.identifier] = p
        self.avisos.append(f"[papel] llenada {o.comment} a {precio} ({hora:%d-%m %H:%M:%S})")

    def _salir(self, p, precio: float, motivo: str, hora: pd.Timestamp):
        self.pos.pop(p.identifier, None)
        d = 1 if p.type == 0 else -1
        bruto = d * (precio - p.price_open) * p.volume * self.valor_punto()
        self.balance += bruto + p.swap_dinero
        self.hist[p.identifier] = {"entrada_hora": p.hora, "salida_hora": str(hora),
                                   "lado": "long" if d == 1 else "short", "volumen": p.volume,
                                   "entrada": p.price_open, "salida": precio, "comentario_entrada": p.comment,
                                   "comentario_salida": motivo, "sl": p.sl, "tp": p.tp, "orden": p.orden,
                                   "profit": round(bruto, 2), "comision": 0.0, "swap": round(p.swap_dinero, 2),
                                   "swap_pts": round(p.swap_pts, 2), "noches": p.noches}
        self.avisos.append(f"[papel] cerrada {p.comment} por {motivo} a {precio} ({hora:%d-%m %H:%M:%S})")

    # ------------------------------------------------------------------ interfaz de ordenes (virtual)
    def posiciones(self) -> list:
        return list(self.pos.values())

    def pendientes(self) -> list:
        return list(self.pend.values())

    def margen_ok(self, o, volumen):
        return True, 0.0

    def orden_valida(self, o, bid: float, ask: float) -> bool:
        """En papel no hay distancia minima del broker (las ordenes son virtuales): solo que no este cruzada."""
        if o.lado == "buy_limit":
            return o.precio < ask
        if o.lado == "sell_limit":
            return o.precio > bid
        if o.lado == "sell_stop":
            return o.precio < bid
        return o.precio > ask

    def poner_limit(self, o, volumen):
        self.n += 1
        hasta = getattr(o, "hasta", None)
        self.pend[self.n] = SimpleNamespace(ticket=self.n, comment=o.comentario, lado=o.lado, price_open=o.precio,
                                            sl=o.sl, tp=o.tp, volume=volumen,
                                            hasta_ms=int(pd.Timestamp(hasta).value // 10 ** 6) if hasta is not None
                                            else None)
        self._guardar()
        return True, f"papel #{self.n}"

    poner_orden = poner_limit                              # en papel una pendiente es una pendiente (guarda el lado)

    def cancelar(self, ticket):
        self.pend.pop(ticket, None)
        self._guardar()
        return True, "ok"

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

    def cerrar(self, p):
        b, a = self.ultimo_tick
        precio = b if p.type == 0 else a
        self._salir(p, precio, "viernes", pd.Timestamp(self.ultimo_msc, unit="ms"))
        self._guardar()
        return True, f"papel cerrada a {precio}"

    def claves_usadas(self, dias=None):
        from .estrategia import clave_de_comentario
        return {clave_de_comentario(h["comentario_entrada"]) for h in self.hist.values()} - {None}

    def cerradas_recientes(self, dias=10):
        return set(self.hist)

    def resumen_posicion(self, pid):
        h = self.hist.get(pid)
        if h is None:
            return None
        return {**h, "entrada_hora": pd.Timestamp(h["entrada_hora"]), "salida_hora": pd.Timestamp(h["salida_hora"])}
