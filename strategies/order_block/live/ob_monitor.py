# -*- coding: utf-8 -*-
"""
Live OB Monitor - Deteccion de Order Blocks y generacion de senales en tiempo real.

Flujo:
  - Cada vela M5 cerrada: re-detecta OBs sobre las ultimas 300 velas M5,
    aplica expiry/destruccion y actualiza la lista activa.
  - Cada vela M1 cerrada: verifica si hay senal de entrada en algun OB activo.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import bisect
import pandas as pd
from datetime import datetime, timezone
from typing import List, Optional, Set, Tuple

from strategies.order_block.backtest.ob_detection import (
    OrderBlock, OBStatus, detect_order_blocks,
)
from strategies.order_block.backtest.signals import Signal, check_entry


# Numero de velas M5 a descargar para deteccion + contexto de expiry
_M5_HISTORY = 350
# Numero de velas M1 a mantener para el filtro BOS
_M1_HISTORY  = 60


def _ob_key(ob: OrderBlock) -> Tuple:
    """Clave unica para identificar un OB."""
    return (ob.ob_type, round(ob.zone_high, 2), round(ob.zone_low, 2), ob.confirmed_at)


class LiveOBMonitor:
    """Monitor de OBs y senales en tiempo real."""

    def __init__(self, params: dict, data_feed):
        self.params      = params
        self.data_feed   = data_feed
        self.active_obs: List[OrderBlock] = []
        self.mitigated_keys: Set[Tuple]   = set()   # OBs ya usados (no re-entrar)
        self.trend_bias: Optional[str]    = None     # "long", "short" o None
        self.recent_m1:  List[dict]       = []       # ventana de velas M1 para BOS
        self.last_ob_update: Optional[datetime] = None

    # ------------------------------------------------------------------
    # Actualizacion de OBs (llamar cada vez que cierra una vela M5)
    # ------------------------------------------------------------------

    def update_obs(self) -> int:
        """
        Descarga datos M5, re-detecta OBs, aplica expiry/destruccion
        y actualiza `self.active_obs`.

        Retorna numero de OBs activos (FRESH).
        """
        df_m5 = self.data_feed.get_latest_candles("M5", _M5_HISTORY)
        if df_m5 is None or len(df_m5) < 20:
            return len(self.active_obs)

        now = df_m5.iloc[-1]["time"]
        if isinstance(now, pd.Timestamp):
            now = now.to_pydatetime()

        # Re-detectar todos los OBs en la ventana historica
        all_obs = detect_order_blocks(df_m5, self.params)

        # Filtrar OBs activos
        self.active_obs = self._build_active_obs(all_obs, df_m5, now)

        # Actualizar trend bias EMA 4H
        self.trend_bias = self._compute_trend_bias(df_m5)

        self.last_ob_update = now
        return len(self.active_obs)

    def _build_active_obs(
        self,
        all_obs:   List[OrderBlock],
        df_m5:     pd.DataFrame,
        now:       datetime,
    ) -> List[OrderBlock]:
        """Filtra la lista de OBs aplicando confirmed_at, mitigados, destruccion y expiry."""
        m5_times  = df_m5["time"].tolist()
        m5_closes = df_m5["close"].tolist()
        n_m5      = len(m5_times)
        expiry    = self.params["expiry_candles"]

        active = []
        for ob in all_obs:
            # Anti-lookahead: solo OBs ya confirmados
            ob_conf = ob.confirmed_at
            if isinstance(ob_conf, pd.Timestamp):
                ob_conf = ob_conf.to_pydatetime()
            if ob_conf > now:
                continue

            # Saltar OBs ya mitigados
            if _ob_key(ob) in self.mitigated_keys:
                continue

            # Buscar indice de la primera vela M5 >= confirmed_at
            idx_start = bisect.bisect_left(m5_times, ob_conf)
            if idx_start >= n_m5:
                continue

            # Verificar destruccion y expiry sobre velas posteriores a confirmed_at
            alive = True
            candles_since = 0
            for j in range(idx_start, n_m5):
                c = m5_closes[j]
                if ob.ob_type == "bullish" and c < ob.zone_low:
                    alive = False
                    break
                if ob.ob_type == "bearish" and c > ob.zone_high:
                    alive = False
                    break
                candles_since += 1
                if candles_since >= expiry:
                    alive = False
                    break

            if alive:
                ob.status = OBStatus.FRESH
                active.append(ob)

        # Limitar a max_active_obs mas recientes
        max_active = self.params["max_active_obs"]
        if len(active) > max_active:
            active = sorted(active, key=lambda o: o.confirmed_at)[-max_active:]

        return active

    def _compute_trend_bias(self, df_m5: pd.DataFrame) -> Optional[str]:
        """Calcula bias de tendencia via EMA(period) sobre velas de 4H resampleadas desde M5."""
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

        # Usar la penultima vela 4H (la ultima puede ser parcial)
        ema_val = float(df_4h["ema"].iloc[-2])
        current_close = float(df_m5.iloc[-1]["close"])

        return "long" if current_close > ema_val else "short"

    # ------------------------------------------------------------------
    # Verificacion de senal (llamar cada vez que cierra una vela M1)
    # ------------------------------------------------------------------

    def check_for_signal(self, balance: float) -> Optional[Signal]:
        """
        Descarga las ultimas M1 cerradas, verifica si alguna toca un OB activo
        y retorna una Signal si todos los filtros pasan.
        """
        bos_lb = self.params.get("bos_lookback", 20)
        needed = bos_lb + 3

        df_m1 = self.data_feed.get_latest_candles("M1", needed)
        if df_m1 is None or len(df_m1) < 3:
            return None

        # La ultima fila puede ser la vela en formacion; usamos [-2] como "ultima cerrada"
        candle      = df_m1.iloc[-2].to_dict()
        prev_candle = df_m1.iloc[-3].to_dict()

        # Ventana de velas M1 cerradas para BOS (excluye la actual)
        recent_candles = [
            df_m1.iloc[i].to_dict()
            for i in range(max(0, len(df_m1) - bos_lb - 2), len(df_m1) - 2)
        ]

        # Convertir timestamp si es necesario
        if isinstance(candle["time"], pd.Timestamp):
            candle["time"] = candle["time"].to_pydatetime()

        signal = check_entry(
            candle         = candle,
            prev_candle    = prev_candle,
            recent_candles = recent_candles,
            active_obs     = self.active_obs,
            n_open_trades  = 0,   # gestionado externamente (trading_bot lo controla)
            params         = self.params,
            balance        = balance,
            trend_bias     = self.trend_bias,
        )

        return signal

    def mark_mitigated(self, ob: OrderBlock):
        """Marca un OB como usado para no generar nuevas entradas sobre el mismo nivel."""
        self.mitigated_keys.add(_ob_key(ob))
        ob.status = OBStatus.MITIGATED
        if ob in self.active_obs:
            self.active_obs.remove(ob)

    def get_summary(self) -> dict:
        bull = sum(1 for o in self.active_obs if o.ob_type == "bullish")
        bear = sum(1 for o in self.active_obs if o.ob_type == "bearish")
        return {
            "total":       len(self.active_obs),
            "bullish":     bull,
            "bearish":     bear,
            "trend_bias":  self.trend_bias,
            "last_update": self.last_ob_update,
        }
