# 🤖 Bot de Trading Automatizado con IA - Estrategia S/R en Índices

## 📋 Resumen del Proyecto

Este es un **bot de trading automatizado** diseñado para operar índices (US30, NAS100, SPX500) en MetaTrader 5, específicamente optimizado para cuentas de fondeo FTMO. El bot implementa una estrategia de **soportes y resistencias (S/R)** con detección de patrones de velas y gestión de riesgo automatizada.

### 🎯 Objetivos Principales

1. **Trading Automatizado**: Operar 24/7 sin intervención humana
2. **Compliance FTMO**: Cumplir estrictamente con las reglas de drawdown (4% diario, 8% total)
3. **Gestión de Riesgo**: 0.5% de riesgo por operación, máximo 3 operaciones simultáneas
4. **Alta Probabilidad**: Enfoque en señales de "falso quiebre" (liquidity sweep) con R:R >= 1.5:1

---

## 🏗️ Arquitectura del Sistema

```
┌─────────────────────────────────────────────────────────────┐
│                      TRADING BOT CORE                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐ │
│  │  Market Data │───▶│ Zone Detector│───▶│Signal Scanner│ │
│  │   (MT5 API)  │    │   (H4 S/R)   │    │  (H1 Entry)  │ │
│  └──────────────┘    └──────────────┘    └──────────────┘ │
│         │                                        │          │
│         ▼                                        ▼          │
│  ┌──────────────┐                      ┌──────────────┐   │
│  │ Risk Manager │◀─────────────────────│   Executor   │   │
│  │ (FTMO Rules) │                      │  (MT5 Orders)│   │
│  └──────────────┘                      └──────────────┘   │
│         │                                        │          │
│         ▼                                        ▼          │
│  ┌──────────────┐                      ┌──────────────┐   │
│  │   Telegram   │                      │ Trade Logger │   │
│  │  Notifier    │                      │   (CSV/DB)   │   │
│  └──────────────┘                      └──────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## 📂 Estructura del Proyecto

```
trading-IA/
├── 📁 config/                      # Configuración YAML
│   ├── strategy_params.yaml        # Parámetros de la estrategia
│   ├── ftmo_rules.yaml             # Reglas FTMO (guardarraíles)
│   └── instruments.yaml            # Config por instrumento (US30, NAS100, SPX500)
│
├── 📁 core/                        # Lógica principal del bot
│   ├── config_loader.py            # Cargador de configuración
│   ├── market_data.py              # Conexión MT5 (Windows + Mac/Docker)
│   ├── levels.py                   # Detección de zonas S/R (H4)
│   ├── signals.py                  # Detección de señales de entrada (H1)
│   ├── risk_manager.py             # Gestión de riesgo y compliance FTMO
│   └── executor.py                 # Ejecución de órdenes en MT5
│
├── 📁 backtest/                    # Sistema de backtesting
│   └── backtester.py               # Motor de backtesting histórico
│
├── 📁 monitoring/                  # Monitoreo y alertas
│   ├── telegram_notifier.py        # Notificaciones Telegram
│   └── trade_logger.py             # Log de trades en CSV
│
├── 📁 docs/                        # Documentación
│   └── estrategia_sr_indices.md    # Documento maestro de la estrategia
│
├── 📁 logs/                        # Logs del bot (auto-generado)
├── 📁 data/                        # Datos históricos para backtest
├── 📁 tests/                       # Tests unitarios
│
├── 📄 main.py                      # Loop principal del bot
├── 📄 run_backtest.py              # Script de backtesting
├── 📄 docker-compose.yml           # MT5 en Docker (para macOS)
├── 📄 setup_mac.sh                 # Setup automático macOS
├── 📄 requirements.txt             # Dependencias Python
├── 📄 .env.example                 # Variables de entorno (template)
├── 📄 .gitignore                   # Archivos a ignorar en git
└── 📄 README.md                    # Documentación principal
```

---

## 🎲 Estrategia de Trading

### 1. Detección de Zonas (H4)

**Objetivo**: Identificar zonas de soporte y resistencia con alta probabilidad de rechazo.

**Proceso**:
1. Analizar últimas 200 velas H4 (~33 días)
2. Detectar **swing highs/lows** con rechazo fuerte (mecha >= 40% del rango)
3. Agrupar swings cercanos en **zonas** (ancho = rango completo de la vela más fuerte)
4. Validar zonas con **mínimo 2 toques** separados por 5+ velas H4
5. Mantener máximo 6 zonas activas (3 soporte + 3 resistencia)

**Ejemplo de Zona Válida**:
```
Resistencia US30: 45,200 - 45,280
├─ Borde superior: 45,280 (high de vela de rechazo)
├─ Borde inferior: 45,200 (low de vela de rechazo)
├─ Toques: 3
└─ Última activación: 2026-03-24 16:00
```

### 2. Señales de Entrada (H1)

**Condición previa**: El precio debe estar dentro o cerca de una zona válida.

**Tipos de señal** (ordenados por prioridad):

#### 🥇 Tipo B1: Falso Quiebre Intra-vela (Mayor probabilidad)
- La **mecha** perfora la zona (liquidity sweep)
- El **cierre** queda dentro de la zona o del lado correcto
- Cuerpo >= 40% del rango de la vela
- **Confianza: 90%**

#### 🥈 Tipo B2: Falso Quiebre en 2 Velas
- Primera vela perfora la zona
- Segunda vela cierra con fuerza de vuelta (cuerpo >= 50%)
- **Confianza: 75%**

#### 🥉 Tipo A: Pin Bar / Envolvente (Estándar)
- **Pin Bar**: Mecha >= 2x cuerpo, cierre en mitad correcta
- **Envolvente**: Cuerpo envuelve el cuerpo de la vela anterior
- **Confianza: 65-70%**

### 3. Gestión de Riesgo

| Parámetro | Valor | Descripción |
|-----------|-------|-------------|
| **Riesgo por trade** | 0.5% | Del balance actual |
| **Stop Loss** | Zona + 80 pts | Más allá del borde de la zona |
| **Take Profit** | Siguiente zona opuesta - 20 pts | O R:R mínimo 1.5:1 |
| **R:R mínimo** | 1.5:1 | Trades con menor R:R se descartan |
| **Max operaciones** | 3 simultáneas | Máximo riesgo total: 1.5% |
| **Break Even** | Al alcanzar 1:1 R:R | SL a entrada + 10 pts |

### 4. Guardarraíles FTMO (Irrompibles)

| Regla | Límite Interno | Límite FTMO | Acción |
|-------|----------------|-------------|---------|
| **Drawdown Diario** | 4% | 5% | Cerrar todo, bloquear día |
| **Drawdown Total** | 8% | 10% | Cerrar todo, bloquear bot |
| **Requests/día** | 500 | 2000 | Bloquear nuevas operaciones |
| **Órdenes abiertas** | 10 | 200 | Bloquear nuevas operaciones |
| **Días de trading** | Mínimo 4 | Mínimo 4 | Tracking automático |
| **Cierre fin de semana** | 30 min antes | N/A | Cerrar todas las posiciones |

---

## 🔧 Configuración e Instalación

### Requisitos

- **Python 3.10+**
- **Docker Desktop** (para macOS) o **MetaTrader 5** instalado (Windows)
- **Cuenta de broker** compatible con MT5 (ej: BlackBull Markets, FTMO)

### Instalación en macOS (Recomendado)

```bash
# 1. Clonar el repositorio
cd "/Users/sebastianosorio/Desktop/trading - IA"

