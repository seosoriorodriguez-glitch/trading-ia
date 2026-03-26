# 🤖 Bot de Trading Automatizado con IA - Estrategia S/R en Índices

Bot automatizado para operar índices (US30, NAS100, SPX500) en MetaTrader 5,
diseñado específicamente para cuentas de fondeo FTMO con gestión de riesgo avanzada.

## Estrategia

- **Zonas en H4:** Detecta soportes y resistencias basados en rechazos fuertes
- **Entradas en H1:** Pin bar, envolvente, y falso quiebre (liquidity sweep)
- **Gestión de riesgo:** 0.5% por operación, máximo 3 simultáneas
- **Compliance FTMO:** Guardarraíles de drawdown diario (4%) y total (8%)

## Estructura del Proyecto

```
sr-trading-bot/
├── config/
│   ├── strategy_params.yaml      # Parámetros de la estrategia
│   ├── ftmo_rules.yaml           # Reglas FTMO (guardarraíles)
│   └── instruments.yaml          # Configuración por instrumento
├── core/
│   ├── config_loader.py          # Cargador de configuración
│   ├── market_data.py            # Conexión MT5 (Windows + Mac/Docker)
│   ├── levels.py                 # Detección de zonas S/R
│   ├── signals.py                # Detección de señales de entrada
│   ├── risk_manager.py           # Gestión de riesgo y compliance
│   └── executor.py               # Ejecución de órdenes en MT5
├── backtest/
│   └── backtester.py             # Motor de backtesting
├── monitoring/
│   ├── telegram_notifier.py      # Notificaciones Telegram
│   └── trade_logger.py           # Log de trades en CSV
├── logs/                         # Logs del bot (auto-generado)
├── data/                         # Datos históricos para backtest
├── main.py                       # Loop principal del bot
├── run_backtest.py               # Script de backtesting
├── docker-compose.yml            # MT5 en Docker (para macOS)
├── setup_mac.sh                  # Setup automático macOS
├── requirements.txt              # Dependencias Python
├── .env.example                  # Variables de entorno (template)
└── .gitignore
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

## Uso

### 1. Exportar datos históricos (desde MT5)

```bash
python run_backtest.py --export-mt5 US30 --days 365
```

Esto genera CSVs en la carpeta `data/`.

### 2. Ejecutar backtest

```bash
# Desde CSV
python run_backtest.py \
  --data-h1 data/US30_raw_H1_365d.csv \
  --data-h4 data/US30_raw_H4_365d.csv \
  --instrument US30 \
  --balance 100000 \
  --output data/backtest_results.csv

# Directo desde MT5
python run_backtest.py --from-mt5 US30 --days 365 --output results.csv
```

### 3. Ejecutar bot (simulación)

```bash
python main.py --log-level INFO
```

### 4. Ejecutar bot (LIVE — ¡solo después de validar con backtest y demo!)

```bash
python main.py --live --log-level INFO
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

## Parámetros Clave (strategy_params.yaml)

| Parámetro | Valor | Descripción |
|-----------|-------|-------------|
| `swing_strength` | 3 | Velas a cada lado para confirmar swing |
| `min_wick_ratio` | 0.40 | Mínimo 40% mecha para rechazo fuerte |
| `min_touches` | 2 | Toques mínimos para validar zona |
| `min_rr_ratio` | 1.5 | R:R mínimo para tomar trade |
| `risk_per_trade_pct` | 0.005 | 0.5% riesgo por operación |
| `sl_buffer_points` | 80 | Puntos extra de SL (US30) |
| `max_simultaneous_trades` | 3 | Máximo operaciones abiertas |

## Proceso de Validación Recomendado

1. **Backtest** con 2+ años de datos → verificar métricas
2. **Paper trading** en cuenta demo FTMO (mínimo 2-4 semanas)
3. **FTMO Free Trial** (si disponible) con el bot
4. **FTMO Challenge** solo si los resultados son consistentes

## Métricas Objetivo del Backtest

- Win Rate: >= 45%
- Profit Factor: >= 1.5
- Max Drawdown: < 8% (compliance FTMO)
- Max Daily Drawdown: < 4%
- R:R promedio: >= 1.5:1

## Advertencias

⚠️ **No soy asesor financiero.** Este bot es una herramienta, no una garantía de ganancias.

⚠️ **Siempre validar con backtest y demo antes de usar dinero real.**

⚠️ **Las cuentas de fondeo (FTMO) usan capital simulado, pero los challenges cuestan dinero real.**

⚠️ **El trading algorítmico no elimina el riesgo de mercado, solo elimina el riesgo emocional.**

---

## 📚 Documentación Completa

Para una visión completa del proyecto, arquitectura y roadmap, ver: **[PROYECTO_OVERVIEW.md](PROYECTO_OVERVIEW.md)**

Para detalles técnicos de la estrategia, ver: **[docs/estrategia_sr_indices.md](docs/estrategia_sr_indices.md)**
