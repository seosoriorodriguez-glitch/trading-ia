# -*- coding: utf-8 -*-
"""
Generar tablas de trades ganadores (desde febrero) y perdedores (marzo)
"""
import sys
import codecs
if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

import pandas as pd
from datetime import datetime

print("\n" + "="*80)
print("  GENERANDO TABLAS DE TRADES")
print("="*80)

# Cargar trades
df = pd.read_csv("strategies/order_block/backtest/results/ny_trades_LIMIT_SIN_BOS.csv")
df["entry_time"] = pd.to_datetime(df["entry_time"])
df["exit_time"] = pd.to_datetime(df["exit_time"])

print(f"\nTotal trades: {len(df)}")
print(f"Período: {df['entry_time'].min()} -> {df['entry_time'].max()}")

# Filtrar trades desde febrero 2026
feb_start = datetime(2026, 2, 1)
df_feb = df[df["entry_time"] >= feb_start].copy()

print(f"\nTrades desde febrero 2026: {len(df_feb)}")

# Winners desde febrero
winners_feb = df_feb[df_feb["pnl_usd"] > 0].copy()
winners_feb = winners_feb.sort_values("entry_time")

print(f"Winners desde febrero: {len(winners_feb)}")

# Losers de marzo
march_start = datetime(2026, 3, 1)
march_end = datetime(2026, 4, 1)
losers_march = df[(df["entry_time"] >= march_start) & (df["entry_time"] < march_end) & (df["pnl_usd"] <= 0)].copy()
losers_march = losers_march.sort_values("entry_time").head(10)

print(f"Losers de marzo (primeros 10): {len(losers_march)}")

# Convertir a timezone America/Santiago (UTC-3)
def to_santiago(dt):
    return dt - pd.Timedelta(hours=3)

winners_feb["entry_time_santiago"] = winners_feb["entry_time"].apply(to_santiago)
winners_feb["exit_time_santiago"] = winners_feb["exit_time"].apply(to_santiago)
losers_march["entry_time_santiago"] = losers_march["entry_time"].apply(to_santiago)
losers_march["exit_time_santiago"] = losers_march["exit_time"].apply(to_santiago)

# Crear tabla de winners
print("\n" + "="*80)
print("  TABLA 1: TRADES GANADORES DESDE FEBRERO 2026")
print("="*80)

winners_table = winners_feb[[
    "trade_id", "direction", "entry_time_santiago", "exit_time_santiago",
    "ob_zone_low", "ob_zone_high", "entry_price", "sl", "tp", "exit_price",
    "pnl_usd", "pnl_r", "exit_reason"
]].copy()

winners_table.columns = [
    "ID", "Dir", "Entry Time (CL)", "Exit Time (CL)",
    "OB Low", "OB High", "Entry", "SL", "TP", "Exit",
    "PnL USD", "R-mult", "Exit Reason"
]

print(f"\n{winners_table.to_string(index=False)}")

# Guardar CSV
winners_table.to_csv("winners_feb_2026.csv", index=False)
print(f"\n✅ Guardado en: winners_feb_2026.csv")

# Crear tabla de losers
print("\n" + "="*80)
print("  TABLA 2: 10 TRADES PERDEDORES DE MARZO 2026")
print("="*80)

losers_table = losers_march[[
    "trade_id", "direction", "entry_time_santiago", "exit_time_santiago",
    "ob_zone_low", "ob_zone_high", "entry_price", "sl", "tp", "exit_price",
    "pnl_usd", "pnl_r", "exit_reason"
]].copy()

losers_table.columns = [
    "ID", "Dir", "Entry Time (CL)", "Exit Time (CL)",
    "OB Low", "OB High", "Entry", "SL", "TP", "Exit",
    "PnL USD", "R-mult", "Exit Reason"
]

print(f"\n{losers_table.to_string(index=False)}")

# Guardar CSV
losers_table.to_csv("losers_march_2026.csv", index=False)
print(f"\n✅ Guardado en: losers_march_2026.csv")

# Resumen
print("\n" + "="*80)
print("  RESUMEN")
print("="*80)

print(f"\n📊 WINNERS DESDE FEBRERO:")
print(f"  Total:            {len(winners_feb)}")
print(f"  LONG:             {len(winners_feb[winners_feb['direction'] == 'long'])}")
print(f"  SHORT:            {len(winners_feb[winners_feb['direction'] == 'short'])}")
print(f"  PnL total:        ${winners_feb['pnl_usd'].sum():,.2f}")
print(f"  PnL promedio:     ${winners_feb['pnl_usd'].mean():,.2f}")
print(f"  R-mult promedio:  {winners_feb['pnl_r'].mean():.2f}R")

print(f"\n📊 LOSERS DE MARZO (10 primeros):")
print(f"  Total:            {len(losers_march)}")
print(f"  LONG:             {len(losers_march[losers_march['direction'] == 'long'])}")
print(f"  SHORT:            {len(losers_march[losers_march['direction'] == 'short'])}")
print(f"  PnL total:        ${losers_march['pnl_usd'].sum():,.2f}")
print(f"  PnL promedio:     ${losers_march['pnl_usd'].mean():,.2f}")
print(f"  R-mult promedio:  {losers_march['pnl_r'].mean():.2f}R")

print("\n" + "="*80)
