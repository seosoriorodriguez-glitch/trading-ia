# -*- coding: utf-8 -*-
import sys
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

import pandas as pd

# Cargar backtests
m15m5 = pd.read_csv('strategies/pivot_scalping/data/backtest_M15M5_29d.csv')
m5m1 = pd.read_csv('strategies/pivot_scalping/data/backtest_M5M1_29d.csv')

def calc_metrics(df, name):
    total = len(df)
    wins = len(df[df['pnl_usd'] > 0])
    wr = wins / total * 100 if total > 0 else 0
    
    gp = df[df['pnl_usd'] > 0]['pnl_usd'].sum()
    gl = abs(df[df['pnl_usd'] <= 0]['pnl_usd'].sum())
    pf = gp / gl if gl > 0 else float('inf')
    
    retorno = df['pnl_usd'].sum() / 100000 * 100
    
    avg_win_usd = df[df['pnl_usd'] > 0]['pnl_usd'].mean() if wins > 0 else 0
    avg_loss_usd = df[df['pnl_usd'] <= 0]['pnl_usd'].mean() if len(df[df['pnl_usd'] <= 0]) > 0 else 0
    
    avg_win_pts = df[df['pnl_usd'] > 0]['pnl_points_net'].mean() if wins > 0 else 0
    avg_loss_pts = df[df['pnl_usd'] <= 0]['pnl_points_net'].mean() if len(df[df['pnl_usd'] <= 0]) > 0 else 0
    
    return {
        'name': name,
        'total': total,
        'trades_mes': total / 0.97,  # 29 días = 0.97 meses
        'wr': wr,
        'pf': pf,
        'retorno': retorno,
        'avg_win_usd': avg_win_usd,
        'avg_loss_usd': avg_loss_usd,
        'avg_win_pts': avg_win_pts,
        'avg_loss_pts': avg_loss_pts
    }

metrics_m15m5 = calc_metrics(m15m5, 'M15/M5')
metrics_m5m1 = calc_metrics(m5m1, 'M5/M1')

print('='*100)
print('COMPARATIVA: M15/M5 vs M5/M1 (29 DÍAS)')
print('='*100)

print(f'\n{"Métrica":<25} | {"M15/M5 (Actual)":>20} | {"M5/M1 (Nuevo)":>20} | {"Diferencia":>20}')
print('-'*100)

print(f'{"Total Trades":<25} | {metrics_m15m5["total"]:20d} | {metrics_m5m1["total"]:20d} | {metrics_m5m1["total"] - metrics_m15m5["total"]:20d}')
print(f'{"Trades/Mes":<25} | {metrics_m15m5["trades_mes"]:20.1f} | {metrics_m5m1["trades_mes"]:20.1f} | {metrics_m5m1["trades_mes"] - metrics_m15m5["trades_mes"]:20.1f}')
print(f'{"Win Rate":<25} | {metrics_m15m5["wr"]:19.1f}% | {metrics_m5m1["wr"]:19.1f}% | {metrics_m5m1["wr"] - metrics_m15m5["wr"]:19.1f}%')

pf_m15 = metrics_m15m5["pf"] if metrics_m15m5["pf"] != float('inf') else 999
pf_m5 = metrics_m5m1["pf"] if metrics_m5m1["pf"] != float('inf') else 999
print(f'{"PF (USD)":<25} | {pf_m15:20.2f} | {pf_m5:20.2f} | {"N/A":>20}')

print(f'{"Retorno":<25} | {metrics_m15m5["retorno"]:19.2f}% | {metrics_m5m1["retorno"]:19.2f}% | {metrics_m5m1["retorno"] - metrics_m15m5["retorno"]:19.2f}%')
print(f'{"Avg Win (USD)":<25} | ${metrics_m15m5["avg_win_usd"]:19,.2f} | ${metrics_m5m1["avg_win_usd"]:19,.2f} | ${metrics_m5m1["avg_win_usd"] - metrics_m15m5["avg_win_usd"]:19,.2f}')
print(f'{"Avg Loss (USD)":<25} | ${metrics_m15m5["avg_loss_usd"]:19,.2f} | ${metrics_m5m1["avg_loss_usd"]:19,.2f} | ${metrics_m5m1["avg_loss_usd"] - metrics_m15m5["avg_loss_usd"]:19,.2f}')
print(f'{"Avg Win (Pts)":<25} | {metrics_m15m5["avg_win_pts"]:20.2f} | {metrics_m5m1["avg_win_pts"]:20.2f} | {metrics_m5m1["avg_win_pts"] - metrics_m15m5["avg_win_pts"]:20.2f}')
print(f'{"Avg Loss (Pts)":<25} | {metrics_m15m5["avg_loss_pts"]:20.2f} | {metrics_m5m1["avg_loss_pts"]:20.2f} | {metrics_m5m1["avg_loss_pts"] - metrics_m15m5["avg_loss_pts"]:20.2f}')

print('\n' + '='*100)
print('ANÁLISIS')
print('='*100)

print(f'''
HALLAZGOS:

1. FRECUENCIA:
   - M15/M5: {metrics_m15m5["total"]} trades en 29 días = {metrics_m15m5["trades_mes"]:.1f} trades/mes
   - M5/M1:  {metrics_m5m1["total"]} trades en 29 días = {metrics_m5m1["trades_mes"]:.1f} trades/mes
   - Diferencia: +{metrics_m5m1["total"] - metrics_m15m5["total"]} trades (+{(metrics_m5m1["total"] / metrics_m15m5["total"] - 1) * 100:.0f}%)

2. CALIDAD:
   - Ambas tienen 100% WR en este período (muestra muy pequeña)
   - M5/M1 tiene mejor retorno: {metrics_m5m1["retorno"]:.2f}% vs {metrics_m15m5["retorno"]:.2f}%
   - M5/M1 tiene mejor Avg Win: ${metrics_m5m1["avg_win_usd"]:.2f} vs ${metrics_m15m5["avg_win_usd"]:.2f}

3. PIVOTS DETECTADOS:
   - M15/M5: 1,034 highs + 1,038 lows = 2,072 pivots
   - M5/M1:  657 highs + 647 lows = 1,304 pivots
   - M5/M1 detecta MENOS pivots (usa M5 en vez de M15)
   - Pero genera MÁS trades (mejor conversión)

4. PROBLEMA DE MUESTRA:
   - Solo 29 días de datos M1
   - Solo 2-5 trades por estrategia
   - NO es suficiente para conclusiones definitivas
   - Necesitamos al menos 60-90 días de M1

CONCLUSIÓN PRELIMINAR:

M5/M1 muestra potencial:
- +150% más trades (5 vs 2)
- Mejor retorno en este período
- Avg Win en puntos similar (31.5 vs 22.4)

PERO la muestra es DEMASIADO PEQUEÑA para validar.

PRÓXIMOS PASOS:

1. Descargar más datos M1 (si MT5 permite)
2. Si no, esperar 30-60 días y acumular datos
3. Re-ejecutar backtest con 60-90 días
4. Si M5/M1 mantiene 10-15 trades/mes con PF > 2.0, es viable

ALTERNATIVA INMEDIATA:

Correr AMBAS estrategias en paralelo:
- M15/M5: 4 trades/mes (validado en 260 días)
- M5/M1:  5-10 trades/mes (estimado, pendiente validar)
- Total:  9-14 trades/mes (suficiente para FTMO)
''')
