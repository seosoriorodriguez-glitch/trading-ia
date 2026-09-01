# S/R Pivot — Soportes y Resistencias por pivotes (LuxAlgo)

Estrategia de rebote en niveles de soporte/resistencia detectados por pivotes.
Equivalente Python del indicador Pine *"Support and Resistance Levels with Breaks"*
de LuxAlgo, con el repintado eliminado.

**Estado: validada en backtest. No está en producción.**

---

## Config validada

```
Detección   : H1, pivote 15/15, 5 niveles totales, vida infinita
Zona        : 30 pts desde el nivel
Entrada     : al toque de mecha del borde cercano, sin confirmación
              1 trade por nivel, 1 posición simultánea, 24h
Salida      : SL 100 pts más allá del nivel | TP = RR 2.0 fijo
Riesgo      : 0.5% fijo | Costos: 4 pts (2 spread + 2 slippage)
```

Riesgo = zona + SL = **130 pts**. Soporte → compra, resistencia → venta.

## Resultados — US30.cash, ene-2024 a ago-2026 (32 meses, 0.5%, cuenta $10k)

| | Operaciones | WR | PF | Total | Mensual | maxDD |
|---|---|---|---|---|---|---|
| In-sample 2024-2025 | 382 | 38.0% | 1.17 | +20.6% | +0.88% | 6.3% |
| **Out-of-sample 2026** | 127 | 42.5% | **1.41** | +15.5% | **+2.17%** | 4.2% |
| **TOTAL** | **511** | **39.1%** | **1.23** | **+36.6%** | **+1.20%** | **6.3%** |

t = +2.21 · 59% de meses ganadores · racha perdedora máxima 9 · ~16 operaciones/mes

**El out-of-sample salió mejor que el in-sample con la config sin tocar.**

### Correlación con OB London

**rho = −0.07** (18 meses solapados). Combinando ambas a 0.5%:

| | Retorno | Mensual | maxDD | Meses+ |
|---|---|---|---|---|
| Solo S/R | +21.0% | +1.17% | −5.0% | 56% |
| Solo OB London | +101.2% | +5.62% | −8.1% | 67% |
| **Las dos** | **+122.2%** | **+6.79%** | **−4.7%** | **78%** |

Más retorno y **menos drawdown que OB sola**. (maxDD medido sobre agregados
mensuales: la mejora relativa es válida, el nivel absoluto está subestimado.)

---

## ⚠️ Dos trampas de lookahead — leer antes de tocar nada

### 1. El indicador Pine repinta

`pivothigh(15,15)` necesita **15 velas posteriores** para confirmarse, +1 por el
`[1]` del Pine. El nivel no existe hasta **pivote + 16 barras**. El
`offset=-(rightBars+1)` del plot lo dibuja hacia atrás, por eso en el chart
parece que estuvo ahí desde el principio.

| | WR | E/trade | t |
|---|---|---|---|
| Con lookahead (nivel desde la vela del pivote) | **94.8%** | +1.369R | **+51.4** |
| Sin lookahead (`activation_index = i + right + 1`) | 42.5% | +0.061R | +0.88 |

Un `pivothigh` **es por definición** el máximo de las 15 velas siguientes.
Vender ahí con lookahead es dinero gratis.

### 2. Filtros que usan la vela en curso

Un filtro de tendencia comparando `close[k]` contra `ema[k]` — el cierre de la
vela **en la que se entra** — dio:

| | n | WR | E/trade | t |
|---|---|---|---|---|
| Con el bug | 181 | 58.6% | +0.700R | +6.35 |
| **Con la vela cerrada anterior** | 161 | 32.9% | **−0.070R** | −0.62 |

Estaba seleccionando velas que *iban a cerrar* a favor.

**Y lo más importante: el out-of-sample PASÓ con el bug puesto** (+0.657R,
t=3.49, 7 de 7 meses positivos). La partición IS/OOS protege del sobreajuste,
**no del lookahead** — el bug está en ambas mitades. Son dos fallas distintas
que necesitan dos chequeos distintos.

**Regla: cualquier filtro nuevo usa la vela cerrada anterior. Y si un número se
ve demasiado bien, primero buscar el lookahead.**

---

## Bitácora de factores probados

Barrido OFAT (un factor a la vez) sobre in-sample 2024-2025, riesgo 0.4%.
Línea base = +0.71%/mes, PF 1.17.

