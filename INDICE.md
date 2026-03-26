# 📑 Índice General del Proyecto

## 🎯 Guía de Navegación Rápida

Este documento te ayuda a encontrar rápidamente la información que necesitas.

---

## 📚 Documentación Principal

### 1. [README.md](README.md) - Punto de Entrada Principal
**¿Cuándo leer?** Primero, para entender qué es el proyecto

**Contenido**:
- Descripción general de la estrategia
- Estructura del proyecto
- Requisitos e instalación
- Uso básico del bot
- Flujo de operación
- Métricas objetivo
- Proceso de validación

**Tiempo de lectura**: 10-15 minutos

---

### 2. [QUICKSTART.md](QUICKSTART.md) - Guía de Inicio Rápido
**¿Cuándo leer?** Cuando quieras empezar a usar el bot HOY

**Contenido**:
- Setup en 5 minutos (macOS)
- Configuración de Telegram
- Conexión a MT5
- Verificación de símbolos
- Ejecución de backtest
- Tests de verificación
- Comandos útiles
- Troubleshooting

**Tiempo de lectura**: 5-10 minutos  
**Tiempo de implementación**: 15-30 minutos

---

### 3. [PROYECTO_OVERVIEW.md](PROYECTO_OVERVIEW.md) - Visión Completa
**¿Cuándo leer?** Cuando quieras entender el proyecto en profundidad

**Contenido**:
- Arquitectura del sistema (diagrama)
- Estructura completa de archivos
- Estrategia de trading detallada
- Gestión de riesgo
- Guardarraíles FTMO
- Configuración e instalación
- Flujo del bot
- Roadmap (Fase 1, 2, 3)
- Mejoras futuras

**Tiempo de lectura**: 20-30 minutos

---

### 4. [ANALISIS_TECNICO.md](ANALISIS_TECNICO.md) - Análisis Profundo
**¿Cuándo leer?** Cuando quieras optimizar y mejorar el bot

**Contenido**:
- Fundamentos de la estrategia S/R
- Ventajas y riesgos
- Expectativas realistas (escenarios)
- Análisis de componentes (código)
- Backtesting: qué buscar
- Optimización de parámetros
- Mejoras futuras (corto, medio, largo plazo)
- Recursos adicionales
- Checklist de validación

**Tiempo de lectura**: 30-40 minutos

---

### 5. [RESUMEN_PROYECTO.md](RESUMEN_PROYECTO.md) - Resumen Ejecutivo
**¿Cuándo leer?** Cuando necesites un resumen completo del estado actual

**Contenido**:
- Estado actual del proyecto
- Contenido completo (archivos)
- Estrategia implementada
- Archivos analizados e integrados
- Próximos pasos detallados (Fase 1, 2, 3, 4)
- Checklist de verificación
- Comandos útiles
- Consejos importantes
- Resumen final

**Tiempo de lectura**: 15-20 minutos

---

### 6. [docs/estrategia_sr_indices.md](docs/estrategia_sr_indices.md) - Estrategia Técnica
**¿Cuándo leer?** Cuando necesites la especificación técnica completa

**Contenido**:
- Resumen general de la estrategia
- Identificación de zonas S/R (H4) - algoritmos
- Señales de entrada (H1) - patrones
- Gestión de riesgo - fórmulas
- Reglas FTMO - hardcoded
- Gestión de operaciones abiertas
- Filtros adicionales
- Notificaciones (Telegram)
- Logging y auditoría
- Flujo completo del bot (pseudocódigo)
- Parámetros por instrumento
- Plan de backtesting

**Tiempo de lectura**: 40-60 minutos  
**Nivel**: Técnico avanzado

---

## 🗂️ Archivos de Código

### Core (Lógica Principal)

#### [core/market_data.py](core/market_data.py)
**Propósito**: Conexión a MetaTrader 5  
**Funciones principales**:
- `MT5Connection`: Clase para conectar a MT5
- `get_candles()`: Obtener velas históricas
- `get_account_info()`: Info de la cuenta
- `get_open_positions()`: Posiciones abiertas
- `get_symbol_info()`: Info del símbolo

