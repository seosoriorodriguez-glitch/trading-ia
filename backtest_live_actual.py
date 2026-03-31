# -*- coding: utf-8 -*-
"""
Backtest con la configuración EXACTA del bot live actual.

CONFIGURACIÓN:
- MARKET orders (entry = candle_close)
- R:R: 3.5
- Buffer SL: 25 puntos
- Filtro BOS: DESACTIVADO
- Sesión NY: 13:45-20:00 UTC (skip_minutes=15)
- consecutive_candles: 4
- zone_type: half_candle
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd
from datetime import datetime
from strategies.order_block.backtest.config import DEFAULT_PARAMS
from strategies.order_block.backtest.backtester import OrderBlockBacktester

def main():
    print("=" * 80)
    print("BACKTEST - CONFIGURACION EXACTA BOT LIVE ACTUAL")
    print("=" * 80)
    print()
    
    # Cargar datos
    print("Cargando datos...")
    df_m5 = pd.read_csv("data/US30_cash_M5_260d.csv", parse_dates=["time"])
    df_m1 = pd.read_csv("data/US30_cash_M1_260d.csv", parse_dates=["time"])
    print(f"   M5: {len(df_m5)} velas ({df_m5['time'].min()} a {df_m5['time'].max()})")
    print(f"   M1: {len(df_m1)} velas ({df_m1['time'].min()} a {df_m1['time'].max()})")
    print()
    
    # Configuración EXACTA del bot live
    params = DEFAULT_PARAMS.copy()
    
    print("PARAMETROS BOT LIVE:")
    print(f"   Tipo de orden: MARKET (entry = candle_close)")
    print(f"   consecutive_candles: {params['consecutive_candles']}")
    print(f"   zone_type: {params['zone_type']}")
    print(f"   max_atr_mult: {params['max_atr_mult']}")
    print(f"   expiry_candles: {params['expiry_candles']}")
    print(f"   buffer_points: {params['buffer_points']}")
    print(f"   target_rr: {params['target_rr']}")
    print(f"   require_bos: {params['require_bos']}")
    print(f"   require_rejection: {params['require_rejection']}")
    print(f"   ema_trend_filter: {params['ema_trend_filter']}")
    print(f"   Sesión NY: {params['sessions']['new_york']}")
    print()
    
    # Ejecutar backtest
    print("Ejecutando backtest...")
    backtester = OrderBlockBacktester(params)
    df_trades = backtester.run(df_m5, df_m1)
    
    print(f"Backtest completado: {len(df_trades)} trades")
    print()
    
    # Análisis de resultados
    print("=" * 80)
    print("RESULTADOS GENERALES")
    print("=" * 80)
    
    if len(df_trades) == 0:
        print("No se generaron trades")
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
    
    print(f"Balance inicial:    ${initial_balance:,.2f}")
    print(f"Balance final:      ${final_balance:,.2f}")
    print(f"Retorno total:      {total_return:+.2%} (${final_balance - initial_balance:+,.2f})")
    print(f"Max Drawdown:       {max_dd_pct:.2f}% (${max_dd:,.2f})")
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
    
    # Por sesión
    print("=" * 80)
    print("RESULTADOS POR SESION")
    print("=" * 80)
    
    for session in df_trades["session"].unique():
        df_sess = df_trades[df_trades["session"] == session]
        sess_winners = df_sess[df_sess["pnl_usd"] > 0]
        sess_wr = len(sess_winners) / len(df_sess) if len(df_sess) > 0 else 0
        sess_pnl = df_sess["pnl_usd"].sum()
        print(f"{session.upper()}:")
        print(f"  Trades:     {len(df_sess)}")
        print(f"  Win Rate:   {sess_wr:.1%}")
        print(f"  PnL:        ${sess_pnl:+,.2f}")
        print()
    
    # Verificar SL/TP
    print("=" * 80)
    print("VERIFICACION SL/TP")
    print("=" * 80)
    
    errors = []
    for idx, trade in df_trades.iterrows():
        entry = trade["entry_price"]
        sl = trade["sl"]
        tp = trade["tp"]
        direction = trade["direction"]
        
        if direction == "long":
            if sl >= entry:
                errors.append(f"Trade {idx}: LONG con SL arriba del entry (SL={sl:.2f}, Entry={entry:.2f})")
            if tp <= entry:
                errors.append(f"Trade {idx}: LONG con TP abajo del entry (TP={tp:.2f}, Entry={entry:.2f})")
        else:  # short
            if sl <= entry:
                errors.append(f"Trade {idx}: SHORT con SL abajo del entry (SL={sl:.2f}, Entry={entry:.2f})")
            if tp >= entry:
                errors.append(f"Trade {idx}: SHORT con TP arriba del entry (TP={tp:.2f}, Entry={entry:.2f})")
    
    if errors:
        print(f"ERRORES DETECTADOS ({len(errors)}):")
        for err in errors[:10]:
            print(f"   {err}")
        if len(errors) > 10:
            print(f"   ... y {len(errors) - 10} mas")
    else:
        print(f"TODOS LOS SL/TP CORRECTOS ({len(df_trades)} trades verificados)")
        print(f"   LONG: SL debajo, TP arriba")
        print(f"   SHORT: SL arriba, TP abajo")
    
    print()
    
    # Guardar resultados
    output_file = "backtest_live_actual_results.csv"
    df_trades.to_csv(output_file, index=False)
    print(f"Resultados guardados en: {output_file}")
    print()
    
    # Exportar últimas 10 ganadoras y 5 perdedoras
    print("=" * 80)
    print("EXPORTANDO TRADES PARA VALIDACION")
    print("=" * 80)
    
    # Últimas 10 ganadoras
    last_10_winners = winners.tail(10).copy()
    last_10_winners["entry_time_chile"] = pd.to_datetime(last_10_winners["entry_time"]).dt.tz_localize("UTC").dt.tz_convert("America/Santiago")
    
    winners_table = last_10_winners[[
        "entry_time_chile", "direction", "entry_price", "sl", "tp", 
        "exit_price", "pnl_usd", "pnl_r"
    ]].copy()
    winners_table.columns = ["Fecha (Chile)", "Dir", "Entry", "SL", "TP", "Exit", "PnL USD", "PnL R"]
    winners_table.to_csv("live_ultimas_10_ganadoras.csv", index=False)
    
    print("\nULTIMAS 10 GANADORAS:")
    print(winners_table.to_string(index=False))
    print()
    
    # Últimas 5 perdedoras
    if len(losers) >= 5:
        last_5_losers = losers.tail(5).copy()
        last_5_losers["entry_time_chile"] = pd.to_datetime(last_5_losers["entry_time"]).dt.tz_localize("UTC").dt.tz_convert("America/Santiago")
        
        losers_table = last_5_losers[[
            "entry_time_chile", "direction", "entry_price", "sl", "tp", 
            "exit_price", "pnl_usd", "pnl_r"
        ]].copy()
        losers_table.columns = ["Fecha (Chile)", "Dir", "Entry", "SL", "TP", "Exit", "PnL USD", "PnL R"]
        losers_table.to_csv("live_ultimas_5_perdedoras.csv", index=False)
        
        print("ULTIMAS 5 PERDEDORAS:")
        print(losers_table.to_string(index=False))
        print()
    
    print("=" * 80)
    print("ANALISIS COMPLETO")
    print("=" * 80)

if __name__ == "__main__":
    main()
