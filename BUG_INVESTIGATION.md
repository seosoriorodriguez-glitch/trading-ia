# 🔍 Investigación de Bug: Win Rate 92%

**Fecha**: 26 de Marzo, 2026  
**Problema**: Win Rate de 92% es anormalmente alto para scalping

---

## 🐛 BUG #1: Look-Ahead Bias (PARCIALMENTE CORREGIDO)

### Descripción
El backtester verificaba BE trigger antes de verificar SL, permitiendo que trades que debían cerrar en pérdida cerraran en ganancia.

### Fix Aplicado
Implementé "conservative fill":
1. Verificar SL primero
2. Si SL y BE trigger en misma vela → asumir peor caso (SL hit)
3. Excepción: si vela abre más allá del BE trigger

### Resultado
- **V1**: 462 trades, WR 94.4%, PF 60.44
- **V2**: 461 trades, WR 92.0%, PF 54.74
- **Cambio**: Solo 12 trades (2.6%) cambiaron de WIN a LOSS

### Conclusión
El look-ahead bias NO es el problema principal. El WR sigue siendo anormalmente alto (92%).

---

## 🔍 POSIBLES BUGS ADICIONALES

### Bug #2: Pivots Demasiado Confiables

**Hipótesis**: Los pivots detectados son demasiado "perfectos" porque:
1. Usamos `swing_strength=3` (muy bajo, genera muchos pivots)
2. Esperamos "segundo toque" pero no validamos calidad del toque
3. Las zonas son muy amplias (vela completa)

**Evidencia**:
- 461 trades en 60 días = 7.7 trades/día
- 92% de éxito sugiere que casi todos los pivots funcionan
- En realidad, los pivots fallan ~40-50% del tiempo

**Posible causa**:
Los pivots se detectan con **hindsight** (mirando velas futuras). El código usa:
```python
for i in range(swing_strength, len(candles) - swing_strength):
    # Verifica N velas ANTES y DESPUÉS
```

Esto es correcto para detectar pivots históricos, pero podría estar generando señales en pivots que "sabemos" que funcionaron porque ya vimos el futuro.

### Bug #3: Zonas Muy Amplias

**Observación**: La zona del pivot es la vela completa (low a high).

Para US30 con velas M15:
- Rango típico: 20-50 puntos
- Zona muy amplia = más fácil "tocar" la zona

**Problema**: Una zona de 50 puntos es ~0.1% del precio. Casi cualquier movimiento "toca" la zona.

### Bug #4: SL Muy Cerca del Pivot

**Config actual**:
```yaml
stop_loss:
  buffer_points: 15  # Solo 15 puntos fuera de zona
```

Si la zona tiene 40 puntos de ancho y el SL está 15 puntos más allá:
- Entry: borde de zona (ej: 46000)
- Zona: 45960-46000 (40 puntos)
- SL: 45945 (15 puntos debajo)
- **Riesgo total: solo 55 puntos**

Para US30 que se mueve 200-500 puntos al día, un SL de 55 puntos es extremadamente ajustado. Esto explica por qué el BE se activa tan fácilmente (solo necesita 55 puntos a favor).

### Bug #5: BE Trigger Muy Cercano (1:1)

**Config actual**:
```yaml
break_even:
  trigger_rr: 1.0  # BE en 1:1
```

Con SL de 55 puntos, el BE se activa con solo 55 puntos a favor. Para US30 en M5, esto puede pasar en 1-2 velas.

**Problema**: El precio puede hacer +55 puntos, activar BE, y luego revertir. Pero como el SL ya se movió a entrada+3, el trade cierra en pequeña ganancia en lugar de pérdida.

---

## 🎯 DIAGNÓSTICO PRINCIPAL

El problema NO es un solo bug, sino una **combinación de factores** que hacen la estrategia artificialmente rentable:

1. **Pivots muy frecuentes** (swing_strength=3)
2. **Zonas muy amplias** (vela completa)
3. **SL muy ajustado** (15 puntos buffer)
4. **BE muy cercano** (1:1 con SL ajustado)
5. **Trailing agresivo** (mueve SL al low/high de cada vela)

