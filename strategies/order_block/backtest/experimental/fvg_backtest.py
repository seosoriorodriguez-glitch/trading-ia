# -*- coding: utf-8 -*-
"""
EXPERIMENTAL - Solo para investigacion. NO modifica ni altera el bot live.
Backtest estrategia FVG (Fair Value Gap) en M5/M1.
Logica identica al bot OB pero usando FVGs en vez de Order Blocks.

FVG Bullish: low[0] > high[2] AND close[1] > high[2]
  zona = [high[2], low[0]]  → precio retrocede al gap → LONG

FVG Bearish: high[0] < low[2] AND close[1] < low[2]
  zona = [high[0], low[2]]  → precio retrocede al gap → SHORT

SL: extremo del FVG + buffer_points
TP: entry +/- riesgo * target_rr
"""
import sys
import copy
import numpy as np
import pandas as pd
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from strategies.order_block.backtest.config import DEFAULT_PARAMS
from strategies.order_block.backtest.data_loader import load_csv
from strategies.order_block.backtest.risk_manager import is_session_allowed

M5_FILE = "data/US30_cash_M5_260d.csv"
M1_FILE = "data/US30_cash_M1_260d.csv"

# ============================================================
# FVG DETECTION
# ============================================================

@dataclass
class FVG:
    fvg_type:     str    # "bullish" o "bearish"
    zone_high:    float
    zone_low:     float
    confirmed_at: datetime
    status:       str = "fresh"  # fresh / mitigated / destroyed


def detect_fvgs(df: pd.DataFrame, params: dict) -> List[FVG]:
    """
    Detecta FVGs en el DataFrame M5.
    Anti look-ahead: confirmed_at = apertura de la vela siguiente al FVG.
    """
    buf      = params["buffer_points"]
    min_size = params.get("fvg_min_size", 5)   # gap minimo en puntos
    fvgs     = []

    for i in range(2, len(df) - 1):
        v0 = df.iloc[i]      # vela actual
        v1 = df.iloc[i - 1]  # vela central (el impulso)
        v2 = df.iloc[i - 2]  # vela anterior

        confirmed_at = df.iloc[i + 1]["time"]  # anti look-ahead

        # Bullish FVG: gap alcista entre high[2] y low[0]
        if v0["low"] > v2["high"] and v1["close"] > v2["high"]:
            zone_low  = v2["high"]
            zone_high = v0["low"]
            if zone_high - zone_low >= min_size:
                fvgs.append(FVG(
                    fvg_type     = "bullish",
                    zone_high    = zone_high,
                    zone_low     = zone_low,
                    confirmed_at = confirmed_at,
                ))

        # Bearish FVG: gap bajista entre low[2] y high[0]
        elif v0["high"] < v2["low"] and v1["close"] < v2["low"]:
            zone_low  = v0["high"]
            zone_high = v2["low"]
            if zone_high - zone_low >= min_size:
                fvgs.append(FVG(
                    fvg_type     = "bearish",
                    zone_high    = zone_high,
                    zone_low     = zone_low,
                    confirmed_at = confirmed_at,
                ))

    return fvgs


# ============================================================
# RISK: SL / TP
# ============================================================

def calculate_sl_tp_fvg(fvg: FVG, entry: float, params: dict):
    buf       = params["buffer_points"]
    target_rr = params["target_rr"]
    min_risk  = params["min_risk_points"]
    max_risk  = params["max_risk_points"]

    if fvg.fvg_type == "bullish":
        sl = fvg.zone_low - buf
        tp = entry + (entry - sl) * target_rr
    else:
        sl = fvg.zone_high + buf
        tp = entry - (sl - entry) * target_rr

    risk = abs(entry - sl)
    if risk < min_risk or risk > max_risk:
        return None, None

    return sl, tp


# ============================================================
# BACKTESTER FVG
# ============================================================

