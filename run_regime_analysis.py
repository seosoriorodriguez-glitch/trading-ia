# -*- coding: utf-8 -*-
"""
Analisis de regimenes de mercado para US30 — 518 dias.
Corre el backtest completo, detecta regimenes y cruza con performance.

Uso: python run_regime_analysis.py
     python run_regime_analysis.py --clusters 4   (probar otro numero)
     python run_regime_analysis.py --elbow         (buscar k optimo)
"""
import sys, argparse
sys.path.insert(0, '.')

import pandas as pd
from strategies.order_block.backtest.config import DEFAULT_PARAMS
from strategies.order_block.backtest.data_loader import load_csv
from strategies.order_block.backtest.backtester_limit_orders import OrderBlockBacktesterLimitOrders
from market_regime_detector import (
    calculate_regime_features,
    fit_regime_model,
    predict_regimes,
    analyze_regime_performance,
    find_optimal_clusters,
    plot_regimes,
    FEATURE_COLS,
)

parser = argparse.ArgumentParser()
parser.add_argument("--clusters", type=int, default=3, help="Numero de clusters (default: 3)")
parser.add_argument("--elbow",    action="store_true",  help="Mostrar elbow plot y salir")
args = parser.parse_args()

# ------------------------------------------------------------------
# 1. Cargar datos y correr backtest
# ------------------------------------------------------------------
print("Cargando datos US30...")
df_m5 = load_csv('data/US30_icm_M5_518d.csv')
df_m1 = load_csv('data/US30_icm_M1_500k.csv')

print("Corriendo backtest LIMIT (518 dias)...")
bt = OrderBlockBacktesterLimitOrders(DEFAULT_PARAMS)
trades_df = bt.run(df_m5, df_m1)
print(f"  Trades generados: {len(trades_df)}")

# ------------------------------------------------------------------
# 2. Calcular features de regimen sobre M5
# ------------------------------------------------------------------
print("\nCalculando features de mercado (M5)...")
df_features = calculate_regime_features(df_m5, lookback=50, ma_period=20, atr_period=14)

df_valid = df_features[df_features[FEATURE_COLS].notna().all(axis=1)].copy()
print(f"  Velas M5 validas para clustering: {len(df_valid)} / {len(df_features)}")

# ------------------------------------------------------------------
# 3. Elbow plot (opcional)
# ------------------------------------------------------------------
train_end = int(len(df_valid) * 0.6)
df_train  = df_valid.iloc[:train_end]
df_test   = df_valid.iloc[train_end:]

from sklearn.preprocessing import StandardScaler
scaler_temp = StandardScaler()
scaler_temp.fit(df_train[FEATURE_COLS])

if args.elbow:
    print("\nBuscando numero optimo de clusters (k=2..6)...")
    find_optimal_clusters(df_train, scaler_temp, max_k=6)
    sys.exit()

# ------------------------------------------------------------------
# 4. Entrenar modelo y predecir
# ------------------------------------------------------------------
n_clusters = args.clusters
print(f"\nEntrenando KMeans con k={n_clusters} (60% train = {len(df_train)} velas)...")
model, scaler = fit_regime_model(df_train, n_clusters=n_clusters)

print("Prediciendo regimenes en dataset completo...")
df_regimes = predict_regimes(df_valid, model, scaler)

# Distribucion de regimenes
print("\nDistribucion de regimenes:")
dist = df_regimes[df_regimes["regime"] >= 0]["regime"].value_counts().sort_index()
for r, cnt in dist.items():
    print(f"  Regimen {r}: {cnt:5d} velas ({cnt/len(df_regimes)*100:.1f}%)")

# ------------------------------------------------------------------
# 5. Cruzar trades con regimenes
# ------------------------------------------------------------------
print("\nCruzando trades con regimenes de mercado...")
report = analyze_regime_performance(trades_df, df_regimes)

# ------------------------------------------------------------------
# 6. Visualizaciones
# ------------------------------------------------------------------
print("\nGenerando graficos...")

# Necesitamos las features en trades_df para el cruce de visualizacion
# Re-hacer el merge para pasar trades con regime a plot_regimes
regimes_idx = df_regimes[["time","regime"]].copy()
regimes_idx["time"] = pd.to_datetime(regimes_idx["time"])
trades_with_regime = pd.merge_asof(
    trades_df.sort_values("entry_time").assign(entry_time=pd.to_datetime(trades_df["entry_time"])),
    regimes_idx.sort_values("time").rename(columns={"time":"entry_time"}),
    on="entry_time",
    direction="backward"
)

plot_regimes(df_regimes, trades_with_regime)

# ------------------------------------------------------------------
# 7. Resumen final
# ------------------------------------------------------------------
print("\n" + "="*60)
print("  RESUMEN EJECUTIVO")
print("="*60)
if not report.empty:
    best  = report.loc[report["pf"].idxmax()]
    worst = report.loc[report["pf"].idxmin()]
    print(f"\n  Mejor regimen  : Regimen {int(best['regime'])} "
          f"— PF {best['pf']:.2f} | WR {best['wr_pct']:.1f}% | {int(best['trades'])} trades")
    print(f"  Peor regimen   : Regimen {int(worst['regime'])} "
          f"— PF {worst['pf']:.2f} | WR {worst['wr_pct']:.1f}% | {int(worst['trades'])} trades")
    pnl_best  = best['total_pnl']
    pnl_worst = worst['total_pnl']
    print(f"\n  PnL en mejor regimen : ${pnl_best:+,.0f}")
    print(f"  PnL en peor regimen  : ${pnl_worst:+,.0f}")
    print(f"\n  Si hubieras filtrado el peor regimen:")
    total_pnl = report["total_pnl"].sum()
    print(f"    PnL total actual    : ${total_pnl:+,.0f}")
    print(f"    PnL sin peor regimen: ${total_pnl - pnl_worst:+,.0f}")
    improvement = (total_pnl - pnl_worst - total_pnl) / abs(total_pnl) * 100 if total_pnl != 0 else 0
    print(f"    Diferencia          : ${-pnl_worst:+,.0f} ({-pnl_worst/abs(total_pnl)*100:+.1f}%)")

print(f"\n  Archivos generados:")
print(f"    regime_analysis.png  — graficos de regimenes y performance")
print(f"\n  Para probar otro numero de clusters:")
print(f"    python run_regime_analysis.py --clusters 4")
print(f"  Para buscar k optimo:")
print(f"    python run_regime_analysis.py --elbow")
print("="*60)
