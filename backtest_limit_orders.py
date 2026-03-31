# -*- coding: utf-8 -*-
"""
Backtest con ÓRDENES LIMIT en límites de zona OB
"""
import sys
import codecs
if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd
from strategies.order_block.backtest.backtester_limit_orders import OrderBlockBacktesterLimitOrders
from strategies.order_block.backtest.config import DEFAULT_PARAMS
from strategies.order_block.backtest.data_loader import load_csv

print("\n" + "="*80)
print("  BACKTEST CON ÓRDENES LIMIT - NY ONLY")
print("="*80)

print("\n📋 LÓGICA:")
print("  • Vela M1 cierra DENTRO de zona OB")
print("  • LONG: Orden LIMIT en zone_high")
print("  • SHORT: Orden LIMIT en zone_low")
print("  • Orden vive hasta que OB se destruya/expire")

# Cargar datos
print("\nCargando datos...")
df_m5 = load_csv("data/US30_cash_M5_260d.csv")
df_m1 = load_csv("data/US30_cash_M1_260d.csv")

start = max(df_m5["time"].iloc[0], df_m1["time"].iloc[0])
end   = min(df_m5["time"].iloc[-1], df_m1["time"].iloc[-1])
df_m5 = df_m5[(df_m5["time"] >= start) & (df_m5["time"] <= end)].reset_index(drop=True)
df_m1 = df_m1[(df_m1["time"] >= start) & (df_m1["time"] <= end)].reset_index(drop=True)

print(f"  Período: {start} -> {end}")
print(f"  M5: {len(df_m5):,} velas | M1: {len(df_m1):,} velas")

# Configuración
params = DEFAULT_PARAMS.copy()
params["sessions"] = {
    "new_york": {"start": "13:30", "end": "20:00", "skip_minutes": 15}
}

print("\n" + "="*80)
print("  EJECUTANDO BACKTEST...")
print("="*80)

bt = OrderBlockBacktesterLimitOrders(params)
df_trades = bt.run(df_m5, df_m1)

if df_trades.empty:
    print("\n❌ No se generaron trades")
    sys.exit(1)

# Guardar resultados
output_dir = Path("strategies/order_block/backtest/results")
output_dir.mkdir(parents=True, exist_ok=True)

trades_file = output_dir / "ny_trades_LIMIT_ORDERS.csv"
df_trades.to_csv(trades_file, index=False)
print(f"\n✅ Trades guardados en: {trades_file}")

# Análisis
df_winners = df_trades[df_trades["pnl_usd"] > 0]
df_losers = df_trades[df_trades["pnl_usd"] <= 0]

df_long = df_trades[df_trades["direction"] == "long"]
df_short = df_trades[df_trades["direction"] == "short"]

df_long_winners = df_long[df_long["pnl_usd"] > 0]
df_short_winners = df_short[df_short["pnl_usd"] > 0]

print("\n" + "="*80)
print("  RESULTADOS")
print("="*80)

initial = params["initial_balance"]
final = df_trades["balance"].iloc[-1]
ret = (final - initial) / initial * 100

print(f"\n💰 RENTABILIDAD:")
print(f"  Balance inicial:  ${initial:,.2f}")
print(f"  Balance final:    ${final:,.2f}")
print(f"  Retorno:          {ret:+.2f}%")

print(f"\n📊 TRADES:")
print(f"  Total:            {len(df_trades)}")
print(f"  Winners:          {len(df_winners)} ({len(df_winners)/len(df_trades)*100:.1f}%)")
print(f"  Losers:           {len(df_losers)} ({len(df_losers)/len(df_trades)*100:.1f}%)")

print(f"\n📈 POR DIRECCIÓN:")
print(f"  LONG:             {len(df_long)} trades")
if len(df_long) > 0:
    print(f"    Winners:        {len(df_long_winners)} ({len(df_long_winners)/len(df_long)*100:.1f}%)")
    print(f"    PnL:            ${df_long['pnl_usd'].sum():,.2f}")

print(f"\n  SHORT:            {len(df_short)} trades")
if len(df_short) > 0:
    print(f"    Winners:        {len(df_short_winners)} ({len(df_short_winners)/len(df_short)*100:.1f}%)")
    print(f"    PnL:            ${df_short['pnl_usd'].sum():,.2f}")
