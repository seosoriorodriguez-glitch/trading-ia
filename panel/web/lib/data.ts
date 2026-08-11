import { createClient } from "@supabase/supabase-js";

export type Trade = {
  bot_id: string; account: number; ticket: number; symbol: string;
  direction: string; entry_price: number; sl: number | null; tp: number | null;
  exit_price: number; entry_time: string; exit_time: string; exit_reason: string;
  pnl_usd: number; pnl_r: number | null; volume: number; session: string;
};
export type Bot = {
  id: string; name: string; symbol: string; account: number | null;
  session: string; risk_pct: number; initial_balance: number; rr: number; magic: number;
};
export type EquityPoint = { i: number; t: string; equity: number; ma: number | null };
export type BotHealth = Bot & {
  n: number; wins: number; losses: number; wr: number; pf: number;
  sumR: number; retPct: number; pnlUsd: number; balance: number;
  ddPct: number; maxDdPct: number; ddLimitPct: number;
  breakevenWr: number; rollingWr: number; aboveMa: boolean;
  health: "good" | "warn" | "bad";
  equity: EquityPoint[]; recent: Trade[]; todayN: number; todayWins: number;
};

const MA_WINDOW = 30;
const ROLL_WINDOW = 30;

function sb() {
  return createClient(process.env.SUPABASE_URL!, process.env.SUPABASE_SERVICE_KEY!, {
    auth: { persistSession: false },
    global: {
      // no cachear: siempre leer data fresca de Supabase (evita que Next cachee el fetch)
      fetch: (u: RequestInfo | URL, o?: RequestInit) => fetch(u, { ...o, cache: "no-store" }),
    },
  });
}

function pf(rs: number[]) {
  const g = rs.filter((r) => r > 0).reduce((a, b) => a + b, 0);
  const l = Math.abs(rs.filter((r) => r <= 0).reduce((a, b) => a + b, 0));
  return l > 0 ? g / l : g > 0 ? 99 : 0;
}

function compute(bot: Bot, all: Trade[]): BotHealth {
  const ts = all
    .filter((t) => t.bot_id === bot.id)
    .sort((a, b) => +new Date(a.exit_time) - +new Date(b.exit_time));
  const n = ts.length;
  const rs = ts.map((t) => (t.pnl_r ?? (t.pnl_usd > 0 ? bot.rr : -1)));
  const wins = ts.filter((t) => t.pnl_usd > 0).length;
  const losses = n - wins;
  const wr = n ? (wins / n) * 100 : 0;
  const sumR = rs.reduce((a, b) => a + b, 0);
  const pnlUsd = ts.reduce((a, t) => a + t.pnl_usd, 0);
  const balance = bot.initial_balance + pnlUsd;
  const retPct = bot.initial_balance ? (pnlUsd / bot.initial_balance) * 100 : 0;

  // curva de equity + media movil
  let cum = bot.initial_balance;
  const equity: EquityPoint[] = ts.map((t, i) => {
    cum += t.pnl_usd;
    return { i, t: t.exit_time, equity: cum, ma: null as number | null };
  });
  // MA sobre la serie de equity ya construida
  const eqVals = equity.map((p) => p.equity);
  equity.forEach((p, i) => {
    const from = Math.max(0, i - MA_WINDOW + 1);
    const win = eqVals.slice(from, i + 1);
    p.ma = win.reduce((a, b) => a + b, 0) / win.length;
  });
  const last = equity[equity.length - 1];
  const aboveMa = last ? last.equity >= (last.ma ?? last.equity) : true;

  // drawdown actual (desde el pico) y max
  let peak = bot.initial_balance, maxDd = 0, curDd = 0;
  for (const v of eqVals) {
    if (v > peak) peak = v;
    const dd = ((peak - v) / bot.initial_balance) * 100;
    if (dd > maxDd) maxDd = dd;
  }
  curDd = ((peak - (last?.equity ?? bot.initial_balance)) / bot.initial_balance) * 100;

  const rollWin = rs.slice(-ROLL_WINDOW);
  const rollingWr = rollWin.length
    ? (ts.slice(-ROLL_WINDOW).filter((t) => t.pnl_usd > 0).length / rollWin.length) * 100
    : 0;
  const breakevenWr = (1 / (1 + bot.rr)) * 100;

  const today = new Date().toISOString().slice(0, 10);
  const todayTs = ts.filter((t) => t.exit_time.slice(0, 10) === today);

  // salud
  let health: BotHealth["health"] = "good";
  if (curDd >= bot.initial_balance * 0 + 6 || (n >= 10 && rollingWr < breakevenWr) || !aboveMa)
    health = "warn";
  if (curDd >= 8 || (n >= 15 && rollingWr < breakevenWr - 4)) health = "bad";

  return {
    ...bot, n, wins, losses, wr, pf: pf(rs), sumR, retPct, pnlUsd, balance,
    ddPct: Math.max(0, curDd), maxDdPct: maxDd, ddLimitPct: 10,
    breakevenWr, rollingWr, aboveMa, health,
    equity, recent: ts.slice(-15).reverse(),
    todayN: todayTs.length, todayWins: todayTs.filter((t) => t.pnl_usd > 0).length,
  };
}

