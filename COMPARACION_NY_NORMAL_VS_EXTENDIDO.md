# 📊 COMPARACIÓN: NY Normal vs NY Extendido (2hr antes)

## ⚙️ CONFIGURACIÓN PROBADA

**Parámetros:**
- R:R: 3.5
- Buffer SL: 25 puntos
- Sin filtro BOS

**Sesiones:**
- **NY Normal**: 13:30-20:00 UTC (6.5 horas)
- **NY Extendido**: 11:30-20:00 UTC (8.5 horas, +2hr antes)

---

## 📊 RESULTADOS COMPARATIVOS

| Métrica | NY Normal | NY Extendido | Diferencia |
|---------|-----------|--------------|------------|
| **Horario** | 13:30-20:00 | 11:30-20:00 | +2 horas |
| **Trades** | 197 | 245 | **+48 (+24%)** |
| **Win Rate** | 29.4% | 26.5% | **-2.9%** ⚠️ |
| **Retorno** | **+30.91%** | +18.83% | **-12.08%** ❌ |
| **Max DD** | **6.62%** | 7.46% | **+0.84%** ⚠️ |
| **Profit Factor** | **1.36** | 1.18 | **-0.18** ❌ |
| **Avg Win** | $2,017 | $1,898 | -$119 |
| **Avg Loss** | $-619 | $-581 | +$38 |

---

## ❌ CONCLUSIÓN: NY NORMAL ES MEJOR

### Razones:
1. **Retorno 39% menor** (+18.83% vs +30.91%)
2. **Win Rate más bajo** (26.5% vs 29.4%)
3. **Profit Factor peor** (1.18 vs 1.36)
4. **Max DD ligeramente mayor** (7.46% vs 6.62%)

---

## 📉 ANÁLISIS DE LAS 2 HORAS NUEVAS (11:00-13:00 UTC)

### Datos:
- **Trades**: 53 (22% del total)
- **Winners**: 10 (18.9% WR)
- **PnL**: **$-6,183.12** ❌
- **Contribución**: **-32.8% del total** (negativa!)

### Por Hora:
| Hora UTC | Trades | Winners | Win Rate | PnL USD |
|----------|--------|---------|----------|---------|
| **11:00-12:00** | 22 | 5 | 22.7% | **$-466.95** ❌ |
| **12:00-13:00** | 31 | 5 | **16.1%** | **$-5,716.17** ❌❌ |

### Observación Crítica:
- **12:00-13:00 UTC** es la **peor hora**:
  - Solo 16.1% Win Rate
  - Pérdida de $-5,716.17
  - 31 trades (muchos trades malos)

---

## 📈 ANÁLISIS POR HORA COMPLETO (UTC)

| Hora UTC | Trades | Win Rate | PnL USD | Calidad |
|----------|--------|----------|---------|---------|
| **11:00-12:00** | 22 | 22.7% | $-466.95 | ❌ Malo |
| **12:00-13:00** | 31 | **16.1%** | **$-5,716.17** | ❌❌ Muy Malo |
| 13:00-14:00 | 20 | 25.0% | $1,153.62 | ⚠️ Regular |
| **14:00-15:00** | 30 | **43.3%** | **$14,378.38** | ✅✅ Excelente |
| 15:00-16:00 | 30 | 30.0% | $4,764.35 | ✅ Bueno |
| 16:00-17:00 | 37 | 29.7% | $5,861.07 | ✅ Bueno |
| 17:00-18:00 | 24 | 25.0% | $1,134.13 | ⚠️ Regular |
| 18:00-19:00 | 30 | 20.0% | $-2,374.91 | ❌ Malo |
| 19:00-20:00 | 21 | 23.8% | $98.47 | ⚠️ Regular |

### Mejores Horas:
1. **14:00-15:00 UTC** (10:00-11:00 AM NY): 43.3% WR, $14,378 ✅✅
2. **15:00-16:00 UTC** (11:00-12:00 PM NY): 30.0% WR, $4,764 ✅
3. **16:00-17:00 UTC** (12:00-01:00 PM NY): 29.7% WR, $5,861 ✅

### Peores Horas:
1. **12:00-13:00 UTC** (08:00-09:00 AM NY): 16.1% WR, $-5,716 ❌❌
2. **18:00-19:00 UTC** (02:00-03:00 PM NY): 20.0% WR, $-2,375 ❌
3. **11:00-12:00 UTC** (07:00-08:00 AM NY): 22.7% WR, $-467 ❌

---

## 🔍 ¿POR QUÉ LAS 2 HORAS ANTES SON MALAS?

### 11:00-13:00 UTC = 07:00-09:00 AM NY (Pre-Market)

**Características:**
- **Pre-apertura de NY**: Baja liquidez
- **Overlap con Londres**: Pero Londres ya está cerrando
- **Volatilidad errática**: Movimientos sin dirección clara
- **OBs menos confiables**: Zonas formadas con bajo volumen

**Resultado:**
- Win Rate muy bajo (16-23%)
- Pérdida neta de $-6,183
- Destruye 32.8% del profit potencial

---

## ✅ RECOMENDACIÓN FINAL

### MANTENER NY NORMAL: 13:30-20:00 UTC

**Razones:**
1. ✅ **+39% más rentable** (+30.91% vs +18.83%)
2. ✅ **Mejor Win Rate** (29.4% vs 26.5%)
3. ✅ **Mejor Profit Factor** (1.36 vs 1.18)
4. ✅ **Menor Max DD** (6.62% vs 7.46%)
5. ✅ **Evita horas pre-market** (baja calidad)

### Horario Óptimo:
- **Inicio**: 13:30 UTC (09:30 AM NY) - Apertura oficial
- **Fin**: 20:00 UTC (04:00 PM NY) - Cierre oficial
- **Skip**: 15 minutos (evita volatilidad inicial)
- **Trading real**: 13:45-20:00 UTC (6h 15min)

---

## 📊 CONFIGURACIÓN FINAL RECOMENDADA

```python
# config.py
DEFAULT_PARAMS = {
    # ... otros params ...
    
    "target_rr": 3.5,           # Óptimo
    "buffer_points": 25,        # Óptimo
    "require_bos": False,       # Sin BOS (más trades)
    
    "sessions": {
        "new_york": {
            "start": "13:30",   # Apertura oficial NY
            "end": "20:00",     # Cierre oficial NY
            "skip_minutes": 15  # Evita primeros 15 min
        },
    },
}
```

### Resultados Esperados:
- **Retorno**: +30.91% (104 días)
- **Win Rate**: 29.4%
- **Max DD**: 6.62%
- **Profit Factor**: 1.36
- **Trades**: ~197 (104 días)
- **Frecuencia**: ~2 trades/día

---

## 🎯 PRÓXIMOS PASOS

1. ✅ Configuración óptima identificada (R:R 3.5 / Buffer 25)
2. ✅ Horario óptimo confirmado (NY 13:30-20:00)
3. ⏳ Implementar en live bot (requiere autorización)
4. ⏳ Testing en dry run
5. ⏳ Deploy en cuenta real

---

*Análisis generado: 2026-03-31*
*Período backtest: 104 días*
*Conclusión: NY Normal (13:30-20:00) es superior*
