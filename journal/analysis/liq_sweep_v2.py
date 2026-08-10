# -*- coding: utf-8 -*-
"""Liquidity Sweep v2: len grande + filtro de sesion. 518d. Robusto=PF>1 ambas mitades."""
import sys
from pathlib import Path
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import numpy as np, pandas as pd
from strategies.fair_value_gap.backtest.data_loader import load_csv

BUFFER = 10; MIN_RISK = 15; MAX_RISK = 500; SPREAD = 4; WKND_H = 19


def pivots(h, l, LEN):
    n = len(h); ph = np.zeros(n, bool); pl = np.zeros(n, bool)
    for j in range(LEN, n - LEN):
        if h[j] > h[j-LEN:j].max() and h[j] > h[j+1:j+LEN+1].max(): ph[j] = True
        if l[j] < l[j-LEN:j].min() and l[j] < l[j+1:j+LEN+1].min(): pl[j] = True
    return ph, pl


def sim(h, l, c, tt, is_ph, is_pl, LEN, RR, sess):
    n = len(h); aPH = []; aPL = []; trades = []; op = None
    for i in range(LEN, n):
        j = i - LEN
        if is_ph[j]: aPH.append(h[j])
        if is_pl[j]: aPL.append(l[j])
        if op is not None:
            d, sl, tp = op['d'], op['sl'], op['tp']; hit = None
            if d == 's':
                if h[i] >= sl: hit = sl
                elif l[i] <= tp: hit = tp
            else:
                if l[i] <= sl: hit = sl
                elif h[i] >= tp: hit = tp
            if hit is not None:
                risk = abs(op['e'] - sl); pp = (op['e']-hit) if d=='s' else (hit-op['e'])
                trades.append((op['et'], tt[i], (pp-SPREAD)/risk if risk>0 else 0)); op = None
        if op is None:
            ts = tt[i]
            ok = ts.weekday() < 5 and not (ts.weekday()==4 and ts.hour>=WKND_H)
            if ok and sess is not None: ok = sess[0] <= ts.hour < sess[1]
            if ok:
                for ph in list(aPH):
                    if h[i] > ph and c[i] < ph:
                        e=c[i]; sl=h[i]+BUFFER; risk=sl-e
                        if MIN_RISK<=risk<=MAX_RISK:
                            op={'d':'s','e':e,'sl':sl,'tp':e-RR*risk,'et':ts}; aPH.remove(ph); break
                        aPH.remove(ph)
                    elif c[i] > ph: aPH.remove(ph)
                if op is None:
                    for pl in list(aPL):
                        if l[i] < pl and c[i] > pl:
                            e=c[i]; sl=l[i]-BUFFER; risk=e-sl
                            if MIN_RISK<=risk<=MAX_RISK:
                                op={'d':'l','e':e,'sl':sl,'tp':e+RR*risk,'et':ts}; aPL.remove(pl); break
                            aPL.remove(pl)
                        elif c[i] < pl: aPL.remove(pl)
    return pd.DataFrame(trades, columns=['et','xt','pnl_r'])


def pfh(x):
    g=x[x>0].sum(); ll=abs(x[x<=0].sum()); return g/ll if ll>0 else 99


if __name__ == "__main__":
    print("Cargando 518d...", flush=True)
    df = load_csv("data/US30_icm_M5_518d.csv")
    h=df.high.values; l=df.low.values; c=df.close.values; tt=pd.to_datetime(df.time.values)
    print("="*86)
    print("  LIQUIDITY SWEEP v2 — len grande + sesion (518d). Robusto=PF>1 ambas mitades")
    print("="*86)
    print(f"  {'len':<5}{'RR':<5}{'sesion':<10}{'Trades':>7}{'WR':>7}{'PF':>7}{'SumaR':>8}{'DD0.5%':>8}{'PF1a':>7}{'PF2a':>7}")
    # sesiones en hora servidor (UTC+3): NY=16-23, London=10-19, LonNY=13-22
    tests = []
    for LEN in (50, 70, 100, 150):
        for RR in (3.0, 4.0):
            tests.append((LEN, RR, None, "todas"))
    for LEN in (70, 100):
        tests.append((LEN, 4.0, (16, 23), "NY"))
        tests.append((LEN, 4.0, (10, 19), "London"))
    cache = {}
    for LEN, RR, sess, sname in tests:
        if LEN not in cache: cache[LEN] = pivots(h, l, LEN)
        is_ph, is_pl = cache[LEN]
        td = sim(h, l, c, tt, is_ph, is_pl, LEN, RR, sess)
        if td.empty: continue
        td = td.sort_values('xt').reset_index(drop=True); mid=len(td)//2
        n=len(td); wr=(td.pnl_r>0).mean()*100; pf=pfh(td.pnl_r)
        cum=td.pnl_r.cumsum(); mddr=(cum.cummax()-cum).max()
        p1=pfh(td.pnl_r.iloc[:mid]); p2=pfh(td.pnl_r.iloc[mid:])
        fl=" ROB" if pf>1 and p1>1 and p2>1 else ""
        print(f"  {LEN:<5}{RR:<5}{sname:<10}{n:>7}{wr:>6.1f}%{pf:>7.2f}{td.pnl_r.sum():>+7.0f}R"
              f"{mddr*0.5:>7.1f}%{p1:>7.2f}{p2:>7.2f}{fl}", flush=True)
    print("="*86)
