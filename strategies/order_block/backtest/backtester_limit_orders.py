# -*- coding: utf-8 -*-
"""
Backtester con ÓRDENES LIMIT en límites de zona OB
Entry: zone_high para LONG, zone_low para SHORT
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

import pandas as pd

from .ob_detection import OrderBlock, OBStatus, detect_order_blocks
from .risk_manager import calc_pnl, is_session_allowed
from .signals import check_bos


@dataclass
class PendingOrder:
    """Orden LIMIT pendiente de ejecución"""
    order_id: int
    direction: str
    entry_price: float  # zone_high para LONG, zone_low para SHORT
    sl: float
    tp: float
    ob: OrderBlock
    created_at: datetime
    session: str
    balance_at_creation: float


@dataclass
class Trade:
    trade_id: int
    direction: str
    entry_price: float
    original_sl: float
    sl: float
    tp: float
    entry_time: datetime
    ob_zone_high: float
    ob_zone_low: float
    ob_confirmed_at: datetime
    session: str
    balance_at_entry: float
    # Rellenados al cierre
    exit_price: float = 0.0
    exit_time: Optional[datetime] = None
    exit_reason: str = ""
    pnl_usd: float = 0.0
    pnl_r: float = 0.0
    pnl_points: float = 0.0


class OrderBlockBacktesterLimitOrders:
    """Backtester con órdenes LIMIT en límites de zona"""

    def __init__(self, params: dict):
        self.params = params
        self.balance = params["initial_balance"]
        self.initial_balance = params["initial_balance"]

        self._trades: List[Trade] = []
        self._active_trades: List[Trade] = []
        self._pending_orders: List[PendingOrder] = []
        self._equity_curve: List[tuple] = []
        self._trade_counter = 0
        self._order_counter = 0

    def run(self, df_higher: pd.DataFrame, df_lower: pd.DataFrame) -> pd.DataFrame:
        """Ejecuta el backtest con órdenes LIMIT"""
        
        # Detectar OBs
        all_obs = detect_order_blocks(df_higher, self.params)
        print(f"   OBs detectados: {len(all_obs)} "
              f"({sum(1 for o in all_obs if o.ob_type=='bullish')} bull / "
              f"{sum(1 for o in all_obs if o.ob_type=='bearish')} bear)")

        # Puntero sobre df_higher
        higher_ptr = 0
        higher_rows = df_higher.to_dict("records")
        n_higher = len(higher_rows)

        active_obs: List[OrderBlock] = []
        higher_candle_count: dict = {}
        max_active = self.params["max_active_obs"]

        lower_rows = df_lower.to_dict("records")

        for idx, lower_row in enumerate(lower_rows):
            current_time = lower_row["time"]
            candle_high = lower_row["high"]
            candle_low = lower_row["low"]
            candle_close = lower_row["close"]

            # 1. Avanzar puntero TF mayor
            while higher_ptr < n_higher and higher_rows[higher_ptr]["time"] <= current_time:
                hrow = higher_rows[higher_ptr]
                htime = hrow["time"]
                hclose = hrow["close"]

                # Activar OBs confirmados
                for ob in all_obs:
                    if ob.status == OBStatus.FRESH and ob.confirmed_at <= htime:
                        if ob not in active_obs:
                            active_obs.append(ob)

                # Limitar a max_active_obs
                if len(active_obs) > max_active:
                    active_obs = sorted(active_obs, key=lambda o: o.confirmed_at, reverse=True)[:max_active]

                # Destrucción y expiry
                for ob in active_obs:
                    if ob.status != OBStatus.FRESH:
                        continue

                    # Destrucción
                    if ob.ob_type == "bullish" and hclose < ob.zone_low:
                        ob.status = OBStatus.DESTROYED
                        self._cancel_orders_for_ob(ob)
                        continue
                    if ob.ob_type == "bearish" and hclose > ob.zone_high:
                        ob.status = OBStatus.DESTROYED
                        self._cancel_orders_for_ob(ob)
                        continue

                    # Expiry
                    oid = id(ob)
                    if oid not in higher_candle_count:
                        higher_candle_count[oid] = 0
                    higher_candle_count[oid] += 1
                    if higher_candle_count[oid] >= self.params["expiry_candles"]:
                        ob.status = OBStatus.EXPIRED
                        self._cancel_orders_for_ob(ob)

                higher_ptr += 1

            # 2. Actualizar trades abiertos
            still_open = []
            for trade in self._active_trades:
                closed = self._check_trade_exit(trade, candle_high, candle_low, current_time)
                if not closed:
                    still_open.append(trade)
            self._active_trades = still_open

            # 3. Verificar ejecución de órdenes LIMIT
            self._check_pending_orders(candle_high, candle_low, current_time)

            # 4. Buscar nueva señal para crear orden LIMIT
            if not is_session_allowed(current_time, self.params):
                continue

            if len(self._active_trades) + len(self._pending_orders) >= self.params["max_simultaneous_trades"]:
                continue

            session = self._which_session(current_time)
            if session is None:
                continue

            # Construir ventana de velas M1 recientes para filtro BOS
            bos_lookback = self.params.get("bos_lookback", 20)
            recent_candles = []
            for j in range(max(0, idx - bos_lookback), idx):
                row = lower_rows[j]
                recent_candles.append({
                    "time": row["time"],
                    "open": row["open"],
                    "high": row["high"],
                    "low": row["low"],
                    "close": row["close"],
                })

            # Buscar OBs que toca la vela actual
            fresh_obs = sorted(
                [ob for ob in active_obs if ob.status == OBStatus.FRESH],
                key=lambda o: o.confirmed_at,
                reverse=True
            )

            for ob in fresh_obs:
                # Verificar si ya hay orden pendiente para este OB
                if any(po.ob == ob for po in self._pending_orders):
                    continue

                # Verificar si vela cierra DENTRO de la zona
                if ob.ob_type == "bullish":
                    if candle_close < ob.zone_low or candle_close > ob.zone_high:
                        continue
                    direction = "long"
                    entry_price = ob.zone_high  # Orden LIMIT en zone_high
                else:
                    if candle_close < ob.zone_low or candle_close > ob.zone_high:
                        continue
                    direction = "short"
                    entry_price = ob.zone_low  # Orden LIMIT en zone_low

                # ✅ FILTRO BOS (Break of Structure) - Solo si está activado
                if self.params.get("require_bos", False):
                    if not check_bos(recent_candles, direction, self.params):
                        continue

                # Calcular SL/TP
                sl, tp = self._calculate_sl_tp_limit(ob, entry_price)
                if sl is None:
                    continue

                # Crear orden pendiente
                self._create_pending_order(
                    direction=direction,
                    entry_price=entry_price,
                    sl=sl,
                    tp=tp,
                    ob=ob,
                    created_at=current_time,
                    session=session
                )
                break  # Solo una orden por vela

            # 5. Equity
            self._equity_curve.append((current_time, self.balance))

        # Cerrar trades abiertos al final
        if self._active_trades and lower_rows:
            last = lower_rows[-1]
            for trade in self._active_trades:
                self._close_trade(trade, last["close"], last["time"], "end_of_data")
            self._active_trades = []

        # Cancelar órdenes pendientes
        self._pending_orders = []

        # Crear DataFrame
        records = []
        for t in self._trades:
            records.append({
                "trade_id": t.trade_id,
                "entry_time": t.entry_time,
                "exit_time": t.exit_time,
                "direction": t.direction,
                "entry_price": t.entry_price,
                "sl": t.original_sl,
                "tp": t.tp,
                "exit_price": t.exit_price,
                "exit_reason": t.exit_reason,
                "pnl_points": round(t.pnl_points, 2),
                "pnl_usd": round(t.pnl_usd, 2),
                "pnl_r": round(t.pnl_r, 3),
                "balance": round(self.balance, 2),
                "session": t.session,
                "ob_zone_high": t.ob_zone_high,
                "ob_zone_low": t.ob_zone_low,
                "ob_confirmed_at": t.ob_confirmed_at,
            })

        df = pd.DataFrame(records)
        
        # Recalcular balance acumulado
        running = self.initial_balance
        balances = []
        for t in self._trades:
            running += t.pnl_usd
            balances.append(round(running, 2))
        if len(balances) > 0:
            df["balance"] = balances

        return df

    def _calculate_sl_tp_limit(self, ob: OrderBlock, entry_price: float) -> tuple:
        """Calcula SL/TP para orden LIMIT"""
        buf = self.params["buffer_points"]
        min_risk = self.params["min_risk_points"]
        max_risk = self.params["max_risk_points"]
        target_rr = self.params["target_rr"]

        if ob.ob_type == "bullish":
            # LONG: Entry en zone_high, SL debajo
            sl = ob.zone_low - buf
            risk_pts = abs(entry_price - sl)
            tp = entry_price + risk_pts * target_rr
        else:
            # SHORT: Entry en zone_low, SL arriba
            sl = ob.zone_high + buf
            risk_pts = abs(entry_price - sl)
            tp = entry_price - risk_pts * target_rr

        # Validar filtros
        if risk_pts < min_risk or risk_pts > max_risk:
            return None, None

        return sl, tp

    def _create_pending_order(self, direction, entry_price, sl, tp, ob, created_at, session):
        """Crea una orden LIMIT pendiente"""
        self._order_counter += 1
        order = PendingOrder(
            order_id=self._order_counter,
            direction=direction,
            entry_price=entry_price,
            sl=sl,
            tp=tp,
            ob=ob,
            created_at=created_at,
            session=session,
            balance_at_creation=self.balance
        )
        self._pending_orders.append(order)

    def _check_pending_orders(self, candle_high, candle_low, current_time):
        """Verifica si alguna orden LIMIT se ejecuta"""
        executed = []
        for order in self._pending_orders:
            # Verificar si el precio tocó el entry_price
            if order.direction == "long":
                if candle_high >= order.entry_price:
                    self._execute_order(order, current_time)
                    executed.append(order)
            else:  # short
                if candle_low <= order.entry_price:
                    self._execute_order(order, current_time)
                    executed.append(order)

        # Remover órdenes ejecutadas
        for order in executed:
            self._pending_orders.remove(order)

    def _execute_order(self, order: PendingOrder, execution_time: datetime):
        """Ejecuta una orden LIMIT"""
        self._trade_counter += 1

        # Slippage en entrada: LONG paga más, SHORT recibe menos
        slip = self.params.get("slippage_points", 0)
        if order.direction == "long":
            effective_entry = order.entry_price + slip
        else:
            effective_entry = order.entry_price - slip

        trade = Trade(
            trade_id=self._trade_counter,
            direction=order.direction,
            entry_price=effective_entry,
            original_sl=order.sl,
            sl=order.sl,
            tp=order.tp,
            entry_time=execution_time,
            ob_zone_high=order.ob.zone_high,
            ob_zone_low=order.ob.zone_low,
            ob_confirmed_at=order.ob.confirmed_at,
            session=order.session,
            balance_at_entry=self.balance
        )
        self._active_trades.append(trade)

        # Marcar OB como mitigado
        order.ob.status = OBStatus.MITIGATED

    def _cancel_orders_for_ob(self, ob: OrderBlock):
        """Cancela órdenes pendientes para un OB destruido/expirado"""
        self._pending_orders = [o for o in self._pending_orders if o.ob != ob]

    def _check_trade_exit(self, trade: Trade, candle_high: float, candle_low: float, current_time: datetime) -> bool:
        """Verifica si la vela cierra el trade"""
        if trade.direction == "long":
            if candle_low <= trade.sl:
                self._close_trade(trade, trade.sl, current_time, "sl")
                return True
            if candle_high >= trade.tp:
                self._close_trade(trade, trade.tp, current_time, "tp")
                return True
        else:  # short
            if candle_high >= trade.sl:
                self._close_trade(trade, trade.sl, current_time, "sl")
                return True
            if candle_low <= trade.tp:
                self._close_trade(trade, trade.tp, current_time, "tp")
                return True
        return False

    def _close_trade(self, trade: Trade, exit_price: float, exit_time: datetime, reason: str):
        """Cierra un trade"""
        # Slippage en salida: solo en SL (ejecucion de mercado), no en TP (orden limite)
        slip = self.params.get("slippage_points", 0)
        if reason == "sl" and slip > 0:
            effective_exit = exit_price - slip if trade.direction == "long" else exit_price + slip
        else:
            effective_exit = exit_price

        pnl_usd, pnl_r, pnl_points = calc_pnl(
            entry_price=trade.entry_price,
            exit_price=effective_exit,
            original_sl=trade.original_sl,
            entry_price_original=trade.entry_price,
            direction=trade.direction,
            balance=trade.balance_at_entry,
            params=self.params,
        )

        trade.exit_price = effective_exit
        trade.exit_time = exit_time
        trade.exit_reason = reason
        trade.pnl_usd = pnl_usd
        trade.pnl_r = pnl_r
        trade.pnl_points = pnl_points

        self.balance += trade.pnl_usd
        self._trades.append(trade)

    def _which_session(self, dt: datetime) -> Optional[str]:
        """Determina en qué sesión está el timestamp"""
        for name, sess in self.params["sessions"].items():
            h_start, m_start = sess["start"].split(":")
            h_end, m_end = sess["end"].split(":")
            sess_start = dt.replace(hour=int(h_start), minute=int(m_start), second=0, microsecond=0)
            sess_end = dt.replace(hour=int(h_end), minute=int(m_end), second=0, microsecond=0)
            if sess_start <= dt < sess_end:
                return name
        return None
