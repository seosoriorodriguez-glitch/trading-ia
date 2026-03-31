# -*- coding: utf-8 -*-
"""
Backtest R:R 3.5 / Buffer 25 con NY extendido (2hr antes)
"""
import sys
import codecs
if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

import pandas as pd
from strategies.order_block.backtest.backtester_limit_orders import OrderBlockBacktesterLimitOrders
from strategies.order_block.backtest.config import DEFAULT_PARAMS

print("\n" + "="*80)
print("  BACKTEST: R:R 3.5 / Buffer 25 - NY EXTENDIDO")
print("="*80)

print("\n📋 CONFIGURACIÓN:")
print("  • R:R: 3.5")
print("  • Buffer SL: 25 puntos")
print("  • Sin filtro BOS")
print("  • Sesión NY: 11:30-20:00 UTC (2hr antes + NY completo)")
print("  • Skip primeros 15 min: NO (ya que empezamos 2hr antes)")

# Cargar datos
print("\nCargando datos...")
df_m5 = pd.read_csv("data/US30_cash_M5_260d.csv")
df_m1 = pd.read_csv("data/US30_cash_M1_260d.csv")

df_m5["time"] = pd.to_datetime(df_m5["time"])
df_m1["time"] = pd.to_datetime(df_m1["time"])

print(f"  Período: {df_m5['time'].min()} -> {df_m5['time'].max()}")
print(f"  M5: {len(df_m5):,} velas | M1: {len(df_m1):,} velas")

# Configurar parámetros
params = DEFAULT_PARAMS.copy()
params["target_rr"] = 3.5
params["buffer_points"] = 25
params["require_bos"] = False  # Sin BOS

# Modificar sesión: 2hr antes de NY (11:30) hasta cierre NY (20:00)
# NY original: 13:30-20:00 UTC
# NY extendido: 11:30-20:00 UTC (2hr antes)
params["sessions"] = {
    "new_york": {"start": "11:30", "end": "20:00", "skip_minutes": 0},  # Sin skip
}

print("\n" + "="*80)
print("  EJECUTANDO BACKTEST...")
print("="*80)

bt = OrderBlockBacktesterLimitOrders(params)
df_trades = bt.run(df_m5, df_m1)

# Guardar resultados
output_path = "strategies/order_block/backtest/results/ny_extended_rr35_buf25.csv"
df_trades.to_csv(output_path, index=False)
print(f"\n✅ Trades guardados en: {output_path}")

# Calcular métricas
balance_inicial = params["initial_balance"]
total_pnl = df_trades["pnl_usd"].sum()
balance_final = balance_inicial + total_pnl
retorno_pct = (balance_final - balance_inicial) / balance_inicial * 100

winners = df_trades[df_trades["pnl_usd"] > 0]
losers = df_trades[df_trades["pnl_usd"] <= 0]

win_rate = len(winners) / len(df_trades) * 100 if len(df_trades) > 0 else 0
profit_factor = abs(winners["pnl_usd"].sum() / losers["pnl_usd"].sum()) if len(losers) > 0 and losers["pnl_usd"].sum() != 0 else 0

# Calcular Max DD
df_sorted = df_trades.sort_values("exit_time")
equity = [balance_inicial]
balance = balance_inicial
peak = balance_inicial
max_dd = 0
max_dd_usd = 0
max_dd_date = None

for idx, row in df_sorted.iterrows():
    balance += row["pnl_usd"]
    equity.append(balance)
    
    if balance > peak:
        peak = balance
    
    dd = peak - balance
    dd_pct = (dd / peak) * 100 if peak > 0 else 0
    
    if dd_pct > max_dd:
        max_dd = dd_pct
        max_dd_usd = dd
        max_dd_date = row["exit_time"]

# Período
start_date = df_trades["entry_time"].min()
end_date = df_trades["exit_time"].max()
days = (end_date - start_date).days

print("\n" + "="*80)
print("  RESULTADOS")
print("="*80)

print(f"\n📅 PERÍODO:")
print(f"  Inicio:     {start_date.strftime('%Y-%m-%d')}")
print(f"  Fin:        {end_date.strftime('%Y-%m-%d')}")
print(f"  Duración:   {days} días")

print(f"\n💰 RENTABILIDAD:")
print(f"  Balance inicial:  ${balance_inicial:,.2f}")
print(f"  Balance final:    ${balance_final:,.2f}")
print(f"  Retorno:          {retorno_pct:+.2f}%")

print(f"\n📊 TRADES:")
print(f"  Total:            {len(df_trades)}")
print(f"  Winners:          {len(winners)} ({win_rate:.1f}%)")
print(f"  Losers:           {len(losers)} ({len(losers)/len(df_trades)*100:.1f}%)")

print(f"\n📈 POR DIRECCIÓN:")
df_long = df_trades[df_trades["direction"] == "long"]
df_short = df_trades[df_trades["direction"] == "short"]

print(f"  LONG:             {len(df_long)} trades")
if len(df_long) > 0:
    long_winners = len(df_long[df_long["pnl_usd"] > 0])
    print(f"    Winners:        {long_winners} ({long_winners/len(df_long)*100:.1f}%)")
    print(f"    PnL:            ${df_long['pnl_usd'].sum():,.2f}")

print(f"\n  SHORT:            {len(df_short)} trades")
if len(df_short) > 0:
    short_winners = len(df_short[df_short["pnl_usd"] > 0])
    print(f"    Winners:        {short_winners} ({short_winners/len(df_short)*100:.1f}%)")
    print(f"    PnL:            ${df_short['pnl_usd'].sum():,.2f}")