export type Alert = { botId: string; botName: string; level: "warn" | "bad"; msg: string };
export type Totals = {
  nBots: number; capital: number; balance: number; pnlUsd: number; retPct: number;
  nTrades: number; wins: number; losses: number; wr: number;
  healthy: number; warn: number; bad: number;
};
export type PortPoint = { i: number; equity: number; ma: number | null };
export type Dashboard = {
  bots: BotHealth[]; totals: Totals; alerts: Alert[]; portfolio: PortPoint[];
  updatedAt: string; error?: string;
};

function alertsFor(b: BotHealth): Alert[] {
  const out: Alert[] = [];
  if (b.ddPct >= b.ddLimitPct * 0.7)
    out.push({ botId: b.id, botName: b.name, level: b.ddPct >= b.ddLimitPct * 0.85 ? "bad" : "warn",
      msg: `Drawdown ${b.ddPct.toFixed(1)}% — cerca del límite ${b.ddLimitPct}%` });
  if (b.n >= 10 && b.rollingWr < b.breakevenWr)
    out.push({ botId: b.id, botName: b.name, level: b.rollingWr < b.breakevenWr - 4 ? "bad" : "warn",
      msg: `WR reciente ${b.rollingWr.toFixed(0)}% bajo el breakeven ${b.breakevenWr.toFixed(0)}%` });
  if (!b.aboveMa && b.n >= 10)
    out.push({ botId: b.id, botName: b.name, level: "warn",
      msg: `Equity bajo su media — posible cambio de régimen` });
  return out;
}

const EMPTY: Totals = { nBots: 0, capital: 0, balance: 0, pnlUsd: 0, retPct: 0, nTrades: 0, wins: 0, losses: 0, wr: 0, healthy: 0, warn: 0, bad: 0 };

export async function getDashboard(): Promise<Dashboard> {
  const base = { bots: [], totals: EMPTY, alerts: [], portfolio: [], updatedAt: new Date().toISOString() };
  if (!process.env.SUPABASE_URL || !process.env.SUPABASE_SERVICE_KEY)
    return { ...base, error: "Falta configurar SUPABASE_URL / SUPABASE_SERVICE_KEY en .env.local" };
  try {
    const client = sb();
    const [{ data: botsRaw }, { data: tradesRaw }] = await Promise.all([
      client.from("bots").select("*").eq("active", true),
      client.from("trades").select("*").order("exit_time", { ascending: true }).limit(5000),
    ]);
    const trades = (tradesRaw ?? []) as Trade[];
    const health = (botsRaw ?? []).map((b) => compute(b as Bot, trades));
    const rank = { bad: 0, warn: 1, good: 2 };
    health.sort((a, b) => rank[a.health] - rank[b.health]);

    const sum = (f: (b: BotHealth) => number) => health.reduce((a, b) => a + f(b), 0);
    const capital = sum((b) => b.initial_balance);
    const pnlUsd = sum((b) => b.pnlUsd);
    const nTrades = sum((b) => b.n);
    const wins = sum((b) => b.wins);
    const totals: Totals = {
      nBots: health.length, capital, balance: sum((b) => b.balance), pnlUsd,
      retPct: capital ? (pnlUsd / capital) * 100 : 0, nTrades, wins, losses: nTrades - wins,
      wr: nTrades ? (wins / nTrades) * 100 : 0,
      healthy: health.filter((b) => b.health === "good").length,
      warn: health.filter((b) => b.health === "warn").length,
      bad: health.filter((b) => b.health === "bad").length,
    };
    const alerts = health.flatMap(alertsFor).sort((a, b) => (a.level === "bad" ? 0 : 1) - (b.level === "bad" ? 0 : 1));

    // equity del portafolio: todos los trades ordenados por salida
    const sorted = [...trades].sort((a, b) => +new Date(a.exit_time) - +new Date(b.exit_time));
    let cum = capital;
    const portfolio: PortPoint[] = sorted.map((t, i) => { cum += t.pnl_usd; return { i, equity: cum, ma: null }; });
    portfolio.forEach((p, i) => {
      const from = Math.max(0, i - MA_WINDOW + 1);
      const win = portfolio.slice(from, i + 1).map((x) => x.equity);
      p.ma = win.reduce((a, b) => a + b, 0) / win.length;
    });

    return { bots: health, totals, alerts, portfolio, updatedAt: new Date().toISOString() };
  } catch (e) {
    return { ...base, error: String(e) };
  }
}
