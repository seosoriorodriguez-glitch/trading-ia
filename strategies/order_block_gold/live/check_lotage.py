# -*- coding: utf-8 -*-
"""
Valida el LOTAJE del bot ORO en el terminal REAL (MT5_FVG) — correr en el VPS.
Confirma que _usd_per_point y el volumen calculado dan el riesgo esperado ANTES
de que el bot opere. Especialmente importante en XAUUSD (algunos brokers reportan
tick_value=0 en la spec; aqui se verifica el valor real via API + order_calc_profit).

Uso (en el VPS):
    python strategies/order_block_gold/live/check_lotage.py --balance 200000
"""
import sys, argparse
from pathlib import Path
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import MetaTrader5 as mt5
from strategies.order_block_gold.live.data_feed import LiveDataFeed
from strategies.order_block_gold.live.order_executor import OrderExecutor

ap = argparse.ArgumentParser()
ap.add_argument("--symbol", default="XAUUSD")
ap.add_argument("--balance", type=float, default=200_000.0)
ap.add_argument("--terminal-path", default=None)
a = ap.parse_args()

feed = LiveDataFeed(a.symbol, a.terminal_path)
if not feed.connect():
    print("NO conecta. Abre el terminal MT5_FVG y loguea la cuenta."); sys.exit(1)

acc = feed.get_account_info()
print(f"Cuenta #{acc['login']}  Balance ${acc['balance']:,.2f}")
info = mt5.symbol_info(a.symbol)
print(f"tick_size={info.trade_tick_size}  tick_value={info.trade_tick_value}  "
      f"contract_size={info.trade_contract_size}  vol_min={info.volume_min}  vol_step={info.volume_step}")

ex = OrderExecutor(a.symbol)
upp = ex._usd_per_point()
print(f"\n_usd_per_point (usado por el bot) = {upp:.4f}   <-- ORO esperado ~100")
if upp < 10:
    print("  *** ALERTA: <10 en oro es SOSPECHOSO (deberia ser ~100). NO operar hasta revisar. ***")

risk_usd = a.balance * 0.005
tick = mt5.symbol_info_tick(a.symbol); price = tick.ask
print(f"\nRiesgo objetivo por trade (0.5%): ${risk_usd:,.0f}  |  precio {price}")
print(f"{'riesgo_pts':>10} {'lotes':>8} {'riesgo_real$':>14} {'order_calc$':>13}")
ok = True
for risk_pts in (3.0, 5.0, 10.0):
    entry = price; sl = round(price - risk_pts, 2)
    vol = ex.calculate_volume(entry, sl, risk_usd)
    real_risk = vol * risk_pts * upp
    ocp = mt5.order_calc_profit(mt5.ORDER_TYPE_BUY, a.symbol, vol, entry, sl)
    ocp = abs(ocp) if ocp else 0
    flag = "" if abs(real_risk - risk_usd) / risk_usd < 0.15 else "  <-- DESCUADRA"
    if flag: ok = False
    print(f"{risk_pts:>10.1f} {vol:>8.2f} {real_risk:>13,.0f} {ocp:>12,.0f}{flag}")

feed.disconnect()
print("\n" + ("LOTAJE CORRECTO: el riesgo real ~= objetivo en todos los casos." if ok
              else "REVISAR: algun caso descuadra — NO operar hasta ajustar _usd_per_point."))
