# -*- coding: utf-8 -*-
import csv
from datetime import datetime

rows=[]
with open(r'c:\Users\sosor\OneDrive\Escritorio\dev\trading\trading-ia\journal\analysis\trades_raw.csv', encoding='utf-8') as f:
    for r in csv.DictReader(f):
        if r['Simbolo']!='US30.cash': continue
        rows.append(dict(
            o=datetime.strptime(r['Abrir'],'%Y-%m-%d %H:%M:%S'),
            c=datetime.strptime(r['Cierre'],'%Y-%m-%d %H:%M:%S'),
            pnl=float(r['Beneficio'])+float(r['Swap'])+float(r['Comisiones']),
            typ=r['Tipo']))

def greedy(trades, cap):
    """Simula tope de operaciones simultaneas. Devuelve (pnl, n_tomados, n_bloqueados, pnl_bloqueado)."""
    ts=sorted(trades, key=lambda t:t['o'])
    active=[]  # lista de close times de trades aceptados aun abiertos
    taken=[]; blocked=[]
    for t in ts:
        active=[ct for ct in active if ct> t['o']]  # cerrar los que ya terminaron
        if len(active)>=cap:
            blocked.append(t)
        else:
            taken.append(t); active.append(t['c'])
    return (sum(x['pnl'] for x in taken), len(taken),
            len(blocked), sum(x['pnl'] for x in blocked))

def report(trades, title):
    print("="*70); print(title); print("="*70)
    base=sum(t['pnl'] for t in trades)
    print(f"  SIN limite (real): n={len(trades)}  PnL={base:+.2f}")
    for cap in (1,2,3):
        pnl,nt,nb,pb=greedy(trades,cap)
        print(f"  cap={cap}: tomados={nt:3d}  PnL={pnl:+8.2f}  | bloqueados={nb:2d} (PnL que te pierdes={pb:+.2f})")
    # concurrencia observada
    ts=sorted(trades,key=lambda t:t['o']); maxc=0; conc_trades=[]
    for i,t in enumerate(ts):
        n=sum(1 for u in ts if u['o']<=t['o']<u['c'] and u is not t)
        if n>0: conc_trades.append((t,n))
        # max concurrency at open
    # max simultaneos reales
    events=[]
    for t in ts: events.append((t['o'],1)); events.append((t['c'],-1))
    events.sort()
    cur=0
    for _,d in events:
        cur+=d; maxc=max(maxc,cur)
    print(f"  Maximo simultaneas observado en real: {maxc}")
    if conc_trades:
        cp=sum(t['pnl'] for t,_ in conc_trades)
        cw=sum(1 for t,_ in conc_trades if t['pnl']>0)
        print(f"  Trades que abrieron con otra YA abierta: {len(conc_trades)}  PnL={cp:+.2f}  WR={cw/len(conc_trades)*100:.1f}%")
    print()

allt=rows
post=[t for t in rows if t['o']>=datetime(2026,6,2)]
report(allt, "TODAS las operaciones reales US30 (3-abr a 12-jun)")
report(post, "Solo POST-cambio (2-12 jun, config nueva en produccion)")
