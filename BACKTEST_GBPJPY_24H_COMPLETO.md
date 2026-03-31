# 📊 BACKTEST GBPJPY 24H - ESTRATEGIA ORDER BLOCK LIMIT

**Fecha**: 30 Marzo 2026  
**Símbolo**: GBPJPY  
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
- **buffer_points**: 0.025 (25 pips)
- **target_rr**: 3.5
- **require_bos**: False
- **Sesión**: 24H (00:00-23:59 UTC)
- **Point value**: $1000 por pip por lote estándar
- **Spread**: 2 pips (0.002)

### Datos:
- **M5**: 7,430 velas (19 Feb - 27 Mar 2026)
- **M1**: 30,000 velas (26 Feb - 27 Mar 2026)
- **Duración efectiva**: 28 días

---

## 📈 RESULTADOS GENERALES

| Métrica | Valor |
|---------|-------|
| **Balance inicial** | $100,000.00 |
| **Balance final** | $100,066.43 |
| **Retorno total** | **+0.07%** |
| **Max Drawdown** | **-17.73%** ($-17,733.21) |
| **Duración** | 28 días |
| **Total trades** | 185 |
| **Ganadores** | 43 (23.2%) |
| **Perdedores** | 142 (76.8%) |
| **Win Rate** | **23.2%** |
| **Profit Factor** | **1.00** |
| **Avg Winner** | $1,668.89 |
| **Avg Loser** | $-504.90 |
| **Expectancy** | $0.36 por trade |
| **Trades/día** | 6.6 |

---

## 📊 RESULTADOS POR DIRECCIÓN

### LONG:
- **Trades**: 92 (49.7%)
- **Win Rate**: 21.7%
- **PnL**: $-2,574.97
- **Avg R**: -0.05R

### SHORT:
- **Trades**: 93 (50.3%)
- **Win Rate**: 24.7%
- **PnL**: $+2,641.40
- **Avg R**: 0.06R

---

## 🕐 DISTRIBUCIÓN POR HORA UTC (Top 10)

| Hora UTC | Trades | % Total |
|----------|--------|---------|
| 16:00 | 17 | 9.2% |
| 19:00 | 12 | 6.5% |
| 07:00 | 11 | 5.9% |
| 12:00 | 11 | 5.9% |
| 18:00 | 10 | 5.4% |
| 00:00 | 9 | 4.9% |
| 22:00 | 9 | 4.9% |
| 03:00 | 8 | 4.3% |
| 11:00 | 8 | 4.3% |
| 13:00 | 7 | 3.8% |

**Observación**: Mayor actividad en horario europeo (07:00-19:00 UTC), como se esperaba para GBPJPY.

---

## 📋 ÚLTIMAS 15 OPERACIONES (más recientes)

| # | Fecha | Hora | Dir | Resultado | Entry | SL | TP | PnL | R |
|---|-------|------|-----|-----------|-------|----|----|-----|---|
| 1 | 26-Mar | 23:11 | LONG | LOSS | 212.805 | 212.708 | 213.145 | -$510.63 | -1.02R |
| 2 | 26-Mar | 20:36 | SHORT | WIN | 213.028 | 213.181 | 212.492 | +$514.25 | +1.05R |
| 3 | 26-Mar | 19:01 | SHORT | WIN | 213.133 | 213.243 | 212.748 | +$1,712.20 | +3.48R |
| 4 | 26-Mar | 18:32 | LONG | LOSS | 213.104 | 213.008 | 213.440 | -$504.57 | -1.02R |
| 5 | 25-Mar | 19:03 | LONG | WIN | 212.779 | 212.656 | 213.209 | +$1,663.68 | +3.48R |
| 6 | 25-Mar | 16:40 | LONG | LOSS | 212.870 | 212.806 | 213.094 | -$495.03 | -1.03R |
| 7 | 25-Mar | 12:24 | LONG | WIN | 212.831 | 212.737 | 213.160 | +$1,641.35 | +3.48R |
| 8 | 25-Mar | 08:38 | SHORT | LOSS | 212.764 | 212.828 | 212.540 | -$489.09 | -1.03R |
| 9 | 25-Mar | 06:10 | LONG | LOSS | 212.774 | 212.703 | 213.022 | -$490.15 | -1.03R |
| 10 | 25-Mar | 05:06 | LONG | LOSS | 212.834 | 212.796 | 212.967 | -$504.47 | -1.05R |
| 11 | 25-Mar | 01:04 | SHORT | LOSS | 212.791 | 212.898 | 212.416 | -$490.70 | -1.02R |
| 12 | 25-Mar | 00:17 | LONG | WIN | 212.619 | 212.451 | 213.207 | +$1,680.21 | +3.49R |
| 13 | 24-Mar | 22:09 | LONG | LOSS | 212.690 | 212.624 | 212.921 | -$501.43 | -1.03R |
| 14 | 24-Mar | 21:43 | SHORT | LOSS | 212.717 | 212.826 | 212.336 | -$495.61 | -1.02R |
| 15 | 24-Mar | 13:12 | SHORT | LOSS | 212.655 | 212.740 | 212.357 | -$500.70 | -1.02R |

