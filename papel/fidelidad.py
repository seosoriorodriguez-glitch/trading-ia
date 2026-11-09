# -*- coding: utf-8 -*-
"""
Comparacion diaria PAPEL vs BACKTEST: corre el backtest de la estrategia sobre las velas M1 del MISMO broker y el
MISMO periodo en que estuvo en papel, y lo compara trade por trade con lo que hizo en papel.

  - Velas: las del terminal (copy_rates_from_pos, por cantidad: no depende de husos horarios), con 40 dias de margen
    antes del inicio para que los niveles se formen igual.
  - Spread del backtest: la mediana del spread de esas velas (el del broker, no el de FTMO).
  - Coincide = misma direccion y entrada en el mismo minuto (+-1). Diferencias esperables: el papel llena con cada
    tick real y el backtest con supuestos de vela (SL - 0.7, el TP no en la vela de entrada).
"""
import json
from pathlib import Path

import pandas as pd


def velas_m1(mt5, simbolo: str, desde: pd.Timestamp, margen_dias: int = 40) -> pd.DataFrame:
    i = mt5.symbol_info_tick(simbolo)
    ahora = pd.Timestamp(i.time, unit="s")
    n = int(min(99_000, (ahora - (desde - pd.Timedelta(days=margen_dias))).total_seconds() // 60 + 10))
    r = mt5.copy_rates_from_pos(simbolo, mt5.TIMEFRAME_M1, 0, n)
    if r is None or len(r) < 2:
        return pd.DataFrame()
    d = pd.DataFrame(r)
    d["time"] = pd.to_datetime(d["time"], unit="s")
    return d.iloc[:-1][["time", "open", "high", "low", "close", "spread"]]     # sin la vela en formacion


def comparar(papel: pd.DataFrame, bt: pd.DataFrame) -> dict:
    """papel / bt: entry_time, direction, R. Devuelve el resumen de coincidencias."""
    if not len(papel) and not len(bt):
        return {"papel": 0, "backtest": 0, "coinciden": 0, "solo_papel": 0, "solo_backtest": 0,
                "R_papel": 0.0, "R_backtest": 0.0, "R_coinciden_papel": 0.0, "R_coinciden_backtest": 0.0}
    p = papel.assign(m=pd.to_datetime(papel.entry_time).dt.floor("min")).reset_index(drop=True)
    b = bt.assign(m=pd.to_datetime(bt.entry_time).dt.floor("min")).reset_index(drop=True)
    usados, pares = set(), []
    for i, x in p.iterrows():
        cand = b[(b.direction == x.direction) & ((b.m - x.m).abs() <= pd.Timedelta(minutes=1))]
        cand = cand[~cand.index.isin(usados)]
        if len(cand):
            j = cand.index[0]
            usados.add(j)
            pares.append((i, j))
    ip, ib = [a for a, _ in pares], [c for _, c in pares]
    return {"papel": len(p), "backtest": len(b), "coinciden": len(pares), "solo_papel": len(p) - len(pares),
            "solo_backtest": len(b) - len(pares), "R_papel": round(float(p.R.sum()), 2),
            "R_backtest": round(float(b.R.sum()), 2), "R_coinciden_papel": round(float(p.loc[ip].R.sum()), 2),
            "R_coinciden_backtest": round(float(b.loc[ib].R.sum()), 2)}


def guardar(carpeta: Path, resumen: dict):
    (Path(carpeta) / "fidelidad.json").write_text(json.dumps(resumen, indent=1, default=str))
