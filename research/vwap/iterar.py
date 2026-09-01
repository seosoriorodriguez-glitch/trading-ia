# -*- coding: utf-8 -*-
"""
Iteracion rapida sobre zonas VWAP del dia anterior. SOLO INVESTIGACION.

    python research/vwap/iterar.py                      # 30 dias, config base
    python research/vwap/iterar.py --dias 30 --ver      # lista las operaciones
    python research/vwap/iterar.py --si 2.01 --se 3.09 --tp rr --rr 2.5
    python research/vwap/iterar.py --dias 500           # muestra completa

PARA QUE SIRVEN 30 DIAS Y PARA QUE NO
  A ~0.8 operaciones/dia, 30 dias son ~25 trades. Con eso el error estandar del
  win rate es +-10 puntos: NO alcanza para decidir si algo funciona.
  Sirve para verificar MECANICA — que las entradas caigan donde uno espera, que
  los SL y TP tengan sentido, que se pueda cotejar contra el grafico.
  La pregunta del edge se contesta con la muestra completa.
"""
import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd

from research.vwap.vwap_lab import load_with_volume, resumen
from research.vwap import zonas_ayer as Z

VELAS = Path(r"C:\Users\sosor\OneDrive\Documentos\velas m1")
M1 = VELAS / "US30.cash_M1_202605050553_202608142349.csv"
M1_LARGO = VELAS / "US30_M1_202401020100_202605201838.csv"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dias", type=int, default=30)
    ap.add_argument("--si", type=float, default=2.01, help="sigma interno de la zona")
    ap.add_argument("--se", type=float, default=3.09, help="sigma externo de la zona")
    ap.add_argument("--tp", default="rr", choices=["rr", "vwap_ayer", "zona_opuesta"])
    ap.add_argument("--rr", type=float, default=2.0)
    ap.add_argument("--buffer", type=float, default=0.0)
    ap.add_argument("--expiry", type=int, default=60, help="min de vida de la pendiente")
    ap.add_argument("--maxdia", type=int, default=1)
    ap.add_argument("--maxrisk", type=float, default=None, help="descarta zonas mas anchas que esto")
    ap.add_argument("--slfrac", type=float, default=1.0, help="fraccion de la zona usada para el SL")
    ap.add_argument("--slpts", type=float, default=None, help="SL fijo en puntos (opcion 2)")
    ap.add_argument("--capsigma", type=float, default=None)
    ap.add_argument("--pen", type=float, default=0.0, help="penetracion exigida (0-1)")
    ap.add_argument("--ent", type=float, default=0.0, help="posicion del STOP en la zona (0-1)")
    ap.add_argument("--maxancho", type=float, default=None)
    ap.add_argument("--tf", type=int, default=1, help="1=cierre M1, 5=cierre M5")
    ap.add_argument("--ssl", type=float, default=None, help="SL en esta banda sigma")
    ap.add_argument("--sesion", default="10,17")
    ap.add_argument("--riesgo", type=float, default=0.005)
    ap.add_argument("--ver", action="store_true", help="listar operaciones")
    a = ap.parse_args()

    src = M1 if a.dias <= 70 else M1_LARGO
    m1 = load_with_volume(str(src))
    fechas = sorted(m1.time.dt.date.unique())
    corte = fechas[max(0, len(fechas) - a.dias - 1)]
    m1 = m1[m1.time.dt.date >= corte].reset_index(drop=True)
    ses = tuple(int(x) for x in a.sesion.split(","))
    dias = m1.time.dt.date.nunique()

    print(f"Datos: {src.name}")
    print(f"Ventana: {m1.time.min().date()} -> {m1.time.max().date()}  ({dias} dias)")
    print(f"Zona {a.si}-{a.se}s | TP={a.tp}"
          f"{' RR'+str(a.rr) if a.tp=='rr' else ''} | buffer {a.buffer} | "
          f"expiry {a.expiry}min | max {a.maxdia}/dia | sesion {ses[0]}-{ses[1]}h\n")

    r = Z.run(m1, s_int=a.si, s_ext=a.se, modo="cierre", tp=a.tp, rr=a.rr,
              buffer_pts=a.buffer, sesion=ses, expiry_min=a.expiry,
              max_por_dia=a.maxdia, max_risk_pts=a.maxrisk, sl_frac=a.slfrac,
              sl_pts=a.slpts, cap_sigma=a.capsigma,
              pen=a.pen, ent=a.ent, max_ancho=a.maxancho, tf=a.tf, s_sl=a.ssl)

    if len(r) == 0:
        print("Sin operaciones."); return

    resumen(r, "  resultado", dias, riesgo=a.riesgo)
    if len(r) < 40:
        import math
        se = math.sqrt(0.4 * 0.6 / len(r)) * 100
        print(f"  AVISO: n={len(r)}. Error estandar del WR = +-{se:.0f} pp. "
              f"Sirve para verificar mecanica, no para concluir.")

    if a.ver:
        print(f"\n{'senal':>17} {'entrada':>17} {'dir':>6} {'entry':>10} "
              f"{'SL':>10} {'TP':>10} {'riesgo':>8} {'zona':>6} {'R':>6}")
        print("-" * 106)
        for _, t in r.iterrows():
            print(f"{pd.Timestamp(t['senal']).strftime('%m-%d %H:%M'):>17} "
                  f"{pd.Timestamp(t['entry_time']).strftime('%m-%d %H:%M'):>17} "
                  f"{'LONG' if t['dir']==1 else 'SHORT':>6} {t['entry']:10.1f} "
                  f"{t['sl']:10.1f} {t['tp']:10.1f} {t['risk']:8.1f} "
                  f"{t['zona']:>6} {t['r']:+6.2f}")
        print("\n  Horas en SERVIDOR (UTC+3). En tu chart de New_York restá 7.")


if __name__ == "__main__":
    main()
