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
