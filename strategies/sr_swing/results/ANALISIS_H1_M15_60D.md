# 📊 Análisis H1+M15 (60 días) - US30

**Fecha**: 26 de Marzo, 2026  
**Período**: 60 días (26 Ene - 26 Mar 2026)  
**Configuración**: H1 para zonas, M15 para señales, Solo LONGs

---

## ⚠️ Conclusión Ejecutiva

**H1+M15 NO es rentable** con los parámetros actuales.

| Métrica | H4+H1 (2 años) | H1+M15 (60 días) | Diferencia |
|---------|----------------|------------------|------------|
| **Profit Factor** | **3.57** | **0.64** | ❌ -82% |
| **Win Rate** | **72.0%** | **36.4%** | ❌ -49% |
| **Retorno** | **+9.01%** | **-1.25%** | ❌ Negativo |
| **Frecuencia** | 1.0 trades/mes | 5.5 trades/mes | ✅ +450% |
| **Max DD** | 0.98% | 2.33% | ⚠️ +138% |

**Veredicto**: La mayor frecuencia de H1+M15 **NO compensa** la caída dramática en calidad de señales.

---

## 📉 Resultados Detallados

### Métricas Generales

```
Balance Inicial:         $100,000.00
Balance Final:           $98,750.12
Retorno:                 -1.25%

Total Trades:            11
Ganadoras:               4 (36.4%)
Perdedoras:              7 (63.6%)

Profit Factor (USD):     0.64  ← POR DEBAJO DE 1.0
Max Drawdown:            2.33%
Max Pérdidas Consecutivas: 2
R:R Promedio:            2.21
```

### Por Tipo de Señal

| Señal | Trades | Win Rate | Calificación |
|-------|--------|----------|--------------|
| **False Breakout B1** | 7 | 42.9% | ⚠️ Marginal |
| **Pin Bar** | 4 | 25.0% | ❌ Muy malo |

**Problema**: Ambos patrones tienen Win Rate **muy por debajo** del 50%.

---

## 🔍 Análisis de Causa Raíz

### 1. Período de Prueba Insuficiente

**60 días NO son suficientes** para validar una estrategia:
- Solo 11 trades (muestra muy pequeña)
- Alta varianza estadística
- Puede ser un período atípico del mercado

**Mínimo recomendado**: 1 año (365 días) con al menos 50 trades.

### 2. Condiciones de Mercado Adversas

El período de prueba (Ene-Mar 2026) fue **bajista** para US30:

```
EMA 200 (H1): 47,606 puntos
Precio actual: 45,955 puntos
Tendencia: BAJISTA (-3.5%)
```

**Problema**: La estrategia Solo LONGs **no puede operar** en mercados bajistas fuertes.

### 3. Parámetros Demasiado Agresivos

Los parámetros de `strategy_params_h1_m15.yaml` fueron ajustados para timeframes menores, pero pueden ser **demasiado permisivos**:

```yaml
zones:
  swing_strength: 3              # Muy bajo (H4+H1 usa 5)
  min_wick_ratio: 0.40           # Muy bajo (H4+H1 usa 0.50)

entry:
  pin_bar:
    min_wick_to_body_ratio: 2.0  # Igual que H4+H1
  false_breakout:
    b1_min_body_ratio: 0.50      # Más bajo que H4+H1 (0.60)
    b1_min_penetration_points: 3 # Más bajo que H4+H1 (5)
```

**Resultado**: Se generan señales de **baja calidad** (Win Rate 36.4%).

### 4. Ruido de Mercado en Timeframes Menores

M15 tiene **mucho más ruido** que H1:
- Más falsos breakouts
- Más manipulación intradía
- Zonas menos respetadas

**Efecto**: Los patrones que funcionan en H4+H1 **no se traducen** a H1+M15.

---

## 🎯 Recomendaciones

### Opción 1: **NO usar H1+M15** (Recomendado)

**Razones**:
- ❌ PF de 0.64 (no rentable)
- ❌ Win Rate de 36.4% (muy bajo)
- ❌ Requiere ajustes drásticos de parámetros
- ✅ H4+H1 ya funciona excelentemente (PF 3.57)

**Acción**: Quedarse con **H4+H1 únicamente** para FTMO.

### Opción 2: Validar en Demo con Más Datos

Si quieres darle otra oportunidad a H1+M15:

1. **Operar en demo durante 3-6 meses** (no backtest de 60 días)
2. **Ajustar parámetros**:
   - Aumentar `swing_strength` de 3 a 4
   - Aumentar `min_wick_ratio` de 0.40 a 0.50
   - Aumentar `b1_min_body_ratio` de 0.50 a 0.65
   - Aumentar `b1_min_penetration_points` de 3 a 7
