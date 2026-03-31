# 📊 BACKTEST NAS100 24H - ESTRATEGIA ORDER BLOCK LIMIT

**Fecha**: 30 Marzo 2026  
**Símbolo**: NAS100 (NASDAQ-100)  
**Timeframes**: M5 (detección OB) + M1 (entry)  
**Tipo de orden**: LIMIT (entry en zone_high/zone_low)  
**Sesión**: 24H (sin filtro)

---

## ⚙️ CONFIGURACIÓN

### Parámetros:
- **consecutive_candles**: 4
- **zone_type**: half_candle
- **max_atr_mult**: 3.5
- **expiry_candles**: 100
- **buffer_points**: 25 puntos
- **target_rr**: 3.5
- **require_bos**: False
- **Sesión**: 24H (00:00-23:59 UTC)
- **Point value**: $1 por punto
- **Spread**: 2 puntos

### Datos:
- **M5**: 10,365 velas (3 Feb - 27 Mar 2026)
- **M1**: 45,000 velas (10 Feb - 27 Mar 2026)
- **Duración efectiva**: 44 días

---

## 📈 RESULTADOS GENERALES

| Métrica | Valor |
|---------|-------|
| **Balance inicial** | $100,000.00 |
| **Balance final** | $80,046.16 |
| **Retorno total** | **-19.95%** ❌ |
| **Max Drawdown** | **-32.17%** ❌ |
| **Duración** | 44 días |
| **Total trades** | 247 |
| **Ganadores** | 48 (19.4%) |
| **Perdedores** | 199 (80.6%) |
| **Win Rate** | **19.4%** ❌ |
| **Profit Factor** | **0.76** ❌ |
| **Avg Winner** | $1,305.77 |
| **Avg Loser** | $-415.23 |
| **Expectancy** | **-$80.78** por trade ❌ |
| **Trades/día** | 5.6 |

---

## 📊 RESULTADOS POR DIRECCIÓN

### LONG:
- **Trades**: 118 (47.8%)
- **Win Rate**: 16.1% ❌
- **PnL**: **-$16,663.49** ❌
- **Avg R**: -0.32R

### SHORT:
- **Trades**: 129 (52.2%)
- **Win Rate**: 22.5%
- **PnL**: **-$3,290.35** ❌
- **Avg R**: -0.03R

---

## 🕐 DISTRIBUCIÓN POR HORA UTC (Top 10)

| Hora UTC | Trades | % Total |
|----------|--------|---------|
| 10:00 | 17 | 6.9% |
| 12:00 | 16 | 6.5% |
| 16:00 | 16 | 6.5% |
| 17:00 | 15 | 6.1% |
| 20:00 | 15 | 6.1% |
| 19:00 | 13 | 5.3% |
| 01:00 | 12 | 4.9% |
| 21:00 | 12 | 4.9% |
| 08:00 | 12 | 4.9% |
| 15:00 | 12 | 4.9% |

**Observación**: Actividad distribuida uniformemente, sin horario dominante.

---

## 📋 ÚLTIMAS 15 OPERACIONES (más recientes)

| # | Fecha | Hora | Dir | Resultado | Entry | SL | TP | PnL | R |
|---|-------|------|-----|-----------|-------|----|----|-----|---|
| 1 | 27-Mar | 19:50 | SHORT | ✅ WIN | 23313.88 | 23348.38 | 23193.13 | +$1,354.30 | +3.44R |
| 2 | 27-Mar | 16:17 | SHORT | ❌ LOSS | 23409.05 | 23462.95 | 23220.40 | -$410.19 | -1.04R |
| 3 | 27-Mar | 15:34 | LONG | ❌ LOSS | 23445.85 | 23394.35 | 23626.10 | -$413.02 | -1.04R |
| 4 | 27-Mar | 12:26 | SHORT | ✅ WIN | 23587.35 | 23628.95 | 23441.75 | +$1,349.12 | +3.45R |
| 5 | 27-Mar | 11:18 | LONG | ❌ LOSS | 23621.95 | 23586.35 | 23746.55 | -$414.98 | -1.06R |
| 6 | 27-Mar | 10:53 | LONG | ❌ LOSS | 23676.25 | 23635.95 | 23817.30 | -$414.58 | -1.05R |
| 7 | 27-Mar | 09:49 | LONG | ❌ LOSS | 23710.35 | 23680.15 | 23816.05 | -$425.64 | -1.07R |
| 8 | 27-Mar | 09:33 | LONG | ❌ LOSS | 23730.85 | 23690.75 | 23871.20 | -$419.11 | -1.05R |
| 9 | 27-Mar | 07:23 | SHORT | ❌ LOSS | 23703.25 | 23734.95 | 23592.30 | -$428.93 | -1.06R |
| 10 | 27-Mar | 05:33 | SHORT | ❌ LOSS | 23677.95 | 23715.25 | 23547.40 | -$425.11 | -1.05R |
| 11 | 27-Mar | 03:21 | LONG | ❌ LOSS | 23673.45 | 23622.85 | 23850.55 | -$421.61 | -1.04R |
| 12 | 26-Mar | 13:06 | SHORT | ❌ LOSS | 23973.15 | 24018.65 | 23813.90 | -$418.98 | -1.04R |
| 13 | 25-Mar | 17:26 | SHORT | ✅ WIN | 24254.63 | 24340.03 | 23955.73 | +$1,371.46 | +3.48R |
| 14 | 25-Mar | 17:01 | LONG | ✅ WIN | 24133.65 | 24089.05 | 24289.75 | +$1,339.86 | +3.46R |
| 15 | 25-Mar | 14:40 | SHORT | ✅ WIN | 24293.55 | 24338.65 | 24135.70 | +$1,317.29 | +3.46R |

