# Estrategia de Soportes y Resistencias en Índices
## Documento de Estrategia v1.0 — Bot Automatizado para FTMO

---

## 1. Resumen General

**Tipo de estrategia:** Reversión a la media en zonas de soporte/resistencia
**Instrumentos:** Índices — US30 (Dow Jones), NAS100 (Nasdaq), SPX500 (S&P 500)
**Timeframe de análisis:** H4 (4 horas) — identificación de zonas
**Timeframe de ejecución:** H1 (1 hora) — confirmación y entrada
**Lookback para zonas:** 200 velas H4 (~33 días de mercado)
**Estilo:** Swing trading / Intraday (operaciones de horas a pocos días)

---

## 2. Identificación de Zonas de Soporte y Resistencia (H4)

### 2.1. ¿Qué es una zona válida?

Una zona NO es un precio exacto. Es una **banda horizontal** definida por el rango completo (high a low, es decir mechas incluidas) de la vela H4 que produjo el **rechazo más fuerte** del precio en ese nivel.

### 2.2. Criterios para marcar una zona

1. **Rechazo fuerte inicial:** Se identifica una vela H4 con un rechazo claro — una vela con mecha pronunciada que indica que la oferta (en resistencia) o la demanda (en soporte) defendió agresivamente ese nivel.

2. **Validación con 2do toque:** La zona se activa como operable cuando el precio **regresa al nivel al menos una segunda vez** y muestra nuevamente rechazo. El primer toque crea la zona, el segundo la valida.

3. **Definición del ancho de la zona:**
   - **Borde superior de la zona** = High de la vela H4 que produjo el rechazo más fuerte
   - **Borde inferior de la zona** = Low de la vela H4 que produjo el rechazo más fuerte
   - La zona incluye **la vela completa**: cuerpo + mechas

4. **Contexto adicional — Rangos:** La estrategia funciona especialmente bien en mercados en rango (consolidación), donde el precio oscila entre un soporte y una resistencia claramente definidos. También funciona en tendencia cuando el precio retestea zonas previas.

### 2.3. Reglas algorítmicas para detección de zonas

Para traducir "rechazo fuerte" a código, se define:

**Método de detección de swing highs/lows en H4:**
- Un **swing high** es una vela H4 cuyo high es mayor que los highs de las N velas anteriores y N velas posteriores (parámetro configurable, sugerido: N=3)
- Un **swing low** es una vela H4 cuyo low es menor que los lows de las N velas anteriores y N velas posteriores

**Filtro de "rechazo fuerte":**
- La vela del swing debe tener una **mecha significativa** relativa a su rango total:
  - Para soporte: `mecha_inferior / rango_total >= 0.40` (40% o más del rango es mecha inferior)
  - Para resistencia: `mecha_superior / rango_total >= 0.40`
  - Donde `rango_total = high - low`, `mecha_inferior = min(open, close) - low`, `mecha_superior = high - max(open, close)`
- Alternativa: vela envolvente que reversa la dirección previa

**Agrupación en zonas:**
- Si dos swing highs/lows están a menos de X puntos de distancia entre sí (parámetro: `zone_merge_distance`), se consideran parte de la **misma zona**
- El ancho de la zona se toma de la vela con mayor rango (high - low) entre las que forman el cluster, es decir, la del rechazo más fuerte

**Validación (mínimo 2 toques):**
- Un "toque" se cuenta cuando el precio (high o low de una vela H4) entra en la zona
- Se requieren mínimo 2 toques separados por al menos 5 velas H4 (~20 horas) para evitar contar velas consecutivas como toques separados

### 2.4. Parámetros configurables (strategy_params.yaml)

```yaml
zone_detection:
  timeframe: H4
  lookback_candles: 200               # ~33 días
  swing_strength: 3                    # Velas a cada lado para confirmar swing
  min_wick_ratio: 0.40                 # Mínimo 40% de mecha para "rechazo fuerte"
  zone_merge_distance: 150             # Puntos para agrupar swings en misma zona (ajustar por instrumento)
  min_touches: 2                       # Toques mínimos para validar zona
  min_touch_separation: 5              # Velas H4 mínimas entre toques
  max_zones_active: 6                  # Máximo de zonas activas simultáneas (3 soporte + 3 resistencia)
```

---

## 3. Señales de Entrada (H1)

### 3.1. Condición previa obligatoria

El precio en H1 debe estar **dentro de una zona válida** de S/R (según la definición de la Sección 2) o haberla **perforado recientemente**.

