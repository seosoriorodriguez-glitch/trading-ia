# -*- coding: utf-8 -*-
"""
Muestra los FVGs activos que el bot detectaria en este momento.

Uso:
    python strategies/fair_value_gap/live/show_fvgs.py

Conecta a MT5, descarga las ultimas 350 velas M5, detecta FVGs,
aplica expiry/destruccion y muestra los que estan FRESH (operables).
"""
import sys

if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from strategies.fair_value_gap.live.data_feed   import LiveDataFeed
from strategies.fair_value_gap.live.fvg_monitor  import LiveFVGMonitor
from strategies.fair_value_gap.backtest.config   import US30_PARAMS
from strategies.fair_value_gap.backtest.risk_manager import is_session_allowed


def main():
    print("=" * 70)
    print("  FVG SCANNER — US30.cash  (parametros del bot FVG live)")
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

    monitor = LiveFVGMonitor(US30_PARAMS, feed)
    n = monitor.update_fvgs()

    # Verificar sesion
    df_m5 = feed.get_latest_candles("M5", 5)
    if df_m5 is not None and len(df_m5) > 0:
        import pandas as pd
        last_time = df_m5.iloc[-1]["time"]
        if isinstance(last_time, pd.Timestamp):
            last_time = last_time.to_pydatetime()
        in_session = is_session_allowed(last_time, US30_PARAMS)
        print(f"  Hora MT5:      {last_time.strftime('%Y-%m-%d %H:%M')} (UTC+3)")
        print(f"  En sesion:     {'SI' if in_session else 'NO (fuera de horario)'}")

    bias = monitor.trend_bias or "sin filtro"
    print(f"  Trend bias:    {bias}")
    print(f"  FVGs activos:  {n}")

    if n == 0:
        print("\n  No hay FVGs activos en este momento.")
        feed.disconnect()
        return

    fvgs = sorted(monitor.active_fvgs, key=lambda f: f.confirmed_at, reverse=True)

    bull = [f for f in fvgs if f.fvg_type == "bullish"]
    bear = [f for f in fvgs if f.fvg_type == "bearish"]

    print(f"  Bullish: {len(bull)}  |  Bearish: {len(bear)}")

    # --- Tabla ---
    print("\n" + "-" * 70)
    print(f"  {'#':<3} {'Tipo':<8} {'Zone Low':>10} {'Zone High':>10} "
          f"{'Gap pts':>8} {'Dist':>8} {'Confirmado':>18}")
    print("-" * 70)

    for i, fvg in enumerate(fvgs, 1):
        gap_size = fvg.zone_high - fvg.zone_low

        if price:
            if fvg.fvg_type == "bullish":
                dist = price - fvg.zone_high
            else:
                dist = fvg.zone_low - price
            dist_str = f"{dist:+.1f}"
        else:
            dist_str = "N/A"

        import pandas as pd
        conf = fvg.confirmed_at
        if isinstance(conf, pd.Timestamp):
            conf = conf.to_pydatetime()
        conf_str = conf.strftime("%m-%d %H:%M")

        tipo = "BULL" if fvg.fvg_type == "bullish" else "BEAR"
        marker = ""
        if price:
            if fvg.fvg_type == "bullish" and fvg.zone_low <= price <= fvg.zone_high:
                marker = " << PRECIO DENTRO"
            elif fvg.fvg_type == "bearish" and fvg.zone_low <= price <= fvg.zone_high:
                marker = " << PRECIO DENTRO"

        print(f"  {i:<3} {tipo:<8} {fvg.zone_low:>10.2f} {fvg.zone_high:>10.2f} "
              f"{gap_size:>8.1f} {dist_str:>8} {conf_str:>18}{marker}")

    print("-" * 70)

    # --- Detalle de los mas cercanos al precio ---
    if price:
        print(f"\n  FVGs mas cercanos al precio ({price:.2f}):")

        closest_bull = None
        closest_bear = None
        for fvg in fvgs:
            if fvg.fvg_type == "bullish":
                d = abs(price - fvg.zone_high)
                if closest_bull is None or d < closest_bull[1]:
                    closest_bull = (fvg, d)
            else:
                d = abs(price - fvg.zone_low)
                if closest_bear is None or d < closest_bear[1]:
                    closest_bear = (fvg, d)

        if closest_bull:
            fvg, d = closest_bull
            risk = fvg.zone_high - fvg.zone_low + US30_PARAMS["buffer_points"]
            tp_dist = risk * US30_PARAMS["target_rr"]
            print(f"\n  BULL mas cercano:")
            print(f"    Zone:  {fvg.zone_low:.2f} - {fvg.zone_high:.2f}  (gap {fvg.zone_high - fvg.zone_low:.1f} pts)")
            print(f"    Entry: {fvg.zone_high:.2f} (BUY STOP)")
            print(f"    SL:    {fvg.zone_low - US30_PARAMS['buffer_points']:.2f}")
            print(f"    TP:    {fvg.zone_high + tp_dist:.2f}")
            print(f"    Risk:  {risk:.1f} pts  |  RR 1:{US30_PARAMS['target_rr']}")
            print(f"    Dist:  {d:.1f} pts del precio")

        if closest_bear:
            fvg, d = closest_bear
            risk = fvg.zone_high - fvg.zone_low + US30_PARAMS["buffer_points"]
            tp_dist = risk * US30_PARAMS["target_rr"]
            print(f"\n  BEAR mas cercano:")
            print(f"    Zone:  {fvg.zone_low:.2f} - {fvg.zone_high:.2f}  (gap {fvg.zone_high - fvg.zone_low:.1f} pts)")
            print(f"    Entry: {fvg.zone_low:.2f} (SELL STOP)")
            print(f"    SL:    {fvg.zone_high + US30_PARAMS['buffer_points']:.2f}")
            print(f"    TP:    {fvg.zone_low - tp_dist:.2f}")
            print(f"    Risk:  {risk:.1f} pts  |  RR 1:{US30_PARAMS['target_rr']}")
            print(f"    Dist:  {d:.1f} pts del precio")

    feed.disconnect()
    print()


if __name__ == "__main__":
    main()
