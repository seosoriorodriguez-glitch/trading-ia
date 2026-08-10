# -*- coding: utf-8 -*-
"""
Liquidity Sweep Reversal — logica fiel a LuxAlgo 'Liquidity Sweeps' (Only Wicks).
Pivots(len,len). Barrido bajista: high>PH and close<PH -> SHORT.
Barrido alcista: low<PL and close>PL -> LONG. SL tras la mecha, TP a RR.
Backtest US30 M5 518d, con robustez por mitades y DD real.

PARAMS arriba para tweak rapido.
"""
import sys
from pathlib import Path
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import numpy as np, pandas as pd
from strategies.fair_value_gap.backtest.data_loader import load_csv

# ---------------- PARAMS ----------------
LEN       = 5        # pivot lookback (LuxAlgo default)
RR        = 2.0
BUFFER    = 10       # pts tras la mecha del barrido para el SL
MIN_RISK  = 15       # SL minimo (pts)
MAX_RISK  = 300      # SL maximo (pts)
SPREAD    = 4        # costo real (pts)
SESSION   = None     # None = todas (Lun-Vie). o (start_h, end_h) en hora servidor
WKND_CLOSE_H = 19    # viernes cierra a esta hora UTC-equiv (servidor)
# ----------------------------------------


def run(df, LEN=LEN, RR=RR, BUFFER=BUFFER, MIN_RISK=MIN_RISK, MAX_RISK=MAX_RISK,
        SPREAD=SPREAD, SESSION=SESSION):
    h = df.high.values; l = df.low.values; c = df.close.values
    tt = pd.to_datetime(df.time.values)
    n = len(df)

    # pivots (strict): high[j] mayor que LEN velas a cada lado
    is_ph = np.zeros(n, bool); is_pl = np.zeros(n, bool)
    for j in range(LEN, n - LEN):
        if h[j] > h[j-LEN:j].max() and h[j] > h[j+1:j+LEN+1].max():
            is_ph[j] = True
        if l[j] < l[j-LEN:j].min() and l[j] < l[j+1:j+LEN+1].min():
            is_pl[j] = True

    def sess_ok(ts):
        if ts.weekday() >= 5: return False
        if ts.weekday() == 4 and ts.hour >= WKND_CLOSE_H: return False
        if SESSION is None: return True
        return SESSION[0] <= ts.hour < SESSION[1]

    aPH = []; aPL = []          # pivots activos (no barridos)
    trades = []
    open_t = None

    for i in range(LEN, n):
        # confirmar pivot en i-LEN (recien tiene LEN velas a la derecha)
        j = i - LEN
        if is_ph[j]: aPH.append(h[j])
        if is_pl[j]: aPL.append(l[j])

        # --- exits del trade abierto (barra i) ---
        if open_t is not None:
            d = open_t['dir']; sl = open_t['sl']; tp = open_t['tp']
            hit = None
            if d == 'short':
                if h[i] >= sl: hit = ('sl', sl)
                elif l[i] <= tp: hit = ('tp', tp)
            else:
                if l[i] <= sl: hit = ('sl', sl)
                elif h[i] >= tp: hit = ('tp', tp)
            if hit is not None:
                ex_r, ex_p = hit
                risk = abs(open_t['entry'] - sl)
                pnl_pts = (open_t['entry'] - ex_p) if d == 'short' else (ex_p - open_t['entry'])
                pnl_r = (pnl_pts - SPREAD) / risk if risk > 0 else 0
                trades.append({'dir': d, 'entry_time': open_t['et'], 'exit_time': tt[i],
                               'pnl_r': pnl_r, 'reason': ex_r})
                open_t = None

        # --- nuevas senales (solo si no hay trade abierto) ---
        if open_t is None and sess_ok(tt[i]):
            # bajista: high>PH and close<PH
            for ph in list(aPH):
                if h[i] > ph and c[i] < ph:
                    entry = c[i]; sl = h[i] + BUFFER; risk = sl - entry
                    if MIN_RISK <= risk <= MAX_RISK:
                        tp = entry - RR * risk
                        open_t = {'dir': 'short', 'entry': entry, 'sl': sl, 'tp': tp, 'et': tt[i]}
                        aPH.remove(ph)
                        break
                    aPH.remove(ph)
                elif c[i] > ph:
                    aPH.remove(ph)   # mitigado (cerro arriba sin barrido)
            if open_t is None:
                for pl in list(aPL):
                    if l[i] < pl and c[i] > pl:
                        entry = c[i]; sl = l[i] - BUFFER; risk = entry - sl
                        if MIN_RISK <= risk <= MAX_RISK:
                            tp = entry + RR * risk
                            open_t = {'dir': 'long', 'entry': entry, 'sl': sl, 'tp': tp, 'et': tt[i]}
                            aPL.remove(pl)
                            break
                        aPL.remove(pl)
                    elif c[i] < pl:
                        aPL.remove(pl)

    return pd.DataFrame(trades)


def metrics(td, days):
    if td.empty: return
    n = len(td); wr = (td.pnl_r > 0).mean() * 100
    gp = td[td.pnl_r > 0].pnl_r.sum(); gl = abs(td[td.pnl_r <= 0].pnl_r.sum())
    pf = gp / gl if gl > 0 else 99
    cum = td.pnl_r.cumsum(); mddr = (cum.cummax() - cum).max()
    td = td.sort_values("exit_time").reset_index(drop=True); mid = len(td)//2
    def pfh(x):
        g = x[x.pnl_r > 0].pnl_r.sum(); ll = abs(x[x.pnl_r <= 0].pnl_r.sum())
        return g/ll if ll > 0 else 99
    print(f"  Trades: {n}  ({n/days:.1f}/dia) | WR: {wr:.1f}% | PF: {pf:.2f}")
    print(f"  SumaR: {td.pnl_r.sum():+.0f}R | AvgR: {td.pnl_r.mean():+.3f} | MaxDD: {mddr*0.5:.1f}% (0.5%)")
    print(f"  PF 1a mitad: {pfh(td.iloc[:mid]):.2f} | PF 2a mitad: {pfh(td.iloc[mid:]):.2f}")
    rob = "SI" if pf > 1 and pfh(td.iloc[:mid]) > 1 and pfh(td.iloc[mid:]) > 1 else "NO"
    print(f"  >> ROBUSTA (PF>1 ambas mitades): {rob}")


if __name__ == "__main__":
    print("Cargando 518d M5...", flush=True)
    df = load_csv("data/US30_icm_M5_518d.csv")
    days = (df.time.iloc[-1] - df.time.iloc[0]).days
    print(f"  {len(df):,} velas | {days} dias\n")
    print(f"LIQUIDITY SWEEP — LuxAlgo (len={LEN}, RR={RR}, buf={BUFFER}, spread={SPREAD})")
    print("=" * 60)
    td = run(df)
    metrics(td, days)
    print("=" * 60)
