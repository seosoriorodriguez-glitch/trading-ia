# -*- coding: utf-8 -*-
"""
Analizar por qué LIMIT genera más trades que MARKET
"""
import sys
import codecs
if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

import pandas as pd

print("\n" + "="*80)
print("  ¿POR QUÉ LIMIT GENERA MÁS TRADES?")
print("="*80)

# Cargar ambos backtests
df_market = pd.read_csv("strategies/order_block/backtest/results/ny_all_trades.csv")
df_limit = pd.read_csv("strategies/order_block/backtest/results/ny_trades_LIMIT_ORDERS.csv")

print(f"\n📊 COMPARACIÓN:")
print(f"  MARKET:  {len(df_market)} trades")
print(f"  LIMIT:   {len(df_limit)} trades")
print(f"  Diferencia: +{len(df_limit) - len(df_market)} trades")

# Analizar por dirección
print(f"\n📈 POR DIRECCIÓN:")

market_long = len(df_market[df_market['direction'] == 'long'])
market_short = len(df_market[df_market['direction'] == 'short'])
limit_long = len(df_limit[df_limit['direction'] == 'long'])
limit_short = len(df_limit[df_limit['direction'] == 'short'])

print(f"\n  LONG:")
print(f"    MARKET: {market_long}")
print(f"    LIMIT:  {limit_long}")
print(f"    Diff:   +{limit_long - market_long} ({(limit_long - market_long)/market_long*100:+.1f}%)")

print(f"\n  SHORT:")
print(f"    MARKET: {market_short}")
print(f"    LIMIT:  {limit_short}")
print(f"    Diff:   +{limit_short - market_short} ({(limit_short - market_short)/market_short*100:+.1f}%)")

# Hipótesis
print(f"\n" + "="*80)
print("  HIPÓTESIS")
print("="*80)

print(f"\n  🤔 ¿Por qué más trades con LIMIT?")

print(f"\n  HIPÓTESIS 1: Filtros más permisivos")
print(f"    MARKET: Rechaza trades fuera de zona (para SHORT)")
print(f"    LIMIT:  Solo verifica que M1 cierre dentro")
print(f"    → Más OBs pasan los filtros")

print(f"\n  HIPÓTESIS 2: Mejor timing de ejecución")
print(f"    MARKET: Entra inmediatamente al close de M1")
print(f"    LIMIT:  Espera a que precio toque el límite")
print(f"    → Captura mejores momentos de reversión")

print(f"\n  HIPÓTESIS 3: Riesgo diferente")
print(f"    MARKET: Entry variable (candle_close)")
print(f"    LIMIT:  Entry fijo (zone_high/low)")
print(f"    → Riesgo más consistente, más trades pasan filtros")

# Verificar filtros de riesgo
print(f"\n" + "="*80)
print("  ANÁLISIS DE RIESGO")
print("="*80)

print(f"\n  MARKET:")
market_risk_avg = abs(df_market['entry_price'] - df_market['sl']).mean()
print(f"    Riesgo promedio: {market_risk_avg:.2f} puntos")

print(f"\n  LIMIT:")
limit_risk_avg = abs(df_limit['entry_price'] - df_limit['sl']).mean()
print(f"    Riesgo promedio: {limit_risk_avg:.2f} puntos")

print(f"\n  Diferencia: {limit_risk_avg - market_risk_avg:+.2f} puntos")

# Analizar SHORT específicamente
print(f"\n📊 ANÁLISIS SHORT:")

market_short_df = df_market[df_market['direction'] == 'short']
limit_short_df = df_limit[df_limit['direction'] == 'short']

if len(market_short_df) > 0:
    market_short_risk = abs(market_short_df['entry_price'] - market_short_df['sl']).mean()
    print(f"\n  MARKET SHORT:")
    print(f"    Trades: {len(market_short_df)}")
    print(f"    Riesgo promedio: {market_short_risk:.2f} puntos")

if len(limit_short_df) > 0:
    limit_short_risk = abs(limit_short_df['entry_price'] - limit_short_df['sl']).mean()
    print(f"\n  LIMIT SHORT:")
    print(f"    Trades: {len(limit_short_df)}")
    print(f"    Riesgo promedio: {limit_short_risk:.2f} puntos")
    
    if len(market_short_df) > 0:
        print(f"\n  Diferencia: {limit_short_risk - market_short_risk:+.2f} puntos")

print(f"\n" + "="*80)
print("  CONCLUSIÓN")
print("="*80)

print(f"\n  La lógica LIMIT genera +{len(df_limit) - len(df_market)} trades porque:")
print(f"  1. Entry fijo en límite de zona → Riesgo más consistente")
print(f"  2. Más OBs pasan los filtros de riesgo (min/max)")
print(f"  3. Especialmente SHORT: +{limit_short - market_short} trades")

print("\n" + "="*80)
