# -*- coding: utf-8 -*-
"""
LABORATORIO EN PAPEL: corre varias estrategias en paper trading con los precios EN VIVO de una terminal MT5 que ya
existe, y las sube al panel (Lab · Demo). 100 % ADITIVO:
  - NO envia ninguna orden: lee precios (como el colector) y todo lo demas es virtual;
  - no importa ni modifica ningun bot en produccion; puede leer la misma terminal que ellos;
  - en el panel solo escribe filas "lab_..." (ver papel/sincro.py).

Un proceso por terminal (la libreria de MT5 se conecta a una sola por proceso):

    $env:SUPABASE_URL="https://....supabase.co"
    $env:SUPABASE_SERVICE_KEY="<service_role_key>"
    python papel/runner.py --feed darwinex          # estrategias de papel/config.json con "feed": "darwinex"
    python papel/runner.py --feed darwinex --sin-panel   # solo local, sin subir nada

Detener: crear papel/STOP_PAPEL.txt (o Ctrl+C). Al relanzar sigue donde iba (estado en papel/estado/<id>/).
Cada dia, en la pausa diaria del mercado (00:05-00:55 del servidor, sin precios: no le quita tiempo a los bots),
compara lo hecho en papel con el backtest del mismo periodo (papel/fidelidad.py) y lo sube como "<id>__bt" para el
detalle de la estrategia en el panel. Un candado por feed impide correr dos laboratorios iguales a la vez.
"""
import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

import MetaTrader5 as mt5
import pandas as pd

from papel import fidelidad as F
from papel.calendario import verano_eeuu
from papel.registro import BACKTESTS, PLUGINS
from papel.sincro import DESFASE_BT, Sincro, fila_trade

ESTADO = RAIZ / "papel" / "estado"
STOP = RAIZ / "papel" / "STOP_PAPEL.txt"
CADA_SINCRO_S = 60
CADA_SNAPSHOT_S = 300


