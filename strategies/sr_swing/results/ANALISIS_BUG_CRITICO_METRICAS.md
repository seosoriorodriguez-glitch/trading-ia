# 🚨 ANÁLISIS DEL BUG CRÍTICO EN MÉTRICAS

**Fecha**: 26 de marzo de 2026  
**Versión**: V3 Corregido  
**Instrumento**: US30 (Dow Jones)  
**Período**: 2 años (Mar 2024 - Mar 2026)

---

## 📋 Resumen Ejecutivo

Se detectó y corrigió un **bug crítico** en el cálculo de métricas del backtester que producía resultados contradictorios:

- **Profit Factor en Puntos**: 1.58 (parecía rentable)
- **Profit Factor en USD**: 0.25 (pérdida masiva)
- **Retorno**: -19.05%

El problema estaba en que el **Profit Factor se calculaba sobre puntos brutos**, mientras que el **balance se calculaba con normalización por riesgo en USD**. Esto generaba una ilusión de rentabilidad cuando en realidad la estrategia estaba perdiendo dinero.

---

## 🔍 Explicación del Bug

### Cálculo Incorrecto (Antes)

```python
# Profit Factor calculado sobre puntos brutos
gross_profit = sum(t.pnl_points for t in trades if t.pnl_points > 0)
gross_loss = abs(sum(t.pnl_points for t in trades if t.pnl_points < 0))
profit_factor = gross_profit / gross_loss  # 1.58
```

**Problema**: Los puntos brutos no reflejan el riesgo real de cada trade. Un trade con SL de 100 pts y ganancia de 200 pts tiene el mismo peso que un trade con SL de 500 pts y ganancia de 200 pts, cuando en realidad el segundo arriesga 5x más capital.

### Cálculo Correcto (Después)

```python
# P&L en USD basado en riesgo normalizado
planned_risk_pts = abs(entry_price - stop_loss)
risk_usd = initial_balance * 0.005  # $500 con 0.5% de riesgo
pnl_usd = (pnl_points / planned_risk_pts) * risk_usd

# Profit Factor calculado sobre USD
gross_profit_usd = sum(t.pnl_usd for t in trades if t.pnl_usd > 0)
gross_loss_usd = abs(sum(t.pnl_usd for t in trades if t.pnl_usd < 0))
profit_factor_usd = gross_profit_usd / gross_loss_usd  # 0.25
```

**Solución**: Cada trade se normaliza por su riesgo planificado, asegurando que todos los trades arriesgan la misma cantidad de capital ($500 en este caso).

---

## 📊 Comparación de Métricas

| Métrica | Puntos (Incorrecto) | USD (Correcto) | Diferencia |
|---------|---------------------|----------------|------------|
| **Profit Factor** | 1.58 | **0.25** | -84% |
| **Retorno Total** | N/A | **-19.05%** | N/A |
| **Win Rate** | 48.5% | 48.5% | 0% |
| **Max Drawdown** | ~31% (incorrecto) | **21.05%** | -10% |
| **Trades Totales** | 99 | 99 | 0 |

### Conclusión

El **Profit Factor real es 0.25**, lo que significa que **por cada $1 que pierde, solo gana $0.25**. La estrategia está destruyendo capital.

---

## 🎯 Análisis por Dirección (Métricas Corregidas)

### LONGs: Altamente Rentables

```
Trades:        26
Win Rate:      73.1%
P&L Promedio:  +311.0 pts
```

**Conclusión**: Los LONGs funcionan excelentemente bien. 3 de cada 4 trades son ganadores.

### SHORTs: Destruyendo Capital

```
Trades:        73
Win Rate:      39.7%
P&L Promedio:  -1.7 pts
```

**Conclusión**: Los SHORTs están perdiendo dinero consistentemente. Solo 4 de cada 10 trades son ganadores.

---

## 🧠 ¿Por Qué el Bug Era Engañoso?

El Profit Factor de 1.58 en puntos sugería que la estrategia era rentable porque:

1. **Algunos trades grandes en puntos** (con SL pequeño) generaban muchos puntos de ganancia
2. **Pero arriesgaban poco capital** en términos absolutos
3. Mientras que **trades perdedores con SL grande** perdían pocos puntos pero **arriesgaban mucho capital**

### Ejemplo Real

**Trade Ganador (LONG)**:
- Entry: 40,000
- SL: 39,900 (100 pts de riesgo)
- TP: 40,200 (200 pts de ganancia)
- **P&L en puntos**: +200
- **P&L en USD**: (200/100) × $500 = **+$1,000**

**Trade Perdedor (SHORT)**:
- Entry: 45,000
- SL: 45,500 (500 pts de riesgo)
- Exit: 45,200 (200 pts de pérdida)
- **P&L en puntos**: -200
- **P&L en USD**: (200/500) × $500 = **-$200**

En puntos brutos, ambos trades se cancelan (+200 - 200 = 0). Pero en USD real, el trade ganador generó +$1,000 y el perdedor solo perdió -$200, resultando en +$800 neto.

Sin embargo, si el patrón se invierte (muchos SHORTs con SL grande perdiendo poco en puntos pero mucho en USD), el balance se destruye mientras el PF en puntos se mantiene alto.

