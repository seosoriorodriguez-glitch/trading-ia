# -*- coding: utf-8 -*-
"""
Runner de Backtest V4 — Prev-Day H/L + Market Structure (EXPERIMENTAL)

Uso:
    python strategies/pivot_scalping/run_backtest_v4.py \
      --data-m1 data/US30_cash_M1_30k.csv \
      --data-m5 data/US30_cash_M5_29d.csv \
      --instrument US30 \
      --output data/backtest_v4_results.csv \
      --balance 100000
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

from strategies.pivot_scalping.backtest.scalping_backtester_v4 import ScalpingBacktesterV4


def load_config(config_path=None):
    if config_path is None:
        config_path = Path(__file__).parent / 'config' / 'scalping_params_M5M1_v4_test.yaml'
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def print_summary(df_results, backtester, label="V4"):
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
    parser = argparse.ArgumentParser(description='Backtest V4 -- Prev-Day H/L + Market Structure')
    parser.add_argument('--data-m1',    required=True,  help='CSV con datos M1 (entradas)')
    parser.add_argument('--data-m5',    required=True,  help='CSV con datos M5 (zonas diarias)')
    parser.add_argument('--data-m15',   default=None,   help='CSV con datos M15 para estructura (opcional, default: usa M5)')
    parser.add_argument('--instrument', default='US30', help='Nombre del instrumento')
    parser.add_argument('--config',     default=None,   help='YAML de configuracion (default: v4_test)')
    parser.add_argument('--output',     default=None,   help='CSV de salida con resultados')
    parser.add_argument('--balance',    type=float, default=100000.0)
    parser.add_argument('--swing-strength', type=int, default=None,
                        help='Override structure_swing_strength')
    args = parser.parse_args()

    print("Cargando configuracion V4...")
    config = load_config(args.config)

    if args.swing_strength is not None:
        config['pivots']['structure_swing_strength'] = args.swing_strength
        print(f"   structure_swing_strength = {args.swing_strength} (override)")

    print(f"Cargando datos...")
    print(f"   M1 (entry):  {args.data_m1}")
    print(f"   M5 (zonas):  {args.data_m5}")
    if args.data_m15:
        print(f"   M15 (estructura): {args.data_m15}")

    try:
        df_m1 = pd.read_csv(args.data_m1)
        df_m5 = pd.read_csv(args.data_m5)
        df_m15 = pd.read_csv(args.data_m15) if args.data_m15 else None
    except Exception as e:
        print(f"\nError cargando datos: {e}\n")
        sys.exit(1)

    df_m5['time'] = pd.to_datetime(df_m5['time'])
    df_m1['time'] = pd.to_datetime(df_m1['time'])
    if df_m15 is not None:
        df_m15['time'] = pd.to_datetime(df_m15['time'])

    structure_label = f"M15 ({len(df_m15)} velas)" if df_m15 is not None else f"M5 (mismo dataset)"

    print(f"\n{'='*80}")
    print(f"  BACKTEST V4: {args.instrument} -- Prev-Day H/L + Market Structure")
    print(f"  Zonas: High/Low del dia anterior (2 zonas/dia)")
    print(f"  Estructura: {structure_label}")
    print(f"  Direccion: HH+HL=long, LH+LL=short, mixto=no operar")
    print(f"{'='*80}\n")
    print(f"Datos:")
    print(f"   M5 (zonas):  {len(df_m5)} velas")
    print(f"   M1 (entry):  {len(df_m1)} velas")
    print(f"   Periodo: {df_m1['time'].iloc[0]} -> {df_m1['time'].iloc[-1]}")
    print(f"   structure_swing_strength: {config['pivots'].get('structure_swing_strength', 10)}")
    print(f"   zone_buffer: {config['pivots'].get('zone_buffer', 20)}\n")

    backtester = ScalpingBacktesterV4(config, args.balance)

    # Inyectar M15 para estructura si se proporcionó
    if df_m15 is not None:
        from strategies.pivot_scalping.core.pivot_detection import Candle
        m15_candles = [
            Candle(
                time=row['time'].to_pydatetime(),
                open=row['open'], high=row['high'],
                low=row['low'],  close=row['close'],
                volume=row.get('volume', 0),
            )
            for _, row in df_m15.iterrows()
        ]
        backtester.set_structure_data(m15_candles)

    df_results = backtester.run(df_m5, df_m1, instrument=args.instrument)

    label = f"V4 -- {args.instrument} | prev-day H/L + structure"

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
