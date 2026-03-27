# -*- coding: utf-8 -*-
"""
Live Data Feed - Conexión en tiempo real con MT5
"""
import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timezone
from typing import Optional
import time


class LiveDataFeed:
    """Feed de datos en tiempo real desde MT5"""
    
    def __init__(self, symbol: str = "US30.cash"):
        self.symbol = symbol
        self.mt5_connected = False
        self.last_m1_time = None
        self.last_m5_time = None
        
    def connect(self) -> bool:
        """Conecta a MT5"""
        if not mt5.initialize():
            print(f"❌ Error inicializando MT5: {mt5.last_error()}")
            return False
        
        self.mt5_connected = True
        print(f"✅ Conectado a MT5")
        
        # Verificar símbolo
        symbol_info = mt5.symbol_info(self.symbol)
        if symbol_info is None:
            print(f"❌ Símbolo {self.symbol} no encontrado")
            return False
        
        if not symbol_info.visible:
            if not mt5.symbol_select(self.symbol, True):
                print(f"❌ Error seleccionando símbolo {self.symbol}")
                return False
        
        print(f"✅ Símbolo {self.symbol} verificado")
        return True
    
    def disconnect(self):
        """Desconecta de MT5"""
        if self.mt5_connected:
            mt5.shutdown()
            self.mt5_connected = False
            print("🔌 Desconectado de MT5")
    
    def get_latest_candles(self, timeframe: str, count: int = 100) -> Optional[pd.DataFrame]:
        """
        Obtiene las últimas N velas de un timeframe
        
        Args:
            timeframe: 'M1' o 'M5'
            count: Número de velas
        
        Returns:
            DataFrame con columnas: time, open, high, low, close, tick_volume, spread, real_volume
        """
        if not self.mt5_connected:
            return None
        
        # Mapear timeframe
        tf_map = {
            'M1': mt5.TIMEFRAME_M1,
            'M5': mt5.TIMEFRAME_M5,
            'M15': mt5.TIMEFRAME_M15
        }
        
        mt5_tf = tf_map.get(timeframe)
        if mt5_tf is None:
            print(f"❌ Timeframe inválido: {timeframe}")
            return None
        
        # Descargar datos
        rates = mt5.copy_rates_from_pos(self.symbol, mt5_tf, 0, count)
        
        if rates is None or len(rates) == 0:
            print(f"❌ Error descargando {timeframe}: {mt5.last_error()}")
            return None
        
        # Convertir a DataFrame
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        
        return df
    
    def wait_for_new_m1_candle(self) -> bool:
        """
        Espera hasta que cierre una nueva vela M1
        
        Returns:
            True si hay nueva vela, False si error
        """
        while True:
            df = self.get_latest_candles('M1', 1)
            if df is None:
                return False
            
            current_time = df.iloc[-1]['time']
            
            # Si es nueva vela
            if self.last_m1_time is None or current_time > self.last_m1_time:
                self.last_m1_time = current_time
                return True
            
            # Esperar 1 segundo
            time.sleep(1)
    
    def wait_for_new_m5_candle(self) -> bool:
        """
        Espera hasta que cierre una nueva vela M5
        
        Returns:
            True si hay nueva vela, False si error
        """
        while True:
            df = self.get_latest_candles('M5', 1)
            if df is None:
                return False
            
            current_time = df.iloc[-1]['time']
            
            # Si es nueva vela
            if self.last_m5_time is None or current_time > self.last_m5_time:
                self.last_m5_time = current_time
                return True
            
            # Esperar 5 segundos
            time.sleep(5)
    
    def get_current_price(self) -> Optional[dict]:
        """Obtiene precio actual (bid/ask)"""
        if not self.mt5_connected:
            return None
        
        tick = mt5.symbol_info_tick(self.symbol)
        if tick is None:
            return None
        
        return {
            'bid': tick.bid,
            'ask': tick.ask,
            'spread': tick.ask - tick.bid,
            'time': datetime.fromtimestamp(tick.time, tz=timezone.utc)
        }
    
    def get_account_info(self) -> Optional[dict]:
        """Obtiene información de la cuenta"""
        if not self.mt5_connected:
            return None
        
        account = mt5.account_info()
        if account is None:
            return None
        
        return {
            'balance': account.balance,
            'equity': account.equity,
            'margin': account.margin,
            'free_margin': account.margin_free,
            'profit': account.profit
        }
