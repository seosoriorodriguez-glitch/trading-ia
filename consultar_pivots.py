# -*- coding: utf-8 -*-
"""
Script para consultar y visualizar pivots activos
Usa la misma lógica del bot para detectar pivots
"""
import sys
import io
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import MetaTrader5 as mt5
import pandas as pd
import yaml
from datetime import datetime, timezone

from strategies.pivot_scalping.core.pivot_detection import detect_pivot_highs, detect_pivot_lows, filter_active_pivots


def main():
    # Conectar a MT5
    print("📡 Conectando a MT5...")
    if not mt5.initialize():
        print("❌ No se pudo conectar a MT5")
        return
    
    print("✅ Conectado a MT5\n")
    
    # Cargar config
    config_path = Path(__file__).parent / 'strategies' / 'pivot_scalping' / 'config' / 'scalping_params_M5M1_aggressive.yaml'
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    pivot_config = config['pivots']
    
    # Descargar datos M5
    symbol = "US30.cash"
    print(f"📥 Descargando últimas 300 velas M5 de {symbol}...")
    
    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M5, 0, 300)
    
    if rates is None or len(rates) == 0:
        print("❌ No se pudieron obtener datos")
        mt5.shutdown()
        return
    
    # Convertir a DataFrame
    df_m5 = pd.DataFrame(rates)
    df_m5['time'] = pd.to_datetime(df_m5['time'], unit='s', utc=True)
    
    print(f"✅ {len(df_m5)} velas descargadas")
    print(f"   Período: {df_m5['time'].iloc[0]} → {df_m5['time'].iloc[-1]}\n")
    
    # Convertir DataFrame a lista de Candles
    from strategies.pivot_scalping.core.pivot_detection import Candle
    
    candles = []
    for _, row in df_m5.iterrows():
        candles.append(Candle(
            time=row['time'],
            open=row['open'],
            high=row['high'],
            low=row['low'],
            close=row['close'],
            volume=int(row['tick_volume'])
        ))
    
    # Detectar pivots
    print("🔍 Detectando pivots...")
    pivot_highs = detect_pivot_highs(
        candles,
        swing_strength=pivot_config['swing_strength'],
        min_zone_width=pivot_config['min_zone_width'],
        max_zone_width=pivot_config['max_zone_width']
    )
    
    pivot_lows = detect_pivot_lows(
        candles,
        swing_strength=pivot_config['swing_strength'],
        min_zone_width=pivot_config['min_zone_width'],
        max_zone_width=pivot_config['max_zone_width']
    )
    
    all_pivots = pivot_highs + pivot_lows
    
    # Filtrar activos
    current_time = datetime.now(timezone.utc)
    active_pivots = filter_active_pivots(
        all_pivots,
        current_time,
        expiry_candles=pivot_config['expiry_candles'],
        max_touches=pivot_config['max_touches'],
        max_active=pivot_config['max_active_zones']
    )
    
    # Separar por tipo
    from strategies.pivot_scalping.core.pivot_detection import PivotType
    highs = [p for p in active_pivots if p.type == PivotType.HIGH]
    lows = [p for p in active_pivots if p.type == PivotType.LOW]
    
    print(f"✅ {len(active_pivots)} pivots activos (H:{len(highs)}, L:{len(lows)})\n")
    
    # Mostrar detalles
    print("=" * 80)
    print("🔴 PIVOT HIGHS (Resistencias)")
    print("=" * 80)
    
    if len(highs) == 0:
        print("   (ninguno)\n")
    else:
        for i, pivot in enumerate(sorted(highs, key=lambda p: p.price_high, reverse=True), 1):
            age_candles = (current_time - pivot.time).total_seconds() / 300  # 5 min = 300 seg
            print(f"\n{i}. Zona: {pivot.price_low:.2f} - {pivot.price_high:.2f}")
            print(f"   Precio pivot: {pivot.price_high:.2f}")
            print(f"   Toques: {pivot.touches}")
            print(f"   Edad: {int(age_candles)} velas M5 (~{int(age_candles * 5)} min)")
            print(f"   Formado: {pivot.time.strftime('%Y-%m-%d %H:%M UTC')}")
    
    print("\n" + "=" * 80)
    print("🟢 PIVOT LOWS (Soportes)")
    print("=" * 80)
    
    if len(lows) == 0:
        print("   (ninguno)\n")
    else:
        for i, pivot in enumerate(sorted(lows, key=lambda p: p.price_low, reverse=True), 1):
            age_candles = (current_time - pivot.time).total_seconds() / 300
            print(f"\n{i}. Zona: {pivot.price_low:.2f} - {pivot.price_high:.2f}")
            print(f"   Precio pivot: {pivot.price_low:.2f}")
            print(f"   Toques: {pivot.touches}")
            print(f"   Edad: {int(age_candles)} velas M5 (~{int(age_candles * 5)} min)")
            print(f"   Formado: {pivot.time.strftime('%Y-%m-%d %H:%M UTC')}")
    
    print("\n" + "=" * 80)
    print("📊 RESUMEN")
    print("=" * 80)
    print(f"Total pivots activos: {len(active_pivots)}")
    print(f"  - Pivot Highs: {len(highs)}")
    print(f"  - Pivot Lows: {len(lows)}")
    print(f"\nParámetros:")
    print(f"  - swing_strength: {pivot_config['swing_strength']}")
    print(f"  - min_touches: {pivot_config['min_touches']}")
    print(f"  - expiry_candles: {pivot_config['expiry_candles']}")
    print(f"  - buffer_points: {config['stop_loss']['buffer_points']}")
    print("\n" + "=" * 80)
    
    # Dibujar líneas en MT5 (opcional)
    print("\n💡 Para dibujar estas zonas en MT5:")
    print("   1. Usa Insert → Objects → Horizontal Line")
    print("   2. Coloca líneas en los precios mostrados arriba")
    print("   3. O ejecuta este script con --draw para dibujarlas automáticamente\n")
    
    mt5.shutdown()


if __name__ == '__main__':
    main()