**Últimas 15**: 5 WIN (33.3%) / 10 LOSS (66.7%) = +$1,563.85

---

## 🆚 COMPARACIÓN: NAS100 24H vs US30 NY

| Métrica | NAS100 24H | US30 NY | Diferencia |
|---------|------------|---------|------------|
| **Retorno** | -19.95% ❌ | +30.91% ✅ | **-50.86%** |
| **Max DD** | -32.17% ❌ | -8.77% ✅ | **-23.40%** |
| **Win Rate** | 19.4% ❌ | 29.4% ✅ | -10.0% |
| **Profit Factor** | 0.76 ❌ | 1.36 ✅ | -0.60 |
| **Trades** | 247 | 197 | +50 |
| **Trades/día** | 5.6 | 1.9 | +3.7 |
| **Expectancy** | -$80.78 ❌ | +$157.21 ✅ | **-$237.99** |
| **FTMO** | NO ❌ | SI ✅ | - |

---

## 🔍 ANÁLISIS CRÍTICO

### ❌ PROBLEMAS CRÍTICOS:

1. **PÉRDIDA MASIVA**: -19.95% en 44 días
   - Pierde $19,953.84
   - Profit Factor = 0.76 (pierde más de lo que gana)
   - **Veredicto**: DESTRUYE CAPITAL

2. **Drawdown catastrófico**: -32.17%
   - 3.7x peor que US30 (-8.77%)
   - **NO cumple FTMO** (límite -10%)
   - **Veredicto**: RIESGO EXTREMO

3. **Win Rate pésimo**: 19.4%
   - Solo 1 de cada 5 trades gana
   - 10% peor que US30 (29.4%)
   - **Veredicto**: BAJA PRECISIÓN

4. **Overtrading severo**: 5.6 trades/día
   - 3x más que US30 (1.9/día)
   - Más comisiones y slippage
   - **Veredicto**: SOBREOPERA

5. **LONG catastrófico**: -$16,663.49
   - Win Rate: 16.1%
   - Pierde 5x más que SHORT
   - **Veredicto**: DIRECCIÓN PERDEDORA

6. **Expectancy negativa**: -$80.78 por trade
   - Cada trade pierde dinero en promedio
   - **Veredicto**: MATEMÁTICAMENTE PERDEDOR

---

## ✅ ASPECTOS POSITIVOS

1. **R:R consistente**: Wins +3.45R, Losses -1.05R
2. **OBs detectados**: 617 (muestra suficiente)
3. **Últimas 15**: 5 wins (mejor que promedio general)

---

## 💡 CONCLUSIONES

### Rentabilidad:
- ❌ **ESTRATEGIA DESTRUYE CAPITAL EN NAS100** (-19.95%)
- ❌ Drawdown catastrófico (-32.17%)
- ❌ Profit Factor < 1.0 (pierde más de lo que gana)
- ❌ Win Rate pésimo (19.4%)
- ❌ Expectancy negativa (-$80.78/trade)

### Comparación con US30:
- ❌ **US30 es infinitamente mejor** (+30.91% vs -19.95%)
- ❌ NAS100 tiene 3.7x peor DD (-32.17% vs -8.77%)
- ❌ Overtrading: 5.6 trades/día vs 1.9 en US30

### Factores clave:
1. **Volatilidad**: NAS100 es más volátil que US30
2. **Parámetros**: Buffer de 25 puntos inadecuado
3. **R:R 3.5**: Demasiado ambicioso para NAS100
4. **LONG**: Dirección perdedora (-$16,663.49)

---

## 🎯 RECOMENDACIONES

### Para NAS100 (NO RECOMENDADO):
1. **Reducir R:R**: 2.0-2.5 (vs 3.5)
2. **Ajustar buffer**: 15-20 puntos (vs 25)
3. **Filtrar sesión**: Solo NY (13:30-20:00)
4. **Aumentar filtros**: Activar BOS obligatorio
5. **Considerar solo SHORT**: LONG pierde -$16,663

### Recomendación final:
- ✅ **MANTENER US30 EXCLUSIVAMENTE**
- ❌ **NO OPERAR NAS100 con estos parámetros**
- ❌ NAS100 pierde -19.95% vs US30 gana +30.91%
- ❌ Diferencia de 50.86% en retorno

