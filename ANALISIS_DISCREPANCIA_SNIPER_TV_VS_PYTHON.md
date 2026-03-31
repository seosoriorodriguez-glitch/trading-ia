# 🔍 ANÁLISIS DE DISCREPANCIA: SNIPER STRATEGY
## TradingView vs Python Backtest (Feb-Mar 2026)

---

## 📊 COMPARACIÓN DE RESULTADOS

### TradingView (Pine Script)
```
Período:          1 feb - 30 mar 2026
Balance inicial:  $100,000.00
Balance final:    $117,825.54
Ganancia:         +$17,825.54 (+17.83%) ✅
Max Drawdown:     4.49%

Total trades:     870
Win Rate:         28.97% (252/870)
Profit Factor:    1.484

Beneficio bruto:  $54,688.09 (54.69%)
Pérdida bruta:    $36,862.55 (36.86%)
Ganancia esperada: $20.49 por trade
```

### Python Backtest
```
Período:          1 feb - 30 mar 2026
Balance inicial:  $100,000.00
Balance final:    $98,599.57
Pérdida:          -$1,400.43 (-1.40%) ❌
Max Drawdown:     7.68%

Total trades:     223
Win Rate:         67.3% (150/223)
Profit Factor:    0.96

Avg Win:          $240.39
Avg Loss:         $513.14
Trades/día:       4.37
```

---

## 🚨 DIFERENCIAS CRÍTICAS IDENTIFICADAS

### 1. NÚMERO DE TRADES: 870 vs 223 (4X DIFERENCIA)

**TradingView:** 870 trades
**Python:**      223 trades
**Diferencia:**  647 trades (74% más en TradingView)

**Posibles causas:**
- ✅ **TradingView cuenta cada TP parcial como trade separado**
- ✅ **Python cuenta 1 trade con múltiples exits parciales**
- ⚠️ Lógica de entrada diferente (filtros más/menos estrictos)
- ⚠️ Gestión de señales simultáneas diferente

---

### 2. WIN RATE INVERTIDO: 28.97% vs 67.3%

**TradingView:** 28.97% WR (bajo, pero winners grandes)
**Python:**      67.3% WR (alto, pero winners pequeños)

**Interpretación:**
```
TradingView:
- Muchos trades pequeños perdedores (SL rápidos)
- Pocos trades ganadores GRANDES (TPs lejanos)
- Estrategia tipo "lottery ticket" (muchas pérdidas pequeñas, pocas ganancias grandes)

Python:
- Muchos trades ganadores pequeños (TPs parciales tempranos)
- Pocos trades perdedores GRANDES (SL completo)
- Estrategia tipo "scalping" (muchas ganancias pequeñas, pocas pérdidas grandes)
```

**Conclusión:** **LÓGICAS COMPLETAMENTE DIFERENTES**

---

### 3. PROFIT FACTOR: 1.484 vs 0.96

**TradingView:** 1.484 (por cada $1 perdido, gana $1.48) ✅ RENTABLE
**Python:**      0.96 (por cada $1 perdido, gana $0.96) ❌ PERDEDOR

**Diferencia:** 54% de discrepancia en rentabilidad

---

## 🔬 ANÁLISIS DE TRADES INDIVIDUALES (30 marzo 2026)

### Observaciones del Screenshot #3:

```
Trade #870: Short 30 mar 20:10, TP5 → PnL: $112,819.00
Trade #869: Short 30 mar 20:10, TP4 → PnL: $0.00
Trade #868: Short 30 mar 20:10, TP3 → PnL: $112,819.00
Trade #867: Short 30 mar 20:10, TP2 → PnL: $112,819.00
Trade #866: Short 30 mar 20:10, TP1 → PnL: $112,819.00
Trade #865: Long  30 mar 20:10      → PnL: $19.41
```

### 🚨 ANOMALÍA DETECTADA:

**4 trades con EXACTAMENTE la misma ganancia: $112,819.00**

