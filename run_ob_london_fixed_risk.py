# -*- coding: utf-8 -*-
"""
Backtest OB London con parametros LIVE (max 2 trades) — riesgo fijo $50.
Data: US30_icm_M5_518d + US30_icm_M1_500k
"""
import sys
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

from pathlib import Path
import copy

sys.path.insert(0, str(Path(__file__).parent))

from strategies.order_block_london.backtest.config import LONDON_PARAMS
from strategies.order_block.backtest.data_loader import load_csv, validate_alignment
from strategies.order_block.backtest.backtester_limit_orders import OrderBlockBacktesterLimitOrders

RISK_USD     = 50.0
ACCOUNT      = 10_000.0
FTMO_DAILY   = 4.0   # % del balance inicial

params = copy.deepcopy(LONDON_PARAMS)
params["initial_balance"] = ACCOUNT

M5_FILE = "data/US30_icm_M5_518d.csv"
M1_FILE = "data/US30_icm_M1_500k.csv"
OUT_CSV = "strategies/order_block_london/backtest/results/ob_london_fixed50.csv"

print("=" * 60)
print("  OB LONDON BACKTEST — PARAMETROS LIVE — RIESGO FIJO $50")
print("=" * 60)
print(f"\nParametros live:")
print(f"  consecutive_candles: {params['consecutive_candles']}")
print(f"  zone_type:           {params['zone_type']}")
print(f"  target_rr:           {params['target_rr']}")
print(f"  buffer_points:       {params['buffer_points']}")
print(f"  min/max_risk:        {params['min_risk_points']} / {params['max_risk_points']}")
print(f"  max_simultaneous:    {params['max_simultaneous_trades']}")
print(f"  sessions:            {list(params['sessions'].keys())}")
print(f"  riesgo fijo:         ${RISK_USD}")

print(f"\nCargando datos...")
df_m5 = load_csv(M5_FILE)
df_m1 = load_csv(M1_FILE)
validate_alignment(df_m5, df_m1)

print(f"  M5: {len(df_m5):,} velas")
print(f"  M1: {len(df_m1):,} velas")

print(f"\nEjecutando backtest...")
bt = OrderBlockBacktesterLimitOrders(params)
df = bt.run(df_m5, df_m1)

if df.empty:
    print("\n  SIN TRADES")
    sys.exit(1)

# Reescalar a riesgo fijo $50 usando pnl_r
df["pnl_fixed"] = df["pnl_r"] * RISK_USD

# Metricas
n       = len(df)
wins    = df[df["pnl_fixed"] > 0]
losses  = df[df["pnl_fixed"] < 0]
wr      = len(wins) / n * 100
pf      = wins["pnl_fixed"].sum() / abs(losses["pnl_fixed"].sum()) if len(losses) > 0 else float("inf")
total   = df["pnl_fixed"].sum()
ret     = total / ACCOUNT * 100
avg_win = wins["pnl_fixed"].mean() if len(wins) > 0 else 0
avg_r   = wins["pnl_r"].mean() if len(wins) > 0 else 0
avg_loss= losses["pnl_fixed"].mean() if len(losses) > 0 else 0

# Drawdown
cumul = df["pnl_fixed"].cumsum()
peak  = cumul.cummax()
dd    = (peak - cumul) / (ACCOUNT + peak) * 100
max_dd = dd.max()

# Por mes
df["exit_time"] = df.get("exit_time", df.get("entry_time"))
df["month"] = df["exit_time"].dt.to_period("M")
monthly = df.groupby("month").agg(
    trades=("pnl_fixed", "count"),
    pnl=("pnl_fixed", "sum"),
    wr=("pnl_fixed", lambda x: (x > 0).sum() / len(x) * 100),
).round(2)

neg_months = (monthly["pnl"] < 0).sum()
avg_month  = total / len(monthly)

# Dias bloqueados FTMO
df["date"] = df["exit_time"].dt.date
daily = df.groupby("date")["pnl_fixed"].sum()
ftmo_limit = ACCOUNT * FTMO_DAILY / 100
blocked = (daily < -ftmo_limit).sum()

# Long/Short
n_long  = len(df[df["direction"] == "long"])
n_short = len(df[df["direction"] == "short"])
wr_long  = len(df[(df["direction"]=="long")  & (df["pnl_fixed"]>0)]) / n_long  * 100 if n_long  > 0 else 0
wr_short = len(df[(df["direction"]=="short") & (df["pnl_fixed"]>0)]) / n_short * 100 if n_short > 0 else 0

# OB stats
ob_traded    = n
ob_expired   = sum(1 for _ in bt._trades if False)  # placeholder

period_start = df["entry_time"].iloc[0].date() if "entry_time" in df.columns else "?"
period_end   = df["exit_time"].iloc[-1].date()
days = (df["exit_time"].iloc[-1] - df["entry_time"].iloc[0]).days

print("\n" + "=" * 60)
print("  ORDER BLOCK BACKTEST - US30 (LONDON)")
print("=" * 60)
print(f"  Timeframes: M5 (OB detection) / M1 (entries)")
print(f"  Period: {period_start} -> {period_end}")
print(f"  Days: {days}")
print(f"")
print(f"  Total Trades:    {n}")
print(f"  Win Rate:        {wr:.1f}%")
print(f"  Profit Factor:   {pf:.2f}")
print(f"  Total Return:    {ret:+.2f}%")
print(f"  Final Balance:   ${ACCOUNT + total:,.2f}")
print(f"")
print(f"  Avg Win:         ${avg_win:,.0f} ({avg_r:.2f}R)")
print(f"  Avg Loss:        ${avg_loss:,.0f}")
print(f"  Max Drawdown:    {max_dd:.2f}%")
print(f"  Trades/Day:      {n/days:.2f}")
print(f"")
print(f"  LONG trades:  {n_long} (WR: {wr_long:.1f}%)")
print(f"  SHORT trades: {n_short} (WR: {wr_short:.1f}%)")
print(f"")
print(f"  London trades: {n} (WR: {wr:.1f}%)")
print("=" * 60)
print(f"")
print(f"--- OB London | MAX {params['max_simultaneous_trades']} TRADES | RR {params['target_rr']} | BUF {params['buffer_points']} | riesgo fijo $50 ---")
print(f"Trades:   {n}")
print(f"WR:       {wr:.1f}%")
print(f"PF:       {pf:.2f}")
print(f"Retorno:  {ret:+.1f}%")
print(f"Max DD:   {max_dd:.1f}%")
print(f"Ganancia/mes: ${avg_month:,.0f}")
print(f"Meses negativos: {neg_months} de {len(monthly)}")
print(f"Dias bloqueados FTMO: {blocked} de {len(daily)}")
print()

print("  POR MES:")
for month, row in monthly.iterrows():
    marker = " <--" if row["pnl"] < 0 else ""
    print(f"  {str(month):10s}: {int(row['trades']):4d} trades | PnL ${row['pnl']:+,.0f} | WR {row['wr']:.1f}%{marker}")

Path(OUT_CSV).parent.mkdir(parents=True, exist_ok=True)
df.to_csv(OUT_CSV, index=False)
print(f"\nCSV guardado en: {OUT_CSV}")
