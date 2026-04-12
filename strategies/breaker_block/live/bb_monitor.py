# -*- coding: utf-8 -*-
"""
Live BB Monitor - Deteccion de Breaker Blocks y generacion de senales en tiempo real.

Flujo:
  - Cada vela M5 cerrada: re-detecta BBs sobre las ultimas 350 velas M5,
    filtra los que ya fueron mitigados/rotos/expirados y actualiza la lista activa.
  - Cada vela M1 cerrada: verifica si hay senal de entrada en algun BB activo.

Logica BB:
  1. OB bullish destruido (M5 cierra bajo zone_low) → BB short
  2. OB bearish destruido (M5 cierra sobre zone_high) → BB long
  3. BB se invalida (broken) si precio cierra al otro lado de zone_low/zone_high
  4. Trigger: vela M1 cerrada DENTRO de la zona → STOP order en el borde
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import bisect
import pandas as pd
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional, Set, Tuple

from strategies.breaker_block.backtest.bb_detection import (
    BreakerBlock, BBStatus, detect_breaker_blocks,
)
from strategies.order_block.backtest.risk_manager import is_session_allowed

_M5_HISTORY = 350
_M1_HISTORY  = 5


def _bb_key(bb: BreakerBlock) -> Tuple:
    return (bb.bb_type, round(bb.zone_high, 2), round(bb.zone_low, 2), bb.destroyed_at)


@dataclass
class BBSignal:
    direction:    str
    entry_price:  float
    sl:           float
    tp:           float
    bb:           BreakerBlock
    candle_time:  datetime
    session:      str


class LiveBBMonitor:
    """Monitor de Breaker Blocks y senales en tiempo real."""

    def __init__(self, params: dict, data_feed):
        self.params          = params
        self.data_feed       = data_feed
        self.active_bbs: List[BreakerBlock] = []
        self.mitigated_keys: Set[Tuple]     = set()
        self.last_bb_update: Optional[datetime] = None

    def update_bbs(self) -> int:
        df_m5 = self.data_feed.get_latest_candles("M5", _M5_HISTORY)
        if df_m5 is None or len(df_m5) < 20:
            return len(self.active_bbs)

        # Excluir la ultima fila: es la vela M5 actualmente abierta (no cerrada).
        # detect_breaker_blocks necesita solo velas cerradas para que zone_high/zone_low
        # y destroyed_at sean definitivos.
        df_m5 = df_m5.iloc[:-1].reset_index(drop=True)

        now = df_m5.iloc[-1]["time"]
        if isinstance(now, pd.Timestamp):
            now = now.to_pydatetime()

        all_bbs = detect_breaker_blocks(df_m5, self.params)
        self.active_bbs = self._build_active_bbs(all_bbs, df_m5, now)
        self.last_bb_update = now
        return len(self.active_bbs)

    def _build_active_bbs(self, all_bbs: List[BreakerBlock], df_m5, now) -> List[BreakerBlock]:
        m5_times  = df_m5["time"].tolist()
        m5_closes = df_m5["close"].tolist()
        expiry    = self.params["expiry_candles"]
        max_active = self.params["max_active_bbs"]

        active = []
        for bb in all_bbs:
            destroyed = bb.destroyed_at
            if isinstance(destroyed, pd.Timestamp):
                destroyed = destroyed.to_pydatetime()

            # Solo BBs ya formados
            if destroyed > now:
                continue

            # Ignorar ya mitigados
            if _bb_key(bb) in self.mitigated_keys:
                continue

            # Verificar si sigue vivo desde destroyed_at
            idx_start = bisect.bisect_left(m5_times, destroyed)
            if idx_start >= len(m5_times):
                continue

            alive = True
            candles_since = 0

            for j in range(idx_start, len(m5_times)):
                c = m5_closes[j]
                # BROKEN: precio cierra al otro lado de la zona (igual que FVG/OB)
                if bb.bb_type == "long" and c < bb.zone_low:
                    alive = False
                    break
                if bb.bb_type == "short" and c > bb.zone_high:
                    alive = False
                    break
                candles_since += 1
                if candles_since >= expiry:
                    alive = False
                    break

            if alive:
                bb.status = BBStatus.FRESH
                active.append(bb)

        # Mantener los mas recientes
        if len(active) > max_active:
            active = sorted(active, key=lambda b: b.destroyed_at)[-max_active:]

        return active

    def check_for_signal(self, skip_bb_keys: set = None) -> Optional[BBSignal]:
        if skip_bb_keys is None:
            skip_bb_keys = set()

        df_m1 = self.data_feed.get_latest_candles("M1", _M1_HISTORY)
        if df_m1 is None or len(df_m1) < 2:
            return None

        # Ultima vela M1 cerrada (penultima del array)
        candle = df_m1.iloc[-2].to_dict()
        if isinstance(candle["time"], pd.Timestamp):
            candle["time"] = candle["time"].to_pydatetime()

        candle_time  = candle["time"]
        candle_close = candle["close"]

        if not is_session_allowed(candle_time, self.params):
            return None

        # Ordenar BBs por los mas recientes primero
        candidates = sorted(
            [bb for bb in self.active_bbs if bb.status == BBStatus.FRESH],
            key=lambda b: b.destroyed_at,
            reverse=True,
        )

        for bb in candidates:
            if _bb_key(bb) in skip_bb_keys:
                continue

            # Trigger: vela M1 cierra DENTRO de la zona del BB
            if not (bb.zone_low <= candle_close <= bb.zone_high):
                continue

            # Calcular SL/TP
            sl, tp = self._calculate_sl_tp(bb)
            if sl is None:
                continue

            if bb.bb_type == "long":
                entry_price = bb.zone_high + self.params["avg_spread_points"] + self.params["slippage_points"]
            else:
                entry_price = bb.zone_low - self.params["avg_spread_points"] - self.params["slippage_points"]

            return BBSignal(
                direction   = bb.bb_type,
                entry_price = entry_price,
                sl          = sl,
                tp          = tp,
                bb          = bb,
                candle_time = candle_time,
                session     = self._which_session(candle_time),
            )

        return None

    def _calculate_sl_tp(self, bb: BreakerBlock):
        buf      = self.params["buffer_points"]
        min_risk = self.params["min_risk_points"]
        max_risk = self.params["max_risk_points"]
        rr       = self.params["target_rr"]
        min_rr   = self.params.get("min_rr_ratio", 1.2)
        spread   = self.params["avg_spread_points"]
        slip     = self.params["slippage_points"]

        if bb.bb_type == "long":
            entry_price = bb.zone_high + spread + slip
            sl          = bb.zone_low - buf
            risk_pts    = abs(entry_price - sl)
            tp          = entry_price + risk_pts * rr
        else:
            entry_price = bb.zone_low - spread - slip
            sl          = bb.zone_high + buf
            risk_pts    = abs(entry_price - sl)
            tp          = entry_price - risk_pts * rr

        if risk_pts < min_risk or risk_pts > max_risk:
            return None, None

        actual_rr = abs(tp - entry_price) / risk_pts if risk_pts > 0 else 0
        if actual_rr < min_rr:
            return None, None

        return sl, tp

    def _which_session(self, dt) -> str:
        from datetime import timedelta
        for name, sess in self.params["sessions"].items():
            h_s, m_s = sess["start"].split(":")
            h_e, m_e = sess["end"].split(":")
            sess_start = dt.replace(hour=int(h_s), minute=int(m_s), second=0, microsecond=0)
            sess_end   = dt.replace(hour=int(h_e), minute=int(m_e), second=0, microsecond=0)
            trade_from = sess_start + timedelta(minutes=sess["skip_minutes"])
            if trade_from <= dt < sess_end:
                return name
        return "unknown"

    def mark_mitigated(self, bb: BreakerBlock):
        self.mitigated_keys.add(_bb_key(bb))
        bb.status = BBStatus.MITIGATED
        if bb in self.active_bbs:
            self.active_bbs.remove(bb)

    def get_summary(self) -> dict:
        long_bbs  = sum(1 for b in self.active_bbs if b.bb_type == "long")
        short_bbs = sum(1 for b in self.active_bbs if b.bb_type == "short")
        return {
            "total":       len(self.active_bbs),
            "long":        long_bbs,
            "short":       short_bbs,
            "last_update": self.last_bb_update,
        }
