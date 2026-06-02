# -*- coding: utf-8 -*-
# CSV "Abrir/Cierre" estan en UTC. Servidor FTMO = UTC+3 (verano EEST).
# NY (EDT) = UTC-4 ; Londres (BST) = UTC+1
import csv
from datetime import datetime, timedelta

rows=[]
with open(r'c:\Users\sosor\OneDrive\Escritorio\dev\trading\trading-ia\journal\analysis\trades_raw.csv', encoding='utf-8') as f:
    for r in csv.DictReader(f):
        if r['Simbolo']!='US30.cash': continue
        o=datetime.strptime(r['Abrir'],'%Y-%m-%d %H:%M:%S')   # UTC
        r['utc']=o
        r['srv']=o+timedelta(hours=3)
        r['ny']=o+timedelta(hours=-4)
        r['lon']=o+timedelta(hours=1)
        r['pnl']=float(r['Beneficio'])+float(r['Swap'])+float(r['Comisiones'])
        r['type']=r['Tipo']; r['dur']=int(r['DuracionSeg'])
        rows.append(r)

def ev(trades,label):
    if not trades:
        print(f"{label:46s}: 0 trades"); return
    n=len(trades); w=[t for t in trades if t['pnl']>0]; tot=sum(t['pnl'] for t in trades)
    # drawdown
    ch=sorted(trades,key=lambda t:t['utc']); eq=0;pk=0;dd=0
    for t in ch:
        eq+=t['pnl']; pk=max(pk,eq); dd=min(dd,eq-pk)
    print(f"{label:46s}: n={n:3d} WR={len(w)/n*100:5.1f}% PnL={tot:8.2f} exp={tot/n:6.2f} maxDD={dd:8.2f}")

print("="*92)
print("DISTRIBUCION POR HORA DE APERTURA — comparada en 3 husos")
print("(UTC = CSV | NY = UTC-4 | servidor MT5 = UTC+3)")
print("="*92)
print(f"{'UTC':>4} {'NY':>4} {'LON':>4} {'SRV':>4} | {'n':>3} {'WR%':>6} {'PnL':>9} {'exp':>7}")
for h in range(7,21):
    ht=[t for t in rows if t['utc'].hour==h]
    if not ht: continue
    n=len(ht); w=[t for t in ht if t['pnl']>0]; tot=sum(t['pnl'] for t in ht)
    ny=(h-4)%24; lon=(h+1)%24; srv=(h+3)%24
    print(f"{h:>4} {ny:>4} {lon:>4} {srv:>4} | {n:>3} {len(w)/n*100:>6.1f} {tot:>9.2f} {tot/n:>7.2f}")

print("\n"+"="*92)
print("SESIONES (segun hora de APERTURA en UTC)")
print("="*92)
# Londres cash 08:00-16:30 BST = 07:00-15:30 UTC
# NY cash 09:30-16:00 EDT = 13:30-20:00 UTC ; NY pre-open 08:00 NY = 12:00 UTC
lon_only   = [t for t in rows if t['utc'].hour < 13 or (t['utc'].hour==13 and t['utc'].minute<30)]  # antes de NY open
ny_session = [t for t in rows if (t['utc'].hour>13) or (t['utc'].hour==13 and t['utc'].minute>=30)]
overlap    = [t for t in rows if 13<=t['utc'].hour<16]  # solape Londres-NY (NY 09-12)
ev(rows,        "TODO (baseline actual)")
ev(lon_only,    "Solo LONDRES (apertura < 13:30 UTC / NY 09:30)")
ev(ny_session,  "Solo NY (apertura >= 13:30 UTC / NY 09:30)")
ev(overlap,     "Solo SOLAPE Lon-NY (13-16 UTC / NY 09-12)")

print("\n"+"="*92)
print("BARRIDO: 'si el bot DEJARA de abrir a la hora X (NY)' -> PnL de lo que queda")
print("="*92)
print("Mantiene los trades cuya APERTURA es ANTES del corte:")
for ny_cut in range(6,17):
    utc_cut=ny_cut+4
    kept=[t for t in rows if t['utc'].hour < utc_cut]
    ev(kept, f"corte {ny_cut:02d}:00 NY (= {utc_cut:02d}:00 UTC = {(utc_cut+3)%24:02d}:00 srv)")

print("\n"+"="*92)
print("BARRIDO: 'si el bot solo abriera DESPUES de la hora X (NY)'")
print("="*92)
for ny_start in range(6,16):
    utc_start=ny_start+4
    kept=[t for t in rows if t['utc'].hour >= utc_start]
    ev(kept, f"empieza {ny_start:02d}:00 NY (= {utc_start:02d}:00 UTC)")

print("\n"+"="*92)
print("ESCENARIOS COMBINADOS (apertura) que pediste")
print("="*92)
# 1. Solo London (stop al abrir NY 09:30)
ev(lon_only, "A) Solo Londres (stop 09:30 NY)")
# 2. Stop a las 9:00 NY (pre-apertura) -> mantener < 13:00 UTC
s_9 = [t for t in rows if t['utc'].hour < 13]
ev(s_9, "B) Stop 09:00 NY pre-open (< 13:00 UTC)")
# 3. Stop a las 12:00 NY -> mantener < 16:00 UTC
s_12 = [t for t in rows if t['utc'].hour < 16]
ev(s_12, "C) Stop 12:00 NY (< 16:00 UTC)")
# 4. Stop 11:00 NY
s_11=[t for t in rows if t['utc'].hour < 15]
ev(s_11, "D) Stop 11:00 NY (< 15:00 UTC)")
# 5. Stop 13:00 NY
s_13=[t for t in rows if t['utc'].hour < 17]
ev(s_13, "E) Stop 13:00 NY (< 17:00 UTC)")

print("\n"+"="*92)
print("CRUCE direccion x sesion (apertura)")
print("="*92)
for sess_name, sset in [("LONDRES (<13:30 UTC)",lon_only),("NY (>=13:30 UTC)",ny_session)]:
    ev([t for t in sset if t['type']=='buy'],  f"{sess_name} BUY")
    ev([t for t in sset if t['type']=='sell'], f"{sess_name} SELL")
