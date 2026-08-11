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


def session_of(hour_server: int) -> str:
    if 10 <= hour_server < 13:   return "london"
    if 13 <= hour_server < 17:   return "london_ny"
    if 17 <= hour_server < 23:   return "new_york"
    return "off"


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

        # historial de deals de la ventana
        now = datetime.now(timezone.utc)
        deals = mt5.history_deals_get(now - timedelta(days=LOOKBACK_DAYS), now + timedelta(minutes=5))
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
    finally:
        mt5.shutdown()


def main():
    print("Colector Panel de Trading iniciado.", flush=True)
    upsert_bots()
    while True:
        for b in CFG["bots"]:
            try:
                collect_bot(b)
            except Exception as e:
                print(f"[{b['id']}] error: {e}", flush=True)
            time.sleep(1)
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
