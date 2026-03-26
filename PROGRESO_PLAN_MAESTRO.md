# 📋 Progreso del Plan Maestro - Estrategia de Scalping

**Fecha**: 26 de Marzo, 2026  
**Objetivo**: Implementar estrategia de scalping basada en Pivot Points puros

---

## ✅ COMPLETADO

### FASE 1: Conexión MT5 (Modificado - Plan B)

**Estado**: ⚠️ Bloqueado → Usando Plan B

**Problema**:
- Imágenes Docker de MT5 no disponibles:
  - `bahadirumutiscimen/pysiliconwine:latest` ❌
  - `alfiej04/metatrader5:latest` ❌

**Solución Temporal**:
- ✅ Usar Yahoo Finance para datos M5 y M15
- ✅ Documentado en `ESTADO_MT5_DOCKER.md`
- ⏳ MT5 necesario para demo/live trading (no para backtest)

### FASE 2: Descarga de Datos

**Estado**: ✅ COMPLETADO

- ✅ Actualizado `tools/download_yahoo_data.py` para soportar `--interval`
- ✅ Descargados datos M5: `data/US30_M5_60d.csv` (3,233 registros)
- ✅ Descargados datos M15: `data/US30_M15_60d.csv` (1,079 registros)
- ✅ Período: 26 Ene - 26 Mar 2026 (60 días)

**Archivos**:
```
data/US30_M5_60d.csv   - 3,233 velas M5
data/US30_M15_60d.csv  - 1,079 velas M15
```

---

## 🔄 EN PROGRESO

### FASE 3: Estrategia de Scalping - Pivot Points

**Estado**: 🔄 Iniciando implementación

**Pendiente**:
1. Crear `strategies/pivot_scalping/core/pivot_detection.py`
2. Crear `strategies/pivot_scalping/core/signal_generation.py`
3. Crear `strategies/pivot_scalping/config/scalping_params.yaml`

---

## ⏳ PENDIENTE

### FASE 4: Backtester de Scalping

**Pendiente**:
1. Crear `strategies/pivot_scalping/backtest/scalping_backtester.py`
2. Crear `strategies/pivot_scalping/run_scalping_backtest.py`

### FASE 5: Ejecución y Resultados

**Pendiente**:
1. Ejecutar backtest completo
2. Analizar resultados
3. Generar reporte

---

## 📊 Especificación de la Estrategia

### Detección de Pivot Points (M15)

```python
# Pivot High: high > highs de N velas a cada lado
# Pivot Low: low < lows de N velas a cada lado
# N = swing_strength (default: 3)
# Zona = [low, high] de la vela pivote
```

### Validación (Segundo Toque)

```python
# Primer toque: registra zona, NO opera
# Segundo toque: activa búsqueda de señal
# Separación mínima: 4 velas M15 (1 hora)
```

### Señales de Entrada (M5)

**LONG** (en soporte):
- Pin Bar alcista: mecha inferior >= 2x cuerpo
- Engulfing alcista

**SHORT** (en resistencia):
- Pin Bar bajista: mecha superior >= 2x cuerpo
- Engulfing bajista

### Stop Loss (Dinámico)

```python
LONG:  SL = borde_inferior_zona - 15 puntos
SHORT: SL = borde_superior_zona + 15 puntos
```

### Take Profit (Por Estructura)

```python
# Primario: Siguiente pivot opuesto ± 5 puntos
# Fallback: R:R 2:1
# Filtro: R:R mínimo 1.5:1
```

### Gestión

```python
# Break Even: En 1:1, mover SL a entry + 3 pts
# Trailing: Por estructura de velas M5 (no fijo)
# Riesgo: 0.5% por trade
# Máximo: 2 trades simultáneos
```

### Filtros

```python
# Horario:
#   Londres: 08:00-11:00 UTC
#   Nueva York: 13:30-19:30 UTC
#   No operar primeros 15 min de sesión
# 
# Spread: Máximo 5 puntos
# Expiración: 200 velas M15 (~50 horas)
# Máximo zonas: 6 activas
```

---

## 🎯 Próximos Pasos Inmediatos

1. **Implementar detección de pivots** en M15
2. **Implementar generación de señales** en M5
3. **Crear configuración** YAML
4. **Implementar backtester** con gestión completa
5. **Ejecutar backtest** y analizar resultados

---

## 📝 Notas Importantes

### Bug Crítico a Evitar

```python
# ❌ INCORRECTO:
pnl_usd = (pnl_points / abs(entry - stop_loss)) * risk_usd

# ✅ CORRECTO:
pnl_usd = (pnl_points / abs(entry - original_stop_loss)) * risk_usd
```

**Razón**: `stop_loss` es modificado por Break Even y Trailing Stop. Siempre usar `original_stop_loss` para calcular riesgo planificado.

### Costos de Spread

```python
# Restar spread de cada trade:
pnl_points -= avg_spread_points  # Simula costo real
```

### Métricas a Reportar

```
- Profit Factor (USD) ← MÉTRICA REAL
- Profit Factor (Puntos) ← Referencia
- Win Rate
- Max Drawdown
- R:R Promedio
- Desglose por dirección (LONG/SHORT)
- Desglose por señal (pin_bar/engulfing)
- Desglose por sesión (Londres/NY)
```

---

## 🔧 Archivos Creados

- ✅ `ESTADO_MT5_DOCKER.md` - Documentación del problema Docker
- ✅ `tools/download_dukascopy_data.py` - Script Dukascopy (info)
- ✅ `tools/download_yahoo_data.py` - Actualizado con `--interval`
- ✅ `data/US30_M5_60d.csv` - Datos M5 (3,233 registros)
- ✅ `data/US30_M15_60d.csv` - Datos M15 (1,079 registros)
- ✅ `PROGRESO_PLAN_MAESTRO.md` - Este archivo

---

## 🚀 Estado General

**Progreso**: ~20% completado  
**Bloqueadores**: Ninguno (Plan B funcionando)  
**Siguiente**: Implementar core de la estrategia  
**ETA**: 2-3 horas para backtest funcional

---

**Última actualización**: 26 Mar 2026, 20:30 UTC
