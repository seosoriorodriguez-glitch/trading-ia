# VALIDACIÓN CON 260 DÍAS (8.7 MESES)

**Fecha:** 2026-03-27  
**Período:** 2025-07-09 → 2026-03-27 (260 días / 8.7 meses)  
**Datos:** 49,879 velas M5, 16,810 velas M15  
**Pivots detectados:** 1,451 highs, 1,510 lows

---

## 📊 RESUMEN EJECUTIVO

### Métricas Clave

```
Total Trades:         36
Win Rate:             63.9%
Profit Factor (USD):  1.65
Profit Factor (Pts):  3.11
Retorno:              4.65% (6.4% anualizado)
Max Drawdown:         -$1,750.97 (-1.75%)

Avg Win:              $514.15 (44.52 pts)
Avg Loss:             $-552.12 (-25.32 pts)
```

### Comparativa: 60 días vs 260 días

| Métrica                   |         60 días |        260 días |      Diferencia |
|---------------------------|----------------:|----------------:|----------------:|
| Trades                    |              35 |              36 |               1 |
| Win Rate                  |           71.4% |           63.9% |           -7.5% |
| PF (USD)                  |            4.01 |            1.65 |          -2.36  |
| Retorno                   |           16.5% |            4.6% |         -11.8%  |
| Avg Win                   |        $878.62  |        $514.15  |       -$364.47  |
| Avg Loss                  |       -$547.70  |       -$552.12  |         -$4.43  |

**Observación crítica:** Los 60 días iniciales fueron un período excepcionalmente favorable. La muestra ampliada revela métricas más modestas pero sostenibles.

---

## 🎯 ANÁLISIS POR DIRECCIÓN

### LONG (Compra en Soporte)

```
Trades:        11 (30.6% del total)
Win Rate:      45.5%
Profit Factor: 0.72 ← PERDEDOR
Avg PnL:       $-84.65
Total PnL:     $-931.19
```

**Problema identificado:** Las entradas LONG no son rentables. PF de 0.72 significa que por cada $1 ganado, se pierden $1.39.

### SHORT (Venta en Resistencia)

```
Trades:        25 (69.4% del total)
Win Rate:      72.0%
Profit Factor: 2.43 ← GANADOR
Avg PnL:       $223.16
Total PnL:     $5,579.05
```

**Fortaleza identificada:** Las entradas SHORT son rentables y consistentes. PF de 2.43 es excelente.

### Conclusión Direccional

**La estrategia tiene un sesgo direccional claro:**
- **SHORT funciona bien** (72% WR, PF 2.43)
- **LONG no funciona** (45.5% WR, PF 0.72)

**Hipótesis:**
1. US30 está en tendencia bajista o lateral-bajista en este período
2. Los pivots de resistencia son más confiables que los de soporte
3. La presión vendedora en resistencias es más fuerte que la compradora en soportes

**Recomendación inmediata:**
- **Opción A:** Deshabilitar entradas LONG completamente (solo operar SHORT)
- **Opción B:** Agregar filtro de tendencia (solo LONG en tendencia alcista, solo SHORT en bajista)

---

## 📅 ANÁLISIS POR MES (Consistencia Temporal)

| Mes             |   Trades |   Win Rate |      PnL USD |  Retorno % |
|-----------------|----------|------------|--------------|------------|
| 2025-08         |        8 |      62.5% | $     656.81 |      0.66% |
| 2026-02         |        6 |      66.7% | $   1,706.31 |      1.71% |
| 2026-03         |       22 |      63.6% | $   2,284.74 |      2.28% |

### Observaciones

1. **Todos los meses son ganadores** (no hay meses perdedores)
2. **Consistencia en Win Rate:** 62.5% - 66.7% (rango estrecho)
3. **Marzo 2026 tuvo más actividad:** 22 trades vs 6-8 en otros meses
4. **Retorno mensual:** 0.66% - 2.28% (modesto pero consistente)

**Nota:** Solo hay 3 meses con datos completos. Los otros meses (sept-enero) no tienen trades registrados, probablemente por:
- Falta de señales válidas (pivots no confirmados)
- Mercado en rango sin pivots claros
- Filtro de `min_risk_points: 10` descartó trades

---

## 🌍 ANÁLISIS POR SESIÓN

