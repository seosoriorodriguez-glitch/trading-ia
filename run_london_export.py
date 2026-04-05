# -*- coding: utf-8 -*-
"""
Backtest Bot 2 London con exportacion de datos detallados.
Genera 3 archivos en strategies/order_block_london/backtest/results/:
  - ob_zones.csv   : todos los OBs detectados con estado final
  - trades.csv     : cada trade con entry/exit/pnl/balance
  - equity.csv     : serie temporal de balance y drawdown

Uso: python run_london_export.py
"""
import sys, copy
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")

sys.path.insert(0, '.')

import pandas as pd
from pathlib import Path
from strategies.order_block_london.backtest.config import LONDON_PARAMS
from strategies.order_block.backtest.data_loader import load_csv
from strategies.order_block.backtest.backtester_limit_orders import OrderBlockBacktesterLimitOrders
from strategies.order_block.backtest.ob_detection import detect_order_blocks, OBStatus

OUT_DIR = Path("strategies/order_block_london/backtest/results")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ----------------------------------------------------------------
# 1. Cargar datos
# ----------------------------------------------------------------
print("Cargando datos US30 (518 dias)...")
df_m5 = load_csv("data/US30_icm_M5_518d.csv")
df_m1 = load_csv("data/US30_icm_M1_500k.csv")
print(f"  M5: {len(df_m5):,} velas | M1: {len(df_m1):,} velas")

# ----------------------------------------------------------------
# 2. Correr backtest
# ----------------------------------------------------------------
params = copy.deepcopy(LONDON_PARAMS)
print("\nCorriendo backtest Bot 2 London...")
bt = OrderBlockBacktesterLimitOrders(params)
trades_df = bt.run(df_m5, df_m1)
print(f"  Trades generados: {len(trades_df)}")

# ----------------------------------------------------------------
# 3. ob_zones.csv
# ----------------------------------------------------------------
print("\nGenerando ob_zones.csv...")

# Usar los OBs que ya pasaron por el backtester (tienen status actualizado)
# bt._trades contiene los trades con referencia al OB original
all_obs = detect_order_blocks(df_m5, params)

# Construir lookup de OBs tocados desde trades
touched_obs = {}  # key=(zone_high, zone_low, confirmed_at) -> trade row
if not trades_df.empty:
    for _, row in trades_df.iterrows():
        key = (row["ob_zone_high"], row["ob_zone_low"], row["ob_confirmed_at"])
        touched_obs[key] = row

# Reconstruir estado via logica del backtester sobre M5
m5_times  = df_m5["time"].tolist()
m5_closes = df_m5["close"].tolist()
expiry    = params["expiry_candles"]

import bisect

ob_records = []
for ob in all_obs:
    key = (ob.zone_high, ob.zone_low, ob.confirmed_at)

    # Si fue tocado (generó trade)
    if key in touched_obs:
        trade_match = touched_obs[key]
        ob_records.append({
            "confirmed_at":  ob.confirmed_at,
            "ob_type":       ob.ob_type,
            "zone_low":      round(ob.zone_low, 2),
            "zone_high":     round(ob.zone_high, 2),
            "zone_size":     round(ob.zone_high - ob.zone_low, 2),
            "estado_final":  "tocado",
            "entry_time":    trade_match["entry_time"],
            "exit_time":     trade_match["exit_time"],
            "exit_reason":   trade_match["exit_reason"],
            "pnl_usd":       trade_match["pnl_usd"],
        })
        continue

    # Determinar si fue destruido, expirado o sigue activo
    ob_conf = ob.confirmed_at
    idx_start = bisect.bisect_left(m5_times, ob_conf)
    estado = "activo"
    candles_since = 0
    for j in range(idx_start, len(m5_times)):
        c = m5_closes[j]
        if ob.ob_type == "bullish" and c < ob.zone_low:
            estado = "destruido"
            break
        if ob.ob_type == "bearish" and c > ob.zone_high:
            estado = "destruido"
            break
        candles_since += 1
        if candles_since >= expiry:
            estado = "expirado"
            break

    ob_records.append({
        "confirmed_at":  ob.confirmed_at,
        "ob_type":       ob.ob_type,
        "zone_low":      round(ob.zone_low, 2),
        "zone_high":     round(ob.zone_high, 2),
        "zone_size":     round(ob.zone_high - ob.zone_low, 2),
        "estado_final":  estado,
        "entry_time":    None,
        "exit_time":     None,
        "exit_reason":   None,
        "pnl_usd":       None,
    })

