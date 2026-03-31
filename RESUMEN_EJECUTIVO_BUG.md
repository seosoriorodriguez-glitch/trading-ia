# 🎯 RESUMEN EJECUTIVO: Bug SL/TP en Trades SHORT

## TL;DR

- ✅ **Backtest VÁLIDO**: Rentabilidad +19.92% es REAL
- ❌ **Bug encontrado**: SL y TP invertidos para trades SHORT
- 🚨 **CRÍTICO**: Bot live operará con R:R invertido si ejecuta SHORT
- 💡 **Solución**: Corregir `risk_manager.py` antes de que el bot opere SHORT

---

## 1. ¿QUÉ ES EL BUG?

En `strategies/order_block/backtest/risk_manager.py` (líneas 38-43), para trades SHORT:

```python
else:  # bearish → SHORT
    sl = ob.zone_high + buf     # ❌ Esto calcula el TP
    tp = entry - (sl - entry) * target_rr  # ❌ Esto calcula el SL
```

Las variables están **invertidas**: lo que se llama `sl` es realmente el TP, y viceversa.

---

## 2. ¿AFECTA LA VALIDEZ DEL BACKTEST?

### ✅ NO, el backtest ES VÁLIDO

**Razón**: El bug es **consistente** en todo el código:

1. **Cálculo** (`risk_manager.py`): Calcula SL/TP invertidos
2. **Ejecución** (`backtester.py`): Los usa invertidos
3. **PnL** (`calc_pnl`): Calcula correctamente desde entry/exit (no usa sl/tp)

**Resultado**: Los trades operan correctamente, solo las etiquetas están mal.

### Métricas Verificadas:

| Métrica | Estado | Valor |
|---------|--------|-------|
| Rentabilidad | ✅ CORRECTA | +19.92% |
| PnL en USD | ✅ CORRECTO | $19,922.97 |
| Win Rate | ✅ CORRECTO | 42.3% |
| Max DD | ✅ CORRECTO | Basado en balance |
| R-multiples SHORT | ❌ INFLADOS | 2.13R → 0.88R real |

---

## 3. EVIDENCIA DEL BUG

### Análisis de 104 trades del backtest:

```
Total trades:     104
├─ LONG:          46 (✅ correctos)
└─ SHORT:         58 (❌ 5 con SL/TP invertidos = 8.6%)

SHORT winners:    24 (41.4%)
├─ exit='sl':     5 (20.8%) ← Salieron en "sl" pero ganaron
└─ exit='tp':     19 (79.2%)

SHORT losers:     34 (58.6%)
├─ exit='sl':     34 (100%) ← Salieron en "sl" pero perdieron
└─ exit='tp':     0 (0%)
```

### R-multiples Inflados:

```
SHORT winners:
  Reportado: 2.13R
  Real:      0.88R
  Inflación: +142%

SHORT losers:
  Reportado: -1.05R
  Real:      -0.40R
  Inflación: +162%
```

---

## 4. ¿AFECTA AL BOT LIVE?

### 🚨 SÍ, CRÍTICO si ejecuta trades SHORT

**Estado actual del bot**:
- ✅ Solo ha ejecutado 2 trades LONG (correctos)
- ⚠️ NO ha ejecutado trades SHORT todavía
- 🔴 **Tiene 2 OBs bearish activos** (puede ejecutar SHORT en cualquier momento)

### ¿Qué pasará cuando ejecute un SHORT?

**Ejemplo simulado**:

```
Señal SHORT detectada:
  Entry: 45,550
  OB zone: 45,480 - 45,500

Cálculo del bot (INCORRECTO):
  sl = 45,500 + 20 = 45,520  (DEBAJO del entry)
  tp = 45,550 - 30 × 2.5 = 45,625  (ARRIBA del entry)

Orden enviada a MT5:
  Type: SELL
  Entry: 45,550
  SL: 45,520  ← MT5 cerrará aquí si BAJA 30 puntos
  TP: 45,625  ← MT5 cerrará aquí si SUBE 75 puntos
```

**Resultado**:
- Si el precio **BAJA** (movimiento esperado): Cierra en "SL" con +30 puntos ✅
- Si el precio **SUBE** (movimiento contrario): Cierra en "TP" con -75 puntos ❌

