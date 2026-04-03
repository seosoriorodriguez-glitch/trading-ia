# Protocolo de Registro de Trades

## Cómo registrar un trade nuevo

### Lo que vos hacés:
1. **Cuando entra la orden** → screenshot del chart M5 con el OB visible → guardar como `setup.png`
2. **Cuando cierra** → screenshot del chart con el resultado → guardar como `result.png`
3. **Enviarme a Claude**:
   - Las 2 imágenes del chart
   - El screenshot de la tabla de MT5
   - Decirme: *"registra el trade"* e indicar si es **US30** o **BTCUSD**

### Lo que yo hago:
1. Creo la carpeta en la ruta correcta según el activo:
   - US30:   `journal/trades/US30/winners/YYYY-MM-DD_NNN_LONG/SHORT_US30/`
   - BTCUSD: `journal/trades/BTCUSD/winners/YYYY-MM-DD_NNN_LONG/SHORT_BTCUSD/`
2. Creo el `trade.md` con todos los datos extraídos de la tabla
3. Actualizo el PROTOCOLO y el GENERAL.md del activo correspondiente

---

## US30 — Tabla resumen

| # | Fecha | Dir | Entry | SL | TP | Cierre | PnL $ | R | Duración | Balance |
|---|-------|-----|-------|----|----|--------|-------|---|----------|---------|
| 001 | 2026-04-01 | LONG  | 46561.49 | 46513.11 | 46729.11 | 46751.11 | +$197.20 | +3.92R | 6 min  | $10,197.20 |
| 002 | 2026-04-01 | LONG  | 46496.49 | 46434.11 | 46710.86 | 46718.80 | +$180.07 | +3.55R | 23 min | $10,377.27 |
| 003 | 2026-04-01 | SHORT | 46753.76 | 46824.09 | 46561.07 | 46560.30 | +$174.11 | +2.75R | 47 min | $10,551.38 |
| 004 | 2026-04-01 | LONG  | 46590.30 | 46553.80 | 46715.80 | 46550.80 | -$54.91  | -1.08R | 3 min  | $10,496.47 |
| 005 | 2026-04-01 | SHORT | 46626.30 | 46694.59 | 46451.30 | 46696.30 | -$59.50  | -1.02R | 8 min  | $10,436.97 |
| 006 | 2026-04-02 | SHORT | 46108.40 | 46147.71 | 45978.96 | 46159.90 | -$68.50  | -1.31R | 22 min | $10,368.47 |
| 007 | 2026-04-02 | SHORT | 46138.40 | 46187.71 | 45971.71 | 46188.90 | -$52.52  | -1.02R | 5 min  | $10,315.95 |

### US30 — Stats acumuladas

| Métrica         | Valor      |
|----------------|------------|
| Total trades   | 7          |
| Wins           | 3          |
| Losses         | 4          |
| Win Rate       | 42.9%      |
| Total PnL $    | +$315.95   |
| Total PnL %    | +3.16%     |
| Avg R ganado   | +3.41R     |
| Avg R perdido  | -1.11R     |
| Max DD diario  | 1.21%      |
| Balance actual | $10,315.95 |

---

## BTCUSD — Tabla resumen

| # | Fecha | Dir | Entry | SL | TP | Cierre | PnL $ | R | Duración | Balance |
|---|-------|-----|-------|----|----|--------|-------|---|----------|---------|
| 001 | 2026-04-02 | LONG  | 66403.87 | 66219.11 | 66752.12 | 66756.70 | +$991.45  | ~+1.9R | 41 min   | $100,991.45 |
| 002 | 2026-04-02 | SHORT | 66689.60 | 66904.42 | 66292.48 | 66322.20 | +$900.13  | ~+1.9R | 2h 43min | $101,891.58 |
| 003 | 2026-04-02 | LONG  | 66354.81 | 66137.69 | 66766.97 | 66111.81 | -$578.34  | -1.15R | 7 min    | $101,313.24 |
| 004 | 2026-04-02 | LONG  | 66238.89 | 66072.38 | 66536.33 | 66513.88 | +$888.22  | +1.65R | ~4 min   | $102,201.46 |

### BTCUSD — Stats acumuladas

| Métrica         | Valor        |
|----------------|--------------|
| Total trades   | 4            |
| Wins           | 3            |
| Losses         | 1            |
| Win Rate       | 75.0%        |
| Total PnL $    | +$2,201.46   |
| Total PnL %    | +2.20%       |
| Avg R ganado   | ~+1.82R      |
| Avg R perdido  | -1.15R       |
| Max DD diario  | 0.57%        |
| Balance actual | $102,201.46  |
