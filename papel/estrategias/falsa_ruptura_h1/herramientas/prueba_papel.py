# -*- coding: utf-8 -*-
"""
Prueba SIN CONEXION del bot en modo papel (bot.py + broker_papel.py): se reemplazan las funciones de MetaTrader5 por
un mercado falso que entrega TICKS armados con velas M1 historicas (4 por vela: apertura, los dos extremos en el orden
probable, cierre; Ask = Bid + 2.1) y un swap de -8 pts largos / -2 cortos (modo puntos).

  A) periodo completo: el bot arranca al inicio y se compara con el backtest (backtest.py) del mismo periodo. No sale
     identico a proposito (en papel la STOP y el SL se llenan al precio del tick, sin el deslizamiento fijo del
     backtest, y el orden de los extremos dentro de la vela es una suposicion); las ENTRADAS (hora, direccion, nivel)
     si deben coincidir.
  B) calentamiento: el bot arranca justo despues de que el backtest lleno y cerro una orden que sigue vigente. Sin el
     calentamiento la volveria a operar (el error del S/R del 10-nov-2026); con el calentamiento no debe tocarla.

    python papel/estrategias/falsa_ruptura_h1/herramientas/prueba_papel.py 2026-09-01 2026-10-01
"""
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

RAIZ = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "research" / "pa_lab"))

import MetaTrader5 as mt5
import numpy as np
import pandas as pd

from datos import m1_periodo, tf
from papel.registro import DEF_FR, construir_falsa_ruptura
from papel.estrategias.falsa_ruptura_h1.backtest import simular
from papel.estrategias.falsa_ruptura_h1.estrategia import EstrategiaFR

SPREAD = 2.1


class Mercado:
    def __init__(self, m1):
        self.m1 = m1.reset_index(drop=True)
        self.h1 = tf(self.m1, 60)
        self.h1t = self.h1.time.values
        self.seg = self.m1.time.values.astype("datetime64[s]").astype(np.int64)
        o, h, l, c = (self.m1[k].values for k in ("open", "high", "low", "close"))
        sube = c >= o
        p1, p2 = np.where(sube, l, h), np.where(sube, h, l)
        ms = np.stack([self.seg * 1000, self.seg * 1000 + 20000, self.seg * 1000 + 40000, self.seg * 1000 + 59000],
                      1).ravel()
        bid = np.stack([o, p1, p2, c], 1).ravel()
        self.ticks = np.zeros(len(ms), dtype=[("time", "i8"), ("time_msc", "i8"), ("bid", "f8"), ("ask", "f8")])
        self.ticks["time_msc"], self.ticks["time"] = ms, ms // 1000
        self.ticks["bid"], self.ticks["ask"] = bid, bid + SPREAD
        self.i = 1

    def symbol_info(self, s):
        return SimpleNamespace(visible=True, digits=2, point=0.01, trade_tick_size=0.01, trade_tick_value=0.01,
                               volume_min=0.01, volume_step=0.01, volume_max=100.0, trade_stops_level=0,
                               swap_mode=1, swap_long=-800.0, swap_short=-200.0, swap_rollover3days=3)

    def symbol_info_tick(self, s):
        b = float(self.m1.open.iloc[self.i])
        return SimpleNamespace(time=int(self.seg[self.i]), bid=b, ask=b + SPREAD)

    def copy_ticks_from(self, s, desde_s, n, flags):
        a = int(np.searchsorted(self.ticks["time_msc"], desde_s * 1000))
        b = int(np.searchsorted(self.ticks["time_msc"], self.seg[self.i] * 1000, side="right"))
        return self.ticks[a:min(b, a + n)]

    def copy_rates_from_pos(self, s, tf_, pos, n):
        if tf_ == mt5.TIMEFRAME_M1:
            d = self.m1.iloc[max(0, self.i - n + 1):self.i + 1].copy()
            d.iloc[-1, d.columns.get_loc("close")] = d.open.iloc[-1]
        else:
            k = int(np.searchsorted(self.h1t, np.datetime64(pd.Timestamp(self.m1.time.iloc[self.i]).floor("h")),
                                    side="right"))
            d = self.h1.iloc[max(0, k - n):k].copy()
        r = np.zeros(len(d), dtype=[("time", "i8"), ("open", "f8"), ("high", "f8"), ("low", "f8"), ("close", "f8"),
                                    ("spread", "i8")])
        r["time"] = d.time.values.astype("datetime64[s]").astype(np.int64)
        for k in ("open", "high", "low", "close"):
            r[k] = d[k].values
        r["spread"] = 210
        return r

    def account_info(self):
        return SimpleNamespace(login=1, server="falso", balance=100000.0, equity=100000.0, margin_free=1e9,
                               currency="USD", leverage=100)


def instalar(mk):
    for nombre in ("symbol_info", "symbol_info_tick", "copy_ticks_from", "copy_rates_from_pos", "account_info"):
        setattr(mt5, nombre, getattr(mk, nombre))
    mt5.initialize = lambda *a, **k: True
    mt5.shutdown = lambda: None
    mt5.symbol_select = lambda *a: True


ENTRADA = {"id": "lab_prueba", "balance": 100000, "riesgo_pct": 0.005, "feed": "f", "simbolo": "US30.cash",
           "valor_punto_lote": 1.0}


