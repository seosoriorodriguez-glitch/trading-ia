# -*- coding: utf-8 -*-
"""
Backtester Breaker Block — US30 M5/M1.

Flujo:
  1. Detectar BBs en M5 (bb_detection.py)
     - BBs ya tienen bb_type="long" o "short" (direccion de entrada)
     - destroyed_at = momento en que el OB fue destruido (nace el BB)

  2. Loop sobre M1:
     - Activar BBs cuyo destroyed_at <= tiempo M1 actual
     - Destruir BBs si precio cierra al otro lado de zone_low/zone_high
     - Expirar BBs por velas sin toque
     - Trigger: vela M1 cierra DENTRO del BB → STOP order en borde
       * bb_type="long"  → stop BUY  en zone_high + spread + slip
       * bb_type="short" → stop SELL en zone_low  - spread - slip
     - Fill: precio alcanza el borde → trade abierto
     - Exit: SL o TP
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional, Tuple
import pandas as pd

from .bb_detection import BreakerBlock, BBStatus, detect_breaker_blocks
from strategies.fair_value_gap.backtest.risk_manager import is_session_allowed


def _bb_key(bb: BreakerBlock) -> Tuple:
    return (bb.bb_type, round(bb.zone_high, 2), round(bb.zone_low, 2), bb.destroyed_at)


@dataclass
class PendingStop:
    direction:    str
    entry_price:  float
    sl:           float
    tp:           float
    bb:           BreakerBlock
    trigger_time: datetime
    session:      str
    risk_pts:     float


@dataclass
class Trade:
    trade_id:    int
    direction:   str
    entry_price: float
    sl:          float
    tp:          float
    entry_time:  datetime
    session:     str
    bb_high:     float
    bb_low:      float
    exit_price:  float = 0.0
    exit_time:   Optional[datetime] = None
    exit_reason: str = ""
    pnl_usd:     float = 0.0
    pnl_r:       float = 0.0


class BBBacktester:

    def __init__(self, params: dict):
        self.params          = params
        self.balance         = params["initial_balance"]
        self.initial_balance = params["initial_balance"]
        self._trades: List[Trade] = []
        self._trade_counter = 0

    def run(self, df_m5: pd.DataFrame, df_m1: pd.DataFrame) -> pd.DataFrame:

        # 1. Detectar BBs en M5
        print(f"   Detectando Breaker Blocks en M5...", flush=True)
        all_bbs = detect_breaker_blocks(df_m5, self.params)
        long_bbs  = sum(1 for b in all_bbs if b.bb_type == "long")
        short_bbs = sum(1 for b in all_bbs if b.bb_type == "short")
        print(f"   BBs detectados: {len(all_bbs)} ({long_bbs} long / {short_bbs} short)", flush=True)

        if not all_bbs:
            return pd.DataFrame()

        params       = self.params
        max_active   = params["max_active_bbs"]
        expiry_c     = params["expiry_candles"]
        buf          = params["buffer_points"]
        min_risk     = params["min_risk_points"]
        max_risk     = params["max_risk_points"]
        rr           = params["target_rr"]
        spread       = params["avg_spread_points"]
        slip         = params["slippage_points"]
        max_sim      = params["max_simultaneous_trades"]
        risk_usd     = self.initial_balance * params["risk_per_trade_pct"]
        ftmo_limit   = self.initial_balance * params["ftmo_daily_loss_pct"] / 100

        # Estado
        active_bbs:     List[BreakerBlock] = []
        bb_candle_count = {}
        active_trades:  List[Trade]       = []
        pending_stops:  List[PendingStop] = []

        # FTMO diario
        daily_pnl    = 0.0
        current_date = None

        m5_rows  = df_m5.to_dict("records")
        m5_times = [pd.Timestamp(r["time"]) for r in m5_rows]
        m5_ptr   = 0
        n_m5     = len(m5_rows)

        # Ordenar BBs por destroyed_at para usar puntero eficiente
        sorted_bbs = sorted(all_bbs, key=lambda b: b.destroyed_at)
        bb_ptr = 0
        n_bbs  = len(sorted_bbs)

        m1_rows = df_m1.to_dict("records")

        for m1_row in m1_rows:
            t        = pd.Timestamp(m1_row["time"])
            m1_high  = m1_row["high"]
            m1_low   = m1_row["low"]
            m1_close = m1_row["close"]

            # Reset diario FTMO
            if current_date is None or t.date() != current_date:
                current_date = t.date()
                daily_pnl    = 0.0

            # 1. Avanzar puntero M5 — activar y gestionar BBs
            while m5_ptr < n_m5 and m5_times[m5_ptr] <= t:
                m5t      = m5_times[m5_ptr]
                m5_close = m5_rows[m5_ptr]["close"]

                # Activar BBs cuyo destroyed_at <= esta vela M5 (puntero ordenado)
                while bb_ptr < n_bbs and sorted_bbs[bb_ptr].destroyed_at <= m5t:
                    bb = sorted_bbs[bb_ptr]
                    if bb.status == BBStatus.FRESH:
                        active_bbs.append(bb)
                    bb_ptr += 1

                # Limitar max activos (los mas recientes)
                if len(active_bbs) > max_active:
                    active_bbs = sorted(active_bbs, key=lambda b: b.destroyed_at, reverse=True)[:max_active]

                # Destruir/expirar BBs
                for bb in list(active_bbs):
                    if bb.status != BBStatus.FRESH:
                        continue

                    # BROKEN: precio cierra al otro lado de la zona (igual que FVG/OB)
                    if bb.bb_type == "long" and m5_close < bb.zone_low:
                        bb.status = BBStatus.BROKEN
                        pending_stops = [p for p in pending_stops if p.bb is not bb]
                        continue
                    if bb.bb_type == "short" and m5_close > bb.zone_high:
                        bb.status = BBStatus.BROKEN
                        pending_stops = [p for p in pending_stops if p.bb is not bb]
                        continue

                    # Expiry por velas
                    oid = id(bb)
                    bb_candle_count[oid] = bb_candle_count.get(oid, 0) + 1
                    if bb_candle_count[oid] >= expiry_c:
                        bb.status = BBStatus.EXPIRED
                        pending_stops = [p for p in pending_stops if p.bb is not bb]

                m5_ptr += 1

            # 2. Monitorear trades activos (SL/TP)
            still_open = []
            for trade in active_trades:
                closed = False
                if trade.direction == "long":
                    if m1_low <= trade.sl:
                        self._close_trade(trade, trade.sl - slip, t, "sl")
                        daily_pnl += trade.pnl_usd
                        closed = True
                    elif m1_high >= trade.tp:
                        self._close_trade(trade, trade.tp, t, "tp")
                        daily_pnl += trade.pnl_usd
                        closed = True
                else:
                    if m1_high >= trade.sl:
                        self._close_trade(trade, trade.sl + slip, t, "sl")
                        daily_pnl += trade.pnl_usd
                        closed = True
                    elif m1_low <= trade.tp:
                        self._close_trade(trade, trade.tp, t, "tp")
                        daily_pnl += trade.pnl_usd
                        closed = True
                if not closed:
                    still_open.append(trade)
            active_trades = still_open

            # 3. Fill de STOP orders pendientes
            filled = []
            for ps in pending_stops:
                if ps.direction == "long" and m1_high >= ps.entry_price:
                    trade = self._open_trade(ps, t)
                    active_trades.append(trade)
                    ps.bb.status = BBStatus.MITIGATED
                    filled.append(ps)
                elif ps.direction == "short" and m1_low <= ps.entry_price:
                    trade = self._open_trade(ps, t)
                    active_trades.append(trade)
                    ps.bb.status = BBStatus.MITIGATED
                    filled.append(ps)
            for ps in filled:
                pending_stops.remove(ps)

            # 4. Buscar nuevo trigger
            if not is_session_allowed(t, params):
                continue
            if daily_pnl <= -ftmo_limit:
                continue
            if len(active_trades) + len(pending_stops) >= max_sim:
                continue

            # Keys de BBs ya en uso
            used_keys = {_bb_key(p.bb) for p in pending_stops}

            session = self._which_session(t)
            if session is None:
                continue

            fresh_bbs = sorted(
                [b for b in active_bbs if b.status == BBStatus.FRESH],
                key=lambda b: b.destroyed_at,
                reverse=True,
            )

            for bb in fresh_bbs:
                if _bb_key(bb) in used_keys:
                    continue

                # Trigger: vela M1 cierra DENTRO del BB
                if not (bb.zone_low <= m1_close <= bb.zone_high):
                    continue

                if bb.bb_type == "long":
                    direction   = "long"
                    entry_price = bb.zone_high + spread + slip
                    sl          = bb.zone_low - buf
                else:
                    direction   = "short"
                    entry_price = bb.zone_low - spread - slip
                    sl          = bb.zone_high + buf

                risk_pts = abs(entry_price - sl)
                if risk_pts < min_risk or risk_pts > max_risk:
                    continue

                if direction == "long":
                    tp = entry_price + risk_pts * rr
                else:
                    tp = entry_price - risk_pts * rr

                min_rr    = params.get("min_rr_ratio", 1.2)
                actual_rr = abs(tp - entry_price) / risk_pts if risk_pts > 0 else 0
                if actual_rr < min_rr:
                    continue

                ps = PendingStop(
                    direction    = direction,
                    entry_price  = entry_price,
                    sl           = sl,
                    tp           = tp,
                    bb           = bb,
                    trigger_time = t,
                    session      = session,
                    risk_pts     = risk_pts,
                )
                pending_stops.append(ps)
                break  # 1 orden por vela

        # Cerrar trades al final
        if m1_rows and active_trades:
            last = m1_rows[-1]
            for trade in active_trades:
                self._close_trade(trade, last["close"], last["time"], "end_of_data")

        return self._build_df()

    def _which_session(self, dt) -> Optional[str]:
        for name, sess in self.params["sessions"].items():
            h_s, m_s = sess["start"].split(":")
            h_e, m_e = sess["end"].split(":")
            sess_start = dt.replace(hour=int(h_s), minute=int(m_s), second=0, microsecond=0)
            sess_end   = dt.replace(hour=int(h_e), minute=int(m_e), second=0, microsecond=0)
            trade_from = sess_start + timedelta(minutes=sess["skip_minutes"])
            if trade_from <= dt < sess_end:
                return name
        return None

    def _open_trade(self, ps: PendingStop, entry_time) -> Trade:
        self._trade_counter += 1
        return Trade(
            trade_id    = self._trade_counter,
            direction   = ps.direction,
            entry_price = ps.entry_price,
            sl          = ps.sl,
            tp          = ps.tp,
            entry_time  = entry_time,
            session     = ps.session,
            bb_high     = ps.bb.zone_high,
            bb_low      = ps.bb.zone_low,
        )

    def _close_trade(self, trade: Trade, exit_price: float, exit_time, reason: str):
        risk_pts = abs(trade.entry_price - trade.sl)
        risk_usd = self.initial_balance * self.params["risk_per_trade_pct"]

        if trade.direction == "long":
            pnl_pts = exit_price - trade.entry_price
        else:
            pnl_pts = trade.entry_price - exit_price

        pnl_usd = (pnl_pts / risk_pts) * risk_usd if risk_pts > 0 else 0
        pnl_r   = pnl_pts / risk_pts if risk_pts > 0 else 0

        trade.exit_price  = exit_price
        trade.exit_time   = exit_time
        trade.exit_reason = reason
        trade.pnl_usd     = round(pnl_usd, 2)
        trade.pnl_r       = round(pnl_r, 3)
        self.balance     += pnl_usd
        self._trades.append(trade)

    def _build_df(self) -> pd.DataFrame:
        if not self._trades:
            return pd.DataFrame()
        records = []
        running = self.initial_balance
        for t in self._trades:
            running += t.pnl_usd
            records.append({
                "trade_id":    t.trade_id,
                "entry_time":  t.entry_time,
                "exit_time":   t.exit_time,
                "direction":   t.direction,
                "entry_price": t.entry_price,
                "sl":          t.sl,
                "tp":          t.tp,
                "exit_price":  t.exit_price,
                "exit_reason": t.exit_reason,
                "pnl_usd":     t.pnl_usd,
                "pnl_r":       t.pnl_r,
                "balance":     round(running, 2),
                "session":     t.session,
                "bb_high":     t.bb_high,
                "bb_low":      t.bb_low,
            })
        return pd.DataFrame(records)
