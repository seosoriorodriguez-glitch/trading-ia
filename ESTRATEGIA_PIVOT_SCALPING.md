# ESTRATEGIA: PIVOT SCALPING M5/M1 - OPTIMIZADA

## RESUMEN EJECUTIVO

Estrategia de scalping agresiva basada en **Pivot Points puros** (High/Low) detectados en **M5** con entradas en **M1**. Diseñada para FTMO Challenge con gestión de riesgo estricta.

**Resultados Backtest (29 días, US30):**
- Win Rate: 81.8%
- Profit Factor: 4.60
- Retorno: +7.94%
- Trades: 22 (~0.75/día)
- Balance: $100,000 → $107,940

---

## 1. DETECCIÓN DE PIVOT POINTS (M5)

### 1.1 Definición de Pivot
Un **Pivot High** se confirma cuando:
```
high[i] > high[i-2] AND high[i] > high[i-1] AND 
high[i] > high[i+1] AND high[i] > high[i+2]
```

Un **Pivot Low** se confirma cuando:
```
low[i] < low[i-2] AND low[i] < low[i-1] AND 
low[i] < low[i+1] AND low[i] < low[i+2]
```

**Parámetros:**
- `swing_strength: 2` (velas a cada lado para confirmar)
- `zone_type: "full_candle"` (zona = [low, high] de la vela pivot)

### 1.2 Zona del Pivot
La zona NO es solo el high/low, sino **toda la vela**:
- **Pivot High**: zona = [low, high] de la vela que hizo el máximo
- **Pivot Low**: zona = [low, high] de la vela que hizo el mínimo

**Validación de zona:**
- `min_zone_width: 3` pts (mínimo)
- `max_zone_width: 150` pts (máximo)

### 1.3 Sistema de Toques
Para que un pivot sea válido, el precio debe "tocar" la zona:

**¿Qué es un toque?**
- Precio entra en la zona [low_zone, high_zone]
- Separación mínima entre toques: `min_touch_separation: 2` velas M5 (10 min)

**Requisitos:**
- `min_touches: 1` (AGRESIVO: primer toque ya es válido)
- `max_touches: 10` (después de 10 toques, la zona "se rompe")

### 1.4 Expiración de Pivots
Un pivot expira si:
- Pasan `expiry_candles: 200` velas M5 (~16.6 horas) sin toques
- Se alcanza `max_touches: 10`

**Límite de zonas activas:**
- `max_active_zones: 12` (máximo 12 pivots simultáneos)

---

## 2. SEÑALES DE ENTRADA (M1)

### 2.1 Condiciones para Trade
Se requieren **3 condiciones simultáneas**:

1. **Precio en zona pivot válida** (con al menos 1 toque)
2. **Patrón de rechazo en M1** (Pin Bar o Engulfing)
3. **Todos los filtros aprobados** (horario, spread, risk)

### 2.2 Patrones de Rechazo

#### Pin Bar (Vela con mecha larga)
**Para LONG (en Pivot Low):**
- Mecha inferior >= 2x cuerpo (`min_wick_to_body_ratio: 2.0`)
- Cuerpo <= 35% del rango total (`max_body_pct: 0.35`)
- Cierre en mitad superior de la vela

**Para SHORT (en Pivot High):**
- Mecha superior >= 2x cuerpo
- Cuerpo <= 35% del rango total
- Cierre en mitad inferior de la vela

#### Engulfing (Vela envolvente)
**Para LONG (en Pivot Low):**
- Vela verde (alcista)
- Cuerpo envuelve >= 100% del cuerpo de la vela anterior (`min_body_ratio: 1.0`)
- Vela anterior debe ser roja (bajista)

**Para SHORT (en Pivot High):**
- Vela roja (bajista)
- Cuerpo envuelve >= 100% del cuerpo de la vela anterior
- Vela anterior debe ser verde (alcista)

---

## 3. GESTIÓN DE RIESGO

### 3.1 Stop Loss (Dinámico)
El SL se coloca **fuera de la zona pivot** con un buffer de seguridad:

**Para LONG:**
```
SL = borde_inferior_zona - buffer_points
SL = pivot_zone_low - 20 pts
```

**Para SHORT:**
```
SL = borde_superior_zona + buffer_points
SL = pivot_zone_high + 20 pts
```

**Parámetros:**
- `buffer_points: 20` (cushion de seguridad, elimina rechazos del broker)
- `min_risk_points: 15` (distancia mínima Entry→SL para aceptar el trade)

