# 🚀 Guía Rápida: Framework Multi-Estrategia

**Última actualización**: 26 de Marzo, 2026

---

## 📁 Estructura del Proyecto

```
trading-ia/
├── strategies/              # Estrategias (cada una autocontenida)
│   ├── sr_swing/           # ✅ S/R Swing (validada)
│   └── pivot_scalping/     # 🔄 Pivot Scalping (en desarrollo)
│
├── tools/                  # Herramientas compartidas
│   ├── compare_strategies.py
│   ├── portfolio_simulator.py
│   ├── create_strategy.py
│   ├── download_yahoo_data.py
│   └── analyze_backtest.py
│
└── core/                   # Código compartido
    ├── candle.py
    ├── config_loader.py
    └── market_data.py
```

---

## ⚡ Comandos Más Usados

### 1. Ejecutar Backtest

```bash
cd strategies/sr_swing
python3 run_backtest.py \
  --data-h1 data/US30_H1_730d.csv \
  --data-h4 data/US30_H4_730d.csv \
  --instrument US30 \
  --output data/backtest_US30_new.csv
```

### 2. Comparar Estrategias

```bash
# Comparar US30 en diferentes estrategias
python3 tools/compare_strategies.py \
  strategies/sr_swing/data/backtest_US30_v4_longs_only.csv \
  strategies/pivot_scalping/data/backtest_US30_scalping_60d.csv

# Comparar múltiples instrumentos de una estrategia
python3 tools/compare_strategies.py \
  strategies/sr_swing/data/backtest_US30_v4_longs_only.csv \
  strategies/sr_swing/data/backtest_NAS100_v4_longs_only.csv \
  strategies/sr_swing/data/backtest_SPX500_v4_longs_only.csv
```

### 3. Simular Portfolio

```bash
python3 tools/portfolio_simulator.py \
  --strategy sr_swing strategies/sr_swing/data/backtest_US30_v4_longs_only.csv \
  --strategy pivot_scalping strategies/pivot_scalping/data/backtest_US30_scalping_60d.csv \
  --balance 100000
```

### 4. Crear Nueva Estrategia

```bash
python3 tools/create_strategy.py mi_nueva_estrategia
```

### 5. Descargar Datos

```bash
# Yahoo Finance (H1, H4, D1)
python3 tools/download_yahoo_data.py \
  --ticker "^DJI" \
  --days 730 \
  --interval 1h \
  --output strategies/mi_estrategia/data/US30_H1_730d
```

---

## 📊 Estrategias Disponibles

### S/R Swing ✅ VALIDADA

**Ubicación**: `strategies/sr_swing/`

**Resultados**:
- US30: PF 3.57, WR 72%, +9.01%
- NAS100: PF 1.89, WR 51.4%, +7.97%
- SPX500: PF 1.24, WR 56.7%, +1.56%

**Documentación**: [strategies/sr_swing/README.md](strategies/sr_swing/README.md)

**Próximos pasos**:
1. Implementar en demo (US30 + NAS100)
2. Monitorear 1-2 meses
3. Challenge FTMO

### Pivot Scalping 🔄 EN DESARROLLO

**Ubicación**: `strategies/pivot_scalping/`

**Estado**: Estructura creada, pendiente de implementación

**Documentación**: [strategies/pivot_scalping/README.md](strategies/pivot_scalping/README.md)

**Próximos pasos**:
1. Implementar módulos core
2. Obtener datos M5
3. Ejecutar backtest
4. Validar en demo

---

## 🔧 Desarrollo de Nueva Estrategia

### Paso 1: Crear Estructura

```bash
python3 tools/create_strategy.py mi_estrategia
```

### Paso 2: Implementar Lógica

```bash
cd strategies/mi_estrategia

# Editar configuración
vim config/strategy_params.yaml
vim config/instruments.yaml

# Implementar lógica
vim core/mi_modulo.py
vim backtest/mi_backtester.py
```

### Paso 3: Ejecutar Backtest

```bash
python3 run_backtest.py \
  --data-h1 data/INSTRUMENT_H1.csv \
  --data-h4 data/INSTRUMENT_H4.csv \
  --instrument INSTRUMENT \
  --output data/backtest_INSTRUMENT.csv
```

### Paso 4: Analizar Resultados

```bash
python3 ../../tools/analyze_backtest.py \
  data/backtest_INSTRUMENT.csv \
  > results/ANALISIS.md
```

### Paso 5: Comparar con Otras Estrategias

```bash
python3 ../../tools/compare_strategies.py \
  data/backtest_INSTRUMENT.csv \
  ../sr_swing/data/backtest_US30_v4_longs_only.csv
```

---

## 📈 Métricas Objetivo

### Swing Trading (H4+H1)
```
Win Rate:       >= 50%
Profit Factor:  >= 1.8
Max Drawdown:   < 5%
Frecuencia:     2-4 trades/mes por instrumento
```

### Scalping (M15+M5)
```
Win Rate:       >= 55%
Profit Factor:  >= 1.3 (después de costos)
Max Drawdown:   < 10%
Frecuencia:     10-30 trades/mes por instrumento
```

### FTMO Compliance (Todas)
```
Max Drawdown Total:  < 8%
Max Daily Drawdown:  < 4%
Trading Days:        4+ trades/mes
```

---

## 🎯 Flujo de Trabajo Recomendado

### Para Estrategia Nueva

1. **Diseño** (1-2 días)
   - Definir reglas claras
   - Documentar en README
   - Configurar parámetros

