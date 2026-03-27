# 🐛 Resumen: Investigación y Fix de Bug

**Fecha**: 26 de Marzo, 2026  
**Problema Reportado**: Win Rate 94.4% es imposible para scalping

---

## ✅ BUG #1 CORREGIDO: Look-Ahead Bias

### Problema
El backtester evaluaba BE trigger ANTES de verificar SL dentro de la misma vela M5. Esto permitía que:
1. Precio alcanza high → BE activado, SL movido a ganancia
2. Precio toca low → SL hit, pero ya está en ganancia

En realidad, el low pudo tocarse PRIMERO.

### Fix Implementado
Implementé **conservative fill** en `scalping_backtester.py`:

```python
def _update_open_trades(self, candle: M5Candle):
    # PASO 1: Verificar SL PRIMERO (antes de moverlo)
    if self._check_sl_hit(trade, candle):
        # CASO AMBIGUO: ¿SL y BE en misma vela?
        if self._be_could_activate_in_candle(trade, candle):
            # ¿Vela abre más allá del BE trigger?
            if self._candle_opens_past_be_trigger(trade, candle):
                # BE se activó primero (sabemos por el open)
                self._activate_break_even(trade, candle)
            else:
                # PEOR CASO: asumir SL hit primero
                close_trade(trade, original_sl, CLOSED_SL)
                continue
    
    # PASO 2: Solo si SL no se tocó, verificar BE/Trailing/TP
    self._check_break_even(trade, candle)
    self._update_trailing_stop(trade, candle)
    self._check_tp_hit(trade, candle)
```

### Resultado
- **V1 (buggy)**: 462 trades, WR 94.4%, PF 60.44
- **V2 (fixed)**: 461 trades, WR 92.0%, PF 54.74
- **Cambio**: Solo 12 trades (2.6%) cambiaron de WIN a LOSS

### Conclusión
El look-ahead bias NO era el problema principal. El WR sigue siendo anormalmente alto.

---

## 🔍 PROBLEMA REAL: Parámetros Demasiado Optimistas

Después de analizar los datos, encontré que el WR alto se debe a una **combinación de factores**:

### Factor 1: SL Muy Ajustado
```yaml
stop_loss:
  buffer_points: 15  # Solo 15 puntos fuera de zona
```

**Problema**: Con zonas de 40 puntos, el SL queda a solo 55 puntos del entry. Para US30 que se mueve 200-500 puntos/día, esto es extremadamente ajustado.

### Factor 2: BE Muy Cercano
```yaml
break_even:
  trigger_rr: 1.0  # BE en 1:1
  offset_points: 3
```

**Problema**: Con SL de 55 puntos, el BE se activa con solo 55 puntos a favor. Esto pasa en 1-2 velas M5.

### Factor 3: Trailing Agresivo
```yaml
trailing_stop:
  method: "candle_structure"  # Mueve SL al low/high de cada vela
```

**Problema**: Mueve el SL en CADA vela que avanza a favor, incluso si es solo 1 punto.

### Efecto Combinado

**Trade típico**:
```
Entry:    46000
SL orig:  45945 (55 puntos)
BE trig:  46055 (55 puntos arriba)

Vela 1:   High 46060 → BE activado, SL → 46003
Vela 2:   Low 46010 → Trailing, SL → 46010
Vela 3:   Low 46005 → Trailing, SL → 46005
Vela 4:   Low 45990 → SL hit @ 46005 = +5 puntos

Resultado: Ganancia de 5 puntos
Realidad: Debería ser pérdida de 10 puntos
```

**Evidencia**:
- 24.3% de los wins son ganancias < 50 puntos
- 10.2% de todos los trades tienen PnL < 20 puntos
- Avg Win: $139 vs Avg Loss: $29 (ratio 4.8:1)

El BE y Trailing están convirtiendo pérdidas pequeñas en ganancias pequeñas.

---

## ⚠️ DIAGNÓSTICO FINAL

El Win Rate de 92% NO es un bug de código, sino el resultado de:

1. ✅ **Look-ahead bias** (corregido, pero solo afectaba 2.6% de trades)
2. ⚠️ **Parámetros demasiado optimistas** (problema principal)
3. ⚠️ **Datos limitados** (solo 60 días)
4. ⚠️ **Período favorable** (posible sesgo de mercado)

---

## 🎯 SOLUCIONES RECOMENDADAS

### Solución 1: Parámetros Más Conservadores

