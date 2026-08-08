# -*- coding: utf-8 -*-
"""
Diagnostico Darwinex/FTMO: margen REAL por trade + hora del servidor.
Solo LEE (order_calc_margin no envia nada). Correr en el VPS.

  # Darwinex:
  python journal/analysis/check_darwinex.py --terminal-path "C:\\Program Files\\MT5_BREAKERBLOCKS\\terminal64.exe" --symbol WS30
  # FTMO (para comparar hora del servidor; sabemos que FTMO = UTC+3):
  python journal/analysis/check_darwinex.py --terminal-path "C:\\Program Files\\MT5_US30\\terminal64.exe" --symbol US30.cash

Muestra, para riesgos 0.5% / 0.2% / 0.1% y SL de 50/100/150 pts:
  cuantos lotes, cuanto margen exige MT5, y si CABE en el balance.
Y la hora del ultimo tick en horario del SERVIDOR (para fijar la sesion).
"""
import sys, argparse, datetime as dt
import MetaTrader5 as mt5

ap = argparse.ArgumentParser()
ap.add_argument("--terminal-path", required=True)
ap.add_argument("--symbol", required=True)
ap.add_argument("--balance", type=float, default=100_000.0)
a = ap.parse_args()

if not mt5.initialize(path=a.terminal_path):
    print("ERROR init:", mt5.last_error()); sys.exit(1)

mt5.symbol_select(a.symbol, True)
s = mt5.symbol_info(a.symbol)
t = mt5.symbol_info_tick(a.symbol)
if s is None or t is None:
    print("ERROR: simbolo no disponible:", a.symbol); mt5.shutdown(); sys.exit(1)

price = t.ask if t.ask else t.bid
usd_per_point = s.trade_tick_value / s.trade_tick_size if s.trade_tick_size else 0.0

print("=" * 64)
print(f"  {a.symbol}  @  {a.terminal_path}")
print("=" * 64)
print(f"  precio: {price}  | digits: {s.digits}  | balance: ${a.balance:,.0f}")
print(f"  USD por punto por lote: {usd_per_point}")
print(f"  margen 1.0 lote: ${mt5.order_calc_margin(mt5.ORDER_TYPE_BUY, a.symbol, 1.0, price):,.2f}")
print(f"  volume min/step/max: {s.volume_min} / {s.volume_step} / {s.volume_max}")
print("-" * 64)
print("  MARGEN REAL por trade (segun riesgo y distancia de SL):")
for risk_pct in (0.005, 0.002, 0.001):
    risk_usd = a.balance * risk_pct
    for sl_pts in (50, 100, 150):
        if usd_per_point <= 0:
            continue
        vol = round(risk_usd / (sl_pts * usd_per_point), 2)
        vol = max(s.volume_min, min(vol, s.volume_max))
        marg = mt5.order_calc_margin(mt5.ORDER_TYPE_BUY, a.symbol, vol, price)
        marg = marg if marg is not None else 0.0
        cabe = "OK" if 0 < marg <= a.balance else "NO CABE"
        print(f"    riesgo {risk_pct*100:>4.1f}%  SL {sl_pts:>3}pts  ->  {vol:>7.2f} lotes"
              f"   margen ${marg:>12,.0f}   [{cabe}]")
print("-" * 64)
print(f"  ULTIMO TICK (hora SERVIDOR): {dt.datetime.utcfromtimestamp(t.time)}")
print(f"  UTC real ahora:              {dt.datetime.utcnow()}")
print("  (FTMO server = UTC+3. Compara el tick de Darwinex vs FTMO para el offset.)")
print("=" * 64)

mt5.shutdown()
