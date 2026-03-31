# 📊 BACKTEST - CONFIGURACIÓN EXACTA BOT LIVE ACTUAL

**Fecha**: 30 Marzo 2026  
**Período**: 104 días (Dic 2025 - Mar 2026)  
**Tipo de orden**: MARKET (entry = candle_close)

---

## ⚙️ CONFIGURACIÓN EXACTA

### Detección OB (M5):
- **consecutive_candles**: 4 velas del mismo color
- **zone_type**: half_candle (mitad de la vela OB)
- **max_atr_mult**: 3.5
- **expiry_candles**: 100 velas M5
- **min_impulse_pct**: 0.0 (desactivado)

### Entrada (M1):
- **Tipo**: MARKET order (inmediata)
- **Entry price**: candle_close (cierre de vela M1)
- **Condición**: Vela M1 cierra dentro de zona OB
- **Sesión**: NY 13:45-20:00 UTC (skip_minutes=15)

### Gestión de Riesgo:
- **Buffer SL**: 25 puntos
- **Target R:R**: 3.5
- **Risk por trade**: 0.5% ($500)
- **Max trades simultáneos**: 2

### Filtros:
- **EMA 4H**: ❌ Desactivado
- **Rejection candle**: ❌ Desactivado
- **BOS**: ❌ Desactivado

---

## 📈 RESULTADOS GENERALES

| Métrica | Valor |
|---------|-------|
| **Balance inicial** | $100,000.00 |
| **Balance final** | $109,689.65 |
| **Retorno total** | **+9.69%** ($9,689.65) |
| **Max Drawdown** | **-10.69%** ($-10,690.83) |
| | |
| **Total trades** | 173 |
| **Ganadores** | 46 (26.6%) |
| **Perdedores** | 127 (73.4%) |
| **Win Rate** | **26.6%** |
| **Profit Factor** | **1.13** |
| | |
| **Avg Winner** | $1,831.19 |
| **Avg Loser** | $-586.97 |
| **Expectancy** | **$56.01** por trade |

---

## 📊 RESULTADOS POR DIRECCIÓN

### LONG:
- **Trades**: 128 (74% del total)
- **Win Rate**: 23.4%
- **PnL**: **-$2,350.95** ❌
- **Avg R**: -0.01R

### SHORT:
- **Trades**: 45 (26% del total)
- **Win Rate**: 35.6%
- **PnL**: **+$12,040.60** ✅
- **Avg R**: 0.49R

---

## 🚨 HALLAZGOS CRÍTICOS

### 1. DEPENDENCIA EXTREMA EN SHORT
- **100% de la rentabilidad** proviene de trades SHORT
- LONG es **PERDEDOR NETO** (-$2,351)
- Si el mercado no ofrece setups SHORT, el bot NO es rentable

### 2. MAX DRAWDOWN EXCEDE LÍMITE FTMO
- **DD máximo**: -10.69%
- **Límite FTMO Phase 1**: -10%
- ⚠️ **El bot habría sido descalificado** en este período

### 3. WIN RATE BAJO
- **26.6%** de efectividad
- Depende de R:R 3.5 para compensar
- 3 de cada 4 trades son perdedores

### 4. ERROR DETECTADO EN BACKTEST
- **1 trade LONG** tiene SL arriba del entry (Trade #69)
- Esto indica un posible bug residual en casos edge

---

## 📊 COMPARACIÓN: LIVE (MARKET) vs OPTIMIZADO (LIMIT)

| Métrica | LIVE (MARKET) | OPTIMIZADO (LIMIT) | Diferencia |
|---------|---------------|---------------------|------------|
| **Retorno** | +9.69% | +30.91% | **+21.22%** |
| **Trades** | 173 | 197 | +24 |
| **Win Rate** | 26.6% | 29.4% | +2.8% |
| **Max DD** | -10.69% | -6.62% | **-4.07%** |
| **Profit Factor** | 1.13 | 1.55 | +0.42 |
| **LONG PnL** | -$2,351 | +$5,148 | **+$7,499** |
| **SHORT PnL** | +$12,041 | +$25,743 | +$13,702 |

---

## 🎯 CONCLUSIÓN

### El bot live actual (MARKET orders):
✅ **Es rentable**: +9.69% en 104 días  
❌ **Excede DD límite FTMO**: -10.69% vs -10% permitido  
❌ **Dependiente de SHORT**: LONG es perdedor neto  
⚠️ **Win Rate bajo**: Solo 26.6%  

### La versión LIMIT (no implementada en live):
✅ **Mucho más rentable**: +30.91% (+220% mejor)  
✅ **DD controlado**: -6.62% (dentro de límites FTMO)  
✅ **LONG rentable**: +$5,148 vs -$2,351  
✅ **Win Rate mejor**: 29.4%  

---

## 🚀 RECOMENDACIÓN

**IMPLEMENTAR LÓGICA LIMIT EN EL BOT LIVE**

El backtest demuestra que cambiar de MARKET a LIMIT orders:
- Triplica la rentabilidad (+9.69% → +30.91%)
- Reduce DD en 38% (-10.69% → -6.62%)
- Hace LONG rentable (actualmente perdedor)
- Aumenta Win Rate y Profit Factor

**Archivos a modificar**:
1. `strategies/order_block/live/ob_monitor.py` → Generar señales LIMIT
2. `strategies/order_block/live/order_executor.py` → Ejecutar órdenes pendientes
3. Agregar gestión de órdenes pendientes en `trading_bot.py`

---

## ⚠️ RIESGO ACTUAL

Con la configuración MARKET actual, el bot:
- Tiene 73.4% de probabilidad de perder en cada trade
- Depende exclusivamente de que el mercado ofrezca setups SHORT
- Está al límite del DD permitido por FTMO

**El bot puede operar, pero está en el límite de viabilidad para FTMO.**
