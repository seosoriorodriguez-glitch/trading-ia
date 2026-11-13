# -*- coding: utf-8 -*-
"""
Bot S/R Pivot al toque H1 (solo ordenes LIMIT). La logica de decision esta en estrategia.py (probada contra el
backtest con herramientas/paridad.py); el bot entero se prueba contra un MT5 falso con herramientas/simulacro.py.

Ciclo (cada ~2 s):
  1. Archivo STOP -> cancela sus pendientes y sale. La posicion abierta queda con su SL/TP (no se cierra).
  2. Corte del viernes -> cancela pendientes y cierra la posicion (como el backtest).
  3. Con posicion abierta -> sin pendientes (1 posicion a la vez). Si un gap (o un movimiento muy rapido) lleno dos
     ordenes a la vez, se queda con la que el backtest habria llenado (la orden mas cercana a su precio de llenado) y
     cierra las otras; sus niveles quedan sin usar, como en el backtest (13-nov-2026).
  4. Noticias 08:26-08:34 ET o fin de semana -> sin pendientes.
  5. Al empezar cada vela M1 -> repasa el historial (niveles usados, trades cerrados), calcula las ordenes que deberian
     estar (niveles activos no usados, del lado de afuera segun el cierre M1 anterior) y pone/cancela para que MT5
     quede igual. Si el precio ya paso una orden al abrir la vela, entra a mercado con su SL/TP (el backtest la
     llena en la apertura, como una limite que ya estaba puesta). Si abrio mas alla del SL, descarta el nivel.
  Un nivel queda USADO cuando su orden se llena (comentario 'SR <clave>' en la posicion y en el historial; ademas se
  guarda en estado.json). Al reiniciar se reconstruye del historial: nunca se opera dos veces el mismo nivel.
Arreglos de la auditoria del 10-nov-2026 (alinean el bot con el backtest en situaciones especiales):
  - Arranque: el calentamiento corre el backtest sobre el historial; si el backtest tiene una posicion ABIERTA ahora,
    su nivel queda usado y el bot queda ocupado por esa "posicion sombra" (no abre nada) hasta que habria cerrado.
  - En el minuto en que cierra una posicion (o en el que arranca) no se decide nada: el backtest espera la vela
    siguiente.
  - Corte de fin de semana con feriados (papel/calendario.py); si el bot estuvo apagado durante un corte, al volver
    cierra la posicion abierta antes de ese corte.
  - Una orden que no se puede poner queda en el log.
Riesgo: `cuenta.riesgo_fijo` (dinero por trade, como el bot OB de Darwinex: $500 = 0.5 % de los 100k iniciales) o, si
no esta, `riesgo_pct` x balance actual.
"""
import csv
import json
import time
from datetime import datetime
from pathlib import Path

import pandas as pd

from .broker_mt5 import BrokerMT5
from .estrategia import EstrategiaSR, bloqueado, clave_de_comentario, corte_viernes, ultimo_corte, ventanas_de_texto

RAIZ = Path(__file__).resolve().parents[3]