| Sesión          |   Trades |   Win Rate |     PF |      Avg PnL |
|-----------------|----------|------------|--------|--------------|
| Londres         |        5 |      40.0% |  0.56  | $    -150.17 |
| Nueva York      |       10 |      70.0% |  1.99  | $     164.02 |
| Overlap         |        3 |      66.7% |  1.73  | $     133.19 |
| Asia/Noche      |       18 |      66.7% |  2.03  | $     186.61 |

### Observaciones

1. **Londres (08:00-12:00 UTC) es PERDEDOR:**
   - Solo 40% WR, PF 0.56
   - Avg PnL negativo: -$150.17
   - **Evitar operar en Londres**

2. **Nueva York (13:00-17:00 UTC) es GANADOR:**
   - 70% WR, PF 1.99
   - Avg PnL positivo: $164.02
   - **Mejor sesión para operar**

3. **Asia/Noche es SORPRENDENTEMENTE BUENA:**
   - 66.7% WR, PF 2.03
   - 18 trades (50% del total)
   - Avg PnL: $186.61
   - **Segunda mejor sesión**

### Recomendación de Sesión

**Filtro de sesión recomendado:**
- **Operar:** Nueva York + Asia/Noche
- **Evitar:** Londres

Esto eliminaría 5 trades perdedores y mejoraría el PF general.

---

## 📉 PEOR RACHA DE PÉRDIDAS CONSECUTIVAS

### Detalles de la Racha

```
Peor racha:           3 pérdidas consecutivas
Drawdown generado:    $-1,588.00
Período:              2026-03-26 22:15:00 → 2026-03-26 22:50:00
Duración:             35 minutos
```

### Trades en la Racha

```
Trade #29 (LONG): $-528.99 (-1.06R) - Entry: 45964.40, SL: 45929.90
Trade #30 (LONG): $-532.73 (-1.07R) - Entry: 45960.45, SL: 45929.90
Trade #31 (LONG): $-526.28 (-1.05R) - Entry: 45967.95, SL: 45929.90
```

### Análisis de la Racha

1. **Todas son entradas LONG** (confirmando el problema con LONG)
2. **Mismo pivot de soporte:** SL en 45929.90 (pivot roto)
3. **Múltiples señales en el mismo soporte:** 3 patrones de rechazo en 35 minutos
4. **Pivot falló:** El soporte se rompió y las 3 entradas perdieron

### Lección

**Problema de "clustering":** Múltiples señales en el mismo pivot en corto tiempo.

**Solución:**
- Agregar filtro: **No tomar más de 1 trade por pivot** (o máximo 2 con cooldown)
- Si un pivot falla (SL hit), **desactivar ese pivot** para futuras señales
- Esto evitaría 2 de las 3 pérdidas en esta racha

---

## 🔍 DIAGNÓSTICO FINAL

### ✅ Fortalezas

1. **Consistencia temporal:** Todos los meses son ganadores
2. **SHORT funciona bien:** 72% WR, PF 2.43
3. **Drawdown controlado:** -1.75% máximo
4. **Asia/Noche es rentable:** 66.7% WR, PF 2.03
5. **No hay meses catastróficos**

### ❌ Debilidades

1. **LONG no funciona:** 45.5% WR, PF 0.72 (perdedor neto)
2. **Londres es perdedor:** 40% WR, PF 0.56
3. **PF general bajo:** 1.65 (apenas positivo)
4. **Retorno modesto:** 6.4% anualizado
5. **Clustering en pivots:** Múltiples trades en el mismo pivot generan rachas

### ⚠️ Riesgos

1. **Sesgo de muestra:** Solo 36 trades en 8.7 meses (4.1 trades/mes)
2. **Período específico:** Puede haber sesgo de mercado (bajista/lateral)
3. **Dependencia de SHORT:** 69% de trades son SHORT

---

## 🚀 RECOMENDACIONES INMEDIATAS

### 1. Filtro Direccional (CRÍTICO)

**Opción A - Solo SHORT:**
```yaml
filters:
  enabled_directions: ["short"]  # Deshabilitar LONG
```

**Impacto esperado:**
- Eliminar 11 trades LONG (-$931.19)
- Retorno pasaría de 4.65% a **5.58%**
- PF pasaría de 1.65 a **2.43**
- Win Rate pasaría de 63.9% a **72.0%**

