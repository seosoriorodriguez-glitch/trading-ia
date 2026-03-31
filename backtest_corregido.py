# -*- coding: utf-8 -*-
"""
Re-ejecutar backtest con el bug SL/TP corregido
"""
import sys
import codecs
if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd
from strategies.order_block.backtest.backtester import OrderBlockBacktester
from strategies.order_block.backtest.config import DEFAULT_PARAMS

print("\n" + "="*80)
print("  BACKTEST CON BUG CORREGIDO - NY ONLY")
print("="*80)

# Cargar datos (mismos que el backtest original)
print("\nCargando datos...")
from strategies.order_block.backtest.data_loader import load_csv

M5_FILE = "data/US30_cash_M5_260d.csv"
M1_FILE = "data/US30_cash_M1_260d.csv"

df_m5 = load_csv(M5_FILE)
df_m1 = load_csv(M1_FILE)

# Alinear períodos
start = max(df_m5["time"].iloc[0], df_m1["time"].iloc[0])
end   = min(df_m5["time"].iloc[-1], df_m1["time"].iloc[-1])
df_m5 = df_m5[(df_m5["time"] >= start) & (df_m5["time"] <= end)].reset_index(drop=True)
df_m1 = df_m1[(df_m1["time"] >= start) & (df_m1["time"] <= end)].reset_index(drop=True)

print(f"  Período: {start} -> {end}")
print(f"  M5: {len(df_m5):,} velas | M1: {len(df_m1):,} velas")

# Configuración NY-only
params = DEFAULT_PARAMS.copy()
params["sessions"] = {
    "new_york": {"start": "13:30", "end": "20:00", "skip_minutes": 15}
}

print("\n" + "="*80)
print("  EJECUTANDO BACKTEST...")
print("="*80)

bt = OrderBlockBacktester(params)
df_trades = bt.run(df_m5, df_m1)

if df_trades.empty:
    print("\n❌ No se generaron trades")
    sys.exit(1)

# Guardar resultados
output_dir = Path("strategies/order_block/backtest/results")
output_dir.mkdir(parents=True, exist_ok=True)

all_trades_file = output_dir / "ny_all_trades_CORREGIDO.csv"
df_trades.to_csv(all_trades_file, index=False)
print(f"\n✅ Trades guardados en: {all_trades_file}")

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

# Verificar SL/TP en SHORT
if len(df_short) > 0:
    print(f"\n" + "="*80)
    print("  VERIFICACIÓN SL/TP EN TRADES SHORT")
    print("="*80)

    errors = 0
    for idx, row in df_short.iterrows():
        entry = row['entry_price']
        sl = row['sl']
        tp = row['tp']
        
        # Para SHORT: SL debe estar ARRIBA, TP DEBAJO
        sl_correcto = sl > entry
        tp_correcto = tp < entry
        
        if not sl_correcto or not tp_correcto:
            errors += 1

    print(f"\n  Total SHORT:      {len(df_short)}")
    print(f"  SL/TP correctos:  {len(df_short) - errors} ({(len(df_short)-errors)/len(df_short)*100:.1f}%)")
    print(f"  SL/TP invertidos: {errors} ({errors/len(df_short)*100:.1f}%)")

    if errors == 0:
        print(f"\n  ✅ TODOS los trades SHORT tienen SL/TP correctos!")
    else:
        print(f"\n  ❌ Todavía hay {errors} trades SHORT con SL/TP invertidos")

    # Mostrar algunos ejemplos de SHORT
    print(f"\n" + "="*80)
    print("  EJEMPLOS DE TRADES SHORT (primeros 5)")
    print("="*80)

    for idx, (i, row) in enumerate(df_short.head(5).iterrows(), 1):
        print(f"\n  Trade #{idx}:")
        print(f"    Entry:     {row['entry_price']:.2f}")
        print(f"    SL:        {row['sl']:.2f} ({'✅ arriba' if row['sl'] > row['entry_price'] else '❌ debajo'})")
        print(f"    TP:        {row['tp']:.2f} ({'✅ debajo' if row['tp'] < row['entry_price'] else '❌ arriba'})")
        print(f"    Exit:      {row['exit_price']:.2f}")
        print(f"    Reason:    {row['exit_reason']}")
        print(f"    PnL:       ${row['pnl_usd']:.2f}")
        print(f"    R:         {row['pnl_r']:.2f}R")
else:
    print(f"\n" + "="*80)
    print("  ⚠️  NO SE GENERARON TRADES SHORT")
    print("="*80)
    print(f"\n  Posibles razones:")
    print(f"  1. La corrección del SL/TP hace que los SHORT no pasen los filtros de riesgo")
    print(f"  2. El período de datos es diferente al backtest anterior")
    print(f"  3. Los OBs bearish no generaron señales válidas")

print("\n" + "="*80)
print("  COMPARACIÓN CON BACKTEST ANTERIOR")
print("="*80)

# Cargar backtest anterior
try:
    df_old = pd.read_csv("strategies/order_block/backtest/results/ny_all_trades.csv")
    
    old_ret = (df_old["balance"].iloc[-1] - initial) / initial * 100
    old_total = len(df_old)
    old_wr = len(df_old[df_old["pnl_usd"] > 0]) / len(df_old) * 100
    old_pnl = df_old["pnl_usd"].sum()
    
    print(f"\n  BACKTEST ANTERIOR (con bug):")
    print(f"    Retorno:      {old_ret:+.2f}%")
    print(f"    Total trades: {old_total}")
    print(f"    Win Rate:     {old_wr:.1f}%")
    print(f"    PnL total:    ${old_pnl:,.2f}")
    
    print(f"\n  BACKTEST CORREGIDO:")
    print(f"    Retorno:      {ret:+.2f}%")
    print(f"    Total trades: {len(df_trades)}")
    print(f"    Win Rate:     {len(df_winners)/len(df_trades)*100:.1f}%")
    print(f"    PnL total:    ${df_trades['pnl_usd'].sum():,.2f}")
    
    print(f"\n  DIFERENCIA:")
    print(f"    Retorno:      {ret - old_ret:+.2f}%")
    print(f"    Total trades: {len(df_trades) - old_total:+d}")
    print(f"    Win Rate:     {len(df_winners)/len(df_trades)*100 - old_wr:+.1f}%")
    print(f"    PnL total:    ${df_trades['pnl_usd'].sum() - old_pnl:+,.2f}")
    
except FileNotFoundError:
    print("\n  ⚠️  No se encontró el backtest anterior para comparar")

print("\n" + "="*80)
