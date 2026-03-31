# -*- coding: utf-8 -*-
"""
Backtest VWAP Momentum Strategy - CORREGIDO
Replica EXACTAMENTE el script de TradingView:
- R:R 1:5 (TP = 150 pts)
- SL desde VWAP (no desde entry)
- Lote fijo (sin compounding)
- VWAP calculado igual que TradingView
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
print("  BACKTEST VWAP MOMENTUM - CORREGIDO (REPLICA TRADINGVIEW)")
print("="*70)

# Cargar datos M5
df = pd.read_csv("data/US30_cash_M5_260d.csv")
df["time"] = pd.to_datetime(df["time"])
df = df.sort_values("time").reset_index(drop=True)

print(f"\nDatos cargados: {len(df):,} velas M5")
print(f"Periodo completo: {df['time'].iloc[0]} -> {df['time'].iloc[-1]}")

# Calcular VWAP (IGUAL QUE TRADINGVIEW)
# TradingView usa: ta.vwap que resetea cada día
print("\nCalculando VWAP (resetea cada día)...")
df["date"] = df["time"].dt.date

# VWAP = sum(typical_price × volume) / sum(volume) acumulado por día
df["typical_price"] = (df["high"] + df["low"] + df["close"]) / 3

def calc_vwap_group(group):
    """Calcula VWAP acumulado para un día"""
    cum_vol = group["volume"].cumsum()
    cum_tp_vol = (group["typical_price"] * group["volume"]).cumsum()
    return cum_tp_vol / cum_vol

df["vwap"] = df.groupby("date", group_keys=False).apply(calc_vwap_group).reset_index(drop=True)

# Identificar sesiones
def get_session(dt):
    hour = dt.hour
    minute = dt.minute
    time_val = hour + minute/60
    
    if 7 <= time_val < 12:
        return "london"
    elif 13.5 <= time_val < 20:
        return "new_york"
    elif 0 <= time_val < 6:
        return "asia"
    else:
        return "other"

df["session"] = df["time"].apply(get_session)

# Señales (IGUAL QUE TRADINGVIEW)
# Long: close[1] < vwap[1] and close > vwap
# Short: close[1] > vwap[1] and close < vwap
df["long_signal"] = (df["close"].shift(1) < df["vwap"].shift(1)) & (df["close"] > df["vwap"])
df["short_signal"] = (df["close"].shift(1) > df["vwap"].shift(1)) & (df["close"] < df["vwap"])

print(f"Señales detectadas: {df['long_signal'].sum()} longs, {df['short_signal'].sum()} shorts")

# PARÁMETROS (IGUAL QUE TRADINGVIEW)
INITIAL_BALANCE = 100_000
LOT_SIZE = 1.0  # FIJO (como TradingView)
SL_POINTS = 30
RR = 5.0  # R:R 1:5
TP_POINTS = SL_POINTS * RR  # 150 puntos
POINT_VALUE = 1.0  # US30: $1 por punto por lote
SPREAD_POINTS = 2

print("\nParámetros (REPLICA TRADINGVIEW):")
print(f"  Lote: {LOT_SIZE} (fijo, sin compounding)")
print(f"  SL: {SL_POINTS} puntos DESDE VWAP")
print(f"  TP: {TP_POINTS} puntos desde entry (R:R 1:{RR})")
print(f"  Spread: {SPREAD_POINTS} puntos")

# Backtest
print("\nEjecutando backtest...")
balance = INITIAL_BALANCE
equity = INITIAL_BALANCE
trades = []
in_position = False
current_trade = None

for i in range(1, len(df)):
    row = df.iloc[i]
    prev_row = df.iloc[i-1]
    
    # Cerrar trade si existe
    if in_position:
        if current_trade["direction"] == "long":
            # SL desde VWAP (como TradingView)
            current_sl = row["vwap"] - SL_POINTS
            current_tp = current_trade["tp"]
            
            # Check SL
            if row["low"] <= current_sl:
                # Calcular PnL
                exit_price = current_sl
                pnl_pts = exit_price - current_trade["entry_price"] - SPREAD_POINTS
                pnl_usd = pnl_pts * POINT_VALUE * LOT_SIZE
                balance += pnl_usd
                equity = balance
                
                trades.append({
                    **current_trade,
                    "exit_price": exit_price,
                    "exit_time": row["time"],
                    "exit_reason": "sl",
                    "pnl_points": pnl_pts,
                    "pnl_usd": pnl_usd,
                    "balance": balance,
                    "equity": equity
                })
                in_position = False
                current_trade = None
                continue
            
            # Check TP
            if row["high"] >= current_tp:
                exit_price = current_tp
                pnl_pts = exit_price - current_trade["entry_price"] - SPREAD_POINTS
                pnl_usd = pnl_pts * POINT_VALUE * LOT_SIZE
                balance += pnl_usd
                equity = balance
                
                trades.append({
                    **current_trade,
                    "exit_price": exit_price,
                    "exit_time": row["time"],
                    "exit_reason": "tp",
                    "pnl_points": pnl_pts,
                    "pnl_usd": pnl_usd,
                    "balance": balance,
                    "equity": equity
                })
                in_position = False
                current_trade = None
                continue
        
        else:  # short
            # SL desde VWAP
            current_sl = row["vwap"] + SL_POINTS
            current_tp = current_trade["tp"]
            
            # Check SL
            if row["high"] >= current_sl:
                exit_price = current_sl
                pnl_pts = current_trade["entry_price"] - exit_price - SPREAD_POINTS
                pnl_usd = pnl_pts * POINT_VALUE * LOT_SIZE
                balance += pnl_usd
                equity = balance
                
                trades.append({
                    **current_trade,
                    "exit_price": exit_price,
                    "exit_time": row["time"],
                    "exit_reason": "sl",
                    "pnl_points": pnl_pts,
                    "pnl_usd": pnl_usd,
                    "balance": balance,
                    "equity": equity
                })
                in_position = False
                current_trade = None
                continue
            
            # Check TP
            if row["low"] <= current_tp:
                exit_price = current_tp
                pnl_pts = current_trade["entry_price"] - exit_price - SPREAD_POINTS
                pnl_usd = pnl_pts * POINT_VALUE * LOT_SIZE
                balance += pnl_usd
                equity = balance
                
                trades.append({
                    **current_trade,
                    "exit_price": exit_price,
                    "exit_time": row["time"],
                    "exit_reason": "tp",
                    "pnl_points": pnl_pts,
                    "pnl_usd": pnl_usd,
                    "balance": balance,
                    "equity": equity
                })
                in_position = False
                current_trade = None
                continue
    
    # Nueva entrada
    if not in_position:
        if row["long_signal"]:
            entry_price = row["close"]
            sl_price = row["vwap"] - SL_POINTS  # SL desde VWAP
            tp_price = entry_price + TP_POINTS  # TP desde entry
            
            current_trade = {
                "direction": "long",
                "entry_price": entry_price,
                "sl": sl_price,
                "tp": tp_price,
                "entry_time": row["time"],
                "session": row["session"],
                "vwap_at_entry": row["vwap"],
                "balance_at_entry": balance
            }
            in_position = True
        
        elif row["short_signal"]:
            entry_price = row["close"]
            sl_price = row["vwap"] + SL_POINTS  # SL desde VWAP
            tp_price = entry_price - TP_POINTS  # TP desde entry
            
            current_trade = {
                "direction": "short",
                "entry_price": entry_price,
                "sl": sl_price,
                "tp": tp_price,
                "entry_time": row["time"],
                "session": row["session"],
                "vwap_at_entry": row["vwap"],
                "balance_at_entry": balance
            }
            in_position = True

# Resultados
df_trades = pd.DataFrame(trades)

if len(df_trades) == 0:
    print("\nNo se generaron trades.")
    sys.exit(0)

# Guardar
df_trades.to_csv("strategies/order_block/backtest/results/vwap_m5_corrected.csv", index=False)

# Análisis general
total_trades = len(df_trades)
wins = df_trades[df_trades["pnl_usd"] > 0]
losses = df_trades[df_trades["pnl_usd"] <= 0]
wr = len(wins) / total_trades * 100
pf = wins["pnl_usd"].sum() / abs(losses["pnl_usd"].sum()) if len(losses) > 0 else float('inf')
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

# Análisis por sesión
print("\n" + "="*70)
print("  RESULTADOS POR SESIÓN")
print("="*70)

for session in ["london", "new_york", "asia", "other"]:
    sess_trades = df_trades[df_trades["session"] == session]
    if len(sess_trades) == 0:
        continue
    
    sess_wins = sess_trades[sess_trades["pnl_usd"] > 0]
    sess_wr = len(sess_wins) / len(sess_trades) * 100
    sess_pnl = sess_trades["pnl_usd"].sum()
    sess_losses = sess_trades[sess_trades["pnl_usd"] <= 0]
    sess_pf = sess_wins["pnl_usd"].sum() / abs(sess_losses["pnl_usd"].sum()) if len(sess_losses) > 0 else float('inf')
    
    print(f"\n  {session.upper()}:")
    print(f"    Trades:        {len(sess_trades)}")
    print(f"    Win Rate:      {sess_wr:.1f}%")
    print(f"    PnL total:     ${sess_pnl:+,.2f}")
    print(f"    Profit Factor: {sess_pf:.2f}")

# Análisis por dirección
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

# Comparación con TradingView
print("\n" + "="*70)
print("  COMPARACIÓN CON TRADINGVIEW")
print("="*70)
print(f"\n  TradingView (1 feb - 30 mar 2026):")
print(f"    Trades:        291")
print(f"    Win Rate:      32.90%")
print(f"    Retorno:       +4.7%")
print(f"    Profit Factor: 1.545")
print(f"\n  Python (periodo completo):")
print(f"    Trades:        {total_trades}")
print(f"    Win Rate:      {wr:.1f}%")
print(f"    Retorno:       {ret:+.2f}%")
print(f"    Profit Factor: {pf:.2f}")

print("\n" + "="*70)
print(f"  Resultados guardados en: strategies/order_block/backtest/results/vwap_m5_corrected.csv")
print("="*70 + "\n")