---

#### [core/levels.py](core/levels.py)
**Propósito**: Detección de zonas de soporte y resistencia  
**Funciones principales**:
- `detect_swing_points()`: Detectar swing highs/lows
- `cluster_into_zones()`: Agrupar swings en zonas
- `count_additional_touches()`: Contar toques a zona
- `detect_zones()`: Pipeline completo de detección
- `find_next_opposite_zone()`: Encontrar zona opuesta para TP

**Clases**:
- `Zone`: Representa una zona de S/R
- `ZoneType`: Enum (SUPPORT, RESISTANCE)

---

#### [core/signals.py](core/signals.py)
**Propósito**: Detección de señales de entrada  
**Funciones principales**:
- `is_pin_bar_bullish()`: Detectar pin bar alcista
- `is_pin_bar_bearish()`: Detectar pin bar bajista
- `is_bullish_engulfing()`: Detectar envolvente alcista
- `is_bearish_engulfing()`: Detectar envolvente bajista
- `is_false_breakout_b1_support()`: Falso quiebre B1 (soporte)
- `is_false_breakout_b1_resistance()`: Falso quiebre B1 (resistencia)
- `is_false_breakout_b2_support()`: Falso quiebre B2 (soporte)
- `is_false_breakout_b2_resistance()`: Falso quiebre B2 (resistencia)
- `evaluate_zone_for_signal()`: Evaluar zona para señal
- `calculate_sl_tp()`: Calcular SL y TP
- `scan_for_signals()`: Escanear todas las zonas

**Clases**:
- `Signal`: Representa una señal de trading
- `SignalType`: Enum (PIN_BAR, ENGULFING, FALSE_BREAKOUT_B1, FALSE_BREAKOUT_B2)
- `Direction`: Enum (LONG, SHORT)

---

#### [core/risk_manager.py](core/risk_manager.py)
**Propósito**: Gestión de riesgo y compliance FTMO  
**Funciones principales**:
- `initialize()`: Inicializar estado de cuenta
- `update_state()`: Actualizar estado (cada ciclo)
- `new_day()`: Resetear estado diario
- `can_open_trade()`: Verificar si se puede abrir trade
- `calculate_position_size()`: Calcular tamaño de posición
- `record_trade_close()`: Registrar cierre de trade
- `get_status_summary()`: Resumen del estado

**Clases**:
- `AccountState`: Estado global de la cuenta
- `DailyState`: Estado diario para drawdown
- `RiskManager`: Gestor principal

---

#### [core/executor.py](core/executor.py)
**Propósito**: Ejecución de órdenes en MT5  
**Funciones principales**:
- `open_position()`: Abrir posición
- `close_position()`: Cerrar posición
- `close_all_positions()`: Cerrar todas
- `manage_break_even()`: Gestionar break even
- `modify_sl()`: Modificar stop loss

---

#### [core/config_loader.py](core/config_loader.py)
**Propósito**: Cargar configuración desde YAML  
**Funciones principales**:
- `get_config()`: Obtener configuración completa
- `load_yaml()`: Cargar archivo YAML

---

### Backtest

#### [backtest/backtester.py](backtest/backtester.py)
**Propósito**: Motor de backtesting histórico  
**Funciones principales**:
- `Backtester`: Clase principal
- `run()`: Ejecutar backtest
- `generate_report()`: Generar reporte de resultados

---

### Monitoring

#### [monitoring/telegram_notifier.py](monitoring/telegram_notifier.py)
**Propósito**: Notificaciones por Telegram  
**Funciones principales**:
- `send_message()`: Enviar mensaje
- `notify_trade_opened()`: Notificar trade abierto
- `notify_trade_closed()`: Notificar trade cerrado
- `notify_emergency_stop()`: Notificar stop de emergencia

---

