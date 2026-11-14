# -*- coding: utf-8 -*-
"""
Bot de la FALSA RUPTURA de pivotes H1 (ordenes STOP). Dos modos:
  papel  precios reales de la terminal, ordenes virtuales (broker_papel.py); lo corre papel/runner.py.
  real   ordenes STOP en MT5 (broker_mt5.py), con su magic; se lanza con run_bot.py (13-nov-2026).
La logica de decision esta en estrategia.py (probada contra la investigacion con herramientas/paridad.py); el bot entero
se prueba con herramientas/prueba_papel.py (papel) y herramientas/simulacro.py (contra un MT5 falso, modo real).

Ciclo (cada ~2 s):
  1. Corte del viernes -> cancela pendientes y cierra la posicion (como el backtest).
  2. Con posicion abierta -> sin pendientes (1 posicion a la vez). Si un gap lleno dos STOP a la vez (MT5 llena todas
     las cruzadas, el backtest una), se queda con la del backtest y cierra las otras; sus ordenes quedan sin usar.
  3. Noticias 08:26-08:34 ET o fin de semana -> sin pendientes.
  4. Al empezar cada vela M1 -> repasa el historial (ordenes usadas, trades cerrados), arma las ordenes con las velas
     H1 CERRADAS (una por nivel roto, vigente 8 h, rotacion de 5), y deja puestas las que corresponden (precio del
     lado de afuera segun el cierre M1 anterior). Si al abrir la vela el precio ya paso la STOP, entra a mercado con
     su SL/TP (el backtest la llena en la apertura). Si abrio mas alla del SL, la orden se descarta.
  Una orden queda USADA cuando se llena (comentario 'FR <clave>'). Al arrancar, el CALENTAMIENTO corre el mismo
  backtest sobre el historial reciente y marca como usadas las ordenes que ya se habrian operado antes de arrancar
  (el error del S/R del 10-nov-2026 no se repite).
Arreglos de la auditoria del 10-nov-2026:
  - Si al arrancar el backtest tiene una posicion ABIERTA, el bot queda ocupado por esa "posicion sombra" (no abre
    nada) hasta que habria cerrado, como el backtest.
  - En el minuto en que cierra una posicion (o en el que arranca) no se decide nada.
  - Corte de fin de semana con feriados (papel/calendario.py); si el bot estuvo apagado durante un corte, al volver
    cierra la posicion abierta antes de ese corte. Las pendientes vencen solas en el broker de papel (8 h).
  - Una orden que no se puede poner queda en el log.
Riesgo: cuenta.riesgo_fijo (dinero por trade, como el bot OB de Darwinex) o, si no esta, riesgo_pct x balance.
Robustez en cuenta real (auditoria del 14-nov-2026), igual que el S/R:
  - reconecta si la terminal se reinicia; avisa si MT5 deja de dar precios;
  - cada STOP vence a la hora mas temprana entre su `hasta` (8 h) y el corte de fin de semana;
  - "del lado de afuera" usa el spread de la vela M1 anterior (como el backtest), no el del tick;
  - una STOP que el broker no deja poner por estar muy cerca del precio (o que rechaza porque el precio se movio) se
    VIGILA el resto del minuto y entra a mercado si el precio la cruza (el 28-34 % de los trades se llenan en el primer
    minuto en que la orden queda del lado de afuera, casi siempre a <= 10 pts);
  - ticket de cada orden -> clave en estado.json: respaldo si el broker borra el comentario;
  - la hora de la vela nueva manda sobre la del tick; cuenta (login) del config verificada; un solo bot por magic.
"""
import csv
import json
import time
from datetime import datetime
from pathlib import Path

import pandas as pd

from papel.calendario import corte_de_la_semana
from papel.estrategias.sr_pivot_h1.broker_mt5 import PRECIO_INVALIDO

from .estrategia import EstrategiaFR, bloqueado, clave_de_comentario, corte_viernes, ultimo_corte, ventanas_de_texto

RAIZ = Path(__file__).resolve().parents[3]


