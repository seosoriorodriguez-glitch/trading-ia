# -*- coding: utf-8 -*-
"""
Breaker Block — MISMA zona que la OB (4 velas + half_candle), pero opera CONTINUACION:
el OB se rompe -> flipea -> retest (M5 cierra dentro de la zona flipeada) -> STOP en el
borde de continuacion. Config espejo de la OB ganadora (RR 2.5, buf 35, max 2, London).
M5-only para el 1er pase rapido (40d). PARAMS arriba.
"""
import sys
from pathlib import Path
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import numpy as np, pandas as pd
from strategies.fair_value_gap.backtest.data_loader import load_csv

# ---- PARAMS (espejo OB ganadora) ----
DIAS=40; RR=2.5; BUFFER=35; MIN_RISK=15; MAX_RISK=300; MAX_SIM=2
EXPIRY=100; SPREAD=4; PEND_MAX=50
SESSION=(10,17)   # London (hora servidor). None = todas
WKND_H=19
# -------------------------------------

def run(RR=RR, SESSION=SESSION, EXPIRY=EXPIRY, MAX_SIM=MAX_SIM):
    df = load_csv("data/US30_icm_M5_518d.csv")
    cut = df.time.iloc[-1] - pd.Timedelta(days=DIAS)
    df = df[df.time >= cut].reset_index(drop=True)
    o=df.open.values; h=df.high.values; l=df.low.values; c=df.close.values
    tt=pd.to_datetime(df.time.values); n=len(df)

    def sess_ok(ts):
        if ts.weekday()>=5: return False
        if ts.weekday()==4 and ts.hour>=WKND_H: return False
        if SESSION is None: return True
        return SESSION[0]<=ts.hour<SESSION[1]

    obs=[]; pends=[]; opens=[]; trades=[]; pb=False; pbr=False
    for i in range(4,n):
        bull = c[i-4]<o[i-4] and c[i-3]>o[i-3] and c[i-2]>o[i-2] and c[i-1]>o[i-1] and c[i]>o[i]
        bear = c[i-4]>o[i-4] and c[i-3]<o[i-3] and c[i-2]<o[i-2] and c[i-1]<o[i-1] and c[i]<o[i]
        if bull and not pb: obs.append({'t':'bull','zh':o[i-4],'zl':l[i-4],'s':'fresh','cb':i})
        if bear and not pbr: obs.append({'t':'bear','zh':h[i-4],'zl':o[i-4],'s':'fresh','cb':i})
        pb=bull; pbr=bear
        # estados
        for ob in obs:
            if ob['s']=='fresh':
                if ob['t']=='bull' and c[i]<ob['zl']: ob['s']='brk_bear'; ob['cb']=i
                elif ob['t']=='bear' and c[i]>ob['zh']: ob['s']='brk_bull'; ob['cb']=i
                elif i-ob['cb']>EXPIRY: ob['s']='dead'
            elif ob['s'] in ('brk_bear','brk_bull') and i-ob['cb']>EXPIRY: ob['s']='dead'
        obs=[ob for ob in obs if ob['s']!='dead']
        # exits
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
        # fills de pendientes
        sp=[]
        for p in pends:
            f=False
            if len(opens)<MAX_SIM:
                if p['d']=='s' and l[i]<=p['e']: opens.append(p); f=True
                elif p['d']=='l' and h[i]>=p['e']: opens.append(p); f=True
            if not f and i-p['cb']<=PEND_MAX: sp.append(p)
        pends=sp
        # nuevos retests de breaker
        if len(opens)+len(pends)<MAX_SIM and sess_ok(tt[i]):
            for ob in obs:
                if ob['s']=='brk_bear' and ob['zl']<=c[i]<=ob['zh']:
                    e=ob['zl']; sl=ob['zh']+BUFFER; risk=sl-e
                    if MIN_RISK<=risk<=MAX_RISK:
                        pends.append({'d':'s','e':e,'sl':sl,'tp':e-RR*risk,'et':tt[i],'cb':i}); ob['s']='dead'; break
                elif ob['s']=='brk_bull' and ob['zl']<=c[i]<=ob['zh']:
                    e=ob['zh']; sl=ob['zl']-BUFFER; risk=e-sl
                    if MIN_RISK<=risk<=MAX_RISK:
                        pends.append({'d':'l','e':e,'sl':sl,'tp':e+RR*risk,'et':tt[i],'cb':i}); ob['s']='dead'; break
    return pd.DataFrame(trades, columns=['et','xt','pnl_r']), DIAS


if __name__ == "__main__":
    print("BREAKER BLOCK (espejo OB: RR2.5, buf35, max2, London) — 40d M5", flush=True)
    print("="*62)
    td, days = run()
    if td.empty:
        print("  Sin trades.")
    else:
        n=len(td); wr=(td.pnl_r>0).mean()*100
        gp=td[td.pnl_r>0].pnl_r.sum(); gl=abs(td[td.pnl_r<=0].pnl_r.sum())
        pf=gp/gl if gl>0 else 99
        cum=td.pnl_r.cumsum(); mddr=(cum.cummax()-cum).max()
        print(f"  Trades: {n} ({n/days:.1f}/dia) | WR: {wr:.1f}% | PF: {pf:.2f}")
        print(f"  SumaR: {td.pnl_r.sum():+.0f}R | AvgR: {td.pnl_r.mean():+.3f} | DD: {mddr*0.5:.1f}% (0.5%)")
    print("="*62)
