# -*- coding: utf-8 -*-
"""
Bot de la FALSA RUPTURA de pivotes H1 (ordenes STOP). SOLO MODO PAPEL: precios reales de la terminal, ordenes
virtuales (broker_papel.py). La logica de decision esta en estrategia.py (probada contra la investigacion con
herramientas/paridad.py); el bot entero en papel se prueba con herramientas/prueba_papel.py.

Ciclo (cada ~2 s, lo llama papel/runner.py):
  1. Corte del viernes -> cancela pendientes y cierra la posicion (como el backtest).
  2. Con posicion abierta -> sin pendientes (1 posicion a la vez).
  3. Noticias 08:26-08:34 ET o fin de semana -> sin pendientes.
  4. Al empezar cada vela M1 -> repasa el historial (ordenes usadas, trades cerrados), arma las ordenes con las velas
     H1 CERRADAS (una por nivel roto, vigente 8 h, rotacion de 5), y deja puestas las que corresponden (precio del
     lado de afuera segun el cierre M1 anterior). Si al abrir la vela el precio ya paso la STOP, entra a mercado con
     su SL/TP (el backtest la llena en la apertura). Si abrio mas alla del SL, la orden se descarta.
  Una orden queda USADA cuando se llena (comentario 'FR <clave>'). Al arrancar, el CALENTAMIENTO corre el mismo
  backtest sobre el historial reciente y marca como usadas las ordenes que ya se habrian operado antes de arrancar
  (el error del S/R del 10-nov-2026 no se repite).
"""
import csv
import json
import time
from datetime import datetime
from pathlib import Path

import pandas as pd

from .estrategia import EstrategiaFR, bloqueado, clave_de_comentario, corte_viernes, ventanas_de_texto

RAIZ = Path(__file__).resolve().parents[3]


