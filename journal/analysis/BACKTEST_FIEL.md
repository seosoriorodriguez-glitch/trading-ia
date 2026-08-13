# BACKTEST FIEL AL LIVE — spec canónico (OB London / US30)

> **Regla dura:** un backtest solo vale si replica EXACTO lo que hace el bot en vivo.
> Params distintos = número sin sentido, y el error casi siempre **apunta hacia abajo**
> (te hace descartar cosas que funcionan). Errores ya cometidos: `maxsim=1` en vez de 2,
> entrada a mercado en vez de STOP, salidas resueltas en M5 en vez de M1, zona horaria sin convertir.

## El ÚNICO backtester fiel
`journal/analysis/bt_stop_entry.py` — replica la entrada **STOP en el borde** del live.

**NUNCA usar `journal/analysis/ob_multiasset.py` para validar** — ese entra a **mercado al cierre de la vela**
(`entry_price = candle_close`), que NO es lo que hace el live. Solo sirve para comparación/exploración, jamás para decidir.

## Cómo entra el LIVE (lo que hay que replicar)
1. **M5** detecta Order Blocks (zonas).
2. Una **vela M1 cierra DENTRO de la zona** (en sesión) → se coloca una orden **STOP en el borde**:
   - Alcista (demanda) → **BUY STOP en `zone_high`**.
   - Bajista (oferta) → **SELL STOP en `zone_low`**.
3. El STOP se **llena solo si el precio alcanza el borde** antes de que la zona se destruya (M5 cierra al otro lado) o expire. Si no, se cancela (no hay trade).
4. **SL/TP se resuelven vela a vela en M1** (SL primero si ambos caen en el mismo minuto).

`bt_stop_entry.py` hace exactamente esto (fill en M1 líneas ~91-93, salidas en M1 líneas ~97-104). Verificado.

## Parámetros canónicos (de `strategies/order_block_london/backtest/config.py`)
| Parámetro | Valor |
|---|---|
| **target_rr** | **2.5** |
| **max_simultaneous_trades** | **2** |
| min_rr_ratio | 1.2 |
| consecutive_candles | 4 |
| zone_type | half_candle |
| max_atr_mult | 3.5 |
| min_impulse_pct | 0.0 |
| Sesión London | **10:00–17:00 hora broker**, skip 15 min |
| Riesgo | 0.5% (para el %; escalar al riesgo real de la cuenta) |
| min_risk / buffer / max_risk | escalados por la mediana del rango M5 (med×0.765 / med×1.276 / med×15.3) |

## Comando fiel
```
python journal/analysis/bt_stop_entry.py <asset> london 2.5 <spread> 2
```
- arg1 asset (clave en ASSETS), arg2 sesión (`london`), arg3 RR=**2.5**, arg4 spread, arg5 maxsim=**2**.
- El default de maxsim en el script es **2** (no pasar 1).

## Zona horaria de la data (CRÍTICO)
El broker (FTMO/IC Markets) corre en **EET con DST de US**: **UTC+2 invierno / UTC+3 verano**,
con transiciones de US (2° domingo de marzo → 1° domingo de noviembre). La sesión `10:00-17:00` está en ESA hora.

La data de **Dukascopy viene en UTC** → hay que convertirla a hora broker antes de usarla:
- offset = **+2** base, **+3** durante DST de US (`[2°dom-mar 07:00 UTC, 1°dom-nov 06:00 UTC)`).
- Si no se convierte, la sesión London agarra otras velas → backtest falso.

Verificado alineando por precio contra la data `_icm_` real (verano +3h error 1.4pts, invierno +2h error 6.8pts, 20-mar +3h → confirma DST de US, no europeo).

## Dónde sacar data histórica (M1)
- **Dukascopy** (gratis, profundo): instrumento **`USA30.IDX/USD`**. Bajar con `npx dukascopy-node@latest -i usa30idxusd -from AAAA-01-01 -to (AAAA+1)-01-01 -t m1 -f csv -p bid`.
- Solo se necesita **M1**; el M5 se deriva resampleando (`resample('5min')`, open=first/high=max/low=min/close=last, dropna).
- Convertir a hora broker (arriba) antes de guardar como `data/US30_dukasAAAA_M1.csv` y `_M5.csv`.

## Resultados medidos (fieles, maxsim=2, RR 2.5, riesgo 0.5%, data Dukascopy) — referencia
| Año | Régimen | Trades | WR | PF | Retorno | Max DD |
|---|---|---|---|---|---|---|
| 2020 | crash COVID + recup. | 719 | 34.2% | 1.22 | +54.3% | 13.8% |
| 2021 | bull | 715 | 32.9% | 1.11 | +28.5% | 11.8% |
| 2022 | bear (−9%) | 778 | 33.3% | 1.17 | +46.2% | 13.7% |
| 2023 | choppy/plano | 734 | 32.3% | 1.06 | +17.1% | 29.1% |
| 2024 | recuperación | 748 | 34.5% | 1.17 | +45.7% | 12.6% |
| 2025 | bull | 753 | 34.5% | 1.21 | +56.1% | 11.5% |

**6 de 6 años positivos y robustos, en TODOS los regímenes (crash, bull, bear, choppy). Promedio ~+41%/año a 0.5%.**
WR consistente 33-35%, PF 1.06-1.22 (edge fino pero persistente). El **DD es la restricción** (11.5-29.1%; 2023 el peor):
- FTMO (límite 10%): bajar riesgo a ~0.2% (peor DD ~12%).
- Darwinex (sin DD duro): riesgo moderado + componer. A 0.2% → ~+16.5%/año promedio, ~2.5× en 6 años, DD máx ~12%.
- El live rinde algo menos (slippage, feed FTMO≠Dukascopy). El futuro puede traer un régimen peor que 2023 → por eso riesgo bajo.

## Checklist antes de confiar en CUALQUIER número
- [ ] ¿Entrada **STOP en el borde** (no a mercado/cierre)?
- [ ] ¿**maxsim=2**?
- [ ] ¿**RR 2.5**?
- [ ] ¿Salidas SL/TP resueltas en **M1** (no M5)?
- [ ] ¿Detección de zonas en **M5**?
- [ ] ¿Zona horaria de la data **convertida a hora broker** (EET/US-DST)?
- [ ] ¿Conteo de trades **varía** por año (no constante = artefacto de cap)?

Si alguna falla, el número **NO vale**.
