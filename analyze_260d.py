# -*- coding: utf-8 -*-
import sys
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

import pandas as pd
import numpy as np
from datetime import datetime

df = pd.read_csv('strategies/pivot_scalping/data/backtest_US30_260d.csv')

# Convertir timestamps
df['entry_time'] = pd.to_datetime(df['entry_time'])
df['exit_time'] = pd.to_datetime(df['exit_time'])

print('='*80)
print('ANÁLISIS COMPLETO - BACKTEST 260 DÍAS (8.7 MESES)')
print('='*80)

# ============================================================================
# 1. TABLA GENERAL
# ============================================================================
print('\n' + '='*80)
print('1. MÉTRICAS GENERALES')
print('='*80)

total_trades = len(df)
wins = len(df[df['pnl_usd'] > 0])
losses = len(df[df['pnl_usd'] <= 0])
win_rate = wins / total_trades * 100

gross_profit = df[df['pnl_usd'] > 0]['pnl_usd'].sum()
gross_loss = abs(df[df['pnl_usd'] <= 0]['pnl_usd'].sum())
pf_usd = gross_profit / gross_loss if gross_loss > 0 else 0

gross_profit_pts = df[df['pnl_points_net'] > 0]['pnl_points_net'].sum()
gross_loss_pts = abs(df[df['pnl_points_net'] <= 0]['pnl_points_net'].sum())
pf_pts = gross_profit_pts / gross_loss_pts if gross_loss_pts > 0 else 0

total_pnl = df['pnl_usd'].sum()
retorno = total_pnl / 100000 * 100

avg_win_usd = df[df['pnl_usd'] > 0]['pnl_usd'].mean()
avg_loss_usd = df[df['pnl_usd'] <= 0]['pnl_usd'].mean()
avg_win_pts = df[df['pnl_usd'] > 0]['pnl_points_net'].mean()
avg_loss_pts = df[df['pnl_usd'] <= 0]['pnl_points_net'].mean()

# Max Drawdown
df['cumulative_pnl'] = df['pnl_usd'].cumsum()
df['running_max'] = df['cumulative_pnl'].cummax()
df['drawdown'] = df['cumulative_pnl'] - df['running_max']
max_dd = df['drawdown'].min()
max_dd_pct = (max_dd / 100000) * 100

print(f'\nTotal Trades:         {total_trades}')
print(f'Win Rate:             {win_rate:.1f}%')
print(f'Profit Factor (USD):  {pf_usd:.2f}')
print(f'Profit Factor (Pts):  {pf_pts:.2f}')
print(f'Retorno:              {retorno:.2f}%')
print(f'Max Drawdown:         ${max_dd:,.2f} ({max_dd_pct:.2f}%)')
print(f'Avg Win:              ${avg_win_usd:,.2f} ({avg_win_pts:.2f} pts)')
print(f'Avg Loss:             ${avg_loss_usd:,.2f} ({avg_loss_pts:.2f} pts)')

# ============================================================================
# 2. DESGLOSE POR DIRECCIÓN
# ============================================================================
print('\n' + '='*80)
print('2. DESGLOSE POR DIRECCIÓN (LONG vs SHORT)')
print('='*80)

for direction in ['long', 'short']:
    df_dir = df[df['type'] == direction]
    
    if len(df_dir) == 0:
        continue
    
    trades_dir = len(df_dir)
    wins_dir = len(df_dir[df_dir['pnl_usd'] > 0])
    wr_dir = wins_dir / trades_dir * 100
    
    gp_dir = df_dir[df_dir['pnl_usd'] > 0]['pnl_usd'].sum()
    gl_dir = abs(df_dir[df_dir['pnl_usd'] <= 0]['pnl_usd'].sum())
    pf_dir = gp_dir / gl_dir if gl_dir > 0 else 0
    
    avg_pnl_dir = df_dir['pnl_usd'].mean()
    total_pnl_dir = df_dir['pnl_usd'].sum()
    
    print(f'\n{direction.upper()}:')
    print(f'  Trades:       {trades_dir} ({trades_dir/total_trades*100:.1f}%)')
    print(f'  Win Rate:     {wr_dir:.1f}%')
    print(f'  Profit Factor: {pf_dir:.2f}')
    print(f'  Avg PnL:      ${avg_pnl_dir:,.2f}')
    print(f'  Total PnL:    ${total_pnl_dir:,.2f}')

