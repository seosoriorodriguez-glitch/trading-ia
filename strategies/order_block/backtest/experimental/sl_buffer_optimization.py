# -*- coding: utf-8 -*-
"""
OPTIMIZACIÓN DE BUFFER SL
Compara diferentes valores de buffer_points: 20, 25, 30, 35, 40
para encontrar el valor óptimo
"""
import sys
import codecs
if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

import copy
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from strategies.order_block.backtest.config import DEFAULT_PARAMS
from strategies.order_block.backtest.data_loader import load_csv
from strategies.order_block.backtest.backtester import OrderBlockBacktester

_ROOT   = Path(__file__).parent.parent.parent.parent.parent
M5_FILE = str(_ROOT / "data/US30_cash_M5_260d.csv")
M1_FILE = str(_ROOT / "data/US30_cash_M1_260d.csv")


def run_backtest(df_m5, df_m1, buffer_points: int, label: str):
    """Ejecuta backtest con un valor específico de buffer_points"""
    params = copy.deepcopy(DEFAULT_PARAMS)
    params["sessions"] = {"new_york": {"start": "13:30", "end": "20:00", "skip_minutes": 15}}
    params["buffer_points"] = buffer_points
    
    bt = OrderBlockBacktester(params)
    df_trades = bt.run(df_m5, df_m1)
    
    if df_trades.empty:
        print(f"\n{label}: ❌ 0 trades")
        return None
    
    # Métricas
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
    max_dd_pct = 0
    for balance in df_trades["balance"]:
        if balance > peak:
            peak = balance
        dd_pct = ((peak - balance) / peak) * 100
        if dd_pct > max_dd_pct:
            max_dd_pct = dd_pct
    
    # Días
    dias = (df_trades["entry_time"].iloc[-1] - df_trades["entry_time"].iloc[0]).days
    
    # Por dirección
    longs = df_trades[df_trades["direction"] == "long"]
    shorts = df_trades[df_trades["direction"] == "short"]
    
    print(f"\n{label}")
    print(f"  📊 Trades:        {len(df_trades)} ({len(df_trades)/dias:.2f}/día)")
    print(f"  🎯 Win Rate:      {wr:.1f}%")
    print(f"  💰 Retorno:       {retorno:+.2f}%")
    print(f"  📉 Max DD:        {max_dd_pct:.2f}%")
    print(f"  📈 Profit Factor: {pf:.2f}")
    print(f"  💵 Avg Win:       ${avg_win:,.2f}")
    print(f"  💸 Avg Loss:      ${avg_loss:,.2f}")
    print(f"  📊 Win/Loss:      {abs(avg_win/avg_loss):.2f}" if avg_loss != 0 else "  📊 Win/Loss:      N/A")
    
    if len(longs) > 0:
        long_wr = (longs['pnl_usd']>0).mean()*100
        long_pnl = longs["pnl_usd"].sum()
        print(f"  🟢 Long:  {len(longs)} trades, WR {long_wr:.0f}%, PnL ${long_pnl:+,.0f}")
    
    if len(shorts) > 0:
        short_wr = (shorts['pnl_usd']>0).mean()*100
        short_pnl = shorts["pnl_usd"].sum()
        print(f"  🔴 Short: {len(shorts)} trades, WR {short_wr:.0f}%, PnL ${short_pnl:+,.0f}")
    
    return {
        "buffer": buffer_points,
        "trades": len(df_trades),
        "wr": wr,
        "return": retorno,
        "max_dd": max_dd_pct,
        "pf": pf,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "win_loss_ratio": abs(avg_win/avg_loss) if avg_loss != 0 else 0,
        "trades_per_day": len(df_trades)/dias,
        "gross_profit": gross_profit,
        "gross_loss": gross_loss,
        "balance_final": balance_final
    }


