# -*- coding: utf-8 -*-
"""
Colector Panel de Trading — lee el historial de MT5 de cada cuenta y lo sube a
Supabase. 100% ADITIVO: no importa ni modifica los bots; solo lee MT5.

Corre en el VPS (donde estan las terminales MT5). Loop cada ~60s.

Env (.env o variables):
  SUPABASE_URL=https://xxxx.supabase.co
  SUPABASE_SERVICE_KEY=eyJ...      (service_role key, NO la anon)

Config de bots:  config.json  (ver config.example.json)
Uso:  python collector.py
"""
import os, json, time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import MetaTrader5 as mt5
from supabase import create_client

ROOT = Path(__file__).parent
CFG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
SB = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])
LOOKBACK_DAYS = 5           # ventana de historial a revisar cada corrida (dedup por unique)
POLL_SECONDS = 60

# --- Vista "En vivo": sesión actual con zonas OB (solo lectura de tu detección real) ---
# symbol -> (hora_inicio, hora_fin) en hora del SERVIDOR MT5 (UTC+3). Fuera de ventana = se limpia.
LIVE_VIEW = {
    "US30.cash":  (10, 17),
    "GER40.cash": (10, 17),
}
OB_PARAMS = {"consecutive_candles": 4, "min_impulse_pct": 0.0, "zone_type": "half_candle", "max_atr_mult": 3.5}
VIEW_MARGIN_H = 2           # horas de contexto antes y después de la sesión (ver zonas previas + qué pasó después)
SESSION_DONE = set()        # símbolos ya empujados en el ciclo actual (evita duplicar el pull)
_LAST_SESSION = {}          # symbol -> date de la última sesión ya congelada (evita rehacerla fuera de horario)
try:
    import sys
    import pandas as pd
    sys.path.insert(0, str(ROOT.parent.parent))   # raíz del repo
    from strategies.order_block.backtest.ob_detection import detect_order_blocks
    _OB_OK = True
except Exception as _e:      # pandas o la estrategia no disponibles → velas sin zonas
    _OB_OK = False
    print(f"[session_view] detección OB no disponible ({_e}); guardaré velas sin zonas", flush=True)


def session_of(hour_server: int) -> str:
    if 10 <= hour_server < 13:   return "london"
    if 13 <= hour_server < 17:   return "london_ny"
    if 17 <= hour_server < 23:   return "new_york"
    return "off"


def push_session_view(symbol: str):
    """Guarda las velas M5 de la SESIÓN ACTUAL + las zonas OB (recalculadas con tu
    detección real). Sobrescribe por símbolo (rodante). Fuera de sesión → limpia."""
    win = LIVE_VIEW.get(symbol)
    if not win:
        return
    start_h, end_h = win                     # hora SERVIDOR (el t de cada vela ya viene en hora servidor)
    tick = mt5.symbol_info_tick(symbol)
    if not tick:
        return
    swc = lambda t: datetime.fromtimestamp(int(t), tz=timezone.utc).replace(tzinfo=None)  # hora servidor de un t
    now = swc(tick.time)
    in_session = start_h <= now.hour < end_h
    # Traer las últimas velas por POSICIÓN (sin fechas) y filtrar por la hora del propio t.
    # Evita el desfase de zona horaria de copy_rates_range en MT5.
    bars = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M5, 0, 800)
    if bars is None or len(bars) == 0:
        return
    insess = [x for x in bars if start_h <= swc(x["time"]).hour < end_h]   # solo London (para elegir el día)
    if in_session:
        target = now.date()
        live = True
    else:
        days = sorted({swc(x["time"]).date() for x in insess})            # última fecha con sesión (maneja finde)
        if not days:
            return
        target = days[-1]
        if _LAST_SESSION.get(symbol) == target:
            return                                                         # ya congelada este proceso
        live = False
    # ventana AMPLIADA ±VIEW_MARGIN_H: contexto antes (zonas previas) y después (qué pasó)
    dstart, dend = start_h - VIEW_MARGIN_H, end_h + VIEW_MARGIN_H
    # NO congelar al cerrar la sesión: el margen posterior aún no ha ocurrido. Seguir
    # refrescando (ya con live=False) hasta que pasen las VIEW_MARGIN_H horas de cola.
    tail_done = not (now.date() == target and now.hour < dend)
    sess = [x for x in bars if swc(x["time"]).date() == target and dstart <= swc(x["time"]).hour < dend]
    if not sess:
        if not live and tail_done:
            _LAST_SESSION[symbol] = target
        return
    candles = [{"t": int(x["time"]), "o": float(x["open"]), "h": float(x["high"]),
                "l": float(x["low"]), "c": float(x["close"])} for x in sess]
    zones = []
    if _OB_OK and len(candles) > OB_PARAMS["consecutive_candles"] + 2:
        try:
            # armar el df desde las velas ya normalizadas (nombres correctos garantizados)
            df = pd.DataFrame(candles).rename(columns={"t": "time", "o": "open", "h": "high", "l": "low", "c": "close"})
            for o in detect_order_blocks(df, OB_PARAMS):
                later = df[df["time"] > o.confirmed_at]   # ¿precio cerró al otro lado? (zona gastada)
                spent = bool((later["close"] < o.zone_low).any()) if o.ob_type == "bullish" \
                    else bool((later["close"] > o.zone_high).any())
                zones.append({"type": o.ob_type, "high": float(o.zone_high), "low": float(o.zone_low),
                              "at": int(o.ob_candle_time), "spent": spent})   # 'at' = vela de origen del OB (donde nace la zona)
            zones = zones[-16:]                            # limitar para no saturar el gráfico
        except Exception as e:
            print(f"[session_view {symbol}] zonas fallo ({e})", flush=True)
    SB.table("session_view").upsert({
        "symbol": symbol, "session": "london", "live": live,
        "candles": candles, "zones": zones,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }, on_conflict="symbol").execute()
    if not live and tail_done:
        _LAST_SESSION[symbol] = target
    state = "EN VIVO" if live else ("congelada" if tail_done else "cerrada (+cola)")
    print(f"[session_view {symbol}] {state} · {len(candles)} velas · {len(zones)} zonas", flush=True)