### Ejemplo Real

Trade típico:
```
Entry:    46000 (borde de resistencia)
Zona:     45960-46000 (40 puntos)
SL orig:  45945 (15 puntos debajo)
BE trig:  46055 (55 puntos arriba = 1:1)

Vela 1:   High 46060 → BE activado, SL → 46003
Vela 2:   Low 46010 → Trailing, SL → 46010
Vela 3:   Low 46005 → Trailing, SL → 46005
Vela 4:   Low 45990 → SL hit @ 46005 = +5 puntos ganancia
```

El trade "debería" haber sido pérdida (precio bajó 55 puntos desde entry), pero BE+Trailing lo convirtieron en pequeña ganancia.

---

## ✅ SOLUCIONES PROPUESTAS

### Solución 1: Parámetros Más Realistas

```yaml
pivots:
  swing_strength: 5  # Pivots más confiables (era 3)
  min_zone_width: 20  # Zonas más estrictas (era 10)
  max_zone_width: 80  # Zonas más estrictas (era 200)

stop_loss:
  buffer_points: 30  # Más espacio (era 15)

break_even:
  trigger_rr: 1.5  # Más lejos (era 1.0)
  offset_points: 10  # Más conservador (era 3)

trailing_stop:
  enabled: false  # DESACTIVAR temporalmente
```

### Solución 2: Validación de Calidad de Toque

Añadir filtros para el "segundo toque":
- Verificar que sea rechazo real (pin bar con mecha >= 60% de vela)
- Verificar volumen del toque
- Verificar que el precio no "atraviese" la zona

### Solución 3: Backtest Más Largo

60 días es muy poco. Necesitamos:
- **Mínimo 1 año** de datos
- **Diferentes condiciones** de mercado (tendencia, rango, alta/baja volatilidad)
- **Walk-forward testing** (entrenar en 6 meses, validar en 3 meses siguientes)

### Solución 4: Forward Testing en Demo

La única forma de validar realmente es:
1. Operar en demo 30+ días
2. Medir slippage real
3. Medir costos reales
4. Ver si el WR se mantiene o baja a niveles realistas (55-70%)

---

## 🚨 RECOMENDACIÓN URGENTE

**NO usar esta estrategia en cuenta real** hasta:

1. ✅ Re-ejecutar backtest con parámetros más conservadores
2. ✅ Backtest con 1+ año de datos
3. ✅ Walk-forward testing
4. ✅ Demo trading 30+ días
5. ✅ Win Rate se estabiliza en 55-70%

Si después de estos pasos el WR sigue en 85%+, entonces hay un bug más profundo que no hemos encontrado, o los datos de MT5 tienen problemas.

---

## 📊 PRÓXIMOS PASOS

### Paso 1: Re-ejecutar con Parámetros Conservadores

```bash
# Editar config/scalping_params.yaml con valores más conservadores
# Luego re-ejecutar
python strategies/pivot_scalping/run_backtest.py \
  --data-m5 data/US30_cash_M5_60d.csv \
  --data-m15 data/US30_cash_M15_60d.csv \
  --instrument US30 \
  --output strategies/pivot_scalping/data/backtest_US30_v3_conservative.csv
```

### Paso 2: Descargar 1 Año de Datos

```bash
python tools/download_mt5_data.py \
  --symbol US30.cash \
  --timeframes M5 M15 \
  --days 365
```

### Paso 3: Análisis de Pivots

Crear script para analizar:
- Cuántos pivots se detectan
- Tasa de éxito real de pivots (sin entrar trades)
- Distribución de anchos de zona
- Frecuencia de toques

### Paso 4: Demo Testing

Si los pasos anteriores muestran métricas más realistas (WR 60-75%), entonces probar en demo.

---

**Conclusión**: El WR de 92% NO es un bug único, sino el resultado de parámetros demasiado optimistas que hacen que casi cualquier trade se convierta en pequeña ganancia gracias a BE y Trailing agresivos.