### 3.2. Tipo A — Entrada estándar (Rechazo en zona)

**Condición:** El precio llega a la zona y se forma una vela de confirmación en H1.

**Velas de confirmación válidas (H1):**

1. **Pin Bar / Martillo (soporte):**
   - Mecha inferior >= 2x el tamaño del cuerpo
   - Cierre en la mitad superior del rango de la vela
   - Cierre dentro o por encima de la zona de soporte

2. **Pin Bar invertido / Estrella fugaz (resistencia):**
   - Mecha superior >= 2x el tamaño del cuerpo
   - Cierre en la mitad inferior del rango de la vela
   - Cierre dentro o por debajo de la zona de resistencia

3. **Envolvente alcista (soporte):**
   - Vela verde cuyo cuerpo envuelve completamente el cuerpo de la vela anterior
   - La vela anterior es roja (bajista)
   - El cierre está dentro o por encima de la zona

4. **Envolvente bajista (resistencia):**
   - Vela roja cuyo cuerpo envuelve completamente el cuerpo de la vela anterior
   - La vela anterior es verde (alcista)
   - El cierre está dentro o por debajo de la zona

### 3.3. Tipo B — Entrada premium (Falso quiebre / Liquidity Sweep)

**Esta es la entrada de mayor probabilidad según el operador.**

**Condición:** La **mecha** de una vela H1 **perfora la zona** (penetra más allá del soporte por debajo o de la resistencia por encima) pero la **vela cierra de vuelta dentro de la zona o del lado correcto**. El rechazo es intra-vela — la demanda u oferta absorbe la ruptura tan rápidamente que no permite un cierre más allá de la zona. Esto indica un barrido de liquidez (liquidity sweep) seguido de absorción.

**Reglas algorítmicas:**

**Variante B1 — Rechazo intra-vela (más común y señal más fuerte):**
1. La **mecha** de una vela H1 penetra más allá de la zona:
   - Para soporte: el low de la vela está **por debajo** del borde inferior de la zona
   - Para resistencia: el high de la vela está **por encima** del borde superior de la zona
2. El **cierre** de esa misma vela está **dentro de la zona o del lado opuesto a la penetración**:
   - Para soporte: el cierre está por encima del borde inferior de la zona
   - Para resistencia: el cierre está por debajo del borde superior de la zona
3. La vela muestra fuerza de reversión: cuerpo >= 40% de su rango total, cerrando en la dirección de la reversión (verde para soporte, roja para resistencia)

**Variante B2 — Rechazo en 2 velas (menos común):**
1. Una vela H1 penetra la zona con su mecha o cierre
2. La **siguiente vela H1** cierra con fuerza de vuelta dentro/encima/debajo de la zona (según dirección)
3. La vela de regreso tiene cuerpo >= 50% de su rango total

**Nota:** La Variante B1 es la preferida y la de mayor probabilidad. La B2 es aceptable pero con menor convicción. En ambos casos, la clave es que el precio demuestra que la ruptura fue falsa y hay absorción clara de oferta/demanda.

**Parámetros:**
```yaml
false_breakout:
  # Variante B1 (intra-vela, preferida)
  b1_min_body_ratio: 0.40              # Cuerpo >= 40% del rango de la vela
  b1_min_penetration: 0                # Cualquier penetración más allá de la zona cuenta

  # Variante B2 (2 velas, aceptable)
  b2_max_candles_to_return: 2          # Máximo la siguiente vela H1
  b2_min_body_ratio: 0.50              # Vela de regreso con cuerpo >= 50% del rango

  # Prioridad
  prefer_b1_over_b2: true              # Si hay señal B1, no esperar B2
```

### 3.4. Dirección de la operación

- **LONG (compra):** Cuando el precio toca/perfora una zona de SOPORTE y se confirma rechazo alcista
- **SHORT (venta):** Cuando el precio toca/perfora una zona de RESISTENCIA y se confirma rechazo bajista

### 3.5. Parámetros de entrada

```yaml
entry:
  timeframe: H1
  valid_patterns:
    - pin_bar
    - engulfing
    - false_breakout
  min_wick_to_body_ratio: 2.0          # Para pin bars: mecha >= 2x cuerpo
  entry_price: close                   # Se entra al cierre de la vela de confirmación
  entry_type: market                   # Orden a mercado al cierre de vela H1
```

---

## 4. Gestión de Riesgo