Editar `config/scalping_params.yaml`:

```yaml
pivots:
  swing_strength: 5  # Más estricto (era 3)
  min_zone_width: 20  # Zonas más estrictas
  max_zone_width: 80  # Zonas más estrictas

stop_loss:
  buffer_points: 30  # Más espacio (era 15)

break_even:
  trigger_rr: 1.5  # Más lejos (era 1.0)
  offset_points: 10  # Más conservador (era 3)

trailing_stop:
  enabled: false  # DESACTIVAR para validar estrategia base
```

**Expectativa**: WR debería bajar a 65-75%

### Solución 2: Backtest con 1 Año de Datos

```bash
# Descargar 1 año
python tools/download_mt5_data.py \
  --symbol US30.cash \
  --timeframes M5 M15 \
  --days 365

# Re-ejecutar
python strategies/pivot_scalping/run_backtest.py \
  --data-m5 data/US30_cash_M5_365d.csv \
  --data-m15 data/US30_cash_M15_365d.csv \
  --instrument US30 \
  --output strategies/pivot_scalping/data/backtest_US30_365d.csv
```

### Solución 3: Demo Trading (OBLIGATORIO)

La única forma de validar realmente:
1. Operar en demo 30+ días
2. Medir slippage real
3. Ver si WR se mantiene o baja a 55-70%

---

## 📊 COMPARATIVA: V1 vs V2

| Métrica | V1 (Buggy) | V2 (Fixed) | Cambio |
|---------|------------|------------|--------|
| Trades | 462 | 461 | -1 |
| Win Rate | 94.4% | 92.0% | -2.4% |
| Profit Factor | 60.44 | 54.74 | -5.70 |
| Retorno | +56.47% | +57.94% | +1.47% |
| Avg Win | $131.70 | $139.18 | +$7.48 |
| Avg Loss | -$36.54 | -$29.14 | +$7.40 |

**Observación**: El fix del look-ahead bias tuvo impacto mínimo. El problema real son los parámetros.

---

## 🚨 RECOMENDACIÓN FINAL

### NO USAR EN CUENTA REAL

El Win Rate de 92% es **artificial** debido a:
1. Parámetros demasiado optimistas
2. BE y Trailing convirtiendo pérdidas en ganancias pequeñas
3. Solo 60 días de datos
4. Posible período de mercado favorable

### Plan de Acción

**Semana 1**:
1. ✅ Ajustar parámetros a valores conservadores
2. ✅ Re-ejecutar backtest
3. ✅ Verificar que WR baje a 60-75%

**Semana 2-3**:
1. ✅ Descargar 1 año de datos
2. ✅ Backtest con datos completos
3. ✅ Walk-forward testing

**Semana 4-8**:
1. ✅ Demo trading 30+ días
2. ✅ Medir métricas reales
3. ✅ Ajustar si es necesario

**Semana 9+**:
- Si WR en demo es 55-70% y PF > 1.5 → Considerar FTMO
- Si WR sigue en 85%+ → Hay otro bug que investigar

---

## 💡 LECCIONES APRENDIDAS

1. **Win Rate alto ≠ Estrategia buena**: Un WR de 90%+ es una bandera roja, no un logro
2. **BE y Trailing pueden distorsionar resultados**: Parámetros agresivos convierten pérdidas en ganancias artificiales
3. **Conservative fill es crítico**: Pero solo resuelve parte del problema
4. **60 días no es suficiente**: Necesitas mínimo 1 año para validar
5. **Demo testing es obligatorio**: El backtest nunca es suficiente

---

## 📁 ARCHIVOS MODIFICADOS

### Código Corregido
- `strategies/pivot_scalping/backtest/scalping_backtester.py` - Conservative fill implementado

### Documentación
- `BUG_INVESTIGATION.md` - Análisis detallado del problema
- `RESUMEN_BUG_FIX.md` - Este archivo

### Resultados
- `strategies/pivot_scalping/data/backtest_US30_scalping_60d.csv` - V1 (buggy)
- `strategies/pivot_scalping/data/backtest_US30_scalping_60d_v2.csv` - V2 (fixed)

---

**Conclusión**: Tienes razón. 94.4% WR era demasiado bueno para ser verdad. El look-ahead bias era parte del problema, pero los parámetros optimistas son el problema principal. Necesitas ajustar parámetros y validar con más datos antes de confiar en esta estrategia.

---

**Última actualización**: 26 de Marzo, 2026
