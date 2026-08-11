# -*- coding: utf-8 -*-
"""
POST-MORTEM del oro: replica la logica EXACTA del bot (deteccion OB + entrada STOP)
sobre las velas REALES del terminal FVG, y dice para cada OB reciente por que entro o NO.

Uso (VPS):  python strategies/order_block_gold/live/postmortem.py            # ultimas 48h
            python strategies/order_block_gold/live/postmortem.py --hours 72 --tipo bull
"""
import sys, argparse
from pathlib import Path
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import MetaTrader5 as mt5
import pandas as pd
from strategies.order_block_gold.live.data_feed import LiveDataFeed
from strategies.order_block_gold.backtest.config import GOLD_PARAMS
from strategies.order_block.backtest.ob_detection import detect_order_blocks
from strategies.order_block.backtest.risk_manager import is_session_allowed

ap = argparse.ArgumentParser()
ap.add_argument("--symbol", default="XAUUSD")
ap.add_argument("--terminal-path", default=None)
ap.add_argument("--hours", type=int, default=48)
ap.add_argument("--tipo", choices=["bull", "bear", "both"], default="both")
a = ap.parse_args()

P = GOLD_PARAMS
BUF = P["buffer_points"]; MINR = P["min_risk_points"]; MAXR = P["max_risk_points"]
RR = P["target_rr"]; MINRR = P["min_rr_ratio"]; EXP = P["expiry_candles"]

feed = LiveDataFeed(a.symbol, a.terminal_path)
if not feed.connect():
    print("NO conecta."); sys.exit(1)
df5 = feed.get_latest_candles("M5", 900)
df1 = feed.get_latest_candles("M1", 5000)
feed.disconnect()
for d in (df5, df1):
    d["time"] = pd.to_datetime(d["time"])
now = df5.time.iloc[-1]
cut = now - pd.Timedelta(hours=a.hours)
print(f"Post-mortem {a.symbol} | ventana ultimas {a.hours}h (desde {cut}) | ahora {now}")
print(f"Params oro: buffer={BUF} min_risk={MINR} max_risk={MAXR} RR={RR}\n")

obs = detect_order_blocks(df5, P)
m5t = df5.time.values; m5c = df5.close.values
MAXA = P["max_active_obs"]
_m5time = df5.time.reset_index(drop=True)
_m5close = df5.close.reset_index(drop=True)


def alive_at(ob, T):
    """True si el OB esta fresco (no destruido/expirado) al tiempo T."""
    conf = pd.to_datetime(ob.confirmed_at)
    if conf > T:
        return False
    zl, zh = ob.zone_low, ob.zone_high
    bull = ob.ob_type == "bullish"
    cs = _m5close[(_m5time >= conf) & (_m5time <= T)]
    cnt = 0
    for c in cs:
        if bull and c < zl:
            return False
        if (not bull) and c > zh:
            return False
        cnt += 1
        if cnt >= EXP:
            return False
    return True


def rank_among_fresh(candidate, T):
    """Posicion (0=mas reciente) del OB entre los frescos vivos en T, y total frescos."""
    fresh = [o for o in obs if alive_at(o, T)]
    fresh.sort(key=lambda o: pd.to_datetime(o.confirmed_at), reverse=True)
    for idx, o in enumerate(fresh):
        if o is candidate:
            return idx, len(fresh)
    return None, len(fresh)


n_analizadas = 0
n_bug = 0
n_truncada = 0