### 4.1. Stop Loss

**Regla:** El SL se coloca a **80 puntos** más allá del extremo de la zona de S/R.

- **Para LONG:** SL = `borde_inferior_zona - 80 puntos`
- **Para SHORT:** SL = `borde_superior_zona + 80 puntos`

**Justificación:** Los 80 puntos de margen permiten absorber los falsos quiebres (que son frecuentes y deseables en esta estrategia) sin ser sacado prematuramente.

```yaml
stop_loss:
  method: zone_edge_plus_buffer
  buffer_points: 80                    # Puntos más allá de la zona
```

### 4.2. Take Profit

**Regla:** El TP se coloca en la **siguiente zona de S/R opuesta**, ligeramente antes del borde para asegurar ejecución.

- **Para LONG:** TP = `borde_inferior_zona_resistencia_siguiente - offset`
- **Para SHORT:** TP = `borde_superior_zona_soporte_siguiente + offset`

```yaml
take_profit:
  method: next_zone_with_offset
  offset_points: 20                    # Puntos antes de la zona opuesta
  min_rr_ratio: 1.5                    # No tomar trades con R:R menor a 1.5:1
```

**Filtro de calidad:** Si el ratio riesgo/beneficio (distancia al TP / distancia al SL) es menor a 1.5:1, la operación **NO se toma**. Esto filtra setups donde las zonas están demasiado cerca.

### 4.3. Tamaño de posición

**Regla:** Riesgo máximo de **0.5% del balance** por operación.

```
Lotes = (Balance × 0.005) / (Distancia_SL_en_puntos × Valor_punto)
```

Donde `Valor_punto` depende del instrumento y del broker (se obtiene dinámicamente de MT5).

```yaml
position_sizing:
  risk_per_trade_pct: 0.005            # 0.5%
  max_simultaneous_trades: 3           # Máximo 3 operaciones abiertas
  max_risk_total_pct: 0.015            # Máximo 1.5% de riesgo total expuesto
```

### 4.4. Regla de exposición máxima

- Máximo **3 operaciones abiertas simultáneamente**
- Riesgo total expuesto no debe superar **1.5% del balance** (3 × 0.5%)
- Si hay correlación entre instrumentos (ej: US30 y SPX500 suelen moverse juntos), máximo **2 operaciones en instrumentos correlacionados**

---

## 5. Reglas FTMO (Hardcoded — No modificables)

Estas reglas se implementan como **guardarraíles irrompibles** en el código. El bot NO opera si alguna se violaría.

```yaml
ftmo_rules:
  # Reglas de drawdown
  max_daily_loss_pct: 0.04             # 4% (usamos 4% como límite interno, FTMO permite 5%)
  max_total_loss_pct: 0.08             # 8% (usamos 8% como límite interno, FTMO permite 10%)
  safety_margin_daily: 0.01            # 1% de margen de seguridad (trigger: dejamos de operar al 4%)
  safety_margin_total: 0.02            # 2% de margen de seguridad (trigger: dejamos de operar al 8%)

  # Reglas operativas
  max_server_requests_per_day: 500     # Muy por debajo del límite de 2000
  max_open_orders: 10                  # Muy por debajo del límite de 200
  min_trading_days: 4                  # Mínimo 4 días con operaciones en el período

  # Reglas de horario
  close_before_weekend: true           # Cerrar posiciones antes del cierre del viernes
  weekend_close_minutes_before: 30     # Cerrar 30 minutos antes del cierre del mercado
  avoid_high_impact_news: true         # No abrir nuevas posiciones 15 min antes/después de noticias de alto impacto
  news_blackout_minutes: 15            # Minutos de blackout alrededor de noticias

  # Challenge específico (ajustar según tipo de cuenta)
  profit_target_phase1_pct: 0.10       # 10% objetivo Phase 1
  profit_target_phase2_pct: 0.05       # 5% objetivo Phase 2
```

### 5.1. Lógica de protección diaria

```
Al inicio de cada día (medianoche hora de Praga, CET):
  → Registrar balance_inicio_dia = balance actual
  → Calcular limite_diario = balance_inicio_dia × max_daily_loss_pct

Durante el día:
  → perdida_actual = (posiciones cerradas hoy) + (P&L flotante de posiciones abiertas)
  → Si perdida_actual >= limite_diario:
       → CERRAR TODAS las posiciones abiertas
       → BLOQUEAR nuevas operaciones hasta el siguiente día
       → Enviar alerta por Telegram
```

