# -*- coding: utf-8 -*-
"""
Replay DEFINITIVO: corre el CODIGO REAL del bot (LiveOBMonitor.check_for_signal) en un
momento exacto, alimentandolo con las velas historicas. Dice si el bot REALMENTE genera
la senal ahi o no — sin reimplementar nada.

Uso (VPS):  python strategies/order_block_gold/live/replay_signal.py --time "2026-08-10 15:27"
  (usa la hora del 'M1 cerro DENTRO' del postmortem + ~2 min, en hora servidor)
"""
import sys, argparse
from pathlib import Path
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import pandas as pd
from strategies.order_block_gold.live.data_feed import LiveDataFeed
from strategies.order_block_gold.live.ob_monitor import LiveOBMonitor, _ob_key
from strategies.order_block_gold.backtest.config import GOLD_PARAMS
from strategies.order_block.backtest.risk_manager import is_session_allowed

ap = argparse.ArgumentParser()
ap.add_argument("--time", required=True, help="hora servidor, ej '2026-08-10 15:27'")
ap.add_argument("--symbol", default="XAUUSD")
ap.add_argument("--terminal-path", default=None)
a = ap.parse_args()
T = pd.to_datetime(a.time)

feed = LiveDataFeed(a.symbol, a.terminal_path)
if not feed.connect():
    print("NO conecta."); sys.exit(1)
DF5 = feed.get_latest_candles("M5", 900)
DF1 = feed.get_latest_candles("M1", 8000)
feed.disconnect()
DF5["time"] = pd.to_datetime(DF5["time"])
DF1["time"] = pd.to_datetime(DF1["time"])


class MockFeed:
    """Devuelve las velas historicas hasta el tiempo T (como si fuera ese instante)."""
    def get_latest_candles(self, tf, count):
        d = DF5 if tf == "M5" else DF1
        return d[d["time"] <= T].tail(count).reset_index(drop=True)


print(f"Replay con CODIGO REAL del bot a las {T} (servidor)\n")
mon = LiveOBMonitor(GOLD_PARAMS, MockFeed())
n = mon.update_obs()
print(f"OBs activos (LiveOBMonitor.update_obs): {n}")
for ob in mon.active_obs:
    print(f"  {ob.ob_type:8} [{ob.zone_low:.2f}-{ob.zone_high:.2f}] status={ob.status} conf={ob.confirmed_at}")

# la ultima M1 cerrada que usaria check_for_signal (iloc[-2])
m1 = MockFeed().get_latest_candles("M1", 30)
candle = m1.iloc[-2]
ct = pd.to_datetime(candle["time"])
print(f"\nUltima M1 CERRADA (la que evalua el bot): {ct}  close={candle['close']:.2f}")
print(f"En sesion? {is_session_allowed(ct.to_pydatetime(), GOLD_PARAMS)}")

sig = mon.check_for_signal(balance=200_000.0)
print("\n" + "=" * 60)
if sig is not None:
    print(f">>> EL CODIGO REAL SI GENERA SENAL: {sig.direction} entry {sig.entry_price:.2f} sl {sig.sl:.2f} tp {sig.tp:.2f}")
    print("    -> La logica funciona. Si el bot en vivo NO la tomo -> es EJECUCION/TIMING")
    print("       (la orden STOP fallo o el precio ya paso el borde). Revisar el executor.")
else:
    print(">>> EL CODIGO REAL DEVUELVE None. La logica NO dispara aqui. Diagnostico:")
    for ob in mon.active_obs:
        if ob.status != "fresh":
            print(f"   OB [{ob.zone_low:.2f}-{ob.zone_high:.2f}] status={ob.status} (no fresh)")
            continue
        c = candle["close"]
        inside = ob.zone_low <= c <= ob.zone_high
        print(f"   OB {ob.ob_type} [{ob.zone_low:.2f}-{ob.zone_high:.2f}]: M1 close {c:.2f} dentro? {inside}")
    print("   -> Si alguna dice 'dentro=True' y aun asi devolvio None -> bug en check_for_signal.")
    print("   -> Si ninguna esta 'dentro' o no hay OB fresh -> la ventana/timing difiere; prueba otra hora.")
