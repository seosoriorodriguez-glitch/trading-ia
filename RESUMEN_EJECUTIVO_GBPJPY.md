# 🎯 RESUMEN EJECUTIVO - BACKTEST GBPJPY 24H

**Fecha**: 30 Marzo 2026  
**Análisis**: Estrategia Order Block LIMIT en GBPJPY vs US30

---

## 📊 RESULTADOS GBPJPY 24H (29 días)

```
Balance:        $100,000 → $100,066 (+0.07%)
Max DD:         -17.73%
Win Rate:       23.2%
Profit Factor:  1.00
Trades:         185 (6.6/día)
Expectancy:     $0.36 por trade
```

---

## 🆚 COMPARACIÓN DIRECTA

| Métrica | GBPJPY 24H | US30 NY | Diferencia |
|---------|------------|---------|------------|
| **Retorno** | +0.07% | +30.91% | **-30.84%** ❌ |
| **Max DD** | -17.73% | -8.77% | **-8.96%** ❌ |
| **Win Rate** | 23.2% | 29.4% | -6.2% ❌ |
| **Profit Factor** | 1.00 | 1.36 | -0.36 ❌ |
| **Trades/día** | 6.6 | 1.9 | +4.7 ❌ |
| **Expectancy** | $0.36 | $157.21 | **-$156.85** ❌ |
| **FTMO** | NO ❌ | SI ✅ | - |

---

## ❌ PROBLEMAS CRÍTICOS GBPJPY

### 1. Retorno casi nulo:
- +0.07% en 28 días = +0.9% anualizado
- Profit Factor = 1.00 (breakeven)
- **Veredicto**: NO RENTABLE

### 2. Drawdown inaceptable:
- -17.73% > límite FTMO (-10%)
- 2x peor que US30
- **Veredicto**: ALTO RIESGO

### 3. Overtrading:
- 6.6 trades/día (3.5x más que US30)
- Más comisiones y slippage
- **Veredicto**: INEFICIENTE

### 4. Win Rate bajo:
- 23.2% (solo 1 de cada 4 gana)
- Menor que US30 (29.4%)
- **Veredicto**: BAJA PRECISIÓN

---

## ✅ ASPECTOS POSITIVOS GBPJPY

1. **R:R consistente**: Wins +3.48R, Losses -1.03R
2. **OBs detectados**: 422 (muestra suficiente)
3. **Distribución balanceada**: 50% LONG / 50% SHORT
4. **Horarios identificados**: Mayor actividad 16:00-19:00 UTC

---

## 🎯 CONCLUSIÓN

### Veredicto final:
**❌ NO USAR GBPJPY CON ESTA ESTRATEGIA**

### Razones:
1. US30 es **440x más rentable** (+30.91% vs +0.07%)
2. GBPJPY tiene **2x peor DD** (-17.73% vs -8.77%)
3. GBPJPY **NO cumple FTMO** (DD > -10%)
4. GBPJPY genera **overtrading** (6.6 trades/día)

### Recomendación:
✅ **MANTENER US30 COMO ÚNICO SÍMBOLO**

---

## 📁 ARCHIVOS GENERADOS

### Documentos:
- `BACKTEST_GBPJPY_24H_COMPLETO.md` - Análisis completo
- `TABLA_GBPJPY_ULTIMAS_15.md` - Tabla detallada (este archivo)
- `RESUMEN_EJECUTIVO_GBPJPY.md` - Resumen ejecutivo

### Datos:
- `backtest_gbpjpy_24h_results.csv` - 185 trades completos
- `gbpjpy_ultimas_15_trades.csv` - Últimas 15 operaciones

### Pine Script:
- `strategies/order_block/tradingview/gbpjpy_ultimas_15.pine` - Visualización TradingView

### Script:
- `backtest_gbpjpy_24h.py` - Script de backtest

---

## 🚀 PRÓXIMOS PASOS

### Opción 1 (RECOMENDADA):
✅ **Continuar con US30 únicamente**
- Retorno: +30.91%
- Max DD: -8.77%
- FTMO compliant
- Probado y validado

### Opción 2 (NO RECOMENDADA):
❌ **Optimizar GBPJPY desde cero**
- Requiere nuevos parámetros
- Requiere más datos históricos
- Requiere tiempo de desarrollo
- Resultado incierto

---

## 📊 DATOS TÉCNICOS

### OBs detectados:
- **Total**: 422 OBs
- **Bullish**: 222 (52.6%)
- **Bearish**: 200 (47.4%)

### Configuración usada:
- consecutive_candles: 4
- zone_type: half_candle
- buffer_points: 25 pips
- target_rr: 3.5
- require_bos: False
- Sesión: 24H

### Período:
- M5: 19 Feb - 27 Mar 2026 (7,430 velas)
- M1: 26 Feb - 27 Mar 2026 (30,000 velas)
- Duración: 28 días

---

**DECISIÓN FINAL**: ❌ GBPJPY NO VIABLE - Mantener US30 exclusivamente

**FECHA**: 30 Marzo 2026
