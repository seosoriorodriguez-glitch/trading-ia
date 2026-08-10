# Investigación de Estrategias — Dow Jones (US30)

**Contexto:** trading de cuentas fondeadas (prop). Objetivo: diversificar la estrategia OB
(que es el "gem" rápido + robusto) con otra de edge distinto para el Dow (o máx. Oro/Plata).
**Método (usuario):** conceptos price action → scripts públicos TradingView (LuxAlgo) →
backtest → afinar. **Rigor:** fiel al live (nada de fill-gate), robustez por mitades
(PF>1 en 1ª Y 2ª mitad), DD real, costo real (spread 4).

Datos: `data/US30_icm_M5_518d.csv` (99,935 velas M5, Oct 2024 - Mar 2026) + M1 500k.

---

## Resumen ejecutivo

| Estrategia | Edge | Retorno realista (0.5%) | Max DD | Robusta | Veredicto |
|---|---|---|---|---|---|
| **OB London** | Reacción en zonas | Fuerte (el gem) | controlado | ✅ (live) | ✅ **EN PRODUCCIÓN** |
| **FVG** | Reacción en gaps | Espejismo → breakeven/pierde | 64-260% | ❌ | 🚫 **ARCHIVADA** |
| **ORB** | Momentum (ruptura) | ~11%/año | **6%** | ✅ | 🟡 Diversificador lento usable |
| **Liq Sweep + Wyckoff** | Reversión (barrido) | ~4.6%/año | **8.2%** | ✅ | 🟡 Diversificador lento usable |
| **Breaker Block** | Continuación | pierde | 63-108% | ❌ | 🔴 **ARCHIVADA (sin edge)** |

**Patrón aprendido:** robusto en el Dow ≈ modesto (~5-15%/año). Rápido ≈ frágil/espejismo.
La OB siendo rápida Y robusta es un gem raro.

### OB en OTROS ACTIVOS (motor real dual M5+M1, data ICM, robustez por mitades)
Regla dura: SIEMPRE M5+M1, nunca M5-only. Params de escala (buffer/min/max_risk/spread)
recalibrados por activo según rango M5 mediano. Script: `journal/analysis/ob_multiasset.py`.

| Activo | PF (costo real) | 1a/2a | Robusta | Retorno/año 0.5% | DD | Veredicto |
|---|---|---|---|---|---|---|
| 🥇 **ORO XAUUSD** | **1.37** | 1.28/1.46 | ✅ SÍ | ~+194% | 22% | 🟢 **SEGUNDO MERCADO REAL** |
| US2000 Russell | 1.09 | 0.97/1.23 | ❌ | +31% | 33% | 🟡 marginal |
| BTCUSD | 1.06 | 1.27/0.88 | ❌ | +17% | 30% | 🔴 no robusto (+comisión) |
| CADJPY | 0.81 | 0.85/0.78 | ❌ | -44% | 79% | 🔴 pierde (costo>rango) |

**ORO CONFIRMADO:** aguanta costo duplicado (0.20→0.40) y sigue robusto. La OB transfiere a
instrumentos volátiles con rango >> costo (US30, oro; mean-reversion en zonas). Falla en JPY
tranquilos (costo relativo alto) y en no-robustos (BTC, Russell).

**Desglose sesión ORO (@0.40, 517d) — las TRES robustas:**
| Sesión | PF | 1a/2a | Retorno/año 0.5% | DD | Ret/DD |
|---|---|---|---|---|---|
| London | 1.35 | 1.24/1.46 | +82% | 12.0% | 6.8 |
| **NY** ⭐ | 1.36 | 1.25/1.49 | +142% | 15.5% | 9.2 (mejor) |
| both | 1.37 | 1.28/1.46 | +194% | 22.0% | 8.8 |

**PRUEBA DE CONFIANZA (backtest no falla):** US30 (probado en vivo) por el MISMO runner nuevo →
NY +84.7%/DD18.9% vs histórico conocido +87.6%/DD17.1% = reproduce. London +65%/DD8.2% robusto.
El motor es de fiar → el oro también.

**⚠️ DD oro a 0.5% pasa el límite FTMO (10%). Config recomendada: ORO sesión NY, riesgo 0.25%
→ DD ~8%, ~+42%/año.** (DD real suele salir < backtest; US30 vivo -8% vs backtest 18.9%.)
Pendiente: re-descargar ICM hasta HOY (data actual termina 2026-04) y testear GBPJPY/XAGUSD/CADCHF.
Ver [[backtest-procedure]].