print(f"\n💵 MÉTRICAS:")
print(f"  PnL total:        ${total_pnl:,.2f}")
print(f"  PnL promedio:     ${df_trades['pnl_usd'].mean():,.2f}")
if len(winners) > 0:
    print(f"  Win avg:          ${winners['pnl_usd'].mean():,.2f}")
if len(losers) > 0:
    print(f"  Loss avg:         ${losers['pnl_usd'].mean():,.2f}")
print(f"  Profit Factor:    {profit_factor:.2f}")

print(f"\n📉 MAX DRAWDOWN:")
print(f"  USD:              ${max_dd_usd:,.2f}")
print(f"  Porcentaje:       {max_dd:.2f}%")
if max_dd_date:
    print(f"  Fecha:            {max_dd_date.strftime('%Y-%m-%d %H:%M')}")

print(f"\n📊 R-MULTIPLES:")
if len(winners) > 0:
    print(f"  Winners promedio: {winners['pnl_r'].mean():.2f}R")
if len(losers) > 0:
    print(f"  Losers promedio:  {losers['pnl_r'].mean():.2f}R")

print(f"\n⏱️  FRECUENCIA:")
print(f"  Trades por día:   {len(df_trades) / days:.2f}")
print(f"  Trades por mes:   {len(df_trades) / (days / 30):.2f}")

print("\n" + "="*80)
print("  COMPARACIÓN CON NY NORMAL")
print("="*80)

print(f"\n{'Métrica':<20} {'NY Normal':<15} {'NY Extendido':<15} {'Diferencia':<15}")
print("-" * 70)
print(f"{'Horario':<20} {'13:30-20:00':<15} {'11:30-20:00':<15} {'+2 horas':<15}")
print(f"{'Trades':<20} {'197':<15} {f'{len(df_trades)}':<15} {f'{len(df_trades)-197:+d}':<15}")
print(f"{'Win Rate':<20} {'29.4%':<15} {f'{win_rate:.1f}%':<15} {f'{win_rate-29.4:+.1f}%':<15}")
print(f"{'Retorno':<20} {'+30.91%':<15} {f'{retorno_pct:+.2f}%':<15} {f'{retorno_pct-30.91:+.2f}%':<15}")
print(f"{'Max DD':<20} {'6.62%':<15} {f'{max_dd:.2f}%':<15} {f'{max_dd-6.62:+.2f}%':<15}")
print(f"{'Profit Factor':<20} {'1.36':<15} {f'{profit_factor:.2f}':<15} {f'{profit_factor-1.36:+.2f}':<15}")

# Analizar trades por hora
print("\n" + "="*80)
print("  ANÁLISIS POR HORA (UTC)")
print("="*80)

df_trades["hour"] = pd.to_datetime(df_trades["entry_time"]).dt.hour

hour_stats = df_trades.groupby("hour").agg({
    "pnl_usd": ["count", "sum", lambda x: (x > 0).sum()]
}).reset_index()
hour_stats.columns = ["hour", "trades", "pnl", "winners"]
hour_stats["win_rate"] = (hour_stats["winners"] / hour_stats["trades"] * 100).round(1)
hour_stats = hour_stats.sort_values("hour")

print(f"\n{'Hora UTC':<12} {'Trades':<10} {'Winners':<10} {'WR %':<10} {'PnL USD':<15}")
print("-" * 60)
for idx, row in hour_stats.iterrows():
    print(f"{int(row['hour']):02d}:00-{int(row['hour'])+1:02d}:00  "
          f"{int(row['trades']):<10} "
          f"{int(row['winners']):<10} "
          f"{row['win_rate']:<10.1f} "
          f"${row['pnl']:>12,.2f}")

# Identificar las 2 horas nuevas (11:00-13:00)
new_hours = df_trades[df_trades["hour"].isin([11, 12])]
if len(new_hours) > 0:
    print(f"\n📊 ANÁLISIS DE LAS 2 HORAS NUEVAS (11:00-13:00 UTC):")
    print(f"  Trades:           {len(new_hours)}")
    new_winners = len(new_hours[new_hours["pnl_usd"] > 0])
    print(f"  Winners:          {new_winners} ({new_winners/len(new_hours)*100:.1f}%)")
    print(f"  PnL:              ${new_hours['pnl_usd'].sum():,.2f}")
    print(f"  Contribución:     {new_hours['pnl_usd'].sum()/total_pnl*100:.1f}% del total")

print("\n" + "="*80)
print("  CONCLUSIÓN")
print("="*80)

if retorno_pct > 30.91:
    print(f"\n  ✅ NY EXTENDIDO ES MEJOR:")
    print(f"     Retorno: {retorno_pct:+.2f}% vs +30.91%")
    print(f"     Diferencia: {retorno_pct-30.91:+.2f}%")
elif retorno_pct < 30.91:
    print(f"\n  ❌ NY NORMAL ES MEJOR:")
    print(f"     Retorno: {retorno_pct:+.2f}% vs +30.91%")
    print(f"     Diferencia: {retorno_pct-30.91:+.2f}%")
else:
    print(f"\n  ⚖️  RESULTADOS SIMILARES")

if max_dd < 6.62:
    print(f"  ✅ Menor Max DD: {max_dd:.2f}% vs 6.62%")
elif max_dd > 6.62:
    print(f"  ⚠️  Mayor Max DD: {max_dd:.2f}% vs 6.62%")

print("\n" + "="*80)
