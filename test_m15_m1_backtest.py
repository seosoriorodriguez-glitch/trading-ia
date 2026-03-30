# -*- coding: utf-8 -*-
"""
Backtest M15/M1 - Detección OB en M15, entrada en M1.
Mismos parámetros que M5/M1, solo cambio de timeframe.
"""
import sys
import codecs
if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from strategies.order_block.backtest.config import DEFAULT_PARAMS
from strategies.order_block.backtest.data_loader import load_csv
from strategies.order_block.backtest.backtester import OrderBlockBacktester

print("\n" + "="*70)
print("  BACKTEST M15/M1 - MISMOS PARAMETROS QUE M5/M1")
print("  (Detección OB en M15, entrada en M1)")
print("="*70)

# Cargar datos
print("\nCargando datos...")
df_m15 = load_csv("data/US30_cash_M15_260d.csv")
df_m1  = load_csv("data/US30_cash_M1_260d.csv")

print(f"  M15: {len(df_m15):,} velas")
print(f"  M1:  {len(df_m1):,} velas")
print(f"  Periodo M15: {df_m15['time'].iloc[0]} -> {df_m15['time'].iloc[-1]}")
print(f"  Periodo M1:  {df_m1['time'].iloc[0]} -> {df_m1['time'].iloc[-1]}")

# Ejecutar backtest M15/M1
print("\nEjecutando backtest M15/M1...")
print()

bt = OrderBlockBacktester(DEFAULT_PARAMS)
result = bt.run(
    df_higher=df_m15,  # M15 para detección de OBs
    df_lower=df_m1     # M1 para entradas
)

# Mostrar resultados
bt.print_summary(result, "M15", "M1")

# Guardar resultados
if not result.empty:
    output_file = "strategies/order_block/backtest/results/m15_m1_test.csv"
    result.to_csv(output_file, index=False)
    print(f"\nResultados guardados en: {output_file}")
    print(f"Total trades: {len(result)}")
else:
    print("\nNo se generaron trades en el backtest M15/M1")

print("\n" + "="*70)
print("  BACKTEST M15/M1 COMPLETADO")
print("="*70 + "\n")
