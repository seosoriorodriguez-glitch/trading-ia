# -*- coding: utf-8 -*-
# Trades POST-cambio (apertura >= 2026-06-02). Hora servidor UTC+3. NY = srv - 7.
data = [
# fecha hora(srv) tipo pnl
("06-12","16:46","buy",  120.48),
("06-12","16:37","buy",  -64.36),
("06-12","10:35","buy",  127.94),
("06-11","16:08","buy",  125.18),
("06-11","16:53","sell", -50.46),
("06-11","15:33","buy",  129.89),
("06-11","15:20","buy",  -53.46),
("06-10","12:27","sell", 124.50),
("06-10","13:49","sell", 127.62),
("06-10","12:45","buy",  -51.73),
("06-10","10:26","buy",  -52.14),
("06-10","10:20","buy",  -50.38),
("06-09","13:14","buy",  111.52),
("06-09","10:17","buy",  124.67),
("06-09","12:39","sell", 124.93),
("06-09","11:07","buy",  126.51),
("06-08","12:10","buy",  129.85),
("06-08","12:37","sell", -50.77),
("06-05","12:57","sell",  -4.85),
("06-04","10:56","sell", -51.96),
("06-03","16:38","sell", 123.84),
("06-03","16:36","sell", 124.80),
("06-03","14:28","sell", 125.36),
("06-03","15:06","buy",  -50.35),
("06-02","14:50","buy",  -56.60),
("06-02","13:09","buy",  -51.85),
]

n=len(data); tot=sum(d[3] for d in data)
wins=[d for d in data if d[3]>0]; losses=[d for d in data if d[3]<=0]
gw=sum(d[3] for d in wins); gl=sum(d[3] for d in losses)
print("="*60)
print("RESULTADO POST-CAMBIO (2-12 jun, 26 trades)")
print("="*60)
print(f"Trades: {n}")
print(f"Win Rate: {len(wins)/n*100:.1f}%  ({len(wins)}W / {len(losses)}L)")
print(f"PnL total: {tot:+.2f} USD")
print(f"Profit Factor: {gw/abs(gl):.2f}")
print(f"Ganancia media: {gw/len(wins):+.2f} | Perdida media: {gl/len(losses):+.2f}")
print(f"Expectativa/trade: {tot/n:+.2f}")

# Verificar corte horario: ninguna apertura >= 17:00 servidor (= 10:00 NY)
print("\n"+"="*60)
print("VERIFICACION DEL CORTE 10:00 NY (17:00 servidor)")
print("="*60)
srv_hours=[int(d[1].split(":")[0]) for d in data]
late=[d for d in data if int(d[1].split(":")[0])>=17]
print(f"Apertura mas tardia (servidor): {max(d[1] for d in data)}")
print(f"Apertura mas tardia (NY):       {max(int(d[1].split(':')[0])-7 for d in data):02d}:xx")
print(f"Trades abiertos >= 17:00 srv (post-corte): {len(late)}  {'<-- CORTE OK' if not late else '<-- FALLO'}")

# distribucion por hora NY
print("\nPor hora de apertura (NY):")
from collections import defaultdict
by=defaultdict(list)
for d in data:
    ny=int(d[1].split(":")[0])-7
    by[ny].append(d[3])
for ny in sorted(by):
    v=by[ny]; w=[x for x in v if x>0]
    print(f"  NY {ny:02d}:00 -> n={len(v):2d}  WR={len(w)/len(v)*100:5.1f}%  PnL={sum(v):+8.2f}")

# por direccion
print("\nPor direccion:")
for t in ("buy","sell"):
    v=[d[3] for d in data if d[2]==t]; w=[x for x in v if x>0]
    print(f"  {t.upper():4s} -> n={len(v):2d}  WR={len(w)/len(v)*100:5.1f}%  PnL={sum(v):+8.2f}")

# equity
print("\nEquity acumulada (orden cronologico inverso del CSV -> reordenar):")
chron=sorted(data, key=lambda d:(d[0],d[1]))
eq=0;pk=0;dd=0
for d in chron:
    eq+=d[3]; pk=max(pk,eq); dd=min(dd,eq-pk)
print(f"  PnL final: {eq:+.2f} | maxDD intratrade: {dd:+.2f}")
