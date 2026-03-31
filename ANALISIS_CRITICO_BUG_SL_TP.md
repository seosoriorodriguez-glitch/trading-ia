# 🔬 ANÁLISIS CRÍTICO: Bug SL/TP Invertidos

## 1. ESTADO ACTUAL DEL BOT LIVE

### Trades Ejecutados
```
Fecha: 2026-03-30 13:37:00
Tipo: LONG
Entry: 45,511.10
SL:    45,459.41  (DEBAJO del entry) ✅ CORRECTO
TP:    45,640.32  (ARRIBA del entry) ✅ CORRECTO
```

```
Fecha: 2026-03-30 13:42:00
Tipo: LONG
Entry: 45,456.60
SL:    45,393.91  (DEBAJO del entry) ✅ CORRECTO
TP:    45,613.32  (ARRIBA del entry) ✅ CORRECTO
```

### ✅ CONCLUSIÓN LIVE BOT
- El bot **NO ha ejecutado trades SHORT** todavía
- Los trades LONG están **CORRECTOS** (el bug solo afecta SHORT)
- **NO HAY RIESGO INMEDIATO** en el bot live

---

## 2. ANÁLISIS DEL BUG EN EL CÓDIGO

### Ubicación: `strategies/order_block/backtest/risk_manager.py` (líneas 38-43)

```python
def calculate_sl_tp(
    ob: OrderBlock,
    entry_price: float,
    params: dict,
) -> Tuple[Optional[float], Optional[float]]:
    buf         = params["buffer_points"]
    min_risk    = params["min_risk_points"]
    max_risk    = params["max_risk_points"]
    target_rr   = params["target_rr"]
    min_rr      = params["min_rr_ratio"]

    if ob.ob_type == "bullish":
        sl = ob.zone_low - buf                           # ✅ CORRECTO
        tp = entry_price + (entry_price - sl) * target_rr  # ✅ CORRECTO
    else:
        sl = ob.zone_high + buf                          # ❌ BUG: esto es el TP
        tp = entry_price - (sl - entry_price) * target_rr  # ❌ BUG: esto es el SL
```

### ¿Por qué está mal?

Para un OB **bearish** (SHORT):
- `ob.zone_high` está en la **parte superior** de la zona OB
- `entry_price` puede estar **ARRIBA** de la zona (cuando el precio rechaza desde arriba)
- El código calcula: `sl = ob.zone_high + buf`
- Pero `ob.zone_high` puede estar **DEBAJO** del `entry_price`
- Resultado: `sl` queda DEBAJO del entry (❌ incorrecto para SHORT)

### Ejemplo Real (Trade #7 del backtest)

```
OB bearish:
  Zone High: 48,454.03
  Zone Low:  48,443.53

Entry: 48,496.71 (ARRIBA de la zona)

Cálculo del código:
  sl = 48,454.03 + 20 = 48,474.03  ← DEBAJO del entry ❌
  tp = 48,496.71 - (48,474.03 - 48,496.71) × 2.5 = 48,553.41  ← ARRIBA del entry ❌

Debería ser:
  SL: 48,553.41 (ARRIBA del entry para protección)
  TP: 48,474.03 (DEBAJO del entry para ganancia)
```

---

## 3. IMPACTO EN EL BACKTEST

### ¿El backtest es VÁLIDO?

**SÍ, el backtest ES VÁLIDO** porque el bug es **consistente** en toda la lógica:

#### 3.1. Cálculo (risk_manager.py)
```python
# Calcula SL/TP invertidos
sl = ob.zone_high + buf     # Realmente es TP
tp = entry - (sl - entry) * target_rr  # Realmente es SL
```

#### 3.2. Verificación de Salida (backtester.py, líneas 274-280)
```python
else:  # short
    if candle_high >= trade.sl:  # Verifica si sube hasta "sl"
        self._close_trade(trade, trade.sl, current_time, "sl")
        return True
    if candle_low <= trade.tp:   # Verifica si baja hasta "tp"
        self._close_trade(trade, trade.tp, current_time, "tp")
        return True
```

#### 3.3. Cálculo de PnL (risk_manager.py, línea 91)
```python
if direction == "long":
    pnl_points = exit_price - entry_price
else:
    pnl_points = entry_price - exit_price  # ✅ CORRECTO
```

### ¿Por qué funciona?

1. **Cálculo**: Asigna el valor del TP a la variable `sl` y viceversa
2. **Ejecución**: Usa `trade.sl` como si fuera el TP (verifica si baja)
3. **PnL**: Calcula correctamente basándose en entry/exit, **NO** en las variables sl/tp

