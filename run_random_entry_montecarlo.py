# -*- coding: utf-8 -*-
"""
Monte Carlo de entradas aleatorias — Bot 2 London.

Objetivo: verificar si la estrategia tiene edge real o es ruido.
Metodologia:
  - Mismos puntos de entrada (horario, precio, zona) que el backtest real
  - Direccion (LONG/SHORT) asignada aleatoriamente 50/50
  - Mismo RR=2.5, mismo risk (pts) por trade, mismo position sizing 0.5%
  - 1,000 simulaciones

Si la estrategia tiene edge real:
  PF_real >> PF_random (p95 del random deberia estar muy por debajo de PF_real)

Uso: python run_random_entry_montecarlo.py
"""
import sys, random
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")

sys.path.insert(0, '.')

import numpy as np
import pandas as pd
from pathlib import Path
from strategies.order_block.backtest.data_loader import load_csv
from strategies.order_block_london.backtest.config import LONDON_PARAMS

N_SIMS      = 1_000
RR          = LONDON_PARAMS["target_rr"]         # 2.5
RISK_PCT    = LONDON_PARAMS["risk_per_trade_pct"] # 0.005
SPREAD      = LONDON_PARAMS["avg_spread_points"]  # 2
SLIP        = LONDON_PARAMS.get("slippage_points", 2)  # 2
INIT_BAL    = LONDON_PARAMS["initial_balance"]    # 10_000
MAX_CANDLES = 2_000  # maximos M1 que busca exit antes de timeout

# ----------------------------------------------------------------
# 1. Cargar datos y trades reales
# ----------------------------------------------------------------
print("Cargando datos...")
df_m1 = load_csv("data/US30_icm_M1_500k.csv")
trades_csv = Path("strategies/order_block_london/backtest/results/trades.csv")
trades_df  = pd.read_csv(trades_csv, parse_dates=["entry_time", "exit_time"])
print(f"  M1: {len(df_m1):,} velas | Trades base: {len(trades_df)}")

# ----------------------------------------------------------------
# 2. Pre-computar resultado LONG y SHORT para cada punto de entrada
# ----------------------------------------------------------------
# Para cada trade real:
#   - Tomamos entry_price y risk_pts (= |entry - sl_real|)
#   - Calculamos SL/TP para LONG y SHORT simetricos en esa zona
#   - Revisamos M1 post-entrada para saber quien gana en cada direccion
#
# Luego las 1000 simulaciones solo sortean la direccion (O(1) por trade).

print("\nPre-computando outcomes para cada punto de entrada...")

m1_times  = df_m1["time"].tolist()
m1_highs  = df_m1["high"].tolist()
m1_lows   = df_m1["low"].tolist()

import bisect

entries = []  # lista de dicts con info por trade

for i, row in trades_df.iterrows():
    entry_price = row["entry_price"]
    sl_col      = "sl_price" if "sl_price" in row.index else "sl"
    risk_pts    = abs(entry_price - row[sl_col])

    if risk_pts <= 0:
        continue

    # SL/TP para LONG aleatorio
    sl_long = entry_price - risk_pts
    tp_long = entry_price + risk_pts * RR

    # SL/TP para SHORT aleatorio
    sl_short = entry_price + risk_pts
    tp_short = entry_price - risk_pts * RR

    # Indice en M1 justo despues de la entrada
    entry_time = row["entry_time"]
    idx_start  = bisect.bisect_right(m1_times, entry_time)

    # Buscar exit para LONG
    res_long = "timeout"
    for j in range(idx_start, min(idx_start + MAX_CANDLES, len(m1_times))):
        if m1_lows[j] <= sl_long:
            res_long = "sl"
            break
        if m1_highs[j] >= tp_long:
            res_long = "tp"
            break

    # Buscar exit para SHORT
    res_short = "timeout"
    for j in range(idx_start, min(idx_start + MAX_CANDLES, len(m1_times))):
        if m1_highs[j] >= sl_short:
            res_short = "sl"
            break
        if m1_lows[j] <= tp_short:
            res_short = "tp"
            break

    entries.append({
        "risk_pts":   risk_pts,
        "res_long":   res_long,   # "tp" | "sl" | "timeout"
        "res_short":  res_short,
    })

    if (i + 1) % 200 == 0:
        print(f"  {i+1}/{len(trades_df)} procesados...")

print(f"  {len(entries)} puntos de entrada pre-computados")

# Estadisticas de los outcomes pre-computados
long_wins  = sum(1 for e in entries if e["res_long"]  == "tp")
short_wins = sum(1 for e in entries if e["res_short"] == "tp")
print(f"\n  WR si todos fueran LONG:  {long_wins/len(entries)*100:.1f}%")
print(f"  WR si todos fueran SHORT: {short_wins/len(entries)*100:.1f}%")

# ----------------------------------------------------------------
# 3. Funcion: calcular PnL de un trade con costos
# ----------------------------------------------------------------
def trade_pnl(result, risk_pts, balance):
    """
    result: "tp" | "sl" | "timeout"
    Retorna pnl_usd aplicando spread + slippage (igual que backtester real).
    """
    risk_usd = balance * RISK_PCT
    if result == "tp":
        # Ganador: spread en entrada, no hay slip en TP
        net_pts  = risk_pts * RR - SPREAD - SLIP
        pnl_usd  = (net_pts / risk_pts) * risk_usd
    elif result == "sl":
        # Perdedor: spread + slip entrada + slip SL
        net_pts  = -risk_pts - SPREAD - SLIP * 2
        pnl_usd  = (net_pts / risk_pts) * risk_usd
    else:  # timeout — cierre al precio de entrada ~ -spread
        net_pts  = -SPREAD - SLIP
        pnl_usd  = (net_pts / risk_pts) * risk_usd
    return pnl_usd

