# -*- coding: utf-8 -*-
"""
Prueba SIN CONEXION del modo papel (bot.py + broker_papel.py): se reemplazan las funciones de MetaTrader5 por un
mercado falso que entrega TICKS armados con velas M1 historicas (4 por vela: apertura, los dos extremos en el orden
probable, cierre; Ask = Bid + 2.1) y un swap de -8 pts largos / -2 cortos (modo puntos, triple el miercoles).

Compara con el backtest del mismo periodo. No sale identico a proposito: en papel el SL se llena al precio del tick
que lo cruza (en el backtest SL - 0.7) y el orden de los extremos dentro de la vela es una suposicion. Las entradas
(nivel, hora) si deben coincidir.

    python strategies/sr_pivot_live/herramientas/prueba_papel.py 2026-09-01 2026-10-01
"""
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

RAIZ = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "research" / "pa_lab"))
sys.path.insert(0, str(RAIZ / "research" / "pa_lab" / "repaso"))

import MetaTrader5 as mt5
import numpy as np
import pandas as pd
import yaml

from datos import m1_periodo, tf
import motor_toque2 as MT
from strategies.sr_pivot_live.bot import BotSR
from strategies.sr_pivot_live.niveles import find_levels

SPREAD = 2.1


class Mercado:
    def __init__(self, m1):
        self.m1 = m1.reset_index(drop=True)
        self.h1 = tf(self.m1, 60)
        self.h1t = self.h1.time.values
        self.seg = (self.m1.time.values.astype("datetime64[s]").astype(np.int64))
        o, h, l, c = (self.m1[k].values for k in ("open", "high", "low", "close"))
        sube = c >= o
        p1, p2 = np.where(sube, l, h), np.where(sube, h, l)
        ms = np.stack([self.seg * 1000, self.seg * 1000 + 20000, self.seg * 1000 + 40000, self.seg * 1000 + 59000], 1).ravel()
        bid = np.stack([o, p1, p2, c], 1).ravel()
        self.ticks = np.zeros(len(ms), dtype=[("time", "i8"), ("time_msc", "i8"), ("bid", "f8"), ("ask", "f8")])
        self.ticks["time_msc"], self.ticks["time"] = ms, ms // 1000
        self.ticks["bid"], self.ticks["ask"] = bid, bid + SPREAD
        self.i = 1

    # funciones de MetaTrader5 que usa el bot en modo papel
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
            k = int(np.searchsorted(self.h1t, np.datetime64(pd.Timestamp(self.m1.time.iloc[self.i]).floor("h")), side="right"))
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


def main():
    ini = pd.Timestamp(sys.argv[1] if len(sys.argv) > 1 else "2026-09-01")
    fin = pd.Timestamp(sys.argv[2] if len(sys.argv) > 2 else "2026-10-01")
    m1 = m1_periodo(ini, fin, margen_dias=40)
    mk = Mercado(m1)
    for nombre in ("symbol_info", "symbol_info_tick", "copy_ticks_from", "copy_rates_from_pos", "account_info"):
        setattr(mt5, nombre, getattr(mk, nombre))
    mt5.initialize = lambda *a, **k: True
    mt5.shutdown = lambda: None
    mt5.symbol_select = lambda *a: True
    cfg = yaml.safe_load((RAIZ / "strategies" / "sr_pivot_live" / "config" / "demo.yaml").read_text(encoding="utf-8"))
    cfg["mt5"]["valor_punto_lote"] = 1.0
    bot = BotSR(cfg, papel=True)
    bot.verbose = False
    with tempfile.TemporaryDirectory() as tmp:
        bot.preparar(dir_logs=tmp)
        for i in range(1, len(m1)):
            mk.i = i
            bot.ciclo()
        t = pd.read_csv(Path(tmp) / "trades.csv", parse_dates=["entrada_hora", "salida_hora"])
        log = (Path(tmp) / "eventos.log").read_text(encoding="utf-8")
        estado = (Path(tmp) / "papel_estado.json").exists()
    t = t[(t.entrada_hora >= ini) & (t.entrada_hora < fin)].copy()
    t["entrada_hora"], t["salida_hora"] = t.entrada_hora.dt.floor("min"), t.salida_hora.dt.floor("min")
    nv = [(pd.Timestamp(x.activation_time), x.price, x.kind, k) for k, x in enumerate(find_levels(tf(m1, 60), 15, 15))]
    r = MT.correr(m1, nv, 20, 130, 2.5, solo_limit=True, escala=True)
    r = r[(r.entry_time >= ini) & (r.entry_time < fin)]
    print(f"backtest {len(r)} trades {r.R.sum():+.2f}R | papel {len(t)} trades {t.R.sum():+.2f}R "
          f"(swap {t.swap.sum():+.2f} USD, {int((t.noches > 0).sum())} con noche) | estado guardado: {estado}")
    m = r.merge(t, left_on="entry_time", right_on="entrada_hora", how="outer", indicator=True)
    ambos = m[m._merge == "both"]
    print(f"misma entrada (hora): {len(ambos)} | misma salida: {(ambos.exit_time == ambos.salida_hora).sum()} | "
          f"solo backtest {(m._merge == 'left_only').sum()} | solo papel {(m._merge == 'right_only').sum()}")
    print(ambos[["entry_time", "direction", "orden_x", "exit_reason", "comentario_salida", "R_x", "R_y", "noches",
                 "swap_pts"]].round(3).to_string(index=False))
    print("\nlineas de swap en el log:", log.count("swap "), "| ejemplo:",
          next((x for x in log.splitlines() if "swap " in x and "pts" in x), "-"))


if __name__ == "__main__":
    main()
