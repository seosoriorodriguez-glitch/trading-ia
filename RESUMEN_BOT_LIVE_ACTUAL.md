# 📊 RESUMEN EXHAUSTIVO - BOT LIVE ORDER BLOCK (Configuración Actual)

**Fecha de análisis**: 30 Marzo 2026  
**Estado**: ACTIVO y operando en MT5  
**Símbolo**: US30.cash (Dow Jones)  
**Balance inicial**: $100,000

---

## 🎯 ESTRATEGIA COMPLETA

### 1. DETECCIÓN DE ORDER BLOCKS (M5)

**Archivo**: `strategies/order_block/backtest/ob_detection.py`

#### Bullish OB:
1. **Vela bajista** (`close < open`)
2. **Seguida de 4 velas TODAS alcistas** (`close > open`)
3. **Impulso mínimo**: 0% (desactivado, `min_impulse_pct: 0.0`)
4. **Zona OB**: `[low, open]` de la vela bajista (`zone_type: "half_candle"`)
5. **Filtro ATR**: Tamaño zona ≤ `ATR(14) * 3.5`

#### Bearish OB:
1. **Vela alcista** (`close > open`)
2. **Seguida de 4 velas TODAS bajistas** (`close < open`)
3. **Impulso mínimo**: 0% (desactivado)
4. **Zona OB**: `[open, high]` de la vela alcista
5. **Filtro ATR**: Igual que bullish

#### Confirmación:
- **Anti look-ahead**: OB se confirma en la apertura de la vela que sigue al cierre de la 4ta vela consecutiva
- **Expiración**: 100 velas M5 sin toque → OB expira
- **Destrucción**: Vela M5 cierra fuera de la zona → OB se destruye
- **Max OBs activos**: 10 (los más recientes)

---

### 2. ENTRADA (M1) - MARKET ORDERS

**Archivo**: `strategies/order_block/backtest/signals.py`

#### Condiciones de entrada:
1. **Horario**: Sesión NY (13:30-20:00 UTC), excluyendo primeros 15 min → **13:45-20:00 UTC**
2. **Vela M1 cierra dentro de la zona OB**:
   - **LONG**: `candle_close ≤ zone_high` (no rechaza si está dentro)
   - **SHORT**: `candle_close ≥ zone_low` (no rechaza si está dentro)
3. **Entry price**: `candle_close` (precio de cierre de la vela M1)
4. **Filtro EMA 4H**: ❌ DESACTIVADO (`ema_trend_filter: False`)
5. **Filtro Rejection**: ❌ DESACTIVADO (`require_rejection: False`)
6. **Filtro BOS**: ❌ DESACTIVADO (`require_bos: False`)

#### Tipo de orden:
- **MARKET ORDER** (`TRADE_ACTION_DEAL`)
- Ejecución inmediata al cierre de vela M1

---

### 3. GESTIÓN DE RIESGO (SL/TP)

**Archivo**: `strategies/order_block/backtest/risk_manager.py`

#### LONG (OB Bullish):
- **Entry**: `candle_close`
- **SL**: `zone_low - 25 puntos` (debajo de la zona)
- **TP**: `entry + (risk_points * 3.5)` (arriba del entry)

#### SHORT (OB Bearish):
- **Entry**: `candle_close`
- **TP**: `zone_low - 25 puntos` (debajo de la zona)
- **Risk points**: `reward_points / 3.5`
- **SL**: `entry + risk_points` (arriba del entry)

#### Parámetros:
- **Buffer SL**: 25 puntos
- **Target R:R**: 3.5
- **Min R:R**: 1.2
- **Min risk**: 15 puntos
- **Max risk**: 300 puntos
- **Risk por trade**: 0.5% del balance ($500 con $100k)
- **Max trades simultáneos**: 2

---

### 4. PROTECCIONES FTMO

**Archivo**: `strategies/order_block/live/config/ftmo_rules.yaml`

