# Manual — Kovatia Invest (dashboard de trading)

Guía completa del funcionamiento, métricas y **todos los procedimientos** del panel.
Complemento: `PROCEDIMIENTOS.md` (mismos temas, foco en los SQL puntuales).

> **Principio rector: 100% ADITIVO.** El dashboard **solo lee**. Nunca toca los bots, las
> estrategias en producción, ni sus configs. Si algo del panel se rompe, los bots siguen operando
> intactos.

---

## 1. Arquitectura (el flujo de la data)

```
   [VPS 24/7]                         [Nube]                    [Tú]
 ┌─────────────┐   cada 60s     ┌──────────────┐          ┌──────────────┐
 │ MT5 + EAs   │ ──lee(RO)──▶  │  Colector    │ ──sube──▶ │  Supabase    │ ◀─lee─ │ Panel (web) │
 │ (FTMO/Dwx/  │                │ collector.py │           │ (Postgres)   │        │  Next.js    │
 │  demo)      │                └──────────────┘           └──────────────┘        └─────────────┘
 └─────────────┘
```

- **Bots/EAs**: corren en terminales MT5 en el VPS (24/7). Son la fuente de verdad.
- **Colector** (`panel/collector/collector.py`): cada 60 s se conecta a cada terminal, **lee el
  historial** (solo lectura), y sube a Supabase. **Nunca escribe en MT5.**
- **Supabase**: base de datos (Postgres) donde vive todo el histórico, para siempre.
- **Panel** (`panel/web/`, Next.js): lee de Supabase, calcula las métricas y las muestra.

---

## 2. El colector — qué hace en cada corrida (cada 60 s)

Por cada bot del `config.json`:
1. Se conecta al terminal (por `terminal_path`) y lee `account_info` (balance/equity reales).
2. **Rotación**: si el login actual ≠ el registrado, **actualiza** el `account` del bot (no salta).
   Porque rotas la cuenta en el mismo terminal (mismo bot).
3. Guarda un **snapshot** de balance/equity → tabla `account_snapshots`.
4. Lee los `deals` de los últimos **5 días** (`LOOKBACK_DAYS`):
   - Los de tipo **BALANCE** (depósitos/retiros) → `balance_ops` (**sin filtro de magic**, no se escapan).
   - El resto, filtrados por **magic** del bot → se reconstruyen en `trades` (posición IN/OUT).
5. Por cada trade nuevo, baja las **velas M5** alrededor → `trade_candles` (para los gráficos).
6. Sube todo con **dedup** por `(account, ticket)` → **nunca duplica, nunca borra**.

**Parámetros:** `POLL_SECONDS = 60`, `LOOKBACK_DAYS = 5`.
**Variables de entorno** (en el VPS): `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`.

---

## 3. Tablas en Supabase

| Tabla | Qué guarda | Clave / dedup |
|---|---|---|
| `bots` | catálogo de cuentas (id, symbol, account, magic, initial_balance, rr, session, active) | `id` |
| `trades` | cada operación cerrada (entry/exit, SL/TP, PnL, R, dirección, motivo) | `(account, ticket)` |
| `account_snapshots` | balance/equity real en cada corrida | por `ts` |
| `balance_ops` | depósitos (+) y retiros (−) que graba MT5 | `(account, ticket)` |
| `trade_candles` | velas M5 de cada trade (para el gráfico) | `ticket` |

---

## 4. Cómo se calcula el RETORNO (la métrica clave)

```
Retorno($) = (balance actual − inicial) + retirado(bruto) − depósitos extra
Retorno(%) = Retorno($) / initial_balance
```

- **balance − inicial** = el **colchón** vivo (ganancia que sigue en la cuenta).
- **retirado (bruto)** = todo lo que sacaste de la cuenta (sin repartición 80/20; el bruto es lo que
  mide la estrategia). Se acumula por `bot_id`, **sobrevive rotaciones**.
- **depósitos extra** = lo depositado **por encima del fondeo inicial** (ej. el colchón que llevas a
  la cuenta nueva). **Se resta** para no contarlo doble (ya está en el balance).

**Ejemplo real (US30 Live 10k):** balance $10.163,51 · inicial $10.000 · retirado $392 · depósito
extra $62,81 (colchón traído) → **($163,51 + $392 − $62,81) = $492,70 = +4,93%**.

Esta fórmula es **robusta**: da el retorno correcto sin importar cuántos trades alcanzó a capturar
el colector, ni cuántas veces rotaste la cuenta.

---

## 5. Secciones del panel

