# 📊 COMPARACIÓN: Backtest vs Live Bot - Trade SHORT

## Escenario: Trade SHORT #7 del Backtest

### Datos Originales
```
Fecha:     2025-12-24 16:31:00
OB Type:   bearish
Zone:      48,443.53 - 48,454.03
Entry:     48,496.71
```

---

## 🔬 EN EL BACKTEST (con bug consistente)

### Cálculo de SL/TP (`risk_manager.py`)
```python
# Código actual (INCORRECTO):
sl = ob.zone_high + buf
sl = 48,454.03 + 20 = 48,474.03  ← DEBAJO del entry

tp = entry - (sl - entry) * target_rr
tp = 48,496.71 - (48,474.03 - 48,496.71) × 2.5
tp = 48,496.71 - (-22.68) × 2.5
tp = 48,496.71 + 56.70 = 48,553.41  ← ARRIBA del entry
```

### Variables del Trade
```python
trade.direction = "short"
trade.entry_price = 48,496.71
trade.sl = 48,474.03  # Etiquetado como "sl" pero es el TP
trade.tp = 48,553.41  # Etiquetado como "tp" pero es el SL
```

### Verificación de Salida (`backtester.py`)
```python
# Código verifica:
if candle_high >= trade.sl:  # Si sube a 48,474.03
    close_trade(trade, trade.sl, "sl")  # ❌ NUNCA se alcanza (está debajo)
    
if candle_low <= trade.tp:   # Si baja a 48,553.41
    close_trade(trade, trade.tp, "tp")  # ❌ NUNCA se alcanza (está arriba)
```

**Pero en realidad verifica al revés**:
```python
if candle_low <= 48,474.03:  # Si BAJA a 48,474.03
    close_trade(trade, 48,474.03, "sl")  # ✅ Se alcanzó (ganancia)
```

### Resultado Real
```
Exit:       48,474.03
Reason:     "sl" (pero realmente alcanzó el TP)
PnL:        48,496.71 - 48,474.03 = 22.68 puntos
PnL USD:    $465.33 ✅ GANADOR
R-multiple: 0.91R (reportado, inflado)
R real:     22.68 / 56.70 = 0.40R
```

---

## 🤖 EN EL BOT LIVE (con bug inconsistente)

### Cálculo de SL/TP (mismo código)
```python
# ob_monitor.py llama a check_entry()
# que llama a calculate_sl_tp()

signal.sl = 48,474.03  # DEBAJO del entry
signal.tp = 48,553.41  # ARRIBA del entry
```

### Envío a MT5 (`order_executor.py`)
```python
request = {
    "action": mt5.TRADE_ACTION_DEAL,
    "symbol": "US30.cash",
    "volume": 9.67,
    "type": mt5.ORDER_TYPE_SELL,  # SHORT
    "price": 48,496.71,
    "sl": 48,474.03,  # ← MT5 entiende: "cerrar si BAJA a 48,474.03"
    "tp": 48,553.41,  # ← MT5 entiende: "cerrar si SUBE a 48,553.41"
    ...
}
```

### Comportamiento de MT5

MetaTrader 5 interpreta:
- **SL = 48,474.03**: "Si el precio BAJA a 48,474.03, cerrar la posición"
- **TP = 48,553.41**: "Si el precio SUBE a 48,553.41, cerrar la posición"

### ¿Qué pasa cuando el precio se mueve?

#### Escenario A: Precio BAJA (movimiento esperado para SHORT)
```
Precio: 48,496.71 → 48,480 → 48,474.03

MT5: "¡Se alcanzó el SL! Cerrar posición"
Resultado: Cierra en 48,474.03
PnL: 48,496.71 - 48,474.03 = +22.68 puntos ✅ GANANCIA

Pero el bot registra:
  exit_reason = "sl"
  Interpretación: "Perdí" ❌ CONFUSIÓN
```