### 5.2. Lógica de protección total

```
En todo momento:
  → drawdown_total = balance_inicial_cuenta - equity_actual
  → Si drawdown_total >= balance_inicial × max_total_loss_pct:
       → CERRAR TODAS las posiciones
       → BLOQUEAR el bot completamente
       → Enviar alerta URGENTE por Telegram
       → Requiere intervención manual para reactivar
```

---

## 6. Gestión de Operaciones Abiertas

### 6.1. Trailing Stop (opcional, desactivado por defecto)

```yaml
trailing_stop:
  enabled: false                       # Desactivado inicialmente, activar tras backtest
  activation_rr: 1.0                   # Activar trailing cuando R:R alcanzado >= 1:1
  trail_distance_points: 100           # Distancia de trailing en puntos
```

### 6.2. Break Even

```yaml
break_even:
  enabled: true
  trigger_rr: 1.0                      # Mover SL a break even cuando se alcanza 1:1 R:R
  offset_points: 10                    # SL se mueve a entrada + 10 puntos (para cubrir spread/comisión)
```

---

## 7. Filtros Adicionales

### 7.1. Filtro de horario de mercado

```yaml
trading_hours:
  # Operar solo durante horarios de mayor liquidez
  us30:
    sessions:
      - start: "08:00"                 # Apertura Londres
        end: "11:00"
        timezone: "America/New_York"
      - start: "09:30"                 # Apertura NY
        end: "16:00"
        timezone: "America/New_York"
  nas100:
    sessions:
      - start: "09:30"
        end: "16:00"
        timezone: "America/New_York"
  spx500:
    sessions:
      - start: "09:30"
        end: "16:00"
        timezone: "America/New_York"
```

### 7.2. Filtro de spread

```yaml
spread_filter:
  max_spread_points: 30                # No operar si el spread supera 30 puntos
```

### 7.3. Filtro de volatilidad mínima

```yaml
volatility_filter:
  min_atr_h4_periods: 14              # ATR de 14 períodos en H4
  min_atr_multiplier: 0.5             # El ATR debe ser al menos 50% de su media de 50 períodos
  # Esto evita operar en mercados completamente muertos
```

---

## 8. Notificaciones (Telegram)

```yaml
notifications:
  telegram:
    enabled: true
    events:
      - zone_detected                  # "Nueva zona de soporte detectada en US30: 44,850 - 44,920"
      - price_approaching_zone         # "US30 acercándose a zona de soporte 44,850 (distancia: 50 pts)"
      - signal_generated               # "Señal LONG en US30: Pin bar en soporte 44,850"
      - trade_opened                   # "COMPRA US30 @ 44,870 | SL: 44,770 | TP: 45,200 | Riesgo: 0.5%"
      - trade_closed                   # "US30 CERRADO @ 45,190 | P&L: +320 pts | +$160"
      - break_even_moved               # "US30: SL movido a break even (44,880)"
      - daily_summary                  # Resumen diario de P&L
      - risk_alert                     # "⚠️ Drawdown diario al 3.2% — Quedan $180 hasta el límite"
      - emergency_stop                 # "🚨 LÍMITE DE PÉRDIDA ALCANZADO — Bot detenido"
```

---

## 9. Logging y Auditoría

Cada operación se registra con:

```yaml
trade_log_fields:
  - timestamp_signal                   # Cuándo se generó la señal
  - timestamp_entry                    # Cuándo se ejecutó la entrada
  - timestamp_exit                     # Cuándo se cerró
  - instrument                         # US30, NAS100, SPX500
  - direction                          # LONG / SHORT
  - entry_type                         # Tipo A (estándar) o Tipo B (falso quiebre)
  - pattern_detected                   # pin_bar, engulfing, false_breakout
  - zone_upper                         # Borde superior de la zona
  - zone_lower                         # Borde inferior de la zona
  - zone_touches                       # Número de toques de la zona
  - entry_price
  - stop_loss_price
  - take_profit_price
  - position_size_lots
  - risk_amount_usd
  - risk_reward_ratio
  - exit_price
  - exit_reason                        # TP hit, SL hit, break_even, manual, weekend_close, risk_limit
  - pnl_points
  - pnl_usd
  - pnl_pct_of_balance
  - daily_drawdown_after               # Drawdown diario después de esta operación
  - total_drawdown_after               # Drawdown total después de esta operación
```

---

## 10. Flujo Completo del Bot (Pseudocódigo)