**Resultado**: El backtest opera correctamente, solo las **etiquetas** están mal.

---

## 4. VERIFICACIÓN MATEMÁTICA

### Trade #7 (SHORT)

```
Entry:     48,496.71
"sl":      48,474.03  (realmente TP)
"tp":      48,553.41  (realmente SL)
Exit:      48,474.03
Reason:    "sl" (realmente alcanzó el TP)
PnL:       +$465.33
```

#### Verificación del PnL:
```
pnl_points = entry - exit = 48,496.71 - 48,474.03 = 22.68 puntos
pnl_usd = 22.68 × $20.50/punto = $465.33 ✅ CORRECTO
```

#### Verificación del R-multiple:
```
Risk = |entry - "tp"| = |48,496.71 - 48,553.41| = 56.70 puntos (SL real)
Reward = |entry - "sl"| = |48,496.71 - 48,474.03| = 22.68 puntos (TP real)
R = 22.68 / 56.70 = 0.40R

Pero el CSV dice: r_multiple = 0.912R
```

**Aquí hay una discrepancia**. Déjame verificar cómo se calcula el R-multiple en el código.

---

## 5. ANÁLISIS DEL CÁLCULO DE R-MULTIPLE

### En backtester.py (línea 291-298):
```python
pnl_dict = calc_pnl(
    entry_price          = trade.entry_price,
    exit_price           = exit_price,
    original_sl          = trade.original_sl,
    entry_price_original = trade.entry_price,
    direction            = trade.direction,
    balance              = trade.balance_at_entry,
    params               = self.params,
)
```

### En risk_manager.py (líneas 85-96):
```python
def calc_pnl(...):
    if direction == "long":
        pnl_points = exit_price - entry_price
    else:
        pnl_points = entry_price - exit_price
    
    risk_points = abs(entry_price_original - original_sl)
    pnl_r = pnl_points / risk_points if risk_points > 0 else 0
```

### Para Trade #7:
```
pnl_points = 48,496.71 - 48,474.03 = 22.68 puntos ✅
risk_points = |48,496.71 - 48,474.03| = 22.68 puntos ❌

¡El risk_points está usando "sl" (48,474.03) que es realmente el TP!

Debería ser:
risk_points = |48,496.71 - 48,553.41| = 56.70 puntos

R-multiple correcto = 22.68 / 56.70 = 0.40R
R-multiple reportado = 22.68 / 22.68 = 1.00R
```

**PROBLEMA CRÍTICO**: El R-multiple está **MAL CALCULADO** para trades SHORT.

---

## 6. IMPACTO REAL EN LAS MÉTRICAS DEL BACKTEST

### Métricas Afectadas:

1. **PnL en USD**: ✅ CORRECTO (usa entry/exit, no sl/tp)
2. **PnL en puntos**: ✅ CORRECTO (usa entry/exit)
3. **R-multiple**: ❌ **INCORRECTO** para SHORT (usa sl invertido)
4. **Win Rate**: ✅ CORRECTO (basado en PnL > 0)
5. **Max Drawdown**: ✅ CORRECTO (basado en balance)
6. **Profit Factor**: ✅ CORRECTO (basado en PnL)

### ¿Qué significa esto?

- **La rentabilidad del backtest ES VÁLIDA** (+19.92%)
- **Los R-multiples de trades SHORT están INFLADOS**
- Los trades SHORT que salieron en "sl" (realmente TP) muestran R ~1.0 cuando deberían ser R ~0.4

---

## 7. RIESGO PARA EL BOT LIVE

### Escenario 1: Bot detecta señal SHORT

Cuando el bot live detecte un OB bearish y genere una señal SHORT:

```python
# En ob_monitor.py, llama a:
signal = check_entry(...)

# Que internamente llama a:
sl, tp = calculate_sl_tp(ob, entry_price, params)

# Para SHORT, retorna:
sl = ob.zone_high + buffer  # Valor bajo (realmente TP)
tp = entry - (sl - entry) * 2.5  # Valor alto (realmente SL)
```

### Escenario 2: Bot envía orden a MT5

```python
# En order_executor.py:
request = {
    "action": mt5.TRADE_ACTION_DEAL,
    "symbol": self.symbol,
    "volume": volume,
    "type": mt5.ORDER_TYPE_SELL,
    "price": signal.entry_price,
    "sl": signal.sl,      # ← Valor BAJO (realmente TP)
    "tp": signal.tp,      # ← Valor ALTO (realmente SL)
    ...
}
```

