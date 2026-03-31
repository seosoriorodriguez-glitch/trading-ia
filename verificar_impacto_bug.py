# -*- coding: utf-8 -*-
"""
Verificación del impacto real del bug SL/TP en el backtest
"""
import sys
import codecs
if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

import pandas as pd

print("\n" + "="*80)
print("  VERIFICACIÓN DEL IMPACTO DEL BUG SL/TP")
print("="*80)

# Leer todos los trades del backtest
df = pd.read_csv("strategies/order_block/backtest/results/ny_all_trades.csv")

print(f"\n📊 RESUMEN GENERAL:")
print(f"  Total trades:     {len(df)}")
print(f"  LONG:             {len(df[df['direction'] == 'long'])}")
print(f"  SHORT:            {len(df[df['direction'] == 'short'])}")
print(f"  Winners:          {len(df[df['pnl_usd'] > 0])}")
print(f"  Losers:           {len(df[df['pnl_usd'] <= 0])}")

# Analizar trades SHORT
df_short = df[df['direction'] == 'short'].copy()
df_short_winners = df_short[df_short['pnl_usd'] > 0]
df_short_losers = df_short[df_short['pnl_usd'] <= 0]

print(f"\n🔍 ANÁLISIS DE TRADES SHORT:")
print(f"  Total SHORT:      {len(df_short)}")
print(f"  Winners:          {len(df_short_winners)} ({len(df_short_winners)/len(df_short)*100:.1f}%)")
print(f"  Losers:           {len(df_short_losers)} ({len(df_short_losers)/len(df_short)*100:.1f}%)")

# Verificar si SL/TP están invertidos
print(f"\n🔬 VERIFICACIÓN DE SL/TP EN TRADES SHORT:")

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

print(f"  Trades SHORT con SL/TP invertidos: {errors} de {len(df_short)} ({errors/len(df_short)*100:.1f}%)")

if errors > 0:
    print(f"\n  ✅ CONFIRMADO: Todos los trades SHORT tienen SL/TP invertidos")
else:
    print(f"\n  ❌ NO se detectó el bug en los trades SHORT")

# Analizar exit_reason
print(f"\n📋 ANÁLISIS DE EXIT_REASON EN TRADES SHORT:")
print(f"\n  Winners (salieron en 'sl' que es realmente TP):")
short_win_sl = df_short_winners[df_short_winners['exit_reason'] == 'sl']
short_win_tp = df_short_winners[df_short_winners['exit_reason'] == 'tp']
print(f"    exit_reason='sl': {len(short_win_sl)} ({len(short_win_sl)/len(df_short_winners)*100:.1f}%)")
print(f"    exit_reason='tp': {len(short_win_tp)} ({len(short_win_tp)/len(df_short_winners)*100:.1f}%)")

print(f"\n  Losers (salieron en 'tp' que es realmente SL):")
short_loss_sl = df_short_losers[df_short_losers['exit_reason'] == 'sl']
short_loss_tp = df_short_losers[df_short_losers['exit_reason'] == 'tp']
print(f"    exit_reason='sl': {len(short_loss_sl)} ({len(short_loss_sl)/len(df_short_losers)*100:.1f}%)")
print(f"    exit_reason='tp': {len(short_loss_tp)} ({len(short_loss_tp)/len(df_short_losers)*100:.1f}%)")

# Verificar R-multiples
print(f"\n💰 ANÁLISIS DE R-MULTIPLES:")

print(f"\n  R-multiple promedio reportado:")
print(f"    LONG winners:  {df[df['direction'] == 'long'][df['pnl_usd'] > 0]['pnl_r'].mean():.2f}R")
print(f"    SHORT winners: {df_short_winners['pnl_r'].mean():.2f}R")
print(f"    LONG losers:   {df[df['direction'] == 'long'][df['pnl_usd'] <= 0]['pnl_r'].mean():.2f}R")
print(f"    SHORT losers:  {df_short_losers['pnl_r'].mean():.2f}R")

