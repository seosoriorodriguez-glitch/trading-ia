# -*- coding: utf-8 -*-
"""FVG Backtest con min_zone_points=5, max_sim=1, look-ahead fix."""
import sys
import copy
import traceback
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

def main():
    t0 = time.time()

    from strategies.fair_value_gap.backtest.config import US30_PARAMS
    from strategies.fair_value_gap.backtest.data_loader import load_csv, validate_alignment
    from strategies.fair_value_gap.backtest.backtester import FVGBacktester

    params = copy.deepcopy(US30_PARAMS)

    print(f"min_zone_points={params['min_zone_points']} "
          f"max_sim={params['max_simultaneous_trades']} "
          f"rr={params['target_rr']} buf={params['buffer_points']} "
          f"ftmo={params['ftmo_daily_loss_pct']}% "
          f"sessions={list(params['sessions'].keys())}", flush=True)

    df_m5 = load_csv("data/US30_icm_M5_518d.csv")
    df_m1 = load_csv("data/US30_icm_M1_500k.csv")
    validate_alignment(df_m5, df_m1)
    print(f"M5={len(df_m5)} M1={len(df_m1)}", flush=True)
    print("Running...", flush=True)

    bt = FVGBacktester(params)
    df_results = bt.run(df_m5, df_m1)

    elapsed = time.time() - t0
    print(f"Done: {len(df_results)} trades in {elapsed:.0f}s", flush=True)

    csv_out = "strategies/fair_value_gap/backtest/results/fvg_live_minzone5.csv"
    Path(csv_out).parent.mkdir(parents=True, exist_ok=True)
    df_results.to_csv(csv_out, index=False)
    print(f"Saved: {csv_out}", flush=True)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"FATAL: {e}", flush=True)
        traceback.print_exc()
        sys.exit(1)