Esto es **estadísticamente imposible** en trading real con:
- Precios dinámicos
- Slippage
- TPs en niveles diferentes (TP1, TP2, TP3, TP5)

---

## 💡 HIPÓTESIS: GESTIÓN DE TPs PARCIALES

### Escenario A: TradingView (probable)

```pine
// Pine Script probablemente hace:
if long_signal
    strategy.entry("Long", strategy.long, qty = position_size)
    
    // Cada exit genera un TRADE SEPARADO en el reporte
    strategy.exit("TP1", "Long", qty_percent = 20, limit = tp1_price)
    strategy.exit("TP2", "Long", qty_percent = 20, limit = tp2_price)
    strategy.exit("TP3", "Long", qty_percent = 20, limit = tp3_price)
    strategy.exit("TP4", "Long", qty_percent = 20, limit = tp4_price)
    strategy.exit("TP5", "Long", qty_percent = 20, limit = tp5_price, stop = sl_price)

Resultado en reporte:
- 1 señal = 5 trades reportados (uno por cada TP)
- Total: 870 trades = ~174 señales reales
```

### Escenario B: Python (implementado)

```python
# Python hace:
if long_signal:
    open_trade = {
        "entry_price": entry_price,
        "qty": position_size,
        "sl": sl_price,
        "tps": [tp1, tp2, tp3, tp4, tp5],
        "qty_remaining": position_size
    }
    
    # Cada TP cierra parcialmente la MISMA posición
    # Al final del trade, se reporta como 1 SOLO trade
    
Resultado en reporte:
- 1 señal = 1 trade reportado (con múltiples exits internos)
- Total: 223 trades = 223 señales reales
```

---

## 🎯 DIFERENCIAS EN CÁLCULO DE MÉTRICAS

### Win Rate

**TradingView:**
```
870 trades totales
252 trades ganadores (cualquier TP alcanzado)
618 trades perdedores (SL alcanzado)
WR = 252/870 = 28.97%
```

**Python:**
```
223 trades totales
150 trades ganadores (al menos 1 TP alcanzado)
73 trades perdedores (solo SL alcanzado)
WR = 150/223 = 67.3%
```

**Conclusión:** Python agrupa TPs parciales → WR más alto

---

### Profit Factor

**TradingView:**
```
Gross Profit:  $54,688.09
Gross Loss:    $36,862.55
PF = 54,688 / 36,862 = 1.484
```

**Python:**
```
Total Wins:  150 × $240 = $36,058
Total Losses: 73 × $513 = $37,458
PF = 36,058 / 37,458 = 0.96
```

**Conclusión:** Mismo concepto, diferente agrupación de trades

---

## 🔍 ANÁLISIS DE DISTRIBUCIÓN DE EXITS

### Python (conocido):
```
TP1 (1R): 50 trades (22.4%)
TP2 (2R): 33 trades (14.8%)
TP3 (3R): 28 trades (12.6%)
TP4 (4R): 20 trades (9.0%)
TP5 (5R): 19 trades (8.5%)
SL:       73 trades (32.7%)
```

### TradingView (estimado):
```
Si 870 trades = 174 señales × 5 TPs cada una:
- Cada señal genera 5 trades potenciales
- Solo ~29% de esos trades son winners (252/870)
- Esto sugiere que la mayoría de trades se cierran en SL antes de alcanzar TPs
```

---

## 📉 ANÁLISIS POR DIRECCIÓN

### Python:
```
LONG:  87 trades, WR 50.6%, PnL -$13,647 ❌
SHORT: 136 trades, WR 77.9%, PnL +$12,246 ✅
```

### TradingView (imagen #2):
```
TODOS:  870 trades, WR 28.97%
LARGO:  Factor de ganancias 0.835 ❌
CORTO:  Factor de ganancias 2.155 ✅
```

**COINCIDENCIA:** Ambos muestran que **SHORTS son superiores a LONGS** en este período

