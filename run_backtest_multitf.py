"""
Backtest multi-timeframe de la estrategia Order Block.
NO modifica ningun archivo del bot live.

Combinaciones:
  A) OB 4H  + entradas 1H
  B) OB 4H  + entradas 15M
  C) OB 1H  + entradas 15M
  D) OB 1H  + entradas 5M   (comparacion con base actual)
  E) OB 5M  + entradas 1M   (BASE ACTUAL - referencia)
"""
import copy
import pandas as pd

from strategies.order_block.backtest.config import DEFAULT_PARAMS
from strategies.order_block.backtest.data_loader import load_csv
from strategies.order_block.backtest.backtester_limit_orders import OrderBlockBacktesterLimitOrders


# ──────────────────────────────────────────────────────────────
# 1. Cargar datos base
# ──────────────────────────────────────────────────────────────
print("Cargando datos base...", flush=True)
df_m1 = load_csv('data/US30_icm_M1_500k.csv')
df_m5 = load_csv('data/US30_icm_M5_518d.csv')
print(f"  M1: {len(df_m1):,} velas  |  M5: {len(df_m5):,} velas", flush=True)


# ──────────────────────────────────────────────────────────────
# 2. Resamplear a los TFs necesarios
# ──────────────────────────────────────────────────────────────
def resample_ohlcv(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    """Resamplea un DataFrame OHLCV a la frecuencia indicada."""
    df = df.copy()
    df['time'] = pd.to_datetime(df['time'])
    df = df.set_index('time')
    agg = df.resample(rule, label='left', closed='left').agg({
        'open':   'first',
        'high':   'max',
        'low':    'min',
        'close':  'last',
        'volume': 'sum',
    }).dropna().reset_index()
    agg = agg.rename(columns={'time': 'time'})
    # Convertir a datetime naive (como el resto del sistema)
    agg['time'] = agg['time'].dt.tz_localize(None) if agg['time'].dt.tz else agg['time']
    return agg

print("Resampleando...", flush=True)
df_15m = resample_ohlcv(df_m1, '15min')
df_1h  = resample_ohlcv(df_m1, '1h')
df_4h  = resample_ohlcv(df_m1, '4h')
print(f"  15M: {len(df_15m):,} velas  |  1H: {len(df_1h):,} velas  |  4H: {len(df_4h):,} velas", flush=True)


# ──────────────────────────────────────────────────────────────
# 3. Parametros adaptados por combinacion
# ──────────────────────────────────────────────────────────────
def make_params(combo: str) -> dict:
    """
    Adapta DEFAULT_PARAMS segun el combo de TFs.
    Solo cambia lo estrictamente necesario para que la logica funcione.
    El resto de parametros (RR, buffer, consecutive_candles, etc.) queda igual.
    """
    p = copy.deepcopy(DEFAULT_PARAMS)

    if combo in ('4H_1H', '4H_15M'):
        # OBs en 4H: zonas mas grandes → buffer y riesgo minimo/maximo mas amplios
        p['buffer_points']   = 50
        p['min_risk_points'] = 30
        p['max_risk_points'] = 600
        # Sesion mas amplia para capturar movimientos de 4H (sin skip agresivo)
        p['sessions'] = {
            'london':   {'start': '08:00', 'end': '12:00', 'skip_minutes': 0},
            'new_york': {'start': '13:30', 'end': '20:00', 'skip_minutes': 15},
        }

    elif combo in ('1H_15M', '1H_5M'):
        # OBs en 1H: intermedios
        p['buffer_points']   = 35
        p['min_risk_points'] = 20
        p['max_risk_points'] = 400
        p['sessions'] = {
            'london':   {'start': '08:00', 'end': '12:00', 'skip_minutes': 0},
            'new_york': {'start': '13:30', 'end': '20:00', 'skip_minutes': 15},
        }

    # BASE: 5M_1M — parametros originales sin cambios
    return p


# ──────────────────────────────────────────────────────────────
# 4. Ejecutar combinaciones
# ──────────────────────────────────────────────────────────────
combos = [
    ('5M_1M',   df_m5,  df_m1,  'BASE ACTUAL'),
    ('4H_1H',   df_4h,  df_1h,  'SWING - OB 4H / Entrada 1H'),
    ('4H_15M',  df_4h,  df_15m, 'SWING - OB 4H / Entrada 15M'),
    ('1H_15M',  df_1h,  df_15m, 'INTRADAY - OB 1H / Entrada 15M'),
    ('1H_5M',   df_1h,  df_m5,  'INTRADAY - OB 1H / Entrada 5M'),
]

print(f'\n{"="*80}')
print(f'  BACKTEST MULTI-TIMEFRAME — 518 dias ICM — US30.cash')
print(f'{"="*80}')
print(f'{"Combo":<16} {"TF OB":<6} {"TF Entr":<8} {"Trades":>7} {"WR%":>6} {"Ret%":>8} {"DD%":>7} {"PF":>6} {"Exp$":>7} {"AvgW":>8} {"AvgL":>8}')
print('-'*80)

results = {}
for combo, df_h, df_l, label in combos:
    p  = make_params(combo)
    bt = OrderBlockBacktesterLimitOrders(p)
    df = bt.run(df_h, df_l)

    if df.empty:
        print(f'{combo:<16}  sin trades')
        continue

    n    = len(df)
    wins = df[df['pnl_usd'] > 0]
    loss = df[df['pnl_usd'] < 0]
    wr   = len(wins)/n*100
    ret  = df['pnl_usd'].sum() / 100_000 * 100
    exp  = df['pnl_usd'].mean()
    pf   = wins['pnl_usd'].sum() / abs(loss['pnl_usd'].sum()) if len(loss)>0 else 999

    peak=100_000; dd=0; run=100_000
    for x in df['pnl_usd']:
        run+=x
        if run>peak: peak=run
        d=(peak-run)/peak*100
        if d>dd: dd=d

    aw = wins['pnl_usd'].mean() if len(wins)>0 else 0
    al = loss['pnl_usd'].mean() if len(loss)>0 else 0

    tf_ob   = combo.split('_')[0]
    tf_entr = combo.split('_')[1]
    base    = ' <- BASE' if combo == '5M_1M' else ''
    print(f'{combo:<16} {tf_ob:<6} {tf_entr:<8} {n:>7} {wr:>5.1f}% {ret:>+7.1f}% {dd:>6.1f}% {pf:>6.2f} {exp:>+7.0f} {aw:>+8.0f} {al:>+8.0f}{base}')

    results[combo] = {'n': n, 'wr': wr, 'ret': ret, 'dd': dd, 'pf': pf, 'label': label}
    df.to_csv(f'strategies/order_block/backtest/results/ob_{combo.lower()}.csv', index=False)

print(f'\n{"="*80}')
print('Resultados guardados en strategies/order_block/backtest/results/')
