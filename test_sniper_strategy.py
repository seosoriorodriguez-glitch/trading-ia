# -*- coding: utf-8 -*-
"""
Backtest "Sniper Entry/Exit Strategy" - Replica TradingView
Basado en KhanSaab V.02

CONCEPTO:
- Entry: Cruce EMA 9/21
- Confirmación: Score bull/bear (7 indicadores)
- SL: ATR × 1.5
- TP: Escalonados 1R, 2R, 3R, 4R, 5R (20% cada uno)
- Risk: 0.5% por trade

INDICADORES:
1. VWAP (precio sobre/bajo)
2. RSI (> 50 / < 50)
3. MACD (línea vs señal)
4. EMA 9/21 (posición relativa)
5. ADX (> 25 + precio vs EMA9)
6. Volumen (> promedio + vela alcista/bajista)
7. RSI 5min (> 50 / < 50)
"""
import sys
import codecs
if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

from pathlib import Path
import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))

print("\n" + "="*70)
print("  BACKTEST SNIPER STRATEGY (KhanSaab V.02)")
print("  Cruce EMA 9/21 + Score Multi-Indicador + TPs Escalonados")
print("="*70)

# Cargar datos M5
df = pd.read_csv("data/US30_cash_M5_260d.csv")
df["time"] = pd.to_datetime(df["time"])
df = df.sort_values("time").reset_index(drop=True)

print(f"\nDatos cargados: {len(df):,} velas M5")
print(f"Periodo completo: {df['time'].iloc[0]} -> {df['time'].iloc[-1]}")

# Filtrar período específico: 1 feb - 30 mar 2026
print("\nFiltrando período: 1 febrero - 30 marzo 2026...")
df = df[(df["time"] >= "2026-02-01") & (df["time"] <= "2026-03-30")].reset_index(drop=True)
print(f"Período filtrado: {len(df):,} velas M5")
print(f"Rango: {df['time'].iloc[0]} -> {df['time'].iloc[-1]}")

# Calcular indicadores
print("\nCalculando indicadores...")

# EMAs
df["ema9"] = df["close"].ewm(span=9, adjust=False).mean()
df["ema21"] = df["close"].ewm(span=21, adjust=False).mean()

# VWAP (resetea cada día)
df["date"] = df["time"].dt.date
df["typical_price"] = (df["high"] + df["low"] + df["close"]) / 3
df["vwap"] = df.groupby("date", group_keys=False).apply(
    lambda x: ((x["typical_price"] * x["volume"]).cumsum() / x["volume"].cumsum())
).reset_index(drop=True)

# ATR
df["atr"] = df[["high", "low", "close"]].apply(
    lambda x: max(x["high"] - x["low"], 
                  abs(x["high"] - df["close"].shift(1).loc[x.name]) if x.name > 0 else 0,
                  abs(x["low"] - df["close"].shift(1).loc[x.name]) if x.name > 0 else 0),
    axis=1
).rolling(14).mean()

# RSI
def calc_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

df["rsi"] = calc_rsi(df["close"], 14)

# MACD
exp1 = df["close"].ewm(span=12, adjust=False).mean()
exp2 = df["close"].ewm(span=26, adjust=False).mean()
df["macd"] = exp1 - exp2
df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()

# ADX (simplificado)
df["adx"] = 25.0  # Placeholder (ADX completo es complejo)

# Volume average
df["vol_avg"] = df["volume"].rolling(20).mean()

# RSI 5min (placeholder - usamos mismo RSI por simplicidad)
df["rsi_5m"] = df["rsi"]

# Señales de cruce
df["ema_cross_up"] = (df["ema9"] > df["ema21"]) & (df["ema9"].shift(1) <= df["ema21"].shift(1))
df["ema_cross_down"] = (df["ema9"] < df["ema21"]) & (df["ema9"].shift(1) >= df["ema21"].shift(1))

