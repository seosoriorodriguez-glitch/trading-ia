# -*- coding: utf-8 -*-
"""
Runner de Backtest V3 — Pivot Scalping M5/M1 (EXPERIMENTAL)

Uso:
    python strategies/pivot_scalping/run_backtest_v3.py \
      --data-m1 data/US30_cash_M1_30k.csv \
      --data-m5 data/US30_cash_M5_29d.csv \
      --instrument US30 \
      --output data/backtest_v3_results.csv \
      --balance 100000

    # Probar diferentes max_active_zones (Punto 8):
    python ... --max-zones 6
    python ... --max-zones 8
    python ... --max-zones 12   (default)

NO modifica ni reemplaza run_backtest_m5m1.py (producción).
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

from strategies.pivot_scalping.backtest.scalping_backtester_v3 import ScalpingBacktesterV3


def load_config(config_path=None):
    if config_path is None:
        config_path = Path(__file__).parent / 'config' / 'scalping_params_M5M1_v3_test.yaml'
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def print_summary(df_results, backtester, label="V3"):
    print("\n" + "="*80)
    print(f"  RESUMEN DE RESULTADOS — {label}")
    print("="*80)

    total = len(df_results)
    if total == 0:
        print("\n  Sin trades en el periodo analizado.\n")
        return

    wins   = len(df_results[df_results['pnl_usd'] > 0])
    losses = len(df_results[df_results['pnl_usd'] <= 0])
    wr     = wins / total * 100

    print(f"\n📊 Trades:")
    print(f"   Total:    {total}")
    print(f"   Ganados:  {wins} ({wr:.1f}%)")
    print(f"   Perdidos: {losses} ({100 - wr:.1f}%)")

    total_usd   = df_results['pnl_usd'].sum()
    avg_win_usd = df_results[df_results['pnl_usd'] > 0]['pnl_usd'].mean() if wins   > 0 else 0
    avg_los_usd = df_results[df_results['pnl_usd'] <= 0]['pnl_usd'].mean() if losses > 0 else 0
    avg_r_win   = df_results[df_results['pnl_usd'] > 0]['r_multiple'].mean() if wins   > 0 else 0
    avg_r_los   = df_results[df_results['pnl_usd'] <= 0]['r_multiple'].mean() if losses > 0 else 0

    print(f"\n💰 PnL (USD):")
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

    print(f"\n📈 Métricas:")
    print(f"   Profit Factor: {pf:.2f}")
    print(f"   Retorno:       {retorno:.2f}%")
    print(f"   Trades/día:    {trades_dia:.2f}")

    print(f"\n🚪 Salidas:")
    for status, count in df_results['status'].value_counts().items():
        print(f"   {status:20s}: {count} ({count/total*100:.1f}%)")

    print(f"\n💵 Balance:")
    print(f"   Inicial: ${backtester.initial_balance:,.2f}")
    print(f"   Final:   ${backtester.balance:,.2f}")
    print(f"   Cambio:  ${backtester.balance - backtester.initial_balance:,.2f}")

    print(f"\n{'='*80}\n")


def main():
    parser = argparse.ArgumentParser(description='Backtest V3 — Pivot Scalping M5/M1')
    parser.add_argument('--data-m1',    required=True,  help='CSV con datos M1 (entradas)')
    parser.add_argument('--data-m5',    required=True,  help='CSV con datos M5 (pivots)')
    parser.add_argument('--instrument', default='US30', help='Nombre del instrumento')
    parser.add_argument('--config',     default=None,   help='YAML de configuración (default: v3_test)')
    parser.add_argument('--output',     default=None,   help='CSV de salida con resultados')
    parser.add_argument('--balance',    type=float, default=100000.0)
    parser.add_argument('--max-zones',  type=int,   default=None,
                        help='Override max_active_zones (6, 8, 12) — Punto 8')
    args = parser.parse_args()

    print("⚙️  Cargando configuración V3...")
    config = load_config(args.config)

    # Override max_active_zones si se pasa por argumento (Punto 8)
    if args.max_zones is not None:
        config['pivots']['max_active_zones'] = args.max_zones
        print(f"   max_active_zones = {args.max_zones} (override)")

    print(f"📥 Cargando datos...")
    print(f"   M1 (entry):  {args.data_m1}")
    print(f"   M5 (pivots): {args.data_m5}")

    try:
        df_m1 = pd.read_csv(args.data_m1)
        df_m5 = pd.read_csv(args.data_m5)
    except Exception as e:
        print(f"\n❌ Error cargando datos: {e}\n")
        sys.exit(1)

    df_m5['time'] = pd.to_datetime(df_m5['time'])
    df_m1['time'] = pd.to_datetime(df_m1['time'])

    print(f"\n{'='*80}")
    print(f"  BACKTEST V3: {args.instrument} — Pivot Scalping M5/M1")
    print(f"  Puntos activos: 2 (activación correcta), 3 (zona simple), 8 (priorización)")
    print(f"{'='*80}\n")
    print(f"📊 Datos:")
    print(f"   M5 (pivots): {len(df_m5)} velas")
    print(f"   M1 (entry):  {len(df_m1)} velas")
    print(f"   Período: {df_m1['time'].iloc[0]} → {df_m1['time'].iloc[-1]}")
    print(f"   max_active_zones: {config['pivots']['max_active_zones']}\n")

    backtester = ScalpingBacktesterV3(config, args.balance)

    # M5 como "M15" (pivots), M1 como "M5" (entradas) — igual que el runner de producción
    df_results = backtester.run(df_m5, df_m1, instrument=args.instrument)

    label = f"V3 — {args.instrument} | zones={config['pivots']['max_active_zones']}"

    if len(df_results) > 0:
        print_summary(df_results, backtester, label=label)

        if args.output:
            df_results.to_csv(args.output, index=False)
            print(f"💾 Resultados guardados en: {args.output}\n")
    else:
        print("\n⚠️  Sin trades en el período analizado.\n")

    sys.exit(0 if len(df_results) > 0 and df_results['pnl_usd'].sum() > 0 else 1)


if __name__ == '__main__':
    main()