class Laboratorio:
    def __init__(self, cfg: dict, feed: str, sb=None, log=None, estado_dir=None):
        self.cfg, self.feed = cfg, feed
        self.estado = Path(estado_dir) if estado_dir else ESTADO
        self.terminal = cfg["feeds"][feed]
        self.estrategias = [e for e in cfg["estrategias"] if e.get("activa", True) and e["feed"] == feed]
        self.sincro = Sincro(sb, self.log) if sb is not None else None
        self._log = log
        self.bots, self.est = {}, {}
        self.ultima_sincro = 0.0
        self.ultimo_snapshot = 0.0

    def log(self, msg: str):
        linea = f"{datetime.now():%Y-%m-%d %H:%M:%S} | [lab {self.feed}] {msg}"
        if self._log:
            self._log(linea)
        else:
            print(linea, flush=True)
        self.estado.mkdir(parents=True, exist_ok=True)
        with open(self.estado / f"runner_{self.feed}.log", "a", encoding="utf-8") as f:
            f.write(linea + "\n")

    # ------------------------------------------------------------------ estado por estrategia
    def _cargar(self, e):
        f = self.estado / e["id"] / "lab.json"
        d = json.loads(f.read_text()) if f.exists() else {}
        return {"subidos": set(d.get("subidos", [])), "inicio": d.get("inicio"),
                "ultima_fidelidad": d.get("ultima_fidelidad")}

    def _guardar(self, e):
        s = self.est[e["id"]]
        (self.estado / e["id"] / "lab.json").write_text(json.dumps(
            {"subidos": sorted(s["subidos"]), "inicio": s["inicio"], "ultima_fidelidad": s["ultima_fidelidad"]},
            indent=1))

    # ------------------------------------------------------------------ arranque
    def iniciar(self) -> bool:
        if not self.estrategias:
            self.log(f"no hay estrategias activas con feed '{self.feed}' en el config")
            return False
        if not mt5.initialize(path=self.terminal):
            self.log(f"no conecta a la terminal {self.terminal}: {mt5.last_error()}")
            return False
        for e in self.estrategias:
            if not e["id"].startswith("lab_"):
                self.log(f"{e['id']}: el id debe empezar con 'lab_' (asi el panel lo aisla del portafolio). Omitida.")
                continue
            if e["cuenta"] < 9_000_000_000:
                self.log(f"{e['id']}: la cuenta virtual debe ser >= 9 000 000 000 (no chocar con cuentas reales). Omitida.")
                continue
            bot = PLUGINS[e["plugin"]](e, self.cfg["feeds"])
            if not bot.preparar(dir_logs=self.estado / e["id"]):
                self.log(f"{e['id']}: no arranco")
                continue
            self.bots[e["id"]] = bot
            self.est[e["id"]] = self._cargar(e)
            if not self.est[e["id"]]["inicio"]:
                tk = mt5.symbol_info_tick(e["simbolo"])
                self.est[e["id"]]["inicio"] = str(pd.Timestamp(tk.time, unit="s").floor("min"))
                self._guardar(e)
            if self.sincro:
                self.sincro.registrar(e)
            self.log(f"{e['id']} en papel desde {self.est[e['id']]['inicio']} (hora servidor) | {e['simbolo']} | "
                     f"riesgo {e['riesgo_pct']:.2%} de {e['balance']:,.0f}")
        return bool(self.bots)

    def _e(self, id_):
        return next(e for e in self.estrategias if e["id"] == id_)

    # ------------------------------------------------------------------ ciclo
    def paso(self):
        if mt5.terminal_info() is None:
            self.log("terminal desconectada: reconecto")
            mt5.initialize(path=self.terminal)
            return
        for id_, bot in self.bots.items():
            try:
                bot.ciclo()
            except Exception as ex:
                self.log(f"{id_}: error en el ciclo {type(ex).__name__}: {ex}")

    def sincronizar(self, forzar_snapshot: bool = False):
        if not self.sincro:
            return
        for id_, bot in self.bots.items():
            e, s = self._e(id_), self.est[id_]
            try:
                nuevos = sorted(pid for pid in bot.broker.hist if pid not in s["subidos"])
                filas = [fila_trade(e, e["cuenta"], pid, bot.broker.hist[pid]) for pid in nuevos]
                if filas:
                    self.sincro.trades(e, filas)
                    self.sincro.velas(e, mt5, filas)
                    s["subidos"] |= set(nuevos)
                    self._guardar(e)
                    self.log(f"{id_}: {len(filas)} trade(s) subidos al panel")
                if forzar_snapshot or time.time() - self.ultimo_snapshot >= CADA_SNAPSHOT_S:
                    c = bot.broker.cuenta()
                    self.sincro.snapshot(e, c["balance"], c["equity"])
            except Exception as ex:
                self.log(f"{id_}: error subiendo al panel {type(ex).__name__}: {ex}")
        if forzar_snapshot or time.time() - self.ultimo_snapshot >= CADA_SNAPSHOT_S:
            self.ultimo_snapshot = time.time()

    @staticmethod
    def hora_servidor() -> pd.Timestamp:
        """Hora del servidor (Nueva York + 7 h) desde el reloj del VPS: en la pausa diaria no hay ticks."""
        utc = pd.Timestamp.utcnow().tz_localize(None)
        return utc + pd.Timedelta(hours=3 if verano_eeuu(utc) else 2)

    def fidelidad(self, forzar: bool = False):
        ahora = self.hora_servidor()
        if not forzar and not (ahora.hour == 0 and 5 <= ahora.minute <= 55):
            return
        for id_, bot in self.bots.items():
            e, s = self._e(id_), self.est[id_]
            if not forzar and s["ultima_fidelidad"] == str(ahora.date()):
                continue
            try:
                inicio = pd.Timestamp(s["inicio"])
                m1 = F.velas_m1(mt5, e["simbolo"], inicio)
                if not len(m1):
                    self.log(f"{id_}: sin velas M1 para comparar con el backtest (revisar 'max bars' de la terminal)")
                    continue
                info = mt5.symbol_info(e["simbolo"])
                spread = m1.spread.values * info.point                  # el del broker, vela por vela
                paso = info.trade_tick_size or info.point
                bt = BACKTESTS[e["plugin"]](e, m1[["time", "open", "high", "low", "close"]].reset_index(drop=True),
                                            spread, paso)
                fin = m1.time.iloc[-1]
                if len(bt):
                    bt = bt[(bt.entry_time >= inicio) & (bt.exit_time <= fin)].reset_index(drop=True)
                hist = bot.broker.hist

                def r_nominal(h):
                    ref = h.get("orden") if h.get("orden") is not None else h["entrada"]
                    d = 1 if h["lado"] == "long" else -1
                    return d * (h["salida"] - h["entrada"]) / abs(ref - h["sl"])
                papel = pd.DataFrame([{"entry_time": pd.Timestamp(h["entrada_hora"]), "direction": h["lado"],
                                       "clave": (h["comentario_entrada"] or "")[3:14], "R": r_nominal(h)}
                                      for h in hist.values()]) if hist else pd.DataFrame(columns=["entry_time", "direction", "R"])
                if len(papel):
                    papel = papel[papel.entry_time >= inicio]
                res = F.comparar(papel, bt if len(bt) else pd.DataFrame(columns=["entry_time", "direction", "R"]))
                res.update({"desde": str(inicio), "hasta": str(fin), "spread_backtest": round(float(spread.mean()), 2),
                            "calculado": f"{datetime.now():%Y-%m-%d %H:%M}"})
                F.guardar(self.estado / id_, res)
                if self.sincro:
                    riesgo_usd = e["balance"] * e["riesgo_pct"]
                    cta = e["cuenta"] + DESFASE_BT
                    filas = [fila_trade(e, cta, k + 1, {
                        "lado": r.direction, "entrada": r.entry_price, "salida": r.exit_price, "sl": r.sl, "tp": r.tp,
                        "orden": r.orden,
                        "entrada_hora": r.entry_time, "salida_hora": r.exit_time, "comentario_salida": r.exit_reason,
                        "volumen": 0, "profit": r.R * riesgo_usd}) for k, r in enumerate(bt.itertuples())] if len(bt) else []
                    self.sincro.backtest(e, filas)
                s["ultima_fidelidad"] = str(ahora.date())
                self._guardar(e)
                self.log(f"{id_}: papel vs backtest desde {inicio:%d-%m}: papel {res['papel']} trades ({res['R_papel']:+.1f}R)"
                         f" | backtest {res['backtest']} ({res['R_backtest']:+.1f}R) | coinciden {res['coinciden']} "
                         f"(mismo minuto {res['mismo_minuto']})")
            except Exception as ex:
                self.log(f"{id_}: error en la comparacion con el backtest {type(ex).__name__}: {ex}")

    def correr(self):
        if not self.iniciar():
            return
        self.log(f"laboratorio activo con {len(self.bots)} estrategia(s). Detener: crear {STOP.relative_to(RAIZ)}")
        try:
            while True:
                if STOP.exists():
                    self.log("STOP_PAPEL.txt detectado: subo lo pendiente y salgo")
                    break
                self.paso()
                if time.time() - self.ultima_sincro >= CADA_SINCRO_S:
                    self.sincronizar()
                    self.fidelidad()
                    self.ultima_sincro = time.time()
                time.sleep(2)
        except KeyboardInterrupt:
            self.log("detenido con Ctrl+C")
        finally:
            self.sincronizar(forzar_snapshot=True)
            mt5.shutdown()


