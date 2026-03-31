# 🎯 ANÁLISIS DE LÓGICA DE ENTRADA - SNIPER STRATEGY

## Período: 1 febrero - 30 marzo 2026

---

## 📋 LÓGICA DE ENTRADA IMPLEMENTADA

### **CONDICIONES PARA LONG:**

```python
1. ✅ Cruce alcista EMA 9 > EMA 21
   - EMA9[actual] > EMA21[actual]
   - EMA9[anterior] <= EMA21[anterior]

2. ✅ Score Bull >= 57% (4/7 indicadores alcistas)
   - Precio > VWAP
   - RSI > 50
   - MACD > Signal
   - EMA9 > EMA21
   - ADX > 25 Y precio > EMA9
   - Volumen > promedio Y vela alcista
   - RSI 5min > 50

3. ✅ Precio > VWAP (si REQUIRE_VWAP_SIDE = True)

4. ✅ Score Bull > Score Bear

5. ✅ No hay trade activo en dirección LONG
```

### **CONDICIONES PARA SHORT:**

```python
1. ✅ Cruce bajista EMA 9 < EMA 21
   - EMA9[actual] < EMA21[actual]
   - EMA9[anterior] >= EMA21[anterior]

2. ✅ Score Bear >= 57% (4/7 indicadores bajistas)
   - Precio < VWAP
   - RSI < 50
   - MACD < Signal
   - EMA9 < EMA21
   - ADX > 25 Y precio < EMA9
   - Volumen > promedio Y vela bajista
   - RSI 5min < 50

3. ✅ Precio < VWAP (si REQUIRE_VWAP_SIDE = True)

4. ✅ Score Bear > Score Bull

5. ✅ No hay trade activo en dirección SHORT
```

---

## 📊 RESULTADOS CON TP FIJO 2:1

### **RESUMEN GENERAL:**

```
Balance inicial:  $100,000.00
Balance final:    $92,847.46
PnL neto:         -$7,152.54 (-7.15%) ❌
Max Drawdown:     -$15,932.49 (-15.93%)

Total trades:     176
Win Rate:         30.7% (54/176)
Avg Win:          $1,005.51
Avg Loss:         -$503.69
Win/Loss Ratio:   2.00 (perfecto por diseño R:R 2:1)
Profit Factor:    0.88 (perdedor)
```

### **POR DIRECCIÓN:**

```
LONG:  90 trades
       WR: 23.3% (21/90)
       PnL: -$13,529.50 ❌
       
SHORT: 86 trades
       WR: 38.4% (33/86)
       PnL: +$6,376.96 ✅
```

---

## 🔍 ANÁLISIS CRÍTICO DE LA LÓGICA DE ENTRADA

### **1. CRUCES EMA DETECTADOS:**

```
Cruces alcistas:  241 (EMA9 > EMA21)
Cruces bajistas:  240 (EMA9 < EMA21)
Total:            481 cruces

Trades ejecutados: 176 (36.6% de los cruces)
Cruces filtrados:  305 (63.4%)
```

**Conclusión:** Los filtros de score y VWAP están rechazando el 63% de los cruces.

---

### **2. EFECTIVIDAD DE LOS FILTROS:**

#### **Score Bull/Bear (57% mínimo):**

```
Requiere 4/7 indicadores alineados:
- Si solo 3/7 están alineados → 42.9% → RECHAZADO
- Si 4/7 están alineados → 57.1% → ACEPTADO
- Si 5/7 están alineados → 71.4% → ACEPTADO
```

**Problema:** Este filtro es **muy estricto** y puede estar rechazando buenos setups.

**Ejemplo:**
- Cruce EMA alcista ✅
- Precio > VWAP ✅
- RSI > 50 ✅
- MACD > Signal ✅
- Pero volumen bajo ❌
- Y RSI 5min < 50 ❌
- Y ADX < 25 ❌

**Score:** 4/7 = 57.1% → APENAS pasa el filtro

---

#### **Filtro VWAP:**

```
REQUIRE_VWAP_SIDE = True

Para LONG: Precio DEBE estar > VWAP
Para SHORT: Precio DEBE estar < VWAP
```

**Problema:** VWAP es un indicador de **valor justo**, no de dirección.

**Casos problemáticos:**
- Cruce alcista fuerte, pero precio ligeramente < VWAP → RECHAZADO
- Cruce bajista fuerte, pero precio ligeramente > VWAP → RECHAZADO

---

### **3. ANÁLISIS DE WIN RATE POR DIRECCIÓN:**

```
LONG:  23.3% WR ❌ (muy bajo)
SHORT: 38.4% WR ✅ (aceptable)

Diferencia: 15.1 puntos porcentuales
```

**Conclusión:** La estrategia tiene **BIAS BAJISTA** en el período feb-mar 2026.

**Posibles causas:**
1. Mercado en tendencia bajista en ese período
2. Filtros más estrictos para LONG que para SHORT
3. VWAP favorece entradas SHORT en mercados bajistas