| Página | Ruta | Qué muestra |
|---|---|---|
| **Vista general** | `/` | KPIs del portafolio real, rentabilidad por cuenta (+ fila Total), equity, calendario, grupos FTMO/Darwinex, alertas. **Excluye demo.** |
| **En vivo** | `/vivo` | Sesión de London de US30 y DAX con velas M5, **zonas OB** (misma detección del bot) y las operaciones del día. En vivo mientras corre (refresca 60 s); al terminar queda **congelada** para analizarla y se reinicia sola al abrir la próxima London. |
| **FTMO** | `/ftmo` | KPIs + card por cada cuenta FTMO. |
| **Darwinex** | `/darwinex` | KPIs + card por cada cuenta Darwinex. |
| **Lab · Demo** | `/demo` | Forward-tests en demo. **Independiente**: no cuenta para el portafolio real. |
| **Trades** | `/trades` | Últimas operaciones con **gráfico de velas** (entry/SL/TP), por cuenta. |
| **Alertas** | `/alertas` | Alertas activas + reglas configuradas. |
| **Detalle** | `/bot/[id]` | KPIs avanzados, equity vs media, R por operación, calendario, tabla de ops. |

**Categorías** (inferidas del `id` del bot):
- contiene `darwinex` → **Darwinex**
- contiene `demo` o `lab` → **Lab · Demo** (independiente)
- si no → **FTMO**

**Hora:** todo se muestra en **hora Chile** (el panel resta el offset del servidor MT5 y formatea a
`America/Santiago`). **No toca los datos ni la hora del servidor.**

---

## 6. Métricas explicadas

- **WR** (win rate) y **WR reciente** (últimas 30 ops).
- **Breakeven WR** = `1 / (1 + RR)`. Es el WR mínimo para no perder. Ej: RR 2.5 → 28,6% · RR 2.0 →
  33,3% · RR 3.5 → 22,2%. Si tu WR está **bajo** el breakeven, la estrategia pierde.
- **PF** (profit factor) = ganancias / pérdidas. >1 gana.
- **Expectancy** = $ (y R) esperado por operación.
- **RRR** = ratio riesgo/beneficio real medio.
- **Drawdown** = cuánto estás **bajo tu pico** de equity (% del inicial). Normal tener algo aunque ganes.
- **Pérdida máx (límite 10%)** = lo más que bajaste **bajo el inicial** (regla dura FTMO: piso −10%).
- **Pérdida hoy (límite 5%)** = caída del día (regla diaria FTMO: −5%).
- **Racha, WR por sesión (London/NY), WR por dirección (Long/Short)**.
- **Estado** (salud): `SANO` / `ATENCIÓN` / `ALERTA` según DD, WR reciente vs breakeven, y equity vs media.

---

## 7. Alertas — el filtro de régimen manual

> **Filosofía:** la alerta **avisa**; **tú decides** si pausar o rotar. **No hay pausa automática.**
> Es tu filtro de régimen manual: si una estrategia se degrada, saltan las banderas y decides sobre
> la marcha.

Reglas activas (por cuenta):

| # | Condición | Nivel |
|---|---|---|
| 1 | Drawdown ≥ 70% del límite (≥85% → grave) | warn/bad |
| 2 | WR reciente (n≥10) bajo el breakeven (−4 → grave) | warn/bad |
| 3 | WR global (n≥20) bajo el breakeven — "no rentable" | warn/bad |
| 4 | Equity bajo su media (n≥10) — "posible cambio de régimen" | warn |
| 5 | Cuenta en pérdida ≤ −5% (≤ −8% → grave) | warn/bad |
| 6 | Pérdida hoy ≤ −3% (ojo con el límite diario 5%) | warn |
| 7 | Racha de ≥ 6 pérdidas seguidas | warn |
| 8 | FTMO cerca del pase (+8% a +10%) | info |

---

## 8. PROCEDIMIENTOS

### 8.1 Recolección — automática
No hay que hacer nada. El colector corre solo cada 60 s en el VPS.

### 8.2 RETIRO (payout) en una cuenta — AUTOMÁTICO
1. Pides el payout en FTMO. Al procesarse, **MT5 graba el retiro** como operación de balance.
2. El colector lo captura en ≤ 60 s → `balance_ops` (bruto).
3. El panel se actualiza solo: **"Retirado (bruto)" sube** y el **balance baja**. El retorno se mantiene.

**Qué VIGILAR al retirar en un fondeo** (checklist, ~2 min después del payout):
- [ ] La tarjeta **"Retirado (bruto)"** subió por el monto retirado.
- [ ] El **balance** de la cuenta bajó por ese mismo monto.
- [ ] El **Retorno** NO cambió bruscamente (retirado + balance se compensan; es lo esperado).
- [ ] Si **no aparece** en un par de minutos: revisa que la cuenta siga **logueada** en el terminal y
      que el **colector esté corriendo** (ver §9).

**Excepción (manual):** si la cuenta se **cierra/inhabilita antes** de que el colector vea el retiro
(como la 10k previa que quedó inaccesible), hay que **sembrarlo a mano** una vez:
```sql
update balance_ops set amount = -<BRUTO_RETIRADO>
where bot_id = '<id_del_bot>' and account = <numero_cuenta>;
-- o insertar una fila nueva si no existe ninguna
```

