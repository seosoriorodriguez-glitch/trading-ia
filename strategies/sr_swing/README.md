# S/R Swing Trading Strategy

## 📋 Descripción

Estrategia de swing trading basada en zonas de **Soporte y Resistencia** con confirmación de patrones de precio (Pin Bar, False Breakout B1).

## ⏰ Timeframes

- **Detección de zonas**: H4 (4 horas)
- **Señales de entrada**: H1 (1 hora)

## 📊 Reglas de Entrada

### Detección de Zonas S/R

1. Identificar swing highs/lows en H4 con `swing_strength: 5`
2. Validar zona con mecha fuerte (`min_wick_ratio: 0.50`)
3. Zona requiere mínimo 2 toques para activarse
4. Zona = rango entre high y low del swing

### Señales de Entrada (H1)

**LONG (en soporte)**:
- Pin Bar alcista: Mecha inferior larga (2x cuerpo)
- False Breakout B1: Barrido de liquidez + cierre dentro de zona

**SHORT (en resistencia)**:
- Pin Bar bajista: Mecha superior larga (2x cuerpo)
- False Breakout B1: Barrido de liquidez + cierre dentro de zona

### Filtro de Tendencia (EMA 200)

- **Precio > EMA 200**: Solo LONGs permitidos
- **Precio < EMA 200**: Solo SHORTs permitidos (desactivado en V4)
- **V4 (Solo LONGs)**: `allow_counter_trend: false` - SHORTs desactivados completamente

## 🎯 Gestión de Riesgo

### Stop Loss
```
LONG:  SL = Zona Low - sl_buffer_points (150 pts para US30)
SHORT: SL = Zona High + sl_buffer_points
```

### Take Profit
```
TP = Próxima zona opuesta - tp_offset_points (50 pts)
R:R mínimo: 2.0:1
```

### Break Even
```
Activación: Cuando precio alcanza 1.5x el riesgo inicial
Acción: Mover SL a Entry + offset_points (30 pts)
```

### Sizing
```
Riesgo por trade: 0.5% del balance
Máximo trades simultáneos: 3
```

## 📈 Resultados de Backtest

### V4 - Solo LONGs (H4+H1) - 2 Años

#### US30
```
Período:           Mar 2024 - Mar 2026 (730 días)
Trades:            25
Win Rate:          72.0%
Profit Factor:     3.57
Retorno:           +9.01%
Max Drawdown:      0.98%
Frecuencia:        1.0 trades/mes
```

**Por Tipo de Señal**:
- Pin Bar: 7 trades, WR 71.4%
- False Breakout B1: 18 trades, WR 72.2%

#### NAS100
```
Período:           Mar 2024 - Mar 2026 (730 días)
Trades:            37
Win Rate:          51.4%
Profit Factor:     1.89
Retorno:           +7.97%
Max Drawdown:      2.75%
Frecuencia:        1.6 trades/mes
```

#### SPX500
```
Período:           Mar 2024 - Mar 2026 (730 días)
Trades:            30
Win Rate:          56.7%
Profit Factor:     1.24
Retorno:           +1.56%
Max Drawdown:      2.25%
Frecuencia:        1.5 trades/mes
```

### Resumen Multi-Instrumento

```
Total Trades:      92 (US30 + NAS100 + SPX500)
Frecuencia:        3.8 trades/mes
Retorno Promedio:  +6.18%
PF Promedio:       2.23
```

## 🔄 Historial de Versiones

### V4 - Solo LONGs (Actual) ✅ VALIDADA
- **Fecha**: 26 Mar 2026
- **Cambios**: 
  - Desactivados SHORTs completamente (`allow_counter_trend: false`)
  - Corrección de bug crítico en cálculo de `pnl_usd`
  - Corrección de bug en `original_stop_loss`
- **Resultado**: PF 3.57, WR 72%, +9.01% en US30

### V3 - Filtro EMA 200
- **Fecha**: 26 Mar 2026
- **Cambios**:
  - Añadido filtro de tendencia con EMA 200 en H4
  - Counter-trend solo con zonas fuertes (7+ toques)
- **Resultado**: PF 1.58, WR 57% (antes de corrección de bugs)

### V2 - Optimización de Filtros
- **Fecha**: 26 Mar 2026
- **Cambios**:
  - Desactivados Engulfing y False Breakout B2
  - B1 más estricto (`b1_min_body_ratio: 0.60`)
  - SL buffer aumentado a 150 pts
  - R:R mínimo aumentado a 2.0
- **Resultado**: PF 1.49, WR 50.9%

### V1 - Versión Inicial
- **Fecha**: 26 Mar 2026
- **Resultado**: PF 1.31, WR 49.4%, -30.45% retorno

## 📁 Archivos

### Configuración
- `config/strategy_params.yaml` - Parámetros de la estrategia
- `config/instruments.yaml` - Configuración por instrumento
- `config/ftmo_rules.yaml` - Reglas de compliance FTMO

### Código
- `core/levels.py` - Detección de zonas S/R
- `core/signals.py` - Generación de señales (Pin Bar, B1)
- `core/trend.py` - Filtro de tendencia EMA 200
- `backtest/backtester.py` - Motor de backtest

### Datos
- `data/US30_H1_730d.csv` - Datos H1 de US30 (2 años)
- `data/US30_H4_730d.csv` - Datos H4 de US30 (2 años)
- `data/backtest_US30_v4_longs_only.csv` - Resultados V4

### Resultados
- `results/ANALISIS_V3_REAL_METRICAS_CORREGIDAS.md` - Análisis detallado V3
- `results/COMPARATIVA_COMPLETA_V1_V2_V3.md` - Comparativa de versiones
- `results/RESULTADOS_MULTI_INSTRUMENTO.md` - Análisis multi-instrumento

## 🚀 Uso

### Ejecutar Backtest

```bash
cd strategies/sr_swing

# Backtest US30
python3 run_backtest.py \
  --data-h1 data/US30_H1_730d.csv \
  --data-h4 data/US30_H4_730d.csv \
  --instrument US30 \
  --balance 100000 \
  --output data/backtest_US30_new.csv
```

### Descargar Nuevos Datos

```bash
# Desde la raíz del proyecto
python3 tools/download_yahoo_data.py \
  --ticker "^DJI" \
  --days 730 \
  --interval 1h \
  --output strategies/sr_swing/data/US30_H1_730d
```

## ✅ Estado

- [x] Backtest completado
- [x] Validado en múltiples instrumentos
- [x] Bugs críticos corregidos
- [ ] Validación en demo
- [ ] Listo para FTMO

## 🎯 Próximos Pasos

1. **Implementar en demo**: Validar con US30 + NAS100 durante 1-2 meses
2. **Monitorear frecuencia**: Si < 4 trades/mes, añadir SPX500
3. **Evaluar H1+M15**: Solo si frecuencia es insuficiente y después de validación en demo
4. **Challenge FTMO**: Una vez validado en demo con métricas consistentes

## 📊 Recomendación

**Configuración óptima para FTMO**:
- Instrumentos: US30 + NAS100
- Timeframes: H4 (zonas) + H1 (señales)
- Dirección: Solo LONGs
- Frecuencia esperada: 2.6 trades/mes
- PF esperado: > 2.0
- Max DD esperado: < 3%