---

## 📁 ARCHIVOS GENERADOS

1. `backtest_nas100_24h_results.csv` - 247 trades completos
2. `nas100_ultimas_15_trades.csv` - Últimas 15 operaciones
3. `strategies/order_block/tradingview/nas100_ultimas_15.pine` - Pine Script
4. `backtest_nas100_24h.py` - Script de backtest

---

## 🎨 VISUALIZACIÓN EN TRADINGVIEW

### Instrucciones:
1. Abrir TradingView con gráfico **NAS100 M1**
2. Ir a Pine Editor
3. Copiar contenido de `strategies/order_block/tradingview/nas100_ultimas_15.pine`
4. Aplicar al gráfico
5. Navegar a fechas: **25-27 Marzo 2026**

### Elementos visualizados:
- **Cajas verdes/rojas**: Zonas OB (bullish/bearish)
- **Línea azul/naranja gruesa**: Entry (LONG/SHORT)
- **Línea roja punteada**: Stop Loss
- **Línea verde punteada**: Take Profit
- **Labels**: Resultado (WIN/LOSS) con PnL

---

## 📊 ESTADÍSTICAS DETALLADAS

### OBs detectados:
- **Total**: 617 OBs en M5
- **Bullish**: 302 (48.9%)
- **Bearish**: 315 (51.1%)

### Distribución de trades:
- **LONG**: 118 trades (47.8%)
  - Win Rate: 16.1% ❌
  - PnL: -$16,663.49 ❌
- **SHORT**: 129 trades (52.2%)
  - Win Rate: 22.5%
  - PnL: -$3,290.35 ❌

### Período efectivo:
- **Inicio**: 10 Feb 2026
- **Fin**: 27 Mar 2026
- **Días**: 44 días

---

## ⚠️ ALERTAS CRÍTICAS

### 🚨 DESTRUYE CAPITAL:
- **Pérdida**: -$19,953.84 en 44 días
- **Expectancy negativa**: -$80.78 por trade
- **Profit Factor**: 0.76 (pierde más de lo que gana)

### 🚨 NO CUMPLE FTMO:
- **Max DD**: -32.17% >>> límite -10%
- **Retorno**: -19.95% (negativo)

### 🚨 RIESGO EXTREMO:
- **DD 3.7x peor** que US30
- **Win Rate 19.4%** (1 de cada 5)
- **LONG pierde** -$16,663.49

---

## 🆚 COMPARACIÓN FINAL: 3 SÍMBOLOS

```
                    US30 NY         NAS100 24H      GBPJPY 24H
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Retorno             +30.91% ✅      -19.95% ❌      +0.07% ⚠️
Max DD              -8.77% ✅       -32.17% ❌      -17.73% ❌
Win Rate            29.4% ✅        19.4% ❌        23.2% ⚠️
Profit Factor       1.36 ✅         0.76 ❌         1.00 ⚠️
Trades              197             247             185
Trades/dia          1.9 ✅          5.6 ❌          6.6 ❌
Expectancy          +$157 ✅        -$81 ❌         +$0.36 ⚠️
FTMO Compliant      SI ✅           NO ❌           NO ❌
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RANKING             🥇 1º           🚫 3º           ⚠️ 2º
```

**GANADOR ABSOLUTO**: US30 NY (único rentable)

---

## 💡 CONCLUSIÓN FINAL

### Veredicto:
**❌ NAS100 NO VIABLE - DESTRUYE CAPITAL**

### Razones:
1. Pérdida de -19.95% en 44 días
2. Drawdown catastrófico (-32.17%)
3. Profit Factor < 1.0 (matemáticamente perdedor)
4. Win Rate pésimo (19.4%)
5. LONG pierde -$16,663 (dirección perdedora)

### Comparación:
- **US30**: +30.91% ✅
- **NAS100**: -19.95% ❌
- **GBPJPY**: +0.07% ⚠️

### Decisión:
✅ **MANTENER US30 COMO ÚNICO SÍMBOLO**

NAS100 y GBPJPY no funcionan con los parámetros optimizados para US30. La estrategia está específicamente diseñada para US30 en sesión NY.

---

## 🚀 RECOMENDACIÓN FINAL

### Para el usuario:
**NO perder tiempo optimizando NAS100 o GBPJPY**

### Razones:
1. US30 funciona perfectamente (+30.91%)
2. NAS100 pierde capital (-19.95%)
3. GBPJPY apenas breakeven (+0.07%)
4. Optimizar otros símbolos requiere meses de trabajo

### Acción:
✅ **Operar EXCLUSIVAMENTE US30 en sesión NY**
- Retorno: +30.91%
- Max DD: -8.77%
- FTMO compliant
- Probado y validado

---

**FECHA**: 30 Marzo 2026  
**CONCLUSIÓN**: ❌ NAS100 DESTRUYE CAPITAL - US30 es el único símbolo viable