# Score bull/bear
df["bull_score"] = (
    (df["close"] > df["vwap"]).astype(int) +
    (df["rsi"] > 50).astype(int) +
    (df["macd"] > df["macd_signal"]).astype(int) +
    (df["ema9"] > df["ema21"]).astype(int) +
    ((df["adx"] > 25) & (df["close"] > df["ema9"])).astype(int) +
    ((df["volume"] > df["vol_avg"]) & (df["close"] > df["open"])).astype(int) +
    (df["rsi_5m"] > 50).astype(int)
)
df["bull_pct"] = (df["bull_score"] / 7.0) * 100

df["bear_score"] = (
    (df["close"] < df["vwap"]).astype(int) +
    (df["rsi"] < 50).astype(int) +
    (df["macd"] < df["macd_signal"]).astype(int) +
    (df["ema9"] < df["ema21"]).astype(int) +
    ((df["adx"] > 25) & (df["close"] < df["ema9"])).astype(int) +
    ((df["volume"] > df["vol_avg"]) & (df["close"] < df["open"])).astype(int) +
    (df["rsi_5m"] < 50).astype(int)
)
df["bear_pct"] = (df["bear_score"] / 7.0) * 100

print(f"Cruces EMA detectados: {df['ema_cross_up'].sum()} up, {df['ema_cross_down'].sum()} down")

# Parámetros
INITIAL_BALANCE = 100_000
RISK_PCT = 0.005  # 0.5% por trade
ATR_MULT = 1.5
MIN_BULL_PCT = 57.0
MIN_BEAR_PCT = 57.0
REQUIRE_VWAP_SIDE = True
SPREAD_POINTS = 2
POINT_VALUE = 1.0

# TPs escalonados (20% cada uno)
TP_LEVELS = [1, 2, 3, 4, 5]  # R-multiples
TP_PERCENTS = [0.20, 0.20, 0.20, 0.20, 0.20]

print("\nParámetros:")
print(f"  Risk: {RISK_PCT*100}% por trade")
print(f"  SL: ATR × {ATR_MULT}")
print(f"  TPs: 1R, 2R, 3R, 4R, 5R (20% cada uno)")
print(f"  Min Bull Score: {MIN_BULL_PCT}%")
print(f"  Min Bear Score: {MIN_BEAR_PCT}%")

# Backtest
print("\nEjecutando backtest...")
balance = INITIAL_BALANCE
trades = []
in_position = False
current_trade = None
last_signal_direction = None

