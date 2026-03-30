# -*- coding: utf-8 -*-
"""
EXPERIMENTAL - Solo para investigacion. NO modifica ni altera el bot live.
Backtest comparativo usando el backtester oficial con distintos filtros BOS:
  A) BOS original (ventana 20 velas M1) — baseline live
  B) BOS fractal (swing highs/lows reales como LuxAlgo)
  C) Solo CHoCH (cambio de caracter)
  D) Sin BOS (referencia)
"""
import sys
import copy
import numpy as np
import pandas as pd
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from strategies.order_block.backtest.config import DEFAULT_PARAMS
from strategies.order_block.backtest.data_loader import load_csv
from strategies.order_block.backtest.backtester import OrderBlockBacktester
from strategies.order_block.backtest.ob_detection import OBStatus

M5_FILE        = "data/US30_cash_M5_260d.csv"
M1_FILE        = "data/US30_cash_M1_260d.csv"
FRACTAL_LENGTH = 5

# ============================================================
# FRACTALES
# ============================================================

def detect_fractals(df: pd.DataFrame, length: int = 5):
    """df debe tener indice 0..N"""
    p = length // 2
    highs = df["high"].values
    lows  = df["low"].values
    swing_high = [False] * len(df)
    swing_low  = [False] * len(df)
    for i in range(p, len(df) - p):
        if highs[i] == max(highs[i - p: i + p + 1]):
            swing_high[i] = True
        if lows[i] == min(lows[i - p: i + p + 1]):
            swing_low[i] = True
    return swing_high, swing_low


def bos_fractal(df: pd.DataFrame, entry_idx: int, direction: str,
                swing_high: list, swing_low: list, lookback: int = 50) -> bool:
    start = max(0, entry_idx - lookback)
    if direction == "long":
        sh_pos = [i for i in range(start, entry_idx) if swing_high[i]]
        if not sh_pos: return False
        last_sh = sh_pos[-1]
        sh_val  = df["high"].iloc[last_sh]
        return any(df["close"].iloc[last_sh + 1: entry_idx] > sh_val)
    else:
        sl_pos = [i for i in range(start, entry_idx) if swing_low[i]]
        if not sl_pos: return False
        last_sl = sl_pos[-1]
        sl_val  = df["low"].iloc[last_sl]
        return any(df["close"].iloc[last_sl + 1: entry_idx] < sl_val)


def bos_choch(df: pd.DataFrame, entry_idx: int, direction: str,
              swing_high: list, swing_low: list, lookback: int = 100) -> bool:
    """CHoCH: BOS contrario previo + BOS en direccion del trade"""
    start = max(0, entry_idx - lookback)
    half  = (entry_idx - start) // 2
    mid   = start + half
    if direction == "long":
        had_bear = bos_fractal(df, mid, "short", swing_high, swing_low, half)
        has_bull = bos_fractal(df, entry_idx, "long", swing_high, swing_low, half)
        return had_bear and has_bull
    else:
        had_bull = bos_fractal(df, mid, "long", swing_high, swing_low, half)
        has_bear = bos_fractal(df, entry_idx, "short", swing_high, swing_low, half)
        return had_bull and has_bear


# ============================================================
# MONKEY-PATCH del backtester para inyectar BOS custom
# ============================================================

class ExperimentalBacktester(OrderBlockBacktester):
    """
    Extiende el backtester oficial reemplazando solo el check_bos interno.
    El resto de la logica (deteccion OB, SL/TP, risk, etc.) es identica.
    """
    def __init__(self, params, bos_mode="original", df_m1_ref=None,
                 swing_high=None, swing_low=None):
        super().__init__(params)
        self.bos_mode   = bos_mode
        self.df_m1_ref  = df_m1_ref
        self.swing_high = swing_high
        self.swing_low  = swing_low

    def _check_bos_custom(self, candle_time, direction: str) -> bool:
        if self.bos_mode == "original":
            return True  # el backtester oficial ya lo maneja via params

        if self.df_m1_ref is None:
            return True

        # Obtener idx en df_m1
        mask = self.df_m1_ref["time"] <= candle_time
        if not mask.any():
            return False
        idx = mask.values.nonzero()[0][-1]

        if self.bos_mode == "fractal":
            return bos_fractal(self.df_m1_ref, idx, direction,
                               self.swing_high, self.swing_low)
        elif self.bos_mode == "choch":
            return bos_choch(self.df_m1_ref, idx, direction,
                             self.swing_high, self.swing_low)
        return True