class BotFR:
    def __init__(self, cfg: dict, papel: bool = True):
        if not papel:
            raise ValueError("BotFR solo corre en modo papel (no hay version para cuenta real todavia)")
        self.cfg = cfg
        m, e = cfg["mt5"], cfg["estrategia"]
        from .broker_papel import BrokerPapelFR
        self.broker = BrokerPapelFR(m["simbolo"], m.get("terminal"), 0, m.get("valor_punto_lote"),
                                    m.get("llenado", "return"),
                                    balance_inicial=cfg.get("papel", {}).get("balance_inicial",
                                                                             cfg["cuenta"]["balance_esperado"]))
        self.est_args = dict(W=e["W"], vig_h=e["vig_h"], buf=e["buf"], n_ext=e["n_ext"], RR=e["RR"],
                             max_niveles=e["max_niveles"], max_ordenes=e["max_ordenes"], izq=e["pivote_izq"],
                             der=e["pivote_der"], precio_ref=e["precio_ref"])
        self.noticias = cfg["horario"]["noticias_et"]
        self.ventanas = ventanas_de_texto(self.noticias)
        self.riesgo_pct = float(cfg["cuenta"]["riesgo_pct"])
        self.usados: set = set()
        self.registradas: set = set()
        self.ordenes, self.hora_h1 = [], None
        self.ultima_m1 = None
        self.posiciones_previas: dict = {}
        self.deseadas_previas = None
        self.ultimo_tablero = 0.0
        self.verbose = True
        self.dry_run = False

    # ------------------------------------------------------------------ registro
    def log(self, msg: str):
        linea = f"{datetime.now():%Y-%m-%d %H:%M:%S} | {msg}"
        if self.verbose:
            print(linea, flush=True)
        with open(self.dir_logs / "eventos.log", "a", encoding="utf-8") as f:
            f.write(linea + "\n")

    def guardar_estado(self):
        (self.dir_logs / "estado.json").write_text(json.dumps(
            {"usados": sorted(self.usados), "actualizado": f"{datetime.now():%Y-%m-%d %H:%M:%S}"}, indent=1))

    def registrar_trade(self, pid: int, previa: dict = None):
        if pid in self.registradas:
            return
        r = self.broker.resumen_posicion(pid)
        if r is None:
            return
        previa = previa or {}
        clave = clave_de_comentario(r["comentario_entrada"]) or previa.get("clave")
        sl = r.get("sl") or previa.get("sl")
        orden = r.get("orden") or previa.get("precio_orden") or r["entrada"]
        riesgo = abs(orden - sl) if sl else float("nan")
        d = 1 if r["lado"] == "long" else -1
        R = d * (r["salida"] - r["entrada"]) / riesgo if riesgo else float("nan")
        riesgo_dinero = riesgo * r["volumen"] * self.broker.valor_punto()
        R_neto = (r["profit"] + r["swap"] + r["comision"]) / riesgo_dinero if riesgo_dinero else float("nan")
        fila = {"position_id": pid, "clave": clave, **r, "orden": orden, "riesgo_pts": round(riesgo, 2),
                "R": round(R, 3), "R_neto": round(R_neto, 3)}
        f = self.dir_logs / "trades.csv"
        nuevo = not f.exists()
        with open(f, "a", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(fila))
            if nuevo:
                w.writeheader()
            w.writerow(fila)
        self.registradas.add(pid)
        self.log(f"CERRADO {r['lado']} {clave} entrada {r['entrada']} salida {r['salida']} ({r['comentario_salida']}) "
                 f"{R:+.2f}R | P&L {r['profit']:+.2f} swap {r['swap']:+.2f}")

    # ------------------------------------------------------------------ arranque
    def preparar(self, dir_logs=None) -> bool:
        ok, msg = self.broker.conectar()
        if not ok:
            print("ERROR:", msg)
            return False
        cta = self.broker.cuenta()
        self.dir_logs = Path(dir_logs) if dir_logs else RAIZ / "papel" / "estado" / "falsa_ruptura"
        self.dir_logs.mkdir(parents=True, exist_ok=True)
        self.broker.abrir_estado(self.dir_logs)
        self.log("MODO PAPEL: precios reales de esta terminal, ordenes VIRTUALES (no se envia nada al broker)")
        i = self.broker.info
        self.est = EstrategiaFR(**self.est_args, paso_precio=i.trade_tick_size or i.point)
        self.log(f"Cuenta {cta['login']} | {self.broker.simbolo} tick {i.trade_tick_size} | valor por punto y lote usado "
                 f"{self.broker.valor_punto():.4f} | riesgo {self.riesgo_pct:.2%} de {cta['balance']:,.2f}")
        self.log(f"Estrategia: falsa ruptura de pivotes H1 {self.est.izq}/{self.est.der}, {self.est.max_niveles} niveles, "
                 f"STOP en contra a W {self.est.W}, vigencia {self.est.vig}, SL espejo (4 velas + {self.est.buf}), "
                 f"RR {self.est.RR}, rotacion {self.est.max_ordenes} ordenes")
        f = self.dir_logs / "estado.json"
        if f.exists():
            self.usados |= set(json.loads(f.read_text()).get("usados", []))
        self.usados |= self.broker.claves_usadas()
        t = self.dir_logs / "trades.csv"
        if t.exists():
            self.registradas |= set(pd.read_csv(t).position_id.astype(int))
        for p in self.broker.posiciones():
            self._anotar_posicion(p)
        self._calentar_usados()
        self.log(f"Ordenes ya usadas: {len(self.usados)} | posiciones abiertas: {len(self.posiciones_previas)} | "
                 f"pendientes: {len(self.broker.pendientes())}")
        self.guardar_estado()
        return True

    def _calentar_usados(self):
        """El bot no sabe que ordenes ya se 'gastaron' antes de existir (una orden se opera una sola vez). Ejemplo real
        del S/R, 10-nov-2026: el papel arranco y opero un nivel que el backtest ya habia operado el 04-nov. Aca se corre
        el MISMO backtest (backtest.simular) sobre el historial M1 reciente del broker y se marcan como usadas todas las
        ordenes que esa simulacion lleno (tambien la de una posicion que la simulacion tendria abierta ahora)."""
        try:
            m1 = self.broker.velas("M1", 60000)
            if m1 is None or len(m1) < 20000:
                self.log("calentamiento: sin historial M1 suficiente, no se marcan ordenes usadas previas")
                return
            from .backtest import simular
            spread = float(m1.spread.median()) * (self.broker.info.point or 0.01) if "spread" in m1 else 2.1
            t = simular(m1.iloc[:-1][["time", "open", "high", "low", "close"]].reset_index(drop=True), self.est,
                        spread=spread, noticias=tuple(self.noticias), abierta=True)
            if not len(t):
                self.log("calentamiento: la simulacion no opero nada")
                return
            ahora = m1.time.iloc[-1]
            recientes = t[t.desde > ahora - self.est.vig - pd.Timedelta(days=1)]
            previos = set(recientes.clave) - self.usados
            self.usados |= set(t.clave)
            if previos:
                self.log(f"calentamiento: ordenes que el backtest ya opero antes de arrancar -> usadas: "
                         f"{', '.join(sorted(previos))}")
            else:
                self.log("calentamiento: ninguna orden vigente estaba usada antes de arrancar")
            ab = t[t.exit_reason == "abierta"]
            if len(ab):
                x = ab.iloc[0]
                self.log(f"calentamiento: OJO el backtest tendria ahora una posicion abierta ({x.direction} {x.clave} "
                         f"desde {x.entry_time:%d-%m %H:%M}); el papel no la abre (arranca sin posicion)")
        except Exception as ex:
            self.log(f"calentamiento: error {type(ex).__name__}: {ex} (sigue sin marcar ordenes previas)")

    def _anotar_posicion(self, p):
        k = clave_de_comentario(p.comment)
        if k and k not in self.usados:
            self.usados.add(k)
            self.guardar_estado()
        if p.identifier not in self.posiciones_previas:
            self.posiciones_previas[p.identifier] = {"clave": k, "sl": p.sl, "tp": p.tp,
                                                     "precio_orden": getattr(p, "orden", p.price_open)}
            self.log(f"ABIERTO {'long' if p.type == 0 else 'short'} {k} {p.volume} lotes a {p.price_open} "
                     f"SL {p.sl} TP {p.tp}")

    def _cancelar_todas(self):
        for o in self.broker.pendientes():
            ok, msg = self.broker.cancelar(o.ticket)
            self.log(f"cancelada {o.comment} ({msg})")

    # ------------------------------------------------------------------ ciclo
    def ciclo(self):
        tk = self.broker.tick()
        for a in self.broker.avisos:
            self.log(a)
        self.broker.avisos.clear()
        if tk is None:
            return
        ahora = tk["hora"]
        pos = self.broker.posiciones()
        abiertas = {p.identifier for p in pos}
        for pid in [x for x in self.posiciones_previas if x not in abiertas]:
            self.registrar_trade(pid, self.posiciones_previas.pop(pid))
        for p in pos:
            self._anotar_posicion(p)

        if corte_viernes(ahora):
            if self.broker.pendientes():
                self._cancelar_todas()
            for p in pos:
                ok, msg = self.broker.cerrar(p)
                self.log(f"cierre del viernes {p.comment}: {msg}")
            return
        if pos:
            if self.broker.pendientes():
                self._cancelar_todas()
            self._tablero(ahora, tk)
            return
        if bloqueado(ahora, self.ventanas):
            if self.broker.pendientes():
                self.log("noticias / fin de semana: cancelo pendientes")
                self._cancelar_todas()
            return

        m1 = self.broker.velas("M1", 3)
        if m1 is None or len(m1) < 2:
            return
        if m1.time.iloc[-1] == self.ultima_m1:
            self._tablero(ahora, tk)
            return
        self.ultima_m1 = m1.time.iloc[-1]
        cierre_ant = float(m1.close.iloc[-2])

        nuevos = self.broker.claves_usadas() - self.usados
        if nuevos:
            self.usados |= nuevos
            self.guardar_estado()
        for pid in self.broker.cerradas_recientes() - self.registradas:
            self.registrar_trade(pid)

        h1 = self.broker.velas("H1", 601)
        if h1 is not None and h1.time.iloc[-1] != self.hora_h1:
            self.ordenes = self.est.ordenes(h1)
            self.hora_h1 = h1.time.iloc[-1]
            nuevas = [o for o in self.ordenes if o.desde == self.hora_h1]
            for o in nuevas:
                self.log(f"RUPTURA {o.clave} nivel {o.nivel} (vela {o.t_vela:%d-%m %H:%M} cerro {o.cierre_ruptura}) -> "
                         f"{o.lado} {o.precio} SL {o.sl} TP {o.tp} riesgo {o.riesgo_pts:.1f} pts, vale hasta "
                         f"{o.hasta:%d-%m %H:%M}")
        vig = self.est.vigentes(self.ordenes, ahora, self.usados)
        spread = tk["ask"] - tk["bid"]
        deseadas = {o.clave: o for o in self.est.deseadas(vig, cierre_ant, spread)}
        if set(deseadas) != self.deseadas_previas:
            self.log("ordenes que corresponden: " + (", ".join(
                f"{o.lado} {o.clave} {o.precio} SL {o.sl} TP {o.tp}" for o in deseadas.values()) or "ninguna")
                + f" | vigentes: {', '.join(o.clave for o in vig) or '-'}")
            self.deseadas_previas = set(deseadas)

        puestas = {}
        for o in self.broker.pendientes():
            k = clave_de_comentario(o.comment)
            if k in deseadas and k not in puestas:
                puestas[k] = o
            else:
                self.broker.cancelar(o.ticket)
                self.log(f"cancelada {o.comment} (ya no corresponde)")
        bal = self.broker.cuenta()["balance"]

        # el precio ya paso la STOP al abrir la vela: el backtest la llena en la apertura -> a mercado
        cruzadas = sorted([o for k, o in deseadas.items() if k not in puestas and
                           ((o.lado == "sell_stop" and tk["bid"] <= o.precio) or
                            (o.lado == "buy_stop" and tk["ask"] >= o.precio))],
                          key=lambda o: abs((tk["bid"] if o.lado == "sell_stop" else tk["ask"]) - o.precio))
        for o in cruzadas:
            if (o.lado == "sell_stop" and tk["ask"] >= o.sl) or (o.lado == "buy_stop" and tk["bid"] <= o.sl):
                self.usados.add(o.clave)
                self.guardar_estado()
                self.log(f"{o.clave}: el precio abrio mas alla del SL, orden descartada")
                continue
            vol = self.broker.volumen(bal * self.riesgo_pct, o.riesgo_pts)
            if vol <= 0:
                continue
            ok, msg = self.broker.abrir_mercado(o, vol)
            self.log(f"{'ENTRADA A MERCADO' if ok else 'FALLO a mercado'} {o.lado} {o.clave} {vol} lotes (STOP "
                     f"{o.precio} ya cruzada) SL {o.sl} TP {o.tp} {msg}")
            if ok:
                self._cancelar_todas()
                return

        for k, o in deseadas.items():
            if k in puestas or not self.broker.orden_valida(o, tk["bid"], tk["ask"]):
                continue
            vol = self.broker.volumen(bal * self.riesgo_pct, o.riesgo_pts)
            if vol <= 0:
                self.log(f"{k}: volumen menor al minimo con riesgo {self.riesgo_pct:.2%}, no se pone")
                continue
            ok, msg = self.broker.poner_orden(o, vol)
            self.log(f"{'PUESTA' if ok else 'FALLO'} {o.lado} {k} {vol} lotes a {o.precio} SL {o.sl} TP {o.tp} "
                     f"(riesgo {o.riesgo_pts:.1f} pts, vale hasta {o.hasta:%d-%m %H:%M}) {msg}")
        self._tablero(ahora, tk)

    def _tablero(self, ahora, tk):
        if time.time() - self.ultimo_tablero < 900:
            return
        self.ultimo_tablero = time.time()
        c = self.broker.cuenta()
        self.log(f"[estado] servidor {ahora:%a %H:%M} | bid {tk['bid']} | balance {c['balance']:,.2f} equity "
                 f"{c['equity']:,.2f} | posiciones {len(self.broker.posiciones())} | pendientes "
                 f"{len(self.broker.pendientes())} | usadas {len(self.usados)}")