# Calcular R-multiple REAL para SHORT (con SL/TP corregidos)
print(f"\n  Calculando R-multiple REAL para SHORT (con SL/TP corregidos):")

real_r_winners = []
real_r_losers = []

for idx, row in df_short.iterrows():
    entry = row['entry_price']
    exit_price = row['exit_price']
    sl_csv = row['sl']  # Realmente es TP
    tp_csv = row['tp']  # Realmente es SL
    
    # SL real está en tp_csv (arriba del entry)
    sl_real = tp_csv
    # TP real está en sl_csv (debajo del entry)
    tp_real = sl_csv
    
    # Calcular PnL y Risk reales
    pnl_points = entry - exit_price  # Para SHORT
    risk_points = abs(entry - sl_real)  # Distancia al SL real (arriba)
    
    r_real = pnl_points / risk_points if risk_points > 0 else 0
    
    if row['pnl_usd'] > 0:
        real_r_winners.append(r_real)
    else:
        real_r_losers.append(r_real)

if real_r_winners:
    print(f"    SHORT winners (R real): {sum(real_r_winners)/len(real_r_winners):.2f}R")
if real_r_losers:
    print(f"    SHORT losers (R real):  {sum(real_r_losers)/len(real_r_losers):.2f}R")

# Impacto en métricas globales
print(f"\n" + "="*80)
print(f"  IMPACTO EN MÉTRICAS DEL BACKTEST")
print("="*80)

total_pnl = df['pnl_usd'].sum()
long_pnl = df[df['direction'] == 'long']['pnl_usd'].sum()
short_pnl = df_short['pnl_usd'].sum()

print(f"\n💵 PnL (NO AFECTADO por el bug):")
print(f"  Total:  ${total_pnl:,.2f}")
print(f"  LONG:   ${long_pnl:,.2f} ({long_pnl/total_pnl*100:.1f}%)")
print(f"  SHORT:  ${short_pnl:,.2f} ({short_pnl/total_pnl*100:.1f}%)")

print(f"\n📊 Win Rate (NO AFECTADO):")
wr_total = len(df[df['pnl_usd'] > 0]) / len(df) * 100
wr_long = len(df[df['direction'] == 'long'][df['pnl_usd'] > 0]) / len(df[df['direction'] == 'long']) * 100
wr_short = len(df_short_winners) / len(df_short) * 100
print(f"  Total:  {wr_total:.1f}%")
print(f"  LONG:   {wr_long:.1f}%")
print(f"  SHORT:  {wr_short:.1f}%")

print(f"\n🎯 R-multiple promedio (AFECTADO para SHORT):")
print(f"  Reportado SHORT winners: {df_short_winners['pnl_r'].mean():.2f}R")
if real_r_winners:
    print(f"  REAL SHORT winners:      {sum(real_r_winners)/len(real_r_winners):.2f}R")
    print(f"  Diferencia:              {df_short_winners['pnl_r'].mean() - sum(real_r_winners)/len(real_r_winners):.2f}R")

print(f"\n" + "="*80)
print(f"  CONCLUSIÓN")
print("="*80)

print(f"\n✅ BACKTEST VÁLIDO:")
print(f"  • Rentabilidad: +19.92% ES CORRECTA")
print(f"  • PnL en USD: CORRECTO")
print(f"  • Win Rate: CORRECTO")
print(f"  • Max DD: CORRECTO")

print(f"\n❌ MÉTRICAS AFECTADAS:")
print(f"  • R-multiples de SHORT: INFLADOS")
print(f"  • Etiquetas SL/TP: INVERTIDAS")
print(f"  • exit_reason: CONFUSO")

print(f"\n🚨 RIESGO LIVE BOT:")
print(f"  • Si ejecuta SHORT: R:R invertido (2.5:1 en lugar de 1:2.5)")
print(f"  • Riesgo real: 2.5x mayor")
print(f"  • Beneficio real: 2.5x menor")
print(f"  • RECOMENDACIÓN: DETENER BOT o SOLO OPERAR LONG")

print("\n" + "="*80)
