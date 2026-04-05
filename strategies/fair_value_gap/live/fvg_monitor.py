# -*- coding: utf-8 -*-
"""
Live FVG Monitor - Deteccion de Fair Value Gaps y generacion de senales en tiempo real.

Flujo:
  - Cada vela M5 cerrada: re-detecta FVGs sobre las ultimas 350 velas M5,
    aplica expiry/destruccion y actualiza la lista activa.
  - Cada vela M1 cerrada: verifica si hay trigger conservative en algun FVG activo.
    Si hay trigger, genera una PendingStop (orden stop en borde de la zona).

Entrada conservative (igual que backtest validado +291%):
  PASO 1 — Trigger: vela M1 cierra DENTRO del FVG.
  PASO 2 — Stop order: se coloca una orden stop en el BORDE de la zona:
           Bullish FVG (long):  stop BUY  en zone_high
           Bearish FVG (short): stop SELL en zone_low
  PASO 3 — Fill: MT5 ejecuta la orden cuando el precio alcanza ese borde.
  Si el FVG expira o se destruye antes del fill -> orden cancelada por trading_bot.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import bisect
import pandas as pd
from datetime import datetime, timezone
from typing import List, Optional, Set, Tuple

from strategies.fair_value_gap.backtest.fvg_detection import (
    FairValueGap, FVGStatus, detect_fvgs,
)
from strategies.fair_value_gap.backtest.signals import (
    Signal, PendingStop, check_conservative_trigger, check_bos,
)
from strategies.fair_value_gap.backtest.risk_manager import is_session_allowed

_M5_HISTORY = 350
_M1_HISTORY = 60


def _fvg_key(fvg: FairValueGap) -> Tuple:
    """Clave unica para identificar un FVG."""
    return (fvg.fvg_type, round(fvg.zone_high, 2), round(fvg.zone_low, 2), fvg.confirmed_at)


class LiveFVGMonitor:
    """Monitor de FVGs y senales en tiempo real."""

    def __init__(self, params: dict, data_feed):
        self.params      = params
        self.data_feed   = data_feed
        self.active_fvgs: List[FairValueGap] = []
        self.mitigated_keys: Set[Tuple]       = set()
        self.trend_bias: Optional[str]        = None
        self.last_fvg_update: Optional[datetime] = None

    # ------------------------------------------------------------------
    # Actualizacion de FVGs (llamar cada vez que cierra una vela M5)
    # ------------------------------------------------------------------

    def update_fvgs(self) -> int:
        """
        Descarga datos M5, re-detecta FVGs, aplica expiry/destruccion
        y actualiza self.active_fvgs.
        Retorna numero de FVGs activos (FRESH).
        """
        df_m5 = self.data_feed.get_latest_candles("M5", _M5_HISTORY)
        if df_m5 is None or len(df_m5) < 20:
            return len(self.active_fvgs)

        now = df_m5.iloc[-1]["time"]
        if isinstance(now, pd.Timestamp):
            now = now.to_pydatetime()

        all_fvgs = detect_fvgs(df_m5, self.params)
        self.active_fvgs = self._build_active_fvgs(all_fvgs, df_m5, now)
        self.trend_bias = self._compute_trend_bias(df_m5)

        self.last_fvg_update = now
        return len(self.active_fvgs)

    def _build_active_fvgs(
        self,
        all_fvgs: List[FairValueGap],
        df_m5:    pd.DataFrame,
        now:      datetime,
    ) -> List[FairValueGap]:
        """Filtra FVGs aplicando confirmed_at, mitigados, destruccion y expiry."""
        m5_times  = df_m5["time"].tolist()
        m5_closes = df_m5["close"].tolist()
        n_m5      = len(m5_times)
        expiry    = self.params["expiry_candles"]

        active = []
        for fvg in all_fvgs:
            fvg_conf = fvg.confirmed_at
            if isinstance(fvg_conf, pd.Timestamp):
                fvg_conf = fvg_conf.to_pydatetime()
            if fvg_conf > now:
                continue

            if _fvg_key(fvg) in self.mitigated_keys:
                continue

            idx_start = bisect.bisect_left(m5_times, fvg_conf)
            if idx_start >= n_m5:
                continue

            alive = True
            candles_since = 0
            for j in range(idx_start, n_m5):
                c = m5_closes[j]
                # Destruccion: precio cierra al otro lado del gap
                if fvg.fvg_type == "bullish" and c < fvg.zone_low:
                    alive = False
                    break
                if fvg.fvg_type == "bearish" and c > fvg.zone_high:
                    alive = False
                    break
                candles_since += 1
                if candles_since >= expiry:
                    alive = False
                    break

            if alive:
                fvg.status = FVGStatus.FRESH
                active.append(fvg)

        max_active = self.params["max_active_fvgs"]
        if len(active) > max_active:
            active = sorted(active, key=lambda f: f.confirmed_at)[-max_active:]

        return active

    def _compute_trend_bias(self, df_m5: pd.DataFrame) -> Optional[str]:
        """Calcula bias de tendencia via EMA sobre 4H resampleadas desde M5."""
        if not self.params.get("ema_trend_filter", False):
            return None

        ema_period = self.params.get("ema_4h_period", 20)
        df_4h = (
            df_m5.set_index("time")
            .resample("4h", label="left", closed="left")
            .agg({"open": "first", "high": "max", "low": "min", "close": "last"})
            .dropna()
        )
        if len(df_4h) < ema_period + 2:
            return None

        df_4h["ema"] = df_4h["close"].ewm(span=ema_period, adjust=False).mean()
        ema_val = float(df_4h["ema"].iloc[-2])
        current_close = float(df_m5.iloc[-1]["close"])

        return "long" if current_close > ema_val else "short"

    # ------------------------------------------------------------------
    # Verificacion de senal (llamar cada vez que cierra una vela M1)
    # ------------------------------------------------------------------

    def check_for_trigger(self, balance: float, skip_fvg_keys: set = None) -> Optional[PendingStop]:
        """
        Descarga las ultimas velas M1, verifica si alguna cierra dentro
        de un FVG activo (trigger conservative) y retorna un PendingStop.
        El trading_bot convierte el PendingStop en una orden STOP real en MT5.
        """
        if skip_fvg_keys is None:
            skip_fvg_keys = set()

        bos_lb = self.params.get("bos_lookback", 20)
        needed = bos_lb + 5

        df_m1 = self.data_feed.get_latest_candles("M1", needed)
        if df_m1 is None or len(df_m1) < 3:
            return None

        candle = df_m1.iloc[-2].to_dict()
        prev_candle = df_m1.iloc[-3].to_dict() if len(df_m1) >= 3 else None

        recent_candles = [
            df_m1.iloc[i].to_dict()
            for i in range(max(0, len(df_m1) - bos_lb - 2), len(df_m1) - 2)
        ]

        if isinstance(candle["time"], pd.Timestamp):
            candle["time"] = candle["time"].to_pydatetime()
        if prev_candle and isinstance(prev_candle["time"], pd.Timestamp):
            prev_candle["time"] = prev_candle["time"].to_pydatetime()

        # Filtrar FVGs que ya tienen orden pendiente
        eligible_fvgs = [
            fvg for fvg in self.active_fvgs
            if fvg.status == FVGStatus.FRESH and _fvg_key(fvg) not in skip_fvg_keys
        ]

        if not eligible_fvgs:
            return None

        pending = check_conservative_trigger(
            candle         = candle,
            prev_candle    = prev_candle,
            recent_candles = recent_candles,
            active_fvgs    = eligible_fvgs,
            params         = self.params,
            trend_bias     = self.trend_bias,
        )

        return pending

    def mark_mitigated(self, fvg: FairValueGap):
        """Marca un FVG como usado para no generar nuevas entradas sobre el mismo nivel."""
        self.mitigated_keys.add(_fvg_key(fvg))
        fvg.status = FVGStatus.MITIGATED
        if fvg in self.active_fvgs:
            self.active_fvgs.remove(fvg)

    def get_summary(self) -> dict:
        bull = sum(1 for f in self.active_fvgs if f.fvg_type == "bullish")
        bear = sum(1 for f in self.active_fvgs if f.fvg_type == "bearish")
        return {
            "total":       len(self.active_fvgs),
            "bullish":     bull,
            "bearish":     bear,
            "trend_bias":  self.trend_bias,
            "last_update": self.last_fvg_update,
        }