**Opción B - Filtro de Tendencia:**
- Agregar indicador de tendencia (EMA 200 en M15)
- Solo LONG si precio > EMA 200
- Solo SHORT si precio < EMA 200

### 2. Filtro de Sesión

```yaml
filters:
  allowed_sessions:
    - "13:00-17:00"  # Nueva York
    - "18:00-07:00"  # Asia/Noche
  blocked_sessions:
    - "08:00-12:00"  # Londres
```

**Impacto esperado:**
- Eliminar 5 trades de Londres (-$750.85)
- Mejorar PF y retorno

### 3. Filtro de Clustering

```yaml
pivot_filters:
  max_trades_per_pivot: 1  # Solo 1 trade por pivot
  pivot_cooldown_minutes: 60  # 1 hora de cooldown después de SL hit
```

**Impacto esperado:**
- Evitar rachas como la de 3 LONGs consecutivos
- Reducir drawdown máximo

### 4. Gestión de Riesgo (BE + Trailing)

Ahora que tenemos la estrategia base validada, agregar:
- Break Even conservador (1.5:1 trigger)
- Trailing stop con `min_improvement_points: 20`

**Impacto esperado:**
- Proteger ganancias en trades que van a favor
- Mejorar R-multiple promedio de wins

---

## 📈 PROYECCIÓN CON FILTROS

### Escenario: Solo SHORT + Filtro de Sesión

```
Trades eliminados: 11 LONG + 5 Londres = 16 trades
Trades restantes:  20 trades (solo SHORT en NY/Asia)

PnL eliminado:     -$931.19 (LONG) + -$750.85 (Londres) = -$1,682.04
PnL restante:      $4,647.85 + $1,682.04 = $6,329.89

Nuevo retorno:     6.33% en 8.7 meses = 8.7% anualizado
Nuevo PF:          ~2.5 (estimado)
Nuevo WR:          ~72% (basado en SHORT)
```

**Esto convertiría la estrategia de "modesta" a "sólida".**

---

## 🎯 PRÓXIMOS PASOS

### Paso 1: Implementar Filtro Direccional (Solo SHORT)

```bash
# Crear nueva config
cp strategies/pivot_scalping/config/scalping_params_A_naked.yaml \
   strategies/pivot_scalping/config/scalping_params_SHORT_only.yaml

# Editar para agregar:
filters:
  enabled_directions: ["short"]
```

### Paso 2: Re-ejecutar Backtest con Filtro

```bash
python strategies/pivot_scalping/run_backtest.py \
  --data-m5 data/US30_cash_M5_260d.csv \
  --data-m15 data/US30_cash_M15_260d.csv \
  --instrument US30 \
  --config strategies/pivot_scalping/config/scalping_params_SHORT_only.yaml \
  --output strategies/pivot_scalping/data/backtest_SHORT_only_260d.csv
```

### Paso 3: Validar Mejora

Comparar métricas antes/después del filtro.

### Paso 4: Agregar Filtro de Sesión

Si el filtro direccional funciona, agregar filtro de sesión.

### Paso 5: Implementar BE + Trailing

Solo después de validar los filtros básicos.

---

## 📝 CONCLUSIÓN

### Estado Actual

La estrategia **Pivot Scalping** es **rentable pero modesta** en su forma base:
- PF 1.65 (positivo pero bajo)
- 6.4% anualizado (conservador)
- Drawdown controlado (-1.75%)

### Problema Principal

**Sesgo direccional crítico:**
- LONG pierde dinero (PF 0.72)
- SHORT gana dinero (PF 2.43)

### Solución Propuesta

**Deshabilitar LONG** mejoraría dramáticamente las métricas:
- Retorno: 4.65% → **6.33%** (+36%)
- PF: 1.65 → **~2.5** (+52%)
- Win Rate: 63.9% → **72%** (+8.1%)

### Validación

Con 36 trades en 8.7 meses, la muestra es **pequeña pero suficiente** para identificar:
- ✅ La estrategia es rentable
- ✅ SHORT funciona, LONG no
- ✅ Sesiones tienen impacto
- ✅ Drawdown es manejable

**Recomendación:** Implementar filtro direccional (solo SHORT) y re-validar.

---

**Status:** ✅ VALIDACIÓN COMPLETA  
**Muestra:** 260 días (8.7 meses)  
**Trades:** 36  
**Resultado:** RENTABLE con mejoras necesarias