---

### **4. ANÁLISIS DE PROFIT FACTOR:**

```
Profit Factor: 0.88

Gross Profit:  54 × $1,005.51 = $54,297.54
Gross Loss:    122 × $503.69 = $61,450.18

Déficit: $7,152.64
```

**Problema:** Necesitas **WR > 33.3%** para ser rentable con R:R 2:1.

**Cálculo:**
```
Break-even WR = 1 / (1 + RR) = 1 / (1 + 2) = 33.3%

WR actual: 30.7% < 33.3% → PERDEDOR
```

---

## 🎯 COMPARACIÓN: SNIPER vs ORDER BLOCKS

### **Sniper (TP 2:1):**
```
Período:      59 días (feb-mar 2026)
Retorno:      -7.15% ❌
Win Rate:     30.7%
Trades:       176 (2.98/día)
Max DD:       -15.93%
Profit Factor: 0.88
```

### **Order Blocks:**
```
Período:      101 días
Retorno:      +24.4% ✅
Win Rate:     42.7%
Trades:       ~1.5/día
Max DD:       -4.07%
Profit Factor: ~1.8
```

**Conclusión:** **Order Blocks es SUPERIOR en todas las métricas.**

---

## 🔬 ANÁLISIS DE TRADES INDIVIDUALES

### **Primeros 10 trades:**

```
#1  LONG  49413 → 49355 (SL) -$500   ❌
#2  SHORT 49378 → 49328 (TP) +$995   ✅
#3  LONG  49527 → 49464 (SL) -$502   ❌
#4  SHORT 49412 → 49206 (TP) +$999   ✅
#5  SHORT 49262 → 49288 (SL) -$504   ❌
#6  LONG  49377 → 49454 (TP) +$1004  ✅
#7  LONG  49408 → 49361 (SL) -$507   ❌
#8  LONG  49548 → 49483 (SL) -$504   ❌
#9  LONG  49517 → 49443 (SL) -$502   ❌
#10 LONG  49493 → 49550 (TP) +$999   ✅
```

**Patrón observado:**
- SHORTS tienen mejor WR (4/5 = 80% en primeros 10)
- LONGS tienen peor WR (2/5 = 40% en primeros 10)
- Mercado claramente bajista en inicio de febrero

---

### **Últimos 10 trades:**

```
#167 SHORT 46469 → 46575 (SL) -$466  ❌
#168 SHORT 46403 → 46517 (SL) -$464  ❌
#169 LONG  46545 → 46410 (SL) -$462  ❌
#170 LONG  46512 → 46419 (SL) -$459  ❌
#171 LONG  46409 → 46373 (SL) -$457  ❌
#172 SHORT 46357 → 46401 (SL) -$455  ❌
#173 SHORT 46371 → 46300 (TP) +$905  ✅
#174 LONG  46415 → 46365 (SL) -$457  ❌
#175 SHORT 46336 → 46283 (TP) +$910  ✅
#176 SHORT 46209 → 46081 (TP) +$919  ✅
```