### 8.3 PASAR DE FASE / FONDEO (challenge → fase 2 → fondeada) — MANUAL ⚠️
Un cambio de fase es una **cuenta nueva** (login distinto, balance arranca de cero). **No hay
balance-op**, así que el colector no lo detecta como retiro; solo actualiza el número de cuenta. El
`initial_balance` **no se resetea solo**.

**Checklist cuando pases una fase o te fondeen:**
- [ ] **Archivar la fase anterior** (queda en el histórico, sale del panel):
      ```sql
      update bots set active = false where id = '<id_fase_anterior>';
      ```
- [ ] **Alta de la nueva fase** con un `id` NUEVO y su **tamaño real**:
      - En `config.json`: entrada nueva, nuevo `account`, `initial_balance` = tamaño de la cuenta nueva.
      - Reiniciar el colector.
- [ ] **Verificar** que el retorno de la fase nueva **arranca limpio** (≈0%), sin arrastrar el retiro
      viejo ni un `initial_balance` equivocado.

> **Regla simple: cada fase/fondeo = un `id` nuevo.** El retorno de un challenge es *virtual* (no te
> pagan por pasar); lo que mide la estrategia (WR/PF/R) igual se ve sumando las fases en el histórico.

**Qué VIGILAR al pasar de fase:**
- [ ] La cuenta vieja desapareció del panel (archivada) pero su histórico sigue.
- [ ] La cuenta nueva aparece con su tamaño correcto y retorno ~0%.
- [ ] El **"Retirado"** viejo NO se filtró a la cuenta nueva (si aparece un retiro que no hiciste en
      la nueva, revisa que usaste un `id` distinto).

### 8.4 Colchón al ROTAR en el mismo terminal — AUTOMÁTICO
Cuando llevas un colchón a la cuenta nueva, MT5 lo graba como **depósito** en la cuenta nueva. El
panel lo **resta** solo (depósito extra) para no contarlo como ganancia. Cero intervención.
⚠️ Asume **mismo tamaño** de cuenta. Si cambia el tamaño → es cambio de fase (§8.3, manual).

### 8.5 SUMAR una cuenta / challenge nuevo
1. En `config.json`, agrega el bloque del bot (id, name, symbol, account, terminal_path, session,
   risk_pct, initial_balance, rr, magic).
2. Reinicia el colector. El panel lo detecta solo y lo ubica por categoría (según el `id`).

### 8.6 Agregar una DEMO / Lab
Igual que §8.5, pero con un `id` que contenga **`demo`** o **`lab`** (ej. `demo_us30_orb`). Aparece
**solo** en Lab · Demo, aislada del portafolio real. Truco: varios EAs con distinto `magic` en una
misma cuenta demo → cada uno su propia card.

### 8.7 NUEVA prop firm (no FTMO/Darwinex)
Hoy la categoría se infiere del `id`. Para una 3ª firma con página propia, se agrega una columna
`category` explícita (pendiente hasta que haga falta).

### 8.8 El HISTÓRICO
- Vive en `trades`, **para siempre** (el colector solo agrega).
- Archivar un bot (`active = false`) lo saca del panel **sin borrar** su historia.
- El selector de temporalidad (Todo / mes / 30d / 7d) filtra la vista sin tocar la data.

---

## 9. Operar el colector (en el VPS)

```powershell
# variables (una vez por sesión de PowerShell)
$env:SUPABASE_URL="https://....supabase.co"
$env:SUPABASE_SERVICE_KEY="<service_role_key>"

# arrancar
python panel/collector/collector.py
```
- Para **reiniciarlo** tras editar `config.json`: detener (Ctrl-C) y volver a arrancar.
- Corre en loop cada 60 s; en el panel, el sidebar muestra "próxima en Xs" y la última recolección.

---

## 10. Troubleshooting

| Síntoma | Causa probable | Solución |
|---|---|---|
| Una cuenta no actualiza | terminal cerrado / no logueado / colector caído | abrir terminal + loguear; reiniciar colector |
| Retiro no aparece | cuenta cerrada antes de capturarlo | sembrar a mano (§8.2) |
| Retorno raro tras pasar fase | no se reseteó `initial_balance` | seguir §8.3 (id nuevo + tamaño) |
| Panel "sin datos" | faltan `SUPABASE_URL`/`SERVICE_KEY` | setear env del panel (`.env.local`) |
| Trade duplicado | (no debería) dedup por `(account, ticket)` | revisar magic/config |

---

## 11. Seguridad
- **Nunca** se commitean secretos: `.env.local` (panel) y las env del colector están gitignoreados.
- El `service_role` key de Supabase se usa **solo del lado servidor** (nunca llega al navegador).
- El panel se protege con `PANEL_PASSWORD` (cookie). Si se despliega público, considerar Cloudflare
  Access para una capa extra.