# ============================================================
# RUNNER
# ============================================================

def run(df_m5, df_m1, swing_high, swing_low, bos_mode, label):
    params = copy.deepcopy(DEFAULT_PARAMS)

    if bos_mode == "original":
        params["require_bos"] = True   # usa el BOS del backtester oficial
    else:
        params["require_bos"] = False  # desactivamos el interno, usamos el custom

    bt = ExperimentalBacktester(
        params,
        bos_mode   = bos_mode,
        df_m1_ref  = df_m1,
        swing_high = swing_high,
        swing_low  = swing_low,
    )

    # Inyectar check custom en el metodo de señales si no es original
    if bos_mode != "original":
        import strategies.order_block.backtest.signals as sig_mod
        original_check = sig_mod.check_bos

        def patched_check_bos(recent_candles, direction, params):
            if not recent_candles:
                return False
            candle_time = recent_candles[-1]["time"]
            return bt._check_bos_custom(candle_time, direction)

        sig_mod.check_bos = patched_check_bos
        result = bt.run(df_m5, df_m1)
        sig_mod.check_bos = original_check  # restaurar siempre
    else:
        result = bt.run(df_m5, df_m1)

    # El backtester oficial retorna un DataFrame directamente
    df_t = result if isinstance(result, pd.DataFrame) else pd.DataFrame(result)
    if df_t is None or len(df_t) == 0:
        print(f"  {label}: 0 trades")
        return

    balance = df_t["balance"].iloc[-1] if "balance" in df_t.columns else 100000
    ret  = (balance - 100000) / 100000 * 100
    wr   = (df_t["pnl_usd"] > 0).mean() * 100 if "pnl_usd" in df_t.columns else 0
    mdd  = 0.0; peak = 100000.0
    for b in df_t["balance"]:
        if b > peak: peak = b
        dd = (peak - b) / peak * 100
        if dd > mdd: mdd = dd

    print(f"  {label}")
    print(f"    Trades:   {len(df_t)}")
    print(f"    Win Rate: {wr:.1f}%")
    print(f"    Retorno:  {ret:+.2f}%")
    print(f"    Max DD:   {mdd:.2f}%")
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
    print(f"  M5: {len(df_m5)} | M1: {len(df_m1)} | {start} -> {end}")
    print()

    print("Detectando fractales M1...")
    swing_high, swing_low = detect_fractals(df_m1, FRACTAL_LENGTH)
    print(f"  Swing Highs: {sum(swing_high)} | Swing Lows: {sum(swing_low)}")
    print()

    print("=" * 55)
    print("  BACKTEST EXPERIMENTAL — BOS/CHoCH FRACTAL")
    print("  (NO modifica el bot live)")
    print("=" * 55)
    print()

    run(df_m5, df_m1, swing_high, swing_low, "original", "A) BOS original (baseline live)")
    run(df_m5, df_m1, swing_high, swing_low, "fractal",  "B) BOS fractal (swing highs/lows)")
    run(df_m5, df_m1, swing_high, swing_low, "choch",    "C) CHoCH (cambio de caracter)")
    run(df_m5, df_m1, swing_high, swing_low, "none",     "D) Sin BOS (referencia)")

    print("=" * 55)
    print("  A = baseline actual en produccion")
    print("  B = BOS mas preciso con fractales reales")
    print("  C = trades de maxima calidad (CHoCH confirmado)")
    print("  D = sin filtro BOS (comparativa)")
    print("=" * 55)
