# 🏗️ Reorganización a Framework Multi-Estrategia

**Fecha**: 26 de Marzo, 2026  
**Objetivo**: Transformar el proyecto de una estrategia única a un framework modular que soporte múltiples estrategias independientes.

---

## ✅ Cambios Realizados

### 1. Estructura de Carpetas Creada

```
trading-ia/
├── strategies/                    # 🆕 Carpeta principal de estrategias
│   ├── sr_swing/                  # Estrategia S/R Swing (migrada)
│   │   ├── config/                # Configs específicas
│   │   ├── core/                  # Lógica de la estrategia
│   │   ├── backtest/              # Backtester
│   │   ├── data/                  # Datos y resultados
│   │   ├── results/               # Análisis
│   │   ├── run_backtest.py        # Script de ejecución
│   │   └── README.md              # Documentación completa
│   │
│   └── pivot_scalping/            # 🆕 Estrategia Pivot Scalping (estructura)
│       ├── config/
│       ├── core/
│       ├── backtest/
│       ├── data/
│       ├── results/
│       └── README.md
│
├── tools/                         # 🆕 Herramientas compartidas
│   ├── download_yahoo_data.py     # Descarga de datos (movido)
│   ├── analyze_backtest.py        # Análisis de backtest (movido)
│   ├── compare_strategies.py      # 🆕 Comparar estrategias
│   ├── portfolio_simulator.py     # 🆕 Simular portfolio
│   └── create_strategy.py         # 🆕 Crear nueva estrategia
│
├── core/                          # Código compartido (sin cambios)
│   ├── candle.py
│   ├── config_loader.py
│   ├── market_data.py
│   └── utils.py
│
└── README.md                      # 🔄 Actualizado
```

### 2. Estrategia S/R Swing Migrada

**Archivos migrados a `strategies/sr_swing/`**:

- ✅ `config/*` → `strategies/sr_swing/config/`
- ✅ `core/levels.py` → `strategies/sr_swing/core/`
- ✅ `core/signals.py` → `strategies/sr_swing/core/`
- ✅ `core/trend.py` → `strategies/sr_swing/core/`
- ✅ `backtest/backtester.py` → `strategies/sr_swing/backtest/`
- ✅ `data/*.csv` → `strategies/sr_swing/data/`
- ✅ `ANALISIS_*.md`, `COMPARATIVA_*.md`, `RESULTADOS_*.md` → `strategies/sr_swing/results/`
- ✅ `run_backtest.py` → `strategies/sr_swing/`

**Documentación creada**:
- ✅ `strategies/sr_swing/README.md` - Documentación completa de la estrategia

### 3. Herramientas de Gestión Creadas

#### `tools/compare_strategies.py`

Compara métricas de múltiples estrategias:

```bash
python3 tools/compare_strategies.py \
  strategies/sr_swing/data/backtest_US30_v4_longs_only.csv \
  strategies/pivot_scalping/data/backtest_US30_scalping_60d.csv
```

**Funcionalidades**:
- Tabla comparativa de métricas
- Rankings por PF, Retorno, Frecuencia
- Recomendaciones automáticas
- Evaluación de compliance FTMO

#### `tools/portfolio_simulator.py`

Simula portfolio combinando múltiples estrategias:

```bash
python3 tools/portfolio_simulator.py \
  --strategy sr_swing strategies/sr_swing/data/backtest_US30_v4_longs_only.csv \
  --strategy pivot_scalping strategies/pivot_scalping/data/backtest_US30_scalping_60d.csv
```

**Funcionalidades**:
- Combina trades de múltiples estrategias
- Calcula métricas del portfolio
- Desglose por estrategia y dirección
- Análisis de diversificación
- Evaluación FTMO

#### `tools/create_strategy.py`

Genera estructura para nueva estrategia:

```bash
python3 tools/create_strategy.py mi_nueva_estrategia
```

**Crea**:
- Estructura de carpetas completa
- README.md con plantilla
- `config/strategy_params.yaml` con plantilla
- `config/instruments.yaml` con plantilla
- Archivos `__init__.py` en todos los módulos

### 4. Estrategia Pivot Scalping Preparada

**Estructura creada**:
- ✅ `strategies/pivot_scalping/` con todas las carpetas
- ✅ `strategies/pivot_scalping/README.md` con especificación completa
- ✅ `strategies/pivot_scalping/config/` con plantillas

**Estado**: 🔄 Estructura lista, pendiente de implementación de código

### 5. Documentación Actualizada

#### README.md Principal

- ✅ Actualizado a "Framework Multi-Estrategia"
- ✅ Listado de estrategias disponibles
- ✅ Nueva estructura de carpetas
- ✅ Sección de uso actualizada
- ✅ Tabla de resultados por estrategia
- ✅ Métricas objetivo por tipo de estrategia

#### READMEs de Estrategias

- ✅ `strategies/sr_swing/README.md` - Completo con historial de versiones
- ✅ `strategies/pivot_scalping/README.md` - Especificación detallada

