# 📊 RESULTADOS MULTI-INSTRUMENTO - V4 Solo LONGs

**Fecha**: 26 de marzo de 2026  
**Estrategia**: V4 Solo LONGs (H4 Zonas + H1 Señales)  
**Período**: 2 años (Mar 2024 - Mar 2026)  
**Capital Inicial**: $100,000 por instrumento

---

## 🎯 Resumen Ejecutivo

He ejecutado la estrategia V4 (Solo LONGs) en los 3 índices principales de EE.UU. Los resultados confirman que la estrategia es **rentable en todos los instrumentos**, aunque con variaciones significativas en rendimiento.

---

## 📈 Resultados por Instrumento

| Instrumento | Trades | Win Rate | Balance Final | Retorno | PF | Max DD |
|-------------|--------|----------|---------------|---------|-----|--------|
| **US30** | 25 | **72.0%** ✅ | **$109,006** | **+9.01%** | **3.57** ✅ | **0.98%** ✅ |
| **NAS100** | 37 | 51.4% | $107,971 | +7.97% | 1.89 | 2.75% |
| **SPX500** | 30 | 56.7% | $101,556 | +1.56% | 1.24 ⚠️ | 2.25% |

### Total Combinado

```
Total Trades:      92 en 2 años
Frecuencia:        3.8 trades/mes
Balance Combinado: $318,533 (+6.18% promedio por instrumento)
```

---

## 🔍 Análisis Detallado

### US30 (Dow Jones) - ⭐ Mejor Rendimiento

```
Trades:        25
Win Rate:      72.0% (18 ganadores, 7 perdedores)
Retorno:       +9.01%
Profit Factor: 3.57 (excelente)
Max Drawdown:  0.98% (mínimo)
```

**Por Tipo de Señal**:
- Pin Bar: 7 trades, WR: 71.4%
- False Breakout B1: 18 trades, WR: 72.2%

**Conclusión**: US30 es el instrumento más confiable. Ambos tipos de señales funcionan bien.

---

### NAS100 (Nasdaq) - ✅ Rentable

```
Trades:        37
Win Rate:      51.4% (19 ganadores, 18 perdedores)
Retorno:       +7.97%
Profit Factor: 1.89 (aceptable)
Max Drawdown:  2.75% (bajo)
```

**Por Tipo de Señal**:
- Pin Bar: 16 trades, WR: 43.8% ⚠️
- False Breakout B1: 21 trades, WR: 57.1% ✅

**Conclusión**: NAS100 es rentable pero menos consistente. Los Pin Bars tienen bajo rendimiento (43.8% WR). Considerar desactivar Pin Bars en NAS100.

---

### SPX500 (S&P 500) - ⚠️ Marginalmente Rentable

```
Trades:        30
Win Rate:      56.7% (17 ganadores, 13 perdedores)
Retorno:       +1.56% (muy bajo)
Profit Factor: 1.24 (apenas por encima de 1.0)
Max Drawdown:  2.25% (bajo)
```

**Por Tipo de Señal**:
- Pin Bar: 15 trades, WR: 60.0% ✅
- False Breakout B1: 15 trades, WR: 53.3%

**Conclusión**: SPX500 es marginalmente rentable. El PF de 1.24 es bajo. Considerar no operar SPX500 o ajustar parámetros específicos.

---

## 🎯 Análisis de Frecuencia

### Frecuencia por Instrumento

| Instrumento | Trades/Año | Trades/Mes | Cumple FTMO (4-5 days/mes) |
|-------------|------------|------------|----------------------------|
| US30 | 12.5 | 1.04 | ❌ No |
| NAS100 | 18.5 | 1.54 | ❌ No |
| SPX500 | 15.0 | 1.25 | ❌ No |
| **TOTAL** | **46** | **3.8** | ⚠️ Casi |

### Conclusión de Frecuencia

- **Individualmente**: Ningún instrumento cumple los mínimos FTMO (4-5 trading days/mes)
- **Combinados**: 3.8 trades/mes está cerca pero **probablemente no es suficiente**
- **Problema**: Si cada trade dura 1-2 días, 3.8 trades/mes = ~4-8 trading days/mes (límite)

---

## 💡 Hallazgos Clave

### 1. US30 es Superior

US30 tiene:
- **Mejor Win Rate**: 72.0% vs 51.4% (NAS100) vs 56.7% (SPX500)
- **Mejor Profit Factor**: 3.57 vs 1.89 vs 1.24
- **Menor Max DD**: 0.98% vs 2.75% vs 2.25%

**Conclusión**: Si solo pudieras operar 1 instrumento, US30 es la mejor opción.

### 2. NAS100 Añade Frecuencia sin Destruir Capital

NAS100 tiene:
- 37 trades (48% más que US30)
- PF de 1.89 (rentable)
- Max DD aceptable (2.75%)

**Conclusión**: NAS100 es un buen complemento para aumentar frecuencia.

### 3. SPX500 No Aporta Mucho Valor

SPX500 tiene:
- PF de solo 1.24 (muy bajo)
- Retorno de solo 1.56% en 2 años
- No justifica el riesgo adicional

**Conclusión**: Considerar NO operar SPX500, o ajustar parámetros específicos.

---

## 🚀 Recomendaciones

### Opción 1: US30 + NAS100 (⭐ Recomendado)

**Configuración**:
- Operar US30 y NAS100 únicamente
- Mantener H4+H1
- Solo LONGs