#### [monitoring/trade_logger.py](monitoring/trade_logger.py)
**Propósito**: Logging de trades en CSV  
**Funciones principales**:
- `log_entry()`: Registrar entrada
- `log_exit()`: Registrar salida
- `get_daily_summary()`: Resumen diario

---

### Scripts Principales

#### [main.py](main.py)
**Propósito**: Loop principal del bot  
**Uso**:
```bash
python main.py                    # Simulación
python main.py --live             # Live trading
python main.py --log-level DEBUG  # Con debug
```

---

#### [run_backtest.py](run_backtest.py)
**Propósito**: Script de backtesting  
**Uso**:
```bash
python run_backtest.py --export-mt5 US30 --days 730
python run_backtest.py --from-mt5 US30 --days 730 --output results.csv
python run_backtest.py --data-h1 data/h1.csv --data-h4 data/h4.csv --instrument US30
```

---

## ⚙️ Archivos de Configuración

### [config/strategy_params.yaml](config/strategy_params.yaml)
**Contenido**:
- `zone_detection`: Parámetros de detección de zonas (H4)
- `entry`: Configuración de señales de entrada (H1)
- `stop_loss`: Método de SL
- `take_profit`: Método de TP y R:R mínimo
- `position_sizing`: Riesgo por trade y máximo simultáneas
- `break_even`: Configuración de break even
- `trailing_stop`: Configuración de trailing (desactivado)
- `filters`: Horarios, spread, volatilidad
- `bot`: Intervalo de check
- `mt5`: Conexión a MT5

---

### [config/ftmo_rules.yaml](config/ftmo_rules.yaml)
**Contenido**:
- `max_daily_loss_pct`: 4% (límite interno)
- `max_total_loss_pct`: 8% (límite interno)
- `max_server_requests_per_day`: 500
- `max_open_orders`: 10
- `min_trading_days`: 4
- `close_before_weekend`: true
- `avoid_high_impact_news`: true
- `challenge`: Objetivos Phase 1 y 2
- `on_daily_limit_hit`: Acciones automáticas
- `on_total_limit_hit`: Acciones automáticas

---

### [config/instruments.yaml](config/instruments.yaml)
**Contenido**:
- `US30`: Configuración para Dow Jones
- `NAS100`: Configuración para Nasdaq
- `SPX500`: Configuración para S&P 500
- `correlation_groups`: Grupos de correlación

**Parámetros por instrumento**:
- `symbol_mt5`: Nombre del símbolo en MT5
- `sl_buffer_points`: Buffer de SL
- `zone_merge_distance`: Distancia para agrupar zonas
- `tp_offset_points`: Offset de TP
- `max_spread_points`: Spread máximo
- `min_zone_width`: Ancho mínimo de zona
- `max_zone_width`: Ancho máximo de zona

---

## 🚀 Flujo de Trabajo Recomendado

### Para Comenzar (Día 1)
1. Leer [README.md](README.md) (10 min)
2. Leer [QUICKSTART.md](QUICKSTART.md) (10 min)
3. Ejecutar `./setup_mac.sh` (15 min)
4. Configurar `.env` con Telegram (5 min)
5. Conectar MT5 y verificar símbolos (10 min)

**Total**: ~50 minutos

---

### Para Entender el Proyecto (Semana 1)
1. Leer [PROYECTO_OVERVIEW.md](PROYECTO_OVERVIEW.md) (30 min)
2. Leer [docs/estrategia_sr_indices.md](docs/estrategia_sr_indices.md) (60 min)
3. Revisar código en `core/` (60 min)
4. Ejecutar backtest (30 min)
5. Analizar resultados (30 min)

**Total**: ~3.5 horas

---

### Para Optimizar (Semana 2-4)
1. Leer [ANALISIS_TECNICO.md](ANALISIS_TECNICO.md) (40 min)
2. Experimentar con parámetros (2-4 horas)
3. Ejecutar múltiples backtests (2-4 horas)
4. Comparar resultados (1-2 horas)
5. Documentar hallazgos (30 min)

