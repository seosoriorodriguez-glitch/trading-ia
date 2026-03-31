# -*- coding: utf-8 -*-
"""
Backtest LIMIT sin filtro BOS
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
print("  BACKTEST CON ÓRDENES LIMIT - SIN FILTRO BOS")
print("="*80)

print("\n📋 LÓGICA:")
print("  • Vela M1 cierra DENTRO de zona OB")
print("  • LONG: Orden LIMIT en zone_high")
print("  • SHORT: Orden LIMIT en zone_low")
print("  • ❌ SIN filtro BOS")
print("  • Orden vive hasta que OB se destruya/expire")

# Cargar datos
print("\nCargando datos...")
df_m5 = pd.read_csv("data/US30_cash_M5_260d.csv")
df_m1 = pd.read_csv("data/US30_cash_M1_260d.csv")

df_m5["time"] = pd.to_datetime(df_m5["time"])
df_m1["time"] = pd.to_datetime(df_m1["time"])

print(f"  Período: {df_m5['time'].min()} -> {df_m5['time'].max()}")
print(f"  M5: {len(df_m5):,} velas | M1: {len(df_m1):,} velas")

# Modificar params para desactivar BOS
params = DEFAULT_PARAMS.copy()
params["require_bos"] = False  # ❌ DESACTIVAR BOS

print("\n" + "="*80)
print("  EJECUTANDO BACKTEST...")
print("="*80)

bt = OrderBlockBacktesterLimitOrders(params)
df_trades = bt.run(df_m5, df_m1)

# Guardar
output_path = "strategies/order_block/backtest/results/ny_trades_LIMIT_SIN_BOS.csv"
df_trades.to_csv(output_path, index=False)
print(f"\n✅ Trades guardados en: {output_path}")

# Resultados
print("\n" + "="*80)
print("  RESULTADOS")
print("="*80)

balance_inicial = params["initial_balance"]
balance_final = balance_inicial + df_trades["pnl_usd"].sum()
retorno_pct = (balance_final - balance_inicial) / balance_inicial * 100

print(f"\n💰 RENTABILIDAD:")
print(f"  Balance inicial:  ${balance_inicial:,.2f}")
print(f"  Balance final:    ${balance_final:,.2f}")
print(f"  Retorno:          {retorno_pct:+.2f}%")

print(f"\n📊 TRADES:")
print(f"  Total:            {len(df_trades)}")
winners = df_trades[df_trades["pnl_usd"] > 0]
losers = df_trades[df_trades["pnl_usd"] <= 0]
print(f"  Winners:          {len(winners)} ({len(winners)/len(df_trades)*100:.1f}%)")
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
print(f"  PnL total:        ${df_trades['pnl_usd'].sum():,.2f}")
print(f"  PnL promedio:     ${df_trades['pnl_usd'].mean():,.2f}")
if len(winners) > 0:
    print(f"  Win avg:          ${winners['pnl_usd'].mean():,.2f}")
if len(losers) > 0:
    print(f"  Loss avg:         ${losers['pnl_usd'].mean():,.2f}")

if len(winners) > 0 and len(losers) > 0:
    pf = abs(winners["pnl_usd"].sum() / losers["pnl_usd"].sum())
    print(f"  Profit Factor:    {pf:.2f}")

print(f"\n📊 R-MULTIPLES:")
if len(winners) > 0:
    print(f"  Winners promedio: {winners['pnl_r'].mean():.2f}R")
if len(losers) > 0:
    print(f"  Losers promedio:  {losers['pnl_r'].mean():.2f}R")
if len(df_long[df_long["pnl_usd"] > 0]) > 0:
    print(f"  LONG winners:     {df_long[df_long['pnl_usd'] > 0]['pnl_r'].mean():.2f}R")
if len(df_short[df_short["pnl_usd"] > 0]) > 0:
    print(f"  SHORT winners:    {df_short[df_short['pnl_usd'] > 0]['pnl_r'].mean():.2f}R")

print("\n" + "="*80)
