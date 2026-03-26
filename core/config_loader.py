"""
Cargador de configuración centralizado.
Lee los YAML de config/ y los expone como objetos accesibles.
"""

import yaml
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, Any, Optional


CONFIG_DIR = Path(__file__).parent.parent / "config"


def load_yaml(filename: str) -> dict:
    """Carga un archivo YAML desde el directorio de configuración."""
    filepath = CONFIG_DIR / filename
    if not filepath.exists():
        raise FileNotFoundError(f"Config file not found: {filepath}")
    with open(filepath, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


class Config:
    """Configuración centralizada del bot."""

    def __init__(self, strategy_config_path: Optional[str] = None, instruments_config_path: Optional[str] = None):
        # Cargar strategy config (permitir path alternativo)
        if strategy_config_path:
            with open(strategy_config_path, "r", encoding="utf-8") as f:
                self.strategy: dict = yaml.safe_load(f)
        else:
            self.strategy: dict = load_yaml("strategy_params.yaml")
        
        # Cargar instruments config (permitir path alternativo)
        if instruments_config_path:
            with open(instruments_config_path, "r", encoding="utf-8") as f:
                self.instruments_raw: dict = yaml.safe_load(f)
        else:
            self.instruments_raw: dict = load_yaml("instruments.yaml")
        
        self.ftmo: dict = load_yaml("ftmo_rules.yaml")["ftmo_rules"]
        self.instruments: Dict[str, dict] = self.instruments_raw["instruments"]
        self.correlation_groups: dict = self.instruments_raw.get("correlation_groups", {})

    def get_instrument(self, name: str) -> dict:
        """Obtiene configuración de un instrumento específico."""
        if name not in self.instruments:
            raise ValueError(f"Instrumento no configurado: {name}")
        return self.instruments[name]

    def get_enabled_instruments(self) -> Dict[str, dict]:
        """Retorna solo los instrumentos habilitados."""
        return {k: v for k, v in self.instruments.items() if v.get("enabled", False)}

    @property
    def zone_detection(self) -> dict:
        return self.strategy["zone_detection"]

    @property
    def entry(self) -> dict:
        return self.strategy["entry"]

    @property
    def stop_loss(self) -> dict:
        return self.strategy["stop_loss"]

    @property
    def take_profit(self) -> dict:
        return self.strategy["take_profit"]

    @property
    def position_sizing(self) -> dict:
        return self.strategy["position_sizing"]

    @property
    def break_even(self) -> dict:
        return self.strategy["break_even"]

    @property
    def filters(self) -> dict:
        return self.strategy["filters"]

    @property
    def bot_settings(self) -> dict:
        return self.strategy["bot"]


# Singleton
_config: Optional[Config] = None


def get_config(strategy_config_path: Optional[str] = None, instruments_config_path: Optional[str] = None) -> Config:
    """Obtiene la instancia global de configuración."""
    global _config
    if _config is None or strategy_config_path or instruments_config_path:
        _config = Config(strategy_config_path, instruments_config_path)
    return _config


def reload_config() -> Config:
    """Recarga la configuración desde disco."""
    global _config
    _config = Config()
    return _config