# 2. Ejecutar el script de setup (instala Docker, MT5, Python deps)
chmod +x setup_mac.sh
./setup_mac.sh

# 3. Configurar variables de entorno
cp .env.example .env
nano .env  # Agregar tokens de Telegram

# 4. Verificar nombres de símbolos en tu broker
# Conectar a MT5 en Docker → Vista → Símbolos
# Actualizar config/instruments.yaml con los nombres exactos

# 5. Verificar conexión
source venv/bin/activate
python -c "from siliconmetatrader5 import MetaTrader5; mt5=MetaTrader5(); print('OK')"
```

### Instalación en Windows

```bash
# 1. Instalar MT5 desde metatrader5.com y loguearse

# 2. Crear entorno virtual
python -m venv venv
venv\Scripts\activate
pip install MetaTrader5 pandas numpy PyYAML requests matplotlib

# 3. Configurar .env
copy .env.example .env
```

---

## 🚀 Uso del Bot

### 1. Exportar Datos Históricos (desde MT5)

```bash
python run_backtest.py --export-mt5 US30 --days 365
```

Esto genera CSVs en la carpeta `data/`.

### 2. Ejecutar Backtest

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

### 3. Ejecutar Bot (Simulación)

```bash
python main.py --log-level INFO
```

### 4. Ejecutar Bot (LIVE — ¡solo después de validar!)

```bash
python main.py --live --log-level INFO
```

---

## 📊 Flujo del Bot

```
Cada 60 segundos (o al cierre de vela H1):

  1. ✅ VERIFICAR GUARDARRAÍLES FTMO
     → Drawdown diario < 4%? Drawdown total < 8%?
     → ¿Es viernes cerca del cierre?
     
  2. 📈 GESTIONAR POSICIONES ABIERTAS
     → Mover a break even si alcanzó 1:1 R:R
     
  3. 🎯 DETECTAR ZONAS (H4)
     → Swing highs/lows con rechazo fuerte
     → Agrupar en zonas, validar con 2+ toques
     
  4. 🔍 BUSCAR SEÑALES (H1)
     → ¿Precio en zona? → ¿Hay patrón de confirmación?
     → Pin bar / Envolvente / Falso quiebre
     
  5. 💰 EJECUTAR (si pasa todos los filtros)
     → Calcular SL, TP, tamaño de posición
     → R:R >= 1.5? Spread OK? Riesgo total OK?
     → Enviar orden → Notificar por Telegram → Registrar en log