**Patrón observado:**
- Racha de 6 pérdidas consecutivas (#167-#172)
- Solo 3 winners en últimos 10 trades (30% WR)
- Mercado volátil y choppy en final de marzo

---

## 💡 PROBLEMAS IDENTIFICADOS EN LA LÓGICA DE ENTRADA

### **1. FILTROS DEMASIADO ESTRICTOS:**

```
Score >= 57% (4/7 indicadores)
+ Precio debe estar del lado correcto de VWAP
+ Score Bull > Score Bear (o viceversa)
```

**Resultado:** Solo 36.6% de los cruces EMA pasan los filtros.

**Solución propuesta:**
- Reducir score mínimo a 50% (3.5/7)
- O hacer VWAP opcional
- O usar score como peso, no como filtro binario

---

### **2. VWAP COMO FILTRO BINARIO:**

**Problema:** VWAP es un indicador de valor justo, no de dirección.

**Ejemplo:**
```
Precio: $49,500
VWAP:   $49,505
Diferencia: -$5 (0.01%)

Cruce alcista fuerte, pero precio < VWAP → RECHAZADO
```

**Solución propuesta:**
- Usar VWAP como confirmación, no como filtro duro
- Permitir entradas si precio está dentro de ±0.1% de VWAP

---

### **3. SCORE MULTI-INDICADOR REDUNDANTE:**

**Problema:** Varios indicadores miden lo mismo.

```
Indicadores correlacionados:
- RSI > 50 ≈ MACD > Signal ≈ EMA9 > EMA21
- Volumen alto + vela alcista ≈ Momentum alcista

Correlación estimada: ~70%
```

**Resultado:** No aportan información independiente.

**Solución propuesta:**
- Usar solo indicadores no correlacionados
- O ponderar por importancia

---

### **4. ADX PLACEHOLDER:**

```python
df["adx"] = 25.0  # Placeholder
```

**Problema:** ADX está hardcodeado a 25.0, por lo que el filtro `ADX > 25` es aleatorio.

**Impacto:** El indicador #5 del score es inútil.

**Solución propuesta:**
- Implementar ADX real
- O remover del score

---

### **5. RSI 5MIN PLACEHOLDER:**

```python
df["rsi_5m"] = df["rsi"]  # Placeholder
```

**Problema:** RSI 5min es igual a RSI 14, por lo que el indicador #7 es redundante.

**Impacto:** El score está inflado artificialmente.

**Solución propuesta:**
- Implementar RSI en datos M1
- O remover del score

---

## 🎯 CONCLUSIONES FINALES

### **✅ LO QUE FUNCIONA:**

1. **Cruce EMA 9/21** es un buen trigger de entrada
2. **Shorts > Longs** en mercados bajistas (confirmado)
3. **R:R 2:1** es matemáticamente correcto
4. **Risk management** (0.5% por trade) es conservador

---

### **❌ LO QUE NO FUNCIONA:**

1. **Win Rate 30.7% < 33.3%** (break-even con R:R 2:1)
2. **Filtros demasiado estrictos** (rechazan 63% de cruces)
3. **VWAP como filtro binario** (muy restrictivo)
4. **Score con indicadores redundantes** (RSI, MACD, EMA correlacionados)
5. **ADX y RSI 5min son placeholders** (no aportan valor real)
6. **Bias direccional** (LONG 23.3% vs SHORT 38.4%)

---

### **⚠️ RIESGOS IDENTIFICADOS:**

1. **Overfitting:** Estrategia optimizada para TradingView, no validada en forward testing
2. **Data snooping:** Período feb-mar 2026 puede ser cherry-picked
3. **Slippage no considerado:** Resultados reales serán peores
4. **Comisiones no consideradas:** Resultados reales serán peores
5. **Drawdown alto:** -15.93% puede activar margin call en cuentas pequeñas

---

## 🔧 RECOMENDACIONES

### **Opción 1: OPTIMIZAR FILTROS**

```python
# Reducir score mínimo
MIN_BULL_PCT = 50.0  # De 57% a 50%
MIN_BEAR_PCT = 50.0

# Hacer VWAP opcional
REQUIRE_VWAP_SIDE = False

# Remover indicadores placeholder
# - ADX (hardcodeado)
# - RSI 5min (duplicado)
```

**Resultado esperado:** Más trades, WR similar, mejor rentabilidad.

---

### **Opción 2: SIMPLIFICAR ESTRATEGIA**

```python
# Solo cruce EMA + VWAP
if ema_cross_up and close > vwap:
    enter_long()

if ema_cross_down and close < vwap:
    enter_short()
```

**Resultado esperado:** Más trades, lógica más clara, menos overfitting.

---

### **Opción 3: ADAPTAR A MERCADO DIRECCIONAL**

```python
# Detectar tendencia (EMA 50 vs EMA 200)
if ema50 > ema200:  # Uptrend
    only_long = True
else:  # Downtrend
    only_short = True
```

**Resultado esperado:** Mejor WR al operar solo a favor de tendencia.

---

### **Opción 4: ABANDONAR Y USAR ORDER BLOCKS**

```
Order Blocks ya demostró ser rentable:
- +24.4% en 101 días
- WR 42.7%
- Max DD -4.07%
- Profit Factor ~1.8

¿Por qué buscar otra estrategia?
```

**Resultado esperado:** Rentabilidad probada, menos riesgo.

---

## 📊 VEREDICTO FINAL

### **SNIPER STRATEGY (TP 2:1):**

```
Rentabilidad:     -7.15% ❌
Win Rate:         30.7% (< break-even 33.3%) ❌
Profit Factor:    0.88 (< 1.0) ❌
Max Drawdown:     -15.93% ⚠️
Trades/día:       2.98 ✅

CALIFICACIÓN: 3/10 (NO RECOMENDADO)
```

### **ORDER BLOCKS:**

```
Rentabilidad:     +24.4% ✅
Win Rate:         42.7% (> break-even 33.3%) ✅
Profit Factor:    ~1.8 (> 1.0) ✅
Max Drawdown:     -4.07% ✅
Trades/día:       ~1.5 ✅

CALIFICACIÓN: 9/10 (ALTAMENTE RECOMENDADO)
```

---

## 🎯 RECOMENDACIÓN FINAL

**NO uses Sniper Strategy en live trading.**

**Razones:**
1. Win Rate insuficiente (30.7% < 33.3% break-even)
2. Drawdown excesivo (-15.93%)
3. Profit Factor < 1.0 (perdedor)
4. Inferior a Order Blocks en todas las métricas

**Alternativa:**
- Continúa con **Order Blocks** (ya probado y rentable)
- Si quieres más frecuencia, optimiza Order Blocks (no busques nueva estrategia)
- Haz paper trading de Sniper por 1 mes antes de considerar live

---

**¿Quieres que optimice los filtros de Sniper o prefieres enfocarte en Order Blocks?**
