# -*- coding: utf-8 -*-
"""Compara MISMO metodo M5: OB reaccion (fresh) vs Breaker continuacion (flipped).
Aisla si el problema es el CONCEPTO o el metodo crudo. 518d, London, RR variable."""
import sys
from pathlib import Path
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import numpy as np, pandas as pd
from strategies.fair_value_gap.backtest.data_loader import load_csv

BUFFER=35; MIN_RISK=15; MAX_RISK=300; MAX_SIM=2; EXPIRY=100; SPREAD=4; PEND_MAX=50; WKND_H=19
SESSION=(10,17)
df = load_csv("data/US30_icm_M5_518d.csv")
o=df.open.values; h=df.high.values; l=df.low.values; c=df.close.values
tt=pd.to_datetime(df.time.values); n=len(df)

def sok(ts):
    if ts.weekday()>=5: return False
    if ts.weekday()==4 and ts.hour>=WKND_H: return False
    return SESSION[0]<=ts.hour<SESSION[1]

def sim(mode, RR):  # mode='reaction' (OB) o 'continuation' (breaker)
    obs=[]; pends=[]; opens=[]; trades=[]; pb=False; pbr=False
    for i in range(4,n):
        bull=c[i-4]<o[i-4] and c[i-3]>o[i-3] and c[i-2]>o[i-2] and c[i-1]>o[i-1] and c[i]>o[i]
        bear=c[i-4]>o[i-4] and c[i-3]<o[i-3] and c[i-2]<o[i-2] and c[i-1]<o[i-1] and c[i]<o[i]
        if bull and not pb: obs.append({'t':'bull','zh':o[i-4],'zl':l[i-4],'s':'fresh','cb':i})
        if bear and not pbr: obs.append({'t':'bear','zh':h[i-4],'zl':o[i-4],'s':'fresh','cb':i})
        pb=bull; pbr=bear
        for ob in obs:
            if ob['s']=='fresh':
                if ob['t']=='bull' and c[i]<ob['zl']: ob['s']='brk_bear'; ob['cb']=i
                elif ob['t']=='bear' and c[i]>ob['zh']: ob['s']='brk_bull'; ob['cb']=i
                elif i-ob['cb']>EXPIRY: ob['s']='dead'
            elif ob['s'] in ('brk_bear','brk_bull') and i-ob['cb']>EXPIRY: ob['s']='dead'
        obs=[x for x in obs if x['s']!='dead']
        still=[]
        for t in opens:
            d,sl,tp=t['d'],t['sl'],t['tp']; hit=None
            if d=='s':
                if h[i]>=sl:hit=sl
                elif l[i]<=tp:hit=tp
            else:
                if l[i]<=sl:hit=sl
                elif h[i]>=tp:hit=tp
            if hit is not None:
                risk=abs(t['e']-sl); pp=(t['e']-hit) if d=='s' else (hit-t['e'])
                trades.append((t['et'],tt[i],(pp-SPREAD)/risk if risk>0 else 0))
            else: still.append(t)
        opens=still
        sp=[]
        for p in pends:
            f=False
            if len(opens)<MAX_SIM:
                if p['d']=='s' and l[i]<=p['e']: opens.append(p); f=True
                elif p['d']=='l' and h[i]>=p['e']: opens.append(p); f=True
            if not f and i-p['cb']<=PEND_MAX: sp.append(p)
        pends=sp
        if len(opens)+len(pends)<MAX_SIM and sok(tt[i]):
            for ob in obs:
                inside = ob['zl']<=c[i]<=ob['zh']
                if mode=='reaction' and ob['s']=='fresh' and inside:
                    if ob['t']=='bull':
                        e=ob['zh'];sl=ob['zl']-BUFFER;risk=e-sl
                        if MIN_RISK<=risk<=MAX_RISK: pends.append({'d':'l','e':e,'sl':sl,'tp':e+RR*risk,'et':tt[i],'cb':i});ob['s']='dead';break
                    else:
                        e=ob['zl'];sl=ob['zh']+BUFFER;risk=sl-e
                        if MIN_RISK<=risk<=MAX_RISK: pends.append({'d':'s','e':e,'sl':sl,'tp':e-RR*risk,'et':tt[i],'cb':i});ob['s']='dead';break
                elif mode=='continuation' and inside:
                    if ob['s']=='brk_bear':
                        e=ob['zl'];sl=ob['zh']+BUFFER;risk=sl-e
                        if MIN_RISK<=risk<=MAX_RISK: pends.append({'d':'s','e':e,'sl':sl,'tp':e-RR*risk,'et':tt[i],'cb':i});ob['s']='dead';break
                    elif ob['s']=='brk_bull':
                        e=ob['zh'];sl=ob['zl']-BUFFER;risk=e-sl
                        if MIN_RISK<=risk<=MAX_RISK: pends.append({'d':'l','e':e,'sl':sl,'tp':e+RR*risk,'et':tt[i],'cb':i});ob['s']='dead';break
    return pd.DataFrame(trades, columns=['et','xt','pnl_r'])

def pfh(x): g=x[x>0].sum(); ll=abs(x[x<=0].sum()); return g/ll if ll>0 else 99
print("OB reaccion vs BREAKER continuacion — MISMO metodo M5 (518d, London)")
print("="*80)
print(f"  {'Modo':<22}{'RR':<5}{'Trades':>7}{'WR':>7}{'PF':>7}{'SumaR':>8}{'DD0.5%':>8}{'PF1a':>7}{'PF2a':>7}")
for mode,mn in [('reaction','OB (reaccion)'),('continuation','Breaker (contin.)')]:
    for RR in (2.5,3.5):
        td=sim(mode,RR)
        if td.empty: continue
        td=td.sort_values('xt').reset_index(drop=True); mid=len(td)//2
        pf=pfh(td.pnl_r); cum=td.pnl_r.cumsum(); mddr=(cum.cummax()-cum).max()
        p1=pfh(td.pnl_r.iloc[:mid]); p2=pfh(td.pnl_r.iloc[mid:])
        fl=" ROB" if pf>1 and p1>1 and p2>1 else ""
        print(f"  {mn:<22}{RR:<5}{len(td):>7}{(td.pnl_r>0).mean()*100:>6.1f}%{pf:>7.2f}{td.pnl_r.sum():>+7.0f}R{mddr*0.5:>7.1f}%{p1:>7.2f}{p2:>7.2f}{fl}",flush=True)
print("="*80)
