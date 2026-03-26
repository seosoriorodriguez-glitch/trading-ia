# 🤖 Trading IA - Framework Multi-Estrategia

Framework modular para desarrollo y backtesting de estrategias de trading automatizado en MetaTrader 5, diseñado para cuentas de fondeo FTMO.

**Plataforma**: Windows  
**Broker**: MetaTrader 5  
**Lenguaje**: Python 3.10+

---

## 🎯 Estrategias Disponibles

### 1. [S/R Swing Trading](strategies/sr_swing/) ✅ VALIDADA

**Swing trading basado en zonas de Soporte y Resistencia**

- **Timeframes**: H4 (zonas) + H1 (señales)
- **Patrones**: Pin Bar, False Breakout B1
- **Filtros**: EMA 200, Solo LONGs
- **Resultados**: PF 3.57, WR 72%, +9.01% (US30, 2 años)
- **Estado**: ✅ Validada, lista para demo

### 2. [Pivot Points Scalping](strategies/pivot_scalping/) 🔄 EN DESARROLLO

**Scalping en pivots puros M15+M5**

- **Timeframes**: M15 (pivots) + M5 (entradas)
- **Patrones**: Pin Bar, Engulfing
- **Gestión**: BE en 1:1, Trailing Stop por estructura
- **Estado**: 🔄 En desarrollo (30% completado)

---

## 🚀 Instalación (Windows)

### Requisitos Previos

- Windows 10/11
- Python 3.10 o superior
- MetaTrader 5 instalado
- Cuenta demo/real en MT5

### Paso 1: Clonar Repositorio

```bash
git clone https://github.com/TU_USUARIO/trading-ia.git
cd trading-ia
```

### Paso 2: Crear Entorno Virtual

```bash
python -m venv venv
venv\Scripts\activate
```

### Paso 3: Instalar Dependencias

```bash
pip install -r requirements.txt
```

### Paso 4: Configurar MetaTrader 5

1. **Abrir MT5** y loguear con tu cuenta
2. **Habilitar Algo Trading**:
   - Tools → Options
   - Expert Advisors tab
   - ✅ Allow automated trading

### Paso 5: Verificar Conexión

```bash
python tools/verify_connection.py
```

**Output esperado**:
```
✅ Conectado a MT5 — Cuenta: 12345678, Broker: FTMO Demo
✅ Encontrado: US30.cash
```

---

## 📊 Uso Rápido

### 1. Descargar Datos de MT5

```bash
# Descargar M5 y M15 de US30 (60 días)
python tools/download_mt5_data.py --symbol US30.cash --timeframes M5 M15 --days 60

# Descargar H1 y H4 (2 años)
python tools/download_mt5_data.py --symbol US30.cash --timeframes H1 H4 --days 730
```

### 2. Ejecutar Backtest (S/R Swing)

```bash
cd strategies/sr_swing
python run_backtest.py \
  --data-h1 data/US30_H1_730d.csv \
  --data-h4 data/US30_H4_730d.csv \
  --instrument US30 \
  --output data/backtest_US30.csv
```

### 3. Comparar Estrategias

```bash
python tools/compare_strategies.py \
  strategies/sr_swing/data/backtest_US30_v4_longs_only.csv \
  strategies/pivot_scalping/data/backtest_US30_scalping.csv
```

### 4. Simular Portfolio

```bash
python tools/portfolio_simulator.py \
  --strategy sr_swing strategies/sr_swing/data/backtest_US30.csv \
  --strategy scalping strategies/pivot_scalping/data/backtest_US30.csv
```

---

## 📁 Estructura del Proyecto

```
trading-ia/
├── strategies/              # Estrategias (modular)
│   ├── sr_swing/           # S/R Swing (validada)
│   │   ├── config/         # Configs YAML
│   │   ├── core/           # Lógica de estrategia
│   │   ├── backtest/       # Backtester
│   │   ├── data/           # Datos y resultados
│   │   └── README.md       # Documentación
│   │
│   └── pivot_scalping/     # Pivot Scalping (en desarrollo)
│       ├── config/
│       ├── core/
│       └── README.md
│
├── core/                   # Código compartido
│   ├── candle.py          # Clases base
│   ├── config_loader.py   # Cargador de configs
│   └── market_data.py     # Conexión MT5
│
├── tools/                  # Herramientas
│   ├── verify_connection.py      # Verificar MT5
│   ├── download_mt5_data.py      # Descargar datos
│   ├── compare_strategies.py     # Comparar estrategias
│   ├── portfolio_simulator.py    # Simular portfolio
│   └── create_strategy.py        # Crear nueva estrategia
│
├── docs/                   # Documentación
├── requirements.txt        # Dependencias
└── README.md              # Este archivo
```