**Ejemplo SHORT:**
```
Pivot High zone: 45,700 - 45,720
Entry: 45,730
SL = 45,720 + 20 = 45,740
Risk = 45,740 - 45,730 = 10 pts → RECHAZADO (< 15 pts)

Pivot High zone: 45,700 - 45,730
Entry: 45,750
SL = 45,730 + 20 = 45,750
Risk = 45,750 - 45,750 = 20 pts → ACEPTADO (>= 15 pts)
```

### 3.2 Take Profit (Por Estructura)
El TP se coloca en el **siguiente pivot opuesto**:

**Para LONG:**
```
TP = borde_inferior_pivot_high_siguiente - offset_points
TP = next_pivot_high_low - 3 pts
```

**Para SHORT:**
```
TP = borde_superior_pivot_low_siguiente + offset_points
TP = next_pivot_low_high + 3 pts
```

**Fallback (si no hay pivot opuesto):**
- Usar R:R fijo: `fallback_rr: 1.5` (1.5:1)
- TP = Entry + (Risk × 1.5)

**Validación:**
- `min_rr_ratio: 1.2` (rechazar trades con R:R < 1.2:1)

### 3.3 Position Sizing
Riesgo **fijo por trade**:

```python
risk_usd = balance × risk_per_trade_pct
risk_usd = $100,000 × 0.005 = $500

lot_size = risk_usd / (risk_points × point_value)
lot_size = $500 / (20 pts × $1) = 25 lotes
```

**Parámetros:**
- `risk_per_trade_pct: 0.005` (0.5% del balance por trade)
- `max_simultaneous_trades: 2` (máximo 2 trades abiertos)
- `max_total_risk_pct: 0.01` (máximo 1% de riesgo total expuesto)

### 3.4 Break Even y Trailing Stop
**DESACTIVADOS** en la versión actual:
- `break_even.enabled: false`
- `trailing_stop.enabled: false`

Esto es para evaluar la estrategia "desnuda" sin optimizaciones adicionales.

---

## 4. FILTROS

### 4.1 Filtro de Horario
Solo operar en **sesiones de alta liquidez**:

**Sesión Londres:**
- Horario: 08:00 - 11:00 UTC
- Skip primeros 15 min (volatilidad de apertura)

**Sesión Nueva York:**
- Horario: 13:30 - 19:30 UTC
- Skip primeros 15 min

**Días permitidos:**
- Lunes a Viernes (1-5)
- NO operar fines de semana

### 4.2 Filtro de Spread
- `max_spread_points: 5` pts
- Si spread > 5 pts → NO abrir trade (evitar costos excesivos)

### 4.3 Filtro de Tendencia
- `enabled: false` (NO se usa filtro de tendencia)
- Estrategia de **Pivot Points puros** (mean reversion)

---

## 5. REGLAS FTMO

### 5.1 Límites de Drawdown
- **Daily Loss**: 5% máximo por día
- **Total Loss**: 10% máximo acumulado
- Si se alcanza cualquiera → bot se detiene automáticamente

### 5.2 Profit Target
- **Objetivo**: +10% del balance inicial
- **Min Trading Days**: 4 días mínimo para pasar

### 5.3 Gestión de Fin de Semana
- `close_before_weekend: true`
- `weekend_close_hour: 21` UTC (viernes)
- Cerrar todos los trades abiertos antes del cierre semanal

---

## 6. LÓGICA DE EJECUCIÓN (LIVE BOT)

### 6.1 Flujo Principal
```
Loop cada 5 segundos:
  1. Obtener última vela M1 y M5
  2. Actualizar pivots (cada 5 min)
  3. Verificar señales en M1
  4. Si hay señal válida:
     a. Calcular SL/TP
     b. Validar risk (min_risk_points, R:R, spread)
     c. Validar FTMO rules (DD, horario)
     d. Calcular lot size
     e. Ejecutar orden en MT5
     f. Enviar notificación Telegram
  5. Actualizar dashboard
```

### 6.2 Gestión de Trades Abiertos
```
Loop cada 5 segundos:
  Para cada trade abierto:
    1. Verificar si alcanzó TP → cerrar
    2. Verificar si alcanzó SL → cerrar
    3. (Si BE/Trailing activo) Actualizar SL
    4. Verificar FTMO weekend close
```

---

## 7. PARÁMETROS CLAVE (OPTIMIZADOS)

### Archivo: `scalping_params_M5M1_aggressive.yaml`

