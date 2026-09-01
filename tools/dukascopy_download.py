# -*- coding: utf-8 -*-
"""
Descarga velas M1 desde Dukascopy y las deja en hora de servidor del broker (EET/EEST).

Dukascopy sirve ticks en archivos .bi5 (LZMA) por hora, en UTC:
    https://datafeed.dukascopy.com/datafeed/{INST}/{YYYY}/{MM0}/{DD}/{HH}h_ticks.bi5
    OJO: MM0 esta indexado desde 0 (enero = 00).

Cada registro son 20 bytes big-endian: uint32 ms_desde_la_hora, uint32 ask, uint32 bid,
float32 vol_ask, float32 vol_bid. Precios enteros -> dividir por DIVISOR.

CONVERSION HORARIA — critico
  El broker MT5 usa EET/EEST: UTC+2 en invierno, UTC+3 en verano (DST europeo,
  ultimo domingo de marzo a ultimo domingo de octubre). Asi la apertura del cash
  de NY (09:30 ET) cae SIEMPRE en 16:30 hora de servidor.
  Aplicar +3 fijo desplaza la sesion una hora en invierno.

Uso:
    python tools/dukascopy_download.py USATECHIDXUSD 2025-01-01 2025-12-31 data/NAS100_duka_M1.csv
"""
import io
import lzma
import struct
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import pandas as pd
import requests

BASE = "https://datafeed.dukascopy.com/datafeed"
HEADERS = {"User-Agent": "Mozilla/5.0"}
DIVISOR = 1000.0          # indices: 3 decimales
# Dukascopy limita: con 12 hilos se perdia ~80% de las peticiones POR TIMEOUT, en
# silencio (5 dias devolvian menos ticks que 1 dia secuencial). No subir de 4.
WORKERS = 4
TIMEOUT = 45
REINTENTOS = 4
MAX_FALLOS_PCT = 2.0      # aborta si se pierde mas de esto

INSTRUMENTOS = {
    "USATECHIDXUSD": "NASDAQ 100",
    "USA30IDXUSD":   "Dow 30",
    "USA500IDXUSD":  "S&P 500",
    "DEUIDXEUR":     "DAX 40",
}


def _last_sunday(year, month):
    d = datetime(year, month, 31) if month == 3 else datetime(year, month, 31)
    while d.month != month:
        d -= timedelta(days=1)
    while d.weekday() != 6:
        d -= timedelta(days=1)
    return d


def offset_broker(dt_utc):
    """UTC -> offset del servidor MT5 (EET/EEST). +3 en verano europeo, +2 en invierno."""
    ini = _last_sunday(dt_utc.year, 3).replace(hour=1)     # 01:00 UTC
    fin = _last_sunday(dt_utc.year, 10).replace(hour=1)
    return 3 if ini <= dt_utc.replace(tzinfo=None) < fin else 2


