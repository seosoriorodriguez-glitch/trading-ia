# Pivot Points Scalping Strategy

## 📋 Descripción

Estrategia de scalping basada en **Pivot Points puros** (High/Low) detectados en M15, con entradas en M5 al segundo toque de la zona pivote.

**Características principales**:
- Sin filtros de tendencia (sin EMA)
- Detección automática de pivots en M15
- Zona = vela completa del pivot (low a high)
- Entrada al segundo toque con patrón de rechazo en M5
- Break Even en 1:1, Trailing Stop activo

## ⏰ Timeframes

- **Detección de pivots**: M15 (15 minutos)
- **Señales de entrada**: M5 (5 minutos)

## 📊 Reglas de la Estrategia

### 1. Detección de Pivot Points (M15)

**Pivot High (Resistencia)**:
- Vela M15 con high mayor que N velas antes y después
- N = `swing_strength` (default: 4)
- Zona = [low, high] de la vela pivote

**Pivot Low (Soporte)**:
- Vela M15 con low menor que N velas antes y después
- N = `swing_strength` (default: 4)
- Zona = [low, high] de la vela pivote

### 2. Validación de Zona

**Estados del pivot**:
1. **Creado**: Pivot detectado, esperando primer toque
2. **Primer toque**: Zona tocada una vez, NO se opera
3. **Activo**: Segundo toque detectado, buscar entrada
4. **Expirado**: Pivot roto o muy antiguo (100 velas M15)

### 3. Señales de Entrada (M5)

**LONG (en soporte)**:
- Precio M5 toca zona del pivot low (segundo toque)
- Vela M5 muestra rechazo:
  - Pin Bar alcista (mecha inferior larga)
  - Engulfing alcista
  - Inside Bar alcista
- Entrada: Al cierre de vela M5 de rechazo

**SHORT (en resistencia)**:
- Precio M5 toca zona del pivot high (segundo toque)
- Vela M5 muestra rechazo:
  - Pin Bar bajista (mecha superior larga)
  - Engulfing bajista
  - Inside Bar bajista
- Entrada: Al cierre de vela M5 de rechazo

### 4. Gestión de Riesgo

**Stop Loss**:
```
LONG:  SL = Pivot Low - 20 pips
SHORT: SL = Pivot High + 20 pips
```

**Take Profit**:
```
TP = Entry + (Entry - SL) * 2.0
R:R inicial = 2:1
```

**Break Even**:
```
Activación: Cuando precio alcanza 1:1 (Entry + distancia al SL)
Acción: Mover SL a Entry + 5 pips (proteger comisiones)
```

**Trailing Stop**:
```
Activación: Después de alcanzar BE (1:1)
Distancia: 15 pips desde el precio actual
Actualización: Cada vela M5 que avanza a favor

Ejemplo LONG:
- Entry: 46000
- SL inicial: 45980 (20 pips)
- BE en: 46020 (1:1) → SL a 46005
- Precio: 46040 → SL a 46025 (trailing 15 pips)
- Precio: 46060 → SL a 46045
```

## 🎯 Parámetros Clave

```yaml
zones:
  swing_strength: 4              # Pivots con 4 velas a cada lado
  min_touches: 2                 # Segundo toque para entrar
  zone_type: "full_candle"       # Zona = vela completa del pivot

entry:
  valid_patterns:
    - 'pin_bar'
    - 'engulfing'
    - 'inside_bar'

stop_loss:
  sl_buffer_points: 20           # 20 pips fuera de zona

take_profit:
  min_rr_ratio: 2.0              # R:R 2:1

break_even:
  trigger_rr: 1.0                # BE en 1:1
  offset_points: 5

trailing_stop:
  activation_rr: 1.0             # Activar después de BE
  trail_distance_points: 15      # Trailing a 15 pips

filters:
  trend:
    enabled: false               # SIN filtro de tendencia
```

## 📈 Resultados de Backtest

### [Pendiente de Implementación]

```
Período:           [TBD]
Trades:            [TBD]
Win Rate:          [TBD]%
Profit Factor:     [TBD]
Retorno:           [TBD]%
Max Drawdown:      [TBD]%
Frecuencia:        [TBD] trades/mes
```

