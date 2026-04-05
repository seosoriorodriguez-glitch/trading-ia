# -*- coding: utf-8 -*-
"""
Analisis de filtro horario — Bot 2 London.
SOLO ANALISIS — no modifica ningun bot live.

Metodologia walk-forward:
  - Train: primeros 2/3 del periodo (aprox 345 dias)
  - Test:  ultimo 1/3 del periodo  (aprox 173 dias)
  - Identificamos horas debiles en TRAIN, aplicamos filtro en TEST
  - Si mejora en TEST => filtro tiene signal real, no overfitting

Uso: python run_hour_filter_analysis.py
"""
import sys
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")

sys.path.insert(0, '.')

import pandas as pd
import numpy as np
from pathlib import Path

TRADES_CSV = Path("strategies/order_block_london/backtest/results/trades.csv")
INIT_BAL   = 10_000.0

print("=" * 65)
print("  ANALISIS FILTRO HORARIO — Bot 2 London (SOLO ANALISIS)")
print("  NOTA: No se modifica ningun bot live")
print("=" * 65)

# ----------------------------------------------------------------
# Cargar trades con slippage
# ----------------------------------------------------------------
df = pd.read_csv(TRADES_CSV, parse_dates=["entry_time", "exit_time"])
df["hour"] = df["entry_time"].dt.hour
df["date"] = df["entry_time"].dt.date
print(f"\n  Trades cargados: {len(df)} | Periodo: {df['entry_time'].min().date()} → {df['entry_time'].max().date()}")

# ----------------------------------------------------------------
# Split walk-forward: 2/3 train / 1/3 test
# ----------------------------------------------------------------
split_idx  = int(len(df) * 2 / 3)
df_train   = df.iloc[:split_idx].copy()
df_test    = df.iloc[split_idx:].copy()
split_date = df_test["entry_time"].min().date()

print(f"\n  Train: {len(df_train)} trades (hasta {df_train['entry_time'].max().date()})")
print(f"  Test:  {len(df_test)} trades (desde {split_date})")

# ----------------------------------------------------------------
# Funcion: metricas por subconjunto
# ----------------------------------------------------------------
def metrics(sub):
    if len(sub) == 0:
        return dict(n=0, wr=0, pf=0, total=0, exp=0)
    w = sub[sub["pnl_usd"] > 0]
    l = sub[sub["pnl_usd"] < 0]
    pf = w["pnl_usd"].sum() / abs(l["pnl_usd"].sum()) if len(l) > 0 else 999
    return dict(
        n=len(sub),
        wr=len(w)/len(sub)*100,
        pf=pf,
        total=sub["pnl_usd"].sum(),
        exp=sub["pnl_usd"].mean(),
    )

# ----------------------------------------------------------------
# Breakdown por hora — sobre TRAIN
# ----------------------------------------------------------------
print("\n")
print("=" * 80)
print("  BREAKDOWN POR HORA — TRAIN (primeros 2/3)")
print("  Sesion London: 10:00-19:00 UTC+2")
print("=" * 80)
print(f"  {'Hora':>6} {'Trades':>8} {'WR%':>8} {'PF':>7} {'PnL $':>10} {'Exp $':>9}  Signal")
print(f"  {'-'*6} {'-'*8} {'-'*8} {'-'*7} {'-'*10} {'-'*9}  -------")

hour_stats_train = {}
for h in sorted(df_train["hour"].unique()):
    sub = df_train[df_train["hour"] == h]
    m   = metrics(sub)
    hour_stats_train[h] = m

    # Clasificar la hora
    if m["pf"] >= 1.25 and m["n"] >= 15:
        signal = "FUERTE +"
    elif m["pf"] >= 1.10 and m["n"] >= 10:
        signal = "OK +"
    elif m["pf"] < 0.90 and m["n"] >= 10:
        signal = "DEBIL --"
    elif m["pf"] < 1.00 and m["n"] >= 8:
        signal = "NEGATIVO -"
    else:
        signal = "muestra insuf."

    marker = " <--" if m["pf"] < 0.95 and m["n"] >= 8 else ""
    print(f"  {h:02d}:00  {m['n']:>8} {m['wr']:>7.1f}% {m['pf']:>7.3f} {m['total']:>+10,.0f} {m['exp']:>+9.2f}  {signal}{marker}")

# ----------------------------------------------------------------
# Identificar horas debiles (criterio: PF < 1.0 con al menos 8 trades)
# ----------------------------------------------------------------
weak_hours = [h for h, m in hour_stats_train.items() if m["pf"] < 1.0 and m["n"] >= 8]
print(f"\n  Horas debiles identificadas en TRAIN: {sorted(weak_hours)}")

# ----------------------------------------------------------------
# Comparacion en TRAIN: con y sin filtro horario
# ----------------------------------------------------------------
df_train_filtered = df_train[~df_train["hour"].isin(weak_hours)]
m_train_base  = metrics(df_train)
m_train_filt  = metrics(df_train_filtered)