```

---

## 📈 Métricas Objetivo del Backtest

| Métrica | Objetivo | Descripción |
|---------|----------|-------------|
| **Win Rate** | >= 45% | Porcentaje de trades ganadores |
| **Profit Factor** | >= 1.5 | Ganancia total / Pérdida total |
| **Max Drawdown** | < 8% | Cumplir con límite FTMO |
| **Max Daily Drawdown** | < 4% | Cumplir con límite FTMO |
| **R:R Promedio** | >= 1.5:1 | Riesgo/Beneficio promedio |
| **Sharpe Ratio** | >= 1.0 | Retorno ajustado por riesgo |
| **Total Trades** | > 100 | Significancia estadística |

---

## 🔔 Configuración de Telegram

1. Buscar `@BotFather` en Telegram
2. Crear bot: `/newbot` → seguir instrucciones → copiar token
3. Enviar un mensaje al bot
4. Obtener chat_id: visitar `https://api.telegram.org/bot<TOKEN>/getUpdates`
5. Poner token y chat_id en `.env`

**Notificaciones que recibirás**:
- 🟢 Nueva zona detectada
- 🔔 Precio acercándose a zona
- ⚡ Señal generada (con detalles del patrón)
- 💰 Trade abierto (entry, SL, TP, riesgo)
- ✅ Trade cerrado (P&L en puntos y USD)
- 🎯 SL movido a break even
- 📊 Resumen diario de P&L
- ⚠️ Alerta de riesgo (drawdown cercano al límite)
- 🚨 Stop de emergencia (límite alcanzado)

---

## 🛡️ Proceso de Validación Recomendado

1. **Backtest** con 2+ años de datos → verificar métricas
2. **Paper trading** en cuenta demo FTMO (mínimo 2-4 semanas)
3. **FTMO Free Trial** (si disponible) con el bot
4. **FTMO Challenge** solo si los resultados son consistentes

---

## ⚠️ Advertencias Importantes

⚠️ **No soy asesor financiero.** Este bot es una herramienta, no una garantía de ganancias.

⚠️ **Siempre validar con backtest y demo antes de usar dinero real.**

⚠️ **Las cuentas de fondeo (FTMO) usan capital simulado, pero los challenges cuestan dinero real.**

⚠️ **El trading algorítmico no elimina el riesgo de mercado, solo elimina el riesgo emocional.**

---

## 📚 Documentación Adicional

- **Estrategia completa**: Ver `docs/estrategia_sr_indices.md`
- **Configuración de parámetros**: Ver archivos en `config/`
- **Código fuente**: Ver módulos en `core/`

---

## 🔄 Próximos Pasos

### Fase 1: Validación (Actual)
- [x] Implementar estrategia base
- [x] Configurar guardarraíles FTMO
- [ ] Ejecutar backtest con 2 años de datos
- [ ] Validar métricas objetivo
- [ ] Optimizar parámetros si es necesario

### Fase 2: Paper Trading
- [ ] Ejecutar bot en cuenta demo FTMO (2-4 semanas)
- [ ] Monitorear drawdown diario y total
- [ ] Verificar cumplimiento de reglas FTMO
- [ ] Ajustar filtros de spread y volatilidad

### Fase 3: Live Trading
- [ ] FTMO Free Trial (si disponible)
- [ ] FTMO Challenge Phase 1 (10% objetivo)
- [ ] FTMO Challenge Phase 2 (5% objetivo)
- [ ] Cuenta fondeada

### Mejoras Futuras
- [ ] Integrar calendario económico (evitar noticias de alto impacto)
- [ ] Implementar trailing stop (después de validar en backtest)
- [ ] Añadir filtros de volatilidad (ATR)
- [ ] Dashboard web para monitoreo en tiempo real
- [ ] Machine Learning para optimización de parámetros
- [ ] Soporte para más instrumentos (Forex, Commodities)

---

## 📞 Contacto y Soporte

**Desarrollador**: Sebastián Osorio  
**Proyecto**: Bot de Trading Automatizado con IA  
**Fecha de Inicio**: Marzo 2026  
**Versión**: 1.0

---

## 📄 Licencia

Este proyecto es de uso personal. No redistribuir sin autorización.

---

**¡Buena suerte con tu trading automatizado! 🚀📈**