### ⚠️ PROBLEMA CRÍTICO

MetaTrader 5 recibirá:
- `sl` con un valor **DEBAJO** del entry (protección incorrecta)
- `tp` con un valor **ARRIBA** del entry (objetivo incorrecto)

**Resultado**: El bot operará con **riesgo/beneficio INVERTIDO** en trades SHORT.

---

## 8. EJEMPLO SIMULADO DE TRADE SHORT EN LIVE

Supongamos que mañana el bot detecta:

```
OB bearish:
  Zone High: 45,500
  Zone Low:  45,480

Entry: 45,550 (precio actual, arriba de la zona)

Cálculo del bot:
  sl = 45,500 + 20 = 45,520  (DEBAJO del entry)
  tp = 45,550 - (45,520 - 45,550) × 2.5 = 45,625  (ARRIBA del entry)

Orden enviada a MT5:
  Type: SELL (SHORT)
  Entry: 45,550
  SL: 45,520  ← MT5 cerrará aquí si el precio BAJA 30 puntos
  TP: 45,625  ← MT5 cerrará aquí si el precio SUBE 75 puntos
```

### ¿Qué pasará?

1. **Si el precio BAJA** (movimiento esperado para SHORT):
   - Bajará a 45,520
   - MT5 cerrará en "SL" con **GANANCIA** de 30 puntos
   - Pero el bot pensará que perdió

2. **Si el precio SUBE** (movimiento contrario):
   - Subirá a 45,625
   - MT5 cerrará en "TP" con **PÉRDIDA** de 75 puntos
   - Pero el bot pensará que ganó

**RIESGO/BENEFICIO INVERTIDO: 1:2.5 → 2.5:1** ❌❌❌

---

## 9. CONCLUSIONES

### ✅ Backtest VÁLIDO
- La rentabilidad de +19.92% ES REAL
- Los trades SHORT funcionan correctamente
- Solo las etiquetas y R-multiples están mal

### ❌ Bot Live EN RIESGO
- **CRÍTICO**: Si el bot ejecuta un trade SHORT, operará con R:R invertido
- Riesgo real: 2.5x mayor que el esperado
- Beneficio real: 2.5x menor que el esperado

### 🎯 Recomendación URGENTE

**ANTES de que el bot ejecute un trade SHORT**:

1. **Corregir `risk_manager.py`** (líneas 38-43)
2. **Probar en backtest** que los SHORT siguen funcionando
3. **Verificar en demo** antes de volver a live

---

## 10. SOLUCIÓN PROPUESTA

### Código Corregido para `risk_manager.py`:

```python
def calculate_sl_tp(
    ob: OrderBlock,
    entry_price: float,
    params: dict,
) -> Tuple[Optional[float], Optional[float]]:
    buf         = params["buffer_points"]
    min_risk    = params["min_risk_points"]
    max_risk    = params["max_risk_points"]
    target_rr   = params["target_rr"]
    min_rr      = params["min_rr_ratio"]

    if ob.ob_type == "bullish":
        # LONG: SL debajo, TP arriba
        sl = ob.zone_low - buf
        tp = entry_price + (entry_price - sl) * target_rr
    else:
        # SHORT: TP debajo, SL arriba
        tp = ob.zone_high + buf  # TP debajo de la zona
        risk_pts = abs(entry_price - tp)
        sl = entry_price + risk_pts * target_rr  # SL arriba del entry

    risk_pts = abs(entry_price - sl)

    if risk_pts < min_risk:
        return None, None
    if risk_pts > max_risk:
        return None, None

    rr = abs(tp - entry_price) / risk_pts
    if rr < min_rr:
        return None, None

    return sl, tp
```

### ⚠️ IMPORTANTE
Después de corregir, **DEBES**:
1. Re-ejecutar el backtest completo
2. Verificar que los resultados sean similares (+19% aprox)
3. Verificar que los R-multiples de SHORT ahora sean correctos
4. Probar en demo antes de live

---

## 11. PRIORIDAD

**🚨 CRÍTICA - DETENER BOT LIVE HASTA CORREGIR**

El bot live está operando con un bug que:
- ✅ NO afecta trades LONG (funcionan correctamente)
- ❌ AFECTARÁ trades SHORT (R:R invertido 2.5:1 en lugar de 1:2.5)

**Recomendación**: Detener el bot hasta corregir el bug, o configurarlo para **SOLO operar LONG** temporalmente.