def fetch_hour(args):
    """Devuelve (dt, ticks, estado). estado: 'ok' | 'vacio' | 'fallo'.
    Distinguir vacio de fallo es esencial: un vacio es mercado cerrado, un fallo
    es data perdida que corrompe el backtest sin avisar."""
    inst, dt = args
    url = f"{BASE}/{inst}/{dt.year}/{dt.month-1:02d}/{dt.day:02d}/{dt.hour:02d}h_ticks.bi5"
    for intento in range(REINTENTOS):
        try:
            r = requests.get(url, timeout=TIMEOUT, headers=HEADERS)
            if r.status_code == 404:
                return dt, [], "vacio"
            if r.status_code != 200:
                raise IOError(f"status {r.status_code}")
            if not r.content:
                # OJO: un cuerpo vacio puede ser mercado cerrado O throttling.
                # Medido: con 8 hilos aparecian 10 "vacias" en horas de mercado abierto
                # que en realidad eran limitacion de tasa. Aceptarlas dejaba huecos
                # invisibles en la serie. Se reintenta; si es cierre real sigue vacia.
                if intento < REINTENTOS - 1:
                    time.sleep(2.0 * (intento + 1))
                    continue
                return dt, [], "vacio"
            raw = lzma.decompress(r.content, format=lzma.FORMAT_AUTO)
            # BUG HISTORICO: dt.timestamp() sobre un datetime naive lo interpreta como
            # hora LOCAL de la maquina. En Chile (UTC-4) eso corria toda la serie 4 horas
            # y la correlacion contra MT5 caia de 0.9997 a 0.7696. dt SIEMPRE es UTC aca.
            base = dt.replace(tzinfo=timezone.utc).timestamp()
            out = []
            for i in range(len(raw) // 20):
                ms, ask, bid, _, _ = struct.unpack_from(">IIIff", raw, i * 20)
                out.append((base + ms / 1000.0, ask / DIVISOR, bid / DIVISOR))
            return dt, out, "ok"
        except Exception:
            if intento == REINTENTOS - 1:
                return dt, [], "fallo"
            time.sleep(2.0 * (intento + 1))
    return dt, [], "fallo"


def descargar(inst, desde, hasta):
    horas = []
    d = desde
    while d <= hasta:
        if d.weekday() < 5 or (d.weekday() == 6 and d.hour >= 21):   # el mercado abre dom 21 UTC
            horas.append((inst, d))
        d += timedelta(hours=1)
    print(f"  {len(horas)} horas a descargar con {WORKERS} hilos...")

    ticks = []
    hechas = ok = vacio = fallo = 0
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        for dt, t, estado in ex.map(fetch_hour, horas):
            ticks.extend(t)
            hechas += 1
            if estado == "ok":      ok += 1
            elif estado == "vacio": vacio += 1
            else:                   fallo += 1
            if hechas % 200 == 0:
                print(f"    {hechas}/{len(horas)}  ticks={len(ticks):,}  fallos={fallo}", flush=True)

    pct = fallo / max(1, len(horas)) * 100
    print(f"  horas: {ok} con datos | {vacio} vacias (mercado cerrado) | {fallo} FALLIDAS ({pct:.1f}%)")
    if pct > MAX_FALLOS_PCT:
        raise RuntimeError(
            f"Se perdio {pct:.1f}% de las horas por error de red (limite {MAX_FALLOS_PCT}%).\n"
            f"La serie tendria huecos y el backtest daria numeros falsos sin avisar.\n"
            f"Bajar WORKERS o reintentar."
        )
    return ticks


def a_m1(ticks):
    """Ticks -> velas M1 en hora de servidor (mid price)."""
    if not ticks:
        return pd.DataFrame()
    df = pd.DataFrame(ticks, columns=["ts", "ask", "bid"])
    df["mid"] = (df.ask + df.bid) / 2
    df["utc"] = pd.to_datetime(df.ts, unit="s", utc=True).dt.tz_localize(None)
    off = df["utc"].map(lambda x: offset_broker(x))
    df["time"] = df["utc"] + pd.to_timedelta(off, unit="h")
    g = df.set_index("time")["mid"].resample("1min")
    out = pd.DataFrame({"open": g.first(), "high": g.max(),
                        "low": g.min(), "close": g.last()}).dropna().reset_index()
    return out


if __name__ == "__main__":
    if len(sys.argv) < 5:
        print(__doc__)
        print("Instrumentos:", ", ".join(f"{k} ({v})" for k, v in INSTRUMENTOS.items()))
        sys.exit(1)
    inst, d0, d1, salida = sys.argv[1:5]
    desde = datetime.strptime(d0, "%Y-%m-%d")
    hasta = datetime.strptime(d1, "%Y-%m-%d") + timedelta(hours=23)
    print(f"Dukascopy {inst} ({INSTRUMENTOS.get(inst,'?')})  {d0} -> {d1}")
    t0 = time.time()
    ticks = descargar(inst, desde, hasta)
    print(f"  {len(ticks):,} ticks en {time.time()-t0:.0f}s")
    m1 = a_m1(ticks)
    m1.to_csv(salida, index=False)
    print(f"  {len(m1):,} velas M1 -> {salida}")
    if len(m1):
        print(f"  rango: {m1.time.iloc[0]} -> {m1.time.iloc[-1]}  (hora de servidor EET/EEST)")
