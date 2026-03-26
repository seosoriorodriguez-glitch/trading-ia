#!/usr/bin/env python3
"""
Simula un portfolio combinando múltiples estrategias

Uso:
    python3 tools/portfolio_simulator.py \
        --strategy sr_swing strategies/sr_swing/data/backtest_US30_v4_longs_only.csv \
        --strategy pivot_scalping strategies/pivot_scalping/data/backtest_US30_scalping_60d.csv
"""

import pandas as pd
import argparse
from pathlib import Path
from typing import Dict, List


def simulate_portfolio(strategy_csvs: Dict[str, str], initial_balance: float = 100000):
    """
    Simula portfolio multi-estrategia
    
    Args:
        strategy_csvs: Dict con {nombre_estrategia: path_csv}
        initial_balance: Balance inicial
    
    Returns:
        DataFrame con historial de balance
    """
    
    all_trades = []
    
    print("\n" + "="*100)
    print("CARGANDO ESTRATEGIAS")
    print("="*100)
    
    # Cargar todos los trades
    for strategy_name, csv_path in strategy_csvs.items():
        try:
            df = pd.read_csv(csv_path)
            df['strategy'] = strategy_name
            all_trades.append(df)
            print(f"✅ {strategy_name:25s}: {len(df):4d} trades cargados desde {Path(csv_path).name}")
        except Exception as e:
            print(f"❌ {strategy_name:25s}: Error - {e}")
            continue
    
    if not all_trades:
        print("\n❌ No se pudieron cargar estrategias")
        return None
    
    # Combinar y ordenar por fecha
    combined = pd.concat(all_trades, ignore_index=True)
    combined['entry_time'] = pd.to_datetime(combined['entry_time'])
    combined = combined.sort_values('entry_time')
    
    print(f"\n📊 Total trades combinados: {len(combined)}")
    print(f"📅 Rango: {combined['entry_time'].min()} → {combined['entry_time'].max()}")
    
    # Simular balance
    balance = initial_balance
    peak = initial_balance
    max_dd = 0
    balance_history = []
    
    for _, trade in combined.iterrows():
        balance += trade['pnl_usd']
        peak = max(peak, balance)
        dd = (peak - balance) / peak if peak > 0 else 0
        max_dd = max(max_dd, dd)
        
        balance_history.append({
            'time': trade['entry_time'],
            'balance': balance,
            'pnl': trade['pnl_usd'],
            'strategy': trade['strategy'],
            'direction': trade['direction']
        })
    
    # Métricas del portfolio
    total_trades = len(combined)
    winners = len(combined[combined['pnl_usd'] > 0])
    win_rate = (winners / total_trades * 100) if total_trades > 0 else 0
    
    gross_profit = combined[combined['pnl_usd'] > 0]['pnl_usd'].sum()
    gross_loss = abs(combined[combined['pnl_usd'] < 0]['pnl_usd'].sum())
    pf = gross_profit / gross_loss if gross_loss > 0 else float('inf')
    
    retorno_pct = ((balance - initial_balance) / initial_balance) * 100
    
    # Calcular período
    date_range_days = (combined['entry_time'].max() - combined['entry_time'].min()).days
    trades_per_month = total_trades / (date_range_days / 30) if date_range_days > 0 else 0
    
    # Mostrar resultados
    print("\n" + "="*100)
    print("SIMULACIÓN DE PORTFOLIO MULTI-ESTRATEGIA")
    print("="*100)
    print(f"Balance Inicial:         ${initial_balance:>12,.2f}")
    print(f"Balance Final:           ${balance:>12,.2f}")
    print(f"Retorno:                 {retorno_pct:>12.2f}%")
    print(f"\nTotal Trades:            {total_trades:>12d}")
    print(f"Ganadoras:               {winners:>12d} ({win_rate:.1f}%)")
    print(f"Perdedoras:              {total_trades - winners:>12d}")
    print(f"Win Rate:                {win_rate:>12.1f}%")
    print(f"Profit Factor:           {pf:>12.2f}")
    print(f"Max Drawdown:            {max_dd * 100:>12.2f}%")
    print(f"\nFrecuencia:              {trades_per_month:>12.1f} trades/mes")
    print(f"Período:                 {date_range_days:>12d} días")
    
    print("\n" + "-"*100)
    print("DESGLOSE POR ESTRATEGIA")
    print("-"*100)
    
    for strategy in sorted(combined['strategy'].unique()):
        strategy_trades = combined[combined['strategy'] == strategy]
        strategy_pnl = strategy_trades['pnl_usd'].sum()
        strategy_winners = len(strategy_trades[strategy_trades['pnl_usd'] > 0])
        strategy_wr = (strategy_winners / len(strategy_trades) * 100) if len(strategy_trades) > 0 else 0
        
        strategy_gross_profit = strategy_trades[strategy_trades['pnl_usd'] > 0]['pnl_usd'].sum()
        strategy_gross_loss = abs(strategy_trades[strategy_trades['pnl_usd'] < 0]['pnl_usd'].sum())
        strategy_pf = strategy_gross_profit / strategy_gross_loss if strategy_gross_loss > 0 else float('inf')
        
        print(f"{strategy:25s}: {len(strategy_trades):4d} trades | WR: {strategy_wr:5.1f}% | PF: {strategy_pf:5.2f} | P&L: ${strategy_pnl:>10,.2f}")
    
    print("\n" + "-"*100)
    print("DESGLOSE POR DIRECCIÓN")
    print("-"*100)
    
    for direction in ['LONG', 'SHORT']:
        dir_trades = combined[combined['direction'] == direction]
        if len(dir_trades) == 0:
            continue
        
        dir_pnl = dir_trades['pnl_usd'].sum()
        dir_winners = len(dir_trades[dir_trades['pnl_usd'] > 0])
        dir_wr = (dir_winners / len(dir_trades) * 100) if len(dir_trades) > 0 else 0
        
        print(f"{direction:25s}: {len(dir_trades):4d} trades | WR: {dir_wr:5.1f}% | P&L: ${dir_pnl:>10,.2f}")
    
    # Análisis de correlación
    print("\n" + "-"*100)
    print("ANÁLISIS DE DIVERSIFICACIÓN")
    print("-"*100)
    
    # Contar trades simultáneos
    combined_sorted = combined.sort_values('entry_time')
    max_simultaneous = 0
    current_open = []
    
    for _, trade in combined_sorted.iterrows():
        # Cerrar trades que ya terminaron
        if 'exit_time' in trade and pd.notna(trade['exit_time']):
            exit_time = pd.to_datetime(trade['exit_time'])
            current_open = [t for t in current_open if pd.to_datetime(t['exit_time']) > trade['entry_time']]
        
        current_open.append(trade)
        max_simultaneous = max(max_simultaneous, len(current_open))
    
    print(f"Máximo trades simultáneos: {max_simultaneous}")
    
    # Días con trades
    trading_days = combined['entry_time'].dt.date.nunique()
    print(f"Días con trades:           {trading_days} de {date_range_days} ({trading_days/date_range_days*100:.1f}%)")
    
    print("="*100)
    
    # Evaluación FTMO
    print("\n" + "="*100)
    print("EVALUACIÓN FTMO")
    print("="*100)
    
    ftmo_pass = True
    
    if max_dd * 100 > 8.0:
        print(f"❌ Max Drawdown: {max_dd * 100:.2f}% (límite: 8%)")
        ftmo_pass = False
    else:
        print(f"✅ Max Drawdown: {max_dd * 100:.2f}% (límite: 8%)")
    
    if trades_per_month < 4.0:
        print(f"⚠️  Frecuencia: {trades_per_month:.1f} trades/mes (recomendado: 4+)")
        print(f"   Considera añadir más instrumentos o estrategias")
    else:
        print(f"✅ Frecuencia: {trades_per_month:.1f} trades/mes (recomendado: 4+)")
    
    if pf < 1.3:
        print(f"⚠️  Profit Factor: {pf:.2f} (recomendado: 1.3+)")
        ftmo_pass = False
    else:
        print(f"✅ Profit Factor: {pf:.2f} (recomendado: 1.3+)")
    
    if retorno_pct < 5.0:
        print(f"⚠️  Retorno: {retorno_pct:.2f}% (objetivo FTMO: 10%)")
    else:
        print(f"✅ Retorno: {retorno_pct:.2f}% (objetivo FTMO: 10%)")
    
    print("\n" + "="*100)
    if ftmo_pass:
        print("🎉 PORTFOLIO APTO PARA FTMO")
    else:
        print("⚠️  PORTFOLIO REQUIERE AJUSTES PARA FTMO")
    print("="*100)
    
    return pd.DataFrame(balance_history)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simular portfolio multi-estrategia")
    parser.add_argument("--strategy", nargs=2, action='append', metavar=('NAME', 'CSV'),
                       help="Estrategia: nombre y path al CSV (puede repetirse)")
    parser.add_argument("--balance", type=float, default=100000,
                       help="Balance inicial (default: 100000)")
    
    args = parser.parse_args()
    
    if not args.strategy:
        print("Error: Debes especificar al menos una estrategia")
        print("\nUso:")
        print("  python3 tools/portfolio_simulator.py \\")
        print("    --strategy sr_swing strategies/sr_swing/data/backtest_US30_v4_longs_only.csv \\")
        print("    --strategy pivot_scalping strategies/pivot_scalping/data/backtest_US30_scalping_60d.csv")
        exit(1)
    
    # Convertir lista de estrategias a dict
    strategy_dict = {name: path for name, path in args.strategy}
    
    # Ejecutar simulación
    balance_history = simulate_portfolio(strategy_dict, args.balance)
    
    if balance_history is not None:
        # Opcional: guardar historial
        output_path = "portfolio_balance_history.csv"
        balance_history.to_csv(output_path, index=False)
        print(f"\n💾 Historial guardado en: {output_path}")
