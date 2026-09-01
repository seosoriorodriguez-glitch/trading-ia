# CONTRATO DE BACKTEST — leer ANTES de correr o interpretar cualquier backtest

> **Por qué existe este archivo**: hay 7 motores de backtest y ~100 scripts sueltos en
> este repo. Cada uno con supuestos distintos. Cuatro veces se sacaron conclusiones
> falsas por usar el motor equivocado o datos con la granularidad equivocada.
> Si vas a backtestear algo de este repo, o a interpretar un resultado ajeno,
> **primero verificá que cumpla este contrato.**

---

## 1. Motor canónico

| Estrategia | Motor | Config |
|---|---|---|
| OB London — **referencia/checksum** | `strategies/order_block/backtest/backtester.py` → `OrderBlockBacktester` | `LONDON_PARAMS` |
| OB London — **el más fiel al live** | `strategies/order_block/backtest/backtester_limit_orders.py` → `OrderBlockBacktesterLimitOrders` | `LONDON_PARAMS` |
| S/R Pivot | `strategies/sr_pivot/backtest/backtester.py` | `strategies/sr_pivot/backtest/config.py` |

**El nombre `backtester_limit_orders.py` engaña: su llenado es de orden STOP.**
Coloca la orden en el borde de la zona (`zone_high` para long, `zone_low` para short,
líneas 190/195) y la llena cuando el precio VUELVE a ese nivel (`candle_high >=
entry_price`, línea 314). Eso es exactamente lo que hace el bot live
(`order_executor.py:44` → `ORDER_TYPE_BUY_STOP`). No lo descartes por el nombre.

**No usar `backtester_stop.py`.** Lo escribí después y es peor: copia la mecánica de
pendiente pero toma `entry_price` de `check_entry`, que devuelve el **cierre de la
vela** en vez del borde de la zona. Por eso el 96% de sus pendientes se llenan —
están al precio de mercado.

### Dónde entra cada motor (la diferencia real)

| | Señal | Precio de entrada | Riesgo |
|---|---|---|---|
| `backtester.py` (canónico) | cierre a un lado de la zona | **cierre de la vela** | variable |
| `backtester_stop.py` | ídem | **cierre de la vela** | variable |
| `backtester_limit_orders.py` | cierre **dentro** de la zona | **borde de la zona** | altura de zona + buffer, fijo |
| **BOT LIVE** (`ob_monitor.py:160`) | cierre **dentro** de la zona | **borde de la zona** | fijo |

### Fidelidad medida contra 126 operaciones live (jun-ago 2026, 50 días)

| Motor | n | trades/día | WR | PF | E/trade |
|---|---|---|---|---|---|
| Canónico | 179 | 3.58 | 38.5% | 1.41 | +0.275R |
| `backtester_stop` (defectuoso) | 171 | 3.42 | 40.9% | 1.51 | +0.325R |
| **`backtester_limit_orders`** | **144** | **2.88** | 41.7% | 1.56 | **+0.352R** |
| **LIVE REAL** | **126** | **2.68** | — | — | **+0.363R** |

El motor de bordes queda a **3% del live** en expectativa y a 7.5% en ritmo de
operaciones. Ese resto se explica por lo que el backtest no modela: blackout de
noticias, cierre de viernes y filtro de spread.

Los números de referencia de la sección 4 son del **canónico**. No los recalcules con
otro motor o el checksum deja de detectar motores rotos.

Los scripts en la raíz del repo (`backtest_*.py`, `run_*.py`) y en `journal/analysis/`
son **exploratorios y de una sola vez**. No son fuente de verdad.

---

## 2. Condiciones obligatorias

### 2.1 Granularidad de salidas: **M1. No negociable.**

Cuando una vela contiene SL y TP a la vez el motor tiene que asumir uno, y la
convención conservadora es asumir SL. Con velas gruesas eso pasa seguido.

Medido sobre US30, misma config, misma ventana (jun-2025 a may-2026), **solo
cambiando el TF de ejecución**:

| Ejecución | n | WR | PF | E/trade | Sesgo |
|---|---|---|---|---|---|
| **M1** | 826 | 36.7% | **1.30** | +0.204R | — |
| M2 | 806 | 34.7% | 1.19 | +0.136R | −1.9 pp |
| M3 | 785 | 32.9% | 1.10 | +0.074R | −3.8 pp |
| M5 | 655 | 30.4% | **0.98** | −0.011R | −6.3 pp |

