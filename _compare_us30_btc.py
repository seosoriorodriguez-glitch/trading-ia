import copy, pandas as pd
from strategies.order_block.backtest.config import DEFAULT_PARAMS
from strategies.order_block.backtest.data_loader import load_csv
from strategies.order_block.backtest.backtester_limit_orders import OrderBlockBacktesterLimitOrders

# US30
df_m5_us = load_csv('data/US30_icm_M5_518d.csv')
df_m1_us = load_csv('data/US30_icm_M1_500k.csv')
p_us = copy.deepcopy(DEFAULT_PARAMS)
p_us['sessions'] = {'new_york': {'start':'13:30','end':'23:00','skip_minutes':15}}
bt_us = OrderBlockBacktesterLimitOrders(p_us)
df_us = bt_us.run(df_m5_us, df_m1_us)

# BTCUSD
df_m1_bt = load_csv('data/BTCUSD_icm_M1.csv')
df_m5_bt = load_csv('data/BTCUSD_icm_M5.csv')
start = max(df_m1_bt['time'].iloc[0], df_m5_bt['time'].iloc[0])
df_m1_bt = df_m1_bt[df_m1_bt['time'] >= start].reset_index(drop=True)
df_m5_bt = df_m5_bt[df_m5_bt['time'] >= start].reset_index(drop=True)
p_bt = copy.deepcopy(DEFAULT_PARAMS)
p_bt['avg_spread_points'] = 10
p_bt['buffer_points'] = 50
p_bt['min_risk_points'] = 10
p_bt['max_risk_points'] = 300
p_bt['target_rr'] = 2.0
p_bt['consecutive_candles'] = 4
p_bt['sessions'] = {'main': {'start':'00:00','end':'23:59','skip_minutes':0}}
bt_bt = OrderBlockBacktesterLimitOrders(p_bt)
df_bt = bt_bt.run(df_m5_bt, df_m1_bt)

def stats(df, label, dias, rr):
    n = len(df)
    wins = df[df['pnl_usd']>0]
    loss = df[df['pnl_usd']<0]
    wr   = len(wins)/n*100
    ret  = df['pnl_usd'].sum()/100_000*100
    exp  = df['pnl_usd'].mean()
    pf   = wins['pnl_usd'].sum()/abs(loss['pnl_usd'].sum()) if len(loss)>0 else 999
    aw   = wins['pnl_usd'].mean() if len(wins)>0 else 0
    al   = loss['pnl_usd'].mean() if len(loss)>0 else 0

    peak=100_000; dd=0; run=100_000
    for x in df['pnl_usd']:
        run+=x
        if run>peak: peak=run
        d=(peak-run)/peak*100
        if d>dd: dd=d

    best_w=0; worst_l=0; cw=0; cl=0
    for x in df['pnl_usd']:
        if x>0: cw+=1; cl=0
        else: cl+=1; cw=0
        if cw>best_w: best_w=cw
        if cl>worst_l: worst_l=cl

    df2 = df.copy()
    df2['date'] = pd.to_datetime(df2['entry_time']).dt.date
    daily = df2.groupby('date')['pnl_usd'].sum()
    pos_days = (daily>0).sum()
    neg_days = (daily<0).sum()

    # mejor/peor racha dias
    best_wd=0; worst_ld=0; cwd=0; cld=0
    for x in daily:
        if x>0: cwd+=1; cld=0
        else: cld+=1; cwd=0
        if cwd>best_wd: best_wd=cwd
        if cld>worst_ld: worst_ld=cld

    print(f'\n  {label}')
    print(f'  {"-"*45}')
    print(f'  Periodo           : {dias} dias')
    print(f'  R:R target        : {rr}')
    print(f'  Total trades      : {n}')
    print(f'  Trades/dia        : {n/dias:.2f}')
    print(f'  Win Rate          : {wr:.1f}%')
    print(f'  Retorno total     : {ret:+.1f}%  (${df["pnl_usd"].sum():,.0f})')
    print(f'  Retorno/mes avg   : {ret/(dias/30):+.1f}%')
    print(f'  Max Drawdown      : {dd:.1f}%')
    print(f'  Profit Factor     : {pf:.2f}')
    print(f'  Expectancy/trade  : ${exp:+.0f}')
    print(f'  Avg Win           : ${aw:+.0f}')
    print(f'  Avg Loss          : ${al:+.0f}')
    print(f'  Ratio W/L         : {abs(aw/al):.2f}x')
    print(f'  Mejor racha wins  : {best_w} trades consecutivos')
    print(f'  Peor racha losses : {worst_l} trades consecutivos')
    print(f'  Dias positivos    : {pos_days} ({pos_days/len(daily)*100:.0f}%)')
    print(f'  Dias negativos    : {neg_days} ({neg_days/len(daily)*100:.0f}%)')
    print(f'  Mejor racha dias+ : {best_wd} dias seguidos')
    print(f'  Peor racha dias-  : {worst_ld} dias seguidos')

print('='*50)
print('  COMPARATIVA: US30 vs BTCUSD')
print('='*50)
stats(df_us, 'US30   | M5/M1 | NY session', 518, 3.5)
stats(df_bt, 'BTCUSD | M5/M1 | 24/7', 351, 2.0)
print()