ob_zones_df = pd.DataFrame(ob_records).sort_values("confirmed_at").reset_index(drop=True)
ob_zones_df.to_csv(OUT_DIR / "ob_zones.csv", index=False)
print(f"  {len(ob_zones_df)} OBs exportados -> ob_zones.csv")

# Distribucion de estados
for estado, cnt in ob_zones_df["estado_final"].value_counts().items():
    print(f"    {estado}: {cnt}")

# ----------------------------------------------------------------
# 4. trades.csv
# ----------------------------------------------------------------
print("\nGenerando trades.csv...")

if not trades_df.empty:
    # Calcular balance post trade y drawdown
    running = params["initial_balance"]
    peak    = params["initial_balance"]
    balance_post = []
    pnl_pct_list = []
    dd_list      = []

    for _, row in trades_df.iterrows():
        running += row["pnl_usd"]
        if running > peak:
            peak = running
        balance_post.append(round(running, 2))
        pnl_pct_list.append(round(row["pnl_usd"] / params["initial_balance"] * 100, 4))
        dd_list.append(round((peak - running) / peak * 100, 4))

    trades_export = pd.DataFrame({
        "trade_id":          trades_df["trade_id"],
        "entry_time":        trades_df["entry_time"],
        "exit_time":         trades_df["exit_time"],
        "tipo":              trades_df["direction"].str.upper(),
        "entry_price":       trades_df["entry_price"],
        "sl_price":          trades_df["sl"],
        "tp_price":          trades_df["tp"],
        "exit_price":        trades_df["exit_price"],
        "exit_reason":       trades_df["exit_reason"],
        "pnl_usd":           trades_df["pnl_usd"],
        "pnl_pct":           pnl_pct_list,
        "pnl_r":             trades_df["pnl_r"],
        "balance_post_trade": balance_post,
        "drawdown_pct":      dd_list,
        "session":           trades_df["session"],
        "ob_zone_low":       trades_df["ob_zone_low"],
        "ob_zone_high":      trades_df["ob_zone_high"],
    })

    trades_export.to_csv(OUT_DIR / "trades.csv", index=False)
    print(f"  {len(trades_export)} trades exportados -> trades.csv")

# ----------------------------------------------------------------
# 5. equity.csv
# ----------------------------------------------------------------
print("\nGenerando equity.csv...")

equity_records = []
running = params["initial_balance"]
peak    = params["initial_balance"]

for ts, bal in bt._equity_curve:
    if bal > peak:
        peak = bal
    dd = round((peak - bal) / peak * 100, 4) if peak > 0 else 0.0
    equity_records.append({
        "timestamp":     ts,
        "balance":       round(bal, 2),
        "drawdown_pct":  dd,
    })

equity_df = pd.DataFrame(equity_records)
equity_df.to_csv(OUT_DIR / "equity.csv", index=False)
print(f"  {len(equity_df):,} puntos de equity exportados -> equity.csv")

# ----------------------------------------------------------------
# 6. Resumen final
# ----------------------------------------------------------------
if not trades_df.empty:
    winners = trades_df[trades_df["pnl_usd"] > 0]
    losers  = trades_df[trades_df["pnl_usd"] < 0]
    total   = trades_df["pnl_usd"].sum()
    wr      = len(winners) / len(trades_df) * 100
    pf      = winners["pnl_usd"].sum() / abs(losers["pnl_usd"].sum())
    ret     = total / params["initial_balance"] * 100
    max_dd  = equity_df["drawdown_pct"].max()

    print(f"\n{'='*55}")
    print(f"  RESUMEN BOT 2 LONDON — 518 dias")
    print(f"{'='*55}")
    print(f"  Trades:   {len(trades_df)}")
    print(f"  WR:       {wr:.1f}%")
    print(f"  PF:       {pf:.2f}")
    print(f"  Retorno:  {ret:+.1f}%")
    print(f"  Max DD:   {max_dd:.1f}%")
    print(f"  PnL:      ${total:+,.0f}")
    print(f"\n  Archivos en: {OUT_DIR}/")
    print(f"    ob_zones.csv  — {len(ob_zones_df)} OBs")
    print(f"    trades.csv    — {len(trades_export)} trades")
    print(f"    equity.csv    — {len(equity_df):,} puntos")
    print(f"{'='*55}")
