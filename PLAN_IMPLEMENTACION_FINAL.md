# 🚀 PLAN DE IMPLEMENTACIÓN FINAL

**Fecha**: 26 de marzo de 2026  
**Estrategia**: V4 Solo LONGs (H4 Zonas + H1 Señales)  
**Estado**: Validada en backtest de 2 años

---

## ✅ Estado Actual

### Estrategia Base Validada

```
Versión:       V4 Solo LONGs
Timeframes:    H4 (zonas) + H1 (señales)
Dirección:     Solo LONGs (SHORTs desactivados)
Período:       2 años (Mar 2024 - Mar 2026)
```

### Resultados por Instrumento

| Instrumento | Trades | Win Rate | Retorno | PF | Max DD | Estado |
|-------------|--------|----------|---------|-----|--------|--------|
| **US30** | 25 | 72.0% | +9.01% | 3.57 | 0.98% | ✅ Excelente |
| **NAS100** | 37 | 51.4% | +7.97% | 1.89 | 2.75% | ✅ Bueno |
| **SPX500** | 30 | 56.7% | +1.56% | 1.24 | 2.25% | ⚠️ Marginal |

**Total**: 92 trades en 2 años = **3.8 trades/mes**

---

## 🎯 Infraestructura Creada

### 1. Configuraciones Modulares

```
config/
├── strategy_params.yaml           # Base H4+H1 (validada)
├── strategy_params_h1_m15.yaml    # Experimental H1+M15
├── instruments.yaml                # Instrumentos para H4+H1
└── instruments_h1_m15.yaml        # Instrumentos para H1+M15
```

### 2. Scripts de Ejecución

```
run_backtest.py              # Backtest individual (ahora acepta --config)
run_parallel_backtests.py   # Backtests en paralelo
download_yahoo_data.py       # Descarga de datos
```

### 3. Uso de Scripts

**Backtest individual**:
```bash
# Estrategia base (H4+H1)
python run_backtest.py \
  --data-h1 data/US30_H1_730d.csv \
  --data-h4 data/US30_H4_730d.csv \
  --instrument US30 \
  --balance 100000 \
  --output data/backtest_US30.csv

# Estrategia experimental (H1+M15)
python run_backtest.py \
  --data-h1 data/US30_M15_60d.csv \
  --data-h4 data/US30_H1_60d.csv \
  --instrument US30 \
  --balance 100000 \
  --output data/backtest_US30_h1_m15.csv \
  --config config/strategy_params_h1_m15.yaml
```

**Backtests en paralelo**:
```bash
# Todos los instrumentos, estrategia base
python run_parallel_backtests.py --strategy h4_h1 --instruments US30 NAS100 SPX500

# Solo US30, ambas estrategias
python run_parallel_backtests.py --strategy h4_h1 h1_m15 --instruments US30

# Todo (cuando tengas datos M15)
python run_parallel_backtests.py --all
```

---

## 📋 Plan de Acción Recomendado

### Fase 1: Implementar US30 + NAS100 en Demo (Esta Semana)

**Objetivo**: Validar la estrategia en condiciones reales.

**Pasos**:
1. ✅ Configurar cuenta FTMO demo
2. ✅ Conectar MT5 (Docker o nativo)
3. ✅ Verificar nombres de símbolos con `verify_mt5.py`
4. ✅ Actualizar `config/instruments.yaml` con nombres correctos
5. ✅ Ejecutar bot en demo durante 1-2 meses
6. ✅ Monitorear métricas diarias

**Criterio de éxito**:
- PF > 2.0 después de 20+ trades
- Max DD < 5%
- Win Rate > 60%
- Al menos 4-5 trading days por mes

**Si pasa**: Proceder a Fase 2  
**Si falla**: Investigar discrepancias entre backtest y demo

---

### Fase 2: SI Fase 1 funciona → Añadir SPX500 o H1+M15 (Próximo Mes)

**Opción A: Añadir SPX500**

**Pros**:
- ✅ Ya está validado en backtest (PF 1.24)
- ✅ Aumenta frecuencia a 3.8 trades/mes
- ✅ Bajo riesgo

**Contras**:
- ❌ PF bajo (1.24)
- ❌ Retorno bajo (1.56%)

**Opción B: Añadir H1+M15 en US30**

**Pros**:
- ✅ Mayor frecuencia (estimado 6-8 trades/mes adicionales)
- ✅ Cumple FTMO

**Contras**:
- ❌ NO validado en backtest (solo 60 días de datos)
- ❌ Mayor riesgo
- ❌ Requiere validación en demo primero

**Recomendación**: Probar **Opción B** (H1+M15) en **demo** durante 1 mes antes de decidir.

---

### Fase 3: SI Fase 2 funciona → Challenge FTMO (Mes 3)

**Objetivo**: Pasar el challenge FTMO y obtener cuenta fondeada.

**Configuración Final**:
- US30 + NAS100 en H4+H1 (base)
- US30 en H1+M15 (si validado en Fase 2)
- Solo LONGs

