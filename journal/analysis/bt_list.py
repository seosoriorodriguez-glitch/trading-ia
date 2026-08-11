# -*- coding: utf-8 -*-
"""
Listado EXACTO de operaciones — TU estrategia (M1 cierra dentro -> orden STOP en el borde),
backtester FIEL (OrderBlockBacktesterLimitOrders = live), config REAL de cada bot.
Ultimos 14 dias de data disponible. Uso: python bt_list.py <oro|dax>
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
from strategies.order_block_dax.backtest.config import DAX_PARAMS
from strategies.order_block_london.backtest.config import LONDON_PARAMS

which = (sys.argv[1] if len(sys.argv) > 1 else "oro").lower()
if which == "oro":
    m5f, m1f, params, name, dec = "data/XAUUSD_icm_M5_fresh.csv", "data/XAUUSD_icm_M1_fresh.csv", GOLD_PARAMS, "ORO (XAUUSD)", 2
elif which == "us30":
    m5f, m1f, params, name, dec = "data/US30_icm_M5_fresh.csv", "data/US30_icm_M1_fresh.csv", LONDON_PARAMS, "US30 (London)", 1
else:
    m5f, m1f, params, name, dec = "data/DE40_icm_M5.csv", "data/DE40_icm_M1.csv", DAX_PARAMS, "DAX (DE40)", 1

df5 = load_csv(m5f); df1 = load_csv(m1f)
cutoff = df1.time.iloc[-1] - pd.Timedelta(days=14)
df1 = df1[df1.time >= cutoff].reset_index(drop=True)
# dar contexto M5 previo para detectar OBs que se operan en la ventana
df5 = df5[(df5.time >= cutoff - pd.Timedelta(days=10)) & (df5.time <= df1.time.iloc[-1])].reset_index(drop=True)

p = copy.deepcopy(params)
bt = OrderBlockBacktesterLimitOrders(p)
res = bt.run(df5, df1)

print(f"\n{'='*92}")
print(f" {name} — TU ESTRATEGIA (STOP en borde) — ultimos 14 dias: {df1.time.iloc[0]:%Y-%m-%d} -> {df1.time.iloc[-1]:%Y-%m-%d}")
print(f" spread {p['avg_spread_points']}  buffer {p['buffer_points']}  RR {p['target_rr']}  maxsim {p['max_simultaneous_trades']}")
print(f"{'='*92}")
if res is None or res.empty:
    print("  SIN OPERACIONES en la ventana."); sys.exit()
res = res.sort_values("entry_time").reset_index(drop=True)
fmt = f"%.{dec}f"
print(f" {'#':>2} {'entrada':<16} {'dir':<5} {'entry':>10} {'SL':>10} {'TP':>10} {'salida':<16} {'motivo':<6} {'R':>6}  res")
print(f" {'-'*90}")
for i, r in res.iterrows():
    win = r.pnl_r > 0
    print(f" {i+1:>2} {pd.Timestamp(r.entry_time):%m-%d %H:%M}    {r.direction:<5} "
          f"{fmt%r.entry_price:>10} {fmt%r.sl:>10} {fmt%r.tp:>10} "
          f"{pd.Timestamp(r.exit_time):%m-%d %H:%M}    {r.exit_reason:<6} {r.pnl_r:>+6.2f}  {'GANA' if win else 'PIERDE'}")
n = len(res); w = int((res.pnl_r > 0).sum()); l = n - w
print(f" {'-'*90}")
print(f" TOTAL {n} ops | {w} ganadoras / {l} perdedoras | WR {w/n*100:.0f}% | "
      f"SumaR {res.pnl_r.sum():+.2f} | Retorno(0.5%/trade) {res.pnl_r.sum()*0.5:+.1f}%")
print(f"{'='*92}\n")
