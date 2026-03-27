# -*- coding: utf-8 -*-
"""
Backtest para Pivot Scalping M5/M1
Detecta pivots en M5, entra en M1
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
import sys
import os

# Agregar path para imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Importar backtester
from strategies.pivot_scalping.backtest.scalping_backtester import ScalpingBacktester


def load_config(config_path=None):
    """Carga configuración desde YAML"""
    if config_path is None:
        config_path = Path(__file__).parent / 'config' / 'scalping_params_M5M1.yaml'
    
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def print_summary(df_results, backtester):
    """Imprime resumen de resultados"""
    print("\n" + "="*80)
    print("  RESUMEN DE RESULTADOS - M5/M1")
    print("="*80)
    
    # Métricas básicas
    total_trades = len(df_results)
    wins = len(df_results[df_results['pnl_usd'] > 0])
    losses = len(df_results[df_results['pnl_usd'] <= 0])
    win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
    
    print(f"\n📊 Trades:")
    print(f"   Total:     {total_trades}")
    print(f"   Ganados:   {wins} ({win_rate:.1f}%)")
    print(f"   Perdidos:  {losses} ({100-win_rate:.1f}%)")
    
    # PnL en USD
    total_pnl_usd = df_results['pnl_usd'].sum()
    avg_win_usd = df_results[df_results['pnl_usd'] > 0]['pnl_usd'].mean() if wins > 0 else 0
    avg_loss_usd = df_results[df_results['pnl_usd'] <= 0]['pnl_usd'].mean() if losses > 0 else 0
    
    # PnL en Puntos
    avg_win_pts = df_results[df_results['pnl_usd'] > 0]['pnl_points_net'].mean() if wins > 0 else 0
    avg_loss_pts = df_results[df_results['pnl_usd'] <= 0]['pnl_points_net'].mean() if losses > 0 else 0
    
    # R-Multiples
    avg_r_win = df_results[df_results['pnl_usd'] > 0]['r_multiple'].mean() if wins > 0 else 0
    avg_r_loss = df_results[df_results['pnl_usd'] <= 0]['r_multiple'].mean() if losses > 0 else 0
    
    print(f"\n💰 Profit/Loss (USD):")
    print(f"   Total:        ${total_pnl_usd:,.2f}")
    print(f"   Avg Win:      ${avg_win_usd:,.2f} ({avg_r_win:.2f}R)")
    print(f"   Avg Loss:     ${avg_loss_usd:,.2f} ({avg_r_loss:.2f}R)")
    
    print(f"\n📊 Profit/Loss (Puntos):")
    print(f"   Avg Win:      {avg_win_pts:.2f} pts")
    print(f"   Avg Loss:     {avg_loss_pts:.2f} pts")
    
    # Profit Factor en USD y Puntos
    gross_profit_usd = df_results[df_results['pnl_usd'] > 0]['pnl_usd'].sum()
    gross_loss_usd = abs(df_results[df_results['pnl_usd'] <= 0]['pnl_usd'].sum())
    pf_usd = gross_profit_usd / gross_loss_usd if gross_loss_usd > 0 else 0
    
    gross_profit_pts = df_results[df_results['pnl_points_net'] > 0]['pnl_points_net'].sum()
    gross_loss_pts = abs(df_results[df_results['pnl_points_net'] <= 0]['pnl_points_net'].sum())
    pf_pts = gross_profit_pts / gross_loss_pts if gross_loss_pts > 0 else 0
    
    print(f"\n📈 Métricas:")
    print(f"   Profit Factor (USD):    {pf_usd:.2f} ← MÉTRICA REAL")
    print(f"   Profit Factor (Puntos): {pf_pts:.2f} (referencia)")
    print(f"   Retorno:                {(total_pnl_usd / backtester.initial_balance * 100):.2f}%")
    
    # Break Even y Trailing
    be_count = len(df_results[df_results['be_activated'] == True])
    trailing_count = len(df_results[df_results['trailing_activated'] == True])
    
    print(f"\n🎯 Gestión:")
    print(f"   Break Even:    {be_count} trades ({be_count/total_trades*100:.1f}%)")
    print(f"   Trailing:      {trailing_count} trades ({trailing_count/total_trades*100:.1f}%)")
    
    # Salidas
    print(f"\n🚪 Salidas:")
    for status in df_results['status'].unique():
        count = len(df_results[df_results['status'] == status])
        print(f"   {status:15s}: {count} ({count/total_trades*100:.1f}%)")
    
    # Balance final
    print(f"\n💵 Balance:")
    print(f"   Inicial:  ${backtester.initial_balance:,.2f}")
    print(f"   Final:    ${backtester.balance:,.2f}")
    print(f"   Cambio:   ${backtester.balance - backtester.initial_balance:,.2f}")
    
    print(f"\n{'='*80}\n")


def main():
    parser = argparse.ArgumentParser(description='Backtest de Pivot Scalping M5/M1')
    parser.add_argument('--data-m1', required=True, help='Archivo CSV con datos M1')
    parser.add_argument('--data-m5', required=True, help='Archivo CSV con datos M5 (pivots)')
    parser.add_argument('--instrument', default='US30', help='Nombre del instrumento')
    parser.add_argument('--config', default=None, help='Archivo de configuración YAML')
    parser.add_argument('--output', default=None, help='Archivo de salida para resultados')
    parser.add_argument('--balance', type=float, default=100000.0, help='Balance inicial')
    
    args = parser.parse_args()
    
    # Cargar configuración
    print("⚙️  Cargando configuración...")
    config = load_config(args.config)
    
    # Cargar datos
    print(f"📥 Cargando datos...")
    print(f"   M1 (entry):  {args.data_m1}")
    print(f"   M5 (pivots): {args.data_m5}")
    
    try:
        df_m1 = pd.read_csv(args.data_m1)
        df_m5 = pd.read_csv(args.data_m5)
    except Exception as e:
        print(f"\n❌ Error cargando datos: {e}\n")
        sys.exit(1)
    
    # Crear backtester
    print("\n" + "="*80)
    print(f"  BACKTEST: {args.instrument} - Pivot Scalping M5/M1")
    print("="*80)
    
    backtester = ScalpingBacktester(config, args.balance)
    
    print(f"\n📊 Datos cargados:")
    print(f"   M5 (pivots): {len(df_m5)} velas")
    print(f"   M1 (entry):  {len(df_m1)} velas")
    
    # Convertir timestamps
    df_m5['time'] = pd.to_datetime(df_m5['time'])
    df_m1['time'] = pd.to_datetime(df_m1['time'])
    
    print(f"   Período: {df_m1['time'].iloc[0]} → {df_m1['time'].iloc[-1]}")
    
    # Ejecutar backtest
    # NOTA: El backtester espera M15 y M5, pero le pasamos M5 y M1
    # Esto funciona porque internamente solo usa los nombres, no valida timeframes
    df_results = backtester.run(df_m5, df_m1)  # M5 como "M15", M1 como "M5"
    
    # Imprimir resumen
    if len(df_results) > 0:
        print_summary(df_results, backtester)
        
        # Guardar resultados
        if args.output:
            df_results.to_csv(args.output, index=False)
            print(f"💾 Resultados guardados en: {args.output}\n")
    else:
        print("\n⚠️  No se generaron trades en el período analizado\n")
    
    # Retornar código de éxito
    if len(df_results) > 0 and df_results['pnl_usd'].sum() > 0:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == '__main__':
    main()
