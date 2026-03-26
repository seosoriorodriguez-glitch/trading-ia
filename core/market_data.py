"""
Módulo de datos de mercado.
Conecta a MetaTrader 5 y obtiene velas, precios, info de cuenta.
Para backtesting, puede trabajar con datos históricos en CSV/DataFrame.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple, Any
from dataclasses import dataclass

import pandas as pd
import numpy as np

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
    Conexión a MetaTrader 5.
    Wrapper que soporta ambas plataformas:
      - Windows: librería oficial MetaTrader5 (pip install MetaTrader5)
      - macOS/Docker: silicon-metatrader5 (pip install siliconmetatrader5)

    La detección es automática. En Mac usa Docker + QEMU por detrás.
    """

    def __init__(self, host: str = "localhost", port: int = 8001):
        self._connected = False
        self._mt5 = None
        self._platform = None          # "windows" o "mac_docker"
        self._host = host              # Solo para mac_docker
        self._port = port              # Solo para mac_docker

    def connect(self) -> bool:
        """
        Conecta a la terminal MT5.
        Intenta primero la librería nativa (Windows),
        si no existe, usa silicon-metatrader5 (Mac/Docker).
        """
        # --- Intento 1: Windows nativo ---
        try:
            import MetaTrader5 as mt5
            self._mt5 = mt5
            self._platform = "windows"

            if not mt5.initialize():
                logger.error(f"MT5 initialize() falló: {mt5.last_error()}")
                return False

            self._connected = True
            info = mt5.account_info()
            if info:
                logger.info(f"Conectado a MT5 (Windows) — Cuenta: {info.login}, "
                           f"Broker: {info.company}, Balance: {info.balance}")
            return True

        except ImportError:
            logger.info("MetaTrader5 nativo no disponible, intentando silicon-metatrader5...")

        # --- Intento 2: Mac/Docker via silicon-metatrader5 ---
        try:
            from siliconmetatrader5 import MetaTrader5
            mt5 = MetaTrader5(host=self._host, port=self._port, keepalive=True)
            self._mt5 = mt5
            self._platform = "mac_docker"

            # silicon-metatrader5 no usa initialize(), la conexión es al instanciar
            # Verificar con ping
            if hasattr(mt5, 'ping') and not mt5.ping():
                logger.error("silicon-metatrader5: ping falló — ¿Docker corriendo?")
                return False

            self._connected = True
            info = mt5.account_info()
            if info:
                logger.info(f"Conectado a MT5 (Mac/Docker) — Cuenta: {info.login}, "
                           f"Broker: {info.company}, Balance: {info.balance}")
            return True

        except ImportError:
            logger.error(
                "Ninguna librería MT5 disponible.\n"
                "  Windows: pip install MetaTrader5\n"
                "  macOS:   pip install siliconmetatrader5\n"
                "  Ver README.md para setup de Docker en Mac."
            )
            return False
        except Exception as e:
            logger.error(f"Error conectando a MT5: {e}")
            return False

    def disconnect(self):
        """Desconecta de MT5."""
        if self._mt5 and self._connected:
            self._mt5.shutdown()
            self._connected = False
            logger.info("Desconectado de MT5")

    def is_connected(self) -> bool:
        return self._connected

    def _get_timeframe_const(self, tf: str):
        """Convierte string de timeframe a constante MT5."""
        tf_map = {
            "M1": self._mt5.TIMEFRAME_M1,
            "M5": self._mt5.TIMEFRAME_M5,
            "M15": self._mt5.TIMEFRAME_M15,
            "M30": self._mt5.TIMEFRAME_M30,
            "H1": self._mt5.TIMEFRAME_H1,
            "H4": self._mt5.TIMEFRAME_H4,
            "D1": self._mt5.TIMEFRAME_D1,
            "W1": self._mt5.TIMEFRAME_W1,
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
        rates = self._mt5.copy_rates_from_pos(symbol, tf_const, 0, count)

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

        tick = self._mt5.symbol_info_tick(symbol)
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

        info = self._mt5.account_info()
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

        info = self._mt5.symbol_info(symbol)
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
            positions = self._mt5.positions_get(symbol=symbol)
        else:
            positions = self._mt5.positions_get()

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
