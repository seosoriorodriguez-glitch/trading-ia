# 🤖 Trading IA - Framework Multi-Estrategia

Framework modular para desarrollo y backtesting de estrategias de trading automatizado en MetaTrader 5, diseñado para cuentas de fondeo FTMO.

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
- **Patrones**: Pin Bar, Engulfing, Inside Bar
- **Gestión**: BE en 1:1, Trailing Stop activo
- **Estado**: 🔄 En desarrollo, pendiente de implementación

## 📁 Estructura del Proyecto

```
trading-ia/
├── strategies/                    # 🎯 Estrategias (modular)
│   ├── sr_swing/                  # Estrategia S/R Swing (validada)
│   │   ├── config/                # Configs específicas
│   │   ├── core/                  # Lógica de la estrategia
│   │   ├── backtest/              # Backtester
│   │   ├── data/                  # Datos y resultados
│   │   ├── results/               # Análisis
│   │   └── README.md              # Documentación
│   │
│   └── pivot_scalping/            # Estrategia Pivot Scalping (en desarrollo)
│       ├── config/
│       ├── core/
│       ├── backtest/
│       └── README.md
│
├── core/                          # 🔧 Código compartido
│   ├── candle.py                  # Clases base
│   ├── config_loader.py           # Cargador de configs
│   ├── market_data.py             # Conexión MT5
│   └── utils.py                   # Utilidades
│
├── tools/                         # 🛠️ Herramientas
│   ├── download_yahoo_data.py     # Descarga datos Yahoo Finance
│   ├── compare_strategies.py      # Comparar estrategias
│   ├── portfolio_simulator.py     # Simular portfolio multi-estrategia
│   └── create_strategy.py         # Crear nueva estrategia
│
├── docs/                          # 📚 Documentación
├── main.py                        # Loop principal del bot
├── requirements.txt               # Dependencias Python
└── README.md                      # Este archivo
```

## Requisitos

- **Python 3.10+**
- **Docker Desktop** (para macOS) o **MetaTrader 5** instalado (Windows)
- **Cuenta de broker** compatible con MT5 (ej: BlackBull Markets, FTMO)

## Instalación — macOS (Recomendado)

```bash
# 1. Clonar el repo
git clone https://github.com/TU_USUARIO/sr-trading-bot.git
cd sr-trading-bot

# 2. Ejecutar el script de setup (instala Docker, MT5, Python deps)
chmod +x setup_mac.sh
./setup_mac.sh

# O paso a paso manual:

# 2a. Levantar MT5 en Docker
docker-compose up -d

# 2b. Crear entorno virtual e instalar dependencias
python3 -m venv venv
source venv/bin/activate
pip install siliconmetatrader5 pandas numpy PyYAML requests matplotlib

# 3. Configurar variables de entorno
cp .env.example .env
# Editar .env con tus tokens de Telegram

# 4. Verificar nombres de símbolos en tu broker
# Conectar a MT5 en Docker → Vista → Símbolos
# Actualizar config/instruments.yaml con los nombres exactos

# 5. Verificar conexión
python -c "from siliconmetatrader5 import MetaTrader5; mt5=MetaTrader5(); print('OK')"
```

## Instalación — Windows

```bash
# 1. Clonar el repo
git clone https://github.com/TU_USUARIO/sr-trading-bot.git
cd sr-trading-bot

# 2. Instalar MT5 desde metatrader5.com y loguearse

# 3. Crear entorno virtual
python -m venv venv
venv\Scripts\activate
pip install MetaTrader5 pandas numpy PyYAML requests matplotlib

# 4. Configurar .env
copy .env.example .env
```

## 🚀 Uso Rápido

### 1. Ejecutar Backtest de una Estrategia

```bash
# S/R Swing (H4+H1)
cd strategies/sr_swing
python3 run_backtest.py \
  --data-h1 data/US30_H1_730d.csv \
  --data-h4 data/US30_H4_730d.csv \
  --instrument US30 \
  --output data/backtest_US30_new.csv
```

### 2. Comparar Múltiples Estrategias

```bash
python3 tools/compare_strategies.py \
  strategies/sr_swing/data/backtest_US30_v4_longs_only.csv \
  strategies/pivot_scalping/data/backtest_US30_scalping_60d.csv
```

**Salida**:
```
================================================================================
COMPARATIVA DE ESTRATEGIAS
================================================================================
Estrategia        Trades  Win Rate  PF    Retorno  Mejor Trade  Peor Trade
sr_swing          25      72.0%     3.57  +9.01%   $2,450.00    -$500.00
pivot_scalping    87      58.3%     1.42  +5.23%   $850.00      -$520.00
================================================================================
```