```yaml
pivots:
  swing_strength: 2              # Velas a cada lado para confirmar pivot
  zone_type: "full_candle"       # Zona = rango completo [low, high]
  min_touches: 1                 # Primer toque ya es válido
  min_touch_separation: 2        # 2 velas M5 (10 min) entre toques
  max_touches: 10                # Máximo 10 toques antes de expirar
  expiry_candles: 200            # 200 velas M5 (~16.6 hrs) de vida
  max_active_zones: 12           # Máximo 12 pivots simultáneos
  min_zone_width: 3              # Mínimo 3 pts de ancho
  max_zone_width: 150            # Máximo 150 pts de ancho

entry:
  valid_patterns: ['pin_bar', 'engulfing']
  pin_bar:
    min_wick_to_body_ratio: 2.0  # Mecha >= 2x cuerpo
    max_body_pct: 0.35           # Cuerpo <= 35% de vela
  engulfing:
    min_body_ratio: 1.0          # Envolver >= 100% de vela anterior

stop_loss:
  buffer_points: 20              # 20 pts fuera de zona (OPTIMIZADO)
  min_risk_points: 15            # Mínimo 15 pts Entry→SL (OPTIMIZADO)

take_profit:
  method: "structure"            # TP en siguiente pivot opuesto
  structure:
    offset_points: 3             # 3 pts antes del pivot
  fallback_rr: 1.5               # R:R 1.5:1 si no hay pivot
  min_rr_ratio: 1.2              # Rechazar si R:R < 1.2:1

break_even:
  enabled: false                 # DESACTIVADO (estrategia desnuda)

trailing_stop:
  enabled: false                 # DESACTIVADO (estrategia desnuda)

filters:
  time:
    enabled: true
    sessions:
      london: {start: "08:00", end: "11:00", skip_first_minutes: 15}
      new_york: {start: "13:30", end: "19:30", skip_first_minutes: 15}
    allowed_days: [1, 2, 3, 4, 5]
  
  spread:
    enabled: true
    max_spread_points: 5         # No abrir si spread > 5 pts

sizing:
  risk_per_trade_pct: 0.005      # 0.5% por trade
  max_simultaneous_trades: 2     # Máximo 2 trades abiertos
  max_total_risk_pct: 0.01       # Máximo 1% riesgo total

costs:
  avg_spread_points: 2           # Spread promedio para backtest
  commission_per_lot: 0          # Sin comisión

ftmo:
  max_daily_drawdown_pct: 0.04   # 4% DD diario (FTMO = 5%, usamos 4%)
  max_total_drawdown_pct: 0.08   # 8% DD total (FTMO = 10%, usamos 8%)
  close_before_weekend: true
  weekend_close_hour: 21         # UTC
```

---

## 8. EJEMPLO DE TRADE COMPLETO

### Setup: SHORT en Pivot High

**Contexto (M5):**
- Pivot High detectado en vela de 14:25 UTC
- High: 46,542.50 | Low: 46,522.50
- Zona pivot: [46,522.50, 46,542.50] (20 pts de ancho)
- Toques previos: 1 (válido para operar)

**Señal (M1 a las 14:33):**
- Pin Bar bajista en 46,515.00
- Mecha superior: 28 pts | Cuerpo: 7 pts
- Ratio mecha/cuerpo: 4.0x ✅ (>= 2.0)
- Cierre en mitad inferior ✅

**Cálculo de Orden:**
```
Entry:  46,515.00
SL:     46,542.50 + 20 = 46,562.50  (buffer 20 pts)
Risk:   46,562.50 - 46,515.00 = 47.5 pts ✅ (>= 15 pts)

Next Pivot Low: 46,421.40
TP:     46,421.40 + 3 = 46,424.40
Reward: 46,515.00 - 46,424.40 = 90.6 pts

R:R:    90.6 / 47.5 = 1.91 ✅ (>= 1.2)
```

**Position Sizing:**
```
Balance:   $100,000
Risk %:    0.5%
Risk USD:  $500

Lot Size:  $500 / (47.5 pts × $1/pt) = 10.53 lotes
```

**Ejecución:**
- Orden SHORT enviada a MT5
- Notificación Telegram: "SHORT US30 @ 46515.00 | SL: 46562.50 | TP: 46424.40"

**Resultado:**
- Precio baja a 46,457.31
- TP alcanzado ✅
- PnL: +55.7 pts × 10.53 lotes = +$1,012.55 (2.03R)

---

## 9. CASOS DE RECHAZO DE SEÑAL

El bot **NO ejecuta** un trade si:

### 9.1 Pivot no válido
- Pivot tiene 0 toques (recién detectado)
- Pivot expiró (>200 velas o >10 toques)
- Zona muy pequeña (<3 pts) o muy grande (>150 pts)

