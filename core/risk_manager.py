"""
Gestión de Riesgo y Compliance FTMO.

Este módulo es el GUARDARRAÍL del bot. Tiene la última palabra
sobre si una operación se puede tomar o no.
"""

import logging
from datetime import datetime, time
from typing import Dict, List, Optional
from dataclasses import dataclass, field

from core.signals import Signal, Direction

logger = logging.getLogger(__name__)


@dataclass
class DailyState:
    """Estado diario para tracking de drawdown."""
    date: str
    starting_balance: float
    realized_pnl: float = 0.0
    floating_pnl: float = 0.0
    trades_opened: int = 0
    trades_closed: int = 0
    server_requests: int = 0
    is_blocked: bool = False
    block_reason: str = ""

    @property
    def total_pnl(self) -> float:
        return self.realized_pnl + self.floating_pnl

    @property
    def daily_drawdown_pct(self) -> float:
        if self.starting_balance == 0:
            return 0
        return abs(min(0, self.total_pnl)) / self.starting_balance


@dataclass
class AccountState:
    """Estado global de la cuenta."""
    initial_balance: float             # Balance al inicio del Challenge
    current_balance: float
    current_equity: float
    open_positions: int = 0
    total_risk_exposed_pct: float = 0
    daily_state: Optional[DailyState] = None
    is_globally_blocked: bool = False
    block_reason: str = ""

    @property
    def total_drawdown_pct(self) -> float:
        if self.initial_balance == 0:
            return 0
        return abs(min(0, self.current_equity - self.initial_balance)) / self.initial_balance


