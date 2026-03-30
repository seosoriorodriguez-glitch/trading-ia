# -*- coding: utf-8 -*-
"""
Motor principal del backtest de Order Blocks.

Loop sobre cada vela del TF menor:
  1. Avanzar puntero TF mayor -> actualizar OBs (expiry, destruccion)
  2. Actualizar trades abiertos (SL/TP check — SL primero)
  3. Buscar nueva senal de entrada
  4. Registrar equity

Anti look-ahead: los OBs solo son visibles cuando current_time >= confirmed_at.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

import pandas as pd

from .ob_detection import OrderBlock, OBStatus, detect_order_blocks
from .signals import Signal, check_entry
from .risk_manager import calc_pnl


# --------------------------------------------------------------------------
# Trade
# --------------------------------------------------------------------------

@dataclass
class Trade:
    trade_id:          int
    direction:         str
    entry_price:       float
    original_sl:       float       # SL original para position sizing
    sl:                float       # SL actual (puede moverse en futuras versiones)
    tp:                float
    entry_time:        datetime
    ob_zone_high:      float
    ob_zone_low:       float
    ob_confirmed_at:   datetime
    session:           str
    balance_at_entry:  float
    # Rellenados al cierre
    exit_price:        float  = 0.0
    exit_time:         Optional[datetime] = None
    exit_reason:       str    = ""
    pnl_usd:           float  = 0.0
    pnl_r:             float  = 0.0
    pnl_points:        float  = 0.0


# --------------------------------------------------------------------------
# Backtester
# --------------------------------------------------------------------------

class OrderBlockBacktester:

    def __init__(self, params: dict):
        self.params  = params
        self.balance = params["initial_balance"]
        self.initial_balance = params["initial_balance"]

        self._trades:       List[Trade]       = []
        self._active_trades: List[Trade]      = []
        self._equity_curve: List[tuple]       = []
        self._trade_counter = 0

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

        df_higher: OHLCV del TF mayor (para detectar OBs)
        df_lower:  OHLCV del TF menor (para entradas)
        """
        # 1. Detectar todos los OBs (pre-computo con anti look-ahead via confirmed_at)
        all_obs = detect_order_blocks(df_higher, self.params)
        print(f"   OBs detectados: {len(all_obs)} "
              f"({sum(1 for o in all_obs if o.ob_type=='bullish')} bull / "
              f"{sum(1 for o in all_obs if o.ob_type=='bearish')} bear)")

        # 2. EMA de tendencia 4H (resampleada desde TF mayor)
        ema_lookup = {}   # timestamp -> ema value (solo velas 4H cerradas)
        if self.params.get("ema_trend_filter", False):
            ema_period = self.params.get("ema_4h_period", 20)
            df_4h = (
                df_higher.set_index("time")
                .resample("4h", label="left", closed="left")
                .agg({"open": "first", "high": "max", "low": "min", "close": "last"})
                .dropna()
            )
            df_4h["ema"] = df_4h["close"].ewm(span=ema_period, adjust=False).mean()
            # Guardar como lista ordenada para busqueda eficiente
            _ema_times  = df_4h.index.tolist()
            _ema_values = df_4h["ema"].tolist()
            print(f"   EMA 4H ({ema_period}): calculada sobre {len(df_4h)} velas de 4H")
        else:
            _ema_times, _ema_values = [], []

        import bisect

        # Puntero sobre df_higher para expiry y destruccion en tiempo real
        higher_ptr = 0
        higher_rows = df_higher.to_dict("records")
        n_higher = len(higher_rows)

        # OBs activos = confirmados y no finalizados
        active_obs: List[OrderBlock] = []
        # Contador de velas del TF mayor para expiry
        higher_candle_count: dict = {}  # id(ob) -> candle count en TF mayor desde confirmed

        max_active = self.params["max_active_obs"]

        lower_rows = df_lower.to_dict("records")
        bos_lb     = self.params.get("bos_lookback", 20)

        for idx, lower_row in enumerate(lower_rows):
            current_time   = lower_row["time"]
            candle_high    = lower_row["high"]
            candle_low     = lower_row["low"]
            candle_close   = lower_row["close"]
            prev_candle    = lower_rows[idx - 1] if idx > 0 else None
            recent_candles = lower_rows[max(0, idx - bos_lb): idx]

            # Trend bias: ultima vela 4H cerrada antes de current_time
            trend_bias = None
            if _ema_times:
                ema_idx = bisect.bisect_right(_ema_times, current_time) - 2
                if ema_idx >= 0:
                    trend_bias = "long" if candle_close > _ema_values[ema_idx] else "short"

            # ---- 1. Avanzar puntero TF mayor ----
            while higher_ptr < n_higher and higher_rows[higher_ptr]["time"] <= current_time:
                hrow = higher_rows[higher_ptr]
                htime = hrow["time"]

                # Activar OBs recien confirmados
                for ob in all_obs:
                    if ob.status == OBStatus.FRESH and ob.confirmed_at <= htime:
                        if ob not in active_obs:
                            active_obs.append(ob)

                # Limitar a max_active_obs mas recientes
                fresh_obs = [o for o in active_obs if o.status == OBStatus.FRESH]
                if len(fresh_obs) > max_active:
                    # Eliminar los mas antiguos (dejarlos expirar logicamente)
                    to_expire = sorted(fresh_obs, key=lambda o: o.confirmed_at)[:-max_active]
                    for ob in to_expire:
                        ob.status = OBStatus.EXPIRED

                # Destruccion y expiry sobre velas del TF mayor
                hclose = hrow["close"]
                for ob in active_obs:
                    if ob.status != OBStatus.FRESH:
                        continue

                    # Destruccion: cierre al otro lado del extremo de la zona
                    if ob.ob_type == "bullish" and hclose < ob.zone_low:
                        ob.status = OBStatus.DESTROYED
                        continue
                    if ob.ob_type == "bearish" and hclose > ob.zone_high:
                        ob.status = OBStatus.DESTROYED
                        continue

                    # Expiry por numero de velas del TF mayor
                    oid = id(ob)
                    if oid not in higher_candle_count:
                        higher_candle_count[oid] = 0
                    higher_candle_count[oid] += 1
                    if higher_candle_count[oid] >= self.params["expiry_candles"]:
                        ob.status = OBStatus.EXPIRED

                higher_ptr += 1

            # ---- 2. Actualizar trades abiertos (SL primero) ----
            still_open = []
            for trade in self._active_trades:
                closed = self._check_trade_exit(trade, candle_high, candle_low, current_time)
                if not closed:
                    still_open.append(trade)
            self._active_trades = still_open

            # ---- 3. Buscar nueva entrada ----
            fresh_active = [o for o in active_obs if o.status == OBStatus.FRESH]
            signal = check_entry(
                candle         = lower_row,
                prev_candle    = prev_candle,
                recent_candles = recent_candles,
                active_obs     = fresh_active,
                n_open_trades  = len(self._active_trades),
                params         = self.params,
                balance        = self.balance,
                trend_bias     = trend_bias,
            )

            if signal is not None:
                self._open_trade(signal)
                # Marcar el OB como mitigado (solo primer retorno)
                signal.ob.status = OBStatus.MITIGATED

            # ---- 4. Equity ----
            self._equity_curve.append((current_time, self.balance))

        # Cerrar trades abiertos al final del dataset
        if self._active_trades and lower_rows:
            last = lower_rows[-1]
            for trade in self._active_trades:
                self._close_trade(trade, last["close"], last["time"], "end_of_data")
            self._active_trades = []

        # Estadisticas de OBs
        self._ob_stats = {
            "total":     len(all_obs),
            "bullish":   sum(1 for o in all_obs if o.ob_type == "bullish"),
            "bearish":   sum(1 for o in all_obs if o.ob_type == "bearish"),
            "mitigated": sum(1 for o in all_obs if o.status == OBStatus.MITIGATED),
            "expired":   sum(1 for o in all_obs if o.status == OBStatus.EXPIRED),
            "destroyed": sum(1 for o in all_obs if o.status == OBStatus.DESTROYED),
        }

        return self._build_results()

    # ------------------------------------------------------------------
    # Apertura / cierre de trades
    # ------------------------------------------------------------------

    def _open_trade(self, signal: Signal):
        self._trade_counter += 1
        trade = Trade(
            trade_id        = self._trade_counter,
            direction       = signal.direction,
            entry_price     = signal.entry_price,
            original_sl     = signal.sl,
            sl              = signal.sl,
            tp              = signal.tp,
            entry_time      = signal.candle_time,
            ob_zone_high    = signal.ob.zone_high,
            ob_zone_low     = signal.ob.zone_low,
            ob_confirmed_at = signal.ob.confirmed_at,
            session         = signal.session,
            balance_at_entry= self.balance,
        )
        self._active_trades.append(trade)
        self._trades.append(trade)

    def _check_trade_exit(
        self,
        trade: Trade,
        candle_high: float,
        candle_low:  float,
        current_time: datetime,
    ) -> bool:
        """
        Verifica si la vela actual cierra el trade.
        Regla (conservadora): SL se verifica PRIMERO.
          LONG:  si low  <= SL  -> cerrar SL. Si no, si high >= TP -> cerrar TP.
          SHORT: si high >= SL  -> cerrar SL. Si no, si low  <= TP -> cerrar TP.
        Retorna True si el trade fue cerrado.
        """
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

    def _close_trade(
        self,
        trade:       Trade,
        exit_price:  float,
        exit_time:   datetime,
        reason:      str,
    ):
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

        self.balance += pnl_usd

    # ------------------------------------------------------------------
    # Resultados
    # ------------------------------------------------------------------

    def _build_results(self) -> pd.DataFrame:
        if not self._trades:
            return pd.DataFrame()

        records = []
        for t in self._trades:
            records.append({
                "trade_id":        t.trade_id,
                "entry_time":      t.entry_time,
                "exit_time":       t.exit_time,
                "direction":       t.direction,
                "entry_price":     t.entry_price,
                "sl":              t.original_sl,
                "tp":              t.tp,
                "exit_price":      t.exit_price,
                "exit_reason":     t.exit_reason,
                "pnl_points":      round(t.pnl_points, 2),
                "pnl_usd":         round(t.pnl_usd,    2),
                "pnl_r":           round(t.pnl_r,       3),
                "balance":         round(self.balance,  2),
                "session":         t.session,
                "ob_zone_high":    t.ob_zone_high,
                "ob_zone_low":     t.ob_zone_low,
                "ob_confirmed_at": t.ob_confirmed_at,
            })

        df = pd.DataFrame(records)
        # Recalcular balance acumulado correctamente
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
        peak     = self.initial_balance
        max_dd   = 0.0
        for b in balances:
            if b > peak:
                peak = b
            dd = (peak - b) / peak * 100
            if dd > max_dd:
                max_dd = dd

        days = max(
            (pd.to_datetime(df["exit_time"].dropna().max()) -
             pd.to_datetime(df["entry_time"].min())).days, 1
        )

        avg_win_usd = wins["pnl_usd"].mean()    if len(wins)   > 0 else 0
        avg_win_r   = wins["pnl_r"].mean()      if len(wins)   > 0 else 0
        avg_los_usd = losses["pnl_usd"].mean()  if len(losses) > 0 else 0

        longs  = df[df["direction"] == "long"]
        shorts = df[df["direction"] == "short"]
        wr_l   = (longs["pnl_usd"] > 0).mean()  * 100 if len(longs)  > 0 else 0
        wr_s   = (shorts["pnl_usd"] > 0).mean() * 100 if len(shorts) > 0 else 0

        london = df[df["session"] == "london"]
        ny     = df[df["session"] == "new_york"]
        wr_lon = (london["pnl_usd"] > 0).mean() * 100 if len(london) > 0 else 0
        wr_ny  = (ny["pnl_usd"] > 0).mean()     * 100 if len(ny)     > 0 else 0

        s = self._ob_stats

        print(f"\n{'='*44}")
        print(f" ORDER BLOCK BACKTEST - US30")
        print(f"{'='*44}")
        print(f" Timeframes: {tf_higher} (OB detection) / {tf_lower} (entries)")
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
        print(f" Bullish OBs detected: {s['bullish']}")
        print(f" Bearish OBs detected: {s['bearish']}")
        print(f" OBs traded:           {s['mitigated']}")
        print(f" OBs expired:          {s['expired']}")
        print(f" OBs destroyed:        {s['destroyed']}")
        print(f"")
        print(f" LONG trades:  {len(longs)} (WR: {wr_l:.1f}%)")
        print(f" SHORT trades: {len(shorts)} (WR: {wr_s:.1f}%)")
        print(f"")
        print(f" London trades: {len(london)} (WR: {wr_lon:.1f}%)")
        print(f" NY trades:     {len(ny)} (WR: {wr_ny:.1f}%)")
        print(f"{'='*44}\n")
