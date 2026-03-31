# -*- coding: utf-8 -*-
"""
Analizar frecuencia de trades y peor día
"""
import sys
import codecs
if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

import pandas as pd
from datetime import datetime

print("\n" + "="*80)
print("  ANÁLISIS DE FRECUENCIA Y PEOR DÍA")
print("="*80)

# Cargar trades
df = pd.read_csv("strategies/order_block/backtest/results/ny_trades_LIMIT_SIN_BOS.csv")
df["entry_time"] = pd.to_datetime(df["entry_time"])
df["exit_time"] = pd.to_datetime(df["exit_time"])

# Ordenar por tiempo de salida
df = df.sort_values("exit_time")

# Período del backtest
start_date = df["entry_time"].min()
end_date = df["exit_time"].max()
days = (end_date - start_date).days
total_trades = len(df)

print(f"\n📅 PERÍODO:")
print(f"  Inicio:     {start_date.strftime('%Y-%m-%d')}")
print(f"  Fin:        {end_date.strftime('%Y-%m-%d')}")
print(f"  Duración:   {days} días")

print(f"\n📊 FRECUENCIA DE TRADES:")
print(f"  Total trades:       {total_trades}")
print(f"  Trades por día:     {total_trades / days:.2f}")
print(f"  Trades por semana:  {total_trades / (days / 7):.2f}")
print(f"  Trades por mes:     {total_trades / (days / 30):.2f}")

# Calcular trades por día de la semana
df["weekday"] = df["exit_time"].dt.day_name()
weekday_counts = df.groupby("weekday").size()
weekday_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
weekday_counts = weekday_counts.reindex(weekday_order, fill_value=0)

print(f"\n📊 TRADES POR DÍA DE LA SEMANA:")
for day, count in weekday_counts.items():
    pct = (count / total_trades * 100) if total_trades > 0 else 0
    print(f"  {day:<10} {count:>3} trades ({pct:>5.1f}%)")

# Agrupar por día
df["date"] = df["exit_time"].dt.date
daily_stats = df.groupby("date").agg({
    "pnl_usd": ["sum", "count"],
}).reset_index()
daily_stats.columns = ["date", "pnl_usd", "trades"]

# Calcular balance acumulado por día
balance_inicial = 100_000
daily_stats["balance"] = balance_inicial + daily_stats["pnl_usd"].cumsum()
daily_stats["pnl_pct"] = (daily_stats["pnl_usd"] / daily_stats["balance"].shift(1).fillna(balance_inicial)) * 100

# Encontrar peor día
worst_day = daily_stats.loc[daily_stats["pnl_usd"].idxmin()]
best_day = daily_stats.loc[daily_stats["pnl_usd"].idxmax()]

print(f"\n📉 PEOR DÍA:")
print(f"  Fecha:      {worst_day['date']}")
print(f"  PnL USD:    ${worst_day['pnl_usd']:,.2f}")
print(f"  PnL %:      {worst_day['pnl_pct']:.2f}%")
print(f"  Trades:     {int(worst_day['trades'])}")
print(f"  Balance:    ${worst_day['balance']:,.2f}")

print(f"\n📈 MEJOR DÍA:")
print(f"  Fecha:      {best_day['date']}")
print(f"  PnL USD:    ${best_day['pnl_usd']:,.2f}")
print(f"  PnL %:      {best_day['pnl_pct']:.2f}%")
print(f"  Trades:     {int(best_day['trades'])}")
print(f"  Balance:    ${best_day['balance']:,.2f}")

# Top 10 peores días
print(f"\n📊 TOP 10 PEORES DÍAS:")
worst_days = daily_stats.nsmallest(10, "pnl_usd")
print(f"\n{'Fecha':<12} {'Trades':<8} {'PnL USD':<12} {'PnL %':<8} {'Balance':<15}")
print("-" * 65)
for idx, row in worst_days.iterrows():
    print(f"{str(row['date']):<12} "
          f"{int(row['trades']):<8} "
          f"${row['pnl_usd']:>10,.2f} "
          f"{row['pnl_pct']:>6.2f}% "
          f"${row['balance']:>12,.2f}")

