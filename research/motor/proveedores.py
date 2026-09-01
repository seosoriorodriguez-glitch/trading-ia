# -*- coding: utf-8 -*-
"""
Proveedores de zonas para el motor generico. Solo investigacion.

Cada funcion recibe M1 y devuelve List[Zona]. Nada mas. Toda la mecanica de
entrada, SL, TP y gestion vive en motor_zonas.py.

REGLA COMUN: `desde` es el momento en que la zona pasa a ser OPERABLE, que no es
lo mismo que cuando se formo. Si una zona necesita N velas posteriores para
confirmarse, `desde` va DESPUES de esas N velas. Ahi es donde se cuelan los
lookahead (ver BACKTEST_SPEC.md, errores #1 y #2).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np
import pandas as pd

from research.motor.motor_zonas import Zona


def _m5(m1):
    return (m1.set_index("time").resample("5min", label="left", closed="left")
            .agg({"open": "first", "high": "max", "low": "min", "close": "last"})
            .dropna().reset_index())


# ------------------------------------------------------------------ ORDER BLOCK
def ob(m1, params=None, expiry_velas=100):
    """
    Usa detect_order_blocks() DEL REPO — el mismo modulo que corre el bot live.

    Antes esto era una reimplementacion mia y se perdia OBs: el 10-ago detectaba
    3 operaciones donde el motor fiel encontraba 4, y el dia cerraba en +0.27R en
    vez de +2.47R (el live dio +3.0R). No reimplementar detecciones que ya existen.

    `confirmed_at` ya viene sin lookahead: es cuando el OB se vuelve operable.
    """
    from strategies.order_block.backtest.ob_detection import detect_order_blocks
    from strategies.order_block_london.backtest.config import LONDON_PARAMS
    q = dict(LONDON_PARAMS)
    if params:
        q.update(params)
    d = _m5(m1)
    t = d["time"].values
    n = len(d)
    out = []
    idx = {v: k for k, v in enumerate(t)}
    for o in detect_order_blocks(d, q):
        # el motor cuenta expiry desde CONFIRMED_AT, no desde la vela del OB
        ic = idx.get(np.datetime64(o.confirmed_at), o.ob_candle_idx)
        fin = t[min(ic + q.get("expiry_candles", expiry_velas), n - 1)]
        out.append(Zona(np.datetime64(o.confirmed_at), fin, o.zone_low, o.zone_high,
                        "alcista" if o.ob_type == "bullish" else "bajista", "OB"))
    return out


# ------------------------------------------------------------ BANDAS VWAP AYER
def vwap_ayer(m1, s_int=1.28, s_ext=2.51, min_barras=30):
    """Bandas del VWAP diario al CIERRE de ayer, proyectadas fijas sobre hoy."""
    d = m1.copy(); d["dia"] = d.time.dt.date
    hl2 = (d.high + d.low) / 2.0
    v = d.volume.astype(float).clip(lower=1e-9)
    pv = (hl2 * v).groupby(d.dia).cumsum(); vv = v.groupby(d.dia).cumsum()
    v2 = (v * hl2 * hl2).groupby(d.dia).cumsum()
    vw = pv / vv
    dev = np.sqrt(np.maximum(v2 / vv - vw * vw, 0))
    nb = d.groupby("dia").cumcount()
    tmp = pd.DataFrame({"dia": d.dia, "vw": vw, "dev": dev})[nb >= min_barras]
    cierre = tmp.groupby("dia").last()
    lim = d.groupby("dia").time.agg(["min", "max"])
    dias = list(cierre.index)
    out = []
    for prev, hoy in zip(dias[:-1], dias[1:]):
        r = cierre.loc[prev]
        if hoy not in lim.index:
            continue
        d0, d1 = lim.loc[hoy, "min"].to_datetime64(), lim.loc[hoy, "max"].to_datetime64()
        out.append(Zona(d0, d1, r.vw + s_int * r.dev, r.vw + s_ext * r.dev,
                        "bajista", "VWAP"))
        out.append(Zona(d0, d1, r.vw - s_ext * r.dev, r.vw - s_int * r.dev,
                        "alcista", "VWAP"))
    return out


# --------------------------------------------------------------------- FVG
def fvg(m1, params=None):
    """Usa detect_fvgs() DEL REPO (strategies/fair_value_gap), no una version propia."""
    from strategies.fair_value_gap.backtest.fvg_detection import detect_fvgs
    from strategies.fair_value_gap.backtest.config import US30_PARAMS as FVG_PARAMS
    q = dict(FVG_PARAMS)
    if params:
        q.update(params)
    d = _m5(m1)
    t = d["time"].values
    n = len(d)
    out = []
    for f in detect_fvgs(d, q):
        i = f.fvg_candle_idx
        fin = t[min(i + q.get("expiry_candles", 100), n - 1)]
        out.append(Zona(np.datetime64(f.confirmed_at), fin, f.zone_low, f.zone_high,
                        "alcista" if f.fvg_type == "bullish" else "bajista", "FVG"))
    return out


# ------------------------------------------- PERFIL DE VOLUMEN: POC / VAH / VAL
def perfil_volumen(m1, bins=60, valor_pct=0.70, ancho_pts=None, min_barras=30):
    """
    Perfil del dia ANTERIOR proyectado a hoy.
      POC = precio con mas volumen | VAH/VAL = bordes del 70% del volumen
    Zonas: [VAL, POC] alcista y [POC, VAH] bajista, o bandas de `ancho_pts`
    alrededor de cada nivel si se especifica.
    AVISO: con <VOL>=0 esto usa tickvol, que es actividad y no contratos.
    """
    d = m1.copy(); d["dia"] = d.time.dt.date
    lim = d.groupby("dia").time.agg(["min", "max"])
    dias = sorted(d.dia.unique())
    out = []
    for prev, hoy in zip(dias[:-1], dias[1:]):
        g = d[d.dia == prev]
        if len(g) < min_barras:
            continue
        precio = (g.high + g.low) / 2.0
        vol = g.volume.astype(float).clip(lower=1e-9)
        hist, bordes = np.histogram(precio, bins=bins, weights=vol)
        centros = (bordes[:-1] + bordes[1:]) / 2
        poc = centros[hist.argmax()]
        orden = np.argsort(hist)[::-1]
        acum = np.cumsum(hist[orden]) / hist.sum()
        sel = centros[orden[:np.searchsorted(acum, valor_pct) + 1]]
        val, vah = sel.min(), sel.max()
        d0, d1 = lim.loc[hoy, "min"].to_datetime64(), lim.loc[hoy, "max"].to_datetime64()
        if ancho_pts:
            for niv, nom in ((poc, "POC"), (vah, "VAH"), (val, "VAL")):
                out.append(Zona(d0, d1, niv - ancho_pts / 2, niv + ancho_pts / 2,
                                "alcista", nom))
                out.append(Zona(d0, d1, niv - ancho_pts / 2, niv + ancho_pts / 2,
                                "bajista", nom))
        else:
            out.append(Zona(d0, d1, val, poc, "alcista", "VAL-POC"))
            out.append(Zona(d0, d1, poc, vah, "bajista", "POC-VAH"))
    return out


PROVEEDORES = {"ob": ob, "vwap": vwap_ayer, "fvg": fvg, "perfil": perfil_volumen}