class BotFR:
    def __init__(self, cfg: dict, papel: bool = True, dry_run: bool = False):
        self.cfg = cfg
        self.papel = papel
        m, e = cfg["mt5"], cfg["estrategia"]
        if papel:
            from .broker_papel import BrokerPapelFR
            self.broker = BrokerPapelFR(m["simbolo"], m.get("terminal"), 0, m.get("valor_punto_lote"),
                                        m.get("llenado", "return"),
                                        balance_inicial=cfg.get("papel", {}).get("balance_inicial",
                                                                                 cfg["cuenta"]["balance_esperado"]))
        else:
            from .broker_mt5 import BrokerMT5FR
            self.broker = BrokerMT5FR(m["simbolo"], m.get("terminal"), m["magic"], m.get("valor_punto_lote"),
                                      m.get("llenado", "return"))
        self.est_args = dict(W=e["W"], vig_h=e["vig_h"], buf=e["buf"], n_ext=e["n_ext"], RR=e["RR"],
                             max_niveles=e["max_niveles"], max_ordenes=e["max_ordenes"], izq=e["pivote_izq"],
                             der=e["pivote_der"], precio_ref=e["precio_ref"])
        self.noticias = cfg["horario"]["noticias_et"]
        self.ventanas = ventanas_de_texto(self.noticias)
        self.feriados = bool(cfg["horario"].get("feriados", True))
        self.sombra = None                 # posicion abierta del backtest al arrancar (ver _calentar_usados)
        self.ultima_salida = None
        self.ultimo_balance = None
        self.riesgo_pct = float(cfg["cuenta"]["riesgo_pct"])
        self.riesgo_fijo = cfg["cuenta"].get("riesgo_fijo")       # dinero fijo por trade (None = riesgo_pct x balance)
        self.usados: set = set()
        self.liberadas: set = set()        # posiciones cerradas por doble llenado: su orden no cuenta como usada
        self.tickets: dict = {}            # ticket de la orden (= id de la posicion que abre) -> clave
        self.vigilar: dict = {}            # clave -> STOP que no se pudo poner este minuto (muy cerca del precio)
        self.login = cfg["cuenta"].get("login")
        self._avisos: dict = {}
        self.registradas: set = set()
        self.ordenes, self.hora_h1 = [], None
        self.ultima_m1 = None
        self.posiciones_previas: dict = {}
        self.deseadas_previas = None
        self.ultimo_tablero = 0.0
        self.verbose = True
        self.dry_run = dry_run

    # ------------------------------------------------------------------ registro
    def log(self, msg: str):
        linea = f"{datetime.now():%Y-%m-%d %H:%M:%S} | {msg}"
        if self.verbose:
            print(linea, flush=True)
        with open(self.dir_logs / "eventos.log", "a", encoding="utf-8") as f:
            f.write(linea + "\n")

    def guardar_estado(self):
        tickets = dict(list(self.tickets.items())[-500:])
        (self.dir_logs / "estado.json").write_text(json.dumps(
            {"usados": sorted(self.usados), "liberadas": sorted(self.liberadas), "tickets": tickets,
             "actualizado": f"{datetime.now():%Y-%m-%d %H:%M:%S}"}, indent=1))

    def aviso(self, tema: str, msg: str, cada_s: float = 600):
        """Log que no se repite mas de una vez cada `cada_s` segundos (fallos que se reintentan cada 2 s)."""
        if time.time() - self._avisos.get(tema, 0) >= cada_s:
            self._avisos[tema] = time.time()
            self.log(msg)

    def _anotar_ticket(self, clave: str):
        t = getattr(self.broker, "ultimo_ticket", None)
        if t is not None and clave:
            self.tickets[str(t)] = clave
            self.guardar_estado()

    def _clave(self, comentario, ticket) -> str:
        return clave_de_comentario(comentario) or self.tickets.get(str(ticket))

    @staticmethod
    def proximo_corte(ahora: pd.Timestamp) -> pd.Timestamp:
        c = corte_de_la_semana(ahora)
        return c if c > ahora else corte_de_la_semana(ahora + pd.Timedelta(days=7))

    def riesgo_dinero(self, balance: float) -> float:
        return float(self.riesgo_fijo) if self.riesgo_fijo else balance * self.riesgo_pct

    def texto_riesgo(self) -> str:
        return f"${float(self.riesgo_fijo):,.0f} fijo por trade" if self.riesgo_fijo else f"{self.riesgo_pct:.2%} del balance"

    def _orden_de_clave(self, clave):
        return next((o for o in reversed(self.ordenes) if o.clave == clave), None)

    def _cerrar_sobrantes(self, pos):
        """MT5 llena TODAS las STOP que un gap (o un movimiento muy rapido) cruza; el backtest llena una sola: la mas
        cercana a la apertura. La apertura se aproxima con el precio del PRIMER llenado: se queda la posicion cuya orden
        esta mas cerca de el (a igual distancia, la primera) y se cierran las demas a mercado. Sus ordenes quedan sin
        usar, como en el backtest."""
        primera = min(pos, key=lambda p: p.time_msc)
        ref, sp = primera.price_open, 0.0
        m1 = self.broker.velas("M1", 5)
        if m1 is not None and len(m1):
            v = m1[m1.time == pd.Timestamp(primera.time_msc, unit="ms").floor("min")]
            if len(v):            # la clave del backtest: distancia a la apertura de esa vela (compras con Ask)
                ref = float(v.open.iloc[0])
                sp = float(v.spread.iloc[0]) * (self.broker.info.point or 0.01)

        def clave_orden(p):
            prev = self.posiciones_previas.get(p.identifier, {})
            r = ref + (sp if p.type == 0 else 0.0)
            return round(abs(prev.get("precio_orden", p.price_open) - r)), p.time_msc
        orden = sorted(pos, key=clave_orden)
        queda = self.posiciones_previas.get(orden[0].identifier, {}).get("clave")
        for p in orden[1:]:
            k = self.posiciones_previas.get(p.identifier, {}).get("clave")
            ok, msg = self.broker.cerrar(p) if not self.dry_run else (True, "dry")
            if ok and not self.dry_run:
                self.liberadas.add(int(p.identifier))
                if k and k != queda:
                    self.usados.discard(k)
                self.guardar_estado()
            self.log(f"se llenaron {len(pos)} ordenes a la vez (gap): queda {queda}, cierro {k} ({msg}); la orden {k} "
                     f"queda sin usar, como en el backtest")

    def registrar_trade(self, pid: int, previa: dict = None):
        if pid in self.registradas:
            return
        r = self.broker.resumen_posicion(pid)
        if r is None:
            return
        previa = previa or {}
        clave = self._clave(r["comentario_entrada"], pid) or previa.get("clave")
        sl = r.get("sl") or previa.get("sl")
        o = self._orden_de_clave(clave)
        orden = (o.precio if o else None) or previa.get("precio_orden") or r.get("orden") or r["entrada"]
        riesgo = abs(orden - sl) if sl else float("nan")
        d = 1 if r["lado"] == "long" else -1
        R = d * (r["salida"] - r["entrada"]) / riesgo if riesgo else float("nan")
        mov = d * (r["salida"] - r["entrada"]) * r["volumen"]
        vp_real = r["profit"] / mov if mov else float("nan")
        vp = self.broker.valor_punto()
        riesgo_dinero = riesgo * r["volumen"] * (vp_real if vp_real == vp_real and vp_real > 0 else vp)
        R_neto = (r["profit"] + r["swap"] + r["comision"]) / riesgo_dinero if riesgo_dinero else float("nan")
        fila = {"position_id": pid, "clave": clave, **r, "orden": orden, "riesgo_pts": round(riesgo, 2),
                "R": round(R, 3), "R_neto": round(R_neto, 3)}
        if not self.papel:
            fila.update(valor_punto_observado=round(vp_real, 4), valor_punto_usado=vp)
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
        self.log(f"CERRADO {r['lado']} {clave} entrada {r['entrada']} salida {r['salida']} ({r['comentario_salida']}) "
                 f"{R:+.2f}R | P&L {r['profit']:+.2f} com {r['comision']:+.2f} swap {r['swap']:+.2f}")
        if not self.papel and vp_real == vp_real and abs(vp_real / vp - 1) > 0.2:
            self.log(f"OJO valor por punto: el bot usa {vp:.4f} por punto y lote, este trade dio {vp_real:.4f}. "
                     f"Revisar 'valor_punto_lote' en el config: el riesgo real no es el configurado.")

    # ------------------------------------------------------------------ modo real
    def _candado(self):
        """Un solo bot por magic: dos copias lanzadas a mano duplicarian ordenes. El candado del sistema operativo se
        suelta solo si el proceso muere."""
        carpeta = RAIZ / self.cfg["archivos"]["logs"]
        carpeta.mkdir(parents=True, exist_ok=True)
        f = open(carpeta / f"instancia_{self.cfg['mt5']['magic']}.lock", "a+")
        try:
            import msvcrt
            f.seek(0)
            msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
        except ImportError:
            import fcntl
            try:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                f.close()
                return None
        except OSError:
            f.close()
            return None
        return f

    def iniciar(self):
        """Bucle del modo real (en papel lo maneja papel/runner.py)."""
        candado = self._candado()
        if candado is None:
            print(f"ABORTADO: ya hay otro bot corriendo con magic {self.cfg['mt5']['magic']} (cierra la otra ventana)")
            return
        if not self.preparar():
            return
        stop = RAIZ / self.cfg["archivos"]["stop"]
        try:
            while True:
                if stop.exists():
                    self.log(f"{stop.name} detectado: cancelo pendientes y salgo (la posicion abierta, si hay, queda "
                             f"con su SL/TP)")
                    self._cancelar_todas()
                    break
                if not self.broker.asegurar_conexion():
                    self.aviso("conexion", "MT5 no responde (terminal cerrada o reiniciandose): reintento cada 10 s")
                    time.sleep(10)
                    continue
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

    # ------------------------------------------------------------------ arranque
    def preparar(self, dir_logs=None) -> bool:
        ok, msg = self.broker.conectar()
        if not ok:
            print("ERROR:", msg)
            return False
        cta = self.broker.cuenta()
        if dir_logs:
            self.dir_logs = Path(dir_logs)
        elif self.papel:
            self.dir_logs = RAIZ / "papel" / "estado" / "falsa_ruptura"
        else:
            carpeta = str(cta["login"]) + ("_dryrun" if self.dry_run else "")    # el dry-run no toca el estado real
            self.dir_logs = RAIZ / self.cfg["archivos"]["logs"] / carpeta
        self.dir_logs.mkdir(parents=True, exist_ok=True)
        if self.papel:
            self.broker.abrir_estado(self.dir_logs)
            self.log("MODO PAPEL: precios reales de esta terminal, ordenes VIRTUALES (no se envia nada al broker)")
        else:
            esperado = float(self.cfg["cuenta"]["balance_esperado"])
            ratio = cta["balance"] / esperado if esperado else 0
            self.log(f"MODO REAL{' (DRY RUN: no se envian ordenes)' if self.dry_run else ''} | cuenta #{cta['login']} "
                     f"{cta['server']} | balance {cta['balance']:,.2f} {cta['moneda']} | apalancamiento "
                     f"1:{cta['apalancamiento']}")
            if not 0.5 <= ratio <= 2.0:
                self.log(f"ABORTADO: el balance no cuadra con balance_esperado={esperado:,.0f}. Revisa terminal y config.")
                self.broker.desconectar()
                return False
            if self.login and str(cta["login"]) != str(self.login):
                self.log(f"ABORTADO: la terminal esta en la cuenta {cta['login']} y el config dice {self.login}.")
                self.broker.desconectar()
                return False
            if hasattr(self.broker, "propiedades"):
                self.log(f"Broker {self.broker.simbolo}: {self.broker.propiedades()}")
        i = self.broker.info
        self.est = EstrategiaFR(**self.est_args, paso_precio=i.trade_tick_size or i.point)
        self.broker.reglas = lambda hora: (bloqueado(hora, self.ventanas, self.feriados),
                                           corte_viernes(hora, self.feriados))
        self.log(f"Cuenta {cta['login']} | {self.broker.simbolo} tick {i.trade_tick_size} lote min {i.volume_min} "
                 f"paso {i.volume_step} | valor por punto y lote: MT5 {self.broker.valor_punto_mt5():.4f}, usado "
                 f"{self.broker.valor_punto():.4f} | magic {self.broker.magic} | riesgo {self.texto_riesgo()} "
                 f"(balance {cta['balance']:,.2f})")
        self.log(f"Estrategia: falsa ruptura de pivotes H1 {self.est.izq}/{self.est.der}, {self.est.max_niveles} niveles, "
                 f"STOP en contra a W {self.est.W}, vigencia {self.est.vig}, SL espejo (4 velas + {self.est.buf}), "
                 f"RR {self.est.RR}, rotacion {self.est.max_ordenes} ordenes")
        f = self.dir_logs / "estado.json"
        if f.exists():
            est = json.loads(f.read_text())
            self.usados |= set(est.get("usados", []))
            self.liberadas |= {int(x) for x in est.get("liberadas", [])}
            self.tickets.update(est.get("tickets", {}))
        h1 = self.broker.velas("H1", 601)          # ordenes antes de anotar posiciones (precio de la STOP)
        if h1 is not None and len(h1) > 40:
            self.ordenes = self.est.ordenes(h1)
            self.hora_h1 = h1.time.iloc[-1]
        self.usados |= self.broker.claves_usadas(excluir=self.liberadas, mapa=self.tickets)
        t = self.dir_logs / "trades.csv"
        if t.exists():
            self.registradas |= set(pd.read_csv(t).position_id.astype(int))
        for p in self.broker.posiciones():
            self._anotar_posicion(p)
        self._calentar_usados()
        m1 = self.broker.velas("M1", 1)
        if m1 is not None and len(m1):
            self.ultima_m1 = m1.time.iloc[-1]          # el minuto del arranque no se decide: se espera la vela siguiente
        self.log(f"Ordenes ya usadas: {len(self.usados)} | posiciones abiertas: {len(self.posiciones_previas)} | "
                 f"pendientes: {len(self.broker.pendientes())}")
        self._autoprueba()
        self.guardar_estado()
        return True

    def _autoprueba(self):
        """Cuenta real: valida con order_check (sin enviar) una VENTA STOP de prueba lejos del precio, con vencimiento."""
        if self.papel or not hasattr(self.broker, "chequear_pendiente"):
            return
        try:
            from .estrategia import OrdenFR
            tk = self.broker.tick()
            if tk is None:
                return
            p = self.est._r(tk["bid"] * 0.97)
            h = tk["hora"].floor("h") + pd.Timedelta(hours=8)
            o = OrdenFR("prueba", "sell_stop", p, self.est._r(p + 270), self.est._r(p - 810), p, 270.0, h, h, h, p)
            vol = self.broker.info.volume_min
            self.log(f"Prueba de orden (order_check, no se envia): "
                     f"{self.broker.chequear_pendiente(o, vol, min(h, self.proximo_corte(tk['hora'])))}")
        except Exception as ex:
            self.log(f"Prueba de orden: error {type(ex).__name__}: {ex}")

    def _calentar_usados(self):
        """El bot no sabe que ordenes ya se 'gastaron' antes de existir (una orden se opera una sola vez). Ejemplo real
        del S/R, 10-nov-2026: el papel arranco y opero un nivel que el backtest ya habia operado el 04-nov. Aca se corre
        el MISMO backtest (backtest.simular) sobre el historial M1 reciente del broker y se marcan como usadas todas las
        ordenes que esa simulacion lleno (tambien la de una posicion que la simulacion tendria abierta ahora)."""
        try:
            m1 = self.broker.velas("M1", 60000)
            if m1 is None or len(m1) < 20000:
                self.log("OJO calentamiento: la terminal no entrega historial M1 suficiente ('max bars' >= 60000): no "
                         "se marcan ordenes usadas previas y el bot podria repetir una orden ya operada")
                return
            from .backtest import simular
            pt = self.broker.info.point or 0.01
            m1 = m1.iloc[:-1].reset_index(drop=True)
            spread = (m1.spread.values * pt) if "spread" in m1 else 2.1
            t = simular(m1[["time", "open", "high", "low", "close"]], self.est, spread=spread,
                        noticias=tuple(self.noticias), abierta=True, feriados=self.feriados)
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
            if len(ab) and not self.broker.posiciones():
                x = ab.iloc[0]
                self.sombra = {"dir": 1 if x.direction == "long" else -1, "sl": float(x.sl), "tp": float(x.tp),
                               "clave": x.clave, "entrada": pd.Timestamp(x.entry_time)}
                self.log(f"calentamiento: el backtest tiene ahora una posicion abierta ({x.direction} {x.clave} desde "
                         f"{x.entry_time:%d-%m %H:%M}, SL {x.sl} TP {x.tp}): el bot queda ocupado sin operar hasta "
                         f"que esa posicion habria cerrado (posicion sombra)")
        except Exception as ex:
            self.log(f"calentamiento: error {type(ex).__name__}: {ex} (sigue sin marcar ordenes previas)")

    def _anotar_posicion(self, p):
        k = self._clave(p.comment, p.identifier)
        if k and k not in self.usados:
            self.usados.add(k)
            self.guardar_estado()
        if p.identifier not in self.posiciones_previas:
            o = self._orden_de_clave(k)
            orden = getattr(p, "orden", None) or (o.precio if o else p.price_open)   # papel la trae; MT5 no
            self.posiciones_previas[p.identifier] = {"clave": k, "sl": p.sl, "tp": p.tp, "precio_orden": orden}
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
            self.aviso("sin_tick", "MT5 no da precio de este simbolo (sin conexion con el broker?)")
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
                if ok:
                    self.log(f"cierre de fin de semana {p.comment}{nota}: {msg}")
                else:
                    self.aviso(f"corte_{p.identifier}", f"cierre de fin de semana {p.comment}{nota}: {msg} (reintento)")
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
            if self.broker.pendientes():
                self._cancelar_todas()
            if len(pos) > 1:
                self._cerrar_sobrantes(pos)
            self._tablero(ahora, tk)
            return
        if bloqueado(ahora, self.ventanas, self.feriados):
            self.vigilar = {}
            if self.broker.pendientes():
                self.log("noticias / fin de semana: cancelo pendientes")
                self._cancelar_todas()
            return

        m1 = self.broker.velas("M1", 3)
        if m1 is None or len(m1) < 2:
            return
        if m1.time.iloc[-1] == self.ultima_m1:
            if self.vigilar:
                self._vigilar(tk, ahora)
            self._tablero(ahora, tk)
            return
        self.vigilar = {}
        if m1.time.iloc[-1] > ahora:                  # el tick se leyo justo antes del cambio de minuto
            ahora = m1.time.iloc[-1]
            if bloqueado(ahora, self.ventanas, self.feriados):
                return

        nuevos = self.broker.claves_usadas(dias=10, excluir=self.liberadas, mapa=self.tickets) - self.usados
        if nuevos:
            self.usados |= nuevos
            self.guardar_estado()
        for pid in self.broker.cerradas_recientes(dias=10) - self.registradas:
            self.registrar_trade(pid)
        self.ultima_m1 = m1.time.iloc[-1]
        if self.ultima_salida is not None and self.ultima_salida.floor("min") >= self.ultima_m1:
            return                                       # cerro una posicion en este minuto: se espera la vela siguiente
        cierre_ant = float(m1.close.iloc[-2])
        pt = self.broker.info.point or 0.01
        sp_ant = float(m1.spread.iloc[-2]) * pt if "spread" in m1 else 0.0

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
        # spread de la vela M1 anterior, como el backtest (no el del tick: en la reapertura de las 01:00 llega a 10-30)
        spread = sp_ant if sp_ant > 0 else tk["ask"] - tk["bid"]
        deseadas = {o.clave: o for o in self.est.deseadas(vig, cierre_ant, spread)}
        if set(deseadas) != self.deseadas_previas:
            self.log("ordenes que corresponden: " + (", ".join(
                f"{o.lado} {o.clave} {o.precio} SL {o.sl} TP {o.tp}" for o in deseadas.values()) or "ninguna")
                + f" | vigentes: {', '.join(o.clave for o in vig) or '-'}")
            self.deseadas_previas = set(deseadas)
        if self.dry_run:
            return

        puestas = {}
        for o in self.broker.pendientes():
            k = self._clave(o.comment, o.ticket)
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
            vol = self.broker.volumen(self.riesgo_dinero(bal), o.riesgo_pts)
            if vol <= 0:
                continue
            ok, msg = self.broker.abrir_mercado(o, vol)
            self.log(f"{'ENTRADA A MERCADO' if ok else 'FALLO a mercado'} {o.lado} {o.clave} {vol} lotes (STOP "
                     f"{o.precio} ya cruzada) SL {o.sl} TP {o.tp} {msg}")
            if ok:
                self._anotar_ticket(o.clave)
                self._cancelar_todas()
                return

        for k, o in deseadas.items():
            if k in puestas:
                continue
            if not self.broker.orden_valida(o, tk["bid"], tk["ask"]):
                self.vigilar[k] = o
                self.log(f"{k}: {o.lado} {o.precio} muy cerca del precio para ponerla (bid {tk['bid']} ask "
                         f"{tk['ask']}): la vigilo este minuto y entro a mercado si la cruza")
                continue
            vol = self.broker.volumen(self.riesgo_dinero(bal), o.riesgo_pts)
            if vol <= 0:
                self.log(f"{k}: volumen menor al minimo con riesgo {self.texto_riesgo()}, no se pone")
                continue
            ok_m, margen = self.broker.margen_ok(o, vol)
            if not ok_m:
                self.log(f"{k}: margen insuficiente ({margen:,.0f}) para {vol} lotes, no se pone")
                continue
            ok, msg = self.broker.poner_orden(o, vol, vence=self.proximo_corte(ahora))
            self.log(f"{'PUESTA' if ok else 'FALLO'} {o.lado} {k} {vol} lotes a {o.precio} SL {o.sl} TP {o.tp} "
                     f"(riesgo {o.riesgo_pts:.1f} pts, vale hasta {o.hasta:%d-%m %H:%M}) {msg}")
            if ok:
                self._anotar_ticket(k)
            elif getattr(self.broker, "ultimo_retcode", None) in PRECIO_INVALIDO:
                self.vigilar[k] = o                       # el precio se movio entre la lectura y el envio
        self._tablero(ahora, tk)

    def _vigilar(self, tk, ahora):
        """STOP que el broker no dejo poner al abrir el minuto (muy cerca del precio): si el precio la cruza dentro del
        minuto, entra a mercado con su SL/TP (el backtest la llenaria en esta vela)."""
        if self.dry_run or self.broker.posiciones():
            self.vigilar = {}
            return
        for k, o in list(self.vigilar.items()):
            if ahora >= o.hasta:
                self.vigilar.pop(k)
                continue
            cruzada = (tk["bid"] <= o.precio) if o.lado == "sell_stop" else (tk["ask"] >= o.precio)
            if not cruzada:
                continue
            if (o.lado == "sell_stop" and tk["ask"] >= o.sl) or (o.lado == "buy_stop" and tk["bid"] <= o.sl):
                self.vigilar.pop(k)
                continue
            if self.ultimo_balance is None:
                return
            vol = self.broker.volumen(self.riesgo_dinero(self.ultimo_balance), o.riesgo_pts)
            if vol <= 0:
                self.vigilar.pop(k)
                continue
            ok, msg = self.broker.abrir_mercado(o, vol)
            self.log(f"{'ENTRADA A MERCADO' if ok else 'FALLO a mercado'} {o.lado} {k} {vol} lotes (STOP vigilada "
                     f"{o.precio}, cruzada dentro del minuto) SL {o.sl} TP {o.tp} {msg}")
            if ok:
                self._anotar_ticket(k)
                self.vigilar = {}
                self._cancelar_todas()
            else:
                self.vigilar.pop(k)
            return

    def _tablero(self, ahora, tk):
        if time.time() - self.ultimo_tablero < 900:
            return
        self.ultimo_tablero = time.time()
        c = self.broker.cuenta()
        self.log(f"[estado] servidor {ahora:%a %H:%M} | bid {tk['bid']} | balance {c['balance']:,.2f} equity "
                 f"{c['equity']:,.2f} | posiciones {len(self.broker.posiciones())} | pendientes "
                 f"{len(self.broker.pendientes())} | usadas {len(self.usados)}")