**Total**: ~6-11 horas

---

## 🔍 Búsqueda Rápida por Tema

### Instalación y Setup
- [QUICKSTART.md](QUICKSTART.md) - Setup en 5 minutos
- [README.md](README.md) - Instalación detallada
- [setup_mac.sh](setup_mac.sh) - Script de instalación

### Estrategia
- [docs/estrategia_sr_indices.md](docs/estrategia_sr_indices.md) - Especificación completa
- [PROYECTO_OVERVIEW.md](PROYECTO_OVERVIEW.md) - Resumen de estrategia
- [ANALISIS_TECNICO.md](ANALISIS_TECNICO.md) - Fundamentos

### Configuración
- [config/strategy_params.yaml](config/strategy_params.yaml) - Parámetros de estrategia
- [config/ftmo_rules.yaml](config/ftmo_rules.yaml) - Reglas FTMO
- [config/instruments.yaml](config/instruments.yaml) - Instrumentos

### Código
- [core/levels.py](core/levels.py) - Detección de zonas
- [core/signals.py](core/signals.py) - Detección de señales
- [core/risk_manager.py](core/risk_manager.py) - Gestión de riesgo
- [core/executor.py](core/executor.py) - Ejecución de órdenes

### Backtesting
- [run_backtest.py](run_backtest.py) - Script de backtest
- [backtest/backtester.py](backtest/backtester.py) - Motor de backtest
- [ANALISIS_TECNICO.md](ANALISIS_TECNICO.md) - Análisis de resultados

### Optimización
- [ANALISIS_TECNICO.md](ANALISIS_TECNICO.md) - Guía de optimización
- [config/strategy_params.yaml](config/strategy_params.yaml) - Parámetros ajustables

### Troubleshooting
- [QUICKSTART.md](QUICKSTART.md) - Sección de troubleshooting
- [RESUMEN_PROYECTO.md](RESUMEN_PROYECTO.md) - Comandos útiles

---

## 📊 Glosario de Términos

### Estrategia
- **S/R**: Soporte y Resistencia
- **Zona**: Rango horizontal donde el precio ha mostrado rechazo
- **Swing High/Low**: Máximo/mínimo local en el gráfico
- **Falso Quiebre**: Penetración breve de una zona seguida de reversión
- **Liquidity Sweep**: Barrido de liquidez (stop-loss) antes de reversión

### Patrones
- **Pin Bar**: Vela con mecha larga y cuerpo pequeño
- **Envolvente**: Vela cuyo cuerpo envuelve el cuerpo de la anterior
- **B1**: Falso quiebre intra-vela (1 vela)
- **B2**: Falso quiebre en 2 velas

### Gestión de Riesgo
- **R:R**: Ratio Riesgo/Beneficio (Risk/Reward)
- **SL**: Stop Loss
- **TP**: Take Profit
- **DD**: Drawdown (pérdida desde el máximo)
- **BE**: Break Even (punto de equilibrio)

### FTMO
- **Phase 1**: Primera fase del challenge (10% objetivo)
- **Phase 2**: Segunda fase del challenge (5% objetivo)
- **Max DD**: Drawdown máximo permitido
- **Daily DD**: Drawdown diario máximo

---

## 🎯 Checklist de Lectura

### Nivel Principiante (Comenzar a usar el bot)
- [ ] README.md
- [ ] QUICKSTART.md
- [ ] RESUMEN_PROYECTO.md (sección "Próximos Pasos")

### Nivel Intermedio (Entender el bot)
- [ ] PROYECTO_OVERVIEW.md
- [ ] docs/estrategia_sr_indices.md
- [ ] Revisar código en core/

### Nivel Avanzado (Optimizar el bot)
- [ ] ANALISIS_TECNICO.md
- [ ] Todos los archivos de código
- [ ] Experimentar con parámetros

---

**Última actualización**: Marzo 26, 2026  
**Versión**: 1.0