def run_fvg_backtest(df_m5: pd.DataFrame, df_m1: pd.DataFrame,
                     params: dict, label: str = "FVG"):
    fvgs = detect_fvgs(df_m5, params)
    print(f"  FVGs detectados: {len(fvgs)}"
          f" ({sum(1 for f in fvgs if f.fvg_type=='bullish')} bull"
          f" / {sum(1 for f in fvgs if f.fvg_type=='bearish')} bear)")

    balance        = params["initial_balance"]
    mitigated_keys = set()
    trades         = []
    peak           = balance

    for idx in range(len(df_m1)):
        row          = df_m1.iloc[idx]
        candle_time  = row["time"]
        candle_close = row["close"]

        # DESTROYED: precio cerro fuera del extremo del FVG
        for fvg in fvgs:
            if fvg.status != "fresh":
                continue
            if fvg.fvg_type == "bullish" and candle_close < fvg.zone_low:
                fvg.status = "destroyed"
            elif fvg.fvg_type == "bearish" and candle_close > fvg.zone_high:
                fvg.status = "destroyed"

        if not is_session_allowed(candle_time, params):
            continue

        # FVGs activos — max 50 mas recientes (FVGs son mas frecuentes que OBs)
        active = sorted(
            [f for f in fvgs
             if f.status == "fresh"
             and f.confirmed_at <= candle_time
             and id(f) not in mitigated_keys],
            key=lambda f: f.confirmed_at, reverse=True
        )[:50]

        for fvg in active:
            in_zone   = False
            direction = None

            # FVGs son estrechos — entrada al tocar la zona (no requiere cierre dentro)
            if fvg.fvg_type == "bullish" and row["low"] <= fvg.zone_high and row["high"] >= fvg.zone_low:
                in_zone = True; direction = "long"
                candle_close = fvg.zone_high  # entrada al techo del FVG
            elif fvg.fvg_type == "bearish" and row["high"] >= fvg.zone_low and row["low"] <= fvg.zone_high:
                in_zone = True; direction = "short"
                candle_close = fvg.zone_low   # entrada al piso del FVG

            if not in_zone:
                continue

            sl, tp = calculate_sl_tp_fvg(fvg, candle_close, params)
            if sl is None:
                continue

            # Simular resultado
            future = df_m1.iloc[idx + 1: idx + 501]
            result = None; exit_price = None
            for _, f in future.iterrows():
                if direction == "long":
                    if f["low"] <= sl:  result = "sl"; exit_price = sl;  break
                    if f["high"] >= tp: result = "tp"; exit_price = tp;  break
                else:
                    if f["high"] >= sl: result = "sl"; exit_price = sl;  break
                    if f["low"] <= tp:  result = "tp"; exit_price = tp;  break

            if result is None:
                continue

            risk   = abs(candle_close - sl)
            volume = (balance * params["risk_per_trade_pct"]) / risk
            pnl    = (exit_price - candle_close) * volume if direction == "long" \
                     else (candle_close - exit_price) * volume

            balance += pnl
            mitigated_keys.add(id(fvg))
            fvg.status = "mitigated"

            trades.append({
                "entry_time":  candle_time,
                "direction":   direction,
                "entry_price": candle_close,
                "sl":          sl,
                "tp":          tp,
                "exit_price":  exit_price,
                "exit_reason": result,
                "pnl_usd":     pnl,
                "balance":     balance,
            })
            break

    if not trades:
        print(f"  {label}: 0 trades")
        return

    df_t = pd.DataFrame(trades)
    ret  = (balance - params["initial_balance"]) / params["initial_balance"] * 100
    wr   = (df_t["pnl_usd"] > 0).mean() * 100
    mdd  = 0.0; peak = params["initial_balance"]
    for b in df_t["balance"]:
        if b > peak: peak = b
        dd = (peak - b) / peak * 100
        if dd > mdd: mdd = dd

    longs  = df_t[df_t["direction"] == "long"]
    shorts = df_t[df_t["direction"] == "short"]
    days   = (df_t["entry_time"].iloc[-1] - df_t["entry_time"].iloc[0]).days or 1

    print(f"  {label}")
    print(f"    Trades:      {len(df_t)}  ({days} dias,  {len(df_t)/days:.2f}/dia)")
    print(f"    Win Rate:    {wr:.1f}%")
    print(f"    Retorno:     {ret:+.2f}%")
    print(f"    Max DD:      {mdd:.2f}%")
    print(f"    Long:  {len(longs)} trades  WR {(longs['pnl_usd']>0).mean()*100:.0f}%")
    print(f"    Short: {len(shorts)} trades  WR {(shorts['pnl_usd']>0).mean()*100:.0f}%")
    print()

    return df_t


# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    print("Cargando datos...")
    df_m5 = load_csv(M5_FILE)
    df_m1 = load_csv(M1_FILE)
    start = max(df_m5["time"].iloc[0], df_m1["time"].iloc[0])
    end   = min(df_m5["time"].iloc[-1], df_m1["time"].iloc[-1])
    df_m5 = df_m5[(df_m5["time"] >= start) & (df_m5["time"] <= end)].reset_index(drop=True)
    df_m1 = df_m1[(df_m1["time"] >= start) & (df_m1["time"] <= end)].reset_index(drop=True)
    print(f"  Periodo: {start} -> {end}")
    print(f"  M5: {len(df_m5)} velas | M1: {len(df_m1)} velas")
    print()

    print("=" * 58)
    print("  BACKTEST EXPERIMENTAL — FVG STRATEGY")
    print("  (NO modifica el bot live)")
    print("=" * 58)
    print()

    # Params base identicos al bot OB live
    params = copy.deepcopy(DEFAULT_PARAMS)
    params["fvg_min_size"] = 5  # gap minimo en puntos para considerar FVG valido

    print("--- Config identica al bot OB (RR=2.5, buf=20, NY only) ---")
    print()
    run_fvg_backtest(df_m5, df_m1, params, "FVG M5/M1")

    print()
    print("--- Comparativa REFERENCIA bot OB actual ---")
    print("  OB live:  98 trades | WR 42.9% | +19.5% | DD 2.56%")
    print()
    print("=" * 58)
    print("  FVGs son gaps de precio — zona mas estrecha y precisa")
    print("  que los OBs. Suelen ser mas frecuentes.")
    print("=" * 58)
