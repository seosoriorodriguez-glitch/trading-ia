# -*- coding: utf-8 -*-
"""
Costos reales del simbolo en un terminal MT5 (SOLO LECTURA: no envia ni cancela nada).
Sirve para correr el backtest con los costos de Darwinex (o de la cuenta de prueba) en vez de los de FTMO.

    python papel/estrategias/sr_pivot_h1/herramientas/costos_broker.py --terminal "C:\\Program Files\\MT5_BREAKERBLOCKS\\terminal64.exe" --simbolo WS30

Muestra: valor por punto, spread (ahora y mediana de los ultimos dias por hora), swap largo/corto y como se cobra,
dia del swap triple, margen de 1 lote, comision observada en los ultimos trades de la cuenta y hora del servidor.
"""
import argparse
import sys
from datetime import datetime, timedelta, timezone

import MetaTrader5 as mt5
import pandas as pd


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--terminal", default=None)
    p.add_argument("--simbolo", default="WS30")
    p.add_argument("--dias", type=int, default=20)
    a = p.parse_args()
    if not (mt5.initialize(path=a.terminal) if a.terminal else mt5.initialize()):
        sys.exit(f"no se pudo iniciar MT5: {mt5.last_error()}")
    try:
        mt5.symbol_select(a.simbolo, True)
        i = mt5.symbol_info(a.simbolo)
        if i is None:
            sys.exit(f"simbolo {a.simbolo} no encontrado")
        acc = mt5.account_info()
        tk = mt5.symbol_info_tick(a.simbolo)
        print(f"Cuenta #{acc.login} {acc.server} | {acc.currency} | apalancamiento 1:{acc.leverage}")
        print(f"\n{a.simbolo}: digitos {i.digits} | point {i.point} | tick {i.trade_tick_size} | valor tick {i.trade_tick_value}"
              f" -> valor por punto y lote segun MT5 = {i.trade_tick_value / i.trade_tick_size:.4f} {acc.currency}")
        print(f"contrato {i.trade_contract_size} | lote min {i.volume_min} paso {i.volume_step} max {i.volume_max}"
              f" | stops level {i.trade_stops_level} | freeze level {i.trade_freeze_level}")
        modos = {0: "desactivado", 1: "puntos", 2: "moneda base", 3: "moneda margen", 4: "moneda deposito",
                 5: "% anual sobre precio actual", 6: "% anual sobre precio de apertura", 7: "reabrir a cierre", 8: "reabrir a bid"}
        dias = ["dom", "lun", "mar", "mie", "jue", "vie", "sab"]
        print(f"swap largo {i.swap_long} | swap corto {i.swap_short} | modo: {modos.get(i.swap_mode, i.swap_mode)}"
              f" | triple el {dias[i.swap_rollover3days] if 0 <= i.swap_rollover3days < 7 else i.swap_rollover3days}")
        m = mt5.order_calc_margin(mt5.ORDER_TYPE_BUY, a.simbolo, 1.0, tk.ask)
        print(f"margen de 1 lote a {tk.ask}: {m}")
        print(f"\nspread ahora: {tk.ask - tk.bid:.2f} pts | hora servidor {pd.Timestamp(tk.time, unit='s')} vs UTC "
              f"{datetime.now(timezone.utc):%Y-%m-%d %H:%M}")
        r = mt5.copy_rates_from_pos(a.simbolo, mt5.TIMEFRAME_M1, 0, a.dias * 1440)
        if r is not None and len(r):
            d = pd.DataFrame(r)
            d["time"] = pd.to_datetime(d.time, unit="s")
            d["spread_pts"] = d.spread * i.point
            print(f"spread M1 (ultimos {a.dias} dias, pts): mediana {d.spread_pts.median():.2f} | p90 {d.spread_pts.quantile(.9):.2f}")
            print("mediana por hora servidor:", d.groupby(d.time.dt.hour).spread_pts.median().round(1).to_dict())
        ds = mt5.history_deals_get(datetime.now() - timedelta(days=90), datetime.now() + timedelta(days=2)) or []
        ds = [x for x in ds if x.symbol == a.simbolo and x.volume > 0]
        if ds:
            c = pd.DataFrame([{"vol": x.volume, "com": x.commission, "swap": x.swap, "entry": x.entry} for x in ds])
            print(f"\ncomision observada (90 dias, {len(c)} deals): {c.com.sum() / c.vol.sum():.4f} {acc.currency} por lote y lado")
            print(f"swap cobrado total {c.swap.sum():.2f} {acc.currency}")
        else:
            print("\nsin deals recientes para medir la comision")
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    main()