for i in range(50, len(df)):  # Start at 50 for indicators warmup
    row = df.iloc[i]
    
    # Cerrar trade si existe (TPs escalonados)
    if in_position and current_trade is not None:
        closed = False
        
        if current_trade["direction"] == "long":
            # Check SL primero
            if row["low"] <= current_trade["sl"]:
                pnl_pts = current_trade["sl"] - current_trade["entry_price"] - SPREAD_POINTS
                pnl_usd = (pnl_pts / current_trade["risk_pts"]) * current_trade["risk_usd"]
                balance += pnl_usd
                
                trades.append({
                    **current_trade,
                    "exit_price": current_trade["sl"],
                    "exit_time": row["time"],
                    "exit_reason": "sl",
                    "pnl_points": pnl_pts,
                    "pnl_usd": pnl_usd,
                    "pnl_r": pnl_pts / current_trade["risk_pts"],
                    "balance": balance
                })
                in_position = False
                current_trade = None
                closed = True
            
            # Check TPs (escalonados)
            if not closed:
                for tp_idx, (tp_r, tp_pct) in enumerate(zip(TP_LEVELS, TP_PERCENTS)):
                    tp_price = current_trade["entry_price"] + (current_trade["risk_pts"] * tp_r)
                    
                    if row["high"] >= tp_price and not current_trade.get(f"tp{tp_idx+1}_hit", False):
                        # TP hit - cerrar parcial
                        pnl_pts = (tp_price - current_trade["entry_price"] - SPREAD_POINTS) * tp_pct
                        pnl_usd = (pnl_pts / current_trade["risk_pts"]) * current_trade["risk_usd"]
                        balance += pnl_usd
                        
                        trades.append({
                            **current_trade,
                            "exit_price": tp_price,
                            "exit_time": row["time"],
                            "exit_reason": f"tp{tp_idx+1}",
                            "pnl_points": pnl_pts,
                            "pnl_usd": pnl_usd,
                            "pnl_r": tp_r * tp_pct,
                            "balance": balance,
                            "partial": True
                        })
                        
                        current_trade[f"tp{tp_idx+1}_hit"] = True
                        
                        # Si todos los TPs fueron hit, cerrar posición
                        if all(current_trade.get(f"tp{j+1}_hit", False) for j in range(5)):
                            in_position = False
                            current_trade = None
                            closed = True
                            break
        
        else:  # short
            # Check SL primero
            if row["high"] >= current_trade["sl"]:
                pnl_pts = current_trade["entry_price"] - current_trade["sl"] - SPREAD_POINTS
                pnl_usd = (pnl_pts / current_trade["risk_pts"]) * current_trade["risk_usd"]
                balance += pnl_usd
                
                trades.append({
                    **current_trade,
                    "exit_price": current_trade["sl"],
                    "exit_time": row["time"],
                    "exit_reason": "sl",
                    "pnl_points": pnl_pts,
                    "pnl_usd": pnl_usd,
                    "pnl_r": pnl_pts / current_trade["risk_pts"],
                    "balance": balance
                })
                in_position = False
                current_trade = None
                closed = True
            
            # Check TPs
            if not closed:
                for tp_idx, (tp_r, tp_pct) in enumerate(zip(TP_LEVELS, TP_PERCENTS)):
                    tp_price = current_trade["entry_price"] - (current_trade["risk_pts"] * tp_r)
                    
                    if row["low"] <= tp_price and not current_trade.get(f"tp{tp_idx+1}_hit", False):
                        pnl_pts = (current_trade["entry_price"] - tp_price - SPREAD_POINTS) * tp_pct
                        pnl_usd = (pnl_pts / current_trade["risk_pts"]) * current_trade["risk_usd"]
                        balance += pnl_usd
                        
                        trades.append({
                            **current_trade,
                            "exit_price": tp_price,
                            "exit_time": row["time"],
                            "exit_reason": f"tp{tp_idx+1}",
                            "pnl_points": pnl_pts,
                            "pnl_usd": pnl_usd,
                            "pnl_r": tp_r * tp_pct,
                            "balance": balance,
                            "partial": True
                        })
                        
                        current_trade[f"tp{tp_idx+1}_hit"] = True
                        
                        if all(current_trade.get(f"tp{j+1}_hit", False) for j in range(5)):
                            in_position = False
                            current_trade = None
                            closed = True
                            break
    
    # Nueva entrada
    if not in_position:
        # Long signal
        if row["ema_cross_up"]:
            # Filtros
            vwap_ok = not REQUIRE_VWAP_SIDE or row["close"] > row["vwap"]
            score_ok = row["bull_pct"] >= MIN_BULL_PCT and row["bull_pct"] > row["bear_pct"]
            direction_ok = last_signal_direction != "long"  # No repetir
            
            if vwap_ok and score_ok and direction_ok:
                risk_pts = row["atr"] * ATR_MULT
                risk_usd = balance * RISK_PCT
                
                current_trade = {
                    "direction": "long",
                    "entry_price": row["close"],
                    "sl": row["close"] - risk_pts,
                    "risk_pts": risk_pts,
                    "risk_usd": risk_usd,
                    "entry_time": row["time"],
                    "bull_score": row["bull_pct"],
                    "bear_score": row["bear_pct"],
                    "balance_at_entry": balance
                }
                in_position = True
                last_signal_direction = "long"
        
        # Short signal
        elif row["ema_cross_down"]:
            vwap_ok = not REQUIRE_VWAP_SIDE or row["close"] < row["vwap"]
            score_ok = row["bear_pct"] >= MIN_BEAR_PCT and row["bear_pct"] > row["bull_pct"]
            direction_ok = last_signal_direction != "short"
            
            if vwap_ok and score_ok and direction_ok:
                risk_pts = row["atr"] * ATR_MULT
                risk_usd = balance * RISK_PCT
                
                current_trade = {
                    "direction": "short",
                    "entry_price": row["close"],
                    "sl": row["close"] + risk_pts,
                    "risk_pts": risk_pts,
                    "risk_usd": risk_usd,
                    "entry_time": row["time"],
                    "bull_score": row["bull_pct"],
                    "bear_score": row["bear_pct"],
                    "balance_at_entry": balance
                }
                in_position = True
                last_signal_direction = "short"