def correr_bot(mk, i0, i1, tmp):
    mk.i = i0
    bot = construir_falsa_ruptura(ENTRADA, {"f": None})
    bot.verbose = False
    bot.preparar(dir_logs=tmp)
    for i in range(i0, i1):
        mk.i = i
        bot.ciclo()
    hist = pd.DataFrame(bot.broker.hist.values())
    log = (Path(tmp) / "eventos.log").read_text(encoding="utf-8")
    return bot, hist, log


def main():
    ini = pd.Timestamp(sys.argv[1] if len(sys.argv) > 1 else "2026-09-01")
    fin = pd.Timestamp(sys.argv[2] if len(sys.argv) > 2 else "2026-10-01")
    m1 = m1_periodo(ini, fin, margen_dias=70)[["time", "open", "high", "low", "close"]].reset_index(drop=True)
    mk = Mercado(m1)
    instalar(mk)
    bt = simular(m1, EstrategiaFR(**{k: DEF_FR[k] for k in ("W", "vig_h", "buf", "n_ext", "RR", "max_niveles",
                                                              "max_ordenes")}))
    i_ini = int(np.searchsorted(m1.time.values, np.datetime64(ini)))

    # A) periodo completo
    with tempfile.TemporaryDirectory() as tmp:
        bot, h, log = correr_bot(mk, i_ini, len(m1), tmp)
    r = bt[(bt.entry_time >= ini) & (bt.entry_time < fin)].reset_index(drop=True)
    h["entry_time"] = pd.to_datetime(h.entrada_hora).dt.floor("min")
    h["clave"] = h.comentario_entrada.str[3:]
    h["R"] = np.where(h.lado == "long", 1, -1) * (h.salida - h.entrada) / (h.orden - h.sl).abs()
    m = r.merge(h, on=["entry_time", "clave"], how="outer", indicator=True, suffixes=("_bt", "_papel"))
    ambos = m[m._merge == "both"]
    print(f"A) {ini:%Y-%m-%d} a {fin:%Y-%m-%d}: backtest {len(r)} trades {r.R.sum():+.2f}R | papel {len(h)} trades "
          f"{h.R.sum():+.2f}R (swap {h.swap.sum():+.2f} USD)")
    print(f"   misma entrada (minuto y nivel): {len(ambos)} | misma salida (minuto): "
          f"{(pd.to_datetime(ambos.exit_time).dt.floor('min') == pd.to_datetime(ambos.salida_hora).dt.floor('min')).sum()}"
          f" | solo backtest {(m._merge == 'left_only').sum()} | solo papel {(m._merge == 'right_only').sum()}")
    print(ambos[["entry_time", "clave", "direction", "orden_bt", "entry_price", "entrada", "exit_reason",
                 "comentario_salida", "R_bt", "R_papel"]].round(2).to_string(index=False))
    ok_a = len(ambos) == len(r) == len(h)
    if (m._merge != "both").any():
        print(m[m._merge != "both"][["entry_time", "clave", "direction", "lado", "exit_time", "salida_hora", "_merge"]].to_string(index=False))
    print("   lineas RUPTURA en el log:", log.count("RUPTURA"), "| PUESTA:", log.count("PUESTA"),
          "| A MERCADO:", log.count("ENTRADA A MERCADO"), "| calentamiento:",
          next((x.split("| ", 1)[1] for x in log.splitlines() if "calentamiento" in x), "-"))

    # B) calentamiento: arrancar justo despues de que el backtest lleno y cerro una orden todavia vigente
    est = EstrategiaFR()
    ords = {o.clave: o for o in est.ordenes(pd.concat([tf(m1, 60), tf(m1, 60).tail(1)]))}
    cand = bt[(bt.entry_time >= ini) & (bt.entry_time < fin)].copy()
    cand["hasta"] = [ords[k].hasta if k in ords else pd.NaT for k in cand.clave]
    cand = cand[cand.exit_time + pd.Timedelta(minutes=5) < cand.hasta]
    if not len(cand):
        print("\nB) no hay en el periodo una orden llenada y cerrada antes de vencer: no se puede probar")
        print("\nPRUEBA OK (solo A)" if ok_a else "\nPRUEBA CON DIFERENCIAS (ver arriba)")
        return
    x = cand.iloc[0]
    arranque = x.exit_time + pd.Timedelta(minutes=2)
    i0 = int(np.searchsorted(m1.time.values, np.datetime64(arranque)))
    i1 = int(np.searchsorted(m1.time.values, np.datetime64(x.hasta + pd.Timedelta(hours=2))))
    with tempfile.TemporaryDirectory() as tmp:
        bot, h, log = correr_bot(mk, i0, i1, tmp)
    repite = (len(h) and (h.comentario_entrada.str[3:] == x.clave).any())
    print(f"\nB) orden {x.clave}: el backtest la lleno {x.entry_time:%d-%m %H:%M}, cerro {x.exit_time:%d-%m %H:%M} "
          f"({x.exit_reason}), vigente hasta {x.hasta:%d-%m %H:%M}. Bot arranca {arranque:%d-%m %H:%M}.")
    print("   log:", next((y.split("| ", 1)[1] for y in log.splitlines() if "calentamiento" in y), "-"))
    print(f"   la vuelve a operar: {'SI (MAL)' if repite else 'NO (bien)'} | marcada usada: {x.clave in bot.usados}")
    print("\nPRUEBA OK" if ok_a and not repite else "\nPRUEBA CON DIFERENCIAS (ver arriba)")


if __name__ == "__main__":
    main()
