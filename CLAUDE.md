# Instrucciones para Claude

## Proyecto
Bot de trading automatizado Order Block sobre US30.cash (FTMO challenge $10,000).
Estrategia: detección OBs en M5, entrada BUY/SELL STOP en M1, RR 3.5, riesgo 0.5%/trade.

---

## Registro de trades (journal)

Cuando el usuario diga **"registra el trade"** y adjunte imágenes:

1. Leer `journal/PROTOCOLO.md` para ver el último número de trade y balance actual
2. Extraer de la tabla MT5: ticket, dirección, entry, SL, TP, cierre, PnL, volumen, duración
3. Crear carpeta: `journal/trades/winners/YYYY-MM-DD_NNN_LONG/SHORT_US30/` si ganó, `journal/trades/losers/YYYY-MM-DD_NNN_LONG/SHORT_US30/` si perdió
4. Crear `trade.md` en esa carpeta usando la plantilla `journal/_template/trade.md`
5. Calcular: R obtenido = PnL_pts / risk_pts, duración en minutos
6. Actualizar la tabla resumen y stats acumuladas en `journal/PROTOCOLO.md`
7. Actualizar `journal/results/GENERAL.md`: balance, stats, dirección, R:R, tabla de trades, equity curve

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
- NO modificar ningún archivo del bot live (`strategies/order_block/live/`)
- El balance actualizado = balance anterior + PnL del trade
- Si el usuario solo manda imágenes sin decir "registra el trade", analizar y comentar pero NO crear archivos
