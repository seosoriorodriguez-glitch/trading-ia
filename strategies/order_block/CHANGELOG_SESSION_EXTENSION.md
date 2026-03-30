# 📋 CHANGELOG - Extensión de Sesión NY

**Fecha:** 2026-03-30  
**Cambio:** Extensión de la sesión de trading de Nueva York hasta el cierre oficial

---

## 🔄 CAMBIOS REALIZADOS

### Configuración Anterior
```yaml
sessions:
  new_york:
    start: "13:30"
    end: "19:30"      # ❌ Cerraba 30 min antes del cierre oficial
    skip_minutes: 15
```

### Configuración Nueva ✅
```yaml
sessions:
  new_york:
    start: "13:30"
    end: "20:00"      # ✅ Hasta cierre oficial de NY (4:00 PM EST)
    skip_minutes: 15
```

---

## 📊 RESULTADOS DEL BACKTEST COMPARATIVO

**Período analizado:** 101 días (2025-12-12 a 2026-03-27)  
**Datos:** US30.cash M5/M1

| Métrica | Anterior (19:30) | Nueva (20:00) | Diferencia |
|---------|------------------|---------------|------------|
| **Trades totales** | 98 | 117 | +19 (+19.4%) |
| **Win Rate** | 42.9% | 42.7% | -0.1pp |
| **Retorno** | +19.50% | +24.41% | **+4.91pp** |
| **Max Drawdown** | 2.56% | 4.07% | +1.51pp |
| **Max Daily DD** | -1.69% | -1.88% | -0.20pp |
| **Profit Factor** | 1.60 | 1.61 | +0.01 |
| **Balance final** | $119,499 | $124,413 | **+$4,914** |

---

## ✅ JUSTIFICACIÓN DEL CAMBIO

1. **Mayor rentabilidad:** +$4,914 adicionales en 101 días (+25% más ganancia)
2. **Más oportunidades:** 19 trades adicionales sin degradar Win Rate
3. **Profit Factor estable:** Se mantiene en 1.60-1.61
4. **Drawdown aceptable:** 4.07% sigue muy por debajo del límite FTMO (10%)
5. **Sesión completa:** Ahora opera toda la sesión oficial de NY (9:30 AM - 4:00 PM EST)

---

## 🕐 HORARIO DE OPERACIÓN

### Sesión de Nueva York (UTC)
- **Inicio:** 13:30 UTC (9:30 AM EST)
- **Inicio efectivo:** 13:45 UTC (después de skip de 15 min)
- **Cierre:** 20:00 UTC (4:00 PM EST)
- **Duración:** 6.25 horas de trading activo

### ¿Por qué skip_minutes = 15?
- Evita volatilidad errática de los primeros 15 minutos post-apertura
- Permite que el mercado se estabilice después de la apertura
- Reduce spreads más altos y movimientos bruscos iniciales
- **Se aplica:** Bot NO toma trades entre 13:30-13:45 UTC

---

## 🎯 IMPACTO EN EL BOT LIVE

- ✅ Bot reiniciado con nueva configuración
- ✅ Balance inicial: $94,238.65 (balance real actual)
- ✅ Ahora opera hasta las 20:00 UTC (30 minutos adicionales)
- ✅ Todos los demás parámetros sin cambios
- ✅ Límites FTMO: Daily DD 5% / Total DD 10% (sin cambios)

---

## 📁 ARCHIVOS MODIFICADOS

1. **`strategies/order_block/backtest/config.py`**
   - Línea 37: `"end": "19:30"` → `"end": "20:00"`
   - Actualizado comentario con resultados del backtest

2. **`strategies/order_block/backtest/experimental/session_extended_test.py`** (NUEVO)
   - Script de backtest comparativo para validar el cambio
   - Ejecutable: `python strategies/order_block/backtest/experimental/session_extended_test.py`

---

## 🔍 VALIDACIÓN

Para verificar que el cambio está activo:
```bash
# Ver configuración actual
cat strategies/order_block/backtest/config.py | grep -A 3 "sessions"

# Ejecutar backtest comparativo
python strategies/order_block/backtest/experimental/session_extended_test.py
```

---

## ⚠️ NOTAS IMPORTANTES

1. **No se modificó el código del bot live** - Solo la configuración de horarios
2. **El bot se reinició automáticamente** después del cambio
3. **Balance preservado:** Se usó el balance real actual ($94,238.65)
4. **Archivo STOP.txt:** Se usó para detener el bot de forma segura antes del reinicio

---

## 📈 PRÓXIMOS PASOS

- Monitorear rendimiento durante los próximos días
- Validar que los trades en el período 19:30-20:00 UTC mantienen calidad
- Comparar resultados reales vs backtest
- Ajustar si es necesario basándose en datos reales

---

**Estado:** ✅ Implementado y operativo  
**Bot activo desde:** 2026-03-30 20:22:30 UTC