**Expectativa**:
- 25 + 37 = **62 trades en 2 años = 2.6 trades/mes**
- Retorno promedio: **+8.5%**
- PF promedio: **2.73**
- Max DD combinado: **~2%**

**Pros**:
- ✅ Elimina SPX500 que tiene PF bajo
- ✅ Mantiene alta calidad (PF > 1.8)
- ✅ Frecuencia aceptable

**Contras**:
- ❌ 2.6 trades/mes sigue siendo bajo para FTMO

---

### Opción 2: Los 3 Instrumentos + Ajustar SPX500

**Configuración**:
- Operar US30, NAS100, SPX500
- Ajustar parámetros específicos para SPX500:
  - Aumentar `min_rr_ratio` a 2.5 (más selectivo)
  - Reducir `sl_buffer_points` a 20 (SL más ajustado)

**Expectativa**:
- 92 trades = **3.8 trades/mes**
- Mejorar PF de SPX500 de 1.24 a ~1.5

**Pros**:
- ✅ Mayor frecuencia
- ✅ Diversificación

**Contras**:
- ❌ SPX500 puede seguir siendo problemático
- ❌ Requiere optimización adicional

---

### Opción 3: US30 + NAS100 en H4+H1 + US30 en H1+M15

**Configuración**:
- US30 y NAS100 en H4+H1 (base)
- US30 en H1+M15 (experimental)
- Zonas diferentes = no se solapan

**Expectativa**:
- H4+H1: 62 trades
- H1+M15: ~150-200 trades (estimado)
- Total: **200+ trades = 8+ trades/mes** ✅

**Pros**:
- ✅ Alta frecuencia
- ✅ Cumple FTMO
- ✅ Mantiene la estrategia base que funciona

**Contras**:
- ❌ H1+M15 NO está validado (puede tener PF bajo)
- ❌ Mayor complejidad operativa
- ❌ Riesgo de sobretrading

---

## ⚠️ Limitación Crítica: Datos M15

**Yahoo Finance limita datos intraday a 60 días** para intervalos < 1h.

Esto significa que **NO podemos hacer backtest de 2 años con M15**. Solo tenemos 60 días de datos, lo cual NO es suficiente para validar una estrategia (mínimo 1 año recomendado).

### Soluciones para Datos M15

1. **Usar broker con datos históricos** (FTMO, MetaTrader 5)
2. **Comprar datos históricos** (proveedores como TickData, Dukascopy)
3. **Forward testing** (operar en demo durante 3-6 meses para validar)
4. **NO usar M15** (quedarse con H4+H1)

---

## 🎯 Mi Recomendación Final

### Fase 1: Implementar US30 + NAS100 en H4+H1 (Inmediato)

**Por qué**:
- ✅ Ya está validado (2 años de datos)
- ✅ Ambos son rentables (PF > 1.8)
- ✅ 62 trades en 2 años = 2.6 trades/mes

**Acción**:
1. Operar US30 y NAS100 únicamente
2. Mantener configuración actual (H4+H1, Solo LONGs)
3. Monitorear durante 1-2 meses en demo

**Criterio de éxito**:
- Mantener PF > 2.0 combinado
- Max DD < 5%
- Al menos 5-6 trades en 2 meses

---

### Fase 2: SI Fase 1 funciona → Evaluar H1+M15

**Por qué**:
- ⚠️ Solo tenemos 60 días de datos M15
- ⚠️ No podemos hacer backtest de 2 años
- ⚠️ Necesitamos validación en demo

**Acción**:
1. Implementar H1+M15 en **demo** (no en backtest)
2. Operar durante 2-3 meses
3. Comparar métricas con H4+H1

**Criterio de éxito**:
- PF > 2.0 en demo
- Max DD < 5%
- Win Rate > 55%
- Frecuencia > 10 trades/mes

**Si H1+M15 funciona**: Añadir a la estrategia  
**Si H1+M15 falla**: Quedarse con H4+H1 únicamente

---

## 📁 Archivos Generados

- `data/backtest_US30_v4_longs_only.csv` - US30 H4+H1
- `data/backtest_NAS100_v4_longs_only.csv` - NAS100 H4+H1
- `data/backtest_SPX500_v4_longs_only.csv` - SPX500 H4+H1
- `config/strategy_params_h1_m15.yaml` - Config para H1+M15 (experimental)
- `config/instruments_h1_m15.yaml` - Instrumentos para H1+M15
- `run_parallel_backtests.py` - Script para backtests en paralelo

---

## 📝 Conclusión

**Estrategia validada en 3 instrumentos**:

✅ **US30**: Excelente (PF 3.57, WR 72%, Max DD 0.98%)  
✅ **NAS100**: Bueno (PF 1.89, WR 51.4%, Max DD 2.75%)  
⚠️ **SPX500**: Marginal (PF 1.24, WR 56.7%, Max DD 2.25%)

**Frecuencia combinada**: 3.8 trades/mes (cerca del mínimo FTMO)

**Recomendación**: Implementar US30 + NAS100 en demo y monitorear. Si la frecuencia es insuficiente, considerar añadir más instrumentos o reducir timeframes (pero validar en demo primero, no en backtest con datos limitados).

---

## ❓ Próximos Pasos

1. **"Implementa US30 + NAS100"** → Configuro para operar ambos instrumentos
2. **"Ajusta SPX500"** → Optimizo parámetros específicos para SPX500
3. **"Prueba H1+M15 en demo"** → Creo config y explico cómo validar en demo
4. **"Analiza por qué SPX500 es bajo"** → Investigo los trades de SPX500

**Tu decisión** 👇
