# Panel de Trading — monitoreo en vivo de la salud de los bots

Panel web privado que muestra en tiempo (casi) real la salud de cada bot: WR,
curva de equity vs su media (señal de régimen), DD vs límite FTMO, operaciones de
la sesión, ganadas/perdidas, alertas. Todo por activo.

```
Bots + MT5 (VPS)  →  Colector (VPS)  →  Supabase (nube)  →  Panel Next.js (trading.kovatia.com)
```

100% ADITIVO: el colector solo LEE el historial de MT5. No importa ni modifica
ningún bot de producción.

---

## Componentes

| Carpeta | Qué es | Dónde corre |
|---|---|---|
| `supabase/schema.sql` | Tablas Postgres | Supabase (nube) |
| `collector/` | Lee MT5 → sube a Supabase | VPS |
| `web/` | Panel Next.js (siguiente entrega) | Vercel → trading.kovatia.com |

---

## Paso 1 — Supabase (base de datos)

1. Crea un **proyecto Supabase nuevo** dedicado al trading (free): https://supabase.com
2. **SQL Editor → New query →** pega todo `supabase/schema.sql` → **Run**.
3. **Settings → API →** copia y guarda:
   - `Project URL`  → `SUPABASE_URL`
   - `service_role` key (secreta) → `SUPABASE_SERVICE_KEY`  (para el colector y el panel, SERVER-SIDE)
   - `anon` key → por si se usa después

> El `service_role` es secreto — nunca va al navegador. Solo el colector (VPS) y el
> servidor del panel (Next.js server-side) lo usan.

## Paso 2 — Colector (en el VPS)

```powershell
cd C:\Users\Administrator\trading-ia\panel\collector
copy config.example.json config.json      # y edita terminal_path / account de cada bot
pip install -r requirements.txt
setx SUPABASE_URL "https://xxxx.supabase.co"
setx SUPABASE_SERVICE_KEY "eyJ...service_role..."
# (reabre la terminal para que tome las variables)
python collector.py
```

- Edita `config.json`: `terminal_path` y `account` de cada bot. El colector solo
  agarra trades cuyo `magic` coincida (ignora manuales).
- Déjalo corriendo en una ventana (como los bots). Sincroniza cada 60s.
- Es idempotente: puedes reiniciarlo sin duplicar (dedup por `account+ticket`).

## Paso 3 — Panel web (siguiente entrega)

Next.js + Tremol + Supabase, protegido por contraseña única, deploy a
`trading.kovatia.com` (subdominio de Kovatia en Vercel). Ver `web/README.md`.

---

## Checklist de credenciales que necesito de ti

- [ ] `SUPABASE_URL` del proyecto nuevo de trading
- [ ] `SUPABASE_SERVICE_KEY` (service_role)
- [ ] `SUPABASE_ANON_KEY` (anon)
- [ ] Confirmar `account` + `terminal_path` reales de cada bot (US30 live, Darwinex)
- [ ] La contraseña que quieres para entrar al panel
- [ ] Acceso para apuntar `trading.kovatia.com` a Vercel (DNS del dominio Kovatia)