# ============================================================================
# 3. DESGLOSE POR MES
# ============================================================================
print('\n' + '='*80)
print('3. DESGLOSE POR MES (Consistencia Temporal)')
print('='*80)

df['month'] = df['entry_time'].dt.to_period('M')
monthly = df.groupby('month').agg({
    'trade_id': 'count',
    'pnl_usd': ['sum', lambda x: (x > 0).sum() / len(x) * 100]
}).round(2)

monthly.columns = ['Trades', 'PnL_USD', 'Win_Rate']

print(f'\n{"Mes":<15} | {"Trades":>8} | {"Win Rate":>10} | {"PnL USD":>12} | {"Retorno %":>10}')
print('-'*80)

for month, row in monthly.iterrows():
    retorno_mes = row['PnL_USD'] / 100000 * 100
    print(f'{str(month):<15} | {int(row["Trades"]):8d} | {row["Win_Rate"]:9.1f}% | ${row["PnL_USD"]:11,.2f} | {retorno_mes:9.2f}%')

# ============================================================================
# 4. DESGLOSE POR SESIÓN
# ============================================================================
print('\n' + '='*80)
print('4. DESGLOSE POR SESIÓN (Londres vs Nueva York)')
print('='*80)

# Londres: 08:00-12:00 UTC, Nueva York: 13:00-17:00 UTC
df['hour_utc'] = df['entry_time'].dt.hour

def classify_session(hour):
    if 8 <= hour < 12:
        return 'Londres'
    elif 13 <= hour < 17:
        return 'Nueva York'
    elif 12 <= hour < 13:
        return 'Overlap'
    else:
        return 'Asia/Noche'

df['session'] = df['hour_utc'].apply(classify_session)

print(f'\n{"Sesión":<15} | {"Trades":>8} | {"Win Rate":>10} | {"PF":>6} | {"Avg PnL":>12}')
print('-'*80)

for session in ['Londres', 'Nueva York', 'Overlap', 'Asia/Noche']:
    df_sess = df[df['session'] == session]
    
    if len(df_sess) == 0:
        continue
    
    trades_sess = len(df_sess)
    wins_sess = len(df_sess[df_sess['pnl_usd'] > 0])
    wr_sess = wins_sess / trades_sess * 100
    
    gp_sess = df_sess[df_sess['pnl_usd'] > 0]['pnl_usd'].sum()
    gl_sess = abs(df_sess[df_sess['pnl_usd'] <= 0]['pnl_usd'].sum())
    pf_sess = gp_sess / gl_sess if gl_sess > 0 else 0
    
    avg_pnl_sess = df_sess['pnl_usd'].mean()
    
    print(f'{session:<15} | {trades_sess:8d} | {wr_sess:9.1f}% | {pf_sess:5.2f} | ${avg_pnl_sess:11,.2f}')

# ============================================================================
# 5. PEOR RACHA DE PÉRDIDAS CONSECUTIVAS
# ============================================================================
print('\n' + '='*80)
print('5. PEOR RACHA DE PÉRDIDAS CONSECUTIVAS')
print('='*80)

# Calcular rachas
df['is_loss'] = df['pnl_usd'] <= 0
df['loss_streak'] = (df['is_loss'] != df['is_loss'].shift()).cumsum()
df['loss_streak'] = df['is_loss'] * df['loss_streak']

# Encontrar la racha más larga
streaks = df[df['is_loss']].groupby('loss_streak').size()
if len(streaks) > 0:
    max_streak_length = streaks.max()
    max_streak_id = streaks.idxmax()
    
    # Obtener trades de esa racha
    streak_trades = df[df['loss_streak'] == max_streak_id]
    streak_dd = streak_trades['pnl_usd'].sum()
    
    print(f'\nPeor racha:           {max_streak_length} pérdidas consecutivas')
    print(f'Drawdown generado:    ${streak_dd:,.2f}')
    print(f'Período:              {streak_trades.iloc[0]["entry_time"]} → {streak_trades.iloc[-1]["exit_time"]}')
    
    print(f'\nTrades en la racha:')
    for idx, trade in streak_trades.iterrows():
        print(f'  Trade #{trade["trade_id"]:2d} ({trade["type"]:5s}): ${trade["pnl_usd"]:8,.2f} ({trade["r_multiple"]:5.2f}R)')
