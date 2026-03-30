# -*- coding: utf-8 -*-
"""
EXPERIMENTAL - Solo para investigacion. NO modifica ni altera el bot live.

Compara tres modos de gestion del SL una vez abierto el trade:

  A) SL fijo (baseline live):
     SL nunca se mueve. Sale en SL original o TP.

  B) Breakeven a 1R:
     Cuando el trade gana 1R (precio se mueve 1x el riesgo a favor),
     el SL se mueve a entry price. El trade no puede perder dinero.

  C) Trailing stop desde 1R (distancia = 1R):
     Cuando el trade gana 1R, empieza a arrastrar el SL
     manteniendolo siempre 1R detras del mejor precio alcanzado.
     Puede salir antes del TP pero captura mas si el precio sigue corriendo.
"""
import sys
import copy
from pathlib import Path
from typing import List
from datetime import datetime

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from strategies.order_block.backtest.config import DEFAULT_PARAMS
from strategies.order_block.backtest.data_loader import load_csv
from strategies.order_block.backtest.backtester import OrderBlockBacktester, Trade

_ROOT   = Path(__file__).parent.parent.parent.parent.parent
M5_FILE = str(_ROOT / "data/US30_cash_M5_260d.csv")
M1_FILE = str(_ROOT / "data/US30_cash_M1_260d.csv")


# ============================================================
# BACKTESTER CON SL DINAMICO
# ============================================================

class DynamicSLBacktester(OrderBlockBacktester):
    """
    Extiende el backtester oficial solo reemplazando _check_trade_exit
    para soportar breakeven y trailing stop.
    """

    def __init__(self, params: dict, sl_mode: str = "fixed"):
        super().__init__(params)
        self.sl_mode = sl_mode  # "fixed" | "breakeven" | "trailing"

    def _check_trade_exit(
        self,
        trade: Trade,
        candle_high: float,
        candle_low: float,
        current_time: datetime,
    ) -> bool:
        risk = abs(trade.entry_price - trade.original_sl)

        # --- Actualizar SL dinamico ANTES de chequear salida ---
        if self.sl_mode == "breakeven" and risk > 0:
            if trade.direction == "long":
                be_trigger = trade.entry_price + risk          # precio al que mueve SL
                if candle_high >= be_trigger:
                    trade.sl = max(trade.sl, trade.entry_price)
            else:
                be_trigger = trade.entry_price - risk
                if candle_low <= be_trigger:
                    trade.sl = min(trade.sl, trade.entry_price)

        elif self.sl_mode == "trailing" and risk > 0:
            if trade.direction == "long":
                trail_trigger = trade.entry_price + risk       # activar trailing desde 1R
                if candle_high >= trail_trigger:
                    new_sl = candle_high - risk                # SL = mejor_precio - 1R
                    trade.sl = max(trade.sl, new_sl)
            else:
                trail_trigger = trade.entry_price - risk
                if candle_low <= trail_trigger:
                    new_sl = candle_low + risk
                    trade.sl = min(trade.sl, new_sl)

        # --- Verificar salida (SL primero, luego TP) ---
        if trade.direction == "long":
            if candle_low <= trade.sl:
                self._close_trade(trade, trade.sl, current_time, "sl")
                return True
            if candle_high >= trade.tp:
                self._close_trade(trade, trade.tp, current_time, "tp")
                return True
        else:
            if candle_high >= trade.sl:
                self._close_trade(trade, trade.sl, current_time, "sl")
                return True
            if candle_low <= trade.tp:
                self._close_trade(trade, trade.tp, current_time, "tp")
                return True

        return False


# ============================================================
# RUNNER
# ============================================================

def run(df_m5, df_m1, sl_mode: str, label: str):
    params = copy.deepcopy(DEFAULT_PARAMS)

    bt = DynamicSLBacktester(params, sl_mode=sl_mode)
    result = bt.run(df_m5, df_m1)

    df_t = result if isinstance(result, pd.DataFrame) else pd.DataFrame(result)
    if df_t is None or len(df_t) == 0:
        print(f"  {label}: 0 trades\n")
        return

    balance = df_t["balance"].iloc[-1]
    ret  = (balance - params["initial_balance"]) / params["initial_balance"] * 100
    wr   = (df_t["pnl_usd"] > 0).mean() * 100
    mdd  = 0.0
    peak = float(params["initial_balance"])
    for b in df_t["balance"]:
        if b > peak:
            peak = b
        dd = (peak - b) / peak * 100
        if dd > mdd:
            mdd = dd

    # Desglose TP / SL / trailing
    tp_exits = (df_t["exit_reason"] == "tp").sum()
    sl_exits = (df_t["exit_reason"] == "sl").sum()
    longs    = df_t[df_t["direction"] == "long"]
    shorts   = df_t[df_t["direction"] == "short"]
    days     = max((df_t["entry_time"].iloc[-1] - df_t["entry_time"].iloc[0]).days, 1)

    print(f"  {label}")
    print(f"    Trades:    {len(df_t)}  ({days} dias,  {len(df_t)/days:.2f}/dia)")
    print(f"    Win Rate:  {wr:.1f}%")
    print(f"    Retorno:   {ret:+.2f}%")
    print(f"    Max DD:    {mdd:.2f}%")
    print(f"    TP hits:   {tp_exits}  |  SL hits: {sl_exits}")
    if len(longs):
        print(f"    Long:  {len(longs)} trades  WR {(longs['pnl_usd']>0).mean()*100:.0f}%")
    if len(shorts):
        print(f"    Short: {len(shorts)} trades  WR {(shorts['pnl_usd']>0).mean()*100:.0f}%")
    print()


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

    print("=" * 60)
    print("  BACKTEST EXPERIMENTAL — TRAILING STOP / BREAKEVEN")
    print("  (NO modifica el bot live)")
    print("=" * 60)
    print()

    run(df_m5, df_m1, "fixed",     "A) SL fijo (baseline live)")
    run(df_m5, df_m1, "breakeven", "B) Breakeven a 1R")
    run(df_m5, df_m1, "trailing",  "C) Trailing stop desde 1R (distancia 1R)")

    print("=" * 60)
    print("  A = baseline, SL nunca se mueve")
    print("  B = no pierde dinero tras 1R ganado")
    print("  C = captura mas si el movimiento continua")
    print("=" * 60)
