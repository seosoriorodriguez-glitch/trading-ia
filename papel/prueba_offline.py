# -*- coding: utf-8 -*-
"""
Prueba SIN CONEXION del laboratorio completo (runner + bot en papel + subida al panel + comparacion con backtest):
  - MT5 falso con ticks armados desde velas M1 (papel/estrategias/sr_pivot_h1/herramientas/prueba_papel.Mercado);
  - Supabase falso que solo anota lo que se subiria (no toca la base real);
  - carpeta de estado temporal.
Revisa: formato de las filas (ids lab_, cuentas y tickets virtuales, horas), que los trades subidos sean los del papel,
que se registre el backtest como __bt archivado y que la comparacion papel vs backtest cuadre.

    python papel/prueba_offline.py 2026-09-01 2026-10-01
"""
import sys
import tempfile
from collections import defaultdict
from pathlib import Path
from types import SimpleNamespace

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "research" / "pa_lab"))
sys.path.insert(0, str(RAIZ / "papel" / "estrategias" / "sr_pivot_h1" / "herramientas"))

import json
import MetaTrader5 as mt5
import numpy as np
import pandas as pd

from datos import m1_periodo
from prueba_papel import Mercado


class SBFalso:
    """Imita supabase-py: table(x).upsert/insert/delete(...).eq(...).execute() y anota todo."""
    def __init__(self):
        self.ops = defaultdict(list)

    def table(self, nombre):
        sb = self

        class Q:
            def __init__(self):
                self.op, self.data, self.filtros = None, None, []

            def upsert(self, data, on_conflict=None):
                self.op, self.data = "upsert", data
                return self

            def insert(self, data):
                self.op, self.data = "insert", data
                return self

            def delete(self):
                self.op = "delete"
                return self

            def eq(self, k, v):
                self.filtros.append((k, v))
                return self

            def execute(self):
                sb.ops[nombre].append((self.op, self.data, self.filtros))
                return SimpleNamespace(data=[])
        return Q()


def main():
    ini = pd.Timestamp(sys.argv[1] if len(sys.argv) > 1 else "2026-09-01")
    fin = pd.Timestamp(sys.argv[2] if len(sys.argv) > 2 else "2026-10-01")
    m1 = m1_periodo(ini - pd.Timedelta(days=45), fin, margen_dias=3)
    mk = Mercado(m1)
    mk.i = int(np.searchsorted(m1.time.values, np.datetime64(ini)))
    for n in ("symbol_info", "symbol_info_tick", "copy_ticks_from", "copy_rates_from_pos", "account_info"):
        setattr(mt5, n, getattr(mk, n))
    mt5.initialize = lambda *a, **k: True
    mt5.shutdown = lambda: None
    mt5.symbol_select = lambda *a: True
    mt5.terminal_info = lambda: SimpleNamespace(connected=True)
    mt5.copy_rates_range = lambda *a: mk.copy_rates_from_pos(None, mt5.TIMEFRAME_M1, 0, 300)
    from papel.runner import Laboratorio
    cfg = json.loads((RAIZ / "papel" / "config.example.json").read_text(encoding="utf-8"))
    cfg["estrategias"][0]["simbolo"] = "US30.cash"
    sb = SBFalso()
    with tempfile.TemporaryDirectory() as tmp:
        lab = Laboratorio(cfg, "darwinex", sb=sb, log=lambda x: None, estado_dir=tmp)
        assert lab.iniciar(), "no arranco"
        bot = lab.bots["lab_sr_pivot_h1"]
        bot.verbose = False
        for i in range(mk.i, len(m1)):
            mk.i = i
            lab.paso()
            if i % 60 == 0:
                lab.sincronizar()
        lab.sincronizar(forzar_snapshot=True)
        lab.fidelidad(forzar=True)
        res = json.loads((Path(tmp) / "lab_sr_pivot_h1" / "fidelidad.json").read_text())
    bots = [d for op, d, _ in sb.ops["bots"]]
    subidos = [r for op, d, _ in sb.ops["trades"] if op == "upsert" for r in d]
    papel = [r for r in subidos if r["bot_id"] == "lab_sr_pivot_h1"]
    bt = [r for r in subidos if r["bot_id"] == "lab_sr_pivot_h1__bt"]
    borrados = [f for op, d, f in sb.ops["trades"] if op == "delete"]
    print("bots registrados:", [(b["id"], b["account"], b["active"]) for b in bots])
    print(f"trades papel subidos {len(papel)} | backtest subidos {len(bt)} | snapshots {len(sb.ops['account_snapshots'])}"
          f" | velas {sum(len(d) for _, d, _ in sb.ops['trade_candles'])} | borrados (solo __bt): {borrados}")
    print("ejemplo de fila:", {k: papel[0][k] for k in ("bot_id", "account", "ticket", "direction", "entry_time",
                                                        "exit_time", "exit_reason", "risk_points", "pnl_usd", "pnl_r", "session")} if papel else "-")
    ok_ids = all(r["bot_id"].startswith("lab_") and r["account"] >= 9_000_000_000 and r["ticket"] >= 9e14 for r in subidos)
    print("todas las filas lab_ / cuentas y tickets virtuales:", ok_ids)
    print("comparacion papel vs backtest:", res)


if __name__ == "__main__":
    main()
