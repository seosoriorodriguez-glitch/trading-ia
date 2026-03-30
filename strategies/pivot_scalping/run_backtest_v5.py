# -*- coding: utf-8 -*-
"""
Runner de Backtest V5 — Order Blocks (EXPERIMENTAL)

Uso:
    python strategies/pivot_scalping/run_backtest_v5.py \
      --data-m1 data/US30_cash_M1_30k.csv \
      --data-m5 data/US30_cash_M5_29d.csv \
      --instrument US30 \
      --output data/backtest_v5_results.csv \
      --balance 100000

Parametros clave:
    --impulse-points  Movimiento minimo para confirmar impulso (default: 50)
    --impulse-candles Velas adelante para medir impulso (default: 3)
"""
import sys
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

import argparse
import pandas as pd
import yaml
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from strategies.pivot_scalping.backtest.scalping_backtester_v5 import ScalpingBacktesterV5


def load_config(config_path=None):
    if config_path is None:
        config_path = Path(__file__).parent / 'config' / 'scalping_params_M5M1_v5_test.yaml'
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def print_summary(df_results, backtester, label="V5"):
    print("\n" + "="*80)
    print(f"  RESUMEN DE RESULTADOS -- {label}")
    print("="*80)

    total = len(df_results)
    if total == 0:
        print("\n  Sin trades en el periodo analizado.\n")
        return

    wins   = len(df_results[df_results['pnl_usd'] > 0])
    losses = len(df_results[df_results['pnl_usd'] <= 0])
    wr     = wins / total * 100

    print(f"\nTrades:")
    print(f"   Total:    {total}")
    print(f"   Ganados:  {wins} ({wr:.1f}%)")
    print(f"   Perdidos: {losses} ({100 - wr:.1f}%)")

    total_usd   = df_results['pnl_usd'].sum()
    avg_win_usd = df_results[df_results['pnl_usd'] > 0]['pnl_usd'].mean() if wins   > 0 else 0
    avg_los_usd = df_results[df_results['pnl_usd'] <= 0]['pnl_usd'].mean() if losses > 0 else 0
    avg_r_win   = df_results[df_results['pnl_usd'] > 0]['r_multiple'].mean() if wins   > 0 else 0
    avg_r_los   = df_results[df_results['pnl_usd'] <= 0]['r_multiple'].mean() if losses > 0 else 0

    print(f"\nPnL (USD):")
    print(f"   Total:     ${total_usd:,.2f}")
    print(f"   Avg Win:   ${avg_win_usd:,.2f} ({avg_r_win:.2f}R)")
    print(f"   Avg Loss:  ${avg_los_usd:,.2f} ({avg_r_los:.2f}R)")

    gp = df_results[df_results['pnl_usd'] > 0]['pnl_usd'].sum()
    gl = abs(df_results[df_results['pnl_usd'] <= 0]['pnl_usd'].sum())
    pf = gp / gl if gl > 0 else float('inf')

    retorno = total_usd / backtester.initial_balance * 100
    trades_dia = total / max(
        (pd.to_datetime(df_results['exit_time'].max()) -
         pd.to_datetime(df_results['entry_time'].min())).days, 1
    )

    print(f"\nMetricas:")
    print(f"   Profit Factor: {pf:.2f}")
    print(f"   Retorno:       {retorno:.2f}%")
    print(f"   Trades/dia:    {trades_dia:.2f}")

    print(f"\nSalidas:")
    for status, count in df_results['status'].value_counts().items():
        print(f"   {status:20s}: {count} ({count/total*100:.1f}%)")

    print(f"\nBalance:")
    print(f"   Inicial: ${backtester.initial_balance:,.2f}")
    print(f"   Final:   ${backtester.balance:,.2f}")
    print(f"   Cambio:  ${backtester.balance - backtester.initial_balance:,.2f}")

    print(f"\n{'='*80}\n")


def main():
    parser = argparse.ArgumentParser(description='Backtest V5 -- Order Blocks')
    parser.add_argument('--data-m1',         required=True, help='CSV con datos M1 (entradas)')
    parser.add_argument('--data-m5',         required=True, help='CSV con datos M5 (order blocks)')
    parser.add_argument('--instrument',      default='US30')
    parser.add_argument('--config',          default=None)
    parser.add_argument('--output',          default=None)
    parser.add_argument('--balance',         type=float, default=100000.0)
    parser.add_argument('--impulse-points',  type=float, default=None,
                        help='Movimiento minimo para confirmar impulso (pts)')
    parser.add_argument('--impulse-candles', type=int,   default=None,
                        help='Velas adelante para medir impulso')
    parser.add_argument('--max-zones',       type=int,   default=None,
                        help='Max OBs activos por tipo')
    args = parser.parse_args()

    print("Cargando configuracion V5...")
    config = load_config(args.config)

    if args.impulse_points is not None:
        config['order_blocks']['impulse_points'] = args.impulse_points
        print(f"   impulse_points = {args.impulse_points}")
    if args.impulse_candles is not None:
        config['order_blocks']['impulse_candles'] = args.impulse_candles
        print(f"   impulse_candles = {args.impulse_candles}")
    if args.max_zones is not None:
        config['order_blocks']['max_active_zones'] = args.max_zones
        print(f"   max_active_zones = {args.max_zones}")

    print(f"Cargando datos...")
    print(f"   M1 (entry):       {args.data_m1}")
    print(f"   M5 (order blocks):{args.data_m5}")

    try:
        df_m1 = pd.read_csv(args.data_m1)
        df_m5 = pd.read_csv(args.data_m5)
    except Exception as e:
        print(f"\nError cargando datos: {e}\n")
        sys.exit(1)

    df_m5['time'] = pd.to_datetime(df_m5['time'])
    df_m1['time'] = pd.to_datetime(df_m1['time'])

    ob_cfg = config['order_blocks']
    print(f"\n{'='*80}")
    print(f"  BACKTEST V5: {args.instrument} -- Order Blocks")
    print(f"  impulse_points={ob_cfg['impulse_points']}  "
          f"impulse_candles={ob_cfg['impulse_candles']}  "
          f"buffer_SL={config['stop_loss']['buffer_points']}")
    print(f"{'='*80}\n")
    print(f"Datos:")
    print(f"   M5 (OBs):   {len(df_m5)} velas")
    print(f"   M1 (entry): {len(df_m1)} velas")
    print(f"   Periodo: {df_m1['time'].iloc[0]} -> {df_m1['time'].iloc[-1]}\n")

    backtester = ScalpingBacktesterV5(config, args.balance)
    df_results = backtester.run(df_m5, df_m1, instrument=args.instrument)

    label = (f"V5 -- {args.instrument} | OB "
             f"impulse={ob_cfg['impulse_points']}pts/{ob_cfg['impulse_candles']}c")

    if len(df_results) > 0:
        print_summary(df_results, backtester, label=label)
        if args.output:
            df_results.to_csv(args.output, index=False)
            print(f"Resultados guardados en: {args.output}\n")
    else:
        print("\nSin trades en el periodo analizado.\n")

    sys.exit(0 if len(df_results) > 0 and df_results['pnl_usd'].sum() > 0 else 1)


if __name__ == '__main__':
    main()