# Top 10 mejores días
print(f"\n📊 TOP 10 MEJORES DÍAS:")
best_days = daily_stats.nlargest(10, "pnl_usd")
print(f"\n{'Fecha':<12} {'Trades':<8} {'PnL USD':<12} {'PnL %':<8} {'Balance':<15}")
print("-" * 65)
for idx, row in best_days.iterrows():
    print(f"{str(row['date']):<12} "
          f"{int(row['trades']):<8} "
          f"${row['pnl_usd']:>10,.2f} "
          f"{row['pnl_pct']:>6.2f}% "
          f"${row['balance']:>12,.2f}")

# Estadísticas de días
positive_days = daily_stats[daily_stats["pnl_usd"] > 0]
negative_days = daily_stats[daily_stats["pnl_usd"] < 0]
neutral_days = daily_stats[daily_stats["pnl_usd"] == 0]

print(f"\n📊 ESTADÍSTICAS DE DÍAS:")
print(f"  Total días con trades:  {len(daily_stats)}")
print(f"  Días positivos:         {len(positive_days)} ({len(positive_days)/len(daily_stats)*100:.1f}%)")
print(f"  Días negativos:         {len(negative_days)} ({len(negative_days)/len(daily_stats)*100:.1f}%)")
print(f"  Días neutros:           {len(neutral_days)} ({len(neutral_days)/len(daily_stats)*100:.1f}%)")

if len(positive_days) > 0:
    print(f"\n  Días positivos:")
    print(f"    PnL promedio:       ${positive_days['pnl_usd'].mean():,.2f}")
    print(f"    PnL % promedio:     {positive_days['pnl_pct'].mean():.2f}%")
    print(f"    Trades promedio:    {positive_days['trades'].mean():.1f}")

if len(negative_days) > 0:
    print(f"\n  Días negativos:")
    print(f"    PnL promedio:       ${negative_days['pnl_usd'].mean():,.2f}")
    print(f"    PnL % promedio:     {negative_days['pnl_pct'].mean():.2f}%")
    print(f"    Trades promedio:    {negative_days['trades'].mean():.1f}")

# Verificar Best Day Rule (día más rentable no debe ser >50% del total de días positivos)
if len(positive_days) > 0:
    total_positive_pnl = positive_days["pnl_usd"].sum()
    best_day_pnl = best_day["pnl_usd"]
    best_day_pct_of_positive = (best_day_pnl / total_positive_pnl) * 100
    
    print(f"\n⚠️  BEST DAY RULE (FTMO):")
    print(f"  Total PnL días positivos:  ${total_positive_pnl:,.2f}")
    print(f"  Mejor día PnL:             ${best_day_pnl:,.2f}")
    print(f"  % del total positivo:      {best_day_pct_of_positive:.2f}%")
    
    if best_day_pct_of_positive > 50:
        print(f"  ❌ FALLA Best Day Rule (>{best_day_pct_of_positive:.1f}% > 50%)")
    else:
        print(f"  ✅ PASA Best Day Rule (<{best_day_pct_of_positive:.1f}% < 50%)")

print("\n" + "="*80)
print("  RESUMEN")
print("="*80)

print(f"\n  Frecuencia:     {total_trades / days:.2f} trades/día")
print(f"  Peor día:       {worst_day['pnl_pct']:.2f}% (${worst_day['pnl_usd']:,.2f})")
print(f"  Mejor día:      {best_day['pnl_pct']:.2f}% (${best_day['pnl_usd']:,.2f})")
print(f"  Días positivos: {len(positive_days)/len(daily_stats)*100:.1f}%")

print("\n" + "="*80)