2. **Implementación** (3-7 días)
   - Crear módulos core
   - Implementar backtester
   - Escribir tests

3. **Backtest** (1 día)
   - Descargar datos (1-2 años)
   - Ejecutar backtest
   - Analizar resultados

4. **Optimización** (2-5 días)
   - Ajustar parámetros
   - Re-ejecutar backtests
   - Comparar versiones

5. **Demo** (1-3 meses)
   - Operar en demo
   - Monitorear métricas
   - Ajustar si es necesario

6. **FTMO** (Solo si demo exitoso)
   - Challenge
   - Verification
   - Funded account

### Para Estrategia Existente

1. **Modificar parámetros** en `config/strategy_params.yaml`
2. **Re-ejecutar backtest**
3. **Comparar** con versión anterior usando `compare_strategies.py`
4. **Documentar** cambios en README
5. **Commit** con mensaje descriptivo

---

## 🛠️ Herramientas Disponibles

### `compare_strategies.py`

**Propósito**: Comparar métricas de múltiples estrategias

**Uso**:
```bash
python3 tools/compare_strategies.py <csv1> <csv2> [csv3 ...]
```

**Output**:
- Tabla comparativa
- Rankings por PF, Retorno, Frecuencia
- Recomendaciones

### `portfolio_simulator.py`

**Propósito**: Simular portfolio combinando estrategias

**Uso**:
```bash
python3 tools/portfolio_simulator.py \
  --strategy nombre1 path1.csv \
  --strategy nombre2 path2.csv \
  [--balance 100000]
```

**Output**:
- Métricas del portfolio
- Desglose por estrategia
- Análisis de diversificación
- Evaluación FTMO

### `create_strategy.py`

**Propósito**: Generar estructura para nueva estrategia

**Uso**:
```bash
python3 tools/create_strategy.py <nombre>
```

**Crea**:
- Carpetas completas
- READMEs con plantillas
- Configs con ejemplos

### `download_yahoo_data.py`

**Propósito**: Descargar datos históricos de Yahoo Finance

**Uso**:
```bash
python3 tools/download_yahoo_data.py \
  --ticker "^DJI" \
  --days 730 \
  --interval 1h \
  --output data/US30_H1_730d
```

**Limitaciones**:
- H1: ~730 días máximo
- M15: ~60 días máximo
- M5: NO disponible (usar MT5)

### `analyze_backtest.py`

**Propósito**: Analizar resultados de backtest

**Uso**:
```bash
python3 tools/analyze_backtest.py <backtest.csv>
```

**Output**:
- Métricas detalladas
- Gráficos (si matplotlib disponible)
- Análisis por patrón

---

## 📚 Documentación

### General
- [README.md](README.md) - Visión general del framework
- [REORGANIZACION_MULTI_ESTRATEGIA.md](REORGANIZACION_MULTI_ESTRATEGIA.md) - Detalles de la reorganización

### Por Estrategia
- [strategies/sr_swing/README.md](strategies/sr_swing/README.md)
- [strategies/pivot_scalping/README.md](strategies/pivot_scalping/README.md)

### Documentación Técnica
- [docs/estrategia_sr_indices.md](docs/estrategia_sr_indices.md) - Estrategia S/R original
- [PROYECTO_OVERVIEW.md](PROYECTO_OVERVIEW.md) - Arquitectura del proyecto

---

## 🎉 Ventajas del Framework

1. **Modularidad**: Cada estrategia es independiente
2. **Escalabilidad**: Añadir estrategias sin conflictos
3. **Comparabilidad**: Herramientas para evaluar múltiples estrategias
4. **Mantenibilidad**: Código y documentación organizados
5. **Flexibilidad**: Combinar estrategias en portfolios
6. **Rapidez**: Plantillas para crear nuevas estrategias

---

## 💡 Tips

### Organización
- Una estrategia = una carpeta en `strategies/`
- Cada estrategia tiene su propio README
- Versionar cambios con Git

### Nomenclatura
- Backtests: `backtest_INSTRUMENT_vX.csv`
- Análisis: `ANALISIS_DESCRIPCION.md`
- Configs: `strategy_params_VARIANTE.yaml`

### Comparación
- Siempre comparar con versión anterior
- Documentar cambios en README
- Guardar backtests de todas las versiones

### Portfolio
- Combinar estrategias complementarias
- Diversificar por timeframe y tipo
- Monitorear correlación

---

## ❓ Preguntas Frecuentes

### ¿Cómo añado un nuevo instrumento?

1. Editar `strategies/[nombre]/config/instruments.yaml`
2. Descargar datos del instrumento
3. Ejecutar backtest
4. Comparar con otros instrumentos

### ¿Cómo creo una variante de una estrategia?

1. Copiar `config/strategy_params.yaml` a `config/strategy_params_VARIANTE.yaml`
2. Modificar parámetros
3. Ejecutar backtest con `--config config/strategy_params_VARIANTE.yaml`
4. Comparar resultados

### ¿Cómo combino múltiples estrategias?

Usar `portfolio_simulator.py` para simular el portfolio combinado.

### ¿Dónde están los archivos originales?

Los archivos originales siguen en la raíz del proyecto. Los de `strategies/` son copias.

---

## 🚀 ¡Listo para Iterar!

El framework está configurado para:
- ✅ Desarrollar múltiples estrategias en paralelo
- ✅ Comparar estrategias fácilmente
- ✅ Simular portfolios multi-estrategia
- ✅ Crear nuevas estrategias rápidamente
- ✅ Mantener código organizado y escalable

**¡Empieza a crear tu próxima estrategia!** 🎯
