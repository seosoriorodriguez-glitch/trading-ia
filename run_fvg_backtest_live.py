# -*- coding: utf-8 -*-
"""
Backtest del bot FVG con parametros LIVE sobre 518 dias de US30 M5/M1.

Anti look-ahead garantizado:
  - FVG formado por 3 velas M5: ref[i-1], mid[i], curr[i+1]
  - confirmed_at = curr.time + candle_duration (= apertura de la vela i+2)
  - Activacion en backtester: solo cuando higher_ptr alcanza htime >= confirmed_at
  - Resultado: la primera entrada posible es en M1 candles a partir de la vela M5 #i+2
    (4ta vela contando desde ref, equivalente al "i+4" desde la referencia)
"""
import sys
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

import copy
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from strategies.fair_value_gap.backtest.config import US30_PARAMS
from strategies.fair_value_gap.backtest.data_loader import load_csv, validate_alignment
from strategies.fair_value_gap.backtest.backtester import FVGBacktester

M5_FILE = "data/US30_icm_M5_518d.csv"
M1_FILE = "data/US30_icm_M1_500k.csv"
OUTPUT  = "output/fvg_live_backtest_518d.csv"


def main():
    params = copy.deepcopy(US30_PARAMS)

    print("\n" + "="*60)
    print(" FVG BACKTEST — PARAMETROS LIVE — US30 518 DIAS")
    print("="*60)

    print(f"\nCargando datos...")
    df_m5 = load_csv(M5_FILE)
    df_m1 = load_csv(M1_FILE)
    validate_alignment(df_m5, df_m1)

    print(f"   M5: {len(df_m5):,} velas  ({df_m5['time'].iloc[0]} -> {df_m5['time'].iloc[-1]})")
    print(f"   M1: {len(df_m1):,} velas  ({df_m1['time'].iloc[0]} -> {df_m1['time'].iloc[-1]})")
    days = (df_m5["time"].iloc[-1] - df_m5["time"].iloc[0]).days
    print(f"   Periodo: {days} dias")

    print(f"\nParametros LIVE:")
    print(f"   entry_method:    {params['entry_method']}")
    print(f"   target_rr:       {params['target_rr']}")
    print(f"   buffer_points:   {params['buffer_points']}")
    print(f"   min_zone_points: {params['min_zone_points']}")
    print(f"   max_atr_mult:    {params['max_atr_mult']}")
    print(f"   threshold_pct:   {params['threshold_pct']}%")
    print(f"   min/max_risk:    {params['min_risk_points']} / {params['max_risk_points']}")
    print(f"   expiry_candles:  {params['expiry_candles']}")
    print(f"   risk_per_trade:  {params['risk_per_trade_pct']*100}%")
    print(f"   spread:          {params['avg_spread_points']} pts")
    print(f"   sessions:        {list(params['sessions'].keys())}")
    print(f"   initial_balance: ${params['initial_balance']:,.0f}")
    print(f"   ftmo_daily_loss: {params['ftmo_daily_loss_pct']}%")

    print(f"\nDetectando FVGs y ejecutando backtest...")
    bt = FVGBacktester(params)
    df_results = bt.run(df_m5, df_m1)

    bt.print_summary(df_results, "M5", "M1")

    if not df_results.empty:
        Path(OUTPUT).parent.mkdir(parents=True, exist_ok=True)
        df_results.to_csv(OUTPUT, index=False)
        print(f"Trades guardados en: {OUTPUT}")

        winners = df_results[df_results["pnl_usd"] > 0].copy()
        print(f"\n{'='*60}")
        print(f" ULTIMAS 10 OPERACIONES GANADORAS")
        print(f"{'='*60}")

        if len(winners) == 0:
            print("  No hay operaciones ganadoras.")
        else:
            last_10 = winners.tail(10)
            cols = [
                "trade_id", "entry_time", "direction", "entry_price",
                "sl", "tp", "exit_price", "exit_reason",
                "pnl_points", "pnl_usd", "pnl_r", "session", "fvg_type",
            ]
            import pandas as pd
            pd.set_option("display.max_columns", 20)
            pd.set_option("display.width", 250)
            pd.set_option("display.max_colwidth", 20)
            print(last_10[cols].to_string(index=False))
        print()


if __name__ == "__main__":
    main()