**Benchmarks esperados para scalping**:
- Win Rate: 55-65%
- Profit Factor: 1.3-1.8 (después de costos)
- Frecuencia: 10-30 trades/mes por instrumento

## ⚠️ Consideraciones Importantes

### Costos de Transacción

En scalping, los costos son **críticos**:

```
US30:
- Spread: 2-5 puntos (~$2-5 por lote mini)
- Comisión FTMO: $7 round-trip
- Total: ~$10-12 por trade

Con SL de 20 pips:
- Costo = 50-60% del riesgo
- Necesitas WR > 55% para ser rentable
```

### Datos M5

**Problema**: Yahoo Finance NO tiene datos M5.

**Soluciones**:
1. Exportar datos M5 desde MT5
2. Usar API de broker (Dukascopy, etc.)
3. Validar en demo en lugar de backtest largo

### Ejecución

Scalping requiere:
- VPS con baja latencia
- Ejecución instantánea
- Monitoreo constante (o bot robusto)

## 🔄 Historial de Versiones

### V1 - Versión Inicial (Pendiente)
- **Fecha**: [TBD]
- **Cambios**: Implementación inicial
- **Resultado**: [TBD]

## 📁 Archivos

### Configuración
- `config/strategy_params.yaml` - Parámetros de scalping
- `config/instruments.yaml` - Config por instrumento

### Código (Por Implementar)
- `core/pivot_points.py` - Detección de pivots en M15
- `core/rejection_patterns.py` - Patrones de rechazo (Pin Bar, Engulfing, Inside Bar)
- `core/scalping_signals.py` - Generación de señales de entrada
- `backtest/scalping_backtester.py` - Backtester con BE y Trailing

### Datos
- `data/` - Datos M5 y M15 (por descargar)

### Resultados
- `results/` - Análisis de backtest (por generar)

## 🚀 Uso

### 1. Descargar Datos M5 desde MT5

```bash
# Exportar datos desde MT5 (no disponibles en Yahoo)
python3 tools/export_mt5_data.py \
  --instrument US30 \
  --timeframe M5 \
  --days 60 \
  --output strategies/pivot_scalping/data/US30_M5_60d.csv
```

### 2. Ejecutar Backtest

```bash
cd strategies/pivot_scalping

python3 run_backtest.py \
  --data-m5 data/US30_M5_60d.csv \
  --data-m15 data/US30_M15_60d.csv \
  --instrument US30 \
  --config config/strategy_params.yaml \
  --output data/backtest_US30_scalping_60d.csv
```

### 3. Analizar Resultados

```bash
python3 ../../tools/analyze_backtest.py \
  data/backtest_US30_scalping_60d.csv \
  > results/ANALISIS_60D.md
```

## ✅ Estado

- [ ] En desarrollo
- [ ] Código implementado
- [ ] Backtest completado
- [ ] Validado en demo
- [ ] Listo para FTMO

## 🎯 Próximos Pasos

1. **Implementar módulos core**:
   - `pivot_points.py` - Detección de pivots
   - `rejection_patterns.py` - Patrones de rechazo
   - `scalping_signals.py` - Generación de señales

2. **Implementar backtester**:
   - `scalping_backtester.py` - Con BE y Trailing Stop

3. **Obtener datos M5**:
   - Exportar desde MT5 o broker
   - Mínimo 60 días para validación inicial

4. **Ejecutar backtest**:
   - Validar con 60 días
   - Criterios: PF > 1.3, WR > 55%, Max DD < 10%

5. **Demo testing** (si backtest es positivo):
   - Operar 30 días en demo
   - Validar ejecución y slippage real
   - Ajustar parámetros si es necesario

6. **Combinar con S/R Swing**:
   - Scalping para frecuencia
   - Swing para calidad
   - Portfolio diversificado

## 💡 Recomendación

**NO usar en FTMO hasta**:
- Backtest con 60+ días y 30+ trades
- PF > 1.3 (después de costos)
- Validación en demo 30+ días
- Slippage y costos reales medidos

**Alternativa**: Usar S/R Swing (H4+H1) que ya está validada (PF 3.57) y añadir más instrumentos para frecuencia.