else:
    print('\nNo hay rachas de pérdidas.')

# ============================================================================
# 6. COMPARATIVA 60d vs 260d
# ============================================================================
print('\n' + '='*80)
print('6. COMPARATIVA: 60 DÍAS vs 260 DÍAS')
print('='*80)

df_60d = pd.read_csv('strategies/pivot_scalping/data/backtest_A_fixed.csv')

print(f'\n{"Métrica":<25} | {"60 días":>15} | {"260 días":>15} | {"Diferencia":>15}')
print('-'*80)

metrics_60d = {
    'Trades': len(df_60d),
    'Win Rate': len(df_60d[df_60d['pnl_usd'] > 0]) / len(df_60d) * 100,
    'PF (USD)': df_60d[df_60d['pnl_usd'] > 0]['pnl_usd'].sum() / abs(df_60d[df_60d['pnl_usd'] <= 0]['pnl_usd'].sum()),
    'Retorno': df_60d['pnl_usd'].sum() / 100000 * 100,
    'Avg Win': df_60d[df_60d['pnl_usd'] > 0]['pnl_usd'].mean(),
    'Avg Loss': df_60d[df_60d['pnl_usd'] <= 0]['pnl_usd'].mean()
}

metrics_260d = {
    'Trades': total_trades,
    'Win Rate': win_rate,
    'PF (USD)': pf_usd,
    'Retorno': retorno,
    'Avg Win': avg_win_usd,
    'Avg Loss': avg_loss_usd
}

for metric in ['Trades', 'Win Rate', 'PF (USD)', 'Retorno', 'Avg Win', 'Avg Loss']:
    val_60 = metrics_60d[metric]
    val_260 = metrics_260d[metric]
    diff = val_260 - val_60
    
    if metric in ['Trades']:
        print(f'{metric:<25} | {val_60:15.0f} | {val_260:15.0f} | {diff:15.0f}')
    elif metric in ['Win Rate', 'Retorno']:
        print(f'{metric:<25} | {val_60:14.1f}% | {val_260:14.1f}% | {diff:14.1f}%')
    else:
        print(f'{metric:<25} | ${val_60:14,.2f} | ${val_260:14,.2f} | ${diff:14,.2f}')

print('\n' + '='*80)
print('CONCLUSIÓN')
print('='*80)

print(f'''
MUESTRA AMPLIADA (260 días vs 60 días):

1. TRADES: {total_trades} trades en 260 días = {total_trades/8.7:.1f} trades/mes
   - Frecuencia baja pero consistente
   - 60 días tenía {len(df_60d)} trades = {len(df_60d)/2:.1f} trades/mes (similar)

2. WIN RATE: {win_rate:.1f}% (bajó de 71.4%)
   - Más realista con muestra mayor
   - Sigue siendo bueno para scalping

3. PROFIT FACTOR: {pf_usd:.2f} (bajó de 4.01)
   - Todavía positivo (>1.0 es ganador)
   - Menos impresionante pero más sostenible

4. RETORNO: {retorno:.2f}% en 8.7 meses = {retorno/8.7*12:.1f}% anualizado
   - Bajó significativamente de 16.49% en 60 días
   - Más conservador y realista

5. MAX DRAWDOWN: ${max_dd:,.2f} ({max_dd_pct:.2f}%)
   - Drawdown controlado
   - Riesgo manejable

SESGO DIRECCIONAL:
- La estrategia muestra diferencias entre LONG y SHORT
- Revisar arriba para ver cuál dirección es más rentable

CONSISTENCIA TEMPORAL:
- Ver desglose mensual arriba
- Identificar si hay meses perdedores

RECOMENDACIÓN:
- La estrategia es RENTABLE pero MODESTA en el largo plazo
- PF de {pf_usd:.2f} es positivo pero no excepcional
- Considerar agregar BE y trailing para mejorar R:R
''')
