# -*- coding: utf-8 -*-
import csv
from datetime import datetime
from collections import defaultdict

rows = []
with open(r'c:\Users\sosor\OneDrive\Escritorio\dev\trading\trading-ia\journal\analysis\trades_raw.csv', encoding='utf-8') as f:
    for r in csv.DictReader(f):
        r['open'] = datetime.strptime(r['Abrir'], '%Y-%m-%d %H:%M:%S')
        r['close'] = datetime.strptime(r['Cierre'], '%Y-%m-%d %H:%M:%S')
        r['pnl'] = float(r['Beneficio']) + float(r['Swap']) + float(r['Comisiones'])
        r['profit'] = float(r['Beneficio'])
        r['swap'] = float(r['Swap'])
        r['comm'] = float(r['Comisiones'])
        r['vol'] = float(r['Volumen'])
        r['entry'] = float(r['Precio'])
        r['sl'] = float(r['SL'])
        r['tp'] = float(r['TP'])
        r['pips'] = float(r['Pips'])
        r['dur'] = int(r['DuracionSeg'])
        r['type'] = r['Tipo']
        r['sym'] = r['Simbolo']
        rows.append(r)

def stats(trades, label):
    if not trades:
        print(f"  {label}: sin trades")
        return None
    n = len(trades)
    wins = [t for t in trades if t['pnl'] > 0]
    losses = [t for t in trades if t['pnl'] <= 0]
    tot = sum(t['pnl'] for t in trades)
    gw = sum(t['pnl'] for t in wins)
    gl = sum(t['pnl'] for t in losses)
    wr = len(wins)/n*100
    avg_w = gw/len(wins) if wins else 0
    avg_l = gl/len(losses) if losses else 0
    pf = gw/abs(gl) if gl else float('inf')
    exp = tot/n
    print(f"  {label}: n={n:3d} | WR={wr:5.1f}% | PnL={tot:9.2f} | PF={pf:5.2f} | "
          f"avgW={avg_w:6.2f} avgL={avg_l:6.2f} | exp/trade={exp:6.2f}")
    return dict(n=n, wr=wr, pnl=tot, pf=pf, wins=len(wins), losses=len(losses))

us30 = [t for t in rows if t['sym']=='US30.cash']
btc  = [t for t in rows if t['sym']=='BTCUSD']

print("="*90)
print("RESUMEN GLOBAL")
print("="*90)
stats(rows, "TODOS    ")
stats(us30, "US30.cash")
stats(btc,  "BTCUSD   ")

print("\n" + "="*90)
print("ANALISIS US30 (foco principal)")
print("="*90)
print("\n-- Por direccion --")
stats([t for t in us30 if t['type']=='buy'],  "BUY ")
stats([t for t in us30 if t['type']=='sell'], "SELL")

print("\n-- Por dia de la semana (hora apertura) --")
days = ['Lun','Mar','Mie','Jue','Vie','Sab','Dom']
for d in range(7):
    dt = [t for t in us30 if t['open'].weekday()==d]
    if dt: stats(dt, days[d])

print("\n-- Por hora de apertura (servidor UTC+3) --")
for h in range(0,24):
    ht = [t for t in us30 if t['open'].hour==h]
    if ht: stats(ht, f"{h:02d}:00")

print("\n-- Bloques horarios --")
blocks = {
 '00-10 (pre-NY)': lambda h: h<10,
 '10-13 (apertura EU/AM)': lambda h: 10<=h<13,
 '13-15 (open NY)': lambda h: 13<=h<15,
 '15-17 (NY mid)': lambda h: 15<=h<17,
 '17-19 (NY tarde)': lambda h: 17<=h<19,
 '19-24 (cierre/noche)': lambda h: h>=19,
}
for name, fn in blocks.items():
    bt = [t for t in us30 if fn(t['open'].hour)]
    if bt: stats(bt, name)