**INSIGHT CLAVE (validado con test OB-reacción vs Breaker-continuación, mismo método M5):**
El **Dow es MEAN-REVERTING en las zonas** — las zonas AGUANTAN (fadearlas = OB reacción → PF 1.03
robusta) y las rupturas FALLAN/whipsaw (perseguirlas = Breaker continuación → PF 0.88 pierde).
Por eso la **OB (reacción) está alineada con el carácter del Dow** y el **momentum es débil aquí**.
Buscar otra "rápida + robusta" es difícil porque la OB ya captura el edge principal del Dow.
Los edges de REACCIÓN funcionan; los de CONTINUACIÓN/momentum no (o son modestos).

---

## 1. OB London — EN PRODUCCIÓN (referencia)
- Order Block: vela opuesta + 4 de impulso, entrada STOP en el borde, RR 2.5, riesgo 0.5%.
- Sesión London 10:00-17:00 servidor (corte 10:00 NY). Corre en FTMO ($10k, $100k) y Darwinex (WS30).
- **Validada en vivo, rentable** (usuario reportó +21% / DD -8% en 3 meses). Rápida + robusta.
- Es el "crusher" — nada que optimizar por ahora.

## 2. FVG (Fair Value Gap) — ARCHIVADA (no viable)
- US30 M5, detección LuxAlgo, entrada STOP conservative, RR 2, riesgo 0.5%.
- **El +305%/PF1.47 del backtest era ARTEFACTO del "fill-gate"** (mantener varias STOP y elegir
  llenar solo 1 — imposible en vivo; MT5 llena todo lo que toca).
- **Versiones desplegables (max 1/2/3, cap/rearm, RR 2-5):** breakeven en el mejor caso (PF 1.00),
  1ª mitad perdedora, **DD catastrófico 64-260%** a 0.5%. Regime-dependiente.
- Bug live: contaba solo posiciones llenas (no las STOP pendientes) → 6 simultáneas → reventó el challenge.
- **Aprendizaje clave:** distinguir edge real de espejismo de simulación. Ver [[project_fvg_strategy]].
- Scripts: `journal/analysis/fvg_*.py`. Código: `strategies/fair_value_gap/`.

## 3. ORB (Opening Range Breakout) — DIVERSIFICADOR usable
- Rango de los primeros 15 min de la sesión NY → ruptura (M5 cierra sobre/bajo el rango).
- SL al otro extremo + buffer, RR 2.5-3, 1 trade/día.
- **Óptimo (rango 15 min, RR 2.5-3):** PF 1.21, **+16%/518d** (~11%/año), **DD 6%**, ROBUSTA (ambas mitades).
- Momentum → diversifica la OB reactiva. DD bajo → se puede escalar (0.75% → ~17%/año, DD ~9%).
- Modesto pero REAL y seguro. **Sirve como ingreso estable en fondeo, no para challenges rápidos.**
- Código: `strategies/opening_range_breakout/`. Script: `journal/analysis/orb_sweep.py`.

## 4. Liquidity Sweep + Wyckoff — DIVERSIFICADOR usable
- LuxAlgo "Liquidity Sweeps" (Only Wicks): pivot(len,len); barrido bajista `high>PH and close<PH`
  → SHORT; alcista `low<PL and close>PL` → LONG. SL tras la mecha + buffer.
- **Óptimo: len 150 (liquidez MAYOR), RR 5, filtro Wyckoff (volumen ≤ promedio 20).**
  - PF 1.12, **+13R (~4.6%/año a 0.5%)**, **DD 8.2%**, ROBUSTA (1.06/1.18). ~120 trades (0.2/día).
- Hallazgos: swings chicos (len 5-20) = ruido (perdía PF 0.80). Swings grandes (150) = liquidez real.
  RR alto ayuda. **Wyckoff (volumen bajo = sin fuerza opuesta) bajó el DD de 12.8% → 8.2%.**
- Modesto pero REAL y usable. Reversión → algo correlacionado con OB (verificar).
- Scripts: `journal/analysis/liq_sweep*.py`, `liq_sweep_v2.py`. (Wyckoff vol: `/tmp/wyck*.py`).

---

## Próximos conceptos a explorar (lista viva)
- [ ] **Modo CONTINUACIÓN del sweep** (LuxAlgo "Outbreaks & Retest") — momentum, quizás más rápido.
- [ ] **Breaker Blocks** (ya hay terminal MT5_BREAKERBLOCKS) — continuación tras OB roto.
- [ ] **BOS / CHoCH** (market structure) — trend-following.
- [ ] Mejor entrada del sweep (entrar en el retest, no en el cierre).
- [ ] Probar los diversificadores (ORB, Sweep) en Oro (XAUUSD).

## Cómo explotar
Los diversificadores (ORB, Liq Sweep+Wyckoff) son robustos pero lentos → ideales como
**ingreso estable en cuentas ya fondeadas** o para armar un **portafolio de robustos-lentos**
(varios juntos = retorno decente + curva suave). Para **pasar challenges rápido**, la OB sigue
siendo la carta (aplicable a otro instrumento si transfiere).
