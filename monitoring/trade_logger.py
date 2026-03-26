"""
Logger de trades para auditoría.
Registra cada operación en CSV para análisis posterior.
"""

import csv
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)

TRADE_LOG_HEADERS = [
    "timestamp_signal", "timestamp_entry", "timestamp_exit",
    "instrument", "direction", "entry_type", "pattern_detected",
    "zone_upper", "zone_lower", "zone_touches",
    "entry_price", "stop_loss", "take_profit",
    "position_size_lots", "risk_amount_usd", "risk_reward_ratio",
    "exit_price", "exit_reason",
    "pnl_points", "pnl_usd", "pnl_pct_of_balance",
    "daily_drawdown_after", "total_drawdown_after",
]


class TradeLogger:
    """Registra trades en archivo CSV."""

    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.filepath = self.log_dir / f"trades_{datetime.now().strftime('%Y%m')}.csv"
        self._ensure_headers()

    def _ensure_headers(self):
        """Crea el archivo con headers si no existe."""
        if not self.filepath.exists():
            with open(self.filepath, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(TRADE_LOG_HEADERS)
            logger.info(f"Trade log creado: {self.filepath}")

    def log_trade(self, trade_data: Dict):
        """Agrega una fila al log de trades."""
        row = [trade_data.get(h, "") for h in TRADE_LOG_HEADERS]

        with open(self.filepath, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(row)

        logger.debug(f"Trade registrado: {trade_data.get('instrument', '')} "
                    f"{trade_data.get('direction', '')} @ {trade_data.get('entry_price', '')}")

    def log_entry(self, signal, lots: float, risk_usd: float):
        """Registra la apertura de un trade."""
        self.log_trade({
            "timestamp_signal": signal.timestamp.isoformat(),
            "timestamp_entry": datetime.now().isoformat(),
            "instrument": signal.instrument,
            "direction": signal.direction.value,
            "entry_type": signal.signal_type.value,
            "pattern_detected": signal.signal_type.value,
            "zone_upper": f"{signal.zone.upper:.1f}",
            "zone_lower": f"{signal.zone.lower:.1f}",
            "zone_touches": signal.zone.touches,
            "entry_price": f"{signal.entry_price:.2f}",
            "stop_loss": f"{signal.stop_loss:.2f}",
            "take_profit": f"{signal.take_profit:.2f}",
            "position_size_lots": f"{lots:.2f}",
            "risk_amount_usd": f"{risk_usd:.2f}",
            "risk_reward_ratio": f"{signal.risk_reward_ratio:.2f}",
        })