```
CADA 5 MINUTOS (o al cierre de vela H1):

  1. VERIFICAR GUARDARRAÍLES FTMO
     → Si drawdown diario >= 4%: BLOQUEAR, alertar, salir
     → Si drawdown total >= 8%: BLOQUEAR, alertar, salir
     → Si es viernes y faltan < 30 min para cierre: cerrar todo, salir
     → Si hay noticia de alto impacto en próximos 15 min: no abrir nuevas, salir

  2. GESTIONAR POSICIONES ABIERTAS
     → Verificar si alguna alcanzó 1:1 R:R → mover a break even
     → Verificar SL/TP (MT5 lo gestiona, pero verificar estado)

  3. ACTUALIZAR ZONAS DE S/R
     → Obtener últimas 200 velas H4
     → Detectar swing highs/lows con rechazo fuerte
     → Agrupar en zonas
     → Filtrar zonas con >= 2 toques
     → Mantener máximo 6 zonas activas

  4. BUSCAR SEÑALES DE ENTRADA (solo si hay capacity para nuevas operaciones)
     → Si ya hay 3 operaciones abiertas: salir
     → Para cada zona activa:
       → ¿El precio actual está dentro o cerca de la zona?
       → Si sí: verificar última vela H1 cerrada
         → ¿Es pin bar, envolvente, o hubo falso quiebre?
         → Si sí: calcular SL, TP, tamaño de posición
           → ¿R:R >= 1.5?
           → ¿Spread <= máximo?
           → ¿Riesgo total con nueva operación <= 1.5%?
           → Si todo OK: EJECUTAR OPERACIÓN
           → Enviar notificación por Telegram
           → Registrar en log

  5. ENVIAR RESUMEN DIARIO (si es fin de sesión)
```

---

## 11. Parámetros por Instrumento

Los puntos de buffer (SL, merge distance, etc.) deben ajustarse por instrumento debido a diferencias en volatilidad y valor del punto:

```yaml
instruments:
  US30:
    symbol_mt5: "US30"                 # Verificar nombre exacto en el broker
    sl_buffer_points: 80
    zone_merge_distance: 150
    tp_offset_points: 20
    max_spread_points: 30
    point_value: 1.0                   # Obtener dinámicamente de MT5
    typical_zone_width: 100-300        # Rango típico para validación

  NAS100:
    symbol_mt5: "NAS100"
    sl_buffer_points: 100              # Más volátil que US30
    zone_merge_distance: 200
    tp_offset_points: 30
    max_spread_points: 40
    point_value: 1.0
    typical_zone_width: 100-400

  SPX500:
    symbol_mt5: "SPX500"
    sl_buffer_points: 30               # Menos volátil
    zone_merge_distance: 50
    tp_offset_points: 10
    max_spread_points: 15
    point_value: 1.0
    typical_zone_width: 30-100
```

> **NOTA:** Los valores de `point_value`, `symbol_mt5` y spreads deben verificarse con el broker específico (ej: BlackBull Markets según las capturas). Los nombres de los símbolos pueden variar entre brokers.

---

## 12. Plan de Backtesting

Antes de operar en vivo (incluso en demo FTMO):

```yaml
backtest:
  data_source: "MT5 histórico o proveedor externo"
  period: "2024-01-01 a 2026-03-01"    # Mínimo 2 años
  instruments: [US30, NAS100, SPX500]
  metrics_a_evaluar:
    - win_rate                         # Objetivo: >= 45%
    - profit_factor                    # Objetivo: >= 1.5
    - max_drawdown                     # Debe ser < 8% (cumplir FTMO)
    - max_daily_drawdown               # Debe ser < 4%
    - avg_rr_ratio                     # Debe ser >= 1.5:1
    - sharpe_ratio                     # Objetivo: >= 1.0
    - total_trades                     # Suficientes para significancia estadística (>100)
    - avg_trades_per_month             # Para verificar que cumplimos 4 días mínimos FTMO
    - max_consecutive_losses           # Para dimensionar psicológicamente
    - recovery_factor                  # Net profit / max drawdown
```

---

## Historial de Cambios

| Versión | Fecha | Cambios |
|---------|-------|---------|
| 1.0 | 2026-03-26 | Versión inicial basada en entrevista con el operador |

---

*Este documento es la referencia maestra para el desarrollo del bot. Cualquier cambio en la estrategia debe reflejarse aquí antes de modificar el código.*
