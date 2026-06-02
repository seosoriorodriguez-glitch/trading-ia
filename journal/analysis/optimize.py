# -*- coding: utf-8 -*-
import csv
from datetime import datetime

rows=[]
with open(r'c:\Users\sosor\OneDrive\Escritorio\dev\trading\trading-ia\journal\analysis\trades_raw.csv', encoding='utf-8') as f:
    for r in csv.DictReader(f):
        r['open']=datetime.strptime(r['Abrir'],'%Y-%m-%d %H:%M:%S')
        r['pnl']=float(r['Beneficio'])+float(r['Swap'])+float(r['Comisiones'])
        r['type']=r['Tipo']; r['dur']=int(r['DuracionSeg'])
        r['h']=r['open'].hour; r['wd']=r['open'].weekday()
        rows.append(r)
us30=[t for t in rows if r and t['Simbolo']=='US30.cash']

def ev(trades,label):
    if not trades:
        print(f"{label:42s}: 0 trades"); return
    n=len(trades); w=[t for t in trades if t['pnl']>0]
    tot=sum(t['pnl'] for t in trades)
    print(f"{label:42s}: n={n:3d} WR={len(w)/n*100:5.1f}% PnL={tot:8.2f} exp={tot/n:7.2f}")

print("="*80)
print("CRUCE: SELL por bloque horario (el lado debil)")
print("="*80)
sells=[t for t in us30 if t['type']=='sell']
for name,lo,hi in [('10-13',10,13),('13-15',13,15),('15-17',15,17),('17-24',17,24),('00-10',0,10)]:
    ev([t for t in sells if lo<=t['h']<hi], f"SELL {name}")

print("\n"+"="*80)
print("CRUCE: SELL por dia")
print("="*80)
days=['Lun','Mar','Mie','Jue','Vie']
for d in range(5):
    ev([t for t in sells if t['wd']==d], f"SELL {days[d]}")

print("\n"+"="*80)
print("CRUCE: BUY por bloque horario (el lado fuerte)")
print("="*80)
buys=[t for t in us30 if t['type']=='buy']
for name,lo,hi in [('00-10',0,10),('10-13',10,13),('13-15',13,15),('15-17',15,17),('17-24',17,24)]:
    ev([t for t in buys if lo<=t['h']<hi], f"BUY {name}")

print("\n"+"="*80)
print("CRUCE: trades <5min (siempre pierden) por hora")
print("="*80)
fast=[t for t in us30 if t['dur']<300]
for t in fast:
    print(f"  {t['open']} {t['type']:4s} dur={t['dur']:4d}s pnl={t['pnl']:7.2f}")

print("\n"+"="*80)
print("SIMULACION DE FILTROS (sobre los mismos 141 trades US30)")
print("="*80)
ev(us30,"BASE (todo)")

f1=[t for t in us30 if not(t['h']>=17)]
ev(f1,"F1: excluir aperturas >=17:00")

f2=[t for t in us30 if t['wd'] not in (1,3)]
ev(f2,"F2: excluir Martes y Jueves")

f3=[t for t in us30 if t['type']=='buy']
ev(f3,"F3: solo BUY")

f4=[t for t in us30 if t['dur']>=300]
ev(f4,"F4: excluir <5min (filtro entrada)")

f5=[t for t in us30 if not(t['h']>=17) and t['wd'] not in (1,3)]
ev(f5,"F5: no>=17h + no Mar/Jue")

f6=[t for t in us30 if not(t['h']>=17) and t['type']=='buy']
ev(f6,"F6: no>=17h + solo BUY")

f7=[t for t in us30 if not(t['h']>=17) and t['wd'] not in (1,3) and t['dur']>=300]
ev(f7,"F7: no>=17h + no Mar/Jue + no<5min")

f8=[t for t in us30 if (10<=t['h']<13 or 15<=t['h']<17)]
ev(f8,"F8: solo ventanas 10-13 y 15-17")

f9=[t for t in us30 if (10<=t['h']<13 or 15<=t['h']<17) and t['wd'] not in (1,3)]
ev(f9,"F9: ventanas 10-13/15-17 + no Mar/Jue")

# combos buy/sell asimetrico
f10=[t for t in us30 if t['type']=='buy' or (t['type']=='sell' and 15<=t['h']<17)]
ev(f10,"F10: BUY siempre + SELL solo 15-17")

f11=[t for t in us30 if (t['type']=='buy' and not(t['h']>=17)) or (t['type']=='sell' and 15<=t['h']<17 and t['wd'] not in (1,3))]
ev(f11,"F11: BUY<17h + SELL 15-17 no Mar/Jue")

print("\n"+"="*80)
print("Detalle F9 y F11 por equity")
print("="*80)
for name,fset in [('F9',f9),('F11',f11),('F7',f7)]:
    ch=sorted(fset,key=lambda t:t['open']); eq=0;peak=0;dd=0
    for t in ch:
        eq+=t['pnl']; peak=max(peak,eq); dd=min(dd,eq-peak)
    print(f"  {name}: PnL={eq:8.2f} maxDD={dd:8.2f} n={len(fset)}")
