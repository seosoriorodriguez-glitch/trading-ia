# -*- coding: utf-8 -*-
"""
Backtest NAS100 24h - Sin filtro de sesion.

CONFIGURACION:
- LIMIT orders (entry en zone_high/zone_low)
- R:R: 3.5
- Buffer SL: 25 puntos
- Filtro BOS: DESACTIVADO
- Sesion: 24h (sin filtro)
- consecutive_candles: 4
- zone_type: half_candle

DATOS: Alinear M5 y M1 disponibles.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd
from datetime import datetime, timedelta
from strategies.order_block.backtest.config import DEFAULT_PARAMS
from strategies.order_block.backtest.backtester_limit_orders import OrderBlockBacktesterLimitOrders

def main():
    print("=" * 80)
    print("BACKTEST NAS100 24H - ESTRATEGIA ORDER BLOCK LIMIT")
    print("=" * 80)
    print()
    
    # Cargar datos
    print("Cargando datos NAS100...")
    df_m5 = pd.read_csv("data/NAS100_M5_260d.csv", parse_dates=["time"])
    df_m1 = pd.read_csv("data/NAS100_M1_30d.csv", parse_dates=["time"])
    
    print(f"   M5 original: {len(df_m5)} velas ({df_m5['time'].min()} a {df_m5['time'].max()})")
    print(f"   M1 original: {len(df_m1)} velas ({df_m1['time'].min()} a {df_m1['time'].max()})")
    print()
    
    # Alinear M5 con el rango de M1
    m1_start = df_m1["time"].min()
    m1_end = df_m1["time"].max()
    
    # Filtrar M5 para que coincida con M1 (con margen para deteccion de OB)
    m5_start = m1_start - timedelta(days=7)
    df_m5_filtered = df_m5[(df_m5["time"] >= m5_start) & (df_m5["time"] <= m1_end)].copy()
    
    print("Datos alineados:")
    print(f"   M5: {len(df_m5_filtered)} velas ({df_m5_filtered['time'].min()} a {df_m5_filtered['time'].max()})")
    print(f"   M1: {len(df_m1)} velas ({df_m1['time'].min()} a {df_m1['time'].max()})")
    print()
    
    # Configuracion para NAS100 24h
    params = DEFAULT_PARAMS.copy()
    
    # NAS100 usa puntos (igual que US30)
    params["buffer_points"] = 25  # 25 puntos
    params["min_risk_points"] = 15
    params["max_risk_points"] = 300
    params["avg_spread_points"] = 2
    params["point_value"] = 1.0  # NAS100: $1 por punto
    
    # DESACTIVAR filtro de sesion (24h trading)
    params["sessions"] = {
        "full_day": {
            "start": "00:00",
            "end": "23:59",
            "skip_minutes": 0
        }
    }
    
    print("PARAMETROS NAS100 24H:")
    print(f"   Tipo de orden: LIMIT (entry en zone_high/zone_low)")
    print(f"   consecutive_candles: {params['consecutive_candles']}")
    print(f"   zone_type: {params['zone_type']}")
    print(f"   max_atr_mult: {params['max_atr_mult']}")
    print(f"   buffer_points: {params['buffer_points']} puntos")
    print(f"   target_rr: {params['target_rr']}")
    print(f"   require_bos: {params['require_bos']}")
    print(f"   Sesion: 24H (sin filtro)")
    print()
    
    # Ejecutar backtest
    print("Ejecutando backtest NAS100 24H...")
    print()
    
    backtester = OrderBlockBacktesterLimitOrders(params)
    df_trades = backtester.run(df_m5_filtered, df_m1)
    
    print(f"Backtest completado: {len(df_trades)} trades")
    print()
    
    if len(df_trades) == 0:
        print("No se generaron trades")
        return
    
    # Analisis de resultados
    print("=" * 80)
    print("RESULTADOS GENERALES - NAS100 24H")
    print("=" * 80)
    
    initial_balance = params["initial_balance"]
    final_balance = initial_balance + df_trades["pnl_usd"].sum()
    total_return = (final_balance - initial_balance) / initial_balance
    
    winners = df_trades[df_trades["pnl_usd"] > 0]
    losers = df_trades[df_trades["pnl_usd"] <= 0]
    win_rate = len(winners) / len(df_trades)
    
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
    
    # Duracion
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
    
    # Por direccion
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
    
    # Comparacion con US30 NY
    print("=" * 80)
    print("COMPARACION: NAS100 24H vs US30 NY")
    print("=" * 80)
    print()
    print(f"                    NAS100 24H      US30 NY")
    print(f"Retorno:            {total_return:+.2%}         +30.91%")
    print(f"Max DD:             {max_dd_pct:.2f}%          -8.77%")
    print(f"Win Rate:           {win_rate:.1%}          29.4%")
    print(f"Profit Factor:      {profit_factor:.2f}           1.36")
    print(f"Trades:             {len(df_trades):<4}            197")
    print(f"Trades/dia:         {len(df_trades)/max(duration_days,1):.1f}             1.9")
    print(f"Duracion:           {duration_days} dias        104 dias")
    print()
    
    # Guardar resultados
    output_file = "backtest_nas100_24h_results.csv"
    df_trades.to_csv(output_file, index=False)
    print(f"Resultados guardados en: {output_file}")
    print()
    
    # Ultimas 15 operaciones
    print("=" * 80)
    print("ULTIMAS 15 OPERACIONES (mas recientes)")
    print("=" * 80)
    print()
    
    df_last15 = df_trades.sort_values("entry_time", ascending=False).head(15)
    
    for idx, trade in df_last15.iterrows():
        resultado = "WIN" if trade["pnl_usd"] > 0 else "LOSS"
        print(f"{trade['entry_time']} | {trade['direction'].upper():5} | {resultado:4} | "
              f"Entry: {trade['entry_price']:.2f} | SL: {trade['sl']:.2f} | TP: {trade['tp']:.2f} | "
              f"PnL: ${trade['pnl_usd']:+,.2f} ({trade['pnl_r']:+.2f}R)")
    
    print()
    
    # Exportar ultimas 15 para Pine Script
    df_last15_sorted = df_trades.sort_values("entry_time", ascending=False).head(15)
    df_last15_sorted.to_csv("nas100_ultimas_15_trades.csv", index=False)
    print("Ultimas 15 operaciones guardadas en: nas100_ultimas_15_trades.csv")
    print()
    
    # Estadisticas por hora
    df_trades["hour"] = pd.to_datetime(df_trades["entry_time"]).dt.hour
    trades_by_hour = df_trades.groupby("hour").size().sort_values(ascending=False)
    
    print("=" * 80)
    print("DISTRIBUCION POR HORA UTC (Top 10)")
    print("=" * 80)
    print()
    for hour, count in trades_by_hour.head(10).items():
        pct = count / len(df_trades) * 100
        print(f"  {hour:02d}:00 UTC - {count:3} trades ({pct:5.1f}%)")
    print()
    
    # Conclusion
    print("=" * 80)
    print("CONCLUSION")
    print("=" * 80)
    print()
    
    if total_return > 0.20:
        print("EXCELENTE: Estrategia muy rentable en NAS100 24h")
    elif total_return > 0.10:
        print("BUENO: Estrategia rentable en NAS100 24h")
    elif total_return > 0:
        print("MARGINAL: Estrategia levemente rentable en NAS100 24h")
    else:
        print("NO RENTABLE: Estrategia pierde en NAS100 24h")
    
    print()
    print(f"Retorno:        {total_return:+.2%} (vs +30.91% en US30 NY)")
    print(f"Max DD:         {max_dd_pct:.2f}% (vs -8.77% en US30 NY)")
    print(f"Profit Factor:  {profit_factor:.2f} (vs 1.36 en US30 NY)")
    print()

if __name__ == "__main__":
    main()