def upsert_bots():
    for b in CFG["bots"]:
        SB.table("bots").upsert({
            "id": b["id"], "name": b["name"], "symbol": b["symbol"],
            "account": b.get("account"), "session": b.get("session"),
            "risk_pct": b.get("risk_pct"), "initial_balance": b.get("initial_balance"),
            "rr": b.get("rr"), "magic": b.get("magic"), "active": True,
        }, on_conflict="id").execute()


def collect_bot(b: dict):
    if not mt5.initialize(path=b["terminal_path"]):
        print(f"[{b['id']}] no conecta MT5: {mt5.last_error()}", flush=True); return
    try:
        acc = mt5.account_info()
        if acc is None:
            print(f"[{b['id']}] sin account_info", flush=True); return
        live_acct = int(acc.login)
        # El usuario ROTA la cuenta en el mismo terminal (mismo bot). No saltamos:
        # seguimos con la cuenta actual y actualizamos el registro del bot.
        if b.get("account") and live_acct != int(b["account"]):
            print(f"[{b['id']}] cuenta rotó: {b['account']} -> {live_acct}. Actualizo registro.", flush=True)
        SB.table("bots").update({"account": live_acct}).eq("id", b["id"]).execute()

        # snapshot balance/equity
        SB.table("account_snapshots").insert({
            "bot_id": b["id"], "account": int(acc.login),
            "balance": float(acc.balance), "equity": float(acc.equity),
        }).execute()

        # historial de deals de la ventana.
        # Límite superior = now + 1 día: MT5 interpreta el rango en hora del servidor (UTC+3),
        # así que un tope "now + minutos" (UTC) deja fuera los trades de las últimas ~3h.
        # Un tope futuro es inofensivo (no hay deals futuros) y elimina ese retraso.
        now = datetime.now(timezone.utc)
        deals = mt5.history_deals_get(now - timedelta(days=LOOKBACK_DAYS), now + timedelta(days=1))
        if deals is None:
            return
        magic = b.get("magic")
        # operaciones de BALANCE (depositos/retiros) — se rastrean SIEMPRE (sin filtro de magic)
        bops = []
        for d in deals:
            if d.type == mt5.DEAL_TYPE_BALANCE:
                bops.append({
                    "bot_id": b["id"], "account": live_acct, "ticket": int(d.ticket),
                    "amount": float(d.profit),   # + deposito, - retiro
                    "ts": datetime.fromtimestamp(d.time, tz=timezone.utc).isoformat(),
                    "comment": (getattr(d, "comment", "") or ""),
                })
        if bops:
            SB.table("balance_ops").upsert(bops, on_conflict="account,ticket").execute()
            print(f"[{b['id']}] {len(bops)} op. de balance (dep/retiro)", flush=True)
        # agrupar por posicion (trades reales)
        pos = {}
        for d in deals:
            if d.type == mt5.DEAL_TYPE_BALANCE:
                continue
            if magic is not None and d.magic != magic:
                continue
            pos.setdefault(d.position_id, []).append(d)

        rows = []
        for pid, ds in pos.items():
            ins = [d for d in ds if d.entry == mt5.DEAL_ENTRY_IN]
            outs = [d for d in ds if d.entry == mt5.DEAL_ENTRY_OUT]
            if not ins or not outs:
                continue                     # posicion aun abierta o incompleta
            din, dout = ins[0], outs[-1]
            direction = "long" if din.type == mt5.DEAL_TYPE_BUY else "short"
            entry, exitp = float(din.price), float(dout.price)
            pnl_usd = sum(float(d.profit) + float(d.commission) + float(d.swap) for d in ds)
            # SL/TP de la orden de apertura
            orders = mt5.history_orders_get(position=pid)
            sl = tp = None
            if orders:
                op = orders[0]
                sl, tp = float(op.sl) or None, float(op.tp) or None
            risk_pts = abs(entry - sl) if sl else None
            pnl_pts = (exitp - entry) if direction == "long" else (entry - exitp)
            pnl_r = round(pnl_pts / risk_pts, 3) if risk_pts else None
            reason = "other"
            if sl and tp:
                reason = "tp" if abs(exitp - tp) < abs(exitp - sl) else "sl"
            etime = datetime.fromtimestamp(din.time, tz=timezone.utc)
            xtime = datetime.fromtimestamp(dout.time, tz=timezone.utc)
            rows.append({
                "bot_id": b["id"], "account": int(acc.login), "ticket": int(pid),
                "symbol": b["symbol"], "direction": direction,
                "entry_price": entry, "sl": sl, "tp": tp, "exit_price": exitp,
                "entry_time": etime.isoformat(), "exit_time": xtime.isoformat(),
                "exit_reason": reason, "risk_points": risk_pts, "volume": float(din.volume),
                "pnl_usd": round(pnl_usd, 2), "pnl_r": pnl_r,
                "session": b.get("session") or session_of((etime + timedelta(hours=3)).hour),
            })
        if rows:
            SB.table("trades").upsert(rows, on_conflict="account,ticket").execute()
            print(f"[{b['id']}] {len(rows)} trades sincronizados (cuenta {acc.login})", flush=True)

            # velas M5 alrededor de cada trade NUEVO (para el grafico del panel)
            existing = set()
            try:
                ex = SB.table("trade_candles").select("ticket").eq("account", live_acct).execute()
                existing = {int(r["ticket"]) for r in (ex.data or [])}
            except Exception as e:
                print(f"[{b['id']}] trade_candles no disponible ({e})", flush=True)
            cbatch = []
            for r in rows:
                if r["ticket"] in existing:
                    continue
                et = datetime.fromisoformat(r["entry_time"]).replace(tzinfo=None)
                xt = datetime.fromisoformat(r["exit_time"]).replace(tzinfo=None)
                rates = mt5.copy_rates_range(b["symbol"], mt5.TIMEFRAME_M5, et - timedelta(hours=4), xt + timedelta(hours=2))
                if rates is None or len(rates) == 0:
                    continue
                candles = [{"t": int(x["time"]), "o": float(x["open"]), "h": float(x["high"]),
                            "l": float(x["low"]), "c": float(x["close"])} for x in rates]
                cbatch.append({"ticket": r["ticket"], "bot_id": b["id"], "account": live_acct, "candles": candles})
            if cbatch:
                SB.table("trade_candles").upsert(cbatch, on_conflict="ticket").execute()
                print(f"[{b['id']}] velas guardadas para {len(cbatch)} trades", flush=True)

        # vista "En vivo": sesión actual + zonas (una vez por símbolo por ciclo)
        if b["symbol"] in LIVE_VIEW and b["symbol"] not in SESSION_DONE:
            try:
                push_session_view(b["symbol"])
                SESSION_DONE.add(b["symbol"])
            except Exception as e:
                print(f"[{b['id']}] session_view error: {e}", flush=True)
    finally:
        mt5.shutdown()


def main():
    print("Colector Panel de Trading iniciado.", flush=True)
    upsert_bots()
    while True:
        SESSION_DONE.clear()   # reset de la vista en vivo por ciclo
        for b in CFG["bots"]:
            try:
                collect_bot(b)
            except Exception as e:
                print(f"[{b['id']}] error: {e}", flush=True)
            time.sleep(1)
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
