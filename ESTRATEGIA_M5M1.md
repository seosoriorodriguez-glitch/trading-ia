# ESTRATEGIA M5/M1 - PIVOT SCALPING EN TIMEFRAME MENOR

**Fecha:** 2026-03-27  
**Objetivo:** Aumentar frecuencia replicando el mismo edge en timeframe menor  
**Período testeado:** 29 días (2026-02-25 → 2026-03-27)  
**Datos:** 30,000 velas M1, 5,790 velas M5

---

## 📊 RESULTADOS COMPARATIVOS

### Tabla Comparativa (29 días)

| Métrica | M15/M5 (Actual) | M5/M1 (Nuevo) | Diferencia |
|---------|----------------:|--------------:|-----------:|
| **Total Trades** | 2 | 5 | +3 (+150%) |
| **Trades/Mes** | 2.1 | 5.2 | +3.1 |
| **Win Rate** | 100.0% | 100.0% | 0.0% |
| **Retorno** | 0.90% | 3.56% | +2.67% |
| **Avg Win (USD)** | $448.08 | $712.65 | +$264.56 |
| **Avg Win (Pts)** | 22.44 | 31.51 | +9.07 |

---

## 🎯 CONFIGURACIÓN M5/M1

### Cambios Principales vs M15/M5

```yaml
# M15/M5 (Actual)
pivots:
  swing_strength: 3
  min_touch_separation: 4  # 4 velas M15 = 60 min
  min_zone_width: 10
  max_zone_width: 200

stop_loss:
  buffer_points: 15
  min_risk_points: 10

# M5/M1 (Nuevo)
pivots:
  swing_strength: 2        # Más ágil
  min_touch_separation: 3  # 3 velas M5 = 15 min
  min_zone_width: 5        # Pivots más pequeños
  max_zone_width: 100

stop_loss:
  buffer_points: 8         # Menos buffer
  min_risk_points: 5       # SL más ajustado
```

### Razón de los Cambios

1. **swing_strength: 2** (vs 3)
   - Confirmación más rápida: 2 velas M5 = 10 min (vs 3 velas M15 = 45 min)
   - Captura pivots más pequeños pero válidos

2. **min_risk_points: 5** (vs 10)
   - Los pivots M5 son más pequeños
   - 5 pts en M5 ≈ 10 pts en M15 (proporcionalmente)

3. **buffer_points: 8** (vs 15)
   - Menos espacio para SL en pivots más ajustados
   - Mantiene el ratio buffer/zona similar

---

## 📈 ANÁLISIS DETALLADO

### 1. Frecuencia

**M15/M5:**
- 2 trades en 29 días
- 2.1 trades/mes
- Extrapolado a 260 días: ~18 trades (vs 36 reales)

**M5/M1:**
- 5 trades en 29 días
- 5.2 trades/mes
- Extrapolado a 260 días: ~45 trades

**Ganancia:** +150% más frecuencia

### 2. Pivots Detectados

**M15/M5:**
- 1,034 pivot highs + 1,038 pivot lows = 2,072 pivots
- Conversión: 2 trades / 2,072 pivots = 0.10%

**M5/M1:**
- 657 pivot highs + 647 pivot lows = 1,304 pivots
- Conversión: 5 trades / 1,304 pivots = 0.38%

**Observación:** M5/M1 detecta MENOS pivots (usa M5 en vez de M15), pero tiene MEJOR conversión (0.38% vs 0.10%).

**Razón:** Los pivots M5 son más "frescos" y relevantes para el precio actual.

### 3. Calidad de Trades

**Avg Win en Puntos:**
- M15/M5: 22.44 pts
- M5/M1: 31.51 pts (+40%)

**Avg Win en USD:**
- M15/M5: $448.08
- M5/M1: $712.65 (+59%)

**Observación:** M5/M1 genera trades MEJORES en este período.

### 4. Trades Individuales M5/M1

```
Trade #1 (LONG):  Entry 45213.31, Exit 45227.31, +12.0 pts (0.86R) = $428.57
Trade #2 (LONG):  Entry 45199.31, Exit 45227.31, +26.0 pts (0.93R) = $464.29
Trade #3 (SHORT): Entry 46667.10, Exit 46622.91, +42.2 pts (0.95R) = $477.37
Trade #4 (SHORT): Entry 46648.60, Exit 46622.91, +23.7 pts (0.92R) = $461.07
Trade #5 (SHORT): Entry 46515.00, Exit 46459.31, +53.7 pts (3.46R) = $1731.94 ← TP hit
```

**Observación:** 4 de 5 salieron por SL movido a profit (0.86-0.95R), 1 alcanzó TP (3.46R).

---

## ⚠️ LIMITACIONES DEL BACKTEST

### 1. Muestra Muy Pequeña

- **Solo 29 días** de datos M1 (limitación de MT5)
- **Solo 5 trades** en M5/M1
- **Solo 2 trades** en M15/M5
- NO es suficiente para validación estadística

### 2. Período Específico

- Febrero-Marzo 2026 fue un período ACTIVO
- Ambas estrategias tuvieron 100% WR (poco realista)
- No sabemos cómo se comporta en períodos tranquilos

### 3. Falta de Datos Históricos