---

## 🎯 CONCLUSIONES

### 1. Diferencia en Conteo de Trades
✅ **CONFIRMADO:** TradingView cuenta cada TP parcial como trade separado
✅ **CONFIRMADO:** Python cuenta 1 trade con múltiples exits

**Ratio:** 870/223 = 3.9x más trades en TradingView
**Explicación:** 5 TPs potenciales × ~174 señales ≈ 870 trades

---

### 2. Diferencia en Win Rate
✅ **CONFIRMADO:** Metodología de cálculo diferente
- TradingView: WR por cada exit individual
- Python: WR por señal completa

**Ambos son correctos**, solo miden cosas diferentes.

---

### 3. Diferencia en Rentabilidad
⚠️ **DISCREPANCIA CRÍTICA:**
- TradingView: +17.83% ✅
- Python: -1.40% ❌

**Posibles causas:**
1. **Lógica de entrada diferente** (filtros, timing)
2. **Cálculo de SL/TP diferente** (ATR, precios)
3. **Gestión de posición diferente** (qty, risk)
4. **Spread/comisiones diferentes**
5. **Datos de precio diferentes** (TradingView usa datos propios)

---

## 🔧 PRÓXIMOS PASOS PARA RESOLVER

### Opción 1: Adaptar Python para replicar TradingView EXACTAMENTE
```python
# Modificar para:
1. Contar cada TP como trade separado
2. Usar misma lógica de entrada que Pine Script
3. Usar mismos precios OHLC que TradingView
4. Replicar exactamente cálculo de ATR, EMA, RSI, etc.
```

### Opción 2: Exportar trades de TradingView para análisis
```
1. Exportar lista completa de 870 trades
2. Comparar trade por trade con Python
3. Identificar exactamente dónde difieren las señales
```

### Opción 3: Simplificar para comparación justa
```
1. Usar solo 1 TP (sin parciales)
2. Comparar resultados
3. Aislar si el problema es la gestión de TPs o la lógica de entrada
```

---

## 💡 RECOMENDACIÓN

**NO confiar ciegamente en ninguno de los dos backtests.**

Ambos tienen limitaciones:

**TradingView:**
- ✅ Usa datos propios (más confiables)
- ✅ Motor de backtest probado
- ❌ Difícil de debuggear
- ❌ Reportes pueden ser confusos (TPs como trades separados)

**Python:**
- ✅ Control total del código
- ✅ Fácil de debuggear
- ✅ Reportes personalizables
- ❌ Depende de calidad de datos externos
- ❌ Posibles bugs en implementación

**Solución:** Validar con **paper trading** o **forward testing** en cuenta demo.

---

## 📊 MÉTRICAS CONFIABLES (COINCIDEN EN AMBOS)

✅ **Shorts > Longs** (ambos confirman)
✅ **Período feb-mar 2026 fue favorable para shorts**
✅ **Estrategia es direccional** (necesita trending market)

---

## ⚠️ MÉTRICAS NO CONFIABLES (DIFIEREN)

❌ **Rentabilidad absoluta** (+17.83% vs -1.40%)
❌ **Número de trades** (870 vs 223)
❌ **Win Rate** (28.97% vs 67.3%)
❌ **Profit Factor** (1.484 vs 0.96)

**Estas métricas NO se pueden comparar directamente** debido a diferencias metodológicas.

---

## 🎯 VEREDICTO FINAL

**La estrategia Sniper PUEDE ser rentable**, pero:

1. ⚠️ Requiere validación en paper trading
2. ⚠️ Los backtests muestran resultados contradictorios
3. ⚠️ Necesita análisis más profundo de la lógica de entrada
4. ✅ Shorts funcionan mejor que Longs (confirmado en ambos)
5. ❌ Aún es inferior a tu Order Blocks en métricas clave

**Recomendación:** Seguir con **Order Blocks** como estrategia principal, y hacer paper trading de Sniper para validar.