| # | Factor | Probado | Resultado | Decisión |
|---|---|---|---|---|
| 1 | **TF de detección** | M15, M30, H1, H2, H4 | Solo H1 positivo. M15 −0.66%, M30 −0.49%, H2 −0.32%, H4 −0.10% | **H1** ⚠️ pico aislado |
| 2 | **Niveles activos** | 2,3,5,8,12,20 | Sin estructura: 2→+0.23, 5→+0.71, 12→+0.45, 20→+0.66 | **5** |
| 3 | **Vida del nivel** | ∞, 24, 48, 100, 200, 400 | ∞ = 100 = 200 = 400. Acortar a 24-48 empeora | **∞** |
| 4 | **Agrupar cercanos** | 0,20,40,60,100 pts | +0.15%/mes IS → **falló OOS** | **No usar** |
| 5 | **Ancho de zona** | 0,10,20,30,40,60 | Meseta 20-40, sin ganador claro | **30** |
| 6 | **Stop loss** | 40..200 pts | Pico en 80 (+0.97%) vs 100 (+0.71%). 40-60 y 130+ malos | **100** ⚠️ ver pendientes |
| 7 | **RR** | 1.0..4.0 | Meseta 2.0-2.5. Pico en 4.0 es ruido (3.0 cae a +0.49%) | **2.0** |
| 8 | **Tipo de TP** | RR fijo vs siguiente nivel | Siguiente nivel: PF 1.27 IS → **0.94 OOS** | **RR fijo** |
| 9 | **Trailing** | 3 arranques × 3 distancias | Perjudica en las 9. El agresivo (0.5R/50pts) da PF 0.78 | **No usar** |
| 10 | **Parciales** | 3 niveles × 3 porcentajes | Neutro o peor. Salir en 0.5R destruye el edge | **No usar** |
| — | **Filtro de tendencia EMA** | 20,30,40,50,60,80,100,200,400 | **No aporta** (con la vela cerrada anterior) | **No usar** |
| — | **Sesión horaria** | 24h, 10-17, 10-23, 15-23, 16-23, 8-17 | 24h gana. La ventana de London da **negativo** | **24h** |
| — | **Reentrada en el nivel** | sí/no | Reentrar es mucho peor (−0.159R, t=−3.24) | **No** |

### Combinaciones probadas out-of-sample

| Config | In-sample | Out-of-sample |
|---|---|---|
| **A — spec original** | +0.71%/mes · PF 1.17 | **+1.74%/mes · PF 1.41** ✅ |
| B — + TP siguiente nivel | +1.08%/mes · PF 1.27 | −0.29%/mes · PF 0.94 ❌ |
| D — B + agrupar 20pts | +1.09%/mes · PF 1.29 | −1.22%/mes · PF 0.75 ❌ |
| E — D + zona 40 | +1.05%/mes · PF 1.29 | −1.13%/mes · PF 0.77 ❌ |

**Las tres "mejoras" fallaron fuera de muestra. La config sin tocar fue la única
que aguantó.** El TP al siguiente nivel parecía el más creíble (estable en todo
el rango de min-RR, PF 1.25-1.29) y colapsó a 0.94.

---

## Presupuesto de muestra

El out-of-sample (2026) **ya se miró 4 veces**. Cada mirada lo desgasta.

- Quedan ~1-2 miradas antes de que deje de ser validación real.
- Después de eso hay que esperar datos nuevos (sep-2026 en adelante) para
  verificar cualquier cambio.
- Correr `run_backtest.py` **sin** `--oos` para explorar; con `--oos` solo para
  la validación final de un candidato ya congelado.

---

## Pendientes

1. **SL=80** — dio +0.97%/mes vs +0.71% de SL=100 en in-sample, con curva limpia
   (40-60 malos, pico en 80, 130+ malos). **No validado OOS.** Es el único
   candidato con forma creíble que queda sin probar.
2. **DAX** — hay datos en `velas m1/` (`DE40_M5_2024...`, `GER40.cash_M5_2026...`).
   No mejora la estrategia pero duplicaría la muestra y el retorno si la
   correlación de rachas sigue baja.
3. **Bot live** — no existe. Para free trial hay que portar `levels.py` +
   la lógica de entrada a un monitor tipo `order_block_london/live/`.
4. **ATR en vez de puntos fijos** (zona y SL) — nunca probado. Es lo que hace
   robusto a OB London ante cambios de volatilidad.

---

## Uso

```bash
# explorar (solo in-sample)
python strategies/sr_pivot/backtest/run_backtest.py

# probar una variante
python strategies/sr_pivot/backtest/run_backtest.py --set sl_points=80

# validación final (gasta muestra)
python strategies/sr_pivot/backtest/run_backtest.py --oos

# otro riesgo
python strategies/sr_pivot/backtest/run_backtest.py --risk 0.004
```

Datos en `C:\Users\sosor\OneDrive\Documentos\velas m1\`. Los M1 se concatenan
automáticamente. `check_timezone()` avisa si el pico de rango no cae en 16-17h
(servidor UTC+3).