_CANDADO = None


def tomar_candado(feed: str) -> bool:
    """Un solo laboratorio por feed: dos procesos escribiendo el mismo estado lo romperian. El candado del sistema
    operativo se suelta solo si el proceso muere."""
    global _CANDADO
    ESTADO.mkdir(parents=True, exist_ok=True)
    f = open(ESTADO / f"runner_{feed}.lock", "a+")
    try:
        if sys.platform == "win32":
            import msvcrt
            f.seek(0)
            msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        f.close()
        return False
    _CANDADO = f
    return True


def main():
    p = argparse.ArgumentParser(description="Laboratorio en papel (paper trading con precios en vivo)")
    p.add_argument("--feed", required=True, help="terminal de precios definida en config.json (darwinex, ftmo, ...)")
    p.add_argument("--config", default=str(RAIZ / "papel" / "config.json"))
    p.add_argument("--sin-panel", action="store_true", help="no sube nada a Supabase (solo logs locales)")
    a = p.parse_args()
    if not tomar_candado(a.feed):
        print(f"Ya hay un laboratorio corriendo con el feed '{a.feed}' (candado papel/estado/runner_{a.feed}.lock). "
              f"No se lanza otro.")
        return
    cfg = json.loads(Path(a.config).read_text(encoding="utf-8"))
    sb = None
    if not a.sin_panel:
        from papel.sincro import cliente
        sb = cliente()
    Laboratorio(cfg, a.feed, sb).correr()


if __name__ == "__main__":
    main()