- **Daily DD máximo**: 5% ($5,000)
- **Total DD máximo**: 10% ($10,000)
- **Profit target**: 10% ($10,000)
- **Max spread**: 5 puntos
- **Cierre fin de semana**: Viernes 21:00 UTC
- **Días mínimos trading**: 4

---

### 5. FLUJO OPERATIVO

**Archivo**: `strategies/order_block/live/trading_bot.py`

1. **Cada 5 minutos** (nueva vela M5):
   - Re-detecta OBs en las últimas 350 velas M5
   - Aplica expiry/destrucción
   - Actualiza lista de OBs activos

2. **Cada 1 minuto** (nueva vela M1):
   - Verifica si vela M1 toca algún OB activo
   - Aplica filtros de entrada
   - Si pasa: ejecuta orden MARKET inmediata

3. **Continuamente**:
   - Monitorea trades abiertos
   - Verifica SL/TP hit
   - Actualiza balance y DD
   - Dashboard cada 30 segundos

4. **Emergency stop**: Archivo `STOP.txt` detiene el bot

---

## 📋 PARÁMETROS CLAVE (config.py)

```python
"consecutive_candles": 4        # 4 velas consecutivas para confirmar OB
"min_impulse_pct": 0.0          # Sin impulso mínimo
"zone_type": "half_candle"      # Zona = mitad de la vela OB
"max_atr_mult": 3.5             # Zona max = ATR(14) * 3.5
"expiry_candles": 100           # OB expira tras 100 velas M5 sin toque
"max_active_obs": 10            # Max 10 OBs activos simultáneos

"buffer_points": 25             # ✅ OPTIMIZADO (antes: 20)
"target_rr": 3.5                # ✅ OPTIMIZADO (antes: 2.5)
"min_risk_points": 15
"max_risk_points": 300
"min_rr_ratio": 1.2
"risk_per_trade_pct": 0.005     # 0.5% = $500 por trade

"sessions": {
    "new_york": {
        "start": "13:30",       # 9:30 AM EST
        "end": "20:00",         # 4:00 PM EST
        "skip_minutes": 15      # Opera desde 13:45 UTC
    }
}

"ema_trend_filter": False       # ❌ DESACTIVADO
"require_rejection": False      # ❌ DESACTIVADO
"require_bos": False            # ❌ DESACTIVADO (optimizado)
```

---

## ⚠️ DIFERENCIA CRÍTICA: LIVE vs BACKTEST OPTIMIZADO

| Aspecto | BOT LIVE (Actual) | BACKTEST OPTIMIZADO (Último) |
|---------|-------------------|------------------------------|
| **Tipo de orden** | MARKET (inmediata) | LIMIT (pendiente) |
| **Entry price** | `candle_close` | `zone_high` (LONG) / `zone_low` (SHORT) |
| **Activación** | Al cierre de vela M1 | Orden pendiente hasta OB destruido |
| **R:R** | 3.5 ✅ | 3.5 ✅ |
| **Buffer SL** | 25 pts ✅ | 25 pts ✅ |
| **Filtro BOS** | Desactivado ✅ | Desactivado ✅ |
| **Resultados** | ❓ (a determinar) | +30.91% / WR 29.4% |

---

## 🚨 HALLAZGO IMPORTANTE

**El bot live está usando MARKET orders, NO LIMIT orders.**

Esto significa:
- ✅ Los parámetros optimizados (R:R 3.5, Buffer 25, sin BOS) están aplicados
- ❌ La lógica de entrada LIMIT (orden pendiente en zone_high/zone_low) NO está implementada en live
- ⚠️ El bot entra a `candle_close`, que puede ser en cualquier punto dentro de la zona, no en el extremo óptimo

**Impacto esperado**: El bot live debería tener resultados similares al backtest MARKET optimizado, NO al backtest LIMIT optimizado (+30.91%).

---

## 📊 PRÓXIMO PASO

Ejecutar backtest con la configuración EXACTA del bot live:
- MARKET orders (entry = candle_close)
- R:R 3.5
- Buffer 25 puntos
- Sin filtro BOS
- Sesión NY 13:45-20:00 UTC