### 9.2 Patrón no válido
- No es Pin Bar ni Engulfing
- Pin Bar: ratio mecha/cuerpo < 2.0
- Engulfing: ratio < 1.0

### 9.3 Risk insuficiente
- Distancia Entry→SL < 15 pts (`min_risk_points`)
- R:R < 1.2:1 (`min_rr_ratio`)

### 9.4 Filtros
- Fuera de horario de trading
- Spread > 5 pts
- Ya hay 2 trades abiertos
- Riesgo total expuesto > 1%

### 9.5 FTMO Rules
- Daily DD >= 4%
- Total DD >= 8%
- Es fin de semana

---

## 10. ARQUITECTURA DEL CÓDIGO

### 10.1 Módulos Core
```
strategies/pivot_scalping/core/
├── pivot_detection.py       # Detecta pivots, gestiona toques
├── rejection_patterns.py    # Detecta Pin Bar y Engulfing
├── scalping_signals.py      # Genera señales de entrada
└── position_sizing.py       # Calcula lot size
```

### 10.2 Módulos Live
```
strategies/pivot_scalping/live/
├── data_feed.py            # Obtiene datos de MT5
├── signal_monitor.py       # Monitorea señales en tiempo real
├── risk_manager.py         # Valida FTMO rules
├── order_executor.py       # Ejecuta órdenes en MT5
├── trading_bot.py          # Orquestador principal
└── monitor.py              # Dashboard y Telegram
```

### 10.3 Configs
```
strategies/pivot_scalping/config/
├── scalping_params_M5M1_aggressive.yaml  # Config en producción
├── ftmo_rules.yaml                       # Reglas FTMO
└── scalping_params_M5M1_buffer*.yaml     # Configs de test
```

---

## 11. CÓMO CORRER UN BACKTEST

### 11.1 Requisitos
- Datos M1 y M5 en formato CSV
- Columnas: `time,open,high,low,close,volume`
- Timestamps alineados (M1 debe estar contenido en rango M5)

### 11.2 Comando
```bash
python strategies/pivot_scalping/run_backtest_m5m1.py \
  --data-m1 data/US30_cash_M1_30k.csv \
  --data-m5 data/US30_cash_M5_29d.csv \
  --instrument US30 \
  --config strategies/pivot_scalping/config/scalping_params_M5M1_aggressive.yaml \
  --output results/backtest_results.csv \
  --balance 100000
```

### 11.3 Output
El backtest genera:
- Resumen en consola (trades, win rate, PF, retorno)
- CSV con todos los trades (`results/backtest_results.csv`)

---

## 12. CÓMO CORRER EL BOT LIVE

### 12.1 Requisitos
- MetaTrader 5 instalado y logueado
- Python 3.11+ con venv activado
- Telegram Bot Token y Chat ID (opcional)

### 12.2 Comando
```bash
# Windows
.\INICIAR_BOT.bat

# O manualmente
python run_live_bot.py \
  --symbol US30.cash \
  --strategy strategies/pivot_scalping/config/scalping_params_M5M1_aggressive.yaml \
  --ftmo-config strategies/pivot_scalping/config/ftmo_rules.yaml \
  --balance 100000 \
  --telegram-token YOUR_TOKEN \
  --telegram-chat-id YOUR_CHAT_ID
```

### 12.3 Dashboard
El bot muestra en consola:
```
==================================================
🤖 FTMO BOT - US30 Pivot Scalping
==================================================

💰 Balance: $100,058.64 (+0.06%)
🎯 Target: 10.0%

📊 Daily DD: 0.00% / 5.0%
📊 Total DD: -0.06% / 10.0%

📈 Trades Hoy: 1
📈 Trades Abiertos: 0

🎯 Estrategia: M5/M1 Agresiva
🔍 Pivots Activos: 12 (H:9, L:3)

✅ Trading: ACTIVO

⏰ Última actualización: 2026-03-27 14:27:30 UTC
==================================================
```

---

## 13. RESULTADOS HISTÓRICOS

### Backtest Buffer Comparison (29 días, US30, $100k inicial)

| Métrica | Buffer 10 | Buffer 15 | Buffer 20 (ACTUAL) |
|---------|-----------|-----------|---------------------|
| **Trades** | 34 | 29 | **22** |
| **Win Rate** | 73.5% | 72.4% | **81.8%** |
| **Profit Factor** | 2.55 | 2.38 | **4.60** |
| **Retorno** | +8.10% | +6.29% | **+7.94%** |
| **Balance Final** | $108,099 | $106,290 | **$107,940** |
| **Avg Win** | $533 | $517 | **$564** |
| **Avg Loss** | -$580 | -$571 | **-$551** |
| **Trades/día** | 1.17 | 1.00 | **0.76** |