---

## 🚨 Impacto del Bug

### Antes de la Corrección

- **Creíamos** que V3 había alcanzado el objetivo de PF > 1.5 (1.58)
- **Creíamos** que el problema era solo el retorno negativo
- **Pensábamos** que optimizar SHORTs mejoraría el resultado

### Después de la Corrección

- **Sabemos** que la estrategia está perdiendo dinero masivamente (PF 0.25)
- **Sabemos** que los SHORTs no solo son malos, sino que están destruyendo capital
- **Sabemos** que necesitamos una solución radical, no optimizaciones incrementales

---

## ✅ Cambios Implementados

### 1. Añadir `pnl_usd` a `BacktestTrade`

```python
@dataclass
class BacktestTrade:
    # ... campos existentes ...
    pnl_usd: float = 0  # P&L en USD basado en riesgo normalizado
```

### 2. Calcular `pnl_usd` en el Backtester

```python
# Balance final y cálculo de P&L en USD
risk_per_trade = initial_balance * sizing_config["risk_per_trade_pct"]
for trade in trades:
    if trade.direction == "LONG":
        planned_risk_pts = trade.entry_price - trade.stop_loss
    else:
        planned_risk_pts = trade.stop_loss - trade.entry_price
    
    if planned_risk_pts > 0:
        pnl_usd = (trade.pnl_points / planned_risk_pts) * risk_per_trade
        trade.pnl_usd = pnl_usd
        balance += pnl_usd
```

### 3. Añadir `profit_factor_usd` a `BacktestResult`

```python
@property
def profit_factor_usd(self) -> float:
    """Profit Factor en USD (MÉTRICA CORRECTA)."""
    gross_profit = sum(t.pnl_usd for t in self.trades if t.pnl_usd > 0)
    gross_loss = abs(sum(t.pnl_usd for t in self.trades if t.pnl_usd < 0))
    if gross_loss == 0:
        return float("inf") if gross_profit > 0 else 0
    return gross_profit / gross_loss
```

### 4. Actualizar `summary()` para Mostrar Ambas Métricas

```
Profit Factor (USD):     0.25  ← MÉTRICA REAL
Profit Factor (Puntos):  1.58  (referencia)
```

### 5. Añadir `pnl_usd` al CSV de Salida

```python
records.append({
    # ... campos existentes ...
    "pnl_usd": t.pnl_usd,
    # ...
})
```

---

## 🎯 Próximos Pasos

### Opción 1: V4 Solo LONGs (Recomendado)

**Objetivo**: Validar si la estrategia es rentable operando solo LONGs.

**Cambios**:
- Desactivar completamente las señales SHORT
- Re-ejecutar backtest con solo LONGs
- Validar si PF en USD > 1.0 y retorno positivo

**Expectativa**: Con 73.1% WR y +311 pts promedio, los LONGs deberían ser altamente rentables.

### Opción 2: Filtro de Tendencia Más Agresivo

**Objetivo**: Permitir SHORTs solo en condiciones extremadamente favorables.

**Cambios**:
- Aumentar `counter_trend_min_touches` de 7 a 10+
- O añadir filtro de EMA 50 además de EMA 200
- O desactivar SHORTs si precio > EMA 200 por más de X días

**Expectativa**: Reducir SHORTs de 73 a ~10-15 trades, manteniendo solo los de altísima calidad.

### Opción 3: Validar en Período Diferente

**Objetivo**: Confirmar si el problema de SHORTs es específico del período alcista 2024-2026.

**Cambios**:
- Descargar datos de 2022-2024 (período bajista para US30)
- Re-ejecutar backtest en ese período
- Validar si SHORTs funcionan en mercado bajista

**Expectativa**: Si SHORTs funcionan en 2022-2024, el problema es el sesgo alcista del período actual.

---

## 📝 Lecciones Aprendidas

1. **Nunca confíes en métricas que no estén normalizadas por riesgo**: El Profit Factor en puntos brutos es engañoso.

2. **El balance es la métrica más honesta**: Si el balance cae, algo está mal, sin importar lo que digan otras métricas.

3. **Validar consistencia entre métricas**: Si PF es alto pero retorno es negativo, hay un bug.

4. **Normalizar por riesgo es fundamental**: Todos los trades deben arriesgar la misma cantidad de capital para comparaciones justas.

5. **Los promedios pueden mentir**: Un promedio de -1.7 pts en SHORTs parece pequeño, pero con 73 trades y normalización por riesgo, destruye el balance.

---

## 🔗 Archivos Relacionados

- **Backtest V3 Corregido**: `data/backtest_US30_v3_fixed.csv`
- **Código del Backtester**: `backtest/backtester.py`
- **Análisis Gráfico**: `data/backtest_analysis.png`
- **Comparativa V1-V2-V3**: `COMPARATIVA_COMPLETA_V1_V2_V3.md`

---

**Conclusión Final**: La estrategia S/R en US30 (2024-2026) es **altamente rentable en LONGs** pero **destruye capital en SHORTs**. El Profit Factor real es **0.25**, no 1.58. Se recomienda proceder con **V4 Solo LONGs** para validar rentabilidad antes de intentar arreglar los SHORTs.
