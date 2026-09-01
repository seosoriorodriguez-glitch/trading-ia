# -*- coding: utf-8 -*-
"""
Motor de backtest FIEL A LA EJECUCION LIVE: ordenes STOP pendientes.

DIFERENCIA CON backtester.py (el canonico)
  El canonico abre el trade en el instante en que se dispara la senal, al precio
  del borde de la zona. El live NO hace eso: manda una orden STOP pendiente
  (order_executor.py:44 -> ORDER_TYPE_BUY_STOP) que solo se llena si el precio
  efectivamente llega a ese nivel.

  En un OB alcista la senal salta cuando una vela M1 CIERRA dentro de la zona;
  en ese momento el precio esta por DEBAJO de zone_high, o sea que el STOP queda
  arriba. Si el precio nunca vuelve a subir y se va al SL, en vivo NO entras.
  El canonico si entra y come la perdida completa.

  => el canonico es CONSERVADOR. Este motor deberia dar menos trades y mejor
     resultado, acercandose al ritmo real del live (2.68 trades/dia).

CICLO DE VIDA DE UNA ORDEN (igual que el bot live)
  1. Senal -> se crea PENDIENTE en signal.entry_price (no hay trade todavia)
  2. Se llena cuando el precio toca ese nivel (con gap: se llena al open, peor)
  3. Se CANCELA si el OB pasa a DESTROYED o EXPIRED antes de llenarse
     (equivalente a trading_bot.py -> _cancel_invalid_orders)
  4. Un solo pendiente por OB; un solo trade por OB
  5. max_simultaneous_trades cuenta POSICIONES ABIERTAS, no pendientes
     (risk_manager.py:92 -> `if self.open_trades >= self.max_simultaneous`)
"""
import bisect
from typing import Dict, List

import pandas as pd

from strategies.order_block.backtest.backtester import OrderBlockBacktester
from strategies.order_block.backtest.ob_detection import OBStatus, detect_order_blocks
from strategies.order_block.backtest.signals import check_entry


class OrderBlockStopBacktester(OrderBlockBacktester):
    """Igual que el canonico pero con ordenes STOP pendientes."""

    def run(self, df_higher: pd.DataFrame, df_lower: pd.DataFrame) -> pd.DataFrame:
        p = self.params
        all_obs = detect_order_blocks(df_higher, p)
        print(f"   OBs detectados: {len(all_obs)} "
              f"({sum(1 for o in all_obs if o.ob_type=='bullish')} bull / "
              f"{sum(1 for o in all_obs if o.ob_type=='bearish')} bear)")

        higher_rows = df_higher.to_dict("records")
        lower_rows = df_lower.to_dict("records")
        n_higher = len(higher_rows)
        higher_ptr = 0
        active_obs: List = []
        higher_count: Dict[int, int] = {}
        max_active = p["max_active_obs"]
        bos_lb = p.get("bos_lookback", 20)

        pendientes: List[dict] = []      # {ob, signal, dir}
        obs_con_orden = set()            # id(ob) con pendiente o trade
        self.stats_stop = {"creadas": 0, "llenadas": 0, "canceladas": 0}

        for idx, row in enumerate(lower_rows):
            t = row["time"]
            hi, lo, cl = row["high"], row["low"], row["close"]
            op = row["open"]
            prev = lower_rows[idx - 1] if idx > 0 else None
            recent = lower_rows[max(0, idx - bos_lb):idx]

            # ---- 1. avanzar TF mayor: activar / destruir / expirar OBs ----
            while higher_ptr < n_higher and higher_rows[higher_ptr]["time"] <= t:
                hrow = higher_rows[higher_ptr]
                for ob in all_obs:
                    if ob.status == OBStatus.FRESH and ob.confirmed_at <= hrow["time"]:
                        if ob not in active_obs:
                            active_obs.append(ob)
                fresh = [o for o in active_obs if o.status == OBStatus.FRESH]
                if len(fresh) > max_active:
                    for ob in sorted(fresh, key=lambda o: o.confirmed_at)[:-max_active]:
                        ob.status = OBStatus.EXPIRED
                hc = hrow["close"]
                for ob in active_obs:
                    if ob.status != OBStatus.FRESH:
                        continue
                    if ob.ob_type == "bullish" and hc < ob.zone_low:
                        ob.status = OBStatus.DESTROYED
                        continue
                    if ob.ob_type == "bearish" and hc > ob.zone_high:
                        ob.status = OBStatus.DESTROYED
                        continue
                    oid = id(ob)
                    higher_count[oid] = higher_count.get(oid, 0) + 1
                    if higher_count[oid] >= p["expiry_candles"]:
                        ob.status = OBStatus.EXPIRED
                higher_ptr += 1

            # ---- 2. cancelar pendientes cuyo OB dejo de estar fresco ----
            vivas = []
            for pd_ in pendientes:
                if pd_["ob"].status != OBStatus.FRESH:
                    obs_con_orden.discard(id(pd_["ob"]))
                    self.stats_stop["canceladas"] += 1
                else:
                    vivas.append(pd_)
            pendientes = vivas

            # ---- 3. salidas de trades abiertos (SL primero, conservador) ----
            self._active_trades = [
                tr for tr in self._active_trades
                if not self._check_trade_exit(tr, hi, lo, t)
            ]

            # ---- 4. llenado de pendientes ----
            #  BUY STOP: se llena si el maximo alcanza el nivel. Con gap de apertura
            #  por encima, se llena al open (peor precio), como en el mercado real.
            todavia = []
            for pd_ in pendientes:
                s = pd_["signal"]
                if len(self._active_trades) >= p["max_simultaneous_trades"]:
                    todavia.append(pd_)
                    continue
                if s.direction == "long":
                    if hi >= s.entry_price:
                        s.entry_price = max(s.entry_price, op) if op > s.entry_price else s.entry_price
                        s.candle_time = t
                        self._open_trade(s)
                        self.stats_stop["llenadas"] += 1
                        continue
                else:
                    if lo <= s.entry_price:
                        s.entry_price = min(s.entry_price, op) if op < s.entry_price else s.entry_price
                        s.candle_time = t
                        self._open_trade(s)
                        self.stats_stop["llenadas"] += 1
                        continue
                todavia.append(pd_)
            pendientes = todavia

            # ---- 5. nueva senal -> crear PENDIENTE (no abrir trade) ----
            if len(self._active_trades) < p["max_simultaneous_trades"]:
                candidatos = [o for o in active_obs
                              if o.status == OBStatus.FRESH and id(o) not in obs_con_orden]
                sig = check_entry(
                    candle=row, prev_candle=prev, recent_candles=recent,
                    active_obs=candidatos, n_open_trades=len(self._active_trades),
                    params=p, balance=self.balance, trend_bias=None,
                )
                if sig is not None:
                    pendientes.append({"ob": sig.ob, "signal": sig, "dir": sig.direction})
                    obs_con_orden.add(id(sig.ob))
                    self.stats_stop["creadas"] += 1

            self._equity_curve.append((t, self.balance))

        if self._active_trades and lower_rows:
            last = lower_rows[-1]
            for tr in self._active_trades:
                self._close_trade(tr, last["close"], last["time"], "end_of_data")
            self._active_trades = []

        s = self.stats_stop
        print(f"   Ordenes STOP: {s['creadas']} creadas | {s['llenadas']} llenadas "
              f"({s['llenadas']/max(1,s['creadas'])*100:.0f}%) | {s['canceladas']} canceladas")

        self._ob_stats = {"total": len(all_obs)}
        return self._build_results()
