# 📊 Análisis del Backtest - US30 (Dow Jones)

**Fecha**: 26 de Marzo 2026  
**Instrumento**: US30 (^DJI - Yahoo Finance)  
**Período**: 2 años (730 días: 27 Mar 2024 - 26 Mar 2026)  
**Balance Inicial**: $100,000  
**Datos**: 3,474 velas H1, 1,162 velas H4

---

## 📉 RESULTADOS GENERALES

| Métrica | Valor | Objetivo | Estado |
|---------|-------|----------|--------|
| **Balance Final** | $69,551.53 | > $100,000 | ❌ FAIL |
| **Retorno Total** | -30.45% | > 0% | ❌ FAIL |
| **Total Operaciones** | 174 | > 100 | ✅ PASS |
| **Win Rate** | 49.4% | >= 45% | ✅ PASS |
| **Ganadoras** | 86 | - | - |
| **Perdedoras** | 88 | - | - |
| **Profit Factor** | 1.31 | >= 1.5 | ❌ FAIL |
| **Max Drawdown** | 4.51% | < 8% | ✅ PASS |
| **Max Pérdidas Consecutivas** | 8 | - | ⚠️ Alto |
| **R:R Promedio Real** | 1.69 | >= 1.5 | ✅ PASS |

---

## 🔍 DIAGNÓSTICO

### ❌ Problemas Críticos

#### 1. Retorno Negativo (-30.45%)
**Problema**: La estrategia perdió $30,448 en 2 años.

**Posibles causas**:
- Parámetros no optimizados para US30
- Datos de Yahoo Finance pueden tener gaps o calidad diferente a MT5
- SL muy ajustado (80 puntos) para la volatilidad del Dow Jones
- Falsos quiebres (B1) tienen 47.2% WR pero pueden estar generando muchas señales

#### 2. Profit Factor Bajo (1.31)
**Problema**: Por cada $1 perdido, solo se ganan $1.31 (objetivo: >= $1.50)

**Interpretación**: Las operaciones ganadoras no compensan suficientemente las perdedoras, a pesar de tener R:R promedio de 1.69.

**Causa probable**: Muchas operaciones no alcanzan el TP completo, o el SL se dispara antes de tiempo.

### ⚠️ Señales de Alerta

#### 3. Max Pérdidas Consecutivas: 8
**Problema**: Racha de 8 pérdidas seguidas es alta.

**Impacto psicológico**: En trading real, esto puede causar pánico y desactivación del bot.

**Impacto en capital**: Con 0.5% de riesgo por trade, 8 pérdidas = -4% de drawdown.

### ✅ Aspectos Positivos

#### 1. Win Rate Aceptable (49.4%)
Casi 50% de trades ganadores es bueno para una estrategia de reversión.

#### 2. Max Drawdown Bajo (4.51%)
Cumple FTMO (< 8%) con margen de seguridad.

#### 3. R:R Promedio Real (1.69)
Supera el objetivo de 1.5:1.

#### 4. Suficientes Trades (174)
Muestra significativa estadísticamente.

---

## 📈 ANÁLISIS POR TIPO DE SEÑAL

| Tipo | Trades | Win Rate | Observación |
|------|--------|----------|-------------|
| **Pin Bar** | 30 (17%) | 60.0% | ✅ Mejor señal |
| **Engulfing** | 14 (8%) | 50.0% | ✅ Aceptable |
| **False Breakout B1** | 123 (71%) | 47.2% | ⚠️ Mayoría de trades, WR bajo |
| **False Breakout B2** | 7 (4%) | 42.9% | ⚠️ Pocas señales, WR bajo |

### Hallazgos Clave

1. **Pin Bar es la mejor señal** (60% WR) pero solo representa 17% de los trades
2. **False Breakout B1 domina** (71% de trades) pero tiene WR más bajo (47.2%)
3. **Desequilibrio**: La estrategia genera muchas señales B1 que no son rentables

---

## 🔧 RECOMENDACIONES DE OPTIMIZACIÓN

### Prioridad 1: Reducir Señales False Breakout B1

**Problema**: 123 trades con 47.2% WR están arrastrando el resultado.

**Solución**: Aumentar filtros de calidad para B1:

```yaml
# config/strategy_params.yaml
entry:
  false_breakout:
    b1_min_body_ratio: 0.50  # Aumentar de 0.40 a 0.50
    b1_min_penetration: 10   # Requerir penetración mínima de 10 puntos
```

**Efecto esperado**: Menos señales B1, pero de mayor calidad.

---

### Prioridad 2: Aumentar Peso de Pin Bar

**Problema**: Pin Bar tiene 60% WR pero solo 17% de trades.

**Solución**: Priorizar Pin Bar sobre B1 cuando ambos están presentes:

```python
# core/signals.py - evaluate_zone_for_signal()
# Cambiar orden de evaluación:
# 1. Pin bar primero
# 2. B1 segundo (con filtros más estrictos)
```

---

### Prioridad 3: Ajustar Stop Loss

**Problema**: SL de 80 puntos puede ser muy ajustado para US30.

**Análisis**: Necesitamos ver cuántos trades fueron stop-out vs TP-hit.

**Solución temporal**: Aumentar buffer:

```yaml
# config/instruments.yaml
US30:
  sl_buffer_points: 120  # Aumentar de 80 a 120
```

**Trade-off**: Peor R:R, pero menos stop-outs prematuros.

---

### Prioridad 4: Filtrar por Fuerza de Zona

**Problema**: No todas las zonas son iguales.

**Solución**: Solo operar zonas con >= 3 toques:

```yaml
# config/strategy_params.yaml
zone_detection:
  min_touches: 3  # Aumentar de 2 a 3
```

**Efecto**: Menos trades, pero en zonas más confiables.

---

### Prioridad 5: Filtro de R:R Más Estricto

**Problema**: Profit Factor bajo a pesar de R:R promedio de 1.69.

**Solución**: Aumentar R:R mínimo:

```yaml
# config/strategy_params.yaml
take_profit:
  min_rr_ratio: 2.0  # Aumentar de 1.5 a 2.0
```

**Efecto**: Menos trades, pero cada uno con mayor potencial de ganancia.

---

## 🎯 PLAN DE ACCIÓN

### Fase 1: Análisis Detallado (HOY)

1. **Revisar CSV de trades**:
   ```bash
   python analyze_backtest.py data/backtest_US30.csv
   ```

2. **Analizar distribución**:
   - ¿Cuántos trades fueron stop-out vs TP-hit?
   - ¿Cuál es el P&L promedio de ganadoras vs perdedoras?
   - ¿Hay patrones temporales (hora del día, día de la semana)?

3. **Visualizar equity curve**:
   - ¿Dónde están las grandes pérdidas?
   - ¿Hay períodos específicos problemáticos?

### Fase 2: Optimización (Semana 1)

1. **Ajuste 1**: Aumentar `b1_min_body_ratio` a 0.50
2. **Ajuste 2**: Aumentar `sl_buffer_points` a 120
3. **Ajuste 3**: Aumentar `min_touches` a 3
4. **Re-ejecutar backtest** y comparar

### Fase 3: Validación (Semana 2)

1. Si los ajustes mejoran el Profit Factor a >= 1.5:
   - Ejecutar backtest en NAS100 y SPX500
   - Verificar consistencia entre índices

2. Si los ajustes NO mejoran:
   - Revisar la lógica de detección de zonas
   - Considerar añadir filtro de tendencia (H4/D1)
   - Evaluar si la estrategia es viable para índices

---

## 📊 MÉTRICAS FTMO

| Regla FTMO | Resultado | Estado |
|------------|-----------|--------|
| **Max Daily Drawdown < 5%** | 4.51% | ✅ PASS |
| **Max Total Drawdown < 10%** | 4.51% | ✅ PASS |
| **Profit Target Phase 1 (10%)** | -30.45% | ❌ FAIL |

**Conclusión FTMO**: La estrategia cumple con los límites de drawdown, pero NO genera ganancias. No pasaría el FTMO Challenge.

---

## 🚨 SEÑALES DE ADVERTENCIA

1. **Retorno negativo**: La estrategia pierde dinero en el período probado
2. **Profit Factor < 1.5**: No cumple el objetivo mínimo
3. **Balance final < inicial**: Pérdida neta de $30,448

