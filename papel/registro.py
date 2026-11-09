# -*- coding: utf-8 -*-
"""
Registro de estrategias que se pueden poner en papel. Su codigo vive en papel/estrategias/<nombre>/
(strategies/ queda solo para produccion: una estrategia pasa ahi cuando se lleva a real). Cada entrada de papel/config.json tiene un "plugin"; aca se
traduce a lo que necesita el bot de esa estrategia.

Para sumar una estrategia nueva:
  1. Su logica pura (que ordenes quiere en cada minuto) y su bot, como papel/estrategias/sr_pivot_h1/.
  2. Una funcion construir_<plugin>(entrada, feeds) aca que devuelva el bot listo en modo papel.
  3. Su backtest (para la comparacion diaria de papel/fidelidad.py) en BACKTESTS.
  4. Una linea en papel/config.json con id "lab_<algo>" (el panel la muestra en Lab · Demo).
"""
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]

DEF_SR = {"W": 20, "S": 130, "RR": 2.5, "max_niveles": 5, "pivote_izq": 15, "pivote_der": 15, "precio_ref": 47000}


def construir_sr_pivot(e: dict, feeds: dict):
    from papel.estrategias.sr_pivot_h1.bot import BotSR
    p = {**DEF_SR, **e.get("params", {})}
    cfg = {
        "cuenta": {"balance_esperado": e["balance"], "riesgo_pct": e["riesgo_pct"]},
        "mt5": {"terminal": feeds[e["feed"]], "simbolo": e["simbolo"], "magic": 0, "llenado": "return",
                "valor_punto_lote": e.get("valor_punto_lote")},
        "estrategia": p,
        "horario": {"noticias_et": e.get("noticias_et", ["08:26-08:34"])},
        "archivos": {"stop": "papel/STOP_PAPEL.txt", "logs": "papel/estado"},
        "papel": {"balance_inicial": e["balance"]},
    }
    return BotSR(cfg, papel=True)


def backtest_sr_pivot(e: dict, m1, spread: float):
    from papel.estrategias.sr_pivot_h1.backtest import simular
    from papel.estrategias.sr_pivot_h1.estrategia import EstrategiaSR
    p = {**DEF_SR, **e.get("params", {})}
    est = EstrategiaSR(p["W"], p["S"], p["RR"], p["max_niveles"], p["pivote_izq"], p["pivote_der"], p["precio_ref"])
    return simular(m1, est, spread=spread, noticias=tuple(e.get("noticias_et", ["08:26-08:34"])))


PLUGINS = {"sr_pivot": construir_sr_pivot}
BACKTESTS = {"sr_pivot": backtest_sr_pivot}
