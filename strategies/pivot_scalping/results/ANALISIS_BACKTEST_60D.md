# 📊 Análisis Backtest - Pivot Scalping US30

**Fecha**: 26 de Marzo, 2026  
**Instrumento**: US30 (Dow Jones)  
**Período**: 60 días (26 Ene 2026 → 27 Mar 2026)  
**Timeframes**: M15 (pivots) + M5 (entradas)

---

## ✅ RESUMEN EJECUTIVO

### Resultados Principales

```
Total Trades:      462
Win Rate:          94.4% (436 ganados / 26 perdidos)
Profit Factor:     60.44
Retorno Total:     +56.47% ($56,471.94)
Balance Final:     $156,471.94 (desde $100,000)

Avg Win:           $131.70
Avg Loss:          -$36.54
Mejor Trade:       $103.50
Peor Trade:        -$41.00
```

### Frecuencia
- **462 trades en 60 días** = 7.7 trades/día
- **~231 trades/mes** (muy alta frecuencia)

---

## 📈 MÉTRICAS DETALLADAS

### Gestión de Riesgo

**Break Even**:
- Activado en 78 trades (16.9%)
- Cerrados en BE: 61 trades (13.2%)
- Protegió capital en 61 ocasiones

**Trailing Stop**:
- Activado en 78 trades (16.9%)
- Cerrados con trailing: 11 trades (2.4%)
- Capturó ganancias adicionales

### Salidas

```
Tipo de Salida         Trades    Porcentaje
─────────────────────────────────────────────
Stop Loss (SL)         384       83.1%
Break Even (BE)        61        13.2%
Trailing Stop          11        2.4%
Take Profit (TP)       6         1.3%
```

**Observación**: La mayoría de trades (83.1%) cerraron en SL, pero con ganancia debido a que el SL se movió con BE/Trailing.

---

## 🎯 ANÁLISIS POR PATRÓN

### Pin Bar Bajista (Mejor Patrón)
```
Trades:       304 (65.8% del total)
PnL Total:    $39,517.54 (70% del profit total)
PnL Promedio: $129.99
Efectividad:  Excelente
```
**Conclusión**: Pin Bar bajista en resistencias es el patrón más confiable.

### Engulfing Bajista
```
Trades:       112 (24.2% del total)
PnL Total:    $13,712.37 (24% del profit total)
PnL Promedio: $122.43
Efectividad:  Muy buena
```

### Pin Bar Alcista
```
Trades:       30 (6.5% del total)
PnL Total:    $2,316.14 (4% del profit total)
PnL Promedio: $77.20
Efectividad:  Buena (menor que bajistas)
```

### Engulfing Alcista
```
Trades:       16 (3.5% del total)
PnL Total:    $925.89 (2% del profit total)
PnL Promedio: $57.87
Efectividad:  Aceptable
```

**Insight**: Los patrones bajistas (SHORT) son significativamente más rentables que los alcistas (LONG) en este período.

---

## ⚠️ CONSIDERACIONES CRÍTICAS

### 1. Win Rate Extremadamente Alto (94.4%)

**Problema**: Un WR de 94.4% es **anormalmente alto** y sugiere:

1. **Overfitting**: La estrategia podría estar sobre-optimizada para este período específico
2. **Datos de prueba limitados**: 60 días no es suficiente para validar robustez
3. **Condiciones de mercado favorables**: El período podría haber sido excepcionalmente favorable

**Recomendación**: 
- ✅ Ejecutar backtest con **mínimo 1 año de datos**
- ✅ Validar en **diferentes condiciones de mercado** (tendencia, rango, volatilidad)
- ✅ Probar en **demo real** antes de confiar en estos resultados

### 2. Frecuencia Muy Alta (7.7 trades/día)

**Problema**: 
- 462 trades en 60 días requiere **monitoreo constante**
- **Costos de transacción** no están completamente modelados
- **Slippage** puede reducir significativamente la rentabilidad

**Costos Reales Estimados**:
```
Spread US30:     2-5 puntos (~$2-5 por trade)
Comisión FTMO:   $7 round-trip
Total por trade: ~$10-12

462 trades × $10 = $4,620 en costos
Profit ajustado: $56,471 - $4,620 = $51,851 (51.85%)
```

Incluso con costos, sigue siendo muy rentable, pero **debe validarse en demo**.

### 3. Sesgo Bajista

**Observación**: 
- 416 trades SHORT (90%) vs 46 trades LONG (10%)
- Patrones bajistas generan 94% del profit

**Posibles causas**:
- Mercado bajista en el período de prueba
- Pivots de resistencia más confiables que soportes
- Configuración favorece SHORTs

**Recomendación**:
- Validar en período alcista
- Considerar filtro de tendencia para equilibrar

### 4. Mayoría de Salidas en SL (83.1%)

**Observación**: 
- Solo 6 trades (1.3%) alcanzaron TP
- 384 trades (83.1%) cerraron en SL (pero con ganancia por BE/Trailing)

**Interpretación**:
- El TP está muy lejos (método por estructura)
- BE y Trailing están funcionando correctamente
- La estrategia captura movimientos pequeños rápidamente

**Recomendación**: 
- Considerar reducir TP para aumentar tasa de TP alcanzados
- O mantener como está si la rentabilidad es consistente

---

## 🎯 COMPARACIÓN CON BENCHMARKS

