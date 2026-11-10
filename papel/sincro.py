# -*- coding: utf-8 -*-
"""
Sube al panel (Supabase) lo que hacen las estrategias en papel, en las MISMAS tablas y con el mismo formato que el
colector, para que el panel las muestre como cualquier cuenta. 100 % aditivo:
  - solo escribe filas de ids "lab_..." (el panel las manda a Lab · Demo y las saca del portafolio real);
  - cuentas virtuales >= 9 000 000 000 y tickets = cuenta x 100 000 + n: nunca chocan con cuentas ni tickets reales;
  - no crea tablas ni cambia columnas; tablas: bots, trades, account_snapshots, trade_candles.
Horas: como el colector, la hora del SERVIDOR guardada con sufijo UTC (el panel la corrige).

El backtest del mismo periodo (papel/fidelidad.py) se guarda como "<id>__bt", archivado (active = false): no aparece
en ninguna lista, solo lo usa el detalle de la estrategia para comparar trade por trade.
"""
import os
from datetime import datetime, timedelta

import pandas as pd

SUF_BT = "__bt"
DESFASE_BT = 500_000_000            # cuenta del backtest = cuenta del papel + esto


def cliente():
    from supabase import create_client
    return create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])


def ticket_de(cuenta: int, n: int) -> int:
    return int(cuenta) * 100_000 + int(n)


def session_of(hour_server: int) -> str:                 # igual que panel/collector/collector.py
    if 10 <= hour_server < 13:
        return "london"
    if 13 <= hour_server < 17:
        return "london_ny"
    if 17 <= hour_server < 23:
        return "new_york"
    return "off"


def _iso(t) -> str:
    return pd.Timestamp(t).tz_localize(None).isoformat() + "+00:00"


def fila_bot(e: dict, backtest: bool = False) -> dict:
    return {"id": e["id"] + (SUF_BT if backtest else ""),
            "name": e["nombre"] + (" · backtest del mismo periodo" if backtest else ""),
            "symbol": e["simbolo"], "account": e["cuenta"] + (DESFASE_BT if backtest else 0),
            "session": e.get("sesion", "24h"), "risk_pct": e["riesgo_pct"], "initial_balance": e["balance"],
            "rr": e.get("params", {}).get("RR", 2.5), "magic": None, "active": not backtest}


def fila_trade(e: dict, cuenta: int, n: int, h: dict) -> dict:
    """h: registro de una posicion cerrada (broker_papel.hist o un trade del backtest normalizado)."""
    larga = h["lado"] == "long"
    ent, sal, sl = float(h["entrada"]), float(h["salida"]), h.get("sl")
    ref = float(h["orden"]) if h.get("orden") is not None else ent      # riesgo nominal (orden - SL), como el backtest
    riesgo = abs(ref - sl) if sl else None
    pts = (sal - ent) if larga else (ent - sal)
    motivo = {"tp": "tp", "sl": "sl", "sl_hueco": "sl"}.get(h["comentario_salida"], "other")
    eh = pd.Timestamp(h["entrada_hora"])
    return {"bot_id": e["id"] if cuenta == e["cuenta"] else e["id"] + SUF_BT, "account": cuenta,
            "ticket": ticket_de(cuenta, n), "symbol": e["simbolo"], "direction": h["lado"],
            "entry_price": round(ent, 2), "sl": sl, "tp": h.get("tp"), "exit_price": round(sal, 2),
            "entry_time": _iso(eh), "exit_time": _iso(h["salida_hora"]), "exit_reason": motivo,
            "risk_points": round(riesgo, 2) if riesgo else None, "volume": float(h.get("volumen", 0) or 0),
            "pnl_usd": round(float(h.get("profit", 0)) + float(h.get("swap", 0)) + float(h.get("comision", 0)), 2),
            "pnl_r": round(pts / riesgo, 3) if riesgo else None,
            "session": session_of(eh.hour)}


def velas_m5(mt5, simbolo: str, desde, hasta) -> list:
    """Velas M5 alrededor de un trade, como el colector (para el grafico del panel)."""
    d0 = pd.Timestamp(desde).to_pydatetime() - timedelta(hours=4)
    d1 = pd.Timestamp(hasta).to_pydatetime() + timedelta(hours=2)
    r = mt5.copy_rates_range(simbolo, mt5.TIMEFRAME_M5, d0, d1)
    if r is None or len(r) == 0:
        return []
    return [{"t": int(x["time"]), "o": float(x["open"]), "h": float(x["high"]), "l": float(x["low"]),
             "c": float(x["close"])} for x in r]


class Sincro:
    def __init__(self, sb, log=print):
        self.sb = sb
        self.log = log

    def registrar(self, e: dict):
        self.sb.table("bots").upsert(fila_bot(e), on_conflict="id").execute()
        self.sb.table("bots").upsert(fila_bot(e, backtest=True), on_conflict="id").execute()

    def trades(self, e: dict, filas: list):
        if filas:
            self.sb.table("trades").upsert(filas, on_conflict="account,ticket").execute()

    def velas(self, e: dict, mt5, filas: list):
        lote = []
        for f in filas:
            c = velas_m5(mt5, e["simbolo"], f["entry_time"][:19], f["exit_time"][:19])
            if c:
                lote.append({"ticket": f["ticket"], "bot_id": f["bot_id"], "account": f["account"], "candles": c})
        if lote:
            self.sb.table("trade_candles").upsert(lote, on_conflict="ticket").execute()

    def snapshot(self, e: dict, balance: float, equity: float):
        self.sb.table("account_snapshots").insert({"bot_id": e["id"], "account": e["cuenta"],
                                                   "balance": round(balance, 2), "equity": round(equity, 2)}).execute()

    def backtest(self, e: dict, filas: list):
        """Reemplaza los trades del backtest del periodo (se recalcula entero cada dia)."""
        cta = e["cuenta"] + DESFASE_BT
        self.sb.table("trades").delete().eq("account", cta).eq("bot_id", e["id"] + SUF_BT).execute()
        if filas:
            self.sb.table("trades").upsert(filas, on_conflict="account,ticket").execute()
