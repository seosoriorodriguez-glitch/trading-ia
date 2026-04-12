# -*- coding: utf-8 -*-
"""
Backtester Opening Range Breakout (ORB) — US30 M5.

Logica exacta del indicador LuxAlgo ORB:
  1. Primeros N minutos de sesion NY -> definir ORH y ORL
  2. Despues del rango: si vela M5 cierra sobre ORH -> LONG
                        si vela M5 cierra bajo ORL  -> SHORT
  3. SL: extremo opuesto del rango - buffer
  4. TP: entry +/- risk * target_rr
  5. Max 1 trade por sesion (el primer breakout valido)
  6. Trade se cancela al fin de sesion si no se ejecuto
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional
import pandas as pd


@dataclass
class Trade:
    trade_id:    int
    direction:   str
    entry_price: float
    sl:          float
    tp:          float
    entry_time:  datetime
    exit_price:  float = 0.0
    exit_time:   Optional[datetime] = None
    exit_reason: str = ""
    pnl_usd:     float = 0.0
    pnl_r:       float = 0.0
    orh:         float = 0.0
    orl:         float = 0.0
    or_range:    float = 0.0


class ORBBacktester:

    def __init__(self, params: dict):
        self.params  = params
        self.balance = params["initial_balance"]
        self.initial_balance = params["initial_balance"]
        self._trades: List[Trade] = []
        self._trade_counter = 0

    def _session_start_dt(self, dt: datetime) -> datetime:
        h, m = self.params["session_start"].split(":")
        return dt.replace(hour=int(h), minute=int(m), second=0, microsecond=0)

    def _session_end_dt(self, dt: datetime) -> datetime:
        h, m = self.params["session_end"].split(":")
        return dt.replace(hour=int(h), minute=int(m), second=0, microsecond=0)

    def _or_end_dt(self, dt: datetime) -> datetime:
        sess_start = self._session_start_dt(dt)
        return sess_start + timedelta(minutes=self.params["or_duration_minutes"])

    def run(self, df: pd.DataFrame) -> pd.DataFrame:
        """Ejecuta el backtest sobre datos M5."""

        rows = df.to_dict("records")
        n = len(rows)

        # Estado por sesion
        orh = None
        orl = None
        or_defined = False
        trade_taken_today = False
        active_trade: Optional[Trade] = None
        daily_pnl = 0.0
        current_date = None

        for i, row in enumerate(rows):
            t = row["time"]
            if isinstance(t, str):
                t = pd.Timestamp(t)

            # Reset diario
            if current_date is None or t.date() != current_date:
                # Cerrar trade abierto al fin del dia anterior
                if active_trade is not None:
                    self._close_trade(active_trade, row["open"], t, "end_of_session")
                    active_trade = None

                current_date = t.date()
                orh = None
                orl = None
                or_defined = False
                trade_taken_today = False
                daily_pnl = 0.0

            # Solo operar lunes-viernes
            if t.weekday() >= 5:
                continue

            sess_start = self._session_start_dt(t)
            sess_end   = self._session_end_dt(t)
            or_end     = self._or_end_dt(t)

            # Fuera de sesion
            if t < sess_start or t >= sess_end:
                # Cerrar trade al fin de sesion
                if active_trade is not None and t >= sess_end:
                    self._close_trade(active_trade, row["open"], t, "end_of_session")
                    active_trade = None
                continue

            # Dentro de la ventana del rango de apertura
            if t < or_end:
                if orh is None:
                    orh = row["high"]
                    orl = row["low"]
                else:
                    if row["high"] > orh:
                        orh = row["high"]
                    if row["low"] < orl:
                        orl = row["low"]
                continue

            # Rango definido — primera vela post-OR
            if not or_defined:
                if orh is None or orl is None:
                    continue
                or_defined = True
                or_range = orh - orl

                # Validar rango
                if or_range < self.params["min_range_points"] or or_range > self.params["max_range_points"]:
                    trade_taken_today = True  # skip este dia
                    continue

            # Monitorear trade activo
            if active_trade is not None:
                # Check SL
                if active_trade.direction == "long":
                    if row["low"] <= active_trade.sl:
                        self._close_trade(active_trade, active_trade.sl, t, "sl")
                        active_trade = None
                        continue
                    if row["high"] >= active_trade.tp:
                        self._close_trade(active_trade, active_trade.tp, t, "tp")
                        active_trade = None
                        continue
                else:
                    if row["high"] >= active_trade.sl:
                        self._close_trade(active_trade, active_trade.sl, t, "sl")
                        active_trade = None
                        continue
                    if row["low"] <= active_trade.tp:
                        self._close_trade(active_trade, active_trade.tp, t, "tp")
                        active_trade = None
                        continue
                continue

            # Buscar señal de breakout (solo 1 por sesion)
            if trade_taken_today:
                continue

            # FTMO daily check
            ftmo_limit = self.initial_balance * self.params["ftmo_daily_loss_pct"] / 100
            if daily_pnl <= -ftmo_limit:
                continue

            candle_close = row["close"]
            buf = self.params["buffer_points"]
            slip = self.params["slippage_points"]
            spread = self.params["avg_spread_points"]
            rr = self.params["target_rr"]
            or_range = orh - orl

            direction = None
            if candle_close > orh:
                direction = "long"
            elif candle_close < orl:
                direction = "short"

            if direction is None:
                continue

            # Calcular SL/TP
            if direction == "long":
                entry = candle_close + spread + slip
                sl    = orl - buf
                risk  = abs(entry - sl)
                tp    = entry + risk * rr
            else:
                entry = candle_close - spread - slip
                sl    = orh + buf
                risk  = abs(sl - entry)
                tp    = entry - risk * rr

            if risk <= 0:
                continue

            # Position sizing
            risk_usd = self.initial_balance * self.params["risk_per_trade_pct"]
            lots     = risk_usd / risk

            self._trade_counter += 1
            trade = Trade(
                trade_id    = self._trade_counter,
                direction   = direction,
                entry_price = entry,
                sl          = sl,
                tp          = tp,
                entry_time  = t,
                orh         = orh,
                orl         = orl,
                or_range    = or_range,
            )
            active_trade = trade
            trade_taken_today = True

        # Cerrar ultimo trade abierto
        if active_trade is not None and rows:
            last = rows[-1]
            self._close_trade(active_trade, last["close"], last["time"], "end_of_data")

        return self._build_df()

    def _close_trade(self, trade: Trade, exit_price: float, exit_time, reason: str):
        slip = self.params.get("slippage_points", 0)
        if reason == "sl":
            effective_exit = exit_price - slip if trade.direction == "long" else exit_price + slip
        else:
            effective_exit = exit_price

        if trade.direction == "long":
            pnl_pts = effective_exit - trade.entry_price
        else:
            pnl_pts = trade.entry_price - effective_exit

        risk_pts = abs(trade.entry_price - trade.sl)
        risk_usd = self.initial_balance * self.params["risk_per_trade_pct"]
        pnl_usd  = (pnl_pts / risk_pts) * risk_usd if risk_pts > 0 else 0
        pnl_r    = pnl_pts / risk_pts if risk_pts > 0 else 0

        trade.exit_price  = effective_exit
        trade.exit_time   = exit_time
        trade.exit_reason = reason
        trade.pnl_usd     = round(pnl_usd, 2)
        trade.pnl_r       = round(pnl_r, 3)

        self.balance += pnl_usd
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
                "orh":         t.orh,
                "orl":         t.orl,
                "or_range":    round(t.or_range, 1),
            })
        return pd.DataFrame(records)
