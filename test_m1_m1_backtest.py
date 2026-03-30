# -*- coding: utf-8 -*-
"""
Backtest M1/M1 - Mismos parámetros que M5/M1, solo cambio de timeframe.
NO modifica nada del código live.
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
print("  BACKTEST M1/M1 - MISMOS PARAMETROS QUE M5/M1")
print("  (NO modifica codigo live)")
print("="*70)

# Cargar datos M1
print("\nCargando datos M1...")
df_m1 = load_csv("data/US30_cash_M1_260d.csv")
print(f"  Datos cargados: {len(df_m1):,} velas M1")
print(f"  Periodo: {df_m1['time'].iloc[0]} -> {df_m1['time'].iloc[-1]}")

# Ejecutar backtest M1/M1 (detección y entrada en M1)
print("\nEjecutando backtest M1/M1...")
print("  (Esto puede tomar 3-5 minutos, procesando 5x más datos que M5/M1)")
print()

bt = OrderBlockBacktester(DEFAULT_PARAMS)
result = bt.run(
    df_higher=df_m1,  # M1 para detección de OBs
    df_lower=df_m1    # M1 para entradas
)

# Mostrar resultados
bt.print_summary(result, "M1", "M1")

# Guardar resultados
if not result.empty:
    output_file = "strategies/order_block/backtest/results/m1_m1_test.csv"
    result.to_csv(output_file, index=False)
    print(f"\nResultados guardados en: {output_file}")
    print(f"Total trades: {len(result)}")
else:
    print("\nNo se generaron trades en el backtest M1/M1")

print("\n" + "="*70)
print("  BACKTEST M1/M1 COMPLETADO")
print("="*70 + "\n")
