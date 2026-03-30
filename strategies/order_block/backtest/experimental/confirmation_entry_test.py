# -*- coding: utf-8 -*-
"""
EXPERIMENTAL - Solo para investigacion. NO modifica ni altera el bot live.

Compara dos modos de entrada en la zona OB:

  A) INMEDIATA (baseline live):
     Entra cuando la vela M1 cierra DENTRO de la zona OB.
     Bullish: close <= zone_high
     Bearish: close >= zone_low

  B) CONFIRMACION (nuevo a testear):
     Espera a que el precio entre a la zona OB (vela cierra dentro),
     y luego entra cuando la SIGUIENTE vela cierra FUERA de la zona
     en la direccion del trade (rechazo confirmado).
     Bullish: vela previa cerro en zona  AND  close_actual > zone_high
     Bearish: vela previa cerro en zona  AND  close_actual < zone_low

     Esto simula colocar una stop-entry en el extremo de la zona OB
     una vez que el precio la ha tocado/penetrado.
"""
import sys
import copy
from pathlib import Path
from typing import Optional, List

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from strategies.order_block.backtest.config import DEFAULT_PARAMS
from strategies.order_block.backtest.data_loader import load_csv
from strategies.order_block.backtest.backtester import OrderBlockBacktester
import strategies.order_block.backtest.signals as sig_mod
import strategies.order_block.backtest.backtester as bt_mod
from strategies.order_block.backtest.signals import (
    Signal, check_rejection, check_bos, calculate_sl_tp,
    is_session_allowed, _which_session, OBStatus,
)

_ROOT   = Path(__file__).parent.parent.parent.parent.parent
M5_FILE = str(_ROOT / "data/US30_cash_M5_260d.csv")
M1_FILE = str(_ROOT / "data/US30_cash_M1_260d.csv")


# ============================================================
# LOGICA DE ENTRADA POR CONFIRMACION
# ============================================================

def check_entry_confirmation(
    candle:         dict,
    prev_candle:    Optional[dict],
    recent_candles: List[dict],
    active_obs:     list,
    n_open_trades:  int,
    params:         dict,
    balance:        float,
    trend_bias:     Optional[str] = None,
) -> Optional[Signal]:
    """
    Entrada por confirmacion: la vela previa cerro dentro de la zona OB
    y la vela actual cierra fuera de la zona en la direccion del trade.
    """
    candle_time  = candle["time"]
    candle_close = candle["close"]

    if n_open_trades >= params["max_simultaneous_trades"]:
        return None
    if not is_session_allowed(candle_time, params):
        return None
    if prev_candle is None:
        return None

    session = _which_session(candle_time, params)

    candidates = sorted(
        [ob for ob in active_obs if ob.status == OBStatus.FRESH],
        key=lambda o: o.confirmed_at,
        reverse=True,
    )

    prev_close = prev_candle["close"]

    for ob in candidates:
        if ob.ob_type == "bullish":
            # Vela previa: cerro dentro de la zona (toco/penetro el OB)
            prev_in_zone = (prev_close <= ob.zone_high and prev_close >= ob.zone_low)
            # Vela actual: cierra POR ENCIMA de la zona (rechazo alcista confirmado)
            confirmation = candle_close > ob.zone_high
            if not (prev_in_zone and confirmation):
                continue
            direction = "long"
            entry_price = ob.zone_high  # entrada al techo del OB (zona de accion)

        else:  # bearish
            # Vela previa: cerro dentro de la zona
            prev_in_zone = (prev_close >= ob.zone_low and prev_close <= ob.zone_high)
            # Vela actual: cierra POR DEBAJO de la zona (rechazo bajista confirmado)
            confirmation = candle_close < ob.zone_low
            if not (prev_in_zone and confirmation):
                continue
            direction = "short"
            entry_price = ob.zone_low  # entrada al piso del OB

        # Filtro de tendencia EMA 4H
        if trend_bias is not None and direction != trend_bias:
            continue

        # Filtro: vela de rechazo (sobre la vela previa que estuvo en zona)
        if not check_rejection(prev_candle, None, direction, params):
            continue

        # Filtro: BOS
        if not check_bos(recent_candles, direction, params):
            continue

        # Validar SL/TP usando la entry_price de confirmacion
        sl, tp = calculate_sl_tp(ob, entry_price, params)
        if sl is None:
            continue

        return Signal(
            direction   = direction,
            entry_price = entry_price,
            sl          = sl,
            tp          = tp,
            ob          = ob,
            candle_time = candle_time,
            session     = session,
        )

    return None


# ============================================================
# RUNNER
# ============================================================

def run(df_m5, df_m1, mode: str, label: str):
    params = copy.deepcopy(DEFAULT_PARAMS)

    if mode == "confirmation":
        # backtester.py importa check_entry directamente — hay que parchear ahi
        original_fn = bt_mod.check_entry
        bt_mod.check_entry = check_entry_confirmation

    bt = OrderBlockBacktester(params)
    result = bt.run(df_m5, df_m1)

    if mode == "confirmation":
        bt_mod.check_entry = original_fn  # restaurar siempre

    df_t = result if isinstance(result, pd.DataFrame) else pd.DataFrame(result)
    if df_t is None or len(df_t) == 0:
        print(f"  {label}: 0 trades")
        return

    balance = df_t["balance"].iloc[-1] if "balance" in df_t.columns else params["initial_balance"]
    ret  = (balance - params["initial_balance"]) / params["initial_balance"] * 100
    wr   = (df_t["pnl_usd"] > 0).mean() * 100 if "pnl_usd" in df_t.columns else 0
    mdd  = 0.0
    peak = float(params["initial_balance"])
    for b in df_t["balance"]:
        if b > peak:
            peak = b
        dd = (peak - b) / peak * 100
        if dd > mdd:
            mdd = dd

    longs  = df_t[df_t["direction"] == "long"]  if "direction" in df_t.columns else pd.DataFrame()
    shorts = df_t[df_t["direction"] == "short"] if "direction" in df_t.columns else pd.DataFrame()
    days   = max((df_t["entry_time"].iloc[-1] - df_t["entry_time"].iloc[0]).days, 1) \
             if "entry_time" in df_t.columns else 1

    print(f"  {label}")
    print(f"    Trades:    {len(df_t)}  ({days} dias,  {len(df_t)/days:.2f}/dia)")
    print(f"    Win Rate:  {wr:.1f}%")
    print(f"    Retorno:   {ret:+.2f}%")
    print(f"    Max DD:    {mdd:.2f}%")
    if len(longs):
        wr_l = (longs["pnl_usd"] > 0).mean() * 100
        print(f"    Long:  {len(longs)} trades  WR {wr_l:.0f}%")
    if len(shorts):
        wr_s = (shorts["pnl_usd"] > 0).mean() * 100
        print(f"    Short: {len(shorts)} trades  WR {wr_s:.0f}%")
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
    print("  BACKTEST EXPERIMENTAL — ENTRADA POR CONFIRMACION")
    print("  (NO modifica el bot live)")
    print("=" * 60)
    print()

    run(df_m5, df_m1, "immediate",    "A) Entrada inmediata (baseline live)")
    run(df_m5, df_m1, "confirmation", "B) Entrada por confirmacion (rechazo confirmado)")

    print("=" * 60)
    print("  A = baseline actual en produccion (entrar al tocar zona)")
    print("  B = esperar cierre fuera de zona en dir. del trade")
    print("  Mejor WR en B = mas calidad, menos trades")
    print("  Peor WR en B  = no vale la pena filtrar")
    print("=" * 60)
