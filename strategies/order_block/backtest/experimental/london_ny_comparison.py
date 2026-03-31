# -*- coding: utf-8 -*-
"""
EXPERIMENTAL - Comparación Londres vs NY vs Ambas

Objetivo: Determinar si el backtest rentable original operaba ambas sesiones
y si Londres aporta valor o "ruido" a la estrategia.
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


def run(df_m5, df_m1, sessions: dict, label: str):
    params = copy.deepcopy(DEFAULT_PARAMS)
    params["sessions"] = sessions

    bt = OrderBlockBacktester(params)
    result = bt.run(df_m5, df_m1)

    df_t = result if isinstance(result, pd.DataFrame) else pd.DataFrame(result)
    if df_t is None or len(df_t) == 0:
        print(f"\n{label}")
        print(f"  ❌ 0 trades\n")
        return None

    balance = df_t["balance"].iloc[-1]
    ret  = (balance - params["initial_balance"]) / params["initial_balance"] * 100
    wr   = (df_t["pnl_usd"] > 0).mean() * 100
    
    # Max drawdown
    mdd  = 0.0
    peak = float(params["initial_balance"])
    for b in df_t["balance"]:
        if b > peak:
            peak = b
        dd = (peak - b) / peak * 100
        if dd > mdd:
            mdd = dd

    longs  = df_t[df_t["direction"] == "long"]
    shorts = df_t[df_t["direction"] == "short"]
    days   = max((df_t["entry_time"].iloc[-1] - df_t["entry_time"].iloc[0]).days, 1)
    
    # Profit factor
    winners = df_t[df_t["pnl_usd"] > 0]
    losers = df_t[df_t["pnl_usd"] < 0]
    gross_profit = winners["pnl_usd"].sum() if len(winners) > 0 else 0
    gross_loss = abs(losers["pnl_usd"].sum()) if len(losers) > 0 else 0
    pf = gross_profit / gross_loss if gross_loss > 0 else float('inf')

    print(f"\n{label}")
    print(f"  📊 Trades:        {len(df_t)}  ({days} días, {len(df_t)/days:.2f}/día)")
    print(f"  🎯 Win Rate:      {wr:.1f}%")
    print(f"  💰 Retorno:       {ret:+.2f}%")
    print(f"  📉 Max DD:        {mdd:.2f}%")
    print(f"  📈 Profit Factor: {pf:.2f}")
    
    if len(longs):
        long_wr = (longs['pnl_usd']>0).mean()*100
        long_pnl = longs["pnl_usd"].sum()
        print(f"  🟢 Long:  {len(longs)} trades, WR {long_wr:.0f}%, PnL ${long_pnl:+,.0f}")
    if len(shorts):
        short_wr = (shorts['pnl_usd']>0).mean()*100
        short_pnl = shorts["pnl_usd"].sum()
        print(f"  🔴 Short: {len(shorts)} trades, WR {short_wr:.0f}%, PnL ${short_pnl:+,.0f}")
    
    return {
        "label": label,
        "trades": len(df_t),
        "wr": wr,
        "return": ret,
        "max_dd": mdd,
        "pf": pf,
        "trades_per_day": len(df_t)/days,
        "df": df_t
    }


if __name__ == "__main__":
    print("\n" + "="*80)
    print("  BACKTEST COMPARATIVO: LONDRES vs NY vs AMBAS")
    print("  Objetivo: Determinar configuración óptima de sesiones")
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

    # A) Solo Londres
    result_london = run(df_m5, df_m1,
        {"london": {"start": "08:00", "end": "13:30", "skip_minutes": 15}},
        "A) SOLO LONDRES (08:00-13:30 UTC)")

    # B) Solo NY (configuración actual del bot)
    result_ny = run(df_m5, df_m1,
        {"new_york": {"start": "13:30", "end": "20:00", "skip_minutes": 15}},
        "B) SOLO NY (13:30-20:00 UTC) — CONFIG ACTUAL BOT")

    # C) Ambas sesiones
    result_both = run(df_m5, df_m1,
        {
            "london": {"start": "08:00", "end": "13:30", "skip_minutes": 15},
            "new_york": {"start": "13:30", "end": "20:00", "skip_minutes": 15}
        },
        "C) LONDRES + NY (08:00-20:00 UTC)")

    print("\n" + "="*80)
    print("  RESUMEN COMPARATIVO")
    print("="*80)
    
    results = [r for r in [result_london, result_ny, result_both] if r is not None]
    
    if len(results) > 0:
        print(f"\n{'Config':<35} {'Trades':<10} {'WR':<10} {'Retorno':<12} {'Max DD':<10} {'PF':<8}")
        print("-" * 80)
        for r in results:
            print(f"{r['label']:<35} {r['trades']:<10} {r['wr']:<10.1f} {r['return']:+<12.2f} {r['max_dd']:<10.2f} {r['pf']:<8.2f}")
    
    print("\n" + "="*80)
    print("  ANÁLISIS")
    print("="*80)
    
    if result_both and result_ny:
        trades_diff = result_both["trades"] - result_ny["trades"]
        trades_diff_pct = (trades_diff / result_ny["trades"]) * 100 if result_ny["trades"] > 0 else 0
        ret_diff = result_both["return"] - result_ny["return"]
        
        print(f"\n📊 LONDRES + NY vs SOLO NY:")
        print(f"  Trades adicionales: +{trades_diff} ({trades_diff_pct:+.1f}%)")
        print(f"  Retorno adicional:  {ret_diff:+.2f}%")
        
        if result_both["return"] > result_ny["return"]:
            print(f"\n✅ CONCLUSIÓN: LONDRES + NY es SUPERIOR")
            print(f"   - Más trades: {result_both['trades']} vs {result_ny['trades']}")
            print(f"   - Mejor retorno: {result_both['return']:+.2f}% vs {result_ny['return']:+.2f}%")
        else:
            print(f"\n⚠️  CONCLUSIÓN: SOLO NY es SUPERIOR")
            print(f"   - Mejor retorno: {result_ny['return']:+.2f}% vs {result_both['return']:+.2f}%")
            print(f"   - Londres añade ruido")
    
    if result_london:
        print(f"\n📊 LONDRES SOLO:")
        print(f"  WR: {result_london['wr']:.1f}%")
        print(f"  Retorno: {result_london['return']:+.2f}%")
        print(f"  Profit Factor: {result_london['pf']:.2f}")
        
        if result_london["wr"] < 40:
            print(f"  ⚠️  WR insuficiente (< 40%)")
        if result_london["pf"] < 1.5:
            print(f"  ⚠️  Profit Factor bajo (< 1.5)")
    
    print("\n" + "="*80)
    print("  RECOMENDACIÓN")
    print("="*80)
    
    if result_both and result_ny and result_both["return"] > result_ny["return"]:
        print("\n✅ ACTIVAR LONDRES + NY en el bot live")
        print("   Configuración recomendada:")
        print('   "sessions": {')
        print('       "london": {"start": "08:00", "end": "13:30", "skip_minutes": 15},')
        print('       "new_york": {"start": "13:30", "end": "20:00", "skip_minutes": 15}')
        print('   }')
    elif result_ny:
        print("\n✅ MANTENER SOLO NY (configuración actual)")
        print("   Londres no aporta valor adicional")
    
    print("\n" + "="*80)