print("\n-- Duracion del trade --")
dur_buckets = {
 '<5min': lambda s: s<300,
 '5-30min': lambda s: 300<=s<1800,
 '30-60min': lambda s: 1800<=s<3600,
 '1-3h': lambda s: 3600<=s<10800,
 '3-8h': lambda s: 10800<=s<28800,
 '>8h (overnight)': lambda s: s>=28800,
}
for name, fn in dur_buckets.items():
    dt = [t for t in us30 if fn(t['dur'])]
    if dt: stats(dt, name)

print("\n-- Resultado: distancia SL y TP (puntos) en trades con SL/TP definido --")
withsltp = [t for t in us30 if t['sl']>0 and t['tp']>0]
for t in withsltp[:1]: pass
risk_pts = []
rr_pts = []
for t in withsltp:
    if t['type']=='buy':
        r = t['entry']-t['sl']; rw = t['tp']-t['entry']
    else:
        r = t['sl']-t['entry']; rw = t['entry']-t['tp']
    if r>0:
        risk_pts.append(r); rr_pts.append(rw/r)
print(f"  trades con SL/TP: {len(withsltp)}")
print(f"  riesgo medio (pts): {sum(risk_pts)/len(risk_pts):.1f}  (min {min(risk_pts):.0f} / max {max(risk_pts):.0f})")
print(f"  RR objetivo medio: {sum(rr_pts)/len(rr_pts):.2f}")

print("\n-- Trades SIN SL/TP (gestion manual/otra logica) --")
nosltp = [t for t in us30 if t['sl']==0 or t['tp']==0]
stats(nosltp, "sin SL/TP")

print("\n-- Por semana --")
wk = defaultdict(list)
for t in us30:
    y,w,_ = t['open'].isocalendar()
    wk[(y,w)].append(t)
for k in sorted(wk):
    stats(wk[k], f"Sem {k[1]}")

print("\n-- Equity acumulada por trade (orden cronologico) --")
ch = sorted(us30, key=lambda t: t['open'])
eq = 0; peak = 0; maxdd = 0
streak = 0; maxlose=0; maxwin=0; cur=0
for t in ch:
    eq += t['pnl']
    peak = max(peak, eq)
    maxdd = min(maxdd, eq-peak)
    if t['pnl']>0:
        cur = cur+1 if cur>0 else 1
    else:
        cur = cur-1 if cur<0 else -1
    maxwin = max(maxwin, cur); maxlose=min(maxlose,cur)
print(f"  PnL final US30: {eq:.2f}")
print(f"  Max drawdown (equity cerrada): {maxdd:.2f}")
print(f"  Racha max ganadora: {maxwin} | Racha max perdedora: {maxlose}")

print("\n-- Magnitud perdidas vs ganancias (US30) --")
wins=[t['pnl'] for t in us30 if t['pnl']>0]
losses=[t['pnl'] for t in us30 if t['pnl']<=0]
print(f"  Ganancia tipica: {sum(wins)/len(wins):.2f} (rango {min(wins):.0f} a {max(wins):.0f})")
print(f"  Perdida tipica:  {sum(losses)/len(losses):.2f} (rango {min(losses):.0f} a {max(losses):.0f})")
# casi todos los SL ~ -50, casi todos los TP ~ +125 => RR efectivo
print(f"  Ratio gan/perd absoluto: {abs(sum(wins)/len(wins))/abs(sum(losses)/len(losses)):.2f}")

print("\n-- Cuanto se necesita de WR para breakeven con ese ratio --")
aw = sum(wins)/len(wins); al = abs(sum(losses)/len(losses))
be = al/(aw+al)*100
print(f"  WR breakeven = {be:.1f}%  | WR actual = {len(wins)/len(us30)*100:.1f}%")

print("\n-- BTCUSD --")
stats(btc, "BTC todos")
for t in btc:
    print(f"   {t['open']} {t['type']:4s} pnl={t['pnl']:7.2f} pips={t['pips']:7.1f} dur={t['dur']}s")
