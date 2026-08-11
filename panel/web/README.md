# Panel web — Next.js + Supabase

Panel privado (contraseña única) que lee Supabase server-side y muestra la salud de
cada bot: WR, WR reciente, PF, retorno, balance, DD vs límite, curva de equity vs
su media (señal de régimen), operaciones recientes y de la sesión. Alertas por color.

## Correr LOCAL (primero)

```bash
cd panel/web
npm install
cp .env.example .env.local     # y edita los 3 valores
npm run dev
# abre http://localhost:3000  -> login con PANEL_PASSWORD
```

`.env.local`:
```
SUPABASE_URL=https://ytpuralmptyswpnwgnlf.supabase.co   # proyecto fitcorner
SUPABASE_SERVICE_KEY=<service_role key de Supabase>       # Settings > API
PANEL_PASSWORD=<la que quieras>
```

> El service_role key queda SOLO en el server (env), nunca se manda al navegador.
> Si aún no corre el colector, el panel dirá "sin datos" — es normal.

## Deploy a Cloudflare Pages (trading.kovatia.com)

1. Añade a cada page/route dinámico `export const runtime = "edge";` (requisito CF).
2. Build para Cloudflare:
   ```bash
   npm run cf:build       # usa @cloudflare/next-on-pages
   ```
3. En Cloudflare Dashboard → **Pages → Create → conecta el repo** (o sube `.vercel/output/static`).
   - Build command: `npx @cloudflare/next-on-pages`
   - Output dir: `.vercel/output/static`
4. **Settings → Environment variables:** `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `PANEL_PASSWORD`.
5. **Custom domains → añade `trading.kovatia.com`** (Cloudflare crea el CNAME solo si el dominio está en tu cuenta CF).

## Notas

- Auto-refresh cada 30s (meta refresh). Se puede subir a Supabase Realtime después.
- Salud por bot: verde (sano) / amarillo (atención) / rojo (alerta) según WR reciente
  vs breakeven, DD y equity vs media.