**Recomendación**: **NO usar en trading real** hasta optimizar y obtener resultados positivos.

---

## 💡 HIPÓTESIS A INVESTIGAR

### 1. Calidad de Datos de Yahoo Finance
**Hipótesis**: Los datos de Yahoo Finance pueden tener:
- Gaps en horarios no líquidos
- Precios ajustados que no reflejan el trading real
- Falta de datos de volumen precisos

**Validación**: Comparar con datos de MT5 o broker real.

### 2. Parámetros No Optimizados
**Hipótesis**: Los parámetros actuales fueron diseñados para otro instrumento o período.

**Validación**: Ejecutar optimización de parámetros (walk-forward).

### 3. Estrategia No Apta para Índices
**Hipótesis**: La estrategia de S/R funciona mejor en Forex que en índices.

**Validación**: Probar en GBP/JPY (Fase 2) y comparar resultados.

### 4. Período Específico Problemático
**Hipótesis**: 2024-2026 fue un período de tendencia fuerte donde S/R no funciona bien.

**Validación**: Probar en períodos diferentes (2022-2024, 2020-2022).

---

## 📋 CHECKLIST DE VALIDACIÓN

Antes de proceder a paper trading, la estrategia DEBE cumplir:

- [ ] Retorno total > 0% (actualmente: -30.45%)
- [ ] Profit Factor >= 1.5 (actualmente: 1.31)
- [ ] Max Drawdown < 8% (actualmente: 4.51% ✅)
- [ ] Win Rate >= 45% (actualmente: 49.4% ✅)
- [ ] R:R promedio >= 1.5 (actualmente: 1.69 ✅)
- [ ] Balance final > inicial (actualmente: $69,551 < $100,000)

**Estado**: 3/6 criterios cumplidos. **NO LISTO** para paper trading.

---

## 🎓 APRENDIZAJES

1. **Win Rate alto no garantiza rentabilidad**: 49.4% WR pero -30% retorno
2. **Calidad sobre cantidad**: 123 señales B1 con 47% WR arrastran el resultado
3. **Pin Bar es oro**: 60% WR en solo 30 trades
4. **Optimización necesaria**: Los parámetros por defecto no funcionan

---

## 🚀 PRÓXIMOS PASOS INMEDIATOS

### 1. Analizar Trades Individuales (HOY)
```bash
python analyze_backtest.py data/backtest_US30.csv
```

### 2. Revisar Distribución de P&L
- ¿Las pérdidas son consistentes o hay outliers?
- ¿Las ganancias son pequeñas vs pérdidas grandes?

### 3. Optimizar Parámetros (Esta Semana)
- Aumentar filtros de calidad para B1
- Ajustar SL buffer
- Priorizar Pin Bar

### 4. Re-ejecutar Backtest
```bash
# Después de ajustar parámetros
python run_backtest.py \
  --data-h1 data/US30_H1_730d.csv \
  --data-h4 data/US30_H4_730d.csv \
  --instrument US30 \
  --output data/backtest_US30_v2.csv
```

### 5. Comparar Resultados
- ¿Mejoró el Profit Factor?
- ¿Mejoró el retorno total?
- ¿Se mantuvo el Max DD bajo?

---

## ⚠️ ADVERTENCIA CRÍTICA

**NO PROCEDER A PAPER TRADING O LIVE TRADING** hasta que:

1. ✅ Profit Factor >= 1.5
2. ✅ Retorno total > 0%
3. ✅ Balance final > inicial
4. ✅ Resultados validados en múltiples períodos

**Usar dinero real con estos resultados sería irresponsable.**

---

## 📚 Recursos para Optimización

- **Archivo de trades**: `data/backtest_US30.csv`
- **Script de análisis**: `analyze_backtest.py`
- **Configuración**: `config/strategy_params.yaml`
- **Documentación**: `ANALISIS_TECNICO.md`

---

**Conclusión**: La estrategia tiene potencial (49.4% WR, buen R:R) pero necesita optimización significativa antes de ser viable. Los datos están listos, el código funciona, ahora toca iterar en los parámetros.

**Siguiente paso**: Ejecutar `analyze_backtest.py` para análisis profundo.