**Conclusión:** Buffer 20 ofrece el mejor balance entre frecuencia y calidad.

---

## 14. PREGUNTAS FRECUENTES

### ¿Por qué buffer 20 y no 5?
- **Buffer 5**: Genera errores "Invalid stops" (10016) porque el SL está demasiado cerca del precio
- **Buffer 20**: Cumple con el "minimum stop level" del broker (~20-30 pts en US30)
- **Beneficio adicional**: Filtra setups de baja calidad, mejora Win Rate

### ¿Por qué min_risk_points 15?
- Trades con SL < 15 pts son demasiado ajustados para US30
- El ruido del mercado puede sacarte prematuramente
- Es mejor NO operar que operar con riesgo mal definido

### ¿Por qué no usar Break Even o Trailing Stop?
- Primero validamos la estrategia "desnuda"
- Si funciona bien, podemos agregar optimizaciones después
- Evita complejidad innecesaria en la fase inicial

### ¿Cuántos trades esperar por día?
- **Promedio**: 0.75 trades/día (buffer 20)
- **Rango**: 0-3 trades/día (depende de volatilidad)
- Es una estrategia de **calidad sobre cantidad**

### ¿Cuánto tiempo para pasar FTMO Trial (+10%)?
- **Estimado**: 38-45 días de trading
- **Cálculo**: +7.94% en 29 días → ~0.27%/día
- **10% / 0.27% = 37 días** (más margen de error)

---

## 15. CALIBRACIÓN PARA OTROS INSTRUMENTOS

Si quieres usar esta estrategia en **GBPJPY, EURUSD, etc.**:

### 15.1 Conversión de Parámetros
Los parámetros están en **puntos** (US30 = 1 punto = $1):

**Para GBPJPY (1 pip = 0.01):**
```yaml
min_zone_width: 3        # → 0.030 (3 pips)
max_zone_width: 150      # → 1.500 (150 pips)
buffer_points: 20        # → 0.200 (20 pips)
min_risk_points: 15      # → 0.150 (15 pips)
max_spread_points: 5     # → 0.050 (5 pips)
```

**Para EURUSD (1 pip = 0.0001):**
```yaml
min_zone_width: 3        # → 0.0003 (3 pips)
buffer_points: 20        # → 0.0020 (20 pips)
# etc.
```

### 15.2 Validar con Backtest
Siempre correr backtest primero para validar que los parámetros son apropiados para el instrumento.

---

## 16. LOGS Y DEBUGGING

### 16.1 Logs del Bot
```
logs/
└── trading_bot_YYYYMMDD.log
```

Contiene:
- Todos los trades ejecutados
- Errores de MT5
- Señales rechazadas (con razón)
- Actualizaciones de pivots

### 16.2 Errores Comunes

**Error 10016 (Invalid stops):**
- SL/TP demasiado cerca del precio
- Solución: Aumentar `buffer_points` a 20+

**Error: Candle.__init__() got unexpected keyword:**
- Conflicto entre `pivot_detection.Candle` y `rejection_patterns.Candle`
- Ya corregido en versión actual

**Bot no ejecuta trades:**
- Verificar horario de trading (UTC)
- Verificar que hay pivots activos
- Revisar logs para ver señales rechazadas

---

## 17. PRÓXIMOS PASOS DE OPTIMIZACIÓN

### 17.1 Activar Break Even
```yaml
break_even:
  enabled: true
  trigger_rr: 1.0      # Cuando alcanza 1:1
  offset_points: 3     # Mover SL a entry + 3 pts
```

### 17.2 Activar Trailing Stop
```yaml
trailing_stop:
  enabled: true
  method: "candle_structure"
  activation_rr: 1.0
  candle_structure:
    update_on_new_candle: true
```

### 17.3 Ajustar Agresividad
- `min_touches: 2` (esperar 2do toque, más conservador)
- `swing_strength: 3` (pivots más fuertes, menos frecuencia)
- `risk_per_trade_pct: 0.01` (1% por trade, más agresivo)

---

## 18. CONTACTO Y SOPORTE

**Repositorio:** C:/Users/sosor/OneDrive/Escritorio/dev/trading/trading-ia

**Archivos clave:**
- `run_live_bot.py` - Ejecutar bot en vivo
- `INICIAR_BOT.bat` - Script de inicio rápido (Windows)
- `COMANDOS_RAPIDOS.md` - Comandos útiles
- `README.md` - Documentación general

**Última actualización:** 27 Mar 2026
**Versión:** 2.2 (Buffer Optimizado)
