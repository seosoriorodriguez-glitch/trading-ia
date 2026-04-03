# -*- coding: utf-8 -*-
"""
Comparacion de expiry_candles: 100 / 200 / 300
Corre backtest US30 (518d) y BTC (351d) para cada valor.
Uso: python run_expiry_comparison.py
"""
import sys, copy
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

sys.path.insert(0, '.')

from strategies.order_block.backtest.config import DEFAULT_PARAMS
from strategies.order_block_btc.backtest.config import BTC_PARAMS
from strategies.order_block.backtest.data_loader import load_csv
from strategies.order_block.backtest.backtester_limit_orders import OrderBlockBacktesterLimitOrders

EXPIRY_VALUES = [100, 200, 300]

# ----------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------
def run_backtest(params, df_m5, df_m1):
    bt = OrderBlockBacktesterLimitOrders(params)
    trades = bt.run(df_m5, df_m1)
    if trades.empty:
        return None

    winners = trades[trades["pnl_usd"] > 0]
    losers  = trades[trades["pnl_usd"] < 0]
    n       = len(trades)
    wr      = len(winners) / n * 100
    pf_num  = winners["pnl_usd"].sum() if len(winners) > 0 else 0
    pf_den  = abs(losers["pnl_usd"].sum()) if len(losers) > 0 else 1
    pf      = pf_num / pf_den if pf_den > 0 else 0
    total   = trades["pnl_usd"].sum()
    ret     = total / params["initial_balance"] * 100

    peak, running, max_dd = params["initial_balance"], params["initial_balance"], 0
    for pnl in trades["pnl_usd"]:
        running += pnl
        if running > peak:
            peak = running
        dd = (peak - running) / peak * 100
        if dd > max_dd:
            max_dd = dd

    return {"trades": n, "wr": wr, "pf": pf, "total": total, "ret": ret, "dd": max_dd}


def print_table(symbol, results):
    print(f"\n{'='*62}")
    print(f"  {symbol}")
    print(f"{'='*62}")
    print(f"  {'Expiry':>8}  {'Trades':>7}  {'WR%':>6}  {'PF':>5}  {'Retorno':>9}  {'MaxDD':>7}  {'PnL $':>10}")
    print(f"  {'-'*58}")
    for exp, r in results.items():
        if r:
            print(f"  {exp:>8}  {r['trades']:>7}  {r['wr']:>5.1f}%  {r['pf']:>5.2f}  {r['ret']:>+8.1f}%  {r['dd']:>6.1f}%  ${r['total']:>+10,.0f}")
        else:
            print(f"  {exp:>8}  {'SIN TRADES':>50}")
    print(f"{'='*62}")


# ----------------------------------------------------------------
# US30 — 518 dias
# ----------------------------------------------------------------
print("\nCargando datos US30...")
df_m5_us  = load_csv('data/US30_icm_M5_518d.csv')
df_m1_us  = load_csv('data/US30_icm_M1_500k.csv')

us30_results = {}
for exp in EXPIRY_VALUES:
    p = copy.deepcopy(DEFAULT_PARAMS)
    p["expiry_candles"] = exp
    print(f"  US30 expiry={exp}...", end=" ", flush=True)
    r = run_backtest(p, df_m5_us, df_m1_us)
    us30_results[exp] = r
    print(f"OK — {r['trades']} trades | {r['ret']:+.1f}%" if r else "SIN TRADES")

# ----------------------------------------------------------------
# BTC — 351 dias
# ----------------------------------------------------------------
print("\nCargando datos BTC...")
df_m5_btc = load_csv('data/BTCUSD_icm_M5.csv')
df_m1_btc = load_csv('data/BTCUSD_icm_M1.csv')

btc_results = {}
for exp in EXPIRY_VALUES:
    p = copy.deepcopy(BTC_PARAMS)
    p["expiry_candles"] = exp
    print(f"  BTC  expiry={exp}...", end=" ", flush=True)
    r = run_backtest(p, df_m5_btc, df_m1_btc)
    btc_results[exp] = r
    print(f"OK — {r['trades']} trades | {r['ret']:+.1f}%" if r else "SIN TRADES")

# ----------------------------------------------------------------
# Tablas
# ----------------------------------------------------------------
print_table("US30 — 518 dias — Balance inicial $10,000", us30_results)
print_table("BTCUSD — 351 dias — Balance inicial $100,000", btc_results)

# Impacto relativo a baseline (expiry=100)
print("\n  IMPACTO vs BASELINE (expiry=100):")
print(f"\n  {'Symbol':>8}  {'Expiry':>8}  {'Delta Trades':>13}  {'Delta Ret':>10}  {'Delta DD':>9}")
print(f"  {'-'*55}")
for symbol, results in [("US30", us30_results), ("BTC", btc_results)]:
    base = results[100]
    if not base:
        continue
    for exp in [200, 300]:
        r = results[exp]
        if not r:
            continue
        dt = r["trades"] - base["trades"]
        dr = r["ret"]    - base["ret"]
        dd = r["dd"]     - base["dd"]
        print(f"  {symbol:>8}  {exp:>8}  {dt:>+13d}  {dr:>+9.1f}%  {dd:>+8.1f}%")
