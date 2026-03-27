# -*- coding: utf-8 -*-
import sys
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

import pandas as pd

# Cargar los 5 backtests
actual = pd.read_csv('strategies/pivot_scalping/data/backtest_US30_260d.csv')
bt1 = pd.read_csv('strategies/pivot_scalping/data/backtest_BT1_touch1.csv')
bt2 = pd.read_csv('strategies/pivot_scalping/data/backtest_BT2_strength2.csv')
bt3 = pd.read_csv('strategies/pivot_scalping/data/backtest_BT3_combo.csv')
bt4 = pd.read_csv('strategies/pivot_scalping/data/backtest_BT4_short_ny.csv')

def calc_metrics(df):
    total = len(df)
    wins = len(df[df['pnl_usd'] > 0])
    wr = wins / total * 100 if total > 0 else 0
    
    gp = df[df['pnl_usd'] > 0]['pnl_usd'].sum()
    gl = abs(df[df['pnl_usd'] <= 0]['pnl_usd'].sum())
    pf = gp / gl if gl > 0 else 0
    
    retorno = df['pnl_usd'].sum() / 100000 * 100
    
    # Max DD
    df_temp = df.copy()
    df_temp['cumulative_pnl'] = df_temp['pnl_usd'].cumsum()
    df_temp['running_max'] = df_temp['cumulative_pnl'].cummax()
    df_temp['drawdown'] = df_temp['cumulative_pnl'] - df_temp['running_max']
    max_dd = df_temp['drawdown'].min() / 100000 * 100
    
    # Por dirección
    long_df = df[df['type'] == 'long']
    short_df = df[df['type'] == 'short']
    
    long_wr = len(long_df[long_df['pnl_usd'] > 0]) / len(long_df) * 100 if len(long_df) > 0 else 0
    short_wr = len(short_df[short_df['pnl_usd'] > 0]) / len(short_df) * 100 if len(short_df) > 0 else 0
    
    return {
        'total': total,
        'trades_mes': total / 8.7,
        'wr': wr,
        'pf': pf,
        'retorno': retorno,
        'max_dd': max_dd,
        'long_wr': long_wr,
        'short_wr': short_wr
    }

metrics = {
    'Actual': calc_metrics(actual),
    'BT1': calc_metrics(bt1),
    'BT2': calc_metrics(bt2),
    'BT3': calc_metrics(bt3),
    'BT4': calc_metrics(bt4)
}

print('='*120)
print('COMPARATIVA: 4 BACKTESTS vs ACTUAL (260 DÍAS)')
print('='*120)

print(f'\n{"Métrica":<20} | {"BT1 (touch=1)":>15} | {"BT2 (str=2)":>15} | {"BT3 (combo)":>15} | {"BT4 (SHORT+NY)":>15} | {"Actual":>15}')
print('-'*120)

print(f'{"Total Trades":<20} | {metrics["BT1"]["total"]:15d} | {metrics["BT2"]["total"]:15d} | {metrics["BT3"]["total"]:15d} | {metrics["BT4"]["total"]:15d} | {metrics["Actual"]["total"]:15d}')
print(f'{"Trades/Mes":<20} | {metrics["BT1"]["trades_mes"]:15.1f} | {metrics["BT2"]["trades_mes"]:15.1f} | {metrics["BT3"]["trades_mes"]:15.1f} | {metrics["BT4"]["trades_mes"]:15.1f} | {metrics["Actual"]["trades_mes"]:15.1f}')
print(f'{"Win Rate":<20} | {metrics["BT1"]["wr"]:14.1f}% | {metrics["BT2"]["wr"]:14.1f}% | {metrics["BT3"]["wr"]:14.1f}% | {metrics["BT4"]["wr"]:14.1f}% | {metrics["Actual"]["wr"]:14.1f}%')
print(f'{"PF (USD)":<20} | {metrics["BT1"]["pf"]:15.2f} | {metrics["BT2"]["pf"]:15.2f} | {metrics["BT3"]["pf"]:15.2f} | {metrics["BT4"]["pf"]:15.2f} | {metrics["Actual"]["pf"]:15.2f}')
print(f'{"Retorno":<20} | {metrics["BT1"]["retorno"]:14.2f}% | {metrics["BT2"]["retorno"]:14.2f}% | {metrics["BT3"]["retorno"]:14.2f}% | {metrics["BT4"]["retorno"]:14.2f}% | {metrics["Actual"]["retorno"]:14.2f}%')
print(f'{"Max DD":<20} | {metrics["BT1"]["max_dd"]:14.2f}% | {metrics["BT2"]["max_dd"]:14.2f}% | {metrics["BT3"]["max_dd"]:14.2f}% | {metrics["BT4"]["max_dd"]:14.2f}% | {metrics["Actual"]["max_dd"]:14.2f}%')
print(f'{"LONG WR":<20} | {metrics["BT1"]["long_wr"]:14.1f}% | {metrics["BT2"]["long_wr"]:14.1f}% | {metrics["BT3"]["long_wr"]:14.1f}% | {metrics["BT4"]["long_wr"]:14.1f}% | {metrics["Actual"]["long_wr"]:14.1f}%')
print(f'{"SHORT WR":<20} | {metrics["BT1"]["short_wr"]:14.1f}% | {metrics["BT2"]["short_wr"]:14.1f}% | {metrics["BT3"]["short_wr"]:14.1f}% | {metrics["BT4"]["short_wr"]:14.1f}% | {metrics["Actual"]["short_wr"]:14.1f}%')

print('\n' + '='*120)
print('ANÁLISIS')
print('='*120)

print(f'''
HALLAZGOS CRÍTICOS:

1. BT1 (min_touches=1): PEOR que Actual
   - Solo 15 trades (vs 36 actual) = MENOS frecuencia
   - PF 2.67 (vs 1.65 actual) = mejor calidad pero menos trades
   - Conclusión: min_touches ya estaba en 1 efectivamente, cambiar a 1 explícito FILTRÓ trades

2. BT2 (swing_strength=2): MEJOR balance
   - 19 trades (vs 36 actual) = MENOS frecuencia pero mejor calidad
   - PF 3.89 (vs 1.65 actual) = MUCHO mejor
   - Retorno 7.96% (vs 4.65% actual) = +71% más retorno
   - Conclusión: Pivots más frecuentes (strength=2) generan MEJOR calidad

3. BT3 (combo): IDÉNTICO a BT2
   - Confirma que min_touches ya estaba en 1
   - El parámetro min_touches: 2 en config NO se estaba respetando

4. BT4 (solo SHORT + solo NY): PERDEDOR
   - Solo 6 trades en 260 días
   - PF 0.85 = PERDEDOR
   - Retorno -0.25%
   - Conclusión: Filtrar por sesión NY ELIMINA los mejores trades SHORT

RECOMENDACIÓN:

Usar BT2 (swing_strength=2) como nueva baseline:
- 19 trades en 260 días = 2.2 trades/mes (sigue siendo bajo)
- PF 3.89 = excelente
- Retorno 7.96% en 8.7 meses = 11% anualizado
- Win Rate 73.7%

PROBLEMA PERSISTENTE:
- Frecuencia sigue siendo BAJA (2.2 trades/mes)
- Para FTMO necesitas ~10-20 trades/mes
- Opciones:
  a) Agregar otra estrategia complementaria (breakouts, pullbacks)
  b) Reducir min_risk_points de 10 a 5
  c) Reducir min_rr_ratio de 1.5 a 1.2
  d) Operar múltiples instrumentos (US30 + NAS100 + GER40)
''')
