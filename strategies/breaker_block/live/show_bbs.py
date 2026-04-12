# -*- coding: utf-8 -*-
"""
Muestra los Breaker Blocks activos que el bot BB detectaria en este momento.

Uso:
    python strategies/breaker_block/live/show_bbs.py

Conecta a MT5 (instancia MT5_BREAKERBLOCKS), descarga las ultimas 350 velas M5,
detecta BBs con BB_PARAMS (sesiones London+NY, 3 consecutivas),
aplica expiry/destruccion y muestra los que estan FRESH (operables).
"""
import sys

if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import pandas as pd
from strategies.breaker_block.live.data_feed   import LiveDataFeed
from strategies.breaker_block.live.bb_monitor  import LiveBBMonitor
from strategies.breaker_block.backtest.config  import BB_PARAMS
from strategies.order_block.backtest.risk_manager import is_session_allowed


def main():
    print("=" * 70)
    print("  BB SCANNER — US30.cash  (Breaker Block bot live params)")
    print("=" * 70)

    # Usar los mismos overrides que el trading_bot
    params = dict(BB_PARAMS)
    params["sessions"] = {
        "london":   {"start": "10:00", "end": "19:00", "skip_minutes": 15},
        "new_york": {"start": "16:30", "end": "23:00", "skip_minutes": 15},
    }
    params["consecutive_candles"] = 3

    feed = LiveDataFeed("US30.cash")
    if not feed.connect():
        return

    tick = feed.get_current_price()
    if tick:
        price  = tick["bid"]
        spread = tick["spread"]
        print(f"\n  Precio actual: {price:.2f}  |  Spread: {spread:.1f} pts")
    else:
        price = None
        print("\n  No se pudo obtener precio actual")

    monitor = LiveBBMonitor(params, feed)
    n = monitor.update_bbs()

    # Verificar sesion
    df_m5 = feed.get_latest_candles("M5", 5)
    if df_m5 is not None and len(df_m5) > 0:
        last_time = df_m5.iloc[-1]["time"]
        if isinstance(last_time, pd.Timestamp):
            last_time = last_time.to_pydatetime()
        in_session = is_session_allowed(last_time, params)
        print(f"  Hora MT5:      {last_time.strftime('%Y-%m-%d %H:%M')} (UTC+3)")
        sessions_str = "London 10:15-19:00 / NY 16:45-23:00"
        print(f"  En sesion:     {'SI (' + sessions_str + ')' if in_session else 'NO (fuera de horario)'}")

    print(f"  Consec. candles: {params['consecutive_candles']}")
    print(f"  BBs activos:   {n}")

    if n == 0:
        print("\n  No hay Breaker Blocks activos en este momento.")
        feed.disconnect()
        return

    bbs = sorted(monitor.active_bbs, key=lambda b: b.destroyed_at, reverse=True)

    longs  = [b for b in bbs if b.bb_type == "long"]
    shorts = [b for b in bbs if b.bb_type == "short"]

    print(f"  Long (buy):  {len(longs)}  |  Short (sell): {len(shorts)}")

    # --- Tabla ---
    print("\n" + "-" * 78)
    print(f"  {'#':<3} {'Dir':<6} {'Zone Low':>10} {'Zone High':>10} "
          f"{'Size pts':>8} {'Dist':>8} {'Destruido':>18}")
    print("-" * 78)

    for i, bb in enumerate(bbs, 1):
        zone_size = bb.zone_high - bb.zone_low

        if price:
            if bb.bb_type == "long":
                dist = price - bb.zone_high
            else:
                dist = bb.zone_low - price
            dist_str = f"{dist:+.1f}"
        else:
            dist_str = "N/A"

        dest = bb.destroyed_at
        if isinstance(dest, pd.Timestamp):
            dest = dest.to_pydatetime()
        dest_str = dest.strftime("%m-%d %H:%M")

        tipo = "LONG" if bb.bb_type == "long" else "SHORT"
        marker = ""
        if price and bb.zone_low <= price <= bb.zone_high:
            marker = " << PRECIO DENTRO"

        print(f"  {i:<3} {tipo:<6} {bb.zone_low:>10.2f} {bb.zone_high:>10.2f} "
              f"{zone_size:>8.1f} {dist_str:>8} {dest_str:>18}{marker}")

    print("-" * 78)

    # --- Detalle de los mas cercanos al precio ---
    if price:
        print(f"\n  BBs mas cercanos al precio ({price:.2f}):")

        buf       = params["buffer_points"]
        spread_p  = params["avg_spread_points"]
        slip      = params["slippage_points"]
        target_rr = params["target_rr"]

        closest_long  = None
        closest_short = None
        for bb in bbs:
            if bb.bb_type == "long":
                d = abs(price - bb.zone_high)
                if closest_long is None or d < closest_long[1]:
                    closest_long = (bb, d)
            else:
                d = abs(price - bb.zone_low)
                if closest_short is None or d < closest_short[1]:
                    closest_short = (bb, d)

        if closest_long:
            bb, d = closest_long
            entry = bb.zone_high + spread_p + slip
            sl    = bb.zone_low - buf
            risk  = abs(entry - sl)
            tp    = entry + risk * target_rr
            print(f"\n  LONG mas cercano (OB bearish destruido → buy):")
            print(f"    Zone:  {bb.zone_low:.2f} - {bb.zone_high:.2f}  (BB {bb.zone_high - bb.zone_low:.1f} pts)")
            print(f"    Entry: {entry:.2f} (BUY STOP = zone_high + spread + slip)")
            print(f"    SL:    {sl:.2f} (zone_low - {buf} buffer)")
            print(f"    TP:    {tp:.2f}")
            print(f"    Risk:  {risk:.1f} pts  |  RR 1:{target_rr}")
            print(f"    Dist:  {d:.1f} pts del precio")

        if closest_short:
            bb, d = closest_short
            entry = bb.zone_low - spread_p - slip
            sl    = bb.zone_high + buf
            risk  = abs(entry - sl)
            tp    = entry - risk * target_rr
            print(f"\n  SHORT mas cercano (OB bullish destruido → sell):")
            print(f"    Zone:  {bb.zone_low:.2f} - {bb.zone_high:.2f}  (BB {bb.zone_high - bb.zone_low:.1f} pts)")
            print(f"    Entry: {entry:.2f} (SELL STOP = zone_low - spread - slip)")
            print(f"    SL:    {sl:.2f} (zone_high + {buf} buffer)")
            print(f"    TP:    {tp:.2f}")
            print(f"    Risk:  {risk:.1f} pts  |  RR 1:{target_rr}")
            print(f"    Dist:  {d:.1f} pts del precio")

    feed.disconnect()
    print()


if __name__ == "__main__":
    main()