else:
    print(f"    ⚠️  No se generaron trades SHORT")

print(f"\n💵 MÉTRICAS:")
print(f"  PnL total:        ${df_trades['pnl_usd'].sum():,.2f}")
print(f"  PnL promedio:     ${df_trades['pnl_usd'].mean():,.2f}")
print(f"  Win avg:          ${df_winners['pnl_usd'].mean():,.2f}")
print(f"  Loss avg:         ${df_losers['pnl_usd'].mean():,.2f}")

if len(df_losers) > 0:
    pf = abs(df_winners['pnl_usd'].sum() / df_losers['pnl_usd'].sum())
    print(f"  Profit Factor:    {pf:.2f}")

print(f"\n📊 R-MULTIPLES:")
print(f"  Winners promedio: {df_winners['pnl_r'].mean():.2f}R")
print(f"  Losers promedio:  {df_losers['pnl_r'].mean():.2f}R")
if len(df_long_winners) > 0:
    print(f"  LONG winners:     {df_long_winners['pnl_r'].mean():.2f}R")
if len(df_short_winners) > 0:
    print(f"  SHORT winners:    {df_short_winners['pnl_r'].mean():.2f}R")

# Verificar entradas dentro de zona
print(f"\n" + "="*80)
print("  VERIFICACIÓN: Entradas dentro de zona")
print("="*80)

# Para LONG: entry debe ser zone_high
long_correct = 0
for idx, row in df_long.iterrows():
    if abs(row['entry_price'] - row['ob_zone_high']) < 0.1:
        long_correct += 1

# Para SHORT: entry debe ser zone_low
short_correct = 0
for idx, row in df_short.iterrows():
    if abs(row['entry_price'] - row['ob_zone_low']) < 0.1:
        short_correct += 1

if len(df_long) > 0:
    print(f"\n  LONG:")
    print(f"    Entry en zone_high: {long_correct}/{len(df_long)} ({long_correct/len(df_long)*100:.1f}%)")

if len(df_short) > 0:
    print(f"\n  SHORT:")
    print(f"    Entry en zone_low:  {short_correct}/{len(df_short)} ({short_correct/len(df_short)*100:.1f}%)")

# Comparación con backtest anterior
print("\n" + "="*80)
print("  COMPARACIÓN CON BACKTESTS ANTERIORES")
print("="*80)

try:
    df_old = pd.read_csv("strategies/order_block/backtest/results/ny_all_trades.csv")
    old_ret = (df_old["balance"].iloc[-1] - initial) / initial * 100
    
    df_corr = pd.read_csv("strategies/order_block/backtest/results/ny_all_trades_CORREGIDO.csv")
    corr_ret = (df_corr["balance"].iloc[-1] - initial) / initial * 100
    
    print(f"\n  BACKTEST ORIGINAL (con bug SL/TP):")
    print(f"    Retorno:      {old_ret:+.2f}%")
    print(f"    Total trades: {len(df_old)}")
    print(f"    Win Rate:     {len(df_old[df_old['pnl_usd'] > 0])/len(df_old)*100:.1f}%")
    
    print(f"\n  BACKTEST CORREGIDO (bug SL/TP fixed):")
    print(f"    Retorno:      {corr_ret:+.2f}%")
    print(f"    Total trades: {len(df_corr)}")
    print(f"    Win Rate:     {len(df_corr[df_corr['pnl_usd'] > 0])/len(df_corr)*100:.1f}%")
    
    print(f"\n  BACKTEST LIMIT ORDERS (nueva lógica):")
    print(f"    Retorno:      {ret:+.2f}%")
    print(f"    Total trades: {len(df_trades)}")
    print(f"    Win Rate:     {len(df_winners)/len(df_trades)*100:.1f}%")
    
    print(f"\n  📊 DIFERENCIAS:")
    print(f"    vs Original:   {ret - old_ret:+.2f}%")
    print(f"    vs Corregido:  {ret - corr_ret:+.2f}%")
    
except FileNotFoundError:
    print("\n  ⚠️  No se encontraron backtests anteriores para comparar")

print("\n" + "="*80)