---

## 🎯 Ventajas de la Nueva Estructura

### 1. Modularidad

- Cada estrategia es **autocontenida**
- No hay conflictos entre configs
- Fácil de versionar con Git
- Código compartido en `core/`

### 2. Escalabilidad

- Añadir nuevas estrategias sin tocar las existentes
- Probar variaciones sin romper código validado
- Iterar rápidamente

### 3. Comparabilidad

- Scripts de comparación estandarizados
- Métricas consistentes entre estrategias
- Portfolio simulator para combinar

### 4. Mantenibilidad

- Documentación por estrategia
- Historial de versiones claro
- Fácil de compartir o publicar

---

## 🚀 Flujo de Trabajo

### Crear Nueva Estrategia

```bash
# 1. Crear estructura
python3 tools/create_strategy.py mi_estrategia

# 2. Implementar lógica
cd strategies/mi_estrategia
vim core/mi_modulo.py
vim backtest/mi_backtester.py

# 3. Configurar parámetros
vim config/strategy_params.yaml

# 4. Ejecutar backtest
python3 run_backtest.py --instrument US30 --output data/backtest_US30.csv

# 5. Analizar resultados
python3 ../../tools/analyze_backtest.py data/backtest_US30.csv > results/ANALISIS.md
```

### Comparar Estrategias

```bash
python3 tools/compare_strategies.py \
  strategies/*/data/backtest_*.csv
```

### Simular Portfolio

```bash
python3 tools/portfolio_simulator.py \
  --strategy estrategia1 strategies/estrategia1/data/backtest.csv \
  --strategy estrategia2 strategies/estrategia2/data/backtest.csv
```

---

## 📊 Estado Actual de Estrategias

### S/R Swing ✅ VALIDADA

```
Estado:     ✅ Validada, lista para demo
Timeframes: H4 + H1
Resultados: PF 3.57, WR 72%, +9.01% (US30, 2 años)
Archivos:   Todos migrados y documentados
```

**Próximos pasos**:
1. Implementar en demo (US30 + NAS100)
2. Monitorear 1-2 meses
3. Challenge FTMO si métricas son consistentes

### Pivot Scalping 🔄 EN DESARROLLO

```
Estado:     🔄 Estructura creada, pendiente de implementación
Timeframes: M15 + M5
Resultados: Pendiente de backtest
Archivos:   README y configs listos
```

**Próximos pasos**:
1. Implementar módulos core:
   - `pivot_points.py` - Detección de pivots
   - `rejection_patterns.py` - Patrones de rechazo
   - `scalping_signals.py` - Generación de señales
2. Implementar backtester con BE y Trailing
3. Obtener datos M5 (MT5, no Yahoo)
4. Ejecutar backtest 60 días
5. Validar en demo si PF > 1.3

---

## 🔄 Archivos Originales

Los archivos originales en la raíz del proyecto **NO fueron eliminados**, solo copiados a `strategies/sr_swing/`.

**Razón**: Mantener compatibilidad con scripts existentes y permitir transición gradual.

**Recomendación futura**: Una vez validado que todo funciona correctamente, se pueden eliminar los archivos duplicados de la raíz.

---

## 📝 Notas Importantes

### Imports

Los imports en `strategies/sr_swing/` siguen apuntando a `core/` en la raíz del proyecto (código compartido).

**Ejemplo**:
```python
# strategies/sr_swing/core/signals.py
from core.candle import Candle  # Importa desde raíz
from core.config_loader import get_config
```

### Ejecución

Para ejecutar backtests de estrategias, **siempre** cambiar al directorio de la estrategia:

```bash
cd strategies/sr_swing
python3 run_backtest.py ...
```

### Datos

Cada estrategia mantiene sus propios datos en `strategies/[nombre]/data/`, pero pueden compartir datos si es necesario.

---

## ✅ Checklist de Migración

- [x] Crear estructura de carpetas
- [x] Migrar código de S/R Swing
- [x] Migrar datos de S/R Swing
- [x] Migrar análisis de S/R Swing
- [x] Crear README de S/R Swing
- [x] Crear estructura de Pivot Scalping
- [x] Crear README de Pivot Scalping
- [x] Crear `compare_strategies.py`
- [x] Crear `portfolio_simulator.py`
- [x] Crear `create_strategy.py`
- [x] Actualizar README principal
- [x] Hacer scripts ejecutables
- [x] Commit de cambios

---

## 🎉 Resultado

El proyecto ahora es un **framework modular** que permite:

1. ✅ Desarrollar múltiples estrategias en paralelo
2. ✅ Comparar estrategias fácilmente
3. ✅ Simular portfolios multi-estrategia
4. ✅ Crear nuevas estrategias con un comando
5. ✅ Mantener código limpio y organizado
6. ✅ Escalar a 10+ estrategias sin problemas

**¡Listo para iterar y crear nuevas estrategias!** 🚀