if __name__ == "__main__":
    print("\n" + "="*80)
    print("  OPTIMIZACIÓN DE BUFFER SL")
    print("  Comparando: 20, 25, 30, 35, 40 puntos")
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
    
    print("\n" + "="*80)
    print("  EJECUTANDO BACKTESTS...")
    print("="*80)
    
    # Probar diferentes valores de buffer
    buffers = [20, 25, 30, 35, 40]
    results = []
    
    for buffer in buffers:
        result = run_backtest(
            df_m5, df_m1, 
            buffer, 
            f"Buffer SL: {buffer} puntos" + (" (ACTUAL)" if buffer == 20 else "")
        )
        if result:
            results.append(result)
    
    if not results:
        print("\n❌ No se generaron resultados")
        sys.exit(1)
    
    # Tabla comparativa
    print("\n" + "="*80)
    print("  TABLA COMPARATIVA")
    print("="*80)
    
    print(f"\n{'Buffer':<10} {'Trades':<10} {'WR':<10} {'Retorno':<12} {'Max DD':<10} {'PF':<8} {'W/L':<8}")
    print("-" * 80)
    
    for r in results:
        marker = " ← ACTUAL" if r["buffer"] == 20 else ""
        print(f"{r['buffer']:<10} {r['trades']:<10} {r['wr']:<10.1f} {r['return']:+<12.2f} "
              f"{r['max_dd']:<10.2f} {r['pf']:<8.2f} {r['win_loss_ratio']:<8.2f}{marker}")
    
    # Análisis
    print("\n" + "="*80)
    print("  ANÁLISIS")
    print("="*80)
    
    # Mejor retorno
    best_return = max(results, key=lambda x: x["return"])
    print(f"\n🏆 MEJOR RETORNO:")
    print(f"   Buffer: {best_return['buffer']} puntos")
    print(f"   Retorno: {best_return['return']:+.2f}%")
    print(f"   Win Rate: {best_return['wr']:.1f}%")
    print(f"   Profit Factor: {best_return['pf']:.2f}")
    
    # Mejor Win Rate
    best_wr = max(results, key=lambda x: x["wr"])
    print(f"\n🎯 MEJOR WIN RATE:")
    print(f"   Buffer: {best_wr['buffer']} puntos")
    print(f"   Win Rate: {best_wr['wr']:.1f}%")
    print(f"   Retorno: {best_wr['return']:+.2f}%")
    
    # Mejor Profit Factor
    best_pf = max(results, key=lambda x: x["pf"])
    print(f"\n📈 MEJOR PROFIT FACTOR:")
    print(f"   Buffer: {best_pf['buffer']} puntos")
    print(f"   Profit Factor: {best_pf['pf']:.2f}")
    print(f"   Retorno: {best_pf['return']:+.2f}%")
    
    # Menor Drawdown
    best_dd = min(results, key=lambda x: x["max_dd"])
    print(f"\n🛡️  MENOR DRAWDOWN:")
    print(f"   Buffer: {best_dd['buffer']} puntos")
    print(f"   Max DD: {best_dd['max_dd']:.2f}%")
    print(f"   Retorno: {best_dd['return']:+.2f}%")
    
    # Mejor ratio Retorno/DD
    for r in results:
        r["return_dd_ratio"] = r["return"] / r["max_dd"] if r["max_dd"] > 0 else 0
    
    best_ratio = max(results, key=lambda x: x["return_dd_ratio"])
    print(f"\n⚖️  MEJOR RATIO RETORNO/DD:")
    print(f"   Buffer: {best_ratio['buffer']} puntos")
    print(f"   Ratio: {best_ratio['return_dd_ratio']:.2f}")
    print(f"   Retorno: {best_ratio['return']:+.2f}%")
    print(f"   Max DD: {best_ratio['max_dd']:.2f}%")
    
    # Gráfico de tendencias
    print("\n" + "="*80)
    print("  TENDENCIAS")
    print("="*80)
    
    print(f"\n{'Buffer':<10} {'Retorno':<15} {'Win Rate':<15} {'Max DD':<15}")
    print("-" * 55)
    
    for r in results:
        ret_bar = "█" * int(r["return"] / 2) if r["return"] > 0 else ""
        wr_bar = "█" * int(r["wr"] / 5)
        dd_bar = "█" * int(r["max_dd"])
        
        print(f"{r['buffer']:<10} {r['return']:+6.2f}% {ret_bar:<10}")
    
    # Recomendación
    print("\n" + "="*80)
    print("  RECOMENDACIÓN")
    print("="*80)
    
    # Calcular score ponderado
    for r in results:
        # Score: 40% retorno, 30% WR, 20% PF, 10% DD inverso
        r["score"] = (
            r["return"] * 0.4 +
            r["wr"] * 0.3 +
            r["pf"] * 10 * 0.2 +
            (10 - r["max_dd"]) * 0.1
        )
    
    best_overall = max(results, key=lambda x: x["score"])
    
    print(f"\n✅ BUFFER ÓPTIMO: {best_overall['buffer']} puntos")
    print(f"\n   Métricas:")
    print(f"   • Retorno:       {best_overall['return']:+.2f}%")
    print(f"   • Win Rate:      {best_overall['wr']:.1f}%")
    print(f"   • Profit Factor: {best_overall['pf']:.2f}")
    print(f"   • Max DD:        {best_overall['max_dd']:.2f}%")
    print(f"   • Trades:        {best_overall['trades']}")
    
    if best_overall['buffer'] == 20:
        print(f"\n   ✅ La configuración actual (20 puntos) es óptima")
    else:
        diff_return = best_overall['return'] - next(r['return'] for r in results if r['buffer'] == 20)
        print(f"\n   ⚠️  Cambiar a {best_overall['buffer']} puntos mejoraría:")
        print(f"      • Retorno: {diff_return:+.2f}% adicional")
        print(f"      • Win Rate: {best_overall['wr'] - next(r['wr'] for r in results if r['buffer'] == 20):+.1f}%")
    
    print("\n" + "="*80)