**Con ejecución M5 la estrategia se ve perdedora (PF 0.98) cuando en realidad da
PF 1.30.** El error siempre apunta hacia abajo: te hace descartar cosas que funcionan.

Si solo hay datos gruesos, aplicar la corrección (~+0.034R por punto de WR) y
**declararlo como estimación**, nunca como medición.

### 2.2 Detección: M5. Ejecución: M1.

El bot live detecta OBs sobre 350 velas M5 y verifica señales en M1
(`ob_monitor.py:27` → `_M5_HISTORY = 350`). El backtest tiene que recibir
`(df_higher=M5, df_lower=M1)`.

### 2.3 Concurrencia: **`max_simultaneous_trades = 2`**

Verificado en `signals.py:192`. Es el error que más veces se cometió.

2024, US30, M1 exits:

| maxsim | Trades | PF | Retorno 0.5% |
|---|---|---|---|
| 1 | 506 | 1.25 | +43.5% |
| **2 (correcto)** | **709** | **1.23** | **+56.8%** |
| 3 | 777 | 1.21 | +56.7% |

### 2.4 Zona horaria: servidor **UTC+3**

La sesión London es `10:00-17:00` **hora de servidor**. Si los datos vienen en otro
huso, el filtro corre sin dar error y mide horas equivocadas.

**Verificación obligatoria**: el pico de volumen (o de rango) por hora tiene que caer
en **16-17h**. Ahí está la apertura del cash de NY (09:30 ET). Si cae en otro lado,
los datos están en otro huso y hay que corregir antes de seguir.

### 2.5 Costos: 4 puntos por operación

`avg_spread_points: 2` + `slippage_points: 2`. El spread real medido en los datos del
bróker es ~2 pts (171-215 en unidades de 0.01).

---

## 3. Chequeo de sanidad contra el live

**El bot live corre a 2.68 operaciones/día** — 126 trades en 47 días hábiles con la
config actual (jun-ago 2026). Sobre la serie completa abr-ago: 2.80/día.

> No usar muestras cortas para esto: 9 días daban 2.89/día y el error se propaga
> a todo el chequeo.

El live tiene filtros que el backtest **no** modela — blackout de noticias, cierre de
viernes, spread máximo, y órdenes STOP que nunca se llenan. Todos **quitan** trades.

> **Por lo tanto un backtest debería dar ~2.7 trades/día o más. Por debajo de 2.4
> hay un problema real: datos incompletos o un filtro de más.**

Es el chequeo más rápido y atrapa la mayoría de los errores groseros. Un análisis
externo que daba ~2.2 trades/día resultó estar corriendo con `max_simultaneous=1`.

Rangos observados con el motor canónico: 2.74 (2024), 3.13 (2025), 3.56 (2026). La
actividad varía entre años, así que un 2.74 no es alarma; un 2.2 sí.

### Validación trade por trade contra el live (jun-ago 2026)

Contrastando las 126 operaciones reales contra el motor STOP:

- **114 de 126 (90%)** de tus trades live tienen contraparte en el backtest
- En los emparejados: backtest **+0.369R/trade** vs live real **+0.363R/trade**
  → cuando toman las mismas operaciones, **dan el mismo resultado**
- Quedan **50 trades del backtest que el live no tomó** (30% de más)

Esos 50 están repartidos parejo (23-44% en toda hora y todo día, sin clusters, solo
4 en ventana de noticias). Esa uniformidad descarta un filtro y apunta a **latencia
de ejecución**: el bot evalúa una vez por minuto sobre la vela ya cerrada
(`ob_monitor.py:134` → `df_m1.iloc[-2]`); si el precio ya atravesó el nivel, MT5
rechaza el STOP por nivel inválido y el trade nunca existe.

**Ningún backtest modela eso.** Asumí un ~25-30% menos de operaciones en vivo que en
backtest, y no lo trates como un bug. Los 50 huérfanos rendían +0.21R contra +0.37R
de los ejecutados: la ejecución real filtró las peores.

---

## 4. Números de referencia (checksum)

Motor canónico, `LONDON_PARAMS` sin modificar, M1 real, riesgo 0.5%, cuenta $10k.
Datos: `US30_M1_202401020100_202605201838.csv` (+ `US30.cash_M1_2026...` para 2026).

