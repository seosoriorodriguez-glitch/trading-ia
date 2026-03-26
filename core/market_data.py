"""
Módulo de datos de mercado para Windows.
Conecta a MetaTrader 5 usando la librería oficial de MetaQuotes.
Para backtesting, puede trabajar con datos históricos en CSV/DataFrame.

Plataforma: Windows
Librería: MetaTrader5 (pip install MetaTrader5)
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

import pandas as pd
import MetaTrader5 as mt5

logger = logging.getLogger(__name__)


@dataclass
class Candle:
    """Representa una vela OHLCV."""
    time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    timeframe: str

    @property
    def body_size(self) -> float:
        return abs(self.close - self.open)

    @property
    def range_size(self) -> float:
        return self.high - self.low

    @property
    def upper_wick(self) -> float:
        return self.high - max(self.open, self.close)

    @property
    def lower_wick(self) -> float:
        return min(self.open, self.close) - self.low

    @property
    def is_bullish(self) -> bool:
        return self.close > self.open

    @property
    def is_bearish(self) -> bool:
        return self.close < self.open

    @property
    def body_ratio(self) -> float:
        """Ratio del cuerpo respecto al rango total."""
        if self.range_size == 0:
            return 0
        return self.body_size / self.range_size

    @property
    def upper_wick_ratio(self) -> float:
        if self.range_size == 0:
            return 0
        return self.upper_wick / self.range_size

    @property
    def lower_wick_ratio(self) -> float:
        if self.range_size == 0:
            return 0
        return self.lower_wick / self.range_size


class MT5Connection:
    """
    Conexión a MetaTrader 5 en Windows.
    Usa la librería oficial de MetaQuotes (MetaTrader5).
    
    Requisitos:
    - Windows OS
    - MetaTrader 5 instalado y ejecutándose
    - pip install MetaTrader5
    """

    def __init__(self):
        self._connected = False

    def connect(self) -> bool:
        """
        Conecta a la terminal MT5 local.
        MT5 debe estar ejecutándose en el mismo sistema.
        """
        if not mt5.initialize():
            error = mt5.last_error()
            logger.error(f"MT5 initialize() falló: {error}")
            logger.error("Verifica que MetaTrader 5 esté instalado y ejecutándose")
            return False

        self._connected = True
        info = mt5.account_info()
        if info:
            logger.info(f"✅ Conectado a MT5 — Cuenta: {info.login}, "
                       f"Broker: {info.company}, Balance: ${info.balance:.2f}")
        else:
            logger.warning("Conectado a MT5 pero no hay cuenta activa")
        
        return True

    def disconnect(self):
        """Desconecta de MT5."""
        if self._connected:
            mt5.shutdown()
            self._connected = False
            logger.info("Desconectado de MT5")

    def is_connected(self) -> bool:
        return self._connected

    def _get_timeframe_const(self, tf: str):
        """Convierte string de timeframe a constante MT5."""
        tf_map = {
            "M1": mt5.TIMEFRAME_M1,
            "M5": mt5.TIMEFRAME_M5,
            "M15": mt5.TIMEFRAME_M15,
            "M30": mt5.TIMEFRAME_M30,
            "H1": mt5.TIMEFRAME_H1,
            "H4": mt5.TIMEFRAME_H4,
            "D1": mt5.TIMEFRAME_D1,
            "W1": mt5.TIMEFRAME_W1,
        }
        if tf not in tf_map:
            raise ValueError(f"Timeframe no válido: {tf}")
        return tf_map[tf]

    def get_candles(self, symbol: str, timeframe: str, count: int) -> List[Candle]:
        """
        Obtiene las últimas N velas de un símbolo.

        Args:
            symbol: Nombre del símbolo en MT5 (ej: "US30.raw")
            timeframe: "M1", "M5", "M15", "H1", "H4", "D1"
            count: Número de velas a obtener

        Returns:
            Lista de objetos Candle ordenados de más antigua a más reciente
        """
        if not self._connected:
            raise ConnectionError("No conectado a MT5")

        tf_const = self._get_timeframe_const(timeframe)
        rates = mt5.copy_rates_from_pos(symbol, tf_const, 0, count)

        if rates is None or len(rates) == 0:
            logger.warning(f"No se obtuvieron velas para {symbol} {timeframe}")
            return []

        candles = []
        for r in rates:
            candles.append(Candle(
                time=datetime.utcfromtimestamp(r["time"]),
                open=float(r["open"]),
                high=float(r["high"]),
                low=float(r["low"]),
                close=float(r["close"]),
                volume=float(r["tick_volume"]),
                timeframe=timeframe,
            ))

        return candles

    def get_current_price(self, symbol: str) -> Optional[Dict[str, float]]:
        """Obtiene bid/ask actual."""
        if not self._connected:
            raise ConnectionError("No conectado a MT5")

        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            return None

        return {
            "bid": tick.bid,
            "ask": tick.ask,
            "spread": tick.ask - tick.bid,
            "time": datetime.utcfromtimestamp(tick.time),
        }

    def get_account_info(self) -> Optional[Dict[str, float]]:
        """Obtiene información de la cuenta."""
        if not self._connected:
            raise ConnectionError("No conectado a MT5")

        info = mt5.account_info()
        if info is None:
            return None

        return {
            "balance": info.balance,
            "equity": info.equity,
            "margin": info.margin,
            "free_margin": info.margin_free,
            "profit": info.profit,
            "leverage": info.leverage,
        }

    def get_symbol_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Obtiene info del símbolo (punto, tamaño de contrato, etc.)."""
        if not self._connected:
            raise ConnectionError("No conectado a MT5")

        info = mt5.symbol_info(symbol)
        if info is None:
            return None

        return {
            "point": info.point,
            "digits": info.digits,
            "contract_size": info.trade_contract_size,
            "volume_min": info.volume_min,
            "volume_max": info.volume_max,
            "volume_step": info.volume_step,
            "trade_stops_level": info.trade_stops_level,
            "spread": info.spread,
        }

    def get_open_positions(self, symbol: Optional[str] = None) -> List[Dict]:
        """Obtiene posiciones abiertas."""
        if not self._connected:
            raise ConnectionError("No conectado a MT5")

        if symbol:
            positions = mt5.positions_get(symbol=symbol)
        else:
            positions = mt5.positions_get()

        if positions is None:
            return []

        return [
            {
                "ticket": p.ticket,
                "symbol": p.symbol,
                "type": "BUY" if p.type == 0 else "SELL",
                "volume": p.volume,
                "price_open": p.price_open,
                "sl": p.sl,
                "tp": p.tp,
                "profit": p.profit,
                "time": datetime.utcfromtimestamp(p.time),
                "comment": p.comment,
            }
            for p in positions
        ]


def candles_from_dataframe(df: pd.DataFrame, timeframe: str) -> List[Candle]:
    """
    Convierte un DataFrame con columnas OHLCV a lista de Candle.
    Útil para backtesting con datos históricos.

    Espera columnas: time/date, open, high, low, close, volume (opcional)
    """
    candles = []
    for _, row in df.iterrows():
        time_val = row.get("time", row.get("date", row.name))
        if isinstance(time_val, str):
            time_val = pd.to_datetime(time_val)

        candles.append(Candle(
            time=time_val,
            open=float(row["open"]),
            high=float(row["high"]),
            low=float(row["low"]),
            close=float(row["close"]),
            volume=float(row.get("volume", row.get("tick_volume", 0))),
            timeframe=timeframe,
        ))

    return candles