### 3. Simular Portfolio Multi-Estrategia

```bash
python3 tools/portfolio_simulator.py \
  --strategy sr_swing strategies/sr_swing/data/backtest_US30_v4_longs_only.csv \
  --strategy pivot_scalping strategies/pivot_scalping/data/backtest_US30_scalping_60d.csv
```

### 4. Crear Nueva Estrategia

```bash
python3 tools/create_strategy.py mi_nueva_estrategia
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

### 5. Descargar Datos

```bash
# Yahoo Finance (H1, H4, D1)
python3 tools/download_yahoo_data.py \
  --ticker "^DJI" \
  --days 730 \
  --interval 1h \
  --output data/US30_H1_730d
```

## Configuración de Telegram

1. Buscar `@BotFather` en Telegram
2. Crear bot: `/newbot` → seguir instrucciones → copiar token
3. Enviar un mensaje al bot
4. Obtener chat_id: visitar `https://api.telegram.org/bot<TOKEN>/getUpdates`
5. Poner token y chat_id en `.env`

## Flujo del Bot

```
Cada 60 segundos (o al cierre de vela H1):

  1. VERIFICAR GUARDARRAÍLES FTMO
     → Drawdown diario < 4%? Drawdown total < 8%?
     → ¿Es viernes cerca del cierre?
     
  2. GESTIONAR POSICIONES ABIERTAS
     → Mover a break even si alcanzó 1:1 R:R
     
  3. DETECTAR ZONAS (H4)
     → Swing highs/lows con rechazo fuerte
     → Agrupar en zonas, validar con 2+ toques
     
  4. BUSCAR SEÑALES (H1)
     → ¿Precio en zona? → ¿Hay patrón de confirmación?
     → Pin bar / Envolvente / Falso quiebre
     
  5. EJECUTAR (si pasa todos los filtros)
     → Calcular SL, TP, tamaño de posición
     → R:R >= 1.5? Spread OK? Riesgo total OK?
     → Enviar orden → Notificar por Telegram → Registrar en log
```

## 📊 Resultados de Estrategias

### S/R Swing (V4 - Solo LONGs)

| Instrumento | Trades | Win Rate | PF | Retorno | Max DD | Frecuencia |
|-------------|--------|----------|-----|---------|--------|------------|
| **US30** | 25 | 72.0% | 3.57 | +9.01% | 0.98% | 1.0/mes |
| **NAS100** | 37 | 51.4% | 1.89 | +7.97% | 2.75% | 1.6/mes |
| **SPX500** | 30 | 56.7% | 1.24 | +1.56% | 2.25% | 1.5/mes |

**Recomendación**: US30 + NAS100 para FTMO (2.6 trades/mes, PF promedio 2.23)

## 🎯 Proceso de Desarrollo de Estrategias

1. **Diseño**: Definir reglas claras de entrada/salida
2. **Implementación**: Crear módulos en `strategies/[nombre]/core/`
3. **Backtest**: Validar con 1-2 años de datos históricos
4. **Optimización**: Ajustar parámetros basado en resultados
5. **Demo**: Operar 1-3 meses en cuenta demo
6. **FTMO**: Solo si métricas son consistentes

## 📈 Métricas Objetivo

### Para Swing Trading (H4+H1)
- Win Rate: >= 50%
- Profit Factor: >= 1.8
- Max Drawdown: < 5%
- Frecuencia: 2-4 trades/mes por instrumento

### Para Scalping (M15+M5)
- Win Rate: >= 55%
- Profit Factor: >= 1.3 (después de costos)
- Max Drawdown: < 10%
- Frecuencia: 10-30 trades/mes por instrumento

### Compliance FTMO (Todas las Estrategias)
- Max Drawdown Total: < 8%
- Max Daily Drawdown: < 4%
- Mínimo Trading Days: 4+ trades/mes

## Advertencias

⚠️ **No soy asesor financiero.** Este bot es una herramienta, no una garantía de ganancias.

⚠️ **Siempre validar con backtest y demo antes de usar dinero real.**

⚠️ **Las cuentas de fondeo (FTMO) usan capital simulado, pero los challenges cuestan dinero real.**

⚠️ **El trading algorítmico no elimina el riesgo de mercado, solo elimina el riesgo emocional.**

---

## 📚 Documentación Completa

Para una visión completa del proyecto, arquitectura y roadmap, ver: **[PROYECTO_OVERVIEW.md](PROYECTO_OVERVIEW.md)**

Para detalles técnicos de la estrategia, ver: **[docs/estrategia_sr_indices.md](docs/estrategia_sr_indices.md)**