**Patrón observado**: 
- 5 WIN (33.3%) vs 10 LOSS (66.7%) en últimas 15
- Wins promedio: +$1,642 (+3.48R)
- Losses promedio: -$498 (-1.03R)

---

## 🆚 COMPARACIÓN: GBPJPY 24H vs US30 NY

| Métrica | GBPJPY 24H | US30 NY | Diferencia |
|---------|------------|---------|------------|
| **Retorno** | +0.07% | +30.91% | **-30.84%** |
| **Max DD** | -17.73% | -8.77% | **-8.96%** (peor) |
| **Win Rate** | 23.2% | 29.4% | -6.2% |
| **Profit Factor** | 1.00 | 1.36 | -0.36 |
| **Trades** | 185 | 197 | -12 |
| **Trades/día** | 6.6 | 1.9 | +4.7 |
| **Duración** | 28 días | 104 días | -76 días |

---

## 🔍 ANÁLISIS CRÍTICO

### ❌ Problemas identificados:

1. **Retorno casi nulo**: +0.07% en 28 días
   - Profit Factor = 1.00 (breakeven)
   - Estrategia no es rentable en GBPJPY

2. **Drawdown excesivo**: -17.73%
   - 2x peor que US30 (-8.77%)
   - **NO cumple FTMO** (límite -10%)
   - Riesgo muy alto para retorno casi nulo

3. **Win Rate muy bajo**: 23.2%
   - Menor que US30 (29.4%)
   - Solo 1 de cada 4 trades gana

4. **Overtrading**: 6.6 trades/día
   - 3.5x más que US30 (1.9/día)
   - Más comisiones y slippage

5. **LONG pierde dinero**: -$2,574.97
   - Solo SHORT es levemente rentable (+$2,641.40)

### ✅ Aspectos positivos:

1. **OBs detectados**: 422 OBs (suficiente muestra)
2. **Distribución balanceada**: 50% LONG / 50% SHORT
3. **R:R consistente**: Avg Winner 3.48R, Avg Loser -1.03R
4. **Horarios identificados**: Mayor actividad 16:00-19:00 UTC (Londres)

---

## 💡 CONCLUSIONES

### Rentabilidad:
- ❌ **Estrategia NO RENTABLE en GBPJPY 24H** (+0.07%)
- ❌ Drawdown inaceptable (-17.73%)
- ❌ Profit Factor = 1.00 (breakeven)
- ❌ Win Rate muy bajo (23.2%)

### Comparación con US30:
- ❌ **US30 es 440x más rentable** (+30.91% vs +0.07%)
- ❌ GBPJPY tiene 2x peor DD (-17.73% vs -8.77%)
- ❌ Overtrading: 6.6 trades/día vs 1.9 en US30

### Factores clave:
1. **Volatilidad**: GBPJPY es más errático que US30
2. **Parámetros**: Buffer de 25 pips puede ser inadecuado
3. **R:R 3.5**: Demasiado ambicioso para GBPJPY
4. **Sesión**: 24h genera overtrading sin mejorar resultados

---

## 🎯 RECOMENDACIONES

### Para GBPJPY (si se desea optimizar):

1. **Reducir R:R**: 2.0-2.5 (vs 3.5)
2. **Ajustar buffer**: 15-20 pips (vs 25)
3. **Filtrar sesiones**: Solo Londres (07:00-16:00) o Asia (00:00-09:00)
4. **Aumentar filtros**: Activar BOS o Rejection
5. **Reducir consecutive_candles**: 3 (vs 4)

### Recomendación final:
- ✅ **MANTENER US30 COMO SÍMBOLO PRINCIPAL**
- ❌ **NO usar GBPJPY con parámetros actuales**
- ⚠️ GBPJPY requiere optimización completa desde cero
- ⚠️ Diferencia de rentabilidad es demasiado grande (440x)

---

