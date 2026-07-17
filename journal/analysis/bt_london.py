# -*- coding: utf-8 -*-
"""Backtest comparativo bot London: end=19:00 (vieja) vs end=17:00 (nueva).
Misma data historica M5+M1. Out-of-sample respecto al live (Abr-Jun 2026)."""
import sys, copy
from pathlib import Path
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd
from strategies.order_block_london.backtest.config import LONDON_PARAMS
from strategies.order_block.backtest.data_loader import load_csv, validate_alignment
from strategies.order_block.backtest.backtester import OrderBlockBacktester

M5 = r"data/US30_cash_M5_260d.csv"
M1 = r"data/US30_cash_M1_260d.csv"

print("Cargando datos...")
dfh = load_csv(M5); dfl = load_csv(M1)
validate_alignment(dfh, dfl)
print(f"  M5: {len(dfh)} velas ({dfh['time'].iloc[0]} -> {dfh['time'].iloc[-1]})")
print(f"  M1: {len(dfl)} velas ({dfl['time'].iloc[0]} -> {dfl['time'].iloc[-1]})")

def run(end):
    p = copy.deepcopy(LONDON_PARAMS)
    p["sessions"] = {"london": {"start": "10:00", "end": end, "skip_minutes": 15}}
    bt = OrderBlockBacktester(p)
    df = bt.run(dfh, dfl)
    return bt, df

def metrics(bt, df):
    if df.empty: return None
    w = df[df.pnl_usd>0]; l = df[df.pnl_usd<=0]
    gp=w.pnl_usd.sum(); gl=abs(l.pnl_usd.sum())
    bal=[bt.initial_balance]+list(df.balance); peak=bt.initial_balance; mdd=0
    for b in bal:
        peak=max(peak,b); mdd=max(mdd,(peak-b)/peak*100)
    return dict(n=len(df), wr=len(w)/len(df)*100, pf=(gp/gl if gl else 0),
                ret=(bt.balance-bt.initial_balance)/bt.initial_balance*100,
                bal=bt.balance, mdd=mdd, pnl=bt.balance-bt.initial_balance)

print("\n>>> Corriendo end=19:00 (config VIEJA)...")
bt19, df19 = run("19:00")
print(">>> Corriendo end=17:00 (config NUEVA, corte 10:00 NY)...")
bt17, df17 = run("17:00")

m19=metrics(bt19,df19); m17=metrics(bt17,df17)
print("\n"+"="*72)
print(f"COMPARATIVA  ({df19['entry_time'].min()} -> {df19['exit_time'].dropna().max()})")
print("="*72)
hdr=f"{'':22s}{'VIEJA 19:00':>16s}{'NUEVA 17:00':>16s}"
print(hdr)
for k,lab,fmt in [('n','Trades','{:d}'),('wr','Win Rate %','{:.1f}'),
                  ('pf','Profit Factor','{:.2f}'),('ret','Retorno %','{:+.2f}'),
                  ('pnl','PnL $','{:+,.0f}'),('bal','Balance final $','{:,.0f}'),
                  ('mdd','Max Drawdown %','{:.2f}')]:
    print(f"{lab:22s}{fmt.format(m19[k]):>16s}{fmt.format(m17[k]):>16s}")

# Desglose por hora NY de la config vieja: confirmar si cola NY 10-12 es mala out-of-sample
print("\n"+"="*72)
print("CONFIG VIEJA (19:00) desglosada por hora NY de apertura")
print("(NY = hora entrada - 7 ; confirma si la cola NY 10-12 sangra fuera de muestra)")
print("="*72)
df19=df19.copy()
df19["ny"]=pd.to_datetime(df19["entry_time"]).dt.hour - 7
for ny in sorted(df19["ny"].unique()):
    sub=df19[df19["ny"]==ny]; w=(sub.pnl_usd>0).mean()*100
    flag = "  <-- COLA (se corta)" if ny>=10 else ""
    print(f"  NY {ny:02d}:00 -> n={len(sub):3d}  WR={w:5.1f}%  PnL={sub.pnl_usd.sum():+9.2f}{flag}")

cola=df19[df19["ny"]>=10]
print(f"\n  COLA NY>=10 (lo que elimina el corte): n={len(cola)}  PnL={cola.pnl_usd.sum():+.2f}  WR={(cola.pnl_usd>0).mean()*100:.1f}%")
