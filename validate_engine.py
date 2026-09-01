# -*- coding: utf-8 -*-
"""
Validador del motor de backtest — ver BACKTEST_SPEC.md

Corre el motor canonico con LONDON_PARAMS sobre datos M1 reales y compara contra
los numeros de referencia. Si tu motor/config no reproduce esto, no es fiel al live.

    python validate_engine.py

Salida: PASA / FALLA por cada chequeo, con el diagnostico de que esta mal.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd

from strategies.order_block.backtest.backtester import OrderBlockBacktester
from strategies.order_block_london.backtest.config import LONDON_PARAMS

VELAS = Path(r"C:\Users\sosor\OneDrive\Documentos\velas m1")
M1_MAIN = VELAS / "US30_M1_202401020100_202605201838.csv"

# Referencia: motor canonico, M1 real, maxsim=2, riesgo 0.5%. Tolerancia +-5%.
REFERENCIA = {
    2024: {"trades": 709, "wr": 35.4, "pf": 1.23, "sumaR": 113.5},
    2025: {"trades": 808, "wr": 34.2, "pf": 1.17, "sumaR": 95.0},
}
TOL = 0.05
# Ritmo real del bot live, config actual: 126 trades / 47 dias habiles (jun-ago 2026).
# Sobre la serie completa abr-ago: 2.80/dia. Ver BACKTEST_SPEC.md seccion 3.
LIVE_TRADES_DIA = 2.68
# Piso de error grosero: la actividad varia entre anios (2.74 / 3.13 / 3.56 observados),
# asi que solo se marca FALLA bien por debajo del live, no por variacion normal.
PISO_TRADES_DIA = 2.40

ok_global = True


def chk(cond, msg, detalle=""):
    global ok_global
    print(f"  [{'PASA' if cond else 'FALLA'}] {msg}")
    if detalle and not cond:
        print(f"         -> {detalle}")
    if not cond:
        ok_global = False
    return cond


def load_mt5(path):
    d = pd.read_csv(path, sep="\t")
    d.columns = [c.strip("<>").lower() for c in d.columns]
    d["time"] = pd.to_datetime(d["date"] + " " + d["time"], format="%Y.%m.%d %H:%M:%S")
    return d[["time", "open", "high", "low", "close"]].sort_values("time").reset_index(drop=True)


def main():
    print("=" * 78)
    print("VALIDADOR DE MOTOR DE BACKTEST — ver BACKTEST_SPEC.md")
    print("=" * 78)

    print("\n1. CONFIGURACION")
    chk(LONDON_PARAMS["max_simultaneous_trades"] == 2,
        "max_simultaneous_trades = 2",
        f"esta en {LONDON_PARAMS['max_simultaneous_trades']}; con 1 el retorno cae ~13 pts")
    sess = LONDON_PARAMS["sessions"]["london"]
    chk(sess["start"] == "10:00" and sess["end"] == "17:00",
        "sesion London 10:00-17:00 (servidor)", f"esta en {sess['start']}-{sess['end']}")
    chk(LONDON_PARAMS["avg_spread_points"] + LONDON_PARAMS["slippage_points"] == 4,
        "costos = 4 pts/trade")

    if not M1_MAIN.exists():
        print(f"\n  No encuentro {M1_MAIN}")
        print("  Los chequeos de datos y referencia no se pueden correr.")
        sys.exit(1)

    print("\n2. DATOS")
    m1 = load_mt5(M1_MAIN)
    print(f"  M1: {len(m1)} velas ({m1.time.iloc[0]} -> {m1.time.iloc[-1]})")

    delta = m1["time"].diff().dt.total_seconds().mode()[0]
    chk(delta == 60, "granularidad de ejecucion = M1",
        f"el intervalo modal es {delta:.0f}s; con M5 la estrategia se ve perdedora (PF 0.98 vs 1.30)")

    rng = (m1["high"] - m1["low"]).groupby(m1["time"].dt.hour).mean()
    pico = int(rng.idxmax())
    chk(pico in (16, 17), f"zona horaria: pico de rango en {pico:02d}h (esperado 16-17h)",
        "los datos estan en otro huso; el filtro de sesion mide horas equivocadas")

    print("\n3. REFERENCIA (tolerancia +-5%)")
    for anio, ref in REFERENCIA.items():
        s = m1[(m1.time >= f"{anio}-01-01") & (m1.time < f"{anio+1}-01-01")].reset_index(drop=True)
        if len(s) < 5000:
            print(f"  {anio}: sin datos suficientes, salteado")
            continue
        h5 = (s.set_index("time").resample("5min", label="left", closed="left")
                .agg({"open": "first", "high": "max", "low": "min", "close": "last"})
                .dropna().reset_index())
        df = OrderBlockBacktester(LONDON_PARAMS).run(h5, s)
        r = df["pnl_r"].values
        w, l = r[r > 0], r[r <= 0]
        got = {"trades": len(r), "wr": (r > 0).mean() * 100,
               "pf": w.sum() / abs(l.sum()), "sumaR": r.sum()}
        dias = s.time.dt.date.nunique()
        tpd = len(r) / dias

        print(f"\n  --- {anio} ---")
        for k, esperado in ref.items():
            dif = abs(got[k] - esperado) / abs(esperado)
            chk(dif <= TOL, f"{k}: {got[k]:.1f} (ref {esperado}, dif {dif*100:.1f}%)")
        chk(tpd >= PISO_TRADES_DIA,
            f"ritmo {tpd:.2f} trades/dia (live {LIVE_TRADES_DIA}, piso {PISO_TRADES_DIA})",
            "muy por debajo del live: datos incompletos o un filtro de mas. "
            "El backtest no modela noticias/viernes/spread/STOPs sin llenar, "
            "asi que deberia dar MAS trades que el live, no menos")
        if PISO_TRADES_DIA <= tpd < LIVE_TRADES_DIA:
            print(f"         (aviso: por debajo del live {LIVE_TRADES_DIA}, "
                  f"aceptable si el anio fue de baja actividad)")

    print("\n" + "=" * 78)
    print("RESULTADO: " + ("MOTOR FIEL AL LIVE" if ok_global
                           else "MOTOR NO FIEL — revisar los FALLA de arriba"))
    print("=" * 78)
    if not ok_global:
        print("\nLeer BACKTEST_SPEC.md seccion 5: los cuatro errores ya cometidos.")
    sys.exit(0 if ok_global else 1)


if __name__ == "__main__":
    main()
