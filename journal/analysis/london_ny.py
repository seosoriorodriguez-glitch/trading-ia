# -*- coding: utf-8 -*-
# BOT = order_block_london. Sesion: 10:00-19:00 hora SERVIDOR (UTC+3), skip 15 min.
# CSV "Abrir/Cierre" = hora SERVIDOR (UTC+3).  ->  NY (EDT) = servidor - 7
import csv
from datetime import datetime, timedelta

rows=[]
with open(r'c:\Users\sosor\OneDrive\Escritorio\dev\trading\trading-ia\journal\analysis\trades_raw.csv', encoding='utf-8') as f:
    for r in csv.DictReader(f):
        if r['Simbolo']!='US30.cash': continue
        srv=datetime.strptime(r['Abrir'],'%Y-%m-%d %H:%M:%S')   # hora servidor UTC+3
        cl =datetime.strptime(r['Cierre'],'%Y-%m-%d %H:%M:%S')
        r['srv']=srv
        r['ny']=srv+timedelta(hours=-7)        # apertura en hora NY
        r['ny_close']=cl+timedelta(hours=-7)   # cierre en hora NY
        r['pnl']=float(r['Beneficio'])+float(r['Swap'])+float(r['Comisiones'])
        r['type']=r['Tipo']; r['dur']=int(r['DuracionSeg']); r['wd']=srv.weekday()
        rows.append(r)

def ev(trades,label):
    if not trades:
        print(f"{label:48s}: 0 trades"); return None
    n=len(trades); w=[t for t in trades if t['pnl']>0]; tot=sum(t['pnl'] for t in trades)
    ch=sorted(trades,key=lambda t:t['srv']); eq=0;pk=0;dd=0
    for t in ch:
        eq+=t['pnl']; pk=max(pk,eq); dd=min(dd,eq-pk)
    print(f"{label:48s}: n={n:3d} WR={len(w)/n*100:5.1f}% PnL={tot:8.2f} exp={tot/n:6.2f} maxDD={dd:8.2f}")
    return tot

print("Rango apertura NY:", min(t['ny'] for t in rows).strftime('%H:%M'), "->", max(t['ny'] for t in rows).strftime('%H:%M'))
print("(confirma ventana del bot london: ~NY 03:15 - 12:00)\n")

print("="*86)
print("PERFIL POR HORA DE APERTURA  (TODO en hora NY)")
print("="*86)
print(f"{'NY':>5} {'srv':>4} | {'n':>3} {'WR%':>6} {'PnL':>9} {'exp':>7}  fase")
fases={3:'London open',4:'London',5:'London mid',6:'pre-NY',7:'pre-NY',
       8:'NY pre-open',9:'NY OPEN (cash)',10:'NY +1h',11:'NY +2h',12:'NY mediodia'}
for nyh in range(3,13):
    ht=[t for t in rows if t['ny'].hour==nyh]
    if not ht: continue
    n=len(ht); w=[t for t in ht if t['pnl']>0]; tot=sum(t['pnl'] for t in ht)
    print(f"{nyh:>3}:00 {(nyh+7):>4} | {n:>3} {len(w)/n*100:>6.1f} {tot:>9.2f} {tot/n:>7.2f}  {fases.get(nyh,'')}")

print("\n"+"="*86)
print("BLOQUES NY")
print("="*86)
ev(rows, "TODO (baseline actual: NY 03-12)")
ev([t for t in rows if 3<=t['ny'].hour<8],  "London puro (NY 03-08, antes pre-NY)")
ev([t for t in rows if 3<=t['ny'].hour<9],  "London+pre-NY (NY 03-09)")
ev([t for t in rows if t['ny'].hour==9],    "Solo NY open (NY 09)")
ev([t for t in rows if 9<=t['ny'].hour<13], "Solo NY (NY 09-12)")
ev([t for t in rows if 10<=t['ny'].hour<13],"Cola NY post-open (NY 10-12) <-- sospechosa")

print("\n"+"="*86)
print("BARRIDO: 'si dejara de abrir a la hora X (NY)' -> queda lo abierto ANTES")
print("="*86)
for cut in range(4,13):
    kept=[t for t in rows if t['ny'].hour < cut]
    ev(kept, f"corte {cut:02d}:00 NY (srv {cut+7:02d}:00)")

print("\n"+"="*86)
print("ESCENARIOS que importan (hora NY)")
print("="*86)
ev(rows,                                          "Actual: abre NY 03-12 (corte 12:00 NY)")
ev([t for t in rows if t['ny'].hour < 10],        "Cortar tras NY open: abre NY 03-10")
ev([t for t in rows if t['ny'].hour < 11],        "Cortar a NY 11:00")
ev([t for t in rows if 3<=t['ny'].hour<8 or t['ny'].hour==9], "London 03-08 + solo vela NY open (09)")
ev([t for t in rows if t['ny'].hour in (3,9)],    "Solo los 2 picos: London open + NY open")

print("\n"+"="*86)
print("DIRECCION x bloque (hora NY)")
print("="*86)
for nm,fn in [("London 03-08",lambda t:3<=t['ny'].hour<8),
              ("NY open 09",  lambda t:t['ny'].hour==9),
              ("NY cola 10-12",lambda t:10<=t['ny'].hour<13)]:
    sub=[t for t in rows if fn(t)]
    ev([t for t in sub if t['type']=='buy'],  f"{nm} BUY")
    ev([t for t in sub if t['type']=='sell'], f"{nm} SELL")

print("\n"+"="*86)
print("DIA DE SEMANA (servidor)")
print("="*86)
days=['Lun','Mar','Mie','Jue','Vie']
for d in range(5):
    ev([t for t in rows if t['wd']==d], days[d])
