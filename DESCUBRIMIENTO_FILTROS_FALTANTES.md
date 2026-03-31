# 🔍 DESCUBRIMIENTO: Filtros Faltantes en LIMIT Orders

## ❌ PROBLEMA IDENTIFICADO

El backtester de **LIMIT orders** genera **MÁS trades** (205) que el backtester **MARKET** (104), cuando debería generar MENOS por ser más restrictivo.

### Comparación de Trades

| Métrica | MARKET | LIMIT | Diferencia |
|---------|--------|-------|------------|
| **Total Trades** | 104 | 205 | **+101 (+97%)** |
| LONG | 46 | 105 | +59 (+128%) |
| SHORT | 58 | 100 | +42 (+72%) |
| **Profitability** | +19.92% | +24.10% | +4.18% |

---

## 🔎 CAUSA RAÍZ

El backtester **LIMIT** (`backtester_limit_orders.py`) **NO aplica** los filtros de confirmación que sí aplica el backtester **MARKET** (`signals.py`).

### Filtros en MARKET (signals.py)

```python
# Líneas 216-225
# Filtro de tendencia EMA 4H
if trend_bias is not None and direction != trend_bias:
    continue

# Filtro 1: vela de rechazo
if not check_rejection(candle, prev_candle, direction, params):
    continue

# Filtro 2: BOS
if not check_bos(recent_candles, direction, params):
    continue
```

### Filtros en LIMIT (backtester_limit_orders.py)

```python
# Líneas 171-186
# Verificar si vela cierra DENTRO de la zona
if ob.ob_type == "bullish":
    if candle_close < ob.zone_low or candle_close > ob.zone_high:
        continue
    direction = "long"
    entry_price = ob.zone_high
else:
    if candle_close < ob.zone_low or candle_close > ob.zone_high:
        continue
    direction = "short"
    entry_price = ob.zone_low

# Calcular SL/TP
sl, tp = self._calculate_sl_tp_limit(ob, entry_price)
if sl is None:
    continue

# ❌ NO HAY FILTROS DE:
# - Rechazo (rejection candle)
# - BOS (Break of Structure)
# - Tendencia EMA 4H
```

---

## 📊 IMPACTO

### 1. Más Trades Generados

Sin los filtros de confirmación, el backtester LIMIT acepta **casi el doble** de trades:
- **MARKET**: 104 trades (con 3 filtros)
- **LIMIT**: 205 trades (sin filtros)

### 2. Mejor Profitability

Paradójicamente, generar más trades resulta en **mejor profitability**:
- **MARKET**: +19.92%
- **LIMIT**: +24.10%

Esto sugiere que:
1. Los filtros de MARKET son **demasiado restrictivos**
2. O los filtros están **rechazando trades buenos**

### 3. Win Rate

| Backtest | Win Rate | Trades |
|----------|----------|--------|
| MARKET | 39.4% | 104 |
| LIMIT | 40.5% | 205 |

El Win Rate es similar, pero LIMIT captura **más oportunidades**.

---

## 🤔 ANÁLISIS

### ¿Por qué LIMIT es más rentable sin filtros?

**Hipótesis 1: Entry timing superior**
- MARKET entra al close de M1 (variable)
- LIMIT entra en zone_high/low (fijo, mejor precio)
- → Mejor R:R efectivo

**Hipótesis 2: Filtros demasiado restrictivos**
- Filtro de rechazo puede ser demasiado estricto
- Filtro de BOS puede rechazar trades válidos
- → Pierden oportunidades rentables

**Hipótesis 3: Consistencia de riesgo**
- MARKET: Entry variable → Riesgo variable
- LIMIT: Entry fijo → Riesgo consistente
- → Más trades pasan filtros de riesgo (min/max)

---

## ✅ SOLUCIÓN PROPUESTA

### Opción 1: Agregar filtros a LIMIT (Conservador)

Aplicar los mismos filtros de MARKET en LIMIT:
- ✅ Mantiene coherencia con estrategia original
- ✅ Reduce trades a nivel similar (~100)
- ❌ Reduce profitability potencial

### Opción 2: Mantener LIMIT sin filtros (Agresivo)

Dejar LIMIT como está:
- ✅ Mayor profitability (+24% vs +19%)
- ✅ Más trades (205 vs 104)
- ❌ Diverge de estrategia original
- ❌ Puede ser menos robusto

### Opción 3: Filtros opcionales (Flexible)

Agregar parámetro para activar/desactivar filtros:
```python
"use_confirmation_filters": True/False
```
- ✅ Permite testing de ambas versiones
- ✅ Usuario decide nivel de agresividad
- ❌ Más complejidad

---

## 🎯 RECOMENDACIÓN

**Agregar los filtros de confirmación a LIMIT** (Opción 1)

### Razones:

1. **Coherencia**: La estrategia original usa estos filtros
2. **Robustez**: Filtros reducen falsos positivos
3. **Realismo**: Backtest debe reflejar lógica de live bot
4. **Comparabilidad**: Permite comparar MARKET vs LIMIT de forma justa

### Implementación:

Modificar `backtester_limit_orders.py` líneas 171-186:

```python
# Verificar si vela cierra DENTRO de la zona
if ob.ob_type == "bullish":
    if candle_close < ob.zone_low or candle_close > ob.zone_high:
        continue
    direction = "long"
    entry_price = ob.zone_high
else:
    if candle_close < ob.zone_low or candle_close > ob.zone_high:
        continue
    direction = "short"
    entry_price = ob.zone_low

# ✅ AGREGAR FILTROS DE CONFIRMACIÓN

# Filtro de tendencia EMA 4H
trend_bias = self._get_trend_bias(higher_rows, current_time)
if trend_bias is not None and direction != trend_bias:
    continue

# Filtro 1: vela de rechazo
if not check_rejection(candle, prev_candle, direction, self.params):
    continue

# Filtro 2: BOS
if not check_bos(recent_candles, direction, self.params):
    continue

# Calcular SL/TP
sl, tp = self._calculate_sl_tp_limit(ob, entry_price)
if sl is None:
    continue
```

---

## 📋 SIGUIENTE PASO

1. ✅ Identificar filtros faltantes
2. ⏳ Agregar filtros a LIMIT backtester
3. ⏳ Re-ejecutar backtest con filtros
4. ⏳ Comparar resultados
5. ⏳ Decidir implementación en live bot

---

## 📝 NOTAS

- Este descubrimiento explica por qué LIMIT genera más trades
- No es un bug, es una **omisión de diseño**
- Los filtros son parte integral de la estrategia OB
- Sin ellos, el backtest no es representativo del live bot

---

*Generado: 2026-03-30*