# Resultados
df_trades = pd.DataFrame(trades)

if len(df_trades) == 0:
    print("\nNo se generaron trades.")
    sys.exit(0)

# Guardar
df_trades.to_csv("strategies/order_block/backtest/results/sniper_strategy_test.csv", index=False)

# Análisis
total_trades = len(df_trades)
wins = df_trades[df_trades["pnl_usd"] > 0]
losses = df_trades[df_trades["pnl_usd"] <= 0]
wr = len(wins) / total_trades * 100 if total_trades > 0 else 0
pf = wins["pnl_usd"].sum() / abs(losses["pnl_usd"].sum()) if len(losses) > 0 and losses["pnl_usd"].sum() != 0 else float('inf')
ret = (balance - INITIAL_BALANCE) / INITIAL_BALANCE * 100

# Max DD
peak = INITIAL_BALANCE
max_dd = 0
for b in df_trades["balance"]:
    if b > peak:
        peak = b
    dd = (peak - b) / peak * 100
    if dd > max_dd:
        max_dd = dd

days = (df_trades["exit_time"].max() - df_trades["entry_time"].min()).days

# Análisis de TPs
tp_counts = {}
for reason in ["tp1", "tp2", "tp3", "tp4", "tp5", "sl"]:
    tp_counts[reason] = len(df_trades[df_trades["exit_reason"] == reason])

print("\n" + "="*70)
print("  RESULTADOS GENERALES")
print("="*70)
print(f"  Total trades:    {total_trades}")
print(f"  Win Rate:        {wr:.1f}%")
print(f"  Profit Factor:   {pf:.2f}")
print(f"  Retorno:         {ret:+.2f}%")
print(f"  Balance final:   ${balance:,.2f}")
print(f"  Max Drawdown:    {max_dd:.2f}%")
print(f"  Trades/día:      {total_trades/days:.2f}")
if len(wins) > 0:
    print(f"  Avg Win:         ${wins['pnl_usd'].mean():.2f}")
if len(losses) > 0:
    print(f"  Avg Loss:        ${losses['pnl_usd'].mean():.2f}")

print("\n" + "="*70)
print("  DISTRIBUCIÓN DE EXITS")
print("="*70)
for reason, count in tp_counts.items():
    pct = count / total_trades * 100 if total_trades > 0 else 0
    print(f"  {reason.upper()}: {count} ({pct:.1f}%)")

# Por dirección
print("\n" + "="*70)
print("  RESULTADOS POR DIRECCIÓN")
print("="*70)

for direction in ["long", "short"]:
    dir_trades = df_trades[df_trades["direction"] == direction]
    if len(dir_trades) == 0:
        continue
    
    dir_wins = dir_trades[dir_trades["pnl_usd"] > 0]
    dir_wr = len(dir_wins) / len(dir_trades) * 100
    dir_pnl = dir_trades["pnl_usd"].sum()
    
    print(f"\n  {direction.upper()}:")
    print(f"    Trades:    {len(dir_trades)}")
    print(f"    Win Rate:  {dir_wr:.1f}%")
    print(f"    PnL total: ${dir_pnl:+,.2f}")

print("\n" + "="*70)
print(f"  Resultados guardados en: strategies/order_block/backtest/results/sniper_strategy_test.csv")
print("="*70 + "\n")
