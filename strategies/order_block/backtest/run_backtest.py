# -*- coding: utf-8 -*-
"""
Runner CLI para el backtest de Order Blocks.

Uso:
    python strategies/order_block/backtest/run_backtest.py \
        --data-higher data/US30_cash_M5_260d.csv \
        --data-lower  data/US30_cash_M1_30k.csv \
        --tf-higher M5 --tf-lower M1 \
        --output strategies/order_block/backtest/results/ob_M5M1.csv

    # Probar N consecutivas:
    python ... --consecutive 3
    python ... --consecutive 5

    # Probar diferentes RR:
    python ... --target-rr 2.0
    python ... --target-rr 2.5

    # Zona full candle:
    python ... --zone-type full_candle
"""
import sys
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

import argparse
import copy
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from strategies.order_block.backtest.config import DEFAULT_PARAMS
from strategies.order_block.backtest.data_loader import load_csv, validate_alignment
from strategies.order_block.backtest.backtester import OrderBlockBacktester


def main():
    parser = argparse.ArgumentParser(description="Order Block Backtester - US30")
    parser.add_argument("--data-higher", required=True,
                        help="CSV del TF mayor (OB detection): M15 o M5")
    parser.add_argument("--data-lower",  required=True,
                        help="CSV del TF menor (entradas): M5 o M1")
    parser.add_argument("--tf-higher",   default="M15",
                        help="Nombre del TF mayor para el reporte (default: M15)")
    parser.add_argument("--tf-lower",    default="M5",
                        help="Nombre del TF menor para el reporte (default: M5)")
    parser.add_argument("--output",      default=None,
                        help="CSV de salida con trades (opcional)")
    parser.add_argument("--balance",     type=float, default=None,
                        help="Balance inicial (default: 100000)")
    # Overrides de parametros
    parser.add_argument("--consecutive", type=int,   default=None,
                        help="N velas consecutivas para confirmar OB (default: 5)")
    parser.add_argument("--target-rr",   type=float, default=None,
                        help="R:R objetivo para TP (default: 2.0)")
    parser.add_argument("--zone-type",   default=None,
                        choices=["half_candle", "full_candle"],
                        help="Tipo de zona del OB (default: half_candle)")
    parser.add_argument("--impulse-pct", type=float, default=None,
                        help="Impulso minimo en %% (default: 0.0)")
    parser.add_argument("--expiry",      type=int,   default=None,
                        help="Velas del TF mayor para expirar OB (default: 100)")
    parser.add_argument("--ema-period",  type=int,   default=None,
                        help="Periodo EMA 4H para filtro de tendencia (default: 20, 0=desactivar)")
    parser.add_argument("--session",     default=None,
                        choices=["london", "new_york", "both"],
                        help="Sesion a operar (default: both)")
    parser.add_argument("--no-rejection", action="store_true",
                        help="Desactivar filtro de vela de rechazo")
    parser.add_argument("--no-bos",       action="store_true",
                        help="Desactivar filtro BOS")
    parser.add_argument("--buffer",      type=int,   default=None,
                        help="Buffer SL en puntos (default: 20)")
    args = parser.parse_args()

    # Copiar params y aplicar overrides
    params = copy.deepcopy(DEFAULT_PARAMS)
    if args.balance      is not None: params["initial_balance"]    = args.balance
    if args.consecutive  is not None: params["consecutive_candles"] = args.consecutive
    if args.target_rr    is not None: params["target_rr"]          = args.target_rr
    if args.zone_type    is not None: params["zone_type"]          = args.zone_type
    if args.impulse_pct  is not None: params["min_impulse_pct"]    = args.impulse_pct / 100
    if args.expiry       is not None: params["expiry_candles"]     = args.expiry
    if args.ema_period   is not None:
        if args.ema_period == 0:
            params["ema_trend_filter"] = False
        else:
            params["ema_4h_period"]    = args.ema_period
            params["ema_trend_filter"] = True
    if args.session == "london":
        params["sessions"] = {"london": params["sessions"]["london"]}
    elif args.session == "new_york":
        params["sessions"] = {"new_york": params["sessions"]["new_york"]}
    if args.no_rejection: params["require_rejection"] = False
    if args.no_bos:       params["require_bos"]       = False
    if args.buffer is not None: params["buffer_points"] = args.buffer

    print(f"\nCargando datos...")
    try:
        df_higher = load_csv(args.data_higher)
        df_lower  = load_csv(args.data_lower)
    except (FileNotFoundError, ValueError) as e:
        print(f"\nERROR: {e}\n")
        sys.exit(1)

    validate_alignment(df_higher, df_lower)

    print(f"   {args.tf_higher}: {len(df_higher)} velas  "
          f"({df_higher['time'].iloc[0]} -> {df_higher['time'].iloc[-1]})")
    print(f"   {args.tf_lower}:  {len(df_lower)} velas  "
          f"({df_lower['time'].iloc[0]} -> {df_lower['time'].iloc[-1]})")
    print(f"\nParametros:")
    print(f"   consecutive_candles: {params['consecutive_candles']}")
    print(f"   zone_type:           {params['zone_type']}")
    print(f"   target_rr:           {params['target_rr']}")
    print(f"   buffer_points:       {params['buffer_points']}")
    print(f"   min/max_risk:        {params['min_risk_points']} / {params['max_risk_points']}")
    print(f"   expiry_candles:      {params['expiry_candles']}")
    print(f"\nDetectando OBs y ejecutando backtest...")

    bt = OrderBlockBacktester(params)
    df_results = bt.run(df_higher, df_lower)

    bt.print_summary(df_results, args.tf_higher, args.tf_lower)

    if not df_results.empty and args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        df_results.to_csv(args.output, index=False)
        print(f"Trades guardados en: {args.output}\n")

    if df_results.empty:
        sys.exit(1)
    sys.exit(0 if bt.balance > bt.initial_balance else 1)


if __name__ == "__main__":
    main()
