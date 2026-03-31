# ✅ CORRECCIÓN: Análisis de Filtros

## ❌ ERROR EN ANÁLISIS ANTERIOR

Anteriormente dije que el backtester LIMIT no aplicaba **3 filtros**:
1. ❌ Filtro de rechazo (rejection)
2. ❌ Filtro de BOS
3. ❌ Filtro de tendencia EMA 4H

## ✅ REALIDAD

Revisando `config.py` del **live bot**:

```python
# --- Filtro de tendencia: EMA 4H ---
"ema_trend_filter": False,     # ❌ DESACTIVADO

# --- Filtro 1: Vela de rechazo ---
"require_rejection": False,    # ❌ DESACTIVADO

# --- Filtro 2: BOS — Break of Structure ---
"require_bos": True,           # ✅ ACTIVADO
"bos_lookback": 20,
```

### El live bot SOLO usa:
- ✅ **Filtro BOS** (Break of Structure, 20 velas M1)
- ❌ NO usa filtro de rechazo
- ❌ NO usa filtro EMA 4H

---

## 🔍 ENTONCES, ¿POR QUÉ LIMIT GENERA MÁS TRADES?

El backtester **LIMIT** (`backtester_limit_orders.py`) **NO aplica el filtro BOS**.

### Código LIMIT (líneas 171-186):

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

# Calcular SL/TP
sl, tp = self._calculate_sl_tp_limit(ob, entry_price)
if sl is None:
    continue

# ❌ NO HAY FILTRO BOS
```

### Código MARKET (signals.py, líneas 224-225):

```python
# Filtro 2: BOS
if not check_bos(recent_candles, direction, params):
    continue
```

---

## 📊 IMPACTO

| Backtest | Filtro BOS | Trades | Profitability |
|----------|-----------|--------|---------------|
| **MARKET** | ✅ Sí | 104 | +19.92% |
| **LIMIT** | ❌ No | 205 | +24.10% |

Sin el filtro BOS, LIMIT genera **el doble de trades** (205 vs 104).

---

## ✅ SOLUCIÓN CORRECTA

Agregar **SOLO el filtro BOS** al backtester LIMIT:

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

# ✅ AGREGAR FILTRO BOS
if not check_bos(recent_candles, direction, self.params):
    continue

# Calcular SL/TP
sl, tp = self._calculate_sl_tp_limit(ob, entry_price)
if sl is None:
    continue
```

---

## 🎯 PRÓXIMO PASO

¿Quieres que agregue el **filtro BOS** al backtester LIMIT y re-ejecute el backtest?

Esto debería:
- ✅ Reducir trades a ~100-120 (similar a MARKET)
- ✅ Mantener coherencia con live bot
- ✅ Permitir comparación justa MARKET vs LIMIT

---

*Corrección generada: 2026-03-30*
