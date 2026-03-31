# -*- coding: utf-8 -*-
"""
Backtest de la estrategia Order Block en GBPJPY.

MISMA CONFIGURACIÓN que US30:
- LIMIT orders (entry en zone_high/zone_low)
- R:R: 3.5
- Buffer SL: 25 pips (no puntos, ya que GBPJPY usa pips)
- Filtro BOS: DESACTIVADO
- Sesión NY: 13:45-20:00 UTC
- consecutive_candles: 4
- zone_type: half_candle

NOTA: GBPJPY usa pips (0.001), no puntos como US30.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd
from datetime import datetime
from strategies.order_block.backtest.config import DEFAULT_PARAMS
from strategies.order_block.backtest.backtester_limit_orders import OrderBlockBacktesterLimitOrders

def main():
    print("=" * 80)
    print("BACKTEST GBPJPY - ESTRATEGIA ORDER BLOCK LIMIT")
    print("=" * 80)
    print()
    
    # Cargar datos GBPJPY
    print("Cargando datos GBPJPY...")
    try:
        df_m5 = pd.read_csv("data/GBPJPY_M5_260d.csv", parse_dates=["time"])
        print(f"   M5: {len(df_m5)} velas ({df_m5['time'].min()} a {df_m5['time'].max()})")
    except Exception as e:
        print(f"   ERROR cargando M5: {e}")
        return
    
    # Verificar si hay datos M1
    try:
        df_m1 = pd.read_csv("data/GBPJPY_M1_29d.csv", parse_dates=["time"])
        print(f"   M1: {len(df_m1)} velas ({df_m1['time'].min()} a {df_m1['time'].max()})")
        print(f"   ADVERTENCIA: Solo 29 dias de M1 vs 260 dias de M5")
    except Exception as e:
        print(f"   ERROR: No hay datos M1 suficientes para GBPJPY")
        print(f"   Se necesita GBPJPY_M1_260d.csv para backtest completo")
        return
    
    print()
    
    # Configuración adaptada para GBPJPY
    params = DEFAULT_PARAMS.copy()
    
    # GBPJPY usa pips (0.001), no puntos
    # 25 pips = 0.025 en GBPJPY
    params["buffer_points"] = 0.025  # 25 pips
    params["min_risk_points"] = 0.015  # 15 pips
    params["max_risk_points"] = 0.300  # 300 pips
    params["avg_spread_points"] = 0.002  # 2 pips de spread
    params["point_value"] = 1000.0  # GBPJPY: 1 pip = $1000 por lote estándar
    
    print("PARAMETROS GBPJPY:")
    print(f"   Tipo de orden: LIMIT (entry en zone_high/zone_low)")
    print(f"   consecutive_candles: {params['consecutive_candles']}")
    print(f"   zone_type: {params['zone_type']}")
    print(f"   max_atr_mult: {params['max_atr_mult']}")
    print(f"   expiry_candles: {params['expiry_candles']}")
    print(f"   buffer_points: {params['buffer_points']} (25 pips)")
    print(f"   target_rr: {params['target_rr']}")
    print(f"   require_bos: {params['require_bos']}")
    print(f"   Sesion NY: {params['sessions']['new_york']}")
    print()
    print("   NOTA: GBPJPY usa pips (0.001), no puntos")
    print("   Point value: $1000 por pip por lote estandar")
    print()
    
    # Ejecutar backtest
    print("Ejecutando backtest GBPJPY con logica LIMIT...")
    print("ADVERTENCIA: Solo 29 dias de datos M1 disponibles")
    print()
    
    backtester = OrderBlockBacktesterLimitOrders(params)
    df_trades = backtester.run(df_m5, df_m1)
    
    print(f"Backtest completado: {len(df_trades)} trades")
    print()
    
    # Análisis de resultados
    print("=" * 80)
    print("RESULTADOS GENERALES - GBPJPY")
    print("=" * 80)
    
    if len(df_trades) == 0:
        print("No se generaron trades")
        print()
        print("POSIBLES RAZONES:")
        print("  - Datos M1 insuficientes (solo 29 dias)")
        print("  - Sesion NY no tiene suficiente actividad en GBPJPY")
        print("  - Parametros no adaptados para Forex")
        return
    
    # Métricas generales
    initial_balance = params["initial_balance"]
    final_balance = initial_balance + df_trades["pnl_usd"].sum()
    total_return = (final_balance - initial_balance) / initial_balance
    
    winners = df_trades[df_trades["pnl_usd"] > 0]
    losers = df_trades[df_trades["pnl_usd"] <= 0]
    win_rate = len(winners) / len(df_trades) if len(df_trades) > 0 else 0
    
    gross_profit = winners["pnl_usd"].sum() if len(winners) > 0 else 0
    gross_loss = abs(losers["pnl_usd"].sum()) if len(losers) > 0 else 0
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
    
    avg_win = winners["pnl_usd"].mean() if len(winners) > 0 else 0
    avg_loss = losers["pnl_usd"].mean() if len(losers) > 0 else 0
    
    # Max Drawdown
    df_trades["cum_pnl"] = df_trades["pnl_usd"].cumsum()
    df_trades["peak"] = df_trades["cum_pnl"].cummax()
    df_trades["dd"] = df_trades["cum_pnl"] - df_trades["peak"]
    max_dd = df_trades["dd"].min()
    max_dd_pct = (max_dd / initial_balance) * 100
    
    # Duración
    start_date = df_trades["entry_time"].min()
    end_date = df_trades["entry_time"].max()
    duration_days = (end_date - start_date).days
    
    print(f"Balance inicial:    ${initial_balance:,.2f}")
    print(f"Balance final:      ${final_balance:,.2f}")
    print(f"Retorno total:      {total_return:+.2%} (${final_balance - initial_balance:+,.2f})")
    print(f"Max Drawdown:       {max_dd_pct:.2f}% (${max_dd:,.2f})")
    print(f"Duracion:           {duration_days} dias")
    print()
    print(f"Total trades:       {len(df_trades)}")
    print(f"Ganadores:          {len(winners)} ({len(winners)/len(df_trades)*100:.1f}%)")
    print(f"Perdedores:         {len(losers)} ({len(losers)/len(df_trades)*100:.1f}%)")
    print(f"Win Rate:           {win_rate:.1%}")
    print(f"Profit Factor:      {profit_factor:.2f}")
    print()
    print(f"Avg Winner:         ${avg_win:,.2f}")
    print(f"Avg Loser:          ${avg_loss:,.2f}")
    print(f"Expectancy:         ${df_trades['pnl_usd'].mean():,.2f} por trade")
    print(f"Trades/dia:         {len(df_trades) / max(duration_days, 1):.1f}")
    print()
    
    # Por dirección
    print("=" * 80)
    print("RESULTADOS POR DIRECCION")
    print("=" * 80)
    
    df_long = df_trades[df_trades["direction"] == "long"]
    df_short = df_trades[df_trades["direction"] == "short"]
    
    if len(df_long) > 0:
        long_winners = df_long[df_long["pnl_usd"] > 0]
        long_wr = len(long_winners) / len(df_long)
        long_pnl = df_long["pnl_usd"].sum()
        print(f"LONG:")
        print(f"  Trades:     {len(df_long)}")
        print(f"  Win Rate:   {long_wr:.1%}")
        print(f"  PnL:        ${long_pnl:+,.2f}")
        print(f"  Avg R:      {df_long['pnl_r'].mean():.2f}R")
        print()
    
    if len(df_short) > 0:
        short_winners = df_short[df_short["pnl_usd"] > 0]
        short_wr = len(short_winners) / len(df_short)
        short_pnl = df_short["pnl_usd"].sum()
        print(f"SHORT:")
        print(f"  Trades:     {len(df_short)}")
        print(f"  Win Rate:   {short_wr:.1%}")
        print(f"  PnL:        ${short_pnl:+,.2f}")
        print(f"  Avg R:      {df_short['pnl_r'].mean():.2f}R")
        print()
    
    # Guardar resultados
    output_file = "backtest_gbpjpy_limit_results.csv"
    df_trades.to_csv(output_file, index=False)
    print(f"Resultados guardados en: {output_file}")
    print()
    
    # Comparación con US30
    print("=" * 80)
    print("COMPARACION: GBPJPY vs US30")
    print("=" * 80)
    print()
    print(f"                    GBPJPY          US30")
    print(f"Retorno:            {total_return:+.2%}         +30.91%")
    print(f"Max DD:             {max_dd_pct:.2f}%          -8.77%")
    print(f"Win Rate:           {win_rate:.1%}          29.4%")
    print(f"Profit Factor:      {profit_factor:.2f}           1.36")
    print(f"Trades:             {len(df_trades):<4}            197")
    print(f"Trades/dia:         {len(df_trades)/max(duration_days,1):.1f}             1.9")
    print()
    
    # Conclusión
    print("=" * 80)
    print("CONCLUSION")
    print("=" * 80)
    print()
    if len(df_trades) < 50:
        print("ADVERTENCIA: Muestra pequeña (< 50 trades)")
        print("  - Se necesitan mas datos M1 para validacion robusta")
        print("  - Resultados no son estadisticamente significativos")
    else:
        if total_return > 0.20:
            print("EXCELENTE: Estrategia muy rentable en GBPJPY")
        elif total_return > 0.10:
            print("BUENO: Estrategia rentable en GBPJPY")
        elif total_return > 0:
            print("MARGINAL: Estrategia levemente rentable en GBPJPY")
        else:
            print("NO RENTABLE: Estrategia pierde en GBPJPY")
    print()

if __name__ == "__main__":
    main()
