# Procedimientos — Kovatia Invest (ciclo de vida de los datos)

Guía para cuando cambien las cuentas: retiros, rollover, nuevos challenges, etc.
El colector corre en el VPS (`panel/collector/`), cada **60 segundos**.

---

## Cómo funciona la recolección (base para entender todo lo demás)

- El colector se conecta al **terminal MT5** de cada cuenta (por `terminal_path` en `config.json`) y **lee el historial** (solo lectura, no toca nada).
- **Seguridad:** verifica que la cuenta logueada en el terminal coincida con `account` del config. Si no cuadra → **salta esa cuenta** (no mezcla data).
- Filtra por **magic** (o toma todo si `magic: null`) → solo los trades del bot.
- Sube a Supabase con **dedup** por `(account, ticket)` → **nunca duplica**.
- **Nunca borra.** El histórico se acumula para siempre en Supabase.
- Guarda un **snapshot de balance real** cada corrida → de ahí sale el "Balance" y los retiros.

---

## 1. Cuando RETIRES ganancias

**No hay que hacer nada — es automático.**
- El colector lee el **balance real** de MT5 (que baja tras el retiro).
- El panel muestra ese balance real y agrega **"retirado $X"** en la tarjeta.
- Las **métricas de trading** (WR, PF, R, expectancy, curva de equity) **NO cambian** — reflejan el rendimiento operativo, no el dinero retirado.

---

## 2. Cuando CAMBIES de cuenta (rollover / renovación / pasar challenge → fondeo)

Al cambiar el número de cuenta de un bot (nueva cuenta en el mismo terminal, o pasar el challenge y recibir la fondeada), tienes 2 caminos:

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
