import sys, copy
sys.path.insert(0, '.')

from strategies.order_block.backtest.config import DEFAULT_PARAMS
from strategies.order_block.backtest.data_loader import load_csv
from strategies.order_block.backtest.backtester_limit_orders import OrderBlockBacktesterLimitOrders

PARAM  = sys.argv[1]          # nombre del parametro
VALUES = [eval(v) for v in sys.argv[2:]]   # valores a testear
BASE   = DEFAULT_PARAMS[PARAM]

df_m5 = load_csv('data/US30_icm_M5_518d.csv')
df_m1 = load_csv('data/US30_icm_M1_500k.csv')

print(f'\n{"="*72}')
print(f'  PARAM: {PARAM}  |  BASE: {BASE}')
print(f'{"="*72}')
print(f'{"Valor":>8} {"Trades":>7} {"WR%":>6} {"Ret%":>8} {"DD%":>7} {"PF":>6} {"Exp$":>7} {"AvgW":>8} {"AvgL":>8}')
print('-'*72)

for v in VALUES:
    p = copy.deepcopy(DEFAULT_PARAMS)
    p[PARAM] = v
    bt = OrderBlockBacktesterLimitOrders(p)
    df = bt.run(df_m5, df_m1)

    if df.empty:
        print(f'{str(v):>8}  sin trades')
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

    aw   = wins['pnl_usd'].mean() if len(wins)>0 else 0
    al   = loss['pnl_usd'].mean() if len(loss)>0 else 0
    flag = ' <- BASE' if v == BASE else ''
    print(f'{str(v):>8} {n:>7} {wr:>5.1f}% {ret:>+7.1f}% {dd:>6.1f}% {pf:>6.2f} {exp:>+7.0f} {aw:>+8.0f} {al:>+8.0f}{flag}')
