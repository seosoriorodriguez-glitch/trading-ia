# 🚨 PROBLEMA CRÍTICO DETECTADO: FILTRO DE SESIONES NO SE RESPETA

## Fecha: 30 marzo 2026

---

## 📊 HALLAZGO

Al analizar las 15 operaciones ganadoras más recientes del archivo `winning_trades.pine`, se descubrió que:

**8 de 15 operaciones (53.3%) están FUERA de la sesión configurada (13:30-19:30 UTC)**

---

## 🔍 EVIDENCIA

### Operaciones FUERA de sesión (13:30-19:30 UTC):

| # | Entrada UTC | Entrada Santiago | Sesión Real |
|---|---|---|---|
| #92 | 2026-03-24 10:56 | 07:56 | **LONDRES** 🇬🇧 |
| #90 | 2026-03-23 12:42 | 09:42 | **LONDRES** 🇬🇧 |
| #84 | 2026-03-19 10:45 | 07:45 | **LONDRES** 🇬🇧 |
| #82 | 2026-03-16 12:54 | 09:54 | **LONDRES** 🇬🇧 |
| #65 | 2026-02-25 11:31 | 08:31 | **LONDRES** 🇬🇧 |
| #59 | 2026-02-17 12:52 | 09:52 | **LONDRES** 🇬🇧 |
| #58 | 2026-02-17 12:51 | 09:51 | **LONDRES** 🇬🇧 |
| #57 | 2026-02-16 10:45 | 07:45 | **LONDRES** 🇬🇧 |

**Todas estas operaciones ocurrieron en horario de Londres (08:00-13:30 UTC)**

### Operaciones DENTRO de sesión (13:30-19:30 UTC):

| # | Entrada UTC | Entrada Santiago | Sesión Real |
|---|---|---|---|
| #87 | 2026-03-20 14:06 | 11:06 | **NY** 🇺🇸 |
| #79 | 2026-03-11 15:04 | 12:04 | **NY** 🇺🇸 |
| #78 | 2026-03-09 15:35 | 12:35 | **NY** 🇺🇸 |
| #75 | 2026-03-05 15:41 | 12:41 | **NY** 🇺🇸 |
| #70 | 2026-02-27 15:17 | 12:17 | **NY** 🇺🇸 |
| #67 | 2026-02-25 15:18 | 12:18 | **NY** 🇺🇸 |
| #66 | 2026-02-25 13:40 | 10:40 | **NY** 🇺🇸 |

---

## 🔎 ANÁLISIS DE CONFIGURACIONES

### 1. **Bot Live** (`strategies/order_block/backtest/config.py`):

```python
"sessions": {
    "new_york": {"start": "13:30", "end": "20:00", "skip_minutes": 15},
}
```

**Solo opera NY:** 13:30-20:00 UTC (10:30-17:00 Santiago)

---

### 2. **TradingView** (`strategies/order_block/tradingview/ob_strategy.pine`):

```pine
ny_session = input.session("1330-1930", "Sesion NY (hora broker)")
in_session = not na(time(timeframe.period, ny_session, "UTC"))
```

**Solo opera NY:** 13:30-19:30 UTC (10:30-16:30 Santiago)

---

### 3. **Archivo `winning_trades.pine`**:

**Contiene operaciones de AMBAS sesiones:**
- Londres: 08:00-13:30 UTC (8 trades)
- NY: 13:30-19:30 UTC (7 trades)

---

## 🚨 CONCLUSIONES

### **PROBLEMA 1: Archivo `winning_trades.pine` NO corresponde a la configuración actual**

El archivo `winning_trades.pine` fue generado con una configuración que incluía **AMBAS sesiones** (Londres + NY), pero:

1. El bot live actual **solo opera NY**
2. El script de TradingView actual **solo opera NY**
3. No hay evidencia en el código actual de que Londres esté configurada

**Esto significa que el archivo `winning_trades.pine` es OBSOLETO o fue generado con una configuración diferente.**

---

### **PROBLEMA 2: El backtest "rentable" (+24.4%) probablemente incluía Londres**

Si 53% de las operaciones ganadoras son de Londres, y el backtest actual solo opera NY, entonces:

**El backtest rentable original (+24.4% en 101 días) probablemente operaba AMBAS sesiones.**

Al remover Londres, el bot live está perdiendo:
- 53% de las operaciones ganadoras
- Potencialmente la mitad de la rentabilidad

---

### **PROBLEMA 3: Inconsistencia histórica**

En el comentario del `config.py` dice:

```python
# Solo NY: backtest 99d muestra WR 42.4%, DD diario max 2.12%, retorno +27.1%
# Londres descartada: WR insuficiente y añade ruido
```

Pero las operaciones ganadoras del archivo `winning_trades.pine` muestran que:
- **Londres tiene operaciones rentables** (8 trades ganadores)
- **Londres NO fue descartada** en el backtest que generó ese archivo

---

## 🔧 HIPÓTESIS

### **Escenario más probable:**

1. **Backtest original** (el que generó `winning_trades.pine`):
   - Operaba **AMBAS sesiones** (Londres + NY)
   - Resultado: +24.4% en 101 días
   - WR: 42.7%
   - 8 trades de Londres + 7 trades de NY

2. **Backtest posterior** (mencionado en comentarios):
   - Solo NY: +27.1% en 99 días
   - Londres descartada por "WR insuficiente"
   - **PERO** este backtest NO generó el archivo `winning_trades.pine`

3. **Situación actual:**
   - Bot live opera solo NY (según config actual)
   - Archivo `winning_trades.pine` es de un backtest anterior con ambas sesiones
   - **Inconsistencia entre documentación y evidencia**

---

## 📊 IMPACTO EN RENTABILIDAD

Si Londres aporta 53% de las operaciones ganadoras:

```
Backtest original (Londres + NY):
- 15 trades ganadores
- 8 de Londres (53%)
- 7 de NY (47%)

Si removemos Londres:
- Solo 7 trades ganadores de NY
- Pérdida de 8 trades ganadores (53%)
- Rentabilidad reducida a la mitad (estimado)
```

**Esto explica por qué el bot live puede tener menor rentabilidad que el backtest.**

---

## ✅ RECOMENDACIONES

### **Opción 1: VALIDAR BACKTEST CON AMBAS SESIONES**

Ejecutar un nuevo backtest con:
```python
"sessions": {
    "london": {"start": "08:00", "end": "13:30", "skip_minutes": 15},
    "new_york": {"start": "13:30", "end": "20:00", "skip_minutes": 15},
}
```

**Objetivo:** Confirmar si el backtest rentable original operaba ambas sesiones.

---

### **Opción 2: REGENERAR `winning_trades.pine` SOLO CON NY**

Ejecutar backtest solo con NY y generar un nuevo archivo `winning_trades.pine` que corresponda a la configuración actual.

**Objetivo:** Tener documentación consistente con la configuración live.

---

### **Opción 3: ACTIVAR LONDRES EN BOT LIVE**

Si el backtest con ambas sesiones es rentable, actualizar el bot live para operar Londres + NY.

**Objetivo:** Maximizar rentabilidad operando ambas sesiones.

---

## 🎯 ACCIÓN INMEDIATA REQUERIDA

1. ✅ **Ejecutar backtest con ambas sesiones** (Londres + NY)
2. ✅ **Comparar resultados** con backtest solo NY
3. ✅ **Decidir configuración óptima** basada en datos
4. ✅ **Actualizar bot live** con la configuración óptima
5. ✅ **Regenerar `winning_trades.pine`** con configuración correcta

---

## 📝 NOTAS ADICIONALES

### **Código del backtester soporta Londres:**

```python
# strategies/order_block/backtest/run_backtest.py (línea 93-96)
if args.session == "london":
    params["sessions"] = {"london": params["sessions"]["london"]}
elif args.session == "new_york":
    params["sessions"] = {"new_york": params["sessions"]["new_york"]}
```

**El código está preparado para operar Londres, pero la configuración actual no la incluye.**

---

### **Sesiones típicas de trading:**

```
Londres:  08:00 - 16:00 UTC (05:00 - 13:00 Santiago)
NY:       13:30 - 20:00 UTC (10:30 - 17:00 Santiago)
Overlap:  13:30 - 16:00 UTC (10:30 - 13:00 Santiago) ← Mayor volumen
```

---

## ⚠️ RIESGO ACTUAL

**El bot live está operando con una configuración (solo NY) que NO corresponde al backtest que demostró rentabilidad.**

Esto puede explicar:
- Menor número de trades de lo esperado
- Rentabilidad inferior a la proyectada
- Pérdida de oportunidades en horario de Londres

---

## 🔍 PRÓXIMOS PASOS

1. Ejecutar backtest comparativo (Londres + NY vs solo NY)
2. Analizar WR y rentabilidad por sesión
3. Tomar decisión basada en datos
4. Actualizar configuración del bot live
5. Documentar decisión y resultados

---

**Fecha de análisis:** 30 marzo 2026
**Analista:** Claude (Cursor AI)
**Prioridad:** 🔴 CRÍTICA