class BotSR:
    def __init__(self, cfg: dict, dry_run: bool = False, papel: bool = False):
        self.cfg = cfg
        self.dry_run = dry_run
        m, e = cfg["mt5"], cfg["estrategia"]
        if papel:
            from .broker_papel import BrokerPapel
            self.broker = BrokerPapel(m["simbolo"], m.get("terminal"), m["magic"], m.get("valor_punto_lote"),
                                      m.get("llenado", "return"),
                                      balance_inicial=cfg.get("papel", {}).get("balance_inicial",
                                                                               cfg["cuenta"]["balance_esperado"]))
        else:
            self.broker = BrokerMT5(m["simbolo"], m.get("terminal"), m["magic"], m.get("valor_punto_lote"),
                                    m.get("llenado", "return"))
        self.est_args = dict(W=e["W"], S=e["S"], RR=e["RR"], max_niveles=e["max_niveles"], izq=e["pivote_izq"],
                             der=e["pivote_der"], precio_ref=e["precio_ref"])
        self.noticias = cfg["horario"]["noticias_et"]
        self.ventanas = ventanas_de_texto(self.noticias)
        self.feriados = bool(cfg["horario"].get("feriados", True))
        self.sombra = None                 # posicion abierta del backtest al arrancar (ver _calentar_usados)
        self.ultima_salida = None          # hora de la ultima salida registrada
        self.ultimo_balance = None
        self.riesgo_pct = float(cfg["cuenta"]["riesgo_pct"])
        self.riesgo_fijo = cfg["cuenta"].get("riesgo_fijo")       # dinero fijo por trade (None = riesgo_pct x balance)
        self.stop_file = RAIZ / cfg["archivos"]["stop"]
        self.usados: set = set()
        self.liberadas: set = set()        # posiciones cerradas por doble llenado: su nivel no cuenta como usado
        self.registradas: set = set()
        self.niveles, self.hora_h1 = [], None
        self.ultima_m1 = None
        self.posiciones_previas: dict = {}
        self.deseadas_previas = None
        self.ultimo_tablero = 0.0
        self.verbose = True

    # ------------------------------------------------------------------ registro
    def log(self, msg: str):
        linea = f"{datetime.now():%Y-%m-%d %H:%M:%S} | {msg}"
        if self.verbose:
            print(linea, flush=True)
        with open(self.dir_logs / "eventos.log", "a", encoding="utf-8") as f:
            f.write(linea + "\n")

    def guardar_estado(self):
        (self.dir_logs / "estado.json").write_text(json.dumps(
            {"usados": sorted(self.usados), "liberadas": sorted(self.liberadas),
             "actualizado": f"{datetime.now():%Y-%m-%d %H:%M:%S}"}, indent=1))

    def riesgo_dinero(self, balance: float) -> float:
        return float(self.riesgo_fijo) if self.riesgo_fijo else balance * self.riesgo_pct

    def texto_riesgo(self) -> str:
        return f"${float(self.riesgo_fijo):,.0f} fijo por trade" if self.riesgo_fijo else f"{self.riesgo_pct:.2%} del balance"

    def _cerrar_sobrantes(self, pos):
        """MT5 llena TODAS las pendientes que un gap (o un movimiento muy rapido) cruza; el backtest llena una sola: la
        mas cercana a la apertura. La apertura se aproxima con el precio del PRIMER llenado (en un gap, todas las cruzadas
        se llenan a ese precio): se queda la posicion cuya orden esta mas cerca de el (a igual distancia, la primera) y
        se cierran las demas a mercado. Sus niveles quedan sin usar, como en el backtest."""
        ref = min(pos, key=lambda p: p.time_msc).price_open

        def clave_orden(p):
            prev = self.posiciones_previas.get(p.identifier, {})
            return round(abs(prev.get("precio_orden", p.price_open) - ref)), p.time_msc
        orden = sorted(pos, key=clave_orden)
        queda = self.posiciones_previas.get(orden[0].identifier, {}).get("clave")
        for p in orden[1:]:
            k = self.posiciones_previas.get(p.identifier, {}).get("clave")
            ok, msg = self.broker.cerrar(p) if not self.dry_run else (True, "dry")
            if ok and not self.dry_run:
                self.liberadas.add(int(p.identifier))
                if k:
                    self.usados.discard(k)
                self.guardar_estado()
            self.log(f"se llenaron {len(pos)} ordenes a la vez (gap): queda {queda}, cierro {k} ({msg}); el nivel {k} "
                     f"queda sin usar, como en el backtest")

    def _orden_de_clave(self, clave):
        n = next((x for x in self.niveles if x.clave == clave), None)
        return self.est.orden(n) if n else None

    def registrar_trade(self, pid: int, previa: dict = None):
        if pid in self.registradas:
            return
        r = self.broker.resumen_posicion(pid)
        if r is None:
            return                                   # el historial aun no lo trae: se reintenta en la proxima vela
        previa = previa or {}
        clave = clave_de_comentario(r["comentario_entrada"]) or previa.get("clave")
        sl = r.get("sl") or previa.get("sl")
        o = self._orden_de_clave(clave)
        orden = o.precio if o else (r.get("orden") or previa.get("precio_orden", r["entrada"]))
        riesgo = abs(orden - sl) if sl else float("nan")
        d = 1 if r["lado"] == "long" else -1
        R = d * (r["salida"] - r["entrada"]) / riesgo if riesgo else float("nan")
        mov = d * (r["salida"] - r["entrada"]) * r["volumen"]
        vp_real = r["profit"] / mov if mov else float("nan")
        riesgo_dinero = riesgo * r["volumen"] * (vp_real if vp_real == vp_real and vp_real > 0 else self.broker.valor_punto())
        R_neto = (r["profit"] + r["swap"] + r["comision"]) / riesgo_dinero if riesgo_dinero else float("nan")
        fila = {"position_id": pid, "clave": clave, **r, "orden": orden, "riesgo_pts": round(riesgo, 2),
                "R": round(R, 3), "R_neto": round(R_neto, 3), "valor_punto_observado": round(vp_real, 4),
                "valor_punto_usado": self.broker.valor_punto()}
        f = self.dir_logs / "trades.csv"
        nuevo = not f.exists()
        with open(f, "a", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(fila))
            if nuevo:
                w.writeheader()
            w.writerow(fila)
        self.registradas.add(pid)
        sal = pd.Timestamp(r["salida_hora"])
        self.ultima_salida = sal if self.ultima_salida is None else max(self.ultima_salida, sal)
        self.log(f"CERRADO {r['lado']} {clave} entrada {r['entrada']} salida {r['salida']} "
                 f"({r['comentario_salida']}) {R:+.2f}R | P&L {r['profit']:+.2f} com {r['comision']:+.2f} swap {r['swap']:+.2f}")
        vp = self.broker.valor_punto()
        if vp_real == vp_real and abs(vp_real / vp - 1) > 0.2:
            self.log(f"OJO valor por punto: el bot usa {vp:.4f} por punto y lote, este trade dio {vp_real:.4f}. "
                     f"Revisar 'valor_punto_lote' en el config: el riesgo real no es el configurado.")

    # ------------------------------------------------------------------ arranque
    def iniciar(self):
        if not self.preparar():
            return
        try:
            while True:
                if self.stop_file.exists():
                    self.log(f"{self.stop_file.name} detectado: cancelo pendientes y salgo (la posicion abierta, si "
                             f"hay, queda con su SL/TP)")
                    self._cancelar_todas()
                    break
                try:
                    self.ciclo()
                except Exception as ex:                       # un error de red no debe tumbar el bot
                    self.log(f"ERROR en el ciclo: {type(ex).__name__}: {ex}")
                    time.sleep(10)
                time.sleep(2)
        except KeyboardInterrupt:
            self.log("Detenido con Ctrl+C (pendientes y posicion quedan como estan)")
        finally:
            self.broker.desconectar()

    def preparar(self, dir_logs=None) -> bool:
        """Conecta, valida la cuenta y reconstruye el estado. False si no debe arrancar."""
        ok, msg = self.broker.conectar()
        if not ok:
            print("ERROR:", msg)
            return False
        cta = self.broker.cuenta()
        self.dir_logs = Path(dir_logs) if dir_logs else RAIZ / self.cfg["archivos"]["logs"] / str(cta["login"])
        self.dir_logs.mkdir(parents=True, exist_ok=True)
        if hasattr(self.broker, "abrir_estado"):             # modo papel: ordenes y posiciones virtuales
            self.broker.abrir_estado(self.dir_logs)
            self.log("MODO PAPEL: precios reales de esta terminal, ordenes VIRTUALES (no se envia nada al broker)")
        esperado = float(self.cfg["cuenta"]["balance_esperado"])
        ratio = cta["balance"] / esperado if esperado else 0
        self.log(f"Cuenta #{cta['login']} {cta['server']} | balance {cta['balance']:,.2f} {cta['moneda']} | "
                 f"apalancamiento 1:{cta['apalancamiento']}")
        if not 0.5 <= ratio <= 2.0:
            self.log(f"ABORTADO: el balance no cuadra con balance_esperado={esperado:,.0f}. Revisa terminal y config.")
            self.broker.desconectar()
            return False
        i = self.broker.info
        self.est = EstrategiaSR(**self.est_args, paso_precio=i.trade_tick_size or i.point)
        # el broker de papel aplica corte y noticias aunque el bot no corra (al relanzar tras una caida)
        self.broker.reglas = lambda hora: (bloqueado(hora, self.ventanas, self.feriados),
                                           corte_viernes(hora, self.feriados))
        self.log(f"{self.broker.simbolo}: digitos {i.digits}, tick {i.trade_tick_size}, lote min {i.volume_min} "
                 f"paso {i.volume_step} | valor por punto y lote: MT5 {self.broker.valor_punto_mt5():.4f}, "
                 f"usado {self.broker.valor_punto():.4f} | magic {self.broker.magic} | riesgo {self.texto_riesgo()}")
        self.log(f"Estrategia: pivotes H1 {self.est.izq}/{self.est.der}, {self.est.max_niveles} niveles, W {self.est.W}, "
                 f"S {self.est.S} (a precio {self.est.precio_ref:,.0f}), RR {self.est.RR}, solo LIMIT"
                 + (" | DRY RUN: no se envian ordenes" if self.dry_run else ""))
        f = self.dir_logs / "estado.json"
        if f.exists():
            est = json.loads(f.read_text())
            self.usados |= set(est.get("usados", []))
            self.liberadas |= {int(x) for x in est.get("liberadas", [])}
        self.usados |= self.broker.claves_usadas(excluir=self.liberadas)
        t = self.dir_logs / "trades.csv"
        if t.exists():
            self.registradas |= set(pd.read_csv(t).position_id.astype(int))
        for p in self.broker.posiciones():
            self._anotar_posicion(p)
        self._calentar_usados()
        m1 = self.broker.velas("M1", 1)
        if m1 is not None and len(m1):
            self.ultima_m1 = m1.time.iloc[-1]          # el minuto del arranque no se decide: se espera la vela siguiente
        self.log(f"Niveles ya usados: {len(self.usados)} | posiciones abiertas: {len(self.posiciones_previas)} | "
                 f"pendientes: {len(self.broker.pendientes())}")
        self.guardar_estado()
        return True

    def _calentar_usados(self):
        """Al arrancar, el bot no sabe que niveles ya se 'gastaron' antes de que existiera (un nivel se opera una sola
        vez). Ejemplo real, 10-nov-2026: la resistencia del 02-nov se toco por primera vez el 04-nov (el backtest la opera
        y pierde ahi), pero el papel arranco el 10-nov y la opero de nuevo. Para empezar alineado con el backtest se corre
        la MISMA logica (backtest.simular) sobre el historial reciente del broker, desde 3 dias antes del pivote mas
        antiguo de los niveles vivos, y se marcan como usados los niveles vivos que esa simulacion ya opero."""
        try:
            h1 = self.broker.velas("H1", 601)
            if h1 is None or len(h1) < 40:
                return
            activos = self.est.activos(self.est.niveles(h1), h1.time.iloc[-1])
            if not activos:
                return
            desde = min(n.pivote for n in activos) - pd.Timedelta(days=10)
            minutos = int((h1.time.iloc[-1] - desde).total_seconds() // 60) + 120
            m1 = self.broker.velas("M1", min(minutos, 99000))
            if m1 is None or len(m1) < 1000:
                self.log("calentamiento: sin historial M1 suficiente, no se marcan niveles usados previos")
                return
            from .backtest import simular
            pt = self.broker.info.point or 0.01
            m1 = m1.iloc[:-1].reset_index(drop=True)
            spread = (m1.spread.values * pt) if "spread" in m1 else 2.1
            t = simular(m1[["time", "open", "high", "low", "close"]], self.est, spread=spread,
                        noticias=tuple(self.noticias), feriados=self.feriados, abierta=True)
            vivos = {n.clave for n in activos}
            ab = t[t.exit_reason == "abierta"] if len(t) else t
            previos = (((set(t.clave) & vivos) | set(ab.clave)) - self.usados) if len(t) else set()
            if previos:
                self.usados |= previos
                self.log(f"calentamiento: niveles que el backtest ya opero antes de arrancar -> usados: "
                         f"{', '.join(sorted(previos))}")
            else:
                self.log("calentamiento: ningun nivel vivo estaba usado antes de arrancar")
            if len(ab) and not self.broker.posiciones():
                x = ab.iloc[0]
                self.sombra = {"dir": 1 if x.direction == "long" else -1, "sl": float(x.sl), "tp": float(x.tp),
                               "clave": x.clave, "entrada": pd.Timestamp(x.entry_time)}
                self.log(f"calentamiento: el backtest tiene ahora una posicion abierta ({x.direction} {x.clave} desde "
                         f"{x.entry_time:%d-%m %H:%M}, SL {x.sl} TP {x.tp}): el bot queda ocupado sin operar hasta "
                         f"que esa posicion habria cerrado (posicion sombra)")
        except Exception as ex:
            self.log(f"calentamiento: error {type(ex).__name__}: {ex} (sigue sin marcar niveles previos)")

    def _anotar_posicion(self, p):
        k = clave_de_comentario(p.comment)
        if k is None and self.niveles:
            # el broker borro el comentario: el nivel es el de la orden mas cercana al precio de entrada, mismo lado
            lado = "buy_limit" if p.type == 0 else "sell_limit"
            cands = [o for o in (self.est.orden(n) for n in self.niveles) if o.lado == lado]
            if cands:
                o = min(cands, key=lambda x: abs(x.precio - p.price_open))
                if abs(o.precio - p.price_open) <= 30 * o.nivel / self.est.precio_ref:
                    k = o.clave
                    if p.identifier not in self.posiciones_previas:
                        self.log(f"posicion {p.identifier} sin comentario: la asigno al nivel {k}")
        if k and k not in self.usados:
            self.usados.add(k)
            self.guardar_estado()
        if p.identifier not in self.posiciones_previas:
            o = self._orden_de_clave(k)
            self.posiciones_previas[p.identifier] = {"clave": k, "sl": p.sl, "tp": p.tp,
                                                     "precio_orden": o.precio if o else p.price_open}
            self.log(f"ABIERTO {'long' if p.type == 0 else 'short'} {k} {p.volume} lotes a {p.price_open} "
                     f"SL {p.sl} TP {p.tp}")

    def _sombra_sigue(self, ahora, tk) -> bool:
        """True mientras la posicion del backtest que habia al arrancar seguiria abierta (SL, TP o corte)."""
        x = self.sombra
        m1 = self.broker.velas("M1", 2)
        hi = lo = None
        if m1 is not None and len(m1) >= 2:
            hi, lo = float(m1.high.iloc[-2]), float(m1.low.iloc[-2])
        sp = tk["ask"] - tk["bid"]
        if x["dir"] == 1:
            fuera = tk["bid"] <= x["sl"] or tk["bid"] >= x["tp"] or (lo is not None and (lo <= x["sl"] or hi >= x["tp"]))
        else:
            fuera = tk["ask"] >= x["sl"] or tk["ask"] <= x["tp"] or (hi is not None and (hi + sp >= x["sl"]
                                                                                        or lo + sp <= x["tp"]))
        if fuera or ultimo_corte(ahora, self.feriados) > x["entrada"]:
            self.log(f"posicion sombra del backtest ({x['clave']}) cerrada: el bot vuelve a operar desde la vela "
                     f"siguiente")
            return False
        return True

    def _cancelar_todas(self):
        for o in self.broker.pendientes():
            if not self.dry_run:
                ok, msg = self.broker.cancelar(o.ticket)
                self.log(f"cancelada {o.comment} ({msg})")

    # ------------------------------------------------------------------ ciclo
    def ciclo(self):
        tk = self.broker.tick()
        for a in getattr(self.broker, "avisos", []):
            self.log(a)
        if hasattr(self.broker, "avisos"):
            self.broker.avisos.clear()
        if tk is None:
            return
        ahora = tk["hora"]
        pos = self.broker.posiciones()
        abiertas = {p.identifier for p in pos}
        cerradas = [x for x in self.posiciones_previas if x not in abiertas]
        for pid in cerradas:
            self.registrar_trade(pid, self.posiciones_previas.pop(pid))
            if pid not in self.registradas:
                # el historial aun no trae la salida: por las dudas no se decide en este minuto. Si se registro, la
                # hora real de salida (ultima_salida) es la que bloquea ese minuto, como el backtest.
                self.ultima_m1 = ahora.floor("min")
        for p in pos:
            self._anotar_posicion(p)

        en_corte = corte_viernes(ahora, self.feriados)
        corte = ultimo_corte(ahora, self.feriados)
        viejas = [] if en_corte else [p for p in pos if pd.Timestamp(p.time_msc, unit="ms") < corte]
        if en_corte or viejas:
            if self.broker.pendientes():
                self._cancelar_todas()
            for p in (pos if en_corte else viejas):
                ok, msg = self.broker.cerrar(p) if not self.dry_run else (True, "dry")
                nota = f" (abierta antes del corte del {corte:%d-%m %H:%M}: el bot estuvo apagado)" if viejas else ""
                self.log(f"cierre de fin de semana {p.comment}{nota}: {msg}")
            return
        if self.sombra is not None and not pos:
            if self._sombra_sigue(ahora, tk):
                if self.broker.pendientes():
                    self._cancelar_todas()
                self._tablero(ahora, tk)
                return
            self.sombra = None
            self.ultima_m1 = ahora.floor("min")
        if pos:
            self._cancelar_todas()
            if len(pos) > 1:
                self._cerrar_sobrantes(pos)
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

        # historial: posiciones que se abrieron y cerraron entre dos vueltas (nivel usado + registro del trade)
        nuevos = self.broker.claves_usadas(dias=10, excluir=self.liberadas) - self.usados
        if nuevos:
            self.usados |= nuevos
            self.guardar_estado()
        for pid in self.broker.cerradas_recientes(dias=10) - self.registradas:
            self.registrar_trade(pid)
        self.ultima_m1 = m1.time.iloc[-1]
        if self.ultima_salida is not None and self.ultima_salida.floor("min") >= self.ultima_m1:
            return                                       # cerro una posicion en este minuto: se espera la vela siguiente
        cierre_ant = float(m1.close.iloc[-2])

        h1 = self.broker.velas("H1", 601)
        if h1 is not None and h1.time.iloc[-1] != self.hora_h1:
            self.niveles = self.est.niveles(h1)
            self.hora_h1 = h1.time.iloc[-1]
        activos = self.est.activos(self.niveles, ahora)
        spread = tk["ask"] - tk["bid"]
        deseadas = {o.clave: o for o in self.est.deseadas(activos, self.usados, cierre_ant, spread)}
        if set(deseadas) != self.deseadas_previas:
            self.log("ordenes que corresponden: " + (", ".join(
                f"{o.lado} {o.clave} {o.precio} SL {o.sl} TP {o.tp}" for o in deseadas.values()) or "ninguna")
                + f" | activos: {', '.join(n.clave + ' ' + str(n.precio) for n in activos)}")
            self.deseadas_previas = set(deseadas)
        if self.dry_run:
            return

        puestas = {}
        for o in self.broker.pendientes():
            k = clave_de_comentario(o.comment)
            if k in deseadas and k not in puestas:
                puestas[k] = o
            else:
                ok, msg = self.broker.cancelar(o.ticket)
                self.log(f"cancelada {o.comment} (ya no corresponde) {msg}")
        c = self.broker.cuenta()
        if c is not None:
            self.ultimo_balance = c["balance"]
        bal = self.ultimo_balance
        if bal is None:
            return

        # el precio ya paso la orden al abrir la vela: el backtest la llena en la apertura -> a mercado
        cruzadas = sorted([o for k, o in deseadas.items() if k not in puestas and
                           ((o.lado == "buy_limit" and tk["ask"] <= o.precio) or
                            (o.lado == "sell_limit" and tk["bid"] >= o.precio))],
                          key=lambda o: abs((tk["ask"] if o.lado == "buy_limit" else tk["bid"]) - o.precio))
        for o in cruzadas:
            if (o.lado == "buy_limit" and tk["bid"] <= o.sl) or (o.lado == "sell_limit" and tk["ask"] >= o.sl):
                self.usados.add(o.clave)
                self.guardar_estado()
                self.log(f"{o.clave}: el precio abrio mas alla del SL, nivel descartado")
                continue
            vol = self.broker.volumen(self.riesgo_dinero(bal), o.riesgo_pts)
            if vol <= 0:
                continue
            ok, msg = self.broker.abrir_mercado(o, vol)
            self.log(f"{'ENTRADA A MERCADO' if ok else 'FALLO a mercado'} {o.lado} {o.clave} {vol} lotes (orden "
                     f"{o.precio} ya cruzada) SL {o.sl} TP {o.tp} {msg}")
            if ok:
                self._cancelar_todas()
                return

        for k, o in deseadas.items():
            if k in puestas:
                continue
            if not self.broker.orden_valida(o, tk["bid"], tk["ask"]):
                self.log(f"{k}: {o.lado} {o.precio} no se puede poner ahora (bid {tk['bid']} ask {tk['ask']}: muy "
                         f"cerca o cruzada); se reintenta en la proxima vela")
                continue
            vol = self.broker.volumen(self.riesgo_dinero(bal), o.riesgo_pts)
            if vol <= 0:
                self.log(f"{k}: volumen menor al minimo con riesgo {self.texto_riesgo()}, no se pone")
                continue
            ok_m, margen = self.broker.margen_ok(o, vol)
            if not ok_m:
                self.log(f"{k}: margen insuficiente ({margen:,.0f}) para {vol} lotes, no se pone")
                continue
            ok, msg = self.broker.poner_limit(o, vol)
            self.log(f"{'PUESTA' if ok else 'FALLO'} {o.lado} {k} {vol} lotes a {o.precio} SL {o.sl} TP {o.tp} "
                     f"(riesgo {o.riesgo_pts:.1f} pts) {msg}")
        self._tablero(ahora, tk)

    def _tablero(self, ahora, tk):
        if time.time() - self.ultimo_tablero < 900:
            return
        self.ultimo_tablero = time.time()
        c = self.broker.cuenta()
        self.log(f"[estado] servidor {ahora:%a %H:%M} | bid {tk['bid']} | balance {c['balance']:,.2f} equity "
                 f"{c['equity']:,.2f} | posiciones {len(self.broker.posiciones())} | pendientes "
                 f"{len(self.broker.pendientes())} | usados {len(self.usados)}")
