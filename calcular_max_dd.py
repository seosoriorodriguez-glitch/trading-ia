# -*- coding: utf-8 -*-
"""
Calcular Max Drawdown del backtest LIMIT sin BOS
"""
import sys
import codecs
if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

import pandas as pd
from datetime import datetime

print("\n" + "="*80)
print("  ANÁLISIS DE DRAWDOWN - LIMIT SIN BOS")
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

print(f"\n📅 PERÍODO DEL BACKTEST:")
print(f"  Inicio:     {start_date.strftime('%Y-%m-%d')}")
print(f"  Fin:        {end_date.strftime('%Y-%m-%d')}")
print(f"  Duración:   {days} días")

# Calcular equity curve
balance_inicial = 100_000
equity = [balance_inicial]
balance = balance_inicial
peak = balance_inicial
max_dd = 0
max_dd_pct = 0
max_dd_date = None
dd_history = []

for idx, row in df.iterrows():
    balance += row["pnl_usd"]
    equity.append(balance)
    
    # Actualizar peak
    if balance > peak:
        peak = balance
    
    # Calcular drawdown actual
    dd = peak - balance
    dd_pct = (dd / peak) * 100 if peak > 0 else 0
    
    dd_history.append({
        "date": row["exit_time"],
        "balance": balance,
        "peak": peak,
        "dd_usd": dd,
        "dd_pct": dd_pct
    })
    
    # Actualizar max drawdown
    if dd > max_dd:
        max_dd = dd
        max_dd_pct = dd_pct
        max_dd_date = row["exit_time"]

balance_final = balance

print(f"\n💰 BALANCE:")
print(f"  Inicial:    ${balance_inicial:,.2f}")
print(f"  Final:      ${balance_final:,.2f}")
print(f"  Retorno:    {((balance_final - balance_inicial) / balance_inicial * 100):+.2f}%")

print(f"\n📉 MAX DRAWDOWN:")
print(f"  USD:        ${max_dd:,.2f}")
print(f"  Porcentaje: {max_dd_pct:.2f}%")
print(f"  Fecha:      {max_dd_date.strftime('%Y-%m-%d %H:%M') if max_dd_date else 'N/A'}")

# Encontrar el período de mayor drawdown
df_dd = pd.DataFrame(dd_history)
df_dd_sorted = df_dd.sort_values("dd_pct", ascending=False).head(10)

print(f"\n📊 TOP 10 MOMENTOS DE MAYOR DRAWDOWN:")
print(f"\n{'Fecha':<20} {'Balance':<15} {'Peak':<15} {'DD USD':<12} {'DD %':<8}")
print("-" * 80)
for idx, row in df_dd_sorted.iterrows():
    print(f"{row['date'].strftime('%Y-%m-%d %H:%M'):<20} "
          f"${row['balance']:>12,.2f} "
          f"${row['peak']:>12,.2f} "
          f"${row['dd_usd']:>10,.2f} "
          f"{row['dd_pct']:>6.2f}%")

# Calcular drawdown por mes
df["month"] = df["exit_time"].dt.to_period("M")
monthly_stats = []

for month in df["month"].unique():
    df_month = df[df["month"] == month]
    month_pnl = df_month["pnl_usd"].sum()
    month_trades = len(df_month)
    month_winners = len(df_month[df_month["pnl_usd"] > 0])
    month_wr = (month_winners / month_trades * 100) if month_trades > 0 else 0
    
    monthly_stats.append({
        "month": str(month),
        "trades": month_trades,
        "winners": month_winners,
        "wr": month_wr,
        "pnl": month_pnl
    })

df_monthly = pd.DataFrame(monthly_stats)

print(f"\n📊 ESTADÍSTICAS MENSUALES:")
print(f"\n{'Mes':<10} {'Trades':<8} {'Winners':<10} {'WR %':<8} {'PnL USD':<12}")
print("-" * 60)
for idx, row in df_monthly.iterrows():
    print(f"{row['month']:<10} "
          f"{row['trades']:<8} "
          f"{row['winners']:<10} "
          f"{row['wr']:>6.1f}% "
          f"${row['pnl']:>10,.2f}")

print(f"\n" + "="*80)
print("  RESUMEN")
print("="*80)

print(f"\n  Período:        {days} días")
print(f"  Total trades:   {len(df)}")
print(f"  Retorno:        {((balance_final - balance_inicial) / balance_inicial * 100):+.2f}%")
print(f"  Max Drawdown:   {max_dd_pct:.2f}%")
print(f"  Profit Factor:  {abs(df[df['pnl_usd'] > 0]['pnl_usd'].sum() / df[df['pnl_usd'] <= 0]['pnl_usd'].sum()):.2f}")

print("\n" + "="*80)
