-- =====================================================================
-- Panel de Trading — esquema Supabase (Postgres)
-- Correr una vez en: Supabase > SQL Editor > New query > Run
-- Proyecto DEDICADO al trading (separado de la data de Kovatia)
-- =====================================================================

-- Registro de bots activos
create table if not exists bots (
  id               text primary key,          -- 'us30_london', 'dax_50k'
  name             text not null,             -- nombre visible
  symbol           text not null,             -- 'GER40.cash'
  account          bigint,                    -- nro cuenta MT5
  session          text,                      -- 'london'
  risk_pct         numeric,                   -- 0.005
  initial_balance  numeric,
  rr               numeric,
  magic            int,
  active           boolean default true,
  created_at       timestamptz default now()
);

-- Cada operación CERRADA (fuente: historial MT5)
create table if not exists trades (
  id           bigserial primary key,
  bot_id       text references bots(id),
  account      bigint not null,
  ticket       bigint not null,               -- position_id de MT5
  symbol       text,
  direction    text,                          -- 'long' | 'short'
  entry_price  numeric,
  sl           numeric,
  tp           numeric,
  exit_price   numeric,
  entry_time   timestamptz,
  exit_time    timestamptz,
  exit_reason  text,                          -- 'tp' | 'sl' | 'other'
  risk_points  numeric,
  volume       numeric,
  pnl_usd      numeric,
  pnl_r        numeric,                        -- R obtenido
  session      text,
  created_at   timestamptz default now(),
  unique(account, ticket)                     -- idempotencia / dedup
);

-- Snapshots periódicos de balance/equity (para curva y DD vs límite)
create table if not exists account_snapshots (
  id         bigserial primary key,
  bot_id     text references bots(id),
  account    bigint not null,
  balance    numeric,
  equity     numeric,
  ts         timestamptz default now()
);

-- Depósitos / retiros (operaciones de balance de MT5) — para el $ retirado acumulado
create table if not exists balance_ops (
  id         bigserial primary key,
  bot_id     text references bots(id),
  account    bigint not null,
  ticket     bigint not null,
  amount     numeric,            -- + depósito, - retiro
  ts         timestamptz,
  comment    text,
  created_at timestamptz default now(),
  unique(account, ticket)
);
create index if not exists idx_bops_bot on balance_ops(bot_id, ts desc);

-- Vista "En vivo": velas M5 de la SESIÓN ACTUAL + zonas OB por símbolo (rodante, se sobrescribe)
create table if not exists session_view (
  symbol     text primary key,          -- 'US30.cash', 'GER40.cash'
  session    text,                      -- 'london'
  live       boolean not null default false,       -- true = llenándose en vivo; false = sesión congelada
  candles    jsonb not null default '[]'::jsonb,   -- [{t,o,h,l,c}]
  zones      jsonb not null default '[]'::jsonb,   -- [{type,high,low,at}]
  updated_at timestamptz not null default now()
);

-- Régimen de volatilidad: ¿sigue el buffer FIJO del SL proporcionado al mercado?
-- ratio = buffer_actual / mediana del rango M5 de las últimas 20 sesiones de London.
-- Solo diagnóstico: el bot NO lo lee ni ajusta nada. Ver la ayuda en /alertas.
create table if not exists vol_regime (
  symbol        text primary key,        -- 'US30.cash'
  fecha         date,                    -- última sesión CERRADA incluida en la mediana
  mediana_m5    numeric,                 -- mediana (high-low) en puntos
  ratio         numeric,                 -- buffer_actual / mediana_m5
  buffer_actual numeric,                 -- 35 (LONDON_PARAMS.buffer_points)
  buffer_sug    numeric,                 -- 1.35 * mediana_m5
  estado        text,                    -- 'verde' <1.6 | 'amarillo' <2.0 | 'rojo'
  n_sesiones    int,                     -- 20
  updated_at    timestamptz not null default now()
);

create index if not exists idx_trades_bot_time  on trades(bot_id, exit_time desc);
create index if not exists idx_trades_exit_time  on trades(exit_time desc);
create index if not exists idx_snap_account_ts   on account_snapshots(account, ts desc);

-- =====================================================================
-- RLS: el colector escribe con SERVICE KEY (bypassa RLS).
-- El panel web lee SERVER-SIDE (Next.js) con service key -> nunca expone
-- claves al cliente, y la contraseña del panel protege el acceso.
-- Por eso dejamos RLS activo SIN políticas públicas (nadie con anon key lee).
-- =====================================================================
alter table bots              enable row level security;
alter table trades            enable row level security;
alter table account_snapshots enable row level security;
alter table session_view      enable row level security;
alter table vol_regime        enable row level security;

-- ============================================================================
-- Recompensas de prop firm (REGISTRO MANUAL)
-- ============================================================================
-- Por que a mano: cuando FTMO paga una recompensa, CIERRA la cuenta y emite otra.
-- El colector deja de consultar la cuenta vieja en cuanto cambias el terminal, asi
-- que el retiro de cierre NUNCA queda en balance_ops. Rastrear payouts desde MT5
-- subestima siempre. Esta tabla es la fuente de verdad del efectivo cobrado.
--
-- Se llena copiando de FTMO > Recompensas > Historial de Recompensas.
create table if not exists payouts (
  id           bigserial primary key,
  bot_id       text references bots(id),
  account      bigint,                    -- cuenta de la que salio
  fecha        date not null,             -- fecha de la factura
  beneficio    numeric,                   -- beneficio total de la cuenta (antes del split)
  recompensa   numeric,                   -- tu parte tras el split (80:20)
  retiro       numeric default 0,         -- cobrado en efectivo
  reinversion  numeric default 0,         -- rollover que quedo en la cuenta siguiente
  reembolso    numeric default 0,         -- devolucion del fee del challenge
  estado       text default 'esperando',  -- 'esperando' | 'pagado'
  nota         text,
  created_at   timestamptz default now(),
  unique(bot_id, fecha)
);
create index if not exists idx_payouts_bot on payouts(bot_id, fecha desc);

-- ============================================================================
-- Ciclos de cuenta — historial que sobrevive a las rotaciones
-- ============================================================================
-- Un bot_id pasa por varias cuentas a lo largo del tiempo (payout, pase de fase,
-- breach). Los trades ya guardan `account`, asi que el historial por cuenta existe;
-- esta tabla le pone nombre, tamaño y fechas a cada ciclo para poder segmentarlo.
--
-- account_size es el tamaño NOMINAL (10000), no el balance con rollover. Es la base
-- sobre la que la prop calcula el limite de perdida.
create table if not exists account_cycles (
  id           bigserial primary key,
  bot_id       text references bots(id),
  account      bigint not null,
  account_size numeric,                   -- 10000 / 100000 — base del limite de perdida
  seed_extra   numeric default 0,         -- rollover con el que arranco
  started_at   timestamptz,
  ended_at     timestamptz,               -- null = ciclo activo
  end_reason   text,                      -- 'payout' | 'phase_pass' | 'breach'
  unique(bot_id, account)
);
create index if not exists idx_cycles_bot on account_cycles(bot_id, started_at desc);
