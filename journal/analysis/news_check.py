# -*- coding: utf-8 -*-
# Cuenta cuantas operaciones habrian caido en la ventana de noticias.
# Hora CSV = servidor (UTC+3). ET (Nueva York, EDT verano) = servidor - 7.
import csv
from datetime import datetime, timedelta

trades = {}  # ticket -> (open_dt_server, tipo, pnl)

# PnL de los tickets del suplemento que caen en ventanas (de los CSV 7 y 8)
supp_pnl = {
    "158849392": -2.97, "143138252": -51.63, "144750737": 125.23,
    "145213676": -50.60,
}

def load(path, has_full):
    with open(path, encoding='utf-8') as f:
        for r in csv.DictReader(f):
            sym = r.get('Simbolo', 'US30.cash')
            if sym != 'US30.cash':
                continue
            tk = r['Ticket']
            dt = datetime.strptime(r['Abrir'], '%Y-%m-%d %H:%M:%S')
            if has_full:
                pnl = float(r['Beneficio']) + float(r['Swap']) + float(r['Comisiones'])
            else:
                pnl = supp_pnl.get(tk, None)
            trades[tk] = (dt, r['Tipo'], pnl)

load(r'journal/analysis/trades_raw.csv', True)
load(r'journal/analysis/supplement.csv', False)

rows = list(trades.values())
n = len(rows)
et = [(o + timedelta(hours=-7), t, p) for o, t, p in rows]   # hora ET de apertura

def in_window(dt, lo, hi):
    m = dt.hour * 60 + dt.minute
    return lo <= m <= hi

# ventanas en ET (minutos desde medianoche)
w_830   = (8*60+27, 8*60+33)   # 08:27-08:33 (solo 8:30)
w_adp   = (8*60+13, 8*60+17)   # 08:13-08:17 (ADP)
w_full  = (8*60+12, 8*60+33)   # 08:12-08:33 (ADP + 8:30, recomendada)

print(f"Total operaciones analizadas (US30, ambos challenges): {n}")
print(f"Rango: {min(o for o,_,_ in rows).date()} a {max(o for o,_,_ in rows).date()}")
print()

def count(win, label):
    hits = [(dt, t, p) for dt, t, p in et if in_window(dt, *win)]
    wins = [h for h in hits if h[2] is not None and h[2] > 0]
    loss = [h for h in hits if h[2] is not None and h[2] <= 0]
    tot  = sum(h[2] for h in hits if h[2] is not None)
    print(f"{label}")
    print(f"   Bloqueadas: {len(hits)} de {n}  ({len(hits)/n*100:.1f}%)  |  "
          f"{len(wins)}W / {len(loss)}L  |  PnL bloqueado: {tot:+.2f}")
    for dt, t, p in sorted(hits):
        tag = "GANO " if (p is not None and p > 0) else "PERDIO"
        print(f"      {dt.strftime('%Y-%m-%d %H:%M')} ET  {t:4s}  {tag}  {p:+.2f}")
    print()

count(w_830,  "VENTANA A: 08:27-08:33 ET (solo noticias de las 8:30)")
count(w_full, "VENTANA C: 08:12-08:33 ET (ADP + 8:30)")