3. **Validar con al menos 50 trades** antes de usar en FTMO

**Riesgo**: Puede seguir siendo no rentable incluso con ajustes.

### Opción 3: Probar H1+M15 en Mercado Alcista

El período de prueba fue bajista. Probar en un período alcista:

```bash
# Descargar datos de Dic 2024 - Feb 2025 (período alcista)
python3 download_yahoo_data.py --ticker "^DJI" --days 60 --interval 15m --output US30_M15_60d_bullish
python3 download_yahoo_data.py --ticker "^DJI" --days 60 --interval 1h --output US30_H1_60d_bullish

# Re-ejecutar backtest
python3 run_backtest.py \
  --data-h1 data/US30_M15_60d_bullish.csv \
  --data-h4 data/US30_H1_60d_bullish.csv \
  --instrument US30 \
  --config config/strategy_params_h1_m15.yaml \
  --output data/backtest_US30_h1_m15_bullish.csv
```

**Problema**: Yahoo Finance solo tiene datos recientes, no históricos de 2024.

---

## 📊 Comparativa Final

### H4+H1 (Validada)

```
✅ Profit Factor: 3.57 (excelente)
✅ Win Rate: 72.0% (muy alto)
✅ Retorno: +9.01% en 2 años
✅ Max DD: 0.98% (mínimo)
⚠️ Frecuencia: 1.0 trades/mes (baja)
```

**Veredicto**: **Estrategia validada y lista para FTMO**.

### H1+M15 (No Validada)

```
❌ Profit Factor: 0.64 (no rentable)
❌ Win Rate: 36.4% (muy bajo)
❌ Retorno: -1.25% en 60 días
⚠️ Max DD: 2.33% (aceptable)
✅ Frecuencia: 5.5 trades/mes (alta)
```

**Veredicto**: **NO usar en FTMO sin validación adicional**.

---

## 🚀 Plan de Acción Recomendado

### Fase 1: Implementar H4+H1 en Demo (Semana 1-2)

**Instrumentos**: US30 + NAS100  
**Configuración**: H4 zonas + H1 señales, Solo LONGs  
**Objetivo**: Validar métricas en cuenta demo

### Fase 2: Monitorear Frecuencia (Semana 3-4)

**Frecuencia esperada**: 2.6 trades/mes (US30 + NAS100)  
**Mínimo FTMO**: 4 trades/mes

**Si frecuencia es insuficiente**:
- Añadir SPX500 (1.5 trades/mes adicionales)
- **NO añadir H1+M15** hasta validar en demo

### Fase 3: Validar H1+M15 en Demo (Mes 2-3, Opcional)

**Solo si**:
- H4+H1 funciona perfectamente en demo
- Frecuencia sigue siendo insuficiente
- Tienes tiempo para validar 3-6 meses

**Ajustes necesarios**:
- Endurecer todos los filtros (ver Opción 2)
- Validar con mínimo 50 trades
- Comparar PF con H4+H1

### Fase 4: Challenge FTMO (Mes 3-4)

**Configuración final**:
- US30 + NAS100 (H4+H1)
- SPX500 (H4+H1) si es necesario para frecuencia
- H1+M15 **solo si** validado en demo con PF > 1.5

---

## 📁 Archivos Generados

- `data/US30_M15_60d.csv` - Datos M15 (1,079 registros)
- `data/US30_H1_60d.csv` - Datos H1 (292 registros)
- `data/backtest_US30_h1_m15_60d.csv` - Resultados backtest (11 trades)
- `config/strategy_params_h1_m15.yaml` - Configuración H1+M15
- `config/instruments_h1_m15.yaml` - Instrumentos H1+M15

---

## 🎓 Lecciones Aprendidas

1. **Timeframes menores ≠ Mejor frecuencia**: Más trades no significa más rentabilidad
2. **60 días NO son suficientes**: Mínimo 1 año para validar estrategia
3. **Parámetros no se escalan linealmente**: Lo que funciona en H4+H1 no funciona igual en H1+M15
4. **Solo LONGs en mercado bajista = 0 trades**: Necesitas direccionalidad bidireccional o filtros más inteligentes
5. **H4+H1 ya funciona**: No arregles lo que no está roto

---

## ✅ Decisión Final

**Recomendación**: **NO usar H1+M15** hasta tener validación en demo con al menos 3 meses de datos y PF > 1.5.

**Quedarse con H4+H1** (US30 + NAS100) para FTMO.

Si la frecuencia es insuficiente, **añadir SPX500** (H4+H1) antes que H1+M15.

---

**Próximos pasos**: ¿Quieres que configure H4+H1 para demo o prefieres ajustar parámetros de H1+M15 y probar de nuevo?
