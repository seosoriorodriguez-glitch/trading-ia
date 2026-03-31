# 📁 CARPETAS ESTRATEGIA ORDER BLOCK

**Para compartir con otro asistente**

---

## 🎯 CARPETAS PRINCIPALES

### 1. `strategies/order_block/` (CARPETA RAÍZ)
Contiene toda la estrategia Order Block completa.

---

### 2. `strategies/order_block/backtest/` (BACKTEST)
Motor de backtesting y configuración.

#### Archivos core:
- ✅ `config.py` - **Parámetros de la estrategia** (CRÍTICO)
- ✅ `ob_detection.py` - Detección de Order Blocks en M5
- ✅ `signals.py` - Generación de señales y filtros (BOS, Rejection)
- ✅ `risk_manager.py` - Cálculo SL/TP y gestión de riesgo
- ✅ `backtester.py` - Backtester con MARKET orders
- ✅ `backtester_limit_orders.py` - Backtester con LIMIT orders (ACTUAL)
- ✅ `data_loader.py` - Carga de datos
- ✅ `run_backtest.py` - Script principal de backtest

#### Subcarpetas:
- `results/` - CSVs de resultados de backtests
- `experimental/` - Tests y optimizaciones

---

### 3. `strategies/order_block/live/` (BOT LIVE)
Código del bot en producción conectado a MT5.

#### Archivos core:
- ✅ `run_bot.py` - **Punto de entrada** (ejecutar bot)
- ✅ `trading_bot.py` - Orquestador principal del bot
- ✅ `ob_monitor.py` - Monitor de OBs y generación de señales LIMIT
- ✅ `order_executor.py` - Ejecución de órdenes en MT5
- ✅ `risk_manager.py` - Protecciones FTMO
- ✅ `data_feed.py` - Conexión a MT5 para datos en vivo
- ✅ `monitor.py` - Logging y notificaciones Telegram

#### Subcarpetas:
- `config/` - Configuración FTMO (`ftmo_rules.yaml`)

---

### 4. `strategies/order_block/tradingview/` (PINE SCRIPTS)
Scripts para visualización en TradingView.

- `ultimas_10_ganadoras.pine` - Últimas 10 operaciones ganadoras
- `winning_trades.pine` - Todas las operaciones ganadoras
- `ob_indicator.pine` - Indicador de Order Blocks
- `ob_strategy.pine` - Estrategia completa

---

### 5. `data/` (DATOS HISTÓRICOS)
Datos OHLCV para backtesting.

#### US30 (Dow Jones):
- `US30_cash_M5_260d.csv` - 260 días M5
- `US30_cash_M1_260d.csv` - 260 días M1

#### GBPJPY (Forex):
- `GBPJPY_M5_260d.csv` - 260 días M5
- `GBPJPY_M1_29d.csv` - 29 días M1

---

## 📋 ARCHIVOS CLAVE PARA OTRO ASISTENTE

### Para entender la estrategia:
1. ✅ `strategies/order_block/backtest/config.py` - **PARÁMETROS**
2. ✅ `strategies/order_block/backtest/ob_detection.py` - Detección OB
3. ✅ `strategies/order_block/live/ob_monitor.py` - Lógica LIMIT
4. ✅ `strategies/order_block/backtest/backtester_limit_orders.py` - Backtest LIMIT

### Para ejecutar backtest:
1. ✅ `strategies/order_block/backtest/run_backtest.py`
2. ✅ `data/US30_cash_M5_260d.csv`
3. ✅ `data/US30_cash_M1_260d.csv`

### Para entender el bot live:
1. ✅ `strategies/order_block/live/run_bot.py` - Punto de entrada
2. ✅ `strategies/order_block/live/trading_bot.py` - Orquestador
3. ✅ `strategies/order_block/live/config/ftmo_rules.yaml` - Reglas FTMO

---

## 🎯 ESTRUCTURA COMPLETA

```
strategies/order_block/
├── backtest/
│   ├── config.py                    ⭐ PARÁMETROS
│   ├── ob_detection.py              ⭐ DETECCIÓN OB
│   ├── signals.py                   ⭐ SEÑALES Y FILTROS
│   ├── risk_manager.py              ⭐ SL/TP
│   ├── backtester.py                (MARKET orders)
│   ├── backtester_limit_orders.py   ⭐ BACKTEST LIMIT
│   ├── data_loader.py
│   ├── run_backtest.py
│   ├── results/                     (CSVs de resultados)
│   └── experimental/                (Tests)
│
├── live/
│   ├── run_bot.py                   ⭐ EJECUTAR BOT
│   ├── trading_bot.py               ⭐ ORQUESTADOR
│   ├── ob_monitor.py                ⭐ LÓGICA LIMIT
│   ├── order_executor.py            ⭐ ÓRDENES MT5
│   ├── risk_manager.py              (FTMO)
│   ├── data_feed.py                 (MT5 data)
│   ├── monitor.py                   (Telegram)
│   └── config/
│       └── ftmo_rules.yaml          ⭐ REGLAS FTMO
│
└── tradingview/
    ├── ultimas_10_ganadoras.pine
    ├── winning_trades.pine
    └── ob_indicator.pine

data/
├── US30_cash_M5_260d.csv           ⭐ DATOS US30
├── US30_cash_M1_260d.csv           ⭐ DATOS US30
├── GBPJPY_M5_260d.csv              ⭐ DATOS GBPJPY
└── GBPJPY_M1_29d.csv               ⭐ DATOS GBPJPY
```

---

## 📊 RESULTADOS ACTUALES

- **Símbolo**: US30.cash
- **Retorno**: +30.91%
- **Max DD**: -8.77%
- **Win Rate**: 29.4%
- **Trades**: 197 (solo NY)

---

## 🚀 PARA COMPARTIR

**Carpetas necesarias**:
1. `strategies/order_block/` (completa)
2. `data/` (archivos US30 y GBPJPY)

**Archivos de documentación**:
- `ESTRATEGIA_BOT_LIVE_FINAL.md`
- `IMPLEMENTACION_LIMIT_COMPLETA.md`
- `RESUMEN_FINAL_ESTRATEGIA_LIVE.md`
