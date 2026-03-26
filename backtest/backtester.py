"""
Backtester para la estrategia de S/R.

Simula la ejecución de la estrategia sobre datos históricos
y calcula métricas de rendimiento.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field

import pandas as pd
import numpy as np

from core.market_data import Candle, candles_from_dataframe
from core.levels import detect_zones, Zone, ZoneType
from core.signals import scan_for_signals, Signal, Direction, SignalType

logger = logging.getLogger(__name__)


@dataclass
class BacktestTrade:
    """Registro de una operación en backtest."""
    entry_time: datetime
    exit_time: Optional[datetime] = None
    instrument: str = ""
    direction: str = ""
    signal_type: str = ""
    entry_price: float = 0
    stop_loss: float = 0
    take_profit: float = 0
    exit_price: float = 0
    exit_reason: str = ""              # tp_hit, sl_hit, break_even, weekend_close
    pnl_points: float = 0
    pnl_pct: float = 0
    risk_reward_planned: float = 0
    risk_reward_actual: float = 0
    zone_touches: int = 0
    sl_miss_points: float = 0          # Puntos que faltaron para TP después de SL (si aplica)
    is_open: bool = True


@dataclass
class BacktestResult:
    """Resultados del backtest."""
    trades: List[BacktestTrade]
    initial_balance: float
    final_balance: float

    @property
    def total_trades(self) -> int:
        return len([t for t in self.trades if not t.is_open])

    @property
    def winning_trades(self) -> int:
        return len([t for t in self.trades if not t.is_open and t.pnl_points > 0])

    @property
    def losing_trades(self) -> int:
        return len([t for t in self.trades if not t.is_open and t.pnl_points < 0])

    @property
    def win_rate(self) -> float:
        if self.total_trades == 0:
            return 0
        return self.winning_trades / self.total_trades

    @property
    def profit_factor(self) -> float:
        gross_profit = sum(t.pnl_points for t in self.trades if t.pnl_points > 0)
        gross_loss = abs(sum(t.pnl_points for t in self.trades if t.pnl_points < 0))
        if gross_loss == 0:
            return float("inf") if gross_profit > 0 else 0
        return gross_profit / gross_loss

    @property
    def total_pnl_pct(self) -> float:
        if self.initial_balance == 0:
            return 0
        return (self.final_balance - self.initial_balance) / self.initial_balance

    @property
    def max_drawdown_pct(self) -> float:
        """Calcula el máximo drawdown como porcentaje."""
        if not self.trades:
            return 0

        peak = self.initial_balance
        max_dd = 0
        balance = self.initial_balance

        for t in sorted(self.trades, key=lambda x: x.entry_time):
            if t.is_open:
                continue
            balance += t.pnl_points  # Simplificación
            peak = max(peak, balance)
            dd = (peak - balance) / peak if peak > 0 else 0
            max_dd = max(max_dd, dd)

        return max_dd

    @property
    def avg_rr_actual(self) -> float:
        rrs = [t.risk_reward_actual for t in self.trades if not t.is_open and t.risk_reward_actual > 0]
        return np.mean(rrs) if rrs else 0

    @property
    def max_consecutive_losses(self) -> int:
        max_streak = 0
        current_streak = 0
        for t in sorted(self.trades, key=lambda x: x.entry_time):
            if t.is_open:
                continue
            if t.pnl_points < 0:
                current_streak += 1
                max_streak = max(max_streak, current_streak)
            else:
                current_streak = 0
        return max_streak

    def summary(self) -> str:
        """Genera resumen legible del backtest."""
        lines = [
            "=" * 60,
            "RESULTADOS DEL BACKTEST",
            "=" * 60,
            f"Balance inicial:         ${self.initial_balance:,.2f}",
            f"Balance final:           ${self.final_balance:,.2f}",
            f"Retorno total:           {self.total_pnl_pct:.2%}",
            "",
            f"Total operaciones:       {self.total_trades}",
            f"Ganadoras:               {self.winning_trades} ({self.win_rate:.1%})",
            f"Perdedoras:              {self.losing_trades}",
            f"Profit Factor:           {self.profit_factor:.2f}",
            "",
            f"Max Drawdown:            {self.max_drawdown_pct:.2%}",
            f"Max pérdidas consecutivas: {self.max_consecutive_losses}",
            f"R:R promedio real:       {self.avg_rr_actual:.2f}",
            "",
            "--- Por tipo de señal ---",
        ]

        for st in SignalType:
            trades_of_type = [t for t in self.trades if t.signal_type == st.value and not t.is_open]
            if trades_of_type:
                wins = sum(1 for t in trades_of_type if t.pnl_points > 0)
                wr = wins / len(trades_of_type) if trades_of_type else 0
                lines.append(f"  {st.value:25s}: {len(trades_of_type):3d} trades, WR: {wr:.1%}")

        lines.append("=" * 60)

        # FTMO compliance check
        lines.append("")
        lines.append("--- Compliance FTMO ---")
        dd_ok = self.max_drawdown_pct < 0.08
        lines.append(f"  Max DD < 8%:  {'✅ PASS' if dd_ok else '❌ FAIL'} ({self.max_drawdown_pct:.2%})")

        return "\n".join(lines)

    def to_dataframe(self) -> pd.DataFrame:
        """Convierte trades a DataFrame para análisis."""
        records = []
        for t in self.trades:
            if t.is_open:
                continue
            records.append({
                "entry_time": t.entry_time,
                "exit_time": t.exit_time,
                "instrument": t.instrument,
                "direction": t.direction,
                "signal_type": t.signal_type,
                "entry_price": t.entry_price,
                "stop_loss": t.stop_loss,
                "take_profit": t.take_profit,
                "exit_price": t.exit_price,
                "exit_reason": t.exit_reason,
                "pnl_points": t.pnl_points,
                "pnl_pct": t.pnl_pct,
                "rr_planned": t.risk_reward_planned,
                "rr_actual": t.risk_reward_actual,
                "zone_touches": t.zone_touches,
                "sl_miss_points": t.sl_miss_points,
            })
        return pd.DataFrame(records)


class Backtester:
    """Motor de backtesting."""

    def __init__(self, config: dict, instrument_config: dict, instrument_name: str):
        self.config = config
        self.instrument_config = instrument_config
        self.instrument_name = instrument_name

    def run(
        self,
        candles_h4: List[Candle],
        candles_h1: List[Candle],
        initial_balance: float = 100_000,
    ) -> BacktestResult:
        """
        Ejecuta el backtest sobre datos históricos.

        Args:
            candles_h4: Datos H4 completos (para detección de zonas)
            candles_h1: Datos H1 completos (para señales y simulación)
            initial_balance: Balance inicial simulado

        Returns:
            BacktestResult con todas las operaciones y métricas
        """
        zone_config = self.config["zone_detection"]
        entry_config = self.config["entry"]
        tp_config = self.config["take_profit"]
        be_config = self.config.get("break_even", {})
        sizing_config = self.config["position_sizing"]

        balance = initial_balance
        trades: List[BacktestTrade] = []
        open_trades: List[BacktestTrade] = []

        # Índice de velas H4 por timestamp para lookback
        h4_by_time = {c.time: i for i, c in enumerate(candles_h4)}

        logger.info(f"Iniciando backtest: {len(candles_h1)} velas H1, "
                    f"{len(candles_h4)} velas H4")

        # Iterar por cada vela H1 (simulando el cierre de cada vela)
        lookback_h4 = zone_config["lookback_candles"]

        for h1_idx in range(2, len(candles_h1)):
            current_h1 = candles_h1[h1_idx]
            prev_h1 = candles_h1[h1_idx - 1]

            # --- 1. Gestionar posiciones abiertas ---
            for trade in open_trades[:]:
                # ¿SL hit?
                if trade.direction == "LONG":
                    if current_h1.low <= trade.stop_loss:
                        trade.exit_price = trade.stop_loss
                        trade.exit_time = current_h1.time
                        trade.exit_reason = "sl_hit"
                        trade.pnl_points = trade.exit_price - trade.entry_price
                        trade.is_open = False
                        open_trades.remove(trade)
                        continue

                    # ¿TP hit?
                    if current_h1.high >= trade.take_profit:
                        trade.exit_price = trade.take_profit
                        trade.exit_time = current_h1.time
                        trade.exit_reason = "tp_hit"
                        trade.pnl_points = trade.exit_price - trade.entry_price
                        trade.is_open = False
                        open_trades.remove(trade)
                        continue

                    # Break even check
                    if be_config.get("enabled", False):
                        trigger_rr = be_config.get("trigger_rr", 1.0)
                        offset = be_config.get("offset_points", 10)
                        risk = trade.entry_price - trade.stop_loss
                        if risk > 0 and current_h1.high >= trade.entry_price + (risk * trigger_rr):
                            new_sl = trade.entry_price + offset
                            if new_sl > trade.stop_loss:
                                trade.stop_loss = new_sl

                else:  # SHORT
                    if current_h1.high >= trade.stop_loss:
                        trade.exit_price = trade.stop_loss
                        trade.exit_time = current_h1.time
                        trade.exit_reason = "sl_hit"
                        trade.pnl_points = trade.entry_price - trade.exit_price
                        trade.is_open = False
                        open_trades.remove(trade)
                        continue

                    if current_h1.low <= trade.take_profit:
                        trade.exit_price = trade.take_profit
                        trade.exit_time = current_h1.time
                        trade.exit_reason = "tp_hit"
                        trade.pnl_points = trade.entry_price - trade.exit_price
                        trade.is_open = False
                        open_trades.remove(trade)
                        continue

                    if be_config.get("enabled", False):
                        trigger_rr = be_config.get("trigger_rr", 1.0)
                        offset = be_config.get("offset_points", 10)
                        risk = trade.stop_loss - trade.entry_price
                        if risk > 0 and current_h1.low <= trade.entry_price - (risk * trigger_rr):
                            new_sl = trade.entry_price - offset
                            if new_sl < trade.stop_loss:
                                trade.stop_loss = new_sl

            # --- 2. ¿Capacidad para nuevas operaciones? ---
            max_trades = sizing_config["max_simultaneous_trades"]
            if len(open_trades) >= max_trades:
                continue

            # --- 3. Detectar zonas (usar velas H4 hasta el momento actual) ---
            # Encontrar las H4 disponibles hasta esta H1
            relevant_h4 = [c for c in candles_h4 if c.time <= current_h1.time]
            if len(relevant_h4) < lookback_h4:
                h4_window = relevant_h4
            else:
                h4_window = relevant_h4[-lookback_h4:]

            if len(h4_window) < 10:
                continue

            zones = detect_zones(h4_window, zone_config, self.instrument_config)

            if not zones:
                continue

            # --- 4. Buscar señales ---
            h1_window = candles_h1[max(0, h1_idx - 1):h1_idx + 1]
            
            # Obtener configuración de filtro de tendencia
            trend_config = self.config.get("filters", {}).get("trend", {})

            signals = scan_for_signals(
                candles_h1=h1_window,
                zones=zones,
                all_zones=zones,
                instrument=self.instrument_name,
                instrument_config=self.instrument_config,
                entry_config=entry_config,
                tp_config=tp_config,
                candles_h4=relevant_h4,  # Pasar TODAS las H4 hasta ahora, no solo la ventana
                trend_config=trend_config,
            )

            if not signals:
                continue

            # Tomar la mejor señal
            signal = signals[0]

            # Verificar que no estemos ya en una operación en la misma zona
            already_in_zone = any(
                t.stop_loss == signal.stop_loss and t.direction == signal.direction.value
                for t in open_trades
            )
            if already_in_zone:
                continue

            # --- 5. Crear trade ---
            trade = BacktestTrade(
                entry_time=current_h1.time,
                instrument=self.instrument_name,
                direction=signal.direction.value,
                signal_type=signal.signal_type.value,
                entry_price=signal.entry_price,
                stop_loss=signal.stop_loss,
                take_profit=signal.take_profit,
                risk_reward_planned=signal.risk_reward_ratio,
                zone_touches=signal.zone.touches,
                is_open=True,
            )

            trades.append(trade)
            open_trades.append(trade)

            logger.debug(f"Trade abierto: {trade.direction} @ {trade.entry_price:.1f} "
                        f"({trade.signal_type}) — {current_h1.time}")

        # --- Cerrar trades abiertos al final ---
        last_price = candles_h1[-1].close if candles_h1 else 0
        for trade in open_trades:
            trade.exit_price = last_price
            trade.exit_time = candles_h1[-1].time if candles_h1 else None
            trade.exit_reason = "backtest_end"
            if trade.direction == "LONG":
                trade.pnl_points = trade.exit_price - trade.entry_price
            else:
                trade.pnl_points = trade.entry_price - trade.exit_price
            trade.is_open = False

        # --- Calcular métricas finales ---
        for trade in trades:
            if trade.direction == "LONG":
                risk = trade.entry_price - trade.stop_loss
            else:
                risk = trade.stop_loss - trade.entry_price

            if risk > 0:
                trade.risk_reward_actual = trade.pnl_points / risk
                trade.pnl_pct = (trade.pnl_points / trade.entry_price) * 100

        # Balance final (simplificado: sumando puntos × sizing)
        risk_per_trade = initial_balance * sizing_config["risk_per_trade_pct"]
        for trade in trades:
            if trade.direction == "LONG":
                planned_risk_pts = trade.entry_price - trade.stop_loss
            else:
                planned_risk_pts = trade.stop_loss - trade.entry_price
            if planned_risk_pts > 0:
                pnl_usd = (trade.pnl_points / planned_risk_pts) * risk_per_trade
                balance += pnl_usd

        result = BacktestResult(
            trades=trades,
            initial_balance=initial_balance,
            final_balance=balance,
        )

        logger.info(f"\n{result.summary()}")

        return result