| Año | Trades | WR | PF | sumaR | Retorno | maxDD |
|---|---|---|---|---|---|---|
| 2024 | 709 | 35.4% | 1.23 | +113.5R | +56.8% | 14.9% |
| 2025 | 808 | 34.2% | 1.17 | +95.0R | +47.5% | 20.1% |
| 2026 (a ago) | 562 | 37.2% | 1.33 | +125.3R | +62.6% | 14.8% |

**Si tu motor no reproduce esto dentro de ±5%, no es fiel al live.**
Correr `python validate_engine.py` para chequearlo automáticamente.

Años con datos gruesos (estimaciones, no mediciones):
2022 (M3): +22.7R crudo → ~+0.157R/trade corregido ·
2023 jun-dic (M2): +25.9R crudo, PF 1.09. **2023 es el año más flojo de la serie.**

---

## 5. Los cuatro errores que ya se cometieron

Todos produjeron números convincentes y falsos. Todos fueron detectados solo porque
alguien fue a buscarlos.

**1. Repintado de indicador con pivotes.**
`pivothigh(15,15)` necesita 15 velas *posteriores*. Usar el nivel desde la vela del
pivote dio **WR 94.8%, t=+51**. Sin lookahead: WR 42.5%. Un pivot high *es por
definición* el máximo de las velas siguientes.

**2. Filtro que usa la vela en curso.**
Comparar `close[k]` contra `ema[k]` — el cierre de la vela en la que se entra — dio
**+0.700R, t=6.35**. Con la vela cerrada anterior: **−0.070R**. Estaba seleccionando
velas que iban a cerrar a favor.
→ **Y pasó la validación out-of-sample** (+0.657R, 7 de 7 meses positivos). La
partición IS/OOS protege del sobreajuste, **no del lookahead**: el bug está en las
dos mitades. Son fallas distintas que necesitan chequeos distintos.

**3. Ejecución en M5.** Ver 2.1. Convirtió PF 1.30 en PF 0.98.

**4. `max_simultaneous_trades = 1`.** Ver 2.3. Recortó el retorno de +56.8% a +43.5%
y el conteo de trades por debajo del ritmo real del live.

**5. Entrar al cierre de la vela en vez de al borde de la zona.**
El bot live pone la orden en `zone_high`/`zone_low` y espera; `signals.py:234` usa
`entry_price = candle_close`. No es lo mismo: cambia el precio, el riesgo (fijo vs
variable) y cuántas operaciones sobreviven. Diferencia medida: +0.275R contra
+0.352R. Escribí un motor "STOP" que heredó este error sin darme cuenta, y lo
documenté como el más fiel. Lo era el que ya existía.

**6. Poner una orden STOP del lado equivocado del precio.**
Una STOP va MÁS ALLÁ del precio actual. Si el nivel queda del otro lado es una LIMIT
y se llena a mejor precio que el de mercado: dinero inventado. En un test de zonas
VWAP eso daba **PF 10.31 y t=+29**. Con la guarda correcta, PF 1.11.
Regla: antes de armar, verificar `precio > entrada` (venta) o `precio < entrada` (compra).

---

## 6. Checklist antes de creer un resultado

- [ ] ¿Usa el motor canónico de la tabla 1?
- [ ] ¿Las salidas se resuelven en **M1**? (si no: el resultado subestima, cuánto está en 2.1)
- [ ] ¿`max_simultaneous_trades = 2`?
- [ ] ¿El pico de rango horario cae en **16-17h**? (zona horaria)
- [ ] ¿Da **más de 2.89 trades/día**?
- [ ] ¿Los costos son 4 pts/trade?
- [ ] ¿Algún filtro o indicador usa la vela **en curso** en vez de la cerrada anterior?
- [ ] Si el número se ve demasiado bien: **buscar el lookahead antes de festejar.**

---

## 7. Presupuesto de muestra

Los datos de validación fuera de muestra se gastan. Cada vez que se optimiza mirando
un período, ese período deja de servir para validar.

- **OB London**: los parámetros salieron de una optimización de 518 días (oct-2024 a
  abr-2026) más el corte de sesión elegido sobre live abr-may 2026. 2022, 2023 y 2024
  son out-of-sample genuinos respecto a eso.
- **S/R Pivot**: 2026 ya se miró 4 veces. Quedan 1-2 miradas útiles.

**La mejor evidencia no es ningún backtest: son las 267 operaciones live** (abr-ago
2026, +21% a 0.5%, p=0.012 corrigiendo por agrupación diaria). Ejecución real, spread
real, órdenes STOP reales. Cuando dos backtests no coinciden, gana el que reproduce
el ritmo y el resultado del live.
