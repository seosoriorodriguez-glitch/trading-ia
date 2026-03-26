#!/usr/bin/env python3
"""
Compara resultados de backtest entre diferentes estrategias

Uso:
    python3 tools/compare_strategies.py \
        strategies/sr_swing/data/backtest_US30_v4_longs_only.csv \
        strategies/pivot_scalping/data/backtest_US30_scalping_60d.csv
"""

import pandas as pd
import sys
from pathlib import Path
from typing import List, Dict


def calculate_metrics(df: pd.DataFrame, strategy_name: str, period_days: int = None) -> Dict:
    """
    Calcula métricas de un backtest
    
    Args:
        df: DataFrame con resultados del backtest
        strategy_name: Nombre de la estrategia
        period_days: Duración del período en días (opcional)
    
    Returns:
        Dict con métricas calculadas
    """
    if len(df) == 0:
        return {
            'Estrategia': strategy_name,
            'Trades': 0,
            'Win Rate': '0.0%',
            'PF': '0.00',
            'Retorno': '0.00%',
            'Max DD': '0.00%',
            'Trades/Mes': '0.0',
            'Mejor Trade': '$0.00',
            'Peor Trade': '$0.00'
        }
    
    balance_inicial = 100000
    total_pnl_usd = df['pnl_usd'].sum()
    retorno_pct = (total_pnl_usd / balance_inicial) * 100
    
    winners = len(df[df['pnl_usd'] > 0])
    win_rate = (winners / len(df) * 100) if len(df) > 0 else 0
    
    gross_profit = df[df['pnl_usd'] > 0]['pnl_usd'].sum()
    gross_loss = abs(df[df['pnl_usd'] < 0]['pnl_usd'].sum())
    pf = gross_profit / gross_loss if gross_loss > 0 else float('inf')
    
    # Max Drawdown
    df_sorted = df.sort_values('entry_time')
    balance = balance_inicial
    peak = balance_inicial
    max_dd = 0
    
    for _, trade in df_sorted.iterrows():
        balance += trade['pnl_usd']
        peak = max(peak, balance)
        dd = (peak - balance) / peak if peak > 0 else 0
        max_dd = max(max_dd, dd)
    
    # Frecuencia
    if period_days:
        trades_per_month = len(df) / (period_days / 30)
    else:
        # Estimar del rango de fechas
        df_sorted['entry_time'] = pd.to_datetime(df_sorted['entry_time'])
        date_range = (df_sorted['entry_time'].max() - df_sorted['entry_time'].min()).days
        trades_per_month = len(df) / (date_range / 30) if date_range > 0 else 0
    
    return {
        'Estrategia': strategy_name,
        'Trades': len(df),
        'Win Rate': f"{win_rate:.1f}%",
        'PF': f"{pf:.2f}",
        'Retorno': f"{retorno_pct:+.2f}%",
        'Max DD': f"{max_dd * 100:.2f}%",
        'Trades/Mes': f"{trades_per_month:.1f}",
        'Mejor Trade': f"${df['pnl_usd'].max():.2f}",
        'Peor Trade': f"${df['pnl_usd'].min():.2f}"
    }


def compare_strategies(strategy_paths: List[str]):
    """
    Compara métricas de múltiples estrategias
    
    Args:
        strategy_paths: Lista de paths a CSVs de backtest
    """
    results = []
    
    for path in strategy_paths:
        path_obj = Path(path)
        
        if not path_obj.exists():
            print(f"⚠️  Archivo no encontrado: {path}")
            continue
        
        try:
            df = pd.read_csv(path)
            
            # Extraer nombre de estrategia del path
            strategy_name = path_obj.parent.parent.name
            
            # Calcular métricas
            metrics = calculate_metrics(df, strategy_name)
            results.append(metrics)
            
        except Exception as e:
            print(f"❌ Error procesando {path}: {e}")
            continue
    
    if not results:
        print("❌ No se pudieron procesar archivos")
        return
    
    # Mostrar tabla comparativa
    df_results = pd.DataFrame(results)
    
    print("\n" + "="*100)
    print("COMPARATIVA DE ESTRATEGIAS")
    print("="*100)
    print(df_results.to_string(index=False))
    print("="*100)
    
    # Rankings
    print("\n🏆 RANKING POR PROFIT FACTOR:")
    sorted_by_pf = sorted(results, key=lambda x: float(x['PF']) if x['PF'] != 'inf' else 999, reverse=True)
    for i, r in enumerate(sorted_by_pf, 1):
        emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "  "
        print(f"{emoji} {i}. {r['Estrategia']:25s} - PF: {r['PF']:>6s} | WR: {r['Win Rate']:>6s} | Retorno: {r['Retorno']:>8s}")
    
    print("\n📊 RANKING POR RETORNO:")
    sorted_by_return = sorted(results, key=lambda x: float(x['Retorno'].replace('%', '').replace('+', '')), reverse=True)
    for i, r in enumerate(sorted_by_return, 1):
        emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "  "
        print(f"{emoji} {i}. {r['Estrategia']:25s} - Retorno: {r['Retorno']:>8s} | Trades: {r['Trades']:>3d}")
    
    print("\n⚡ RANKING POR FRECUENCIA:")
    sorted_by_freq = sorted(results, key=lambda x: float(x['Trades/Mes']), reverse=True)
    for i, r in enumerate(sorted_by_freq, 1):
        emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "  "
        print(f"{emoji} {i}. {r['Estrategia']:25s} - {r['Trades/Mes']:>5s} trades/mes | Total: {r['Trades']:>3d}")
    
    # Recomendación
    print("\n" + "="*100)
    print("💡 RECOMENDACIÓN")
    print("="*100)
    
    best_pf = sorted_by_pf[0]
    best_return = sorted_by_return[0]
    best_freq = sorted_by_freq[0]
    
    if best_pf['Estrategia'] == best_return['Estrategia']:
        print(f"✅ {best_pf['Estrategia']} es la MEJOR estrategia (mejor PF y retorno)")
    else:
        print(f"⚖️  Trade-off: {best_pf['Estrategia']} tiene mejor PF ({best_pf['PF']}), pero {best_return['Estrategia']} tiene mejor retorno ({best_return['Retorno']})")
    
    if float(best_freq['Trades/Mes']) < 4.0:
        print(f"⚠️  Frecuencia baja: {best_freq['Estrategia']} solo genera {best_freq['Trades/Mes']} trades/mes (FTMO requiere ~4)")
        print(f"   Considera combinar múltiples estrategias o añadir más instrumentos")
    
    print("="*100)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python3 tools/compare_strategies.py <path1.csv> <path2.csv> [path3.csv ...]")
        print("\nEjemplo:")
        print("  python3 tools/compare_strategies.py \\")
        print("    strategies/sr_swing/data/backtest_US30_v4_longs_only.csv \\")
        print("    strategies/pivot_scalping/data/backtest_US30_scalping_60d.csv")
        sys.exit(1)
    
    compare_strategies(sys.argv[1:])
