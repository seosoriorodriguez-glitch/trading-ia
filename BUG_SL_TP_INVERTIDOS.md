# 🐛 BUG CRÍTICO: SL y TP invertidos para trades SHORT

## Resumen Ejecutivo

Se detectó un **bug crítico** en el cálculo de Stop Loss (SL) y Take Profit (TP) para trades SHORT en la estrategia Order Block. Las variables `sl` y `tp` están **invertidas** en el código, lo que causa que:

- Lo que se etiqueta como "SL" es en realidad el TP
- Lo que se etiqueta como "TP" es en realidad el SL

## Evidencia del Bug

### Trade #7 (SHORT) - Ejemplo

```
Direction:  SHORT
Entry:      48,496.71
SL (CSV):   48,474.03  ← DEBAJO del entry (❌ incorrecto)
TP (CSV):   48,553.41  ← ARRIBA del entry (❌ incorrecto)
Exit:       48,474.03
Reason:     "sl"
PnL:        +$465.33 (GANADOR)
```

### ¿Por qué es un problema?

Para un trade SHORT:
- **SL debería estar ARRIBA** del entry (protección si el precio sube)
- **TP debería estar DEBAJO** del entry (objetivo de ganancia si el precio baja)

Pero en el código:
- `sl = 48,474.03` (DEBAJO del entry) ❌
- `tp = 48,553.41` (ARRIBA del entry) ❌

### ¿Por qué el backtest funciona?

El bug es **consistente** en todo el código:

1. **`risk_manager.py`** calcula SL y TP invertidos
2. **`backtester.py`** los usa invertidos en `_check_trade_exit`:
   ```python
   else:  # short
       if candle_high >= trade.sl:  # Verifica si sube hasta "sl"
           self._close_trade(trade, trade.sl, current_time, "sl")
       if candle_low <= trade.tp:   # Verifica si baja hasta "tp"
           self._close_trade(trade, trade.tp, current_time, "tp")
   ```

Como ambos están invertidos, el backtest **funciona correctamente** pero con etiquetas confusas.

## Ubicación del Bug

### Archivo: `strategies/order_block/backtest/risk_manager.py`

**Líneas 38-43:**

```python
if ob.ob_type == "bullish":
    sl = ob.zone_low - buf
    tp = entry_price + (entry_price - sl) * target_rr
else:
    sl = ob.zone_high + buf     # ❌ BUG: esto es realmente el TP
    tp = entry_price - (sl - entry_price) * target_rr  # ❌ BUG: esto es realmente el SL
```

## Solución Propuesta

### Opción 1: Corregir las etiquetas (más simple)

Simplemente intercambiar las asignaciones para SHORT:

```python
if ob.ob_type == "bullish":
    sl = ob.zone_low - buf
    tp = entry_price + (entry_price - sl) * target_rr
else:
    # Calcular primero el TP (debajo)
    tp_temp = ob.zone_high + buf
    # Calcular el SL (arriba) basado en el riesgo
    risk_pts = abs(entry_price - tp_temp)
    sl = entry_price + risk_pts * (target_rr / (target_rr + 1))
    tp = tp_temp
```

### Opción 2: Mantener la lógica actual (más conservador)

Si el backtest ha sido validado y funciona correctamente, podemos:

1. **Mantener el código como está**
2. **Documentar** que para SHORT:
   - La variable `sl` contiene el precio objetivo (TP real)
   - La variable `tp` contiene el precio de protección (SL real)
3. **Corregir solo el CSV** para mostrar las etiquetas correctas

## Impacto

### En el Backtest
- ✅ **Funciona correctamente** (bug consistente)
- ❌ **Confusión** en los CSVs y logs
- ❌ **Dificulta** el análisis de trades

### En el Live Bot
- ⚠️ **CRÍTICO**: Verificar que MetaTrader 5 reciba los valores correctos
- El live bot usa la misma función `calculate_sl_tp`
- Si MT5 espera SL arriba y TP abajo, el bot podría estar operando con riesgo invertido

## Trades Afectados

De las 44 operaciones ganadoras en el backtest NY-only:

- **20 LONG**: ✅ Correctos
- **24 SHORT**: ❌ Todos tienen SL/TP invertidos en el CSV

Específicamente, estos trades SHORT tienen el bug:
- Trade #4, #5, #6, #8, #10, #12, #15, #18, #19, #23, #25, #26, #27, #28, #30, #33, #36, #38, #39, #40, #41, #42, #43, #44

## Recomendación

### URGENTE: Verificar Live Bot

1. **Revisar logs del live bot** para confirmar que los SL/TP se están enviando correctamente a MT5
2. **Verificar en MT5** que los trades SHORT tienen:
   - SL arriba del entry
   - TP debajo del entry

### Luego: Corregir el código

Si el live bot está funcionando correctamente (porque MT5 interpreta los valores correctamente), entonces:

1. **Corregir `risk_manager.py`** para usar las etiquetas correctas
2. **Actualizar `backtester.py`** para usar las etiquetas correctas
3. **Regenerar todos los CSVs** con las etiquetas corregidas

## Conclusión

Este es un **bug de etiquetado** que no afecta la lógica de trading (porque es consistente en todo el código), pero:

- ❌ Genera confusión en el análisis
- ❌ Dificulta el debugging
- ⚠️ Podría causar problemas si se integra con otros sistemas que esperan la convención estándar

**Prioridad: ALTA** - Requiere verificación inmediata del live bot y corrección del código.
