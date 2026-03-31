# 📊 RESUMEN EJECUTIVO: ¿Por qué LIMIT genera más trades?

## 🎯 RESPUESTA CORTA

El backtester **LIMIT** genera **el doble de trades** (205 vs 104) porque **NO aplica los filtros de confirmación** que sí usa el backtester MARKET:

1. ❌ **Filtro de rechazo** (rejection candle)
2. ❌ **Filtro de BOS** (Break of Structure)
3. ❌ **Filtro de tendencia EMA 4H**

---

## 📈 COMPARACIÓN

| Métrica | MARKET (con filtros) | LIMIT (sin filtros) | Diferencia |
|---------|---------------------|---------------------|------------|
| **Trades** | 104 | 205 | **+97%** |
| **Profitability** | +19.92% | +24.10% | +4.18% |
| **Win Rate** | 39.4% | 40.5% | +1.1% |
| **LONG** | 46 | 105 | +128% |
| **SHORT** | 58 | 100 | +72% |

---

## 🔍 HALLAZGO CLAVE

**Sin filtros, LIMIT es MÁS rentable** (+24% vs +19%)

Esto sugiere que:
- Los filtros actuales pueden ser **demasiado restrictivos**
- O están **rechazando trades buenos**

---

## ✅ SOLUCIÓN

Agregar los 3 filtros de confirmación al backtester LIMIT para:
1. ✅ Mantener coherencia con estrategia original
2. ✅ Hacer comparación justa MARKET vs LIMIT
3. ✅ Reflejar lógica que usará el live bot

---

## 🎯 PRÓXIMO PASO

¿Quieres que:
1. **Agregue los filtros** a LIMIT y re-ejecute el backtest?
2. **Mantengamos LIMIT sin filtros** para aprovechar mayor rentabilidad?
3. **Hagamos ambos** y comparemos resultados?

---

*Ver análisis completo en: `DESCUBRIMIENTO_FILTROS_FALTANTES.md`*
