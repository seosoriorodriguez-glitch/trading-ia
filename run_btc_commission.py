# -*- coding: utf-8 -*-
import sys, copy
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")

sys.path.insert(0, '.')
from strategies.order_block_btc.backtest.config import BTC_PARAMS
from strategies.order_block.backtest.data_loader import load_csv
from strategies.order_block.backtest.backtester_limit_orders import OrderBlockBacktesterLimitOrders

def stats(trades, balance):
    w = trades[trades['pnl_usd'] > 0]
    l = trades[trades['pnl_usd'] < 0]
    n = len(trades)
    wr = len(w)/n*100
    pf = w['pnl_usd'].sum() / abs(l['pnl_usd'].sum())
    total = trades['pnl_usd'].sum()
    ret = total / balance * 100
    peak = running = balance
    max_dd = 0
    for pnl in trades['pnl_usd']:
        running += pnl
        if running > peak: peak = running
        dd = (peak-running)/peak*100
        if dd > max_dd: max_dd = dd
    return n, wr, pf, ret, max_dd, total

print('Cargando datos BTC...')
df_m5 = load_csv('data/BTCUSD_icm_M5.csv')
df_m1 = load_csv('data/BTCUSD_icm_M1.csv')
print('OK\n')

print("=" * 60)
print("  IMPACTO COMISION REAL — BTCUSD 351 dias")
print("=" * 60)
print(f"  {'Config':<30} {'Trades':>6}  {'WR%':>5}  {'PF':>5}  {'Retorno':>8}  {'DD':>6}  {'PnL $':>12}")
print(f"  {'-'*56}")

for label, spread in [
    ('spread=10 (backtest actual)', 10),
    ('spread=43 (comision real ICM)', 43),
]:
    p = copy.deepcopy(BTC_PARAMS)
    p['avg_spread_points'] = spread
    bt = OrderBlockBacktesterLimitOrders(p)
    trades = bt.run(df_m5, df_m1)
    n, wr, pf, ret, dd, total = stats(trades, p['initial_balance'])
    print(f"  {label:<30} {n:>6}  {wr:>4.1f}%  {pf:>5.2f}  {ret:>+7.1f}%  {dd:>5.1f}%  ${total:>+12,.0f}")

print("=" * 60)
print("\nNota: spread_points en el backtester se aplica como costo")
print("fijo por trade en puntos. 1 punto BTC = $1/lote.")
print("Comision real ICMarkets BTCUSD: ~$21.5/lado = $43 round-trip.")
