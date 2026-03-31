# 📊 BACKTEST GBPJPY - ESTRATEGIA ORDER BLOCK LIMIT

**Fecha**: 30 Marzo 2026  
**Símbolo**: GBPJPY  
**Timeframes**: M5 (detección OB) + M1 (entry)  
**Tipo de orden**: LIMIT (entry en zone_high/zone_low)

---

## ⚙️ CONFIGURACIÓN

### Parámetros (idénticos a US30):
- **consecutive_candles**: 4
- **zone_type**: half_candle
- **max_atr_mult**: 3.5
- **expiry_candles**: 100
- **buffer_points**: 0.025 (25 pips)
- **target_rr**: 3.5
- **require_bos**: False
- **Sesión NY**: 13:30-20:00 UTC (skip 15 min)

### Adaptaciones para GBPJPY:
- **Buffer**: 25 pips (0.025) vs 25 puntos en US30
- **Point value**: $1000 por pip por lote estándar
- **Spread**: 2 pips (0.002)

---

## 📈 RESULTADOS GENERALES

| Métrica | Valor |
|---------|-------|
| **Balance inicial** | $100,000.00 |
| **Balance final** | $103,129.41 |
| **Retorno total** | **+3.13%** |
| **Max Drawdown** | **-6.81%** ($-6,805.69) |
| **Duración** | 28 días |
| **Total trades** | 64 |
| **Win Rate** | 25.0% |
| **Profit Factor** | 1.13 |
| **Avg Winner** | $1,733.94 |
| **Avg Loser** | $-512.78 |
| **Expectancy** | $48.90 por trade |
| **Trades/día** | 2.3 |

---

## 📊 RESULTADOS POR DIRECCIÓN

### LONG:
- **Trades**: 32
- **Win Rate**: 28.1%
- **PnL**: $+3,826.93
- **Avg R**: 0.24R

### SHORT:
- **Trades**: 32
- **Win Rate**: 21.9%
- **PnL**: $-697.52
- **Avg R**: -0.04R

---

## 🆚 COMPARACIÓN: GBPJPY vs US30

| Métrica | GBPJPY | US30 | Diferencia |
|---------|--------|------|------------|
| **Retorno** | +3.13% | +30.91% | **-27.78%** |
| **Max DD** | -6.81% | -8.77% | +1.96% (mejor) |
| **Win Rate** | 25.0% | 29.4% | -4.4% |
| **Profit Factor** | 1.13 | 1.36 | -0.23 |
| **Trades** | 64 | 197 | -133 |
| **Trades/día** | 2.3 | 1.9 | +0.4 |
| **Duración** | 28 días | 104 días | -76 días |

---

## ⚠️ LIMITACIONES DEL BACKTEST

### 1. Datos M1 insuficientes:
- **M5**: 260 días (Jul 2025 - Mar 2026)
- **M1**: Solo 29 días (Feb 2026 - Mar 2026)
- **Impacto**: Solo se pueden generar trades en los últimos 29 días

### 2. Muestra pequeña:
- 64 trades vs 197 en US30
- Menor significancia estadística
- Resultados menos confiables

### 3. Sesión NY en GBPJPY:
- GBPJPY es un par asiático/europeo
- Sesión NY (13:30-20:00 UTC) no es su horario de mayor liquidez
- Londres (07:00-16:00 UTC) y Asia (00:00-09:00 UTC) son más activas

---

## 🎯 CONCLUSIONES

### Rentabilidad:
- ✅ **Estrategia MARGINAL en GBPJPY** (+3.13%)
- ✅ Drawdown controlado (-6.81%)
- ⚠️ Profit Factor bajo (1.13)
- ⚠️ Win Rate bajo (25%)

### Comparación con US30:
- ❌ **US30 es 10x más rentable** (+30.91% vs +3.13%)
- ✅ GBPJPY tiene menor DD (-6.81% vs -8.77%)
- ❌ Menos trades y menor frecuencia

### Factores clave:
1. **Sesión**: NY no es óptima para GBPJPY
2. **Volatilidad**: GBPJPY es más volátil que US30 en diferentes horarios
3. **Datos**: Solo 29 días M1 limita la validación

---

## 💡 RECOMENDACIONES

### Para mejorar GBPJPY:
1. **Cambiar sesión**:
   - Probar Londres: 07:00-16:00 UTC
   - Probar Asia: 00:00-09:00 UTC
   - Probar 24h sin filtro de sesión

2. **Ajustar parámetros**:
   - Buffer: 15-20 pips (GBPJPY más volátil)
   - R:R: 2.5-3.0 (menor que US30)
   - ATR mult: 2.5-3.0

3. **Obtener más datos**:
   - Descargar GBPJPY_M1_260d.csv completo
   - Validar con muestra > 150 trades

### Recomendación final:
- ✅ **Mantener US30 como símbolo principal** (+30.91%)
- ⚠️ GBPJPY requiere optimización específica
- ⚠️ No usar GBPJPY con parámetros de US30

---

## 📁 ARCHIVOS GENERADOS

- `backtest_gbpjpy_limit_results.csv` - Resultados detallados de 64 trades
- `backtest_gbpjpy_limit.py` - Script de backtest

---

## 🔍 DATOS TÉCNICOS

### OBs detectados:
- **Total**: 2870 OBs en M5
- **Bullish**: 1541 (53.7%)
- **Bearish**: 1329 (46.3%)

### Distribución de trades:
- **LONG**: 32 trades (50%)
- **SHORT**: 32 trades (50%)

### Período efectivo:
- **Inicio**: 26 Feb 2026
- **Fin**: 27 Mar 2026
- **Días**: 28 días (limitado por datos M1)

---

**CONCLUSIÓN FINAL**: La estrategia funciona en GBPJPY pero con rentabilidad 10x menor que US30. Se recomienda mantener US30 como símbolo principal y optimizar GBPJPY por separado si se desea operar Forex.
