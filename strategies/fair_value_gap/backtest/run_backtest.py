# -*- coding: utf-8 -*-
"""
Runner CLI para el backtest de Fair Value Gap.

Uso basico:
    # US30 - entrada conservadora (cierre dentro del gap)
    python strategies/fair_value_gap/backtest/run_backtest.py \
        --data-higher data/US30_cash_M5_260d.csv \
        --data-lower  data/US30_cash_M1_30k.csv \
        --tf-higher M5 --tf-lower M1 \
        --symbol US30 \
        --output strategies/fair_value_gap/backtest/results/fvg_us30_M5M1.csv

    # NAS100 - entrada agresiva (toque de zona)
    python strategies/fair_value_gap/backtest/run_backtest.py \
        --data-higher data/NAS100_M5.csv \
        --data-lower  data/NAS100_M1.csv \
        --symbol NAS100 \
        --entry-method aggressive \
        --output strategies/fair_value_gap/backtest/results/fvg_nas100_aggressive.csv

    # Comparar RR:
    python ... --target-rr 2.0
    python ... --target-rr 3.5

    # Comparar metodos de entrada:
    python ... --entry-method conservative
    python ... --entry-method aggressive
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

from strategies.fair_value_gap.backtest.config import US30_PARAMS, NAS100_PARAMS
from strategies.fair_value_gap.backtest.data_loader import load_csv, validate_alignment
from strategies.fair_value_gap.backtest.backtester import FVGBacktester


SYMBOL_PARAMS = {
    "US30":   US30_PARAMS,
    "NAS100": NAS100_PARAMS,
}


def main():
    parser = argparse.ArgumentParser(description="Fair Value Gap Backtester")
    parser.add_argument("--data-higher", required=True,
                        help="CSV del TF mayor (FVG detection): M15 o M5")
    parser.add_argument("--data-lower",  required=True,
                        help="CSV del TF menor (entradas): M5 o M1")
    parser.add_argument("--tf-higher",   default="M5",
                        help="Nombre del TF mayor para el reporte (default: M5)")
    parser.add_argument("--tf-lower",    default="M1",
                        help="Nombre del TF menor para el reporte (default: M1)")
    parser.add_argument("--symbol",      default="US30",
                        choices=["US30", "NAS100"],
                        help="Activo a backtestear (default: US30)")
    parser.add_argument("--output",      default=None,
                        help="CSV de salida con trades (opcional)")
    parser.add_argument("--balance",     type=float, default=None,
                        help="Balance inicial (default: 100000)")

    # Overrides de parametros clave
    parser.add_argument("--entry-method", default=None,
                        choices=["conservative", "aggressive"],
                        help="Metodo de entrada: conservative (cierre en zona) o aggressive (toque)")
    parser.add_argument("--target-rr",    type=float, default=None,
                        help="R:R objetivo para TP")
    parser.add_argument("--buffer",       type=int,   default=None,
                        help="Buffer SL en puntos")
    parser.add_argument("--threshold",    type=float, default=None,
                        help="Tamano minimo del FVG como %% del precio (0=desactivado)")
    parser.add_argument("--min-zone-pts", type=float, default=None,
                        help="Tamano minimo absoluto del FVG en puntos (0=desactivado)")
    parser.add_argument("--ftmo-daily",   type=float, default=None,
                        help="Limite de perdida diaria FTMO en %% del balance inicial (default: 4.5)")
    parser.add_argument("--expiry",       type=int,   default=None,
                        help="Velas del TF mayor para expirar FVG")
    parser.add_argument("--session",      default=None,
                        choices=["new_york", "london", "both"],
                        help="Sesion a operar")
    parser.add_argument("--no-rejection", action="store_true",
                        help="Desactivar filtro de vela de rechazo")
    parser.add_argument("--no-bos",       action="store_true",
                        help="Desactivar filtro BOS")
    parser.add_argument("--ema-period",   type=int,   default=None,
                        help="Periodo EMA 4H para filtro de tendencia (0=desactivar)")
    args = parser.parse_args()

    # Seleccionar params base segun simbolo
    params = copy.deepcopy(SYMBOL_PARAMS[args.symbol])

    # Aplicar overrides
    if args.balance      is not None: params["initial_balance"]  = args.balance
    if args.entry_method is not None: params["entry_method"]     = args.entry_method
    if args.target_rr    is not None: params["target_rr"]        = args.target_rr
    if args.buffer       is not None: params["buffer_points"]    = args.buffer
    if args.threshold    is not None: params["threshold_pct"]    = args.threshold
    if args.min_zone_pts is not None: params["min_zone_points"]  = args.min_zone_pts
    if args.ftmo_daily   is not None: params["ftmo_daily_loss_pct"] = args.ftmo_daily
    if args.expiry       is not None: params["expiry_candles"]   = args.expiry
    if args.no_rejection:             params["require_rejection"] = False
    if args.no_bos:                   params["require_bos"]       = False
    if args.ema_period   is not None:
        if args.ema_period == 0:
            params["ema_trend_filter"] = False
        else:
            params["ema_4h_period"]    = args.ema_period
            params["ema_trend_filter"] = True
    if args.session == "new_york":
        params["sessions"] = {"new_york": params["sessions"]["new_york"]}
    elif args.session == "london":
        # Si se agrega sesion london en el futuro, configurarla aqui
        params["sessions"] = {"london": {"start": "09:00", "end": "12:00", "skip_minutes": 15}}

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
    print(f"   symbol:          {params['symbol']}")
    print(f"   entry_method:    {params['entry_method']}")
    print(f"   target_rr:       {params['target_rr']}")
    print(f"   buffer_points:   {params['buffer_points']}")
    print(f"   threshold_pct:   {params['threshold_pct']}%")
    print(f"   min/max_risk:    {params['min_risk_points']} / {params['max_risk_points']}")
    print(f"   expiry_candles:  {params['expiry_candles']}")
    print(f"\nDetectando FVGs y ejecutando backtest...")

    bt = FVGBacktester(params)
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