## 📁 ARCHIVOS GENERADOS

1. `backtest_gbpjpy_24h_results.csv` - 185 trades completos
2. `gbpjpy_ultimas_15_trades.csv` - Últimas 15 operaciones
3. `strategies/order_block/tradingview/gbpjpy_ultimas_15.pine` - Pine Script para TradingView
4. `backtest_gbpjpy_24h.py` - Script de backtest

---

## 🎨 VISUALIZACIÓN EN TRADINGVIEW

### Instrucciones:
1. Abrir TradingView con gráfico GBPJPY M1
2. Ir a Pine Editor
3. Copiar contenido de `strategies/order_block/tradingview/gbpjpy_ultimas_15.pine`
4. Aplicar al gráfico
5. Navegar a fechas: 24-27 Marzo 2026

### Elementos visualizados:
- **Cajas verdes/rojas**: Zonas OB (bullish/bearish)
- **Línea azul/naranja gruesa**: Entry (LONG/SHORT)
- **Línea roja punteada**: Stop Loss
- **Línea verde punteada**: Take Profit
- **Labels**: Resultado (WIN/LOSS) con PnL en USD y R

---

## 📊 ESTADÍSTICAS DETALLADAS

### OBs detectados:
- **Total**: 422 OBs en M5
- **Bullish**: 222 (52.6%)
- **Bearish**: 200 (47.4%)

### Distribución de trades:
- **LONG**: 92 trades (49.7%)
  - Win Rate: 21.7%
  - PnL: -$2,574.97
- **SHORT**: 93 trades (50.3%)
  - Win Rate: 24.7%
  - PnL: +$2,641.40

### Período efectivo:
- **Inicio**: 26 Feb 2026
- **Fin**: 27 Mar 2026
- **Días**: 28 días

### Frecuencia:
- **Trades/día**: 6.6
- **Trades/semana**: 46.2

---

## ⚠️ ALERTAS CRÍTICAS

### 🚨 NO CUMPLE FTMO:
- **Max DD**: -17.73% > límite -10%
- **Retorno**: +0.07% (insuficiente)

### 🚨 RIESGO/RETORNO DESFAVORABLE:
- **Sharpe Ratio**: ~0 (retorno = riesgo)
- **Expectancy**: $0.36 por trade (casi nulo)

### 🚨 OVERTRADING:
- 6.6 trades/día es excesivo
- Más comisiones y slippage
- Mayor exposición al riesgo

---

## 🆚 COMPARACIÓN FINAL: GBPJPY vs US30

```
                    GBPJPY 24H      US30 NY         Ganador
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Retorno             +0.07%          +30.91%         US30 ✅
Max DD              -17.73%         -8.77%          US30 ✅
Win Rate            23.2%           29.4%           US30 ✅
Profit Factor       1.00            1.36            US30 ✅
Trades              185             197             Similar
Trades/dia          6.6             1.9             US30 ✅
Expectancy          $0.36           $157.21         US30 ✅
FTMO Compliant      NO ❌           SI ✅            US30 ✅
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**GANADOR ABSOLUTO**: US30 NY (en todas las métricas)

---

## 💡 CONCLUSIÓN FINAL

### Veredicto:
**NO USAR GBPJPY CON ESTA ESTRATEGIA**

### Razones:
1. Retorno casi nulo (+0.07% en 28 días)
2. Drawdown 2x peor que US30
3. No cumple reglas FTMO
4. Profit Factor = 1.00 (breakeven)
5. US30 es 440x más rentable

### Recomendación:
✅ **MANTENER US30 COMO ÚNICO SÍMBOLO**

Si se desea operar GBPJPY:
- Requiere optimización completa desde cero
- Diferentes parámetros (R:R, buffer, consecutive_candles)
- Filtro de sesión específico (Londres o Asia)
- Validación con más datos históricos

---

## 📁 ARCHIVOS PARA VISUALIZACIÓN

### CSV:
- `backtest_gbpjpy_24h_results.csv` - 185 trades completos
- `gbpjpy_ultimas_15_trades.csv` - Últimas 15 operaciones

### Pine Script:
- `strategies/order_block/tradingview/gbpjpy_ultimas_15.pine`

### Instrucciones TradingView:
1. Abrir GBPJPY M1
2. Cargar Pine Script
3. Navegar a 24-27 Marzo 2026
4. Visualizar zonas OB, Entry, SL, TP

---

**FECHA**: 30 Marzo 2026  
**STATUS**: ❌ GBPJPY NO RENTABLE - Mantener US30 únicamente