for ob in obs:
    conf = pd.to_datetime(ob.confirmed_at)
    if conf < cut:
        continue
    if a.tipo != "both" and ob.ob_type != ("bullish" if a.tipo == "bull" else "bearish"):
        continue
    n_analizadas += 1
    bull = ob.ob_type == "bullish"
    zl, zh = ob.zone_low, ob.zone_high
    entry = zh if bull else zl
    sl = (zl - BUF) if bull else (zh + BUF)
    risk = abs(entry - sl)
    tag = "BULL (compra)" if bull else "BEAR (venta)"
    print(f"== {tag}  [{zl:.2f} - {zh:.2f}]  size {zh-zl:.2f}  confirmada {conf} ==")

    # 1) filtro de riesgo
    if risk < MINR or risk > MAXR:
        print(f"   RIESGO {risk:.2f} pts FUERA de [{MINR}-{MAXR}] -> FILTRADA (nunca se opera)\n")
        continue
    print(f"   entry={entry:.2f} sl={sl:.2f} risk={risk:.2f} pts -> pasa filtro")

    # 2) vida del OB: destruccion/expiry (M5 desde confirmed)
    i0 = int((df5.time >= conf).values.argmax())
    destroyed_at = None
    for j in range(i0, len(df5)):
        c = m5c[j]
        if bull and c < zl:
            destroyed_at = df5.time.iloc[j]; break
        if (not bull) and c > zh:
            destroyed_at = df5.time.iloc[j]; break
        if j - i0 >= EXP:
            destroyed_at = "EXPIRO"; break

    # 3) trigger: primera M1 que CIERRA dentro de la zona, en sesion, antes de destruirse
    end_t = destroyed_at if isinstance(destroyed_at, pd.Timestamp) else now
    m1w = df1[(df1.time >= conf) & (df1.time <= end_t)]
    trig = None
    for _, r in m1w.iterrows():
        if zl <= r.close <= zh and is_session_allowed(r.time.to_pydatetime(), P):
            trig = r; break

    if trig is None:
        why = f"destruida {destroyed_at}" if destroyed_at is not None else "sigue viva"
        print(f"   NO hubo M1 que cerrara dentro en sesion ({why}) -> no se genero senal\n")
        continue
    # 4) truncacion: estaba el OB entre los max_active_obs mas recientes al momento del trigger?
    rank, n_fresh = rank_among_fresh(ob, trig.time)
    pos = f"#{rank+1}" if rank is not None else "?"
    print(f"   M1 cerro DENTRO a {trig.time} (close {trig.close:.2f}). Habia {n_fresh} OBs frescas; esta es la {pos} mas reciente.")
    if rank is None or rank >= MAXA:
        n_truncada += 1
        print(f"   -> TRUNCADA por max_active_obs={MAXA} (el bot solo guarda las {MAXA} mas recientes) -> el bot NO la ve. Diseno, NO bug. MEJORABLE subiendo max_active_obs.\n")
        continue

    # 5) fill: el precio alcanza el borde antes de destruirse
    after = df1[(df1.time > trig.time) & (df1.time <= end_t)]
    filled_at = None
    for _, r in after.iterrows():
        if bull and r.high >= entry:
            filled_at = r.time; break
        if (not bull) and r.low <= entry:
            filled_at = r.time; break
    if filled_at:
        n_bug += 1
        print(f"   -> {'BUY' if bull else 'SELL'} STOP en {entry:.2f}, SE LLENO a {filled_at}. Estaba ACTIVA ({pos}/{MAXA}) -> DEBIO ENTRAR = *** BUG ***\n")
    else:
        d = destroyed_at if destroyed_at is not None else "no aun"
        print(f"   -> STOP en {entry:.2f} NO se lleno (precio no alcanzo el borde antes de destruirse: {d}) -> no entro (correcto)\n")

if n_analizadas == 0:
    print("No hay OBs de ese tipo confirmados en la ventana. Sube --hours.")
print("=" * 60)
print(f"RESUMEN: {n_bug} zona(s) que DEBIERON entrar y no (BUG) | {n_truncada} truncada(s) por max_active_obs (diseno)")
if n_bug > 0:
    print(">>> HAY BUG: zonas activas que debieron entrar. Hay que arreglarlo.")
elif n_truncada > 0:
    print(">>> NO es bug: las zonas viejas se truncan por max_active_obs=10. MEJORABLE subiendo ese limite y re-validando.")
else:
    print(">>> Todo correcto: las que no entraron fue por destruccion/no-fill legitimo.")