**R:R invertido**: 1:2.5 → 2.5:1 (riesgo 2.5x mayor que beneficio)

---

## 5. IMPACTO EN RENTABILIDAD

### Backtest (con bug consistente):
```
LONG:   $11,264 (56.5%)
SHORT:  $8,659 (43.5%)
Total:  $19,923 (+19.92%)
```

### Live Bot (con bug en MT5):

Si el bot ejecuta SHORT con el bug:
- **Riesgo**: 2.5x mayor (75 puntos en lugar de 30)
- **Beneficio**: 2.5x menor (30 puntos en lugar de 75)
- **Expectativa**: Pérdidas en lugar de ganancias

**Estimación**: Si el 43.5% de la rentabilidad viene de SHORT, y estos operan con R:R invertido, el bot podría perder todo lo ganado con LONG.

---

## 6. SOLUCIÓN

### Código Corregido para `risk_manager.py`:

```python
def calculate_sl_tp(
    ob: OrderBlock,
    entry_price: float,
    params: dict,
) -> Tuple[Optional[float], Optional[float]]:
    buf         = params["buffer_points"]
    min_risk    = params["min_risk_points"]
    max_risk    = params["max_risk_points"]
    target_rr   = params["target_rr"]
    min_rr      = params["min_rr_ratio"]

    if ob.ob_type == "bullish":
        # LONG: SL debajo, TP arriba
        sl = ob.zone_low - buf
        tp = entry_price + (entry_price - sl) * target_rr
    else:
        # SHORT: TP debajo, SL arriba (CORREGIDO)
        tp = ob.zone_high + buf  # TP debajo de la zona
        risk_pts = abs(entry_price - tp)
        sl = entry_price + risk_pts * target_rr  # SL arriba del entry

    risk_pts = abs(entry_price - sl)

    if risk_pts < min_risk:
        return None, None
    if risk_pts > max_risk:
        return None, None

    rr = abs(tp - entry_price) / risk_pts
    if rr < min_rr:
        return None, None

    return sl, tp
```

### Pasos para Implementar:

1. ✅ **Detener el bot live** (o configurar solo LONG)
2. ✅ **Corregir** `risk_manager.py`
3. ✅ **Re-ejecutar backtest** completo
4. ✅ **Verificar** que rentabilidad sigue siendo ~19%
5. ✅ **Probar en demo** antes de volver a live

---

## 7. RECOMENDACIÓN INMEDIATA

### 🚨 ACCIÓN URGENTE

**Opción 1: Detener el bot**
```bash
# Detener el bot hasta corregir
Ctrl+C en la terminal
```

**Opción 2: Configurar solo LONG (temporal)**
```python
# En check_entry (signals.py), agregar:
if direction == "short":
    continue  # Saltar trades SHORT temporalmente
```

**Opción 3: Monitorear y cerrar SHORT manualmente**
- Dejar el bot corriendo
- Si abre un SHORT, **cerrar manualmente** en MT5
- Verificar que SL/TP estén correctos antes de dejar correr

---

## 8. CONCLUSIÓN

### ✅ Buenas Noticias:
1. **Backtest es válido**: +19.92% es rentabilidad real
2. **Bug es corregible**: Solución simple en 10 líneas
3. **No hay pérdidas**: Bot no ha ejecutado SHORT todavía

### ⚠️ Riesgos:
1. **Bot puede ejecutar SHORT** en cualquier momento (tiene 2 OBs bearish activos)
2. **R:R invertido**: Operará con 2.5:1 en lugar de 1:2.5
3. **Pérdidas potenciales**: Puede perder todo lo ganado con LONG

### 🎯 Acción Requerida:
**DETENER BOT o SOLO OPERAR LONG hasta corregir el bug**

---

## Archivos Generados

1. `BUG_SL_TP_INVERTIDOS.md` - Análisis detallado del bug
2. `ANALISIS_CRITICO_BUG_SL_TP.md` - Análisis exhaustivo con ejemplos
3. `verificar_impacto_bug.py` - Script de verificación
4. `RESUMEN_EJECUTIVO_BUG.md` - Este documento

---

**Fecha**: 2026-03-31  
**Prioridad**: 🚨 CRÍTICA  
**Estado**: ⚠️ PENDIENTE DE CORRECCIÓN