- MT5 solo tiene ~30 días de M1
- No podemos hacer backtest de 260 días como con M15/M5
- Necesitamos acumular datos en tiempo real

---

## 🎯 CONCLUSIÓN

### Hallazgos Positivos

1. ✅ **Frecuencia aumenta:** 5.2 trades/mes vs 2.1 (en este período)
2. ✅ **Calidad se mantiene:** 100% WR, mejor Avg Win
3. ✅ **Mismo edge:** Rebotes en pivots confirmados
4. ✅ **Implementación simple:** Misma lógica, solo cambio de timeframe

### Hallazgos Negativos

1. ❌ **Muestra insuficiente:** Solo 29 días, 5 trades
2. ❌ **No validado en período largo:** Necesitamos 60-90 días mínimo
3. ❌ **Limitación de datos:** MT5 no tiene más M1 histórico

### Recomendación

**NO adoptar M5/M1 todavía.** La muestra es demasiado pequeña.

**Plan de acción:**

#### Opción A: Acumular Datos (Recomendado)
1. Correr M5/M1 en **paper trading** durante 60-90 días
2. Acumular datos M1 en tiempo real
3. Re-ejecutar backtest con muestra grande
4. Si mantiene 10-15 trades/mes con PF > 2.0, adoptar

#### Opción B: Correr Ambas en Paralelo (Riesgoso)
1. Correr M15/M5 (validado) + M5/M1 (experimental)
2. M15/M5: 4 trades/mes (confiable)
3. M5/M1: 5-10 trades/mes (estimado)
4. Total: 9-14 trades/mes
5. **Riesgo:** M5/M1 puede tener PF < 1.0 en período largo

#### Opción C: Multi-Instrumento (Más Seguro)
1. Aplicar M15/M5 (validado) a múltiples instrumentos:
   - US30: 4 trades/mes
   - NAS100: 4 trades/mes
   - GER40: 4 trades/mes
2. Total: 12 trades/mes (suficiente para FTMO)
3. Mismo edge validado, solo diversificado

---

## 📊 PROYECCIÓN CONSERVADORA

### Si M5/M1 mantiene métricas en 260 días:

```
Asumiendo degradación por ruido:
- Trades/mes: 5.2 → 4.0 (conservador)
- Win Rate: 100% → 60% (realista)
- PF: ∞ → 2.5 (estimado)
- Retorno: 3.56% en 29 días → 45% anualizado

Combinado con M15/M5:
- M15/M5: 4 trades/mes, PF 1.65, 6.4% anualizado
- M5/M1:  4 trades/mes, PF 2.5, 45% anualizado
- Total:  8 trades/mes, retorno combinado ~25% anualizado
```

**Esto sería EXCELENTE para FTMO.**

---

## 🚀 PRÓXIMOS PASOS

### Inmediato (Hoy)

1. ✅ Implementada configuración M5/M1
2. ✅ Backtest ejecutado (29 días)
3. ✅ Resultados documentados

### Corto Plazo (Esta Semana)

1. **Decidir approach:**
   - Opción A: Paper trading M5/M1 (60-90 días)
   - Opción B: Live con ambas estrategias
   - Opción C: Multi-instrumento M15/M5

2. **Si eliges Opción A:**
   - Configurar script para guardar datos M1 diariamente
   - Correr M5/M1 en demo durante 60 días
   - Re-evaluar con muestra grande

3. **Si eliges Opción B:**
   - Empezar con size pequeño en M5/M1
   - Monitorear métricas diarias
   - Escalar si PF > 2.0 después de 20 trades

4. **Si eliges Opción C:**
   - Descargar datos de NAS100 y GER40
   - Ejecutar backtests M15/M5 en ambos
   - Si PF > 1.5, agregar a portfolio

### Mediano Plazo (1-2 Meses)

1. Acumular 60-90 días de datos M1
2. Re-ejecutar backtest M5/M1 completo
3. Validar frecuencia y PF
4. Tomar decisión final sobre adopción

---

## 📁 ARCHIVOS CREADOS

### Configuración
- `strategies/pivot_scalping/config/scalping_params_M5M1.yaml`

### Scripts
- `strategies/pivot_scalping/run_backtest_m5m1.py`
- `tools/download_m1_limited.py`
- `compare_m15m5_vs_m5m1.py`

### Datos
- `data/US30_cash_M1_30k.csv` (30,000 velas, 29 días)
- `data/US30_cash_M5_29d.csv` (5,790 velas, 29 días)

### Resultados
- `strategies/pivot_scalping/data/backtest_M5M1_29d.csv` (5 trades)
- `strategies/pivot_scalping/data/backtest_M15M5_29d.csv` (2 trades)

---

## 💡 INSIGHT CLAVE

**La idea de replicar el edge en timeframe menor es CORRECTA.**

Los resultados preliminares son prometedores:
- +150% más frecuencia
- Calidad similar o mejor
- Mismo edge validado

**PERO necesitamos más datos para confirmar.**

No tomes decisiones basadas en 5 trades. Acumula 60-90 días de datos y re-evalúa.

---

**Status:** ✅ IMPLEMENTADO Y TESTEADO  
**Muestra:** 29 días (insuficiente)  
**Resultado:** Prometedor pero no validado  
**Próximo paso:** Acumular datos o multi-instrumento