---

## 🛠️ Crear Nueva Estrategia

```bash
python tools/create_strategy.py mi_nueva_estrategia
```

Esto crea:
```
strategies/mi_nueva_estrategia/
├── config/
├── core/
├── backtest/
├── data/
├── results/
└── README.md
```

---

## 📈 Resultados de S/R Swing (Validada)

| Instrumento | Trades | Win Rate | PF | Retorno | Max DD | Frecuencia |
|-------------|--------|----------|-----|---------|--------|------------|
| **US30** | 25 | 72.0% | 3.57 | +9.01% | 0.98% | 1.0/mes |
| **NAS100** | 37 | 51.4% | 1.89 | +7.97% | 2.75% | 1.6/mes |
| **SPX500** | 30 | 56.7% | 1.24 | +1.56% | 2.25% | 1.5/mes |

**Recomendación**: US30 + NAS100 para FTMO (2.6 trades/mes, PF promedio 2.23)

---

## 📚 Documentación

### Guías Principales
- [MIGRACION_WINDOWS.md](MIGRACION_WINDOWS.md) - Setup en Windows
- [GUIA_RAPIDA_MULTI_ESTRATEGIA.md](GUIA_RAPIDA_MULTI_ESTRATEGIA.md) - Uso del framework
- [REORGANIZACION_MULTI_ESTRATEGIA.md](REORGANIZACION_MULTI_ESTRATEGIA.md) - Arquitectura

### Por Estrategia
- [S/R Swing README](strategies/sr_swing/README.md) - Documentación completa
- [Pivot Scalping README](strategies/pivot_scalping/README.md) - Especificación

### Análisis de Backtests
- [strategies/sr_swing/results/](strategies/sr_swing/results/) - Análisis detallados V1-V4

---

## 🎯 Métricas Objetivo

### Para Swing Trading (H4+H1)
- Win Rate: >= 50%
- Profit Factor: >= 1.8
- Max Drawdown: < 5%
- Frecuencia: 2-4 trades/mes

### Para Scalping (M15+M5)
- Win Rate: >= 55%
- Profit Factor: >= 1.3 (después de costos)
- Max Drawdown: < 10%
- Frecuencia: 10-30 trades/mes

### Compliance FTMO
- Max Drawdown Total: < 8%
- Max Daily Drawdown: < 4%
- Trading Days: 4+ trades/mes

---

## 🔧 Herramientas Disponibles

### `verify_connection.py`
Verifica conexión a MT5 y descubre nombres de símbolos.

### `download_mt5_data.py`
Descarga datos históricos directamente de MT5.

### `compare_strategies.py`
Compara métricas de múltiples estrategias.

### `portfolio_simulator.py`
Simula portfolio combinando estrategias.

### `create_strategy.py`
Genera estructura para nueva estrategia.

---

## ⚠️ Advertencias

- **No soy asesor financiero**. Este framework es una herramienta, no una garantía de ganancias.
- **Siempre validar con backtest y demo** antes de usar dinero real.
- **Las cuentas de fondeo (FTMO)** usan capital simulado, pero los challenges cuestan dinero real.
- **El trading algorítmico no elimina el riesgo** de mercado, solo el riesgo emocional.

---

## 🤝 Contribuciones

Este es un proyecto personal de trading automatizado. Si encuentras bugs o tienes sugerencias, abre un issue.

---

## 📝 Licencia

Este proyecto es de código abierto para fines educativos. Úsalo bajo tu propio riesgo.

---

## 🚀 Roadmap

- [x] Framework multi-estrategia
- [x] Estrategia S/R Swing (validada)
- [x] Migración a Windows
- [x] Scripts de conexión MT5
- [ ] Estrategia Pivot Scalping (en desarrollo)
- [ ] Validación en demo
- [ ] Challenge FTMO
- [ ] Trading en vivo

---

**¿Preguntas?** Revisa la [documentación](docs/) o abre un issue.

**¡Buena suerte con tu trading!** 📈