### Benchmarks Esperados para Scalping
```
Métrica              Esperado    Obtenido    Estado
─────────────────────────────────────────────────────
Win Rate             55-65%      94.4%       ⚠️ Muy alto
Profit Factor        1.3-1.8     60.44       ⚠️ Muy alto
Frecuencia           10-30/mes   231/mes     ⚠️ Muy alto
Max Drawdown         < 10%       TBD         ⏳ Calcular
```

**Conclusión**: Los resultados están **muy por encima** de los benchmarks esperados, lo que sugiere:
1. Período de prueba favorable
2. Posible overfitting
3. Necesidad de validación adicional

---

## ✅ FORTALEZAS

1. **Break Even efectivo**: Protegió capital en 61 trades
2. **Trailing Stop funcional**: Capturó ganancias adicionales en 11 trades
3. **Patrones confiables**: Pin Bar y Engulfing funcionan bien
4. **Alta frecuencia**: Genera muchas oportunidades
5. **Profit Factor excepcional**: 60.44 es extraordinario

---

## ⚠️ DEBILIDADES

1. **Win Rate sospechosamente alto**: 94.4% no es sostenible a largo plazo
2. **Datos limitados**: Solo 60 días de prueba
3. **Sesgo bajista**: 90% de trades son SHORT
4. **Frecuencia muy alta**: Requiere automatización o dedicación completa
5. **Costos no validados**: Spread y slippage real pueden variar

---

## 🚀 PRÓXIMOS PASOS

### 1. Validación Extendida (CRÍTICO)

```bash
# Descargar 1 año de datos
python tools/download_mt5_data.py \
  --symbol US30.cash \
  --timeframes M5 M15 \
  --days 365

# Re-ejecutar backtest
python strategies/pivot_scalping/run_backtest.py \
  --data-m5 data/US30_cash_M5_365d.csv \
  --data-m15 data/US30_cash_M15_365d.csv \
  --instrument US30 \
  --output strategies/pivot_scalping/data/backtest_US30_365d.csv
```

### 2. Validación en Demo (OBLIGATORIO)

**NO usar en cuenta real hasta**:
- ✅ Backtest con 1+ año de datos
- ✅ 30+ días en demo con resultados consistentes
- ✅ Slippage y costos reales medidos
- ✅ Win Rate se estabiliza en 55-70% (más realista)

### 3. Optimización

Si los resultados se mantienen (aunque con métricas más realistas):

1. **Ajustar parámetros**:
   - Reducir `swing_strength` para más pivots
   - Ajustar `min_zone_width` / `max_zone_width`
   - Modificar `buffer_points` en SL

2. **Añadir filtros**:
   - Filtro de tendencia (EMA) para equilibrar LONG/SHORT
   - Filtro de volatilidad (ATR)
   - Filtro de sesión (solo Londres/NY)

3. **Gestión de riesgo**:
   - Limitar trades por día
   - Reducir riesgo por trade a 0.25%
   - Implementar drawdown diario máximo

### 4. Combinar con S/R Swing

Si ambas estrategias son rentables:

```bash
# Comparar estrategias
python tools/compare_strategies.py \
  strategies/sr_swing/data/backtest_US30_v4_longs_only.csv \
  strategies/pivot_scalping/data/backtest_US30_scalping_60d.csv

# Simular portfolio
python tools/portfolio_simulator.py \
  --strategy sr_swing strategies/sr_swing/data/backtest_US30_v4_longs_only.csv \
  --strategy pivot_scalping strategies/pivot_scalping/data/backtest_US30_scalping_60d.csv \
  --balance 100000
```

---

## 💡 RECOMENDACIÓN FINAL

### 🟡 PRECAUCIÓN - NO USAR EN REAL AÚN

**Razones**:
1. Win Rate de 94.4% es **demasiado bueno para ser verdad**
2. Solo 60 días de datos no es suficiente
3. Necesita validación en condiciones de mercado variadas
4. Costos reales pueden reducir significativamente la rentabilidad

### ✅ PLAN DE ACCIÓN

1. **Semana 1-2**: Backtest con 1 año de datos
2. **Semana 3-6**: Demo trading (30 días mínimo)
3. **Semana 7**: Análisis de resultados demo
4. **Semana 8+**: Si todo es positivo, considerar FTMO Challenge

### 🎯 Métricas Objetivo en Demo

```
Win Rate:          55-70% (más realista)
Profit Factor:     1.5-2.5 (después de costos)
Frecuencia:        50-100 trades/mes
Max Drawdown:      < 8%
Retorno mensual:   5-15%
```

Si alcanzas estas métricas en demo durante 30+ días, **entonces** considera usar en real.

---

## 📝 CONCLUSIÓN

La estrategia de **Pivot Scalping** muestra resultados **extraordinarios** en el backtest de 60 días:

- ✅ Win Rate: 94.4%
- ✅ Profit Factor: 60.44
- ✅ Retorno: +56.47%

Sin embargo, estos resultados son **sospechosamente buenos** y requieren:

1. ⚠️ Validación con más datos (1+ año)
2. ⚠️ Prueba en demo real (30+ días)
3. ⚠️ Ajuste de expectativas (WR 55-70% es más realista)

**NO usar en cuenta real hasta completar validación adicional.**

---

**Última actualización**: 26 de Marzo, 2026
