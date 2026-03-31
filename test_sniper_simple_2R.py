# -*- coding: utf-8 -*-
"""
Backtest "Sniper Entry/Exit Strategy" - VERSIÓN SIMPLIFICADA
Basado en KhanSaab V.02

CAMBIOS vs versión original:
- TP FIJO: 2:1 (sin parciales)
- MISMA lógica de entrada (cruce EMA + score)
- SL: ATR × 1.5
- Risk: 0.5% por trade

LÓGICA DE ENTRADA (LONG):
1. Cruce alcista EMA 9 > EMA 21
2. Score bull >= 57% (4/7 indicadores alcistas)
3. Precio > VWAP (opcional según REQUIRE_VWAP_SIDE)
4. No hay trade activo en esa dirección

INDICADORES PARA SCORE (7 total):
1. Precio > VWAP
2. RSI > 50
3. MACD > Signal
4. EMA9 > EMA21
5. ADX > 25 Y precio > EMA9
6. Volumen > promedio Y vela alcista
7. RSI 5min > 50
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
print("  BACKTEST SNIPER STRATEGY - SIMPLIFICADO (TP 2:1 FIJO)")
print("  Cruce EMA 9/21 + Score Multi-Indicador")
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
df["adx"] = 25.0  # Placeholder

# Volume average
df["vol_avg"] = df["volume"].rolling(20).mean()

# RSI 5min (placeholder - usamos mismo RSI)
df["rsi_5m"] = df["rsi"]

# Señales de cruce
df["ema_cross_up"] = (df["ema9"] > df["ema21"]) & (df["ema9"].shift(1) <= df["ema21"].shift(1))
df["ema_cross_down"] = (df["ema9"] < df["ema21"]) & (df["ema9"].shift(1) >= df["ema21"].shift(1))

# Score bull/bear (7 indicadores)
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
RR_RATIO = 2.0  # TP FIJO 2:1
MIN_BULL_PCT = 57.0
MIN_BEAR_PCT = 57.0
REQUIRE_VWAP_SIDE = True
SPREAD_POINTS = 2
POINT_VALUE = 1.0

print("\nParámetros:")
print(f"  Risk: {RISK_PCT*100}% por trade")
print(f"  SL: ATR × {ATR_MULT}")
print(f"  TP: {RR_RATIO}:1 (FIJO, sin parciales)")
print(f"  Min Bull Score: {MIN_BULL_PCT}%")
print(f"  Min Bear Score: {MIN_BEAR_PCT}%")
print(f"  Require VWAP side: {REQUIRE_VWAP_SIDE}")

# Backtest
balance = INITIAL_BALANCE
trades = []
open_trade = None
last_signal_direction = None

for i in range(30, len(df)):
    row = df.iloc[i]
    
    # Gestionar trade abierto
    if open_trade:
        direction = open_trade["direction"]
        
        if direction == "long":
            # Check TP
            if row["high"] >= open_trade["tp"]:
                pnl = (open_trade["tp"] - open_trade["entry"]) * open_trade["qty"] * POINT_VALUE
                balance += pnl
                trades.append({
                    "entry_time": open_trade["entry_time"],
                    "exit_time": row["time"],
                    "direction": "long",
                    "entry": open_trade["entry"],
                    "exit": open_trade["tp"],
                    "sl": open_trade["sl"],
                    "tp": open_trade["tp"],
                    "qty": open_trade["qty"],
                    "pnl": pnl,
                    "exit_type": "TP",
                    "balance": balance
                })
                open_trade = None
                last_signal_direction = None
            # Check SL
            elif row["low"] <= open_trade["sl"]:
                pnl = (open_trade["sl"] - open_trade["entry"]) * open_trade["qty"] * POINT_VALUE
                balance += pnl
                trades.append({
                    "entry_time": open_trade["entry_time"],
                    "exit_time": row["time"],
                    "direction": "long",
                    "entry": open_trade["entry"],
                    "exit": open_trade["sl"],
                    "sl": open_trade["sl"],
                    "tp": open_trade["tp"],
                    "qty": open_trade["qty"],
                    "pnl": pnl,
                    "exit_type": "SL",
                    "balance": balance
                })
                open_trade = None
                last_signal_direction = None
        
        elif direction == "short":
            # Check TP
            if row["low"] <= open_trade["tp"]:
                pnl = (open_trade["entry"] - open_trade["tp"]) * open_trade["qty"] * POINT_VALUE
                balance += pnl
                trades.append({
                    "entry_time": open_trade["entry_time"],
                    "exit_time": row["time"],
                    "direction": "short",
                    "entry": open_trade["entry"],
                    "exit": open_trade["tp"],
                    "sl": open_trade["sl"],
                    "tp": open_trade["tp"],
                    "qty": open_trade["qty"],
                    "pnl": pnl,
                    "exit_type": "TP",
                    "balance": balance
                })
                open_trade = None
                last_signal_direction = None
            # Check SL
            elif row["high"] >= open_trade["sl"]:
                pnl = (open_trade["entry"] - open_trade["sl"]) * open_trade["qty"] * POINT_VALUE
                balance += pnl
                trades.append({
                    "entry_time": open_trade["entry_time"],
                    "exit_time": row["time"],
                    "direction": "short",
                    "entry": open_trade["entry"],
                    "exit": open_trade["sl"],
                    "sl": open_trade["sl"],
                    "tp": open_trade["tp"],
                    "qty": open_trade["qty"],
                    "pnl": pnl,
                    "exit_type": "SL",
                    "balance": balance
                })
                open_trade = None
                last_signal_direction = None
        
        continue
    
    # Buscar nuevas entradas
    # LONG
    if row["ema_cross_up"]:
        vwap_ok = not REQUIRE_VWAP_SIDE or row["close"] > row["vwap"]
        score_ok = row["bull_pct"] >= MIN_BULL_PCT and row["bull_pct"] > row["bear_pct"]
        direction_ok = last_signal_direction != "long"
        
        if vwap_ok and score_ok and direction_ok:
            entry_price = row["close"] + SPREAD_POINTS
            risk_pts = row["atr"] * ATR_MULT
            sl_price = entry_price - risk_pts
            tp_price = entry_price + (risk_pts * RR_RATIO)
            
            risk_usd = balance * RISK_PCT
            qty = risk_usd / (risk_pts * POINT_VALUE)
            
            open_trade = {
                "entry_time": row["time"],
                "direction": "long",
                "entry": entry_price,
                "sl": sl_price,
                "tp": tp_price,
                "qty": qty,
                "risk_pts": risk_pts
            }
            last_signal_direction = "long"
    
    # SHORT
    elif row["ema_cross_down"]:
        vwap_ok = not REQUIRE_VWAP_SIDE or row["close"] < row["vwap"]
        score_ok = row["bear_pct"] >= MIN_BEAR_PCT and row["bear_pct"] > row["bull_pct"]
        direction_ok = last_signal_direction != "short"
        
        if vwap_ok and score_ok and direction_ok:
            entry_price = row["close"] - SPREAD_POINTS
            risk_pts = row["atr"] * ATR_MULT
            sl_price = entry_price + risk_pts
            tp_price = entry_price - (risk_pts * RR_RATIO)
            
            risk_usd = balance * RISK_PCT
            qty = risk_usd / (risk_pts * POINT_VALUE)
            
            open_trade = {
                "entry_time": row["time"],
                "direction": "short",
                "entry": entry_price,
                "sl": sl_price,
                "tp": tp_price,
                "qty": qty,
                "risk_pts": risk_pts
            }
            last_signal_direction = "short"

# Resultados
print("\n" + "="*70)
print("  RESULTADOS")
print("="*70)

if not trades:
    print("\n⚠️  No se ejecutaron trades en el período analizado")
else:
    df_trades = pd.DataFrame(trades)
    
    total_trades = len(df_trades)
    winners = df_trades[df_trades["pnl"] > 0]
    losers = df_trades[df_trades["pnl"] < 0]
    
    win_rate = len(winners) / total_trades * 100
    avg_win = winners["pnl"].mean() if len(winners) > 0 else 0
    avg_loss = losers["pnl"].mean() if len(losers) > 0 else 0
    
    total_pnl = df_trades["pnl"].sum()
    return_pct = (total_pnl / INITIAL_BALANCE) * 100
    
    gross_profit = winners["pnl"].sum() if len(winners) > 0 else 0
    gross_loss = abs(losers["pnl"].sum()) if len(losers) > 0 else 0
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
    
    # Max drawdown
    df_trades["cumulative"] = df_trades["pnl"].cumsum()
    df_trades["peak"] = df_trades["cumulative"].cummax()
    df_trades["dd"] = df_trades["cumulative"] - df_trades["peak"]
    max_dd = df_trades["dd"].min()
    max_dd_pct = (max_dd / INITIAL_BALANCE) * 100
    
    # Por dirección
    longs = df_trades[df_trades["direction"] == "long"]
    shorts = df_trades[df_trades["direction"] == "short"]
    
    print(f"\n📊 GENERAL:")
    print(f"  Balance inicial:  ${INITIAL_BALANCE:,.2f}")
    print(f"  Balance final:    ${balance:,.2f}")
    print(f"  PnL neto:         ${total_pnl:,.2f} ({return_pct:+.2f}%)")
    print(f"  Max Drawdown:     ${max_dd:,.2f} ({max_dd_pct:.2f}%)")
    
    print(f"\n📈 TRADES:")
    print(f"  Total:            {total_trades}")
    print(f"  Winners:          {len(winners)} ({win_rate:.1f}%)")
    print(f"  Losers:           {len(losers)} ({100-win_rate:.1f}%)")
    print(f"  Avg Win:          ${avg_win:,.2f}")
    print(f"  Avg Loss:         ${avg_loss:,.2f}")
    print(f"  Win/Loss Ratio:   {abs(avg_win/avg_loss):.2f}" if avg_loss != 0 else "  Win/Loss Ratio:   N/A")
    print(f"  Profit Factor:    {profit_factor:.2f}")
    
    print(f"\n🎯 POR DIRECCIÓN:")
    if len(longs) > 0:
        long_wr = len(longs[longs["pnl"] > 0]) / len(longs) * 100
        long_pnl = longs["pnl"].sum()
        print(f"  LONG:  {len(longs)} trades, WR {long_wr:.1f}%, PnL ${long_pnl:,.2f}")
    else:
        print(f"  LONG:  0 trades")
    
    if len(shorts) > 0:
        short_wr = len(shorts[shorts["pnl"] > 0]) / len(shorts) * 100
        short_pnl = shorts["pnl"].sum()
        print(f"  SHORT: {len(shorts)} trades, WR {short_wr:.1f}%, PnL ${short_pnl:,.2f}")
    else:
        print(f"  SHORT: 0 trades")
    
    # Primeros 10 trades
    print(f"\n📋 PRIMEROS 10 TRADES:")
    print(f"{'#':<4} {'Fecha':<17} {'Dir':<5} {'Entry':<10} {'Exit':<10} {'Type':<4} {'PnL':<12} {'Balance':<12}")
    print("-" * 90)
    for idx, trade in df_trades.head(10).iterrows():
        direction_symbol = "LONG" if trade["direction"] == "long" else "SHORT"
        exit_type = trade["exit_type"]
        print(f"{idx+1:<4} {str(trade['entry_time']):<17} {direction_symbol:<5} "
              f"{trade['entry']:<10.2f} {trade['exit']:<10.2f} {exit_type:<4} "
              f"${trade['pnl']:>10,.2f} ${trade['balance']:>10,.2f}")
    
    if len(df_trades) > 10:
        print(f"... y {len(df_trades) - 10} trades más")
    
    # Últimos 10 trades
    print(f"\n📋 ÚLTIMOS 10 TRADES:")
    print(f"{'#':<4} {'Fecha':<17} {'Dir':<5} {'Entry':<10} {'Exit':<10} {'Type':<4} {'PnL':<12} {'Balance':<12}")
    print("-" * 90)
    for idx, trade in df_trades.tail(10).iterrows():
        direction_symbol = "LONG" if trade["direction"] == "long" else "SHORT"
        exit_type = trade["exit_type"]
        print(f"{idx+1:<4} {str(trade['entry_time']):<17} {direction_symbol:<5} "
              f"{trade['entry']:<10.2f} {trade['exit']:<10.2f} {exit_type:<4} "
              f"${trade['pnl']:>10,.2f} ${trade['balance']:>10,.2f}")

print("\n" + "="*70)
print("  ANÁLISIS COMPLETO")
print("="*70)
