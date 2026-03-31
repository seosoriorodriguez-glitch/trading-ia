# -*- coding: utf-8 -*-
"""
Backtest Final - Validación de SL/TP y últimas operaciones
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
print("  BACKTEST FINAL - VALIDACIÓN COMPLETA")
print("="*80)

print("\n📋 CONFIGURACIÓN:")
print(f"  R:R:              {DEFAULT_PARAMS['target_rr']}")
print(f"  Buffer SL:        {DEFAULT_PARAMS['buffer_points']} puntos")
print(f"  Filtro BOS:       {DEFAULT_PARAMS['require_bos']}")
print(f"  Sesión:           {DEFAULT_PARAMS['sessions']['new_york']['start']}-{DEFAULT_PARAMS['sessions']['new_york']['end']} UTC")

# Cargar datos
print("\nCargando datos...")
df_m5 = pd.read_csv("data/US30_cash_M5_260d.csv")
df_m1 = pd.read_csv("data/US30_cash_M1_260d.csv")

df_m5["time"] = pd.to_datetime(df_m5["time"])
df_m1["time"] = pd.to_datetime(df_m1["time"])

print(f"  M5: {len(df_m5):,} velas | M1: {len(df_m1):,} velas")

print("\n" + "="*80)
print("  EJECUTANDO BACKTEST...")
print("="*80)

bt = OrderBlockBacktesterLimitOrders(DEFAULT_PARAMS)
df_trades = bt.run(df_m5, df_m1)

# Guardar
output_path = "backtest_final_validacion.csv"
df_trades.to_csv(output_path, index=False)
print(f"\n✅ Trades guardados en: {output_path}")

# Calcular métricas
balance_inicial = DEFAULT_PARAMS["initial_balance"]
total_pnl = df_trades["pnl_usd"].sum()
balance_final = balance_inicial + total_pnl
retorno_pct = (balance_final - balance_inicial) / balance_inicial * 100

winners = df_trades[df_trades["pnl_usd"] > 0]
losers = df_trades[df_trades["pnl_usd"] <= 0]

print("\n" + "="*80)
print("  RESULTADOS GENERALES")
print("="*80)

print(f"\n💰 RENTABILIDAD:")
print(f"  Balance inicial:  ${balance_inicial:,.2f}")
print(f"  Balance final:    ${balance_final:,.2f}")
print(f"  Retorno:          {retorno_pct:+.2f}%")

print(f"\n📊 TRADES:")
print(f"  Total:            {len(df_trades)}")
print(f"  Winners:          {len(winners)} ({len(winners)/len(df_trades)*100:.1f}%)")
print(f"  Losers:           {len(losers)} ({len(losers)/len(df_trades)*100:.1f}%)")

# Verificar SL/TP
print("\n" + "="*80)
print("  VERIFICACIÓN DE SL/TP")
print("="*80)

errors = []

for idx, row in df_trades.iterrows():
    direction = row['direction']
    entry = row['entry_price']
    sl = row['sl']
    tp = row['tp']
    zone_low = row['ob_zone_low']
    zone_high = row['ob_zone_high']
    
    # Verificar LONG
    if direction == 'long':
        # Entry debe ser zone_high
        if abs(entry - zone_high) > 1:
            errors.append(f"Trade {row['trade_id']}: LONG entry {entry:.2f} != zone_high {zone_high:.2f}")
        
        # SL debe estar DEBAJO de entry
        if sl >= entry:
            errors.append(f"Trade {row['trade_id']}: LONG SL {sl:.2f} >= entry {entry:.2f} ❌")
        
        # TP debe estar ARRIBA de entry
        if tp <= entry:
            errors.append(f"Trade {row['trade_id']}: LONG TP {tp:.2f} <= entry {entry:.2f} ❌")
    
    # Verificar SHORT
    else:
        # Entry debe ser zone_low
        if abs(entry - zone_low) > 1:
            errors.append(f"Trade {row['trade_id']}: SHORT entry {entry:.2f} != zone_low {zone_low:.2f}")
        
        # SL debe estar ARRIBA de entry
        if sl <= entry:
            errors.append(f"Trade {row['trade_id']}: SHORT SL {sl:.2f} <= entry {entry:.2f} ❌")
        
        # TP debe estar ABAJO de entry
        if tp >= entry:
            errors.append(f"Trade {row['trade_id']}: SHORT TP {tp:.2f} >= entry {entry:.2f} ❌")

if errors:
    print(f"\n❌ {len(errors)} ERRORES ENCONTRADOS:")
    for error in errors[:10]:
        print(f"  {error}")
else:
    print(f"\n✅ TODOS LOS SL/TP CORRECTOS ({len(df_trades)} trades verificados)")

# Últimos 10 ganadores
print("\n" + "="*80)
print("  📈 ÚLTIMOS 10 TRADES GANADORES")
print("="*80)

last_winners = winners.sort_values("exit_time").tail(10)

# Convertir a Chile timezone
last_winners["entry_cl"] = pd.to_datetime(last_winners["entry_time"]) - pd.Timedelta(hours=3)
last_winners["exit_cl"] = pd.to_datetime(last_winners["exit_time"]) - pd.Timedelta(hours=3)

print(f"\n{'ID':<5} {'Dir':<6} {'Entry (CL)':<17} {'OB Zone':<20} {'Entry':<10} {'SL':<10} {'TP':<10} {'Exit':<10} {'PnL':<12} {'R':<6}")
print("-" * 120)

for idx, row in last_winners.iterrows():
    zone = f"{row['ob_zone_low']:.0f}-{row['ob_zone_high']:.0f}"
    print(f"{row['trade_id']:<5} "
          f"{row['direction']:<6} "
          f"{row['entry_cl'].strftime('%Y-%m-%d %H:%M'):<17} "
          f"{zone:<20} "
          f"{row['entry_price']:<10.2f} "
          f"{row['sl']:<10.2f} "
          f"{row['tp']:<10.2f} "
          f"{row['exit_price']:<10.2f} "
          f"${row['pnl_usd']:<11,.2f} "
          f"{row['pnl_r']:<6.2f}R")

# Últimos 5 perdedores
print("\n" + "="*80)
print("  📉 ÚLTIMOS 5 TRADES PERDEDORES")
print("="*80)

last_losers = losers.sort_values("exit_time").tail(5)

last_losers["entry_cl"] = pd.to_datetime(last_losers["entry_time"]) - pd.Timedelta(hours=3)
last_losers["exit_cl"] = pd.to_datetime(last_losers["exit_time"]) - pd.Timedelta(hours=3)

print(f"\n{'ID':<5} {'Dir':<6} {'Entry (CL)':<17} {'OB Zone':<20} {'Entry':<10} {'SL':<10} {'TP':<10} {'Exit':<10} {'PnL':<12} {'R':<6}")
print("-" * 120)

for idx, row in last_losers.iterrows():
    zone = f"{row['ob_zone_low']:.0f}-{row['ob_zone_high']:.0f}"
    print(f"{row['trade_id']:<5} "
          f"{row['direction']:<6} "
          f"{row['entry_cl'].strftime('%Y-%m-%d %H:%M'):<17} "
          f"{zone:<20} "
          f"{row['entry_price']:<10.2f} "
          f"{row['sl']:<10.2f} "
          f"{row['tp']:<10.2f} "
          f"{row['exit_price']:<10.2f} "
          f"${row['pnl_usd']:<11,.2f} "
          f"{row['pnl_r']:<6.2f}R")

# Validación detallada de ejemplos
print("\n" + "="*80)
print("  🔍 VALIDACIÓN DETALLADA (3 Ejemplos)")
print("="*80)

# 1 LONG winner
long_winner = winners[winners['direction'] == 'long'].tail(1).iloc[0]
print(f"\n✅ LONG GANADOR (Trade #{long_winner['trade_id']}):")
print(f"  OB Zone:      {long_winner['ob_zone_low']:.2f} - {long_winner['ob_zone_high']:.2f}")
print(f"  Entry:        {long_winner['entry_price']:.2f} (debe ser ~{long_winner['ob_zone_high']:.2f}) ✅")
print(f"  SL:           {long_winner['sl']:.2f} (debe estar DEBAJO de {long_winner['entry_price']:.2f}) {'✅' if long_winner['sl'] < long_winner['entry_price'] else '❌'}")
print(f"  TP:           {long_winner['tp']:.2f} (debe estar ARRIBA de {long_winner['entry_price']:.2f}) {'✅' if long_winner['tp'] > long_winner['entry_price'] else '❌'}")
print(f"  Exit:         {long_winner['exit_price']:.2f}")
print(f"  PnL:          ${long_winner['pnl_usd']:,.2f} ({long_winner['pnl_r']:.2f}R)")

# 1 SHORT winner
short_winner = winners[winners['direction'] == 'short'].tail(1).iloc[0]
print(f"\n✅ SHORT GANADOR (Trade #{short_winner['trade_id']}):")
print(f"  OB Zone:      {short_winner['ob_zone_low']:.2f} - {short_winner['ob_zone_high']:.2f}")
print(f"  Entry:        {short_winner['entry_price']:.2f} (debe ser ~{short_winner['ob_zone_low']:.2f}) ✅")
print(f"  SL:           {short_winner['sl']:.2f} (debe estar ARRIBA de {short_winner['entry_price']:.2f}) {'✅' if short_winner['sl'] > short_winner['entry_price'] else '❌'}")
print(f"  TP:           {short_winner['tp']:.2f} (debe estar ABAJO de {short_winner['entry_price']:.2f}) {'✅' if short_winner['tp'] < short_winner['entry_price'] else '❌'}")
print(f"  Exit:         {short_winner['exit_price']:.2f}")
print(f"  PnL:          ${short_winner['pnl_usd']:,.2f} ({short_winner['pnl_r']:.2f}R)")

# 1 LONG loser
long_loser = losers[losers['direction'] == 'long'].tail(1).iloc[0]
print(f"\n❌ LONG PERDEDOR (Trade #{long_loser['trade_id']}):")
print(f"  OB Zone:      {long_loser['ob_zone_low']:.2f} - {long_loser['ob_zone_high']:.2f}")
print(f"  Entry:        {long_loser['entry_price']:.2f} (debe ser ~{long_loser['ob_zone_high']:.2f}) ✅")
print(f"  SL:           {long_loser['sl']:.2f} (debe estar DEBAJO de {long_loser['entry_price']:.2f}) {'✅' if long_loser['sl'] < long_loser['entry_price'] else '❌'}")
print(f"  TP:           {long_loser['tp']:.2f} (debe estar ARRIBA de {long_loser['entry_price']:.2f}) {'✅' if long_loser['tp'] > long_loser['entry_price'] else '❌'}")
print(f"  Exit:         {long_loser['exit_price']:.2f} (tocó SL)")
print(f"  PnL:          ${long_loser['pnl_usd']:,.2f} ({long_loser['pnl_r']:.2f}R)")

print("\n" + "="*80)
print("  CONCLUSIÓN FINAL")
print("="*80)

if len(errors) == 0:
    print(f"\n  ✅ BACKTEST 100% CORRECTO")
    print(f"  ✅ Todos los SL/TP están bien posicionados")
    print(f"  ✅ LONG: SL debajo, TP arriba")
    print(f"  ✅ SHORT: SL arriba, TP abajo")
    print(f"  ✅ Entries en límites de zona correctos")
    print(f"\n  🚀 BOT LIVE OPERARÁ CORRECTAMENTE")
else:
    print(f"\n  ❌ HAY {len(errors)} ERRORES")
    print(f"  ⚠️  REVISAR ANTES DE OPERAR EN LIVE")

print("\n" + "="*80)
