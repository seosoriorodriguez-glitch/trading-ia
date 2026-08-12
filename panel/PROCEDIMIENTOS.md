# Procedimientos — Kovatia Invest (ciclo de vida de los datos)

Guía para cuando cambien las cuentas: retiros, rollover, nuevos challenges, etc.
El colector corre en el VPS (`panel/collector/`), cada **60 segundos**.

---

## Cómo funciona la recolección (base para entender todo lo demás)

- El colector se conecta al **terminal MT5** de cada cuenta (por `terminal_path` en `config.json`) y **lee el historial** (solo lectura, no toca nada).
- **Rotación de cuenta:** como rotas el login en el mismo terminal (mismo bot), el colector **NO salta** si el número no coincide: actualiza el `account` registrado al login actual y sigue. (Los retiros se acumulan por `bot_id`, así sobreviven la rotación.)
- Filtra por **magic** (o toma todo si `magic: null`) → solo los trades del bot.
- Sube a Supabase con **dedup** por `(account, ticket)` → **nunca duplica**.
- **Nunca borra.** El histórico se acumula para siempre en Supabase.
- Guarda un **snapshot de balance real** cada corrida → de ahí sale el "Balance" y los retiros.

---

## 1. Cuando RETIRES ganancias (payout)

**Automático** — MT5 graba el retiro como operación de balance dentro de la cuenta; el colector la captura a `balance_ops`.
- El monto retirado se registra **BRUTO** (lo que sale de la cuenta). El panel:
  - Suma el bruto al **retorno/PnL generado** (mide la estrategia: tu bot SÍ generó ese dinero antes del split).
  - En la tarjeta **"Retirado (bruto)"** muestra el bruto y debajo el desglose **"tú 80% · FTMO 20%"** (split configurable en `data.ts`, hoy 0.8 para FTMO, 1.0 para Darwinex).
- Las **métricas de trading** (WR, PF, R, expectancy) **NO cambian** — reflejan lo operativo.

> Nota sobre la semilla del 10k previo: se sembró a mano. El valor correcto es el **bruto** ($392, no el neto $314). Corregir con:
> ```sql
> update balance_ops set amount = -392.00 where bot_id = 'us30_live_10k' and amount = -314.03;
> ```

---

## 2. Cuando PASES DE FASE o te FONDEEN (challenge → fase 2 → fondeada)

⚠️ **Esto es MANUAL** (a diferencia del retiro). Un cambio de fase es una **cuenta nueva** (login distinto, balance arranca de cero en su tamaño) — **no hay balance-op**, así que el colector no lo detecta como retiro; sólo actualiza el número de cuenta. El `initial_balance` y la línea base de retiros **no se resetean solos**.

**Cuando pases una fase / te fondeen, avísame y hago (o corres tú el SQL):**
1. **Archivar la fase anterior** como registro cerrado (queda en el histórico, sale del panel):
   ```sql
   update bots set active = false where id = 'dax_50k_fase1';
   ```
2. **Alta de la nueva fase** con su tamaño real (así el retorno arranca limpio):
   - En `config.json`, entrada nueva con `id` distinto, nuevo `account`, `initial_balance` = tamaño de la cuenta nueva.
   - Reiniciar el colector.
3. Esto evita que (a) el `initial_balance` viejo quede mal si cambia el tamaño, y (b) el retiro viejo se filtre al nuevo `bot_id`.

> Regla simple: **cada fase/fondeo = un `id` nuevo**. El retorno de un challenge es virtual (no te pagan por pasar); lo que mide la estrategia (WR/PF/R) igual se ve sumando las fases en el histórico.

---

## 2b. Cuando sólo cambia el NÚMERO (misma cuenta lógica, renovación)

Si es la misma cuenta (mismo tamaño, misma lineage) y sólo cambió el login:

**Opción A (RECOMENDADA) — cuenta nueva = bot nuevo (historial limpio):**
1. En `config.json`, **agrega una entrada NUEVA** con `id` distinto (ej. `dax_50k` → `dax_funded`), el nuevo `account` y `terminal_path`.
2. **Archiva la vieja** en Supabase (SQL Editor):
   ```sql
   update bots set active = false where id = 'dax_50k';
   ```
   → desaparece del panel pero **el histórico queda guardado**.
3. Reinicia el colector.

**Opción B — misma cuenta lógica, solo cambió el número:**
- Actualiza el `account` en `config.json` y reinicia el colector.
- ⚠️ El bot mezclará trades de la cuenta vieja + la nueva bajo el mismo `id`. Solo úsalo si quieres continuidad (ej. misma estrategia, cuenta renovada).

---

## 3. Cuando SUMES un nuevo challenge / cuenta

1. En `config.json`, agrega la entrada del bot:
   ```json
   {
     "id": "nuevo_challenge_25k",
     "name": "US30 Challenge 25k",
     "symbol": "US30.cash",
     "account": 12345678,
     "terminal_path": "C:\\Program Files\\MT5_XXX\\terminal64.exe",
     "session": "london", "risk_pct": 0.005, "initial_balance": 25000,
     "rr": 2.5, "magic": 345680
   }
   ```
2. Reinicia el colector → registra el bot y empieza a recolectar.
3. El panel lo detecta solo. Si el `id` **no** contiene "darwinex" → aparece en **FTMO**; si contiene "darwinex" → en **Darwinex**.

---

## 4. Cuando sumes una NUEVA prop firm (no FTMO ni Darwinex)

Hoy la categoría se infiere del `id` (contiene "darwinex" = Darwinex, si no = FTMO). Para una 3ª firma hay que agregar una **columna `category`** explícita:
1. Supabase: `alter table bots add column if not exists category text;`
2. Poner `"category": "fundednext"` (o la que sea) en el `config.json` del bot, y que el colector la suba.
3. Avísame para agregar la página/sección de esa firma en el panel.
*(Pendiente de implementar cuando pase — por ahora FTMO/Darwinex funcionan por inferencia.)*

---

## 5. El HISTÓRICO

- Vive en la tabla `trades` de Supabase, **para siempre** (el colector solo agrega).
- Archivar un bot (`active = false`) lo saca del panel **sin borrar** su historia.
- Si algún día quieres borrar data de prueba o de una cuenta vieja:
  ```sql
  delete from trades where bot_id = 'xxx';   -- cuidado, es irreversible
  ```
- El selector de **temporalidad** del panel (Todo / mes / 30d / 7d) filtra la vista sin tocar la data.
