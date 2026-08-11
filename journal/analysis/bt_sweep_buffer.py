# -*- coding: utf-8 -*-
"""
Barrido de BUFFER en ORO con el backtester FIEL (STOP = live), muestra completa.
Config real del oro (RR 2.5, London+NY, spread 0.4). Robustez por mitades + DD + mejor/ult 90d.
"""
import sys, copy
from pathlib import Path
if sys.platform == "win32":
    import codecs; sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import pandas as pd
from strategies.order_block.backtest.data_loader import load_csv
from strategies.order_block.backtest.backtester_limit_orders import OrderBlockBacktesterLimitOrders
from strategies.order_block_gold.backtest.config import GOLD_PARAMS

df5 = load_csv("data/XAUUSD_icm_M5_fresh.csv")
df1 = load_csv("data/XAUUSD_icm_M1_fresh.csv")
df5 = df5[(df5.time >= df1.time.iloc[0]) & (df5.time <= df1.time.iloc[-1])].reset_index(drop=True)

def pf(x):
    g = x[x > 0].sum(); l = abs(x[x <= 0].sum()); return g/l if l > 0 else 99

print(f"=== ORO — barrido BUFFER (STOP fiel) — {df1.time.iloc[0]:%Y-%m-%d} -> {df1.time.iloc[-1]:%Y-%m-%d} ===")
print(f"    (actual = 4.5)   RR {GOLD_PARAMS['target_rr']}  London+NY  spread {GOLD_PARAMS['avg_spread_points']}")
print(f" {'buf':>4} {'trades':>7} {'WR':>6} {'PF':>5} {'1a/2a':>10} {'robusta':>8} {'ret%':>7} {'DD%':>6} {'mej90':>7} {'ult90':>7}")
print(f" {'-'*76}")
for buf in [2, 3, 4.5, 6, 8, 10, 15]:
    p = copy.deepcopy(GOLD_PARAMS)
    p["buffer_points"] = buf
    res = OrderBlockBacktesterLimitOrders(p).run(df5, df1)
    if res is None or res.empty:
        print(f" {buf:>4}   sin trades"); continue
    res = res.sort_values("exit_time").reset_index(drop=True)
    n = len(res); wr = (res.pnl_r > 0).mean()*100; PF = pf(res.pnl_r)
    mid = n//2; p1, p2 = pf(res.pnl_r.iloc[:mid]), pf(res.pnl_r.iloc[mid:])
    rob = "SI" if PF > 1 and p1 > 1 and p2 > 1 else "no"
    cum = res.pnl_r.cumsum(); dd = (cum.cummax()-cum).max()*0.5
    tout = pd.to_datetime(res.exit_time)
    best90 = max((res.pnl_r[(tout >= s) & (tout < s+pd.Timedelta(days=90))].sum()*0.5 for s in tout), default=0.0)
    rec90 = res.pnl_r[tout >= tout.max()-pd.Timedelta(days=90)].sum()*0.5
    star = " *actual" if buf == 4.5 else ""
    print(f" {buf:>4} {n:>7} {wr:>5.1f}% {PF:>5.2f} {p1:>4.2f}/{p2:<4.2f} {rob:>8} "
          f"{res.pnl_r.sum()*0.5:>+6.1f} {dd:>5.1f} {best90:>+6.1f} {rec90:>+6.1f}{star}")
print(f" {'-'*76}")
print(" ret% = retorno a 0.5%/trade sobre toda la muestra | breakeven RR2.5 = WR 28.6%", flush=True)
