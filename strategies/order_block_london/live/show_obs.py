# -*- coding: utf-8 -*-
"""
Muestra los Order Blocks activos que el Bot 2 London detectaria en este momento.

Uso:
    python strategies/order_block_london/live/show_obs.py

Conecta a MT5 (instancia MT5_BTCUSD), descarga las ultimas 350 velas M5,
detecta OBs con LONDON_PARAMS, aplica expiry/destruccion y muestra los FRESH.
"""
import sys

if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from strategies.order_block_london.live.data_feed   import LiveDataFeed
from strategies.order_block_london.live.ob_monitor   import LiveOBMonitor
from strategies.order_block_london.backtest.config   import LONDON_PARAMS
from strategies.order_block.backtest.risk_manager    import is_session_allowed


def main():
    print("=" * 70)
    print("  OB SCANNER — Bot 2 London  US30.cash  (LONDON_PARAMS)")
    print("=" * 70)

    feed = LiveDataFeed("US30.cash")
    if not feed.connect():
        return

    tick = feed.get_current_price()
    if tick:
        price = tick["bid"]
        spread = tick["spread"]
        print(f"\n  Precio actual: {price:.2f}  |  Spread: {spread:.1f} pts")
    else:
        price = None
        print("\n  No se pudo obtener precio actual")

    monitor = LiveOBMonitor(LONDON_PARAMS, feed)
    n = monitor.update_obs()

    # Verificar sesion
    import pandas as pd
    df_m5 = feed.get_latest_candles("M5", 5)
    if df_m5 is not None and len(df_m5) > 0:
        last_time = df_m5.iloc[-1]["time"]
        if isinstance(last_time, pd.Timestamp):
            last_time = last_time.to_pydatetime()
        in_session = is_session_allowed(last_time, LONDON_PARAMS)
        print(f"  Hora MT5:      {last_time.strftime('%Y-%m-%d %H:%M')} (UTC+3)")
        print(f"  En sesion:     {'SI (London 10:15-19:00)' if in_session else 'NO (fuera de horario)'}")

    bias = monitor.trend_bias or "sin filtro"
    print(f"  Trend bias:    {bias}")
    print(f"  OBs activos:   {n}")

    if n == 0:
        print("\n  No hay OBs activos en este momento.")
        feed.disconnect()
        return

    obs = sorted(monitor.active_obs, key=lambda o: o.confirmed_at, reverse=True)

    bull = [o for o in obs if o.ob_type == "bullish"]
    bear = [o for o in obs if o.ob_type == "bearish"]

    print(f"  Bullish: {len(bull)}  |  Bearish: {len(bear)}")

    # --- Tabla ---
    print("\n" + "-" * 70)
    print(f"  {'#':<3} {'Tipo':<8} {'Zone Low':>10} {'Zone High':>10} "
          f"{'Size pts':>8} {'Dist':>8} {'Confirmado':>18}")
    print("-" * 70)

    for i, ob in enumerate(obs, 1):
        zone_size = ob.zone_high - ob.zone_low

        if price:
            if ob.ob_type == "bullish":
                dist = price - ob.zone_high
            else:
                dist = ob.zone_low - price
            dist_str = f"{dist:+.1f}"
        else:
            dist_str = "N/A"

        conf = ob.confirmed_at
        if isinstance(conf, pd.Timestamp):
            conf = conf.to_pydatetime()
        conf_str = conf.strftime("%m-%d %H:%M")

        tipo = "BULL" if ob.ob_type == "bullish" else "BEAR"
        marker = ""
        if price and ob.zone_low <= price <= ob.zone_high:
            marker = " << PRECIO DENTRO"

        print(f"  {i:<3} {tipo:<8} {ob.zone_low:>10.2f} {ob.zone_high:>10.2f} "
              f"{zone_size:>8.1f} {dist_str:>8} {conf_str:>18}{marker}")

    print("-" * 70)

    # --- Detalle de los mas cercanos ---
    if price:
        print(f"\n  OBs mas cercanos al precio ({price:.2f}):")

        buf       = LONDON_PARAMS["buffer_points"]
        target_rr = LONDON_PARAMS["target_rr"]

        closest_bull = None
        closest_bear = None
        for ob in obs:
            if ob.ob_type == "bullish":
                d = abs(price - ob.zone_high)
                if closest_bull is None or d < closest_bull[1]:
                    closest_bull = (ob, d)
            else:
                d = abs(price - ob.zone_low)
                if closest_bear is None or d < closest_bear[1]:
                    closest_bear = (ob, d)

        if closest_bull:
            ob, d = closest_bull
            risk = ob.zone_high - ob.zone_low + buf
            tp_dist = risk * target_rr
            print(f"\n  BULL mas cercano:")
            print(f"    Zone:  {ob.zone_low:.2f} - {ob.zone_high:.2f}  (OB {ob.zone_high - ob.zone_low:.1f} pts)")
            print(f"    Entry: {ob.zone_high:.2f} (BUY STOP)")
            print(f"    SL:    {ob.zone_low - buf:.2f}")
            print(f"    TP:    {ob.zone_high + tp_dist:.2f}")
            print(f"    Risk:  {risk:.1f} pts  |  RR 1:{target_rr}")
            print(f"    Dist:  {d:.1f} pts del precio")

        if closest_bear:
            ob, d = closest_bear
            risk = ob.zone_high - ob.zone_low + buf
            tp_dist = risk * target_rr
            print(f"\n  BEAR mas cercano:")
            print(f"    Zone:  {ob.zone_low:.2f} - {ob.zone_high:.2f}  (OB {ob.zone_high - ob.zone_low:.1f} pts)")
            print(f"    Entry: {ob.zone_low:.2f} (SELL STOP)")
            print(f"    SL:    {ob.zone_high + buf:.2f}")
            print(f"    TP:    {ob.zone_low - tp_dist:.2f}")
            print(f"    Risk:  {risk:.1f} pts  |  RR 1:{target_rr}")
            print(f"    Dist:  {d:.1f} pts del precio")

    feed.disconnect()
    print()


if __name__ == "__main__":
    main()
