# Protocolo de Registro de Trades

## Cómo registrar un trade nuevo

### Lo que vos hacés:
1. **Cuando entra la orden** → screenshot del chart M5 con el OB visible → guardar como `setup.png`
2. **Cuando cierra** → screenshot del chart con el resultado → guardar como `result.png`
3. **Enviarme a Claude**:
   - Las 2 imágenes del chart
   - El screenshot de la tabla de MT5 (como el que mandaste hoy)
   - Decirme: *"registra el trade"*

### Lo que yo hago:
1. Creo la carpeta `YYYY-MM-DD_NNN_LONG/SHORT_US30`
2. Creo el `trade.md` con todos los datos extraídos de la tabla
3. Vos arrastras las imágenes a la carpeta

---

## Tabla resumen (actualizo con cada trade)

| # | Fecha | Dir | Entry | SL | TP | Cierre | PnL $ | R | Duración | Balance |
|---|-------|-----|-------|----|----|--------|-------|---|----------|---------|
| 001 | 2026-04-01 | LONG | 46561.49 | 46513.11 | 46729.11 | 46751.11 | +$197.20 | +3.92R | 6 min | $10,197.20 |
| 002 | 2026-04-01 | LONG  | 46496.49 | 46434.11 | 46710.86 | 46718.80 | +$180.07 | +3.55R | 23 min | $10,377.27 |
| 003 | 2026-04-01 | SHORT | 46753.76 | 46824.09 | 46561.07 | 46560.30 | +$174.11 | +2.75R | 47 min | $10,551.38 |
| 004 | 2026-04-01 | LONG  | 46590.30 | 46553.80 | 46715.80 | 46550.80 | -$54.91  | -1.08R | 3 min  | $10,496.47 |
| 005 | 2026-04-01 | SHORT | 46626.30 | 46694.59 | 46451.30 | 46696.30 | -$59.50  | -1.02R | 8 min  | $10,436.97 |

---

## Stats acumuladas

| Métrica         | Valor |
|----------------|-------|
| Total trades   | 5     |
| Wins           | 3     |
| Losses         | 2     |
| Win Rate       | 60%   |
| Total PnL $    | +$436.97 |
| Total PnL %    | +4.37% |
| Avg R ganado   | +3.41R |
| Avg R perdido  | -1.05R |
| Max DD diario  | 0.56% |
| Balance actual | $10,436.97 |
