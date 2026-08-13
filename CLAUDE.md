# Instrucciones para Claude

## Proyecto
Dos bots de trading automatizado Order Block:
- **US30.cash** — FTMO Challenge $10,000 — RR 3.5 — sesión NY 13:30-23:00 UTC+3
- **BTCUSD**    — FTMO Free Trial $100,000 — RR 2.0 — 24/7

---

## ⚠️ BACKTEST FIEL AL LIVE (regla dura — leer SIEMPRE antes de backtestear)

**Antes de correr o interpretar CUALQUIER backtest, leer `journal/analysis/BACKTEST_FIEL.md`.**
Un backtest con params distintos al live NO significa nada y el error suele apuntar hacia abajo
(te hace descartar cosas que funcionan). Ya pasó varias veces (maxsim mal, entrada a mercado, salidas en M5).

**El ÚNICO backtester fiel es `journal/analysis/bt_stop_entry.py`.**
NUNCA usar `ob_multiasset.py` para validar (entra a **mercado al cierre**, no con STOP → NO es el live).

**Parámetros canónicos del OB London (US30) — DEBEN coincidir SIEMPRE:**
| Parámetro | Valor live | |
|---|---|---|
| Entrada | **STOP en el borde** (M1 cierra dentro → BUY STOP `zone_high` / SELL STOP `zone_low`). Nunca a mercado. |
| Detección zonas | **M5** | consecutive_candles 4, zone_type half_candle, max_atr_mult 3.5, min_impulse 0 |
| Entrada + salidas (SL/TP) | **M1** (SL/TP se resuelven en cada vela M1, SL primero) |
| **RR (target_rr)** | **2.5** | min_rr_ratio 1.2 |
| **max_simultaneous_trades** | **2** | ← el default del script es 2; NO pasar 1 |
| Sesión London | **10:00–17:00 hora broker**, skip 15 min |
| Zona horaria data | broker = **EET con DST de US** (UTC+2 inv / UTC+3 ver, transición 2°dom-mar → 1°dom-nov). Data Dukascopy viene en UTC → convertir. Si no, la sesión agarra otras velas. |
| Riesgo | 0.5% para el % (escalar al riesgo real) |

**Comando fiel:** `python journal/analysis/bt_stop_entry.py <asset> london 2.5 <spread> 2`

**Checklist antes de confiar en un número de backtest:** ¿entrada STOP (no mercado)? ¿maxsim=2? ¿RR 2.5?
¿salidas resueltas en M1? ¿detección en M5? ¿zona horaria de la data convertida a hora broker? Si alguna falla → el número NO vale.

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
