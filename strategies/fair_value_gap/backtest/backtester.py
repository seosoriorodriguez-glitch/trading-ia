# -*- coding: utf-8 -*-
"""
Motor principal del backtest de Fair Value Gap.

Loop sobre cada vela del TF menor:
  1. Avanzar puntero TF mayor -> activar/destruir/expirar FVGs
  2. Actualizar trades abiertos (SL primero, luego TP)
  3. Buscar nueva senal de entrada
  4. Registrar equity

Anti look-ahead: los FVGs solo son visibles cuando current_time >= confirmed_at.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

import pandas as pd

from .fvg_detection import FairValueGap, FVGStatus, detect_fvgs
from .signals import Signal, PendingStop, check_entry, check_conservative_trigger
from .risk_manager import calc_pnl


# --------------------------------------------------------------------------
# Trade
# --------------------------------------------------------------------------

@dataclass
class Trade:
    trade_id:           int
    direction:          str
    entry_price:        float
    original_sl:        float
    sl:                 float
    tp:                 float
    entry_time:         datetime
    fvg_zone_high:      float
    fvg_zone_low:       float
    fvg_confirmed_at:   datetime
    fvg_type:           str        # "bullish" o "bearish"
    session:            str
    entry_method:       str        # "conservative" o "aggressive"
    balance_at_entry:   float
    # Rellenados al cierre
    exit_price:         float  = 0.0
    exit_time:          Optional[datetime] = None
    exit_reason:        str    = ""
    pnl_usd:            float  = 0.0
    pnl_r:              float  = 0.0
    pnl_points:         float  = 0.0


# --------------------------------------------------------------------------
# Backtester
# --------------------------------------------------------------------------

class FVGBacktester:

    def __init__(self, params: dict):
        self.params          = params
        self.balance         = params["initial_balance"]
        self.initial_balance = params["initial_balance"]

        self._trades:         List[Trade]       = []
        self._active_trades:  List[Trade]       = []
        self._pending_stops:  List[PendingStop] = []
        self._equity_curve:   List[tuple]       = []
        self._trade_counter   = 0

        # FTMO: control de limite diario
        self._daily_loss_limit = params.get("ftmo_daily_loss_pct", 0.0) / 100.0
        self._max_dd_limit     = params.get("ftmo_max_dd_pct", 0.0) / 100.0
        self._current_day      = None       # fecha del dia en curso
        self._day_start_balance = params["initial_balance"]  # balance al inicio del dia
        self._daily_blocked    = False      # True = limite diario alcanzado, no abrir trades
        self._ftmo_violations  = []         # log de dias bloqueados
        self._strategy_paused  = False      # True = DD total superado

    # ------------------------------------------------------------------
    # Loop principal
    # ------------------------------------------------------------------

    def run(
        self,
        df_higher: pd.DataFrame,
        df_lower:  pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Ejecuta el backtest.

        df_higher: OHLCV del TF mayor (deteccion de FVGs)
        df_lower:  OHLCV del TF menor (entradas)
        """
        # 1. Detectar todos los FVGs
        all_fvgs = detect_fvgs(df_higher, self.params)
        print(f"   FVGs detectados: {len(all_fvgs)} "
              f"({sum(1 for f in all_fvgs if f.fvg_type=='bullish')} bull / "
              f"{sum(1 for f in all_fvgs if f.fvg_type=='bearish')} bear)")

        # 2. EMA 4H opcional
        ema_lookup = {}
        if self.params.get("ema_trend_filter", False):
            ema_period = self.params.get("ema_4h_period", 20)
            df_4h = (
                df_higher.set_index("time")
                .resample("4h", label="left", closed="left")
                .agg({"open": "first", "high": "max", "low": "min", "close": "last"})
                .dropna()
            )
            df_4h["ema"] = df_4h["close"].ewm(span=ema_period, adjust=False).mean()
            _ema_times  = df_4h.index.tolist()
            _ema_values = df_4h["ema"].tolist()
            print(f"   EMA 4H ({ema_period}): calculada sobre {len(df_4h)} velas")
        else:
            _ema_times, _ema_values = [], []

        import bisect

        higher_ptr   = 0
        higher_rows  = df_higher.to_dict("records")
        n_higher     = len(higher_rows)
        active_fvgs: List[FairValueGap] = []
        higher_candle_count: dict = {}
        max_active   = self.params["max_active_fvgs"]

        lower_rows = df_lower.to_dict("records")
        bos_lb     = self.params.get("bos_lookback", 20)

        for idx, lower_row in enumerate(lower_rows):
            current_time   = lower_row["time"]
            candle_high    = lower_row["high"]
            candle_low     = lower_row["low"]
            candle_close   = lower_row["close"]
            prev_candle    = lower_rows[idx - 1] if idx > 0 else None
            recent_candles = lower_rows[max(0, idx - bos_lb): idx]

            # ---- FTMO: control de dia ----
            current_day = current_time.date()
            if current_day != self._current_day:
                # Nuevo dia: resetear limite diario
                self._current_day       = current_day
                self._day_start_balance = self.balance
                self._daily_blocked     = False

            # Trend bias
            trend_bias = None
            if _ema_times:
                ema_idx = bisect.bisect_right(_ema_times, current_time) - 2
                if ema_idx >= 0:
                    trend_bias = "long" if candle_close > _ema_values[ema_idx] else "short"

            # ---- 1. Avanzar puntero TF mayor ----
            while higher_ptr < n_higher and higher_rows[higher_ptr]["time"] <= current_time:
                hrow  = higher_rows[higher_ptr]
                htime = hrow["time"]

                # Activar FVGs recien confirmados
                for fvg in all_fvgs:
                    if fvg.status == FVGStatus.FRESH and fvg.confirmed_at <= htime:
                        if fvg not in active_fvgs:
                            active_fvgs.append(fvg)

                # Limitar a max_active_fvgs mas recientes
                fresh_fvgs = [f for f in active_fvgs if f.status == FVGStatus.FRESH]
                if len(fresh_fvgs) > max_active:
                    to_expire = sorted(fresh_fvgs, key=lambda f: f.confirmed_at)[:-max_active]
                    for fvg in to_expire:
                        fvg.status = FVGStatus.EXPIRED

                # Destruccion y expiry
                hclose = hrow["close"]
                for fvg in active_fvgs:
                    if fvg.status != FVGStatus.FRESH:
                        continue

                    if fvg.fvg_type == "bullish" and hclose < fvg.zone_low:
                        fvg.status = FVGStatus.DESTROYED
                        continue
                    if fvg.fvg_type == "bearish" and hclose > fvg.zone_high:
                        fvg.status = FVGStatus.DESTROYED
                        continue

                    oid = id(fvg)
                    if oid not in higher_candle_count:
                        higher_candle_count[oid] = 0
                    higher_candle_count[oid] += 1
                    if higher_candle_count[oid] >= self.params["expiry_candles"]:
                        fvg.status = FVGStatus.EXPIRED

                higher_ptr += 1

            # ---- 2. Actualizar trades abiertos (SL primero) ----
            still_open = []
            for trade in self._active_trades:
                closed = self._check_trade_exit(trade, candle_high, candle_low, current_time)
                if not closed:
                    still_open.append(trade)
            self._active_trades = still_open

            # ---- FTMO: verificar limite diario tras cerrar trades ----
            if self._daily_loss_limit > 0 and not self._daily_blocked:
                daily_loss_pct = (self.balance - self._day_start_balance) / self.initial_balance
                if daily_loss_pct <= -self._daily_loss_limit:
                    self._daily_blocked = True
                    self._ftmo_violations.append({
                        "date":       current_day,
                        "loss_pct":   daily_loss_pct * 100,
                        "balance":    self.balance,
                    })
                    # Cerrar trades abiertos restantes al precio actual
                    for trade in self._active_trades:
                        self._close_trade(trade, candle_close, current_time, "ftmo_daily_stop")
                    self._active_trades = []
                    self._pending_stops = []

            # ---- FTMO: verificar DD total (opcional) ----
            if self._max_dd_limit > 0 and not self._strategy_paused:
                total_dd_pct = (self.initial_balance - self.balance) / self.initial_balance
                if total_dd_pct >= self._max_dd_limit:
                    self._strategy_paused = True
                    for trade in self._active_trades:
                        self._close_trade(trade, candle_close, current_time, "ftmo_max_dd_stop")
                    self._active_trades = []
                    self._pending_stops = []

            # ---- 3. Procesar pending stops + buscar nueva entrada ----
            # No abrir si el dia esta bloqueado por FTMO o la estrategia pausada
            if self._daily_blocked or self._strategy_paused:
                self._equity_curve.append((current_time, self.balance))
                continue

            entry_method = self.params.get("entry_method", "conservative")

            # 3a. Fills de pending stops (conservative)
            if entry_method == "conservative":
                still_pending = []
                for pending in self._pending_stops:
                    # Cancelar si el FVG ya no esta activo
                    if pending.fvg.status != FVGStatus.FRESH:
                        continue
                    # Comprobar fill
                    filled = False
                    if len(self._active_trades) < self.params["max_simultaneous_trades"]:
                        if pending.direction == "long" and candle_high >= pending.entry_price:
                            self._open_trade_from_pending(pending, current_time)
                            pending.fvg.status = FVGStatus.MITIGATED
                            filled = True
                        elif pending.direction == "short" and candle_low <= pending.entry_price:
                            self._open_trade_from_pending(pending, current_time)
                            pending.fvg.status = FVGStatus.MITIGATED
                            filled = True
                    if not filled:
                        still_pending.append(pending)
                self._pending_stops = still_pending

            # 3b. Detectar nuevos triggers / entradas
            fresh_active = [f for f in active_fvgs if f.status == FVGStatus.FRESH]

            if entry_method == "conservative":
                # Solo crear trigger si no hay ya un pending para ese FVG
                pending_fvg_ids = {id(p.fvg) for p in self._pending_stops}
                trigger = check_conservative_trigger(
                    candle         = lower_row,
                    prev_candle    = prev_candle,
                    recent_candles = recent_candles,
                    active_fvgs    = [f for f in fresh_active if id(f) not in pending_fvg_ids],
                    params         = self.params,
                    trend_bias     = trend_bias,
                )
                if trigger is not None:
                    self._pending_stops.append(trigger)
            else:
                signal = check_entry(
                    candle         = lower_row,
                    prev_candle    = prev_candle,
                    recent_candles = recent_candles,
                    active_fvgs    = fresh_active,
                    n_open_trades  = len(self._active_trades),
                    params         = self.params,
                    balance        = self.balance,
                    trend_bias     = trend_bias,
                )
                if signal is not None:
                    self._open_trade(signal)
                    signal.fvg.status = FVGStatus.MITIGATED

            # ---- 4. Equity ----
            self._equity_curve.append((current_time, self.balance))

        # Cerrar trades abiertos al final del dataset
        if self._active_trades and lower_rows:
            last = lower_rows[-1]
            for trade in self._active_trades:
                self._close_trade(trade, last["close"], last["time"], "end_of_data")
            self._active_trades = []

        # Estadisticas de FVGs
        self._fvg_stats = {
            "total":     len(all_fvgs),
            "bullish":   sum(1 for f in all_fvgs if f.fvg_type == "bullish"),
            "bearish":   sum(1 for f in all_fvgs if f.fvg_type == "bearish"),
            "mitigated": sum(1 for f in all_fvgs if f.status == FVGStatus.MITIGATED),
            "expired":   sum(1 for f in all_fvgs if f.status == FVGStatus.EXPIRED),
            "destroyed": sum(1 for f in all_fvgs if f.status == FVGStatus.DESTROYED),
        }

        return self._build_results()

    # ------------------------------------------------------------------
    # Apertura / cierre de trades
    # ------------------------------------------------------------------

    def _open_trade(self, signal: Signal):
        self._trade_counter += 1
        trade = Trade(
            trade_id         = self._trade_counter,
            direction        = signal.direction,
            entry_price      = signal.entry_price,
            original_sl      = signal.sl,
            sl               = signal.sl,
            tp               = signal.tp,
            entry_time       = signal.candle_time,
            fvg_zone_high    = signal.fvg.zone_high,
            fvg_zone_low     = signal.fvg.zone_low,
            fvg_confirmed_at = signal.fvg.confirmed_at,
            fvg_type         = signal.fvg.fvg_type,
            session          = signal.session,
            entry_method     = signal.entry_method,
            balance_at_entry = self.balance,
        )
        self._active_trades.append(trade)
        self._trades.append(trade)

    def _open_trade_from_pending(self, pending: PendingStop, fill_time: datetime):
        self._trade_counter += 1
        trade = Trade(
            trade_id         = self._trade_counter,
            direction        = pending.direction,
            entry_price      = pending.entry_price,
            original_sl      = pending.sl,
            sl               = pending.sl,
            tp               = pending.tp,
            entry_time       = fill_time,
            fvg_zone_high    = pending.fvg.zone_high,
            fvg_zone_low     = pending.fvg.zone_low,
            fvg_confirmed_at = pending.fvg.confirmed_at,
            fvg_type         = pending.fvg.fvg_type,
            session          = pending.session,
            entry_method     = "conservative",
            balance_at_entry = self.balance,
        )
        self._active_trades.append(trade)
        self._trades.append(trade)

    def _check_trade_exit(
        self,
        trade:        Trade,
        candle_high:  float,
        candle_low:   float,
        current_time: datetime,
    ) -> bool:
        """SL verificado primero, luego TP."""
        if trade.direction == "long":
            if candle_low <= trade.sl:
                self._close_trade(trade, trade.sl, current_time, "sl")
                return True
            if candle_high >= trade.tp:
                self._close_trade(trade, trade.tp, current_time, "tp")
                return True
        else:
            if candle_high >= trade.sl:
                self._close_trade(trade, trade.sl, current_time, "sl")
                return True
            if candle_low <= trade.tp:
                self._close_trade(trade, trade.tp, current_time, "tp")
                return True
        return False

    def _close_trade(self, trade: Trade, exit_price: float, exit_time: datetime, reason: str):
        pnl_usd, pnl_r, pnl_pts = calc_pnl(
            entry_price          = trade.entry_price,
            exit_price           = exit_price,
            original_sl          = trade.original_sl,
            entry_price_original = trade.entry_price,
            direction            = trade.direction,
            balance              = trade.balance_at_entry,
            params               = self.params,
        )
        trade.exit_price  = exit_price
        trade.exit_time   = exit_time
        trade.exit_reason = reason
        trade.pnl_usd     = pnl_usd
        trade.pnl_r       = pnl_r
        trade.pnl_points  = pnl_pts
        self.balance     += pnl_usd

    # ------------------------------------------------------------------
    # Resultados
    # ------------------------------------------------------------------

    def _build_results(self) -> pd.DataFrame:
        if not self._trades:
            return pd.DataFrame()

        records = []
        for t in self._trades:
            records.append({
                "trade_id":         t.trade_id,
                "entry_time":       t.entry_time,
                "exit_time":        t.exit_time,
                "direction":        t.direction,
                "entry_price":      t.entry_price,
                "sl":               t.original_sl,
                "tp":               t.tp,
                "exit_price":       t.exit_price,
                "exit_reason":      t.exit_reason,
                "pnl_points":       round(t.pnl_points, 2),
                "pnl_usd":          round(t.pnl_usd,    2),
                "pnl_r":            round(t.pnl_r,       3),
                "balance":          round(self.balance,  2),
                "session":          t.session,
                "entry_method":     t.entry_method,
                "fvg_type":         t.fvg_type,
                "fvg_zone_high":    t.fvg_zone_high,
                "fvg_zone_low":     t.fvg_zone_low,
                "fvg_confirmed_at": t.fvg_confirmed_at,
            })

        df = pd.DataFrame(records)
        running = self.initial_balance
        balances = []
        for t in self._trades:
            running += t.pnl_usd
            balances.append(round(running, 2))
        df["balance"] = balances

        return df

    def print_summary(self, df: pd.DataFrame, tf_higher: str, tf_lower: str):
        if df.empty:
            print("Sin trades en el periodo analizado.")
            return

        symbol = self.params.get("symbol", "US30")
        method = self.params.get("entry_method", "conservative")

        wins   = df[df["pnl_usd"] > 0]
        losses = df[df["pnl_usd"] <= 0]
        total  = len(df)
        wr     = len(wins) / total * 100

        gp = wins["pnl_usd"].sum()
        gl = abs(losses["pnl_usd"].sum())
        pf = gp / gl if gl > 0 else float("inf")

        retorno = (self.balance - self.initial_balance) / self.initial_balance * 100

        # Max drawdown
        balances = [self.initial_balance] + list(df["balance"])
        peak = self.initial_balance
        max_dd = 0.0
        for b in balances:
            if b > peak: peak = b
            dd = (peak - b) / peak * 100
            if dd > max_dd: max_dd = dd

        days = max(
            (pd.to_datetime(df["exit_time"].dropna().max()) -
             pd.to_datetime(df["entry_time"].min())).days, 1
        )

        avg_win_usd = wins["pnl_usd"].mean()   if len(wins)   > 0 else 0
        avg_win_r   = wins["pnl_r"].mean()     if len(wins)   > 0 else 0
        avg_los_usd = losses["pnl_usd"].mean() if len(losses) > 0 else 0

        longs  = df[df["direction"] == "long"]
        shorts = df[df["direction"] == "short"]
        wr_l   = (longs["pnl_usd"]  > 0).mean() * 100 if len(longs)  > 0 else 0
        wr_s   = (shorts["pnl_usd"] > 0).mean() * 100 if len(shorts) > 0 else 0

        s = self._fvg_stats

        print(f"\n{'='*48}")
        print(f" FAIR VALUE GAP BACKTEST - {symbol}")
        print(f"{'='*48}")
        print(f" Entry method: {method}")
        print(f" Timeframes:   {tf_higher} (FVG detection) / {tf_lower} (entries)")
        print(f" Period: {df['entry_time'].min()} -> {df['exit_time'].dropna().max()}")
        print(f" Days: {days}")
        print(f"")
        print(f" Total Trades:    {total}")
        print(f" Win Rate:        {wr:.1f}%")
        print(f" Profit Factor:   {pf:.2f}")
        print(f" Total Return:    {retorno:+.2f}%")
        print(f" Final Balance:   ${self.balance:,.2f}")
        print(f"")
        print(f" Avg Win:         ${avg_win_usd:,.0f} ({avg_win_r:.2f}R)")
        print(f" Avg Loss:        ${avg_los_usd:,.0f}")
        print(f" Max Drawdown:    {max_dd:.2f}%")
        print(f" Trades/Day:      {total/days:.2f}")
        print(f"")
        print(f" Bullish FVGs detected: {s['bullish']}")
        print(f" Bearish FVGs detected: {s['bearish']}")
        print(f" FVGs traded:           {s['mitigated']}")
        print(f" FVGs expired:          {s['expired']}")
        print(f" FVGs destroyed:        {s['destroyed']}")
        print(f"")
        print(f" LONG  trades: {len(longs)} (WR: {wr_l:.1f}%)")
        print(f" SHORT trades: {len(shorts)} (WR: {wr_s:.1f}%)")
        print(f"")

        # FTMO report
        daily_lim = self.params.get("ftmo_daily_loss_pct", 0.0)
        max_dd    = self.params.get("ftmo_max_dd_pct", 0.0)
        if daily_lim > 0 or max_dd > 0:
            v = self._ftmo_violations
            print(f" --- FTMO Rules ---")
            print(f" Limite diario:    {daily_lim}% del balance inicial")
            print(f" Dias bloqueados:  {len(v)} de {days} dias operados")
            if v:
                worst = min(v, key=lambda x: x['loss_pct'])
                print(f" Peor dia bloq.:   {worst['date']} ({worst['loss_pct']:.2f}%)")
            if self._strategy_paused:
                print(f" *** ESTRATEGIA PAUSADA por DD total >= {max_dd}% ***")
        print(f"{'='*48}\n")