print(f"\n  TRAIN — Impacto del filtro (IN-SAMPLE, referencial):")
print(f"  {'':20} {'Base':>12} {'Filtrado':>12} {'Delta':>10}")
print(f"  {'Trades':<20} {m_train_base['n']:>12} {m_train_filt['n']:>12} {m_train_filt['n']-m_train_base['n']:>+10}")
print(f"  {'WR%':<20} {m_train_base['wr']:>11.1f}% {m_train_filt['wr']:>11.1f}% {m_train_filt['wr']-m_train_base['wr']:>+9.1f}%")
print(f"  {'Profit Factor':<20} {m_train_base['pf']:>12.3f} {m_train_filt['pf']:>12.3f} {m_train_filt['pf']-m_train_base['pf']:>+10.3f}")
print(f"  {'Total PnL':<20} ${m_train_base['total']:>+10,.0f} ${m_train_filt['total']:>+10,.0f} ${m_train_filt['total']-m_train_base['total']:>+9,.0f}")
print(f"  {'Expectancy':<20} ${m_train_base['exp']:>+10.2f} ${m_train_filt['exp']:>+10.2f} ${m_train_filt['exp']-m_train_base['exp']:>+9.2f}")

# ----------------------------------------------------------------
# Aplicar mismo filtro en TEST (out-of-sample — lo que importa)
# ----------------------------------------------------------------
df_test_filtered = df_test[~df_test["hour"].isin(weak_hours)]
m_test_base  = metrics(df_test)
m_test_filt  = metrics(df_test_filtered)

print(f"\n")
print("=" * 65)
print(f"  TEST — Impacto del filtro (OUT-OF-SAMPLE — lo que importa)")
print(f"  Periodo: {split_date} en adelante")
print("=" * 65)
print(f"  {'':20} {'Base':>12} {'Filtrado':>12} {'Delta':>10}")
print(f"  {'Trades':<20} {m_test_base['n']:>12} {m_test_filt['n']:>12} {m_test_filt['n']-m_test_base['n']:>+10}")
print(f"  {'WR%':<20} {m_test_base['wr']:>11.1f}% {m_test_filt['wr']:>11.1f}% {m_test_filt['wr']-m_test_base['wr']:>+9.1f}%")
print(f"  {'Profit Factor':<20} {m_test_base['pf']:>12.3f} {m_test_filt['pf']:>12.3f} {m_test_filt['pf']-m_test_base['pf']:>+10.3f}")
print(f"  {'Total PnL':<20} ${m_test_base['total']:>+10,.0f} ${m_test_filt['total']:>+10,.0f} ${m_test_filt['total']-m_test_base['total']:>+9,.0f}")
print(f"  {'Expectancy':<20} ${m_test_base['exp']:>+10.2f} ${m_test_filt['exp']:>+10.2f} ${m_test_filt['exp']-m_test_base['exp']:>+9.2f}")

# ----------------------------------------------------------------
# Breakdown hora por hora en TEST (para ver si el patron se mantiene)
# ----------------------------------------------------------------
print(f"\n")
print("=" * 80)
print("  BREAKDOWN POR HORA — TEST (ultimo 1/3, OOS)")
print("=" * 80)
print(f"  {'Hora':>6} {'Trades':>8} {'WR%':>8} {'PF':>7} {'PnL $':>10}  Train-PF  Consistente?")
print(f"  {'-'*6} {'-'*8} {'-'*8} {'-'*7} {'-'*10}  --------  ------------")

for h in sorted(df_test["hour"].unique()):
    sub_test  = df_test[df_test["hour"] == h]
    m_t       = metrics(sub_test)
    m_tr      = hour_stats_train.get(h, {})
    train_pf  = m_tr.get("pf", 0)

    # Consistente = ambos en el mismo lado (ambos > 1 o ambos < 1)
    if m_t["n"] < 5:
        consistent = "muestra insuf."
    elif (train_pf > 1.0) == (m_t["pf"] > 1.0):
        consistent = "SI"
    else:
        consistent = "NO (diverge)"

    weak_tag = " [FILTRADA]" if h in weak_hours else ""
    print(f"  {h:02d}:00  {m_t['n']:>8} {m_t['wr']:>7.1f}% {m_t['pf']:>7.3f} {m_t['total']:>+10,.0f}  {train_pf:>8.3f}  {consistent}{weak_tag}")

# ----------------------------------------------------------------
# Veredicto
# ----------------------------------------------------------------
print("\n")
print("=" * 65)
print("  VEREDICTO")
print("=" * 65)

delta_pf_test = m_test_filt["pf"] - m_test_base["pf"]
delta_trades  = m_test_filt["n"] - m_test_base["n"]

print(f"\n  Horas a filtrar (si se aplica): {sorted(weak_hours)}")
print(f"  Trades eliminados:  {abs(delta_trades)} ({abs(delta_trades)/m_test_base['n']*100:.1f}% menos)")
print(f"  Delta PF en OOS:    {delta_pf_test:+.3f}")
print(f"  Delta PnL en OOS:   ${m_test_filt['total']-m_test_base['total']:+,.0f}")

if delta_pf_test > 0.05:
    verdict = "FILTRO PROMETEDOR — mejora significativa en OOS. Candidato para validar con live data."
elif delta_pf_test > 0:
    verdict = "FILTRO MARGINAL — mejora pequena en OOS. Esperar mas datos live antes de decidir."
else:
    verdict = "FILTRO SIN SIGNAL — no mejora en OOS. Probable overfitting en train. NO aplicar."

print(f"\n  {verdict}")
print(f"\n  RECORDATORIO: No modificar bots live hasta tener 1-2 meses")
print(f"  de datos reales para comparar con estos resultados.")
print("=" * 65)