class RiskManager:
    """
    Gestor de riesgo centralizado.
    Verifica todas las condiciones antes de permitir operaciones.
    """

    def __init__(self, ftmo_config: dict, sizing_config: dict):
        self.ftmo = ftmo_config
        self.sizing = sizing_config
        self.account = AccountState(
            initial_balance=0,
            current_balance=0,
            current_equity=0,
        )
        self._trade_log: List[Dict] = []

    def initialize(self, initial_balance: float, current_balance: float, current_equity: float):
        """Inicializa el estado de la cuenta."""
        self.account.initial_balance = initial_balance
        self.account.current_balance = current_balance
        self.account.current_equity = current_equity

        today = datetime.now().strftime("%Y-%m-%d")
        self.account.daily_state = DailyState(
            date=today,
            starting_balance=current_balance,
        )
        logger.info(f"RiskManager inicializado — Balance inicial: {initial_balance}, "
                    f"Balance actual: {current_balance}, Equity: {current_equity}")

    def update_state(self, balance: float, equity: float, floating_pnl: float,
                     open_positions: int, total_risk_pct: float):
        """Actualiza el estado de la cuenta (llamar en cada ciclo del bot)."""
        self.account.current_balance = balance
        self.account.current_equity = equity
        self.account.open_positions = open_positions
        self.account.total_risk_exposed_pct = total_risk_pct

        if self.account.daily_state:
            self.account.daily_state.floating_pnl = floating_pnl

        # Verificar drawdown diario
        self._check_daily_drawdown()

        # Verificar drawdown total
        self._check_total_drawdown()

    def new_day(self, current_balance: float):
        """Resetea el estado diario (llamar a medianoche CET)."""
        today = datetime.now().strftime("%Y-%m-%d")
        self.account.daily_state = DailyState(
            date=today,
            starting_balance=current_balance,
        )
        logger.info(f"Nuevo día: {today} — Balance de inicio: {current_balance}")

    def _check_daily_drawdown(self):
        """Verifica si se alcanzó el límite de drawdown diario."""
        if not self.account.daily_state:
            return

        daily_dd = self.account.daily_state.daily_drawdown_pct
        limit = self.ftmo["max_daily_loss_pct"]

        if daily_dd >= limit:
            self.account.daily_state.is_blocked = True
            self.account.daily_state.block_reason = (
                f"Drawdown diario {daily_dd:.2%} >= límite {limit:.2%}"
            )
            logger.critical(f"⚠️ LÍMITE DIARIO ALCANZADO: {daily_dd:.2%}")

    def _check_total_drawdown(self):
        """Verifica si se alcanzó el límite de drawdown total."""
        total_dd = self.account.total_drawdown_pct
        limit = self.ftmo["max_total_loss_pct"]

        if total_dd >= limit:
            self.account.is_globally_blocked = True
            self.account.block_reason = (
                f"Drawdown total {total_dd:.2%} >= límite {limit:.2%}"
            )
            logger.critical(f"🚨 LÍMITE TOTAL ALCANZADO: {total_dd:.2%} — BOT BLOQUEADO")

    def can_open_trade(self, signal: Signal) -> tuple:
        """
        Verifica si se puede abrir una nueva operación.

        Returns:
            (allowed: bool, reason: str)
        """
        # 1. ¿Bot bloqueado globalmente?
        if self.account.is_globally_blocked:
            return False, f"Bot bloqueado: {self.account.block_reason}"

        # 2. ¿Día bloqueado?
        if self.account.daily_state and self.account.daily_state.is_blocked:
            return False, f"Día bloqueado: {self.account.daily_state.block_reason}"

        # 3. ¿Máximo de operaciones simultáneas?
        max_trades = self.sizing["max_simultaneous_trades"]
        if self.account.open_positions >= max_trades:
            return False, f"Máximo de operaciones abiertas alcanzado ({max_trades})"

        # 4. ¿Riesgo total expuesto?
        max_risk = self.sizing["max_risk_total_pct"]
        new_risk = self.account.total_risk_exposed_pct + self.sizing["risk_per_trade_pct"]
        if new_risk > max_risk:
            return False, (f"Riesgo total {new_risk:.2%} superaría máximo {max_risk:.2%}")

        # 5. ¿Es viernes cerca del cierre?
        if self.ftmo.get("close_before_weekend", True):
            if self._is_near_weekend_close():
                return False, "Cerca del cierre de fin de semana — no abrir nuevas"

        # 6. ¿Requests de servidor?
        if self.account.daily_state:
            max_req = self.ftmo.get("max_server_requests_per_day", 500)
            if self.account.daily_state.server_requests >= max_req:
                return False, f"Límite de requests diarios alcanzado ({max_req})"

        return True, "OK"

    def calculate_position_size(
        self,
        signal: Signal,
        symbol_info: Dict,
    ) -> float:
        """
        Calcula el tamaño de posición basado en el riesgo.

        Fórmula: Lotes = (Balance × RiskPct) / (SL_distance × point_value)
        """
        balance = self.account.current_balance
        risk_pct = self.sizing["risk_per_trade_pct"]
        risk_amount = balance * risk_pct

        # Distancia al SL en puntos del instrumento
        if signal.direction == Direction.LONG:
            sl_distance = signal.entry_price - signal.stop_loss
        else:
            sl_distance = signal.stop_loss - signal.entry_price

        if sl_distance <= 0:
            logger.error(f"SL distance inválida: {sl_distance}")
            return 0.0

        # Valor del punto
        contract_size = symbol_info.get("contract_size", 1)
        point = symbol_info.get("point", 1)

        # Calcular lotes
        # Para índices CFD: P&L = lotes × contract_size × variación_precio
        # risk_amount = lotes × contract_size × sl_distance
        if contract_size > 0:
            lots = risk_amount / (sl_distance * contract_size)
        else:
            lots = risk_amount / sl_distance

        # Ajustar al step del volumen
        vol_step = symbol_info.get("volume_step", 0.01)
        vol_min = symbol_info.get("volume_min", 0.01)
        vol_max = symbol_info.get("volume_max", 100)

        # Redondear al step más cercano hacia abajo
        lots = max(vol_min, min(vol_max, lots))
        if vol_step > 0:
            lots = round(lots / vol_step) * vol_step
            lots = round(lots, 2)  # Evitar errores de punto flotante

        logger.info(f"Position size: {lots} lotes "
                    f"(riesgo: ${risk_amount:.2f}, SL dist: {sl_distance:.1f} pts)")

        return lots

    def _is_near_weekend_close(self) -> bool:
        """Verifica si estamos cerca del cierre del viernes."""
        now = datetime.now()
        if now.weekday() != 4:  # 4 = Viernes
            return False

        minutes_before = self.ftmo.get("weekend_close_minutes_before", 30)
        # El mercado de índices cierra ~21:00 UTC el viernes
        market_close = time(21, 0)
        cutoff = time(
            market_close.hour,
            max(0, market_close.minute - minutes_before)
        )

        return now.time() >= cutoff

    def record_trade_close(self, pnl: float):
        """Registra el cierre de una operación."""
        if self.account.daily_state:
            self.account.daily_state.realized_pnl += pnl
            self.account.daily_state.trades_closed += 1

    def record_server_request(self, count: int = 1):
        """Incrementa el contador de requests al servidor."""
        if self.account.daily_state:
            self.account.daily_state.server_requests += count

    def get_status_summary(self) -> Dict:
        """Retorna resumen del estado de riesgo."""
        daily = self.account.daily_state
        return {
            "balance": self.account.current_balance,
            "equity": self.account.current_equity,
            "total_drawdown_pct": f"{self.account.total_drawdown_pct:.2%}",
            "daily_drawdown_pct": f"{daily.daily_drawdown_pct:.2%}" if daily else "N/A",
            "open_positions": self.account.open_positions,
            "total_risk_exposed": f"{self.account.total_risk_exposed_pct:.2%}",
            "daily_blocked": daily.is_blocked if daily else False,
            "globally_blocked": self.account.is_globally_blocked,
            "server_requests_today": daily.server_requests if daily else 0,
        }
