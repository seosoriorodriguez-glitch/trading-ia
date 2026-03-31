# -*- coding: utf-8 -*-
"""
Backtest LIMIT ORDERS — US30 M5/M1 — ~106 días completos
Usa la misma configuración que el bot live actual.
"""
import sys
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

from pathlib import Path
import copy
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))

from strategies.order_block.backtest.config import DEFAULT_PARAMS
from strategies.order_block.backtest.data_loader import load_csv, validate_alignment
from strategies.order_block.backtest.backtester_limit_orders import OrderBlockBacktesterLimitOrders

params = copy.deepcopy(DEFAULT_PARAMS)

M5_FILE = "data/US30_cash_M5_260d.csv"
M1_FILE = "data/US30_cash_M1_260d.csv"

print("=" * 60)
print("  BACKTEST LIMIT/STOP ORDERS — US30 M5/M1")
print("  Configuración idéntica al bot live")
print("=" * 60)

print(f"\nParámetros:")
print(f"  consecutive_candles: {params['consecutive_candles']}")
print(f"  zone_type:           {params['zone_type']}")
print(f"  target_rr:           {params['target_rr']}")
print(f"  buffer_points:       {params['buffer_points']}")
print(f"  min/max_risk:        {params['min_risk_points']} / {params['max_risk_points']}")
print(f"  expiry_candles:      {params['expiry_candles']}")
print(f"  sessions:            {list(params['sessions'].keys())}")
print(f"  require_bos:         {params.get('require_bos', False)}")
print(f"  ema_trend_filter:    {params.get('ema_trend_filter', False)}")
print(f"  require_rejection:   {params.get('require_rejection', False)}")
print(f"  risk_per_trade_pct:  {params['risk_per_trade_pct']}")
print(f"  initial_balance:     ${params['initial_balance']:,.0f}")

print(f"\nCargando datos...")
df_m5 = load_csv(M5_FILE)
df_m1 = load_csv(M1_FILE)
validate_alignment(df_m5, df_m1)

print(f"  M5: {len(df_m5)} velas ({df_m5['time'].iloc[0]} -> {df_m5['time'].iloc[-1]})")
print(f"  M1: {len(df_m1)} velas ({df_m1['time'].iloc[0]} -> {df_m1['time'].iloc[-1]})")

m1_start = df_m1["time"].iloc[0]
m1_end = df_m1["time"].iloc[-1]
days = (m1_end - m1_start).days
print(f"  Período efectivo: {days} días ({m1_start.date()} -> {m1_end.date()})")

print(f"\nEjecutando backtest con OrderBlockBacktesterLimitOrders...")
bt = OrderBlockBacktesterLimitOrders(params)
df_results = bt.run(df_m5, df_m1)

if df_results.empty:
    print("\n  SIN TRADES GENERADOS")
    sys.exit(1)

n_trades = len(df_results)
winners = df_results[df_results["pnl_usd"] > 0]
losers = df_results[df_results["pnl_usd"] < 0]
n_long = len(df_results[df_results["direction"] == "long"])
n_short = len(df_results[df_results["direction"] == "short"])

wr = len(winners) / n_trades * 100
avg_win = winners["pnl_usd"].mean() if len(winners) > 0 else 0
avg_loss = losers["pnl_usd"].mean() if len(losers) > 0 else 0
total_pnl = df_results["pnl_usd"].sum()
total_ret = total_pnl / params["initial_balance"] * 100

peak = params["initial_balance"]
max_dd = 0
running = params["initial_balance"]
for pnl in df_results["pnl_usd"]:
    running += pnl
    if running > peak:
        peak = running
    dd = (peak - running) / peak * 100
    if dd > max_dd:
        max_dd = dd

pf_num = winners["pnl_usd"].sum() if len(winners) > 0 else 0
pf_den = abs(losers["pnl_usd"].sum()) if len(losers) > 0 else 1
profit_factor = pf_num / pf_den if pf_den > 0 else float("inf")

expectancy = df_results["pnl_usd"].mean()
expectancy_r = df_results["pnl_r"].mean() if "pnl_r" in df_results.columns else 0

long_pnl = df_results[df_results["direction"] == "long"]["pnl_usd"].sum()
short_pnl = df_results[df_results["direction"] == "short"]["pnl_usd"].sum()
long_wr = len(winners[winners.index.isin(df_results[df_results["direction"] == "long"].index)]) / n_long * 100 if n_long > 0 else 0
short_wr = len(winners[winners.index.isin(df_results[df_results["direction"] == "short"].index)]) / n_short * 100 if n_short > 0 else 0

print("\n" + "=" * 60)
print("  RESULTADOS — BACKTEST LIMIT/STOP ORDERS")
print("=" * 60)
print(f"  Período:          {days} días ({m1_start.date()} -> {m1_end.date()})")
print(f"  Total trades:     {n_trades}")
print(f"  Win Rate:         {wr:.1f}%  ({len(winners)}W / {len(losers)}L)")
print(f"  Profit Factor:    {profit_factor:.2f}")
print(f"  Expectancy:       ${expectancy:+,.0f} / trade")
print(f"  Expectancy (R):   {expectancy_r:+.3f}R / trade")
print(f"  ---")
print(f"  Total PnL:        ${total_pnl:+,.0f}")
print(f"  Retorno:          {total_ret:+.2f}%")
print(f"  Max Drawdown:     {max_dd:.2f}%")
print(f"  Balance final:    ${params['initial_balance'] + total_pnl:,.0f}")
print(f"  ---")
print(f"  LONG:  {n_long} trades  WR {long_wr:.1f}%  PnL ${long_pnl:+,.0f}")
print(f"  SHORT: {n_short} trades  WR {short_wr:.1f}%  PnL ${short_pnl:+,.0f}")
print(f"  ---")
print(f"  Avg Win:          ${avg_win:+,.0f}")
print(f"  Avg Loss:         ${avg_loss:+,.0f}")

tp_trades = df_results[df_results["exit_reason"] == "tp"]
sl_trades = df_results[df_results["exit_reason"] == "sl"]
eod_trades = df_results[df_results["exit_reason"] == "end_of_data"]
print(f"  ---")
print(f"  TP hits:          {len(tp_trades)}")
print(f"  SL hits:          {len(sl_trades)}")
if len(eod_trades) > 0:
    print(f"  End of data:      {len(eod_trades)}")

print("\n" + "=" * 60)
print("  ÚLTIMAS 20 OPERACIONES")
print("=" * 60)
last20 = df_results.tail(20)
print(f"{'#':>3} {'Dir':>5} {'Entry':>10} {'SL':>10} {'TP':>10} {'Exit':>10} {'Reason':>6} {'PnL':>10} {'R':>6} {'Entry Time'}")
print("-" * 100)
for _, row in last20.iterrows():
    print(f"{row['trade_id']:3d} {row['direction']:>5} {row['entry_price']:10.1f} {row['sl']:10.1f} {row['tp']:10.1f} {row['exit_price']:10.1f} {row['exit_reason']:>6} ${row['pnl_usd']:+9,.0f} {row['pnl_r']:+5.2f}R {row['entry_time']}")

out_file = "strategies/order_block/backtest/results/ob_limit_106d.csv"
Path(out_file).parent.mkdir(parents=True, exist_ok=True)
df_results.to_csv(out_file, index=False)
print(f"\nTrades guardados en: {out_file}")
