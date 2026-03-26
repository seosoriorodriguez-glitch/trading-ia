#!/usr/bin/env python3
"""
Crea estructura de carpetas para nueva estrategia

Uso:
    python3 tools/create_strategy.py <nombre_estrategia>
    
Ejemplo:
    python3 tools/create_strategy.py pivot_scalping
"""

import os
import sys
from pathlib import Path


STRATEGY_README_TEMPLATE = """# {strategy_name}

## 📋 Descripción

[Descripción breve de la estrategia]

## ⏰ Timeframes

- **Detección**: [Timeframe para detección de zonas/niveles]
- **Entrada**: [Timeframe para señales de entrada]

## 📊 Reglas de Entrada

### Condiciones de Entrada

1. [Condición 1]
2. [Condición 2]
3. [Condición 3]

### Filtros

- [Filtro 1]
- [Filtro 2]

## 🎯 Gestión de Riesgo

### Stop Loss
```
[Descripción del Stop Loss]
```

### Take Profit
```
[Descripción del Take Profit]
```

### Break Even
```
[Descripción del Break Even - si aplica]
```

### Trailing Stop
```
[Descripción del Trailing Stop - si aplica]
```

## 📈 Resultados de Backtest

### [Instrumento] (Período: [fechas])

```
Trades:            [N]
Win Rate:          [X]%
Profit Factor:     [X.XX]
Retorno:           [+X.XX]%
Max Drawdown:      [X.XX]%
Frecuencia:        [X.X] trades/mes
```

## 🔄 Historial de Versiones

### V1 - Versión Inicial
- **Fecha**: [fecha]
- **Cambios**: Versión inicial
- **Resultado**: [métricas]

## 📁 Archivos

### Configuración
- `config/strategy_params.yaml` - Parámetros de la estrategia
- `config/instruments.yaml` - Configuración por instrumento

### Código
- `core/` - Lógica de la estrategia
- `backtest/` - Motor de backtest

### Datos
- `data/` - Datos históricos y resultados

### Resultados
- `results/` - Análisis y reportes

## 🚀 Uso

### Ejecutar Backtest

```bash
cd strategies/{strategy_name}

python3 run_backtest.py \\
  --data-[tf1] data/[instrument]_[TF1]_[period].csv \\
  --data-[tf2] data/[instrument]_[TF2]_[period].csv \\
  --instrument [INSTRUMENT] \\
  --output data/backtest_[instrument].csv
```

## ✅ Estado

- [ ] En desarrollo
- [ ] Backtest completado
- [ ] Validado en demo
- [ ] Listo para FTMO

## 🎯 Próximos Pasos

1. [Paso 1]
2. [Paso 2]
3. [Paso 3]
"""


CONFIG_TEMPLATE = """# Configuración de {strategy_name}

# ============================================================
# DETECCIÓN DE ZONAS/NIVELES
# ============================================================
zones:
  # [Parámetros de detección]
  swing_strength: 5
  min_wick_ratio: 0.50

# ============================================================
# SEÑALES DE ENTRADA
# ============================================================
entry:
  valid_patterns:
    - 'pattern_1'
    - 'pattern_2'
  
  # [Parámetros de patrones]

# ============================================================
# GESTIÓN DE RIESGO
# ============================================================
stop_loss:
  sl_buffer_points: 20

take_profit:
  min_rr_ratio: 2.0
  tp_offset_points: 0

break_even:
  enabled: true
  trigger_rr: 1.5
  offset_points: 30

trailing_stop:
  enabled: false
  activation_rr: 2.0
  trail_distance_points: 50

# ============================================================
# FILTROS
# ============================================================
filters:
  trend:
    enabled: false
  
  time:
    enabled: false

# ============================================================
# SIZING
# ============================================================
sizing:
  risk_per_trade_pct: 0.005
  max_simultaneous_trades: 3
"""


INSTRUMENTS_TEMPLATE = """# Instrumentos para {strategy_name}

instruments:
  US30:
    enabled: true
    symbol_mt5: "US30"
    point_value: 1.0
    min_distance_points: 100
    sl_buffer_points: 20
    tp_offset_points: 50
  
  NAS100:
    enabled: false
    symbol_mt5: "NAS100"
    point_value: 1.0
    min_distance_points: 150
    sl_buffer_points: 30
    tp_offset_points: 70
  
  SPX500:
    enabled: false
    symbol_mt5: "SPX500"
    point_value: 1.0
    min_distance_points: 80
    sl_buffer_points: 15
    tp_offset_points: 40
"""


def create_strategy(strategy_name: str):
    """
    Crea estructura de carpetas para nueva estrategia
    
    Args:
        strategy_name: Nombre de la estrategia (ej: 'pivot_scalping')
    """
    
    base_path = Path(f"strategies/{strategy_name}")
    
    if base_path.exists():
        print(f"⚠️  La estrategia '{strategy_name}' ya existe en: {base_path}")
        response = input("¿Sobrescribir? (y/N): ")
        if response.lower() != 'y':
            print("❌ Operación cancelada")
            return
    
    # Crear carpetas
    folders = [
        base_path,
        base_path / "config",
        base_path / "core",
        base_path / "backtest",
        base_path / "data",
        base_path / "results"
    ]
    
    print(f"\n📁 Creando estructura para '{strategy_name}'...")
    
    for folder in folders:
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "__init__.py").touch()
        print(f"  ✅ {folder}")
    
    # Crear README
    readme_path = base_path / "README.md"
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(STRATEGY_README_TEMPLATE.format(strategy_name=strategy_name))
    print(f"  ✅ {readme_path}")
    
    # Crear config básico
    config_path = base_path / "config" / "strategy_params.yaml"
    with open(config_path, "w", encoding="utf-8") as f:
        f.write(CONFIG_TEMPLATE.format(strategy_name=strategy_name))
    print(f"  ✅ {config_path}")
    
    # Crear instruments config
    instruments_path = base_path / "config" / "instruments.yaml"
    with open(instruments_path, "w", encoding="utf-8") as f:
        f.write(INSTRUMENTS_TEMPLATE.format(strategy_name=strategy_name))
    print(f"  ✅ {instruments_path}")
    
    # Crear .gitkeep para carpetas vacías
    (base_path / "data" / ".gitkeep").touch()
    (base_path / "results" / ".gitkeep").touch()
    
    print(f"\n✅ Estrategia '{strategy_name}' creada exitosamente!")
    print(f"\n📝 Próximos pasos:")
    print(f"  1. Edita {readme_path} para documentar tu estrategia")
    print(f"  2. Edita {config_path} para configurar parámetros")
    print(f"  3. Implementa la lógica en {base_path / 'core'}/")
    print(f"  4. Crea el backtester en {base_path / 'backtest'}/")
    print(f"  5. Ejecuta tu primer backtest!")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python3 tools/create_strategy.py <nombre_estrategia>")
        print("\nEjemplo:")
        print("  python3 tools/create_strategy.py pivot_scalping")
        print("  python3 tools/create_strategy.py ema_crossover")
        sys.exit(1)
    
    strategy_name = sys.argv[1]
    
    # Validar nombre
    if not strategy_name.replace('_', '').isalnum():
        print("❌ Error: El nombre debe contener solo letras, números y guiones bajos")
        sys.exit(1)
    
    create_strategy(strategy_name)