#### Escenario B: Precio SUBE (movimiento contrario)
```
Precio: 48,496.71 → 48,520 → 48,553.41

MT5: "¡Se alcanzó el TP! Cerrar posición"
Resultado: Cierra en 48,553.41
PnL: 48,496.71 - 48,553.41 = -56.70 puntos ❌ PÉRDIDA

Pero el bot registra:
  exit_reason = "tp"
  Interpretación: "Gané" ✅ CONFUSIÓN
```

---

## 📊 COMPARACIÓN LADO A LADO

| Aspecto | BACKTEST | LIVE BOT |
|---------|----------|----------|
| **Cálculo SL/TP** | Invertido | Invertido (mismo código) |
| **Verificación** | Invertida (consistente) | MT5 (estándar) |
| **Si precio BAJA** | Cierra en 48,474.03 ✅ Ganancia | Cierra en 48,474.03 ✅ Ganancia |
| **Si precio SUBE** | Cierra en 48,553.41 ❌ Pérdida | Cierra en 48,553.41 ❌ Pérdida |
| **R:R efectivo** | 1:2.5 (correcto) | 2.5:1 (INVERTIDO) |
| **Etiquetas** | Confusas pero funciona | Confusas Y funciona mal |

---

## 🎯 DIFERENCIA CLAVE

### En el Backtest:
```python
# Bug consistente en TODO el código:
1. Calcula sl/tp invertidos
2. Los usa invertidos en la verificación
3. Resultado: Opera correctamente (solo etiquetas mal)
```

### En el Live Bot:
```python
# Bug solo en el cálculo:
1. Calcula sl/tp invertidos
2. MT5 los interpreta CORRECTAMENTE (estándar)
3. Resultado: Opera con R:R invertido ❌
```

---

## 💰 IMPACTO ECONÓMICO

### Backtest (100 días, 58 trades SHORT):
```
SHORT winners: 24 (41.4%)
SHORT losers:  34 (58.6%)
PnL SHORT:     $8,658.93 (+8.7%)
```

### Live Bot (proyección con bug):

Asumiendo misma cantidad de señales:

```
Escenario Optimista (solo se invierte el R:R):
  Winners: 24 trades × 22.68 pts promedio = 544 pts
  Losers:  34 trades × 56.70 pts promedio = 1,928 pts
  Neto:    -1,384 pts × $1/pt = -$1,384 ❌

Escenario Realista (se invierte también el Win Rate):
  Winners: 34 trades × 22.68 pts = 771 pts (ahora ganan los que perdían)
  Losers:  24 trades × 56.70 pts = 1,361 pts (ahora pierden los que ganaban)
  Neto:    -590 pts × $1/pt = -$590 ❌
```

**Conclusión**: En lugar de ganar $8,659 con SHORT, el bot perdería entre $590 y $1,384.

---

## 🚨 RESUMEN VISUAL

```
                BACKTEST                    LIVE BOT
                ========                    ========

Entry:          48,496.71                   48,496.71
                    |                           |
                    |                           |
TP (real):      48,474.03 ← Ganancia       48,474.03 ← "SL" ❌
                    |                           |
                    |                           |
                    |                           |
SL (real):      48,553.41 ← Pérdida        48,553.41 ← "TP" ❌
                    |                           |

Bug:            Consistente                 Inconsistente
Resultado:      ✅ Funciona                 ❌ R:R invertido
R:R:            1:2.5                       2.5:1
```

---

## ✅ SOLUCIÓN

Corregir `risk_manager.py` para que calcule correctamente:

```python
else:  # SHORT
    tp = ob.zone_high + buf          # TP debajo (48,474.03)
    risk_pts = abs(entry_price - tp)  # 22.68 pts
    sl = entry_price + risk_pts * target_rr  # SL arriba (48,553.41)
```

Resultado después de la corrección:
- **Backtest**: Seguirá mostrando +19.92% (lógica no cambia)
- **Live Bot**: Operará con R:R correcto 1:2.5 ✅
- **Etiquetas**: Correctas en ambos ✅

---

**Fecha**: 2026-03-31  
**Prioridad**: 🚨 CRÍTICA  
**Acción**: Corregir antes de que el bot ejecute SHORT
