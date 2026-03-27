# -*- coding: utf-8 -*-
"""
Live Signal Monitor - Detección de señales en tiempo real
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import pandas as pd
from datetime import datetime, timezone
from typing import List, Optional

from strategies.pivot_scalping.core.pivot_detection import (
    PivotPoint, detect_pivot_highs, detect_pivot_lows,
    update_pivot_touches, filter_active_pivots, Candle as M5Candle
)
from strategies.pivot_scalping.core.scalping_signals import (
    TradingSignal, ScalpingSignalGenerator
)
from strategies.pivot_scalping.core.rejection_patterns import Candle as M1Candle


class LiveSignalMonitor:
    """Monitor de señales en tiempo real"""
    
    def __init__(self, config: dict, data_feed):
        self.config = config
        self.data_feed = data_feed
        self.signal_generator = ScalpingSignalGenerator(config)
        self.all_pivots: List[PivotPoint] = []
        self.last_pivot_update = None
        
    def update_pivots(self) -> int:
        """
        Actualiza pivots con datos M5 más recientes
        
        Returns:
            Número de pivots activos
        """
        # Descargar últimas 200 velas M5
        df_m5 = self.data_feed.get_latest_candles('M5', 200)
        if df_m5 is None or len(df_m5) == 0:
            print("⚠️  No se pudieron obtener datos M5")
            return 0
        
        # Convertir a lista de Candles
        candles_m5 = []
        for _, row in df_m5.iterrows():
            candle = M5Candle(
                time=row['time'],
                open=row['open'],
                high=row['high'],
                low=row['low'],
                close=row['close'],
                volume=row['tick_volume']
            )
            candles_m5.append(candle)
        
        # Detectar pivots
        pivot_config = self.config['pivots']
        swing_strength = pivot_config['swing_strength']
        
        pivot_highs = detect_pivot_highs(candles_m5, swing_strength)
        pivot_lows = detect_pivot_lows(candles_m5, swing_strength)
        
        # Combinar y actualizar toques
        self.all_pivots = pivot_highs + pivot_lows
        
        # Actualizar toques para cada pivot
        for pivot in self.all_pivots:
            update_pivot_touches(
                pivot,
                candles_m5,
                min_separation=pivot_config['min_touch_separation']
            )
        
        # Filtrar pivots activos
        current_time = candles_m5[-1].time
        self.all_pivots = filter_active_pivots(
            self.all_pivots,
            current_time,
            expiry_candles=pivot_config['expiry_candles'],
            max_touches=pivot_config['max_touches'],
            max_active=pivot_config['max_active_zones']
        )
        
        # Actualizar pivots en el signal generator
        self.signal_generator.update_pivots(self.all_pivots)
        
        self.last_pivot_update = current_time
        
        return len(self.all_pivots)
    
    def check_for_signal(self) -> Optional[TradingSignal]:
        """
        Verifica si hay señal en la última vela M1 cerrada
        
        Returns:
            TradingSignal si hay señal, None si no
        """
        try:
            # Descargar últimas 2 velas M1
            df_m1 = self.data_feed.get_latest_candles('M1', 2)
            if df_m1 is None or len(df_m1) < 2:
                return None
            
            # Convertir a Candles (rejection_patterns.Candle solo usa OHLC)
            current_candle = M1Candle(
                open=df_m1.iloc[-1]['open'],
                high=df_m1.iloc[-1]['high'],
                low=df_m1.iloc[-1]['low'],
                close=df_m1.iloc[-1]['close']
            )
            
            previous_candle = M1Candle(
                open=df_m1.iloc[-2]['open'],
                high=df_m1.iloc[-2]['high'],
                low=df_m1.iloc[-2]['low'],
                close=df_m1.iloc[-2]['close']
            )
            
            # Verificar señal (usar timestamp de la última vela M1)
            current_time = df_m1.iloc[-1]['time']
            signal = self.signal_generator.check_signal(
                current_candle,
                previous_candle,
                self.all_pivots,
                current_time
            )
            
            return signal
        except Exception as e:
            # Capturar traceback completo
            import traceback
            error_msg = f"Error en check_for_signal: {e}\n{traceback.format_exc()}"
            print(f"❌ {error_msg}", flush=True)
            raise
    
    def get_pivot_summary(self) -> dict:
        """Retorna resumen de pivots activos"""
        if not self.all_pivots:
            return {'total': 0, 'highs': 0, 'lows': 0}
        
        from strategies.pivot_scalping.core.pivot_detection import PivotType
        
        highs = sum(1 for p in self.all_pivots if p.type == PivotType.HIGH)
        lows = sum(1 for p in self.all_pivots if p.type == PivotType.LOW)
        
        return {
            'total': len(self.all_pivots),
            'highs': highs,
            'lows': lows,
            'last_update': self.last_pivot_update
        }
