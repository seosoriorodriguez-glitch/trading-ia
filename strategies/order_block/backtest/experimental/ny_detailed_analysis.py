# -*- coding: utf-8 -*-
"""
ANÁLISIS DETALLADO: SOLO NEW YORK
Objetivo: Analizar en profundidad la rentabilidad de operar solo NY
"""
import sys
import codecs
if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

import copy
from pathlib import Path
import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from strategies.order_block.backtest.config import DEFAULT_PARAMS
from strategies.order_block.backtest.data_loader import load_csv
from strategies.order_block.backtest.backtester import OrderBlockBacktester

_ROOT   = Path(__file__).parent.parent.parent.parent.parent
M5_FILE = str(_ROOT / "data/US30_cash_M5_260d.csv")
M1_FILE = str(_ROOT / "data/US30_cash_M1_260d.csv")


if __name__ == "__main__":
    print("\n" + "="*80)
    print("  ANÁLISIS DETALLADO: SOLO NEW YORK")
    print("  Configuración actual del bot live")
    print("="*80)
    
    print("\nCargando datos...")
    df_m5 = load_csv(M5_FILE)
    df_m1 = load_csv(M1_FILE)
    start = max(df_m5["time"].iloc[0], df_m1["time"].iloc[0])
    end   = min(df_m5["time"].iloc[-1], df_m1["time"].iloc[-1])
    df_m5 = df_m5[(df_m5["time"] >= start) & (df_m5["time"] <= end)].reset_index(drop=True)
    df_m1 = df_m1[(df_m1["time"] >= start) & (df_m1["time"] <= end)].reset_index(drop=True)
    print(f"  Período: {start} -> {end}")
    print(f"  M5: {len(df_m5):,} velas | M1: {len(df_m1):,} velas")
    
    # Configuración actual (solo NY)
    params = copy.deepcopy(DEFAULT_PARAMS)
    params["sessions"] = {"new_york": {"start": "13:30", "end": "20:00", "skip_minutes": 15}}
    
    print("\n" + "="*80)
    print("  EJECUTANDO BACKTEST...")
    print("="*80)
    
    bt = OrderBlockBacktester(params)
    df_trades = bt.run(df_m5, df_m1)
    
    if df_trades.empty:
        print("\n❌ No se generaron trades")
        sys.exit(1)
    
    # Métricas generales
    balance_inicial = params["initial_balance"]
    balance_final = df_trades["balance"].iloc[-1]
    retorno = (balance_final - balance_inicial) / balance_inicial * 100
    
    winners = df_trades[df_trades["pnl_usd"] > 0]
    losers = df_trades[df_trades["pnl_usd"] < 0]
    wr = len(winners) / len(df_trades) * 100
    
    avg_win = winners["pnl_usd"].mean() if len(winners) > 0 else 0
    avg_loss = losers["pnl_usd"].mean() if len(losers) > 0 else 0
    
    gross_profit = winners["pnl_usd"].sum() if len(winners) > 0 else 0
    gross_loss = abs(losers["pnl_usd"].sum()) if len(losers) > 0 else 0
    pf = gross_profit / gross_loss if gross_loss > 0 else float('inf')
    
    # Max drawdown
    peak = balance_inicial
    max_dd = 0
    max_dd_pct = 0
    for balance in df_trades["balance"]:
        if balance > peak:
            peak = balance
        dd = peak - balance
        dd_pct = (dd / peak) * 100
        if dd_pct > max_dd_pct:
            max_dd_pct = dd_pct
            max_dd = dd
    
    # Días de trading
    dias = (df_trades["entry_time"].iloc[-1] - df_trades["entry_time"].iloc[0]).days
    
    # Por dirección
    longs = df_trades[df_trades["direction"] == "long"]
    shorts = df_trades[df_trades["direction"] == "short"]
    
    print("\n" + "="*80)
    print("  RESULTADOS GENERALES")
    print("="*80)
    
    print(f"\n💰 RENTABILIDAD:")
    print(f"  Balance inicial:  ${balance_inicial:,.2f}")
    print(f"  Balance final:    ${balance_final:,.2f}")
    print(f"  PnL neto:         ${balance_final - balance_inicial:+,.2f}")
    print(f"  Retorno:          {retorno:+.2f}%")
    
    print(f"\n📊 TRADES:")
    print(f"  Total:            {len(df_trades)}")
    print(f"  Winners:          {len(winners)} ({wr:.1f}%)")
    print(f"  Losers:           {len(losers)} ({100-wr:.1f}%)")
    print(f"  Trades/día:       {len(df_trades)/dias:.2f}")
    print(f"  Período:          {dias} días")
    
    print(f"\n💵 PROMEDIO POR TRADE:")
    print(f"  Avg Win:          ${avg_win:,.2f}")
    print(f"  Avg Loss:         ${avg_loss:,.2f}")
    print(f"  Win/Loss ratio:   {abs(avg_win/avg_loss):.2f}" if avg_loss != 0 else "  Win/Loss ratio:   N/A")
    print(f"  Expectativa:      ${(gross_profit - gross_loss) / len(df_trades):,.2f} por trade")
    
    print(f"\n📈 MÉTRICAS CLAVE:")
    print(f"  Profit Factor:    {pf:.2f}")
    print(f"  Max Drawdown:     ${max_dd:,.2f} ({max_dd_pct:.2f}%)")
    print(f"  Gross Profit:     ${gross_profit:,.2f}")
    print(f"  Gross Loss:       ${gross_loss:,.2f}")
    
    print(f"\n🎯 POR DIRECCIÓN:")
    if len(longs) > 0:
        long_wr = len(longs[longs["pnl_usd"] > 0]) / len(longs) * 100
        long_pnl = longs["pnl_usd"].sum()
        long_avg = longs["pnl_usd"].mean()
        print(f"  LONG:  {len(longs)} trades, WR {long_wr:.1f}%, PnL ${long_pnl:+,.2f}, Avg ${long_avg:+,.2f}")
    
    if len(shorts) > 0:
        short_wr = len(shorts[shorts["pnl_usd"] > 0]) / len(shorts) * 100
        short_pnl = shorts["pnl_usd"].sum()
        short_avg = shorts["pnl_usd"].mean()
        print(f"  SHORT: {len(shorts)} trades, WR {short_wr:.1f}%, PnL ${short_pnl:+,.2f}, Avg ${short_avg:+,.2f}")
    
    # Análisis de rachas
    print("\n" + "="*80)
    print("  ANÁLISIS DE RACHAS")
    print("="*80)
    
    current_streak = 0
    max_win_streak = 0
    max_loss_streak = 0
    
    for pnl in df_trades["pnl_usd"]:
        if pnl > 0:
            if current_streak >= 0:
                current_streak += 1
            else:
                current_streak = 1
            max_win_streak = max(max_win_streak, current_streak)
        else:
            if current_streak <= 0:
                current_streak -= 1
            else:
                current_streak = -1
            max_loss_streak = max(max_loss_streak, abs(current_streak))
    
    print(f"\n  Max racha ganadora:  {max_win_streak} trades consecutivos")
    print(f"  Max racha perdedora: {max_loss_streak} trades consecutivos")
    
    # Análisis mensual
    print("\n" + "="*80)
    print("  ANÁLISIS MENSUAL")
    print("="*80)
    
    df_trades["month"] = pd.to_datetime(df_trades["entry_time"]).dt.to_period("M")
    monthly = df_trades.groupby("month").agg({
        "pnl_usd": ["sum", "count"],
    })
    
    print(f"\n{'Mes':<12} {'Trades':<10} {'PnL':<15} {'Retorno':<12}")
    print("-" * 50)
    
    cumulative_balance = balance_inicial
    for month, row in monthly.iterrows():
        month_pnl = row[("pnl_usd", "sum")]
        month_trades = int(row[("pnl_usd", "count")])
        month_return = (month_pnl / cumulative_balance) * 100
        cumulative_balance += month_pnl
        print(f"{str(month):<12} {month_trades:<10} ${month_pnl:>12,.2f} {month_return:>10.2f}%")
    
    # Distribución de R-multiples
    print("\n" + "="*80)
    print("  DISTRIBUCIÓN DE R-MULTIPLES")
    print("="*80)
    
    if 'pnl_r' in df_trades.columns:
        r_bins = [-float('inf'), -2, -1, 0, 1, 2, 3, float('inf')]
        r_labels = ['< -2R', '-2R a -1R', '-1R a 0R', '0R a 1R', '1R a 2R', '2R a 3R', '> 3R']
        
        df_trades['r_bin'] = pd.cut(df_trades['pnl_r'], bins=r_bins, labels=r_labels)
        r_dist = df_trades.groupby('r_bin', observed=True).size()
        
        print(f"\n{'R-Multiple':<15} {'Trades':<10} {'%':<10}")
        print("-" * 35)
        for r_label in r_labels:
            if r_label in r_dist.index:
                count = r_dist[r_label]
                pct = (count / len(df_trades)) * 100
                print(f"{r_label:<15} {count:<10} {pct:.1f}%")
    else:
        print("\n  ⚠️  Columna 'pnl_r' no disponible en resultados")
    
    # Mejor y peor trade
    print("\n" + "="*80)
    print("  MEJORES Y PEORES TRADES")
    print("="*80)
    
    best_trade = df_trades.loc[df_trades["pnl_usd"].idxmax()]
    worst_trade = df_trades.loc[df_trades["pnl_usd"].idxmin()]
    
    print(f"\n🏆 MEJOR TRADE:")
    print(f"  Fecha:      {best_trade['entry_time']}")
    print(f"  Dirección:  {best_trade['direction'].upper()}")
    print(f"  Entry:      {best_trade['entry_price']:.2f}")
    print(f"  Exit:       {best_trade['exit_price']:.2f}")
    print(f"  PnL:        ${best_trade['pnl_usd']:,.2f}")
    if 'pnl_r' in df_trades.columns:
        print(f"  R-multiple: {best_trade['pnl_r']:.2f}R")
    
    print(f"\n💀 PEOR TRADE:")
    print(f"  Fecha:      {worst_trade['entry_time']}")
    print(f"  Dirección:  {worst_trade['direction'].upper()}")
    print(f"  Entry:      {worst_trade['entry_price']:.2f}")
    print(f"  Exit:       {worst_trade['exit_price']:.2f}")
    print(f"  PnL:        ${worst_trade['pnl_usd']:,.2f}")
    if 'pnl_r' in df_trades.columns:
        print(f"  R-multiple: {worst_trade['pnl_r']:.2f}R")
    
    # Últimos 20 trades
    print("\n" + "="*80)
    print("  ÚLTIMOS 20 TRADES")
    print("="*80)
    
    if 'pnl_r' in df_trades.columns:
        print(f"\n{'Fecha':<20} {'Dir':<6} {'Entry':<10} {'Exit':<10} {'PnL':<12} {'R':<8} {'Balance':<12}")
        print("-" * 80)
        
        for idx, trade in df_trades.tail(20).iterrows():
            direction = trade["direction"].upper()[:5]
            print(f"{str(trade['entry_time']):<20} {direction:<6} {trade['entry_price']:<10.2f} "
                  f"{trade['exit_price']:<10.2f} ${trade['pnl_usd']:>10,.2f} {trade['pnl_r']:>6.2f}R "
                  f"${trade['balance']:>10,.2f}")
    else:
        print(f"\n{'Fecha':<20} {'Dir':<6} {'Entry':<10} {'Exit':<10} {'PnL':<12} {'Balance':<12}")
        print("-" * 75)
        
        for idx, trade in df_trades.tail(20).iterrows():
            direction = trade["direction"].upper()[:5]
            print(f"{str(trade['entry_time']):<20} {direction:<6} {trade['entry_price']:<10.2f} "
                  f"{trade['exit_price']:<10.2f} ${trade['pnl_usd']:>10,.2f} "
                  f"${trade['balance']:>10,.2f}")
    
    print("\n" + "="*80)
    print("  CONCLUSIÓN")
    print("="*80)
    
    print(f"\n✅ ESTRATEGIA SOLO NY:")
    print(f"  • Rentabilidad: {retorno:+.2f}% en {dias} días")
    print(f"  • Win Rate: {wr:.1f}% (objetivo: > 40%)")
    print(f"  • Profit Factor: {pf:.2f} (objetivo: > 1.5)")
    print(f"  • Max DD: {max_dd_pct:.2f}% (límite FTMO: 10%)")
    print(f"  • Trades/día: {len(df_trades)/dias:.2f}")
    
    if wr >= 40 and pf >= 1.5 and max_dd_pct < 10:
        print(f"\n🎯 VEREDICTO: ESTRATEGIA SÓLIDA Y CONSISTENTE ✅")
    elif wr >= 35 and pf >= 1.3:
        print(f"\n⚠️  VEREDICTO: ESTRATEGIA VIABLE PERO MEJORABLE")
    else:
        print(f"\n❌ VEREDICTO: ESTRATEGIA REQUIERE OPTIMIZACIÓN")
    
    print("\n" + "="*80)