# ----------------------------------------------------------------
# 4. Monte Carlo: 1,000 simulaciones
# ----------------------------------------------------------------
print(f"\nCorriendo {N_SIMS:,} simulaciones Monte Carlo...")

pf_list    = []
ret_list   = []
wr_list    = []
rng = random.Random(42)  # seed reproducible

for sim in range(N_SIMS):
    balance = INIT_BAL
    gross_win = 0.0
    gross_loss = 0.0
    wins = 0

    for e in entries:
        # Direccion aleatoria 50/50
        direction = rng.choice(["long", "short"])
        result    = e["res_long"] if direction == "long" else e["res_short"]
        pnl       = trade_pnl(result, e["risk_pts"], balance)
        balance  += pnl

        if pnl > 0:
            gross_win  += pnl
            wins       += 1
        else:
            gross_loss += abs(pnl)

    pf  = gross_win / gross_loss if gross_loss > 0 else 999.0
    ret = (balance - INIT_BAL) / INIT_BAL * 100
    wr  = wins / len(entries) * 100

    pf_list.append(pf)
    ret_list.append(ret)
    wr_list.append(wr)

    if (sim + 1) % 200 == 0:
        print(f"  Sim {sim+1:,}/{N_SIMS:,} — PF medio hasta ahora: {np.mean(pf_list):.3f}")

# ----------------------------------------------------------------
# 5. Estadisticas del backtest REAL (con slippage)
# ----------------------------------------------------------------
real_winners = trades_df[trades_df["pnl_usd"] > 0]
real_losers  = trades_df[trades_df["pnl_usd"] < 0]
real_pf      = real_winners["pnl_usd"].sum() / abs(real_losers["pnl_usd"].sum())
real_ret     = trades_df["pnl_usd"].sum() / INIT_BAL * 100
real_wr      = len(real_winners) / len(trades_df) * 100

# ----------------------------------------------------------------
# 6. Resultados
# ----------------------------------------------------------------
pf_arr  = np.array(pf_list)
ret_arr = np.array(ret_list)
wr_arr  = np.array(wr_list)

print("\n")
print("=" * 65)
print("  MONTE CARLO RANDOM ENTRIES — Bot 2 London (1,000 sims)")
print("=" * 65)
print(f"\n  {'Metrica':<22} {'ESTRATEGIA REAL':>18} {'RANDOM (media)':>16}")
print(f"  {'-'*22} {'-'*18} {'-'*16}")
print(f"  {'Win Rate':<22} {real_wr:>17.1f}% {np.mean(wr_arr):>15.1f}%")
print(f"  {'Profit Factor':<22} {real_pf:>18.3f} {np.mean(pf_arr):>16.3f}")
print(f"  {'Retorno %':<22} {real_ret:>17.1f}% {np.mean(ret_arr):>15.1f}%")

print(f"\n  {'--- Distribucion PF Random (1,000 sims) ---':}")
print(f"  {'Minimo':<22} {np.min(pf_arr):>18.3f}")
print(f"  {'Percentil 5':<22} {np.percentile(pf_arr, 5):>18.3f}")
print(f"  {'Percentil 25':<22} {np.percentile(pf_arr, 25):>18.3f}")
print(f"  {'Mediana (p50)':<22} {np.median(pf_arr):>18.3f}")
print(f"  {'Media':<22} {np.mean(pf_arr):>18.3f}")
print(f"  {'Percentil 75':<22} {np.percentile(pf_arr, 75):>18.3f}")
print(f"  {'Percentil 95':<22} {np.percentile(pf_arr, 95):>18.3f}")
print(f"  {'Maximo':<22} {np.max(pf_arr):>18.3f}")
print(f"  {'Desv. Estandar':<22} {np.std(pf_arr):>18.3f}")

# Cuantas sims superan el PF real
pct_beating_real = np.mean(pf_arr >= real_pf) * 100
print(f"\n  Sims que superan PF real ({real_pf:.3f}): {pct_beating_real:.1f}%")
print(f"  => Probabilidad de obtener PF>={real_pf:.3f} al azar: {pct_beating_real:.1f}%")

# Cuantas sims son rentables (PF > 1.0)
pct_profitable = np.mean(pf_arr > 1.0) * 100
print(f"\n  Sims rentables (PF > 1.0): {pct_profitable:.1f}%")
print(f"  Sims con retorno positivo: {np.mean(ret_arr > 0)*100:.1f}%")

print("\n")
print("=" * 65)
print("  VEREDICTO")
print("=" * 65)

z_score = (real_pf - np.mean(pf_arr)) / np.std(pf_arr)
print(f"\n  Z-score del PF real vs distribucion random: {z_score:.2f}")

if pct_beating_real < 1.0:
    verdict = "EDGE ESTADISTICAMENTE SIGNIFICATIVO (p<1%)"
elif pct_beating_real < 5.0:
    verdict = "EDGE PROBABLE (p<5%)"
elif pct_beating_real < 10.0:
    verdict = "EDGE DEBIL (p<10%)"
else:
    verdict = "SIN EDGE CLARO — resultados compatibles con azar"

print(f"  {verdict}")
print(f"\n  El PF real de {real_pf:.3f} supera al {100-pct_beating_real:.1f}%")
print(f"  de las simulaciones aleatorias.")
print("=" * 65)
