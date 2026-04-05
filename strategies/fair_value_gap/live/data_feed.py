# -*- coding: utf-8 -*-
"""
Live Data Feed - Conexion en tiempo real con MT5.
Bot FVG — conecta a la instancia MT5_US30 (misma cuenta que Bot 1 OB NY).
"""
import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timezone
from typing import Optional
import time


class LiveDataFeed:
    """Feed de datos en tiempo real desde MT5."""

    def __init__(self, symbol: str = "US30.cash"):
        self.symbol = symbol
        self.mt5_connected = False

    def connect(self) -> bool:
        if not mt5.initialize(path=r"C:\Program Files\MT5_US30\terminal64.exe"):
            print(f"ERROR inicializando MT5: {mt5.last_error()}")
            return False
        self.mt5_connected = True

        symbol_info = mt5.symbol_info(self.symbol)
        if symbol_info is None:
            print(f"ERROR: simbolo {self.symbol} no encontrado")
            return False
        if not symbol_info.visible:
            if not mt5.symbol_select(self.symbol, True):
                print(f"ERROR seleccionando simbolo {self.symbol}")
                return False

        print(f"MT5 conectado - {self.symbol}")
        return True

    def disconnect(self):
        if self.mt5_connected:
            mt5.shutdown()
            self.mt5_connected = False

    def get_latest_candles(self, timeframe: str, count: int = 100) -> Optional[pd.DataFrame]:
        """Retorna las ultimas `count` velas del timeframe dado (M1 o M5)."""
        if not self.mt5_connected:
            return None

        tf_map = {
            "M1":  mt5.TIMEFRAME_M1,
            "M5":  mt5.TIMEFRAME_M5,
            "M15": mt5.TIMEFRAME_M15,
        }
        mt5_tf = tf_map.get(timeframe)
        if mt5_tf is None:
            print(f"Timeframe invalido: {timeframe}")
            return None

        rates = mt5.copy_rates_from_pos(self.symbol, mt5_tf, 0, count)
        if rates is None or len(rates) == 0:
            print(f"Error descargando {timeframe}: {mt5.last_error()}")
            return None

        df = pd.DataFrame(rates)
        df["time"] = pd.to_datetime(df["time"], unit="s")
        return df

    def get_current_price(self) -> Optional[dict]:
        if not self.mt5_connected:
            return None
        tick = mt5.symbol_info_tick(self.symbol)
        if tick is None:
            return None
        return {
            "bid":    tick.bid,
            "ask":    tick.ask,
            "spread": tick.ask - tick.bid,
            "time":   datetime.fromtimestamp(tick.time, tz=timezone.utc),
        }

    def get_account_info(self) -> Optional[dict]:
        if not self.mt5_connected:
            return None
        account = mt5.account_info()
        if account is None:
            return None
        return {
            "balance":     account.balance,
            "equity":      account.equity,
            "margin":      account.margin,
            "free_margin": account.margin_free,
            "profit":      account.profit,
        }
