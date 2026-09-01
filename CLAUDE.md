# Instrucciones para Claude

## ⚠️ ANTES DE CUALQUIER BACKTEST — OBLIGATORIO

**Leer `BACKTEST_SPEC.md` antes de correr, escribir o interpretar cualquier backtest
de este repo.** Hay 7 motores y ~100 scripts sueltos con supuestos distintos, y ya se
sacaron cuatro conclusiones falsas por usar el equivocado.

Lo mínimo, sin excepciones:
- Motor canónico: `strategies/order_block/backtest/backtester.py` + `LONDON_PARAMS`
- **Salidas resueltas en M1** (con M5 la estrategia se ve perdedora: PF 0.98 vs 1.30 real)
- **`max_simultaneous_trades = 2`** (con 1 el retorno cae de +56.8% a +43.5%)
- Zona horaria servidor UTC+3: el pico de rango horario debe caer en 16-17h
- Ningún filtro puede usar la vela **en curso**, solo la cerrada anterior

Verificar con `python validate_engine.py` — compara contra números de referencia y
falla si el motor no es fiel al live.

Si un resultado se ve demasiado bien, buscar el lookahead **antes** de reportarlo.
Los scripts en la raíz y en `journal/analysis/` son exploratorios, no fuente de verdad.

## Proyecto
Dos bots de trading automatizado Order Block:
- **US30.cash** — FTMO Challenge $10,000 — RR 3.5 — sesión NY 13:30-23:00 UTC+3
- **BTCUSD**    — FTMO Free Trial $100,000 — RR 2.0 — 24/7

---

## Registro de trades (journal)

Cuando el usuario diga **"registra el trade"** e indique si es **US30** o **BTCUSD**:

1. Leer `journal/PROTOCOLO.md` para ver el último número de trade del activo y balance actual
2. Extraer de la tabla MT5: ticket, dirección, entry, SL, TP, cierre, PnL, volumen, duración
3. Crear carpeta según activo y resultado:
   - US30 ganó:   `journal/trades/US30/winners/YYYY-MM-DD_NNN_LONG/SHORT_US30/`
   - US30 perdió: `journal/trades/US30/losers/YYYY-MM-DD_NNN_LONG/SHORT_US30/`
   - BTC ganó:    `journal/trades/BTCUSD/winners/YYYY-MM-DD_NNN_LONG/SHORT_BTCUSD/`
   - BTC perdió:  `journal/trades/BTCUSD/losers/YYYY-MM-DD_NNN_LONG/SHORT_BTCUSD/`
4. Crear `trade.md` en esa carpeta usando la plantilla `journal/_template/trade.md`
5. Calcular: R obtenido = PnL_pts / risk_pts, duración en minutos
6. Actualizar la sección del activo correspondiente en `journal/PROTOCOLO.md`
7. Actualizar `journal/results/US30/GENERAL.md` o `journal/results/BTCUSD/GENERAL.md` según corresponda

### Datos a extraer de la tabla MT5
- Time (entrada y cierre)
- Ticket
- Symbol
- Type (buy/sell)
- Volume (lotes)
- Price (entry)
- S/L
- T/P
- Precio de cierre
- Profit

### Reglas
- El usuario siempre indicará si el trade es de **US30** o **BTCUSD**
- NO modificar ningún archivo del bot live (`strategies/order_block/live/` ni `strategies/order_block_btc/live/`)
- El balance actualizado = balance anterior + PnL del trade
- Si el usuario solo manda imágenes sin decir "registra el trade", analizar y comentar pero NO crear archivos
- Numeración independiente por activo: US30 tiene su propio contador, BTCUSD tiene el suyo
