# -*- coding: utf-8 -*-
"""
DIAGNOSTICO en vivo del camino de senal — dice EXACTAMENTE por que no entra.
Traza cada gate: sesion, spread, noticias, zonas activas, y si la ultima M1
cae dentro de alguna zona (condicion de entrada). Correr en el VPS.

Uso:  python strategies/order_block_gold/live/diag_signal.py
      (para DAX: copia equivalente en order_block_dax, o corre alla)
"""
import sys
from pathlib import Path
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import argparse, yaml
import pandas as pd
from strategies.order_block_gold.live.data_feed import LiveDataFeed
from strategies.order_block_gold.live.ob_monitor import LiveOBMonitor, _ob_key
from strategies.order_block_gold.live.risk_manager import FTMORiskManager
from strategies.order_block_gold.backtest.config import GOLD_PARAMS
from strategies.order_block.backtest.risk_manager import is_session_allowed

ap = argparse.ArgumentParser()
ap.add_argument("--symbol", default="XAUUSD")
ap.add_argument("--balance", type=float, default=200_000.0)
ap.add_argument("--terminal-path", default=None)
a = ap.parse_args()

feed = LiveDataFeed(a.symbol, a.terminal_path)
if not feed.connect():
    print("NO conecta."); sys.exit(1)

# --- estado de mercado ---
px = feed.get_current_price()
df5 = feed.get_latest_candles("M5", 350)
df1 = feed.get_latest_candles("M1", 30)
print(f"Simbolo: {a.symbol}  precio bid={px['bid']} ask={px['ask']} spread={px['spread']:.3f}")
print(f"M5 velas: {len(df5) if df5 is not None else 'NONE'}  |  M1 velas: {len(df1) if df1 is not None else 'NONE'}")
srv_now = pd.to_datetime(df5.iloc[-1]['time']).to_pydatetime() if df5 is not None else None
print(f"Hora ULTIMA vela M5 (servidor): {srv_now}")

# --- gate 1: sesion ---
sess_ok = is_session_allowed(srv_now, GOLD_PARAMS) if srv_now else False
print(f"\n[1] SESION permitida ahora?  {sess_ok}   (sesiones: {list(GOLD_PARAMS['sessions'].keys())})")

# --- gate 2: risk manager (spread, noticias, DD, profit) ---
cfgp = Path(__file__).parent / "config" / "ftmo_rules.yaml"
rm = FTMORiskManager(yaml.safe_load(open(cfgp, encoding="utf-8")), a.balance)
acc = feed.get_account_info(); rm.update_balance(acc['balance']); rm.open_trades = 0
can, reason = rm.can_take_trade(px)
print(f"[2] can_take_trade?  {can}   razon: {reason}")
print(f"    (spread {px['spread']:.3f} vs limite {rm.max_spread} | noticias={rm.in_news_window()} | max_spread_ok={px['spread']<=rm.max_spread})")

# --- gate 3: OBs activos ---
mon = LiveOBMonitor(GOLD_PARAMS, feed)
n = mon.update_obs()
print(f"\n[3] OBs activos: {n}")
last_m1_close = float(df1.iloc[-2]['close']) if df1 is not None and len(df1) >= 2 else None
print(f"    ultima M1 cerrada: close={last_m1_close}")
for ob in mon.active_obs:
    inside = ob.zone_low <= last_m1_close <= ob.zone_high if last_m1_close else False
    dist = ""
    if last_m1_close:
        if last_m1_close < ob.zone_low: dist = f"precio {ob.zone_low-last_m1_close:.2f} DEBAJO de la zona"
        elif last_m1_close > ob.zone_high: dist = f"precio {last_m1_close-ob.zone_high:.2f} ARRIBA de la zona"
        else: dist = "precio DENTRO"
    print(f"    {ob.ob_type:8} [{ob.zone_low:.2f}-{ob.zone_high:.2f}] size={ob.zone_high-ob.zone_low:.2f}  {'<-- M1 DENTRO (gatillaria)' if inside else dist}")

# --- gate 4: check_for_signal real ---
sig = mon.check_for_signal(balance=acc['balance'])
print(f"\n[4] check_for_signal AHORA: {'SENAL -> '+sig.direction+' entry '+str(sig.entry_price) if sig else 'None (ninguna zona con M1 dentro en sesion)'}")

print("\n" + "="*64)
if not sess_ok:
    print("VEREDICTO: FUERA DE SESION ahora. Corre esto DENTRO de 10:00-23:00 servidor.")
elif not can:
    print(f"VEREDICTO: bloqueado por risk_manager -> {reason}. Ahi esta el problema.")
elif n == 0:
    print("VEREDICTO: 0 OBs activos. La deteccion no ve zonas -> revisar data/params.")
elif sig is None:
    print("VEREDICTO: hay zonas y sesion OK, pero el precio NO esta dentro de ninguna zona ahora.")
    print("  -> Si NUNCA entra teniendo zonas frescas tocadas en sesion, hay bug. Corre varias veces.")
else:
    print("VEREDICTO: HAY SENAL AHORA. Si el bot no la toma, el bug esta en execute/loop del bot.")
feed.disconnect()