**Expectativa**:
- Frecuencia: 6-10 trades/mes
- PF: > 2.0
- Max DD: < 5%
- Cumple todos los requisitos FTMO

---

## ⚠️ Consideraciones Importantes

### 1. Correlación entre Instrumentos

US30, NAS100 y SPX500 están **altamente correlacionados** (>0.9). Esto significa:

- Si el mercado cae, los 3 caen juntos
- No es verdadera diversificación
- Riesgo de tener 3 trades perdedores simultáneos

**Solución**: Configuración actual ya limita a **máximo 2 trades simultáneos** en el mismo grupo de correlación.

### 2. Limitación de Datos M15

Yahoo Finance solo tiene 60 días de datos M15. Para validar H1+M15 necesitas:

**Opción A**: Usar broker con datos históricos (FTMO, MT5)  
**Opción B**: Forward testing en demo (3-6 meses)  
**Opción C**: Comprar datos históricos

**Recomendación**: Opción B (demo) es la más práctica y realista.

### 3. Frecuencia de Trading para FTMO

**Requisito FTMO**: 4-5 trading days por mes (depende del plan)

**Situación actual**:
- US30 + NAS100: 2.6 trades/mes
- Si cada trade dura 1-2 días: ~3-5 trading days/mes ⚠️

**Riesgo**: Puede no cumplir mínimos en meses con pocas señales.

**Soluciones**:
1. Añadir H1+M15 (más frecuencia)
2. Añadir más instrumentos (EUR/USD, GBP/USD)
3. Reducir `min_rr_ratio` de 2.0 a 1.8 (más señales, menor calidad)

---

## 🔧 Cómo Probar Nuevas Estrategias

### Estructura Modular Implementada

Ahora puedes probar nuevas estrategias sin modificar la base:

1. **Crear nuevo config**: `config/strategy_params_NOMBRE.yaml`
2. **Ajustar parámetros**: Timeframes, filtros, etc.
3. **Ejecutar backtest**: `python run_backtest.py --config config/strategy_params_NOMBRE.yaml ...`
4. **Comparar resultados**: Mantener la mejor estrategia

### Ejemplo: Probar Diferentes Configuraciones

```bash
# Estrategia 1: H4+H1 Solo LONGs (actual)
python run_backtest.py --data-h1 data/US30_H1_730d.csv --data-h4 data/US30_H4_730d.csv --instrument US30 --output data/backtest_v4_base.csv

# Estrategia 2: H4+H1 Con SHORTs selectivos
# (Crear config/strategy_params_with_shorts.yaml con counter_trend_min_touches: 10)
python run_backtest.py --data-h1 data/US30_H1_730d.csv --data-h4 data/US30_H4_730d.csv --instrument US30 --output data/backtest_v4_with_shorts.csv --config config/strategy_params_with_shorts.yaml

# Estrategia 3: H1+M15 (cuando tengas datos)
python run_backtest.py --data-h1 data/US30_M15_60d.csv --data-h4 data/US30_H1_60d.csv --instrument US30 --output data/backtest_h1_m15.csv --config config/strategy_params_h1_m15.yaml
```

---

## 📊 Resumen de Validación Completada

### ✅ Completado

1. ✅ Estrategia base V4 validada en US30 (PF 3.57, +9.01%)
2. ✅ Bugs críticos corregidos (Break Even, pnl_usd)
3. ✅ Estrategia validada en NAS100 (PF 1.89, +7.97%)
4. ✅ Estrategia validada en SPX500 (PF 1.24, +1.56%)
5. ✅ Infraestructura modular para probar nuevas estrategias
6. ✅ Configs para H1+M15 creados (pendiente de validación)

### ⏳ Pendiente

1. ⏳ Validar en FTMO demo (1-2 meses)
2. ⏳ Decidir si añadir SPX500 o no
3. ⏳ Validar H1+M15 en demo (si se decide probar)
4. ⏳ Challenge FTMO (si demo es exitoso)

---

## 🎯 Decisión Inmediata Necesaria

**¿Qué configuración quieres usar para empezar en demo?**

### Opción 1: US30 + NAS100 (Conservador)

```
Frecuencia: 2.6 trades/mes
PF Promedio: 2.73
Riesgo: Bajo
```

### Opción 2: US30 + NAS100 + SPX500 (Balanceado)

```
Frecuencia: 3.8 trades/mes
PF Promedio: 2.23
Riesgo: Medio
```

### Opción 3: Solo US30 (Máxima Calidad)

```
Frecuencia: 1.0 trades/mes
PF: 3.57
Riesgo: Mínimo
```

**Mi recomendación**: **Opción 1** (US30 + NAS100) - Balance entre calidad y frecuencia.

---

**¿Qué quieres hacer ahora?**

1. **"Configura para demo"** → Preparo archivos para ejecutar en FTMO demo
2. **"Analiza SPX500"** → Investigo por qué SPX500 tiene PF bajo
3. **"Prueba H1+M15"** → Descargo datos M15 (60 días) y ejecuto backtest experimental
4. **"Optimiza NAS100"** → Ajusto parámetros específicos para NAS100
