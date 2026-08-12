import { createClient } from "@supabase/supabase-js";
import { chDate, chToday } from "./tz";

// Categoría inferida del id del bot. "demo"/"lab" = laboratorio (independiente del resto).
export function catOf(id: string): "ftmo" | "darwinex" | "demo" {
  if (id.includes("demo") || id.includes("lab")) return "demo";
  if (id.includes("darwinex")) return "darwinex";
  return "ftmo";
}

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
export type DayPnl = { date: string; pnl: number; n: number; wins: number };
export type BotHealth = Bot & {
  category: "ftmo" | "darwinex" | "demo";
  n: number; wins: number; losses: number; wr: number; pf: number;
  sumR: number; retPct: number; pnlUsd: number; balance: number;
  realBalance: number | null; netFlows: number; withdrawn: number; deposited: number;
  realPnl: number; realRetPct: number;
  ddPct: number; maxDdPct: number; ddLimitPct: number;
  maxLossFromInitialPct: number; todayPnlUsd: number; todayPnlPct: number;
  breakevenWr: number; rollingWr: number; aboveMa: boolean;
  // stats avanzadas (estilo FTMO)
  expectancyUsd: number; expectancyR: number;
  avgWinUsd: number; avgLossUsd: number; avgWinR: number; avgLossR: number;
  rrr: number; streak: number; streakWin: boolean;
  bestUsd: number; worstUsd: number; avgDurationMin: number;
  wrLondon: number; wrNy: number; wrLong: number; wrShort: number;
  health: "good" | "warn" | "bad";
  equity: EquityPoint[]; recent: Trade[]; todayN: number; todayWins: number;
  daily: DayPnl[];  // para el calendario
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
  const minEq = eqVals.length ? Math.min(bot.initial_balance, ...eqVals) : bot.initial_balance;
  const maxLossFromInitialPct = Math.max(0, ((bot.initial_balance - minEq) / bot.initial_balance) * 100);

  const rollWin = rs.slice(-ROLL_WINDOW);
  const rollingWr = rollWin.length
    ? (ts.slice(-ROLL_WINDOW).filter((t) => t.pnl_usd > 0).length / rollWin.length) * 100
    : 0;
  const breakevenWr = (1 / (1 + bot.rr)) * 100;

  const today = chToday();
  const todayTs = ts.filter((t) => chDate(t.exit_time) === today);

  // --- stats avanzadas (estilo FTMO) ---
  const avg = (a: number[]) => (a.length ? a.reduce((x, y) => x + y, 0) / a.length : 0);
  const winsArr = ts.filter((t) => t.pnl_usd > 0);
  const lossArr = ts.filter((t) => t.pnl_usd <= 0);
  const avgWinUsd = avg(winsArr.map((t) => t.pnl_usd));
  const avgLossUsd = avg(lossArr.map((t) => t.pnl_usd));
  const avgWinR = avg(winsArr.map((t) => t.pnl_r ?? bot.rr));
  const avgLossR = avg(lossArr.map((t) => t.pnl_r ?? -1));
  const expectancyUsd = n ? pnlUsd / n : 0;
  const expectancyR = n ? sumR / n : 0;
  const rrr = avgLossUsd !== 0 ? Math.abs(avgWinUsd / avgLossUsd) : 0;
  const bestUsd = n ? Math.max(...ts.map((t) => t.pnl_usd)) : 0;
  const worstUsd = n ? Math.min(...ts.map((t) => t.pnl_usd)) : 0;
  const avgDurationMin = avg(ts.map((t) => (+new Date(t.exit_time) - +new Date(t.entry_time)) / 60000));
  let streak = 0, streakWin = true;
  if (n) {
    streakWin = ts[n - 1].pnl_usd > 0;
    for (let i = n - 1; i >= 0; i--) { if ((ts[i].pnl_usd > 0) === streakWin) streak++; else break; }
  }
  const wrOf = (arr: Trade[]) => (arr.length ? (arr.filter((t) => t.pnl_usd > 0).length / arr.length) * 100 : 0);
  const wrLondon = wrOf(ts.filter((t) => (t.session ?? "").includes("london")));
  const wrNy = wrOf(ts.filter((t) => { const s = t.session ?? ""; return s.includes("new_york") || s.includes("ny"); }));
  const wrLong = wrOf(ts.filter((t) => t.direction === "long"));
  const wrShort = wrOf(ts.filter((t) => t.direction === "short"));
  const dmap = new Map<string, { pnl: number; n: number; wins: number }>();
  for (const t of ts) {
    const d = chDate(t.exit_time);
    const e = dmap.get(d) ?? { pnl: 0, n: 0, wins: 0 };
    e.pnl += t.pnl_usd; e.n++; if (t.pnl_usd > 0) e.wins++;
    dmap.set(d, e);
  }
  const daily: DayPnl[] = Array.from(dmap.entries()).map(([date, v]) => ({ date, ...v })).sort((a, b) => a.date.localeCompare(b.date));
  const category = catOf(bot.id);
  const todayPnlUsd = todayTs.reduce((a, t) => a + t.pnl_usd, 0);
  const todayPnlPct = bot.initial_balance ? (todayPnlUsd / bot.initial_balance) * 100 : 0;

  // salud
  let health: BotHealth["health"] = "good";
  if (curDd >= bot.initial_balance * 0 + 6 || (n >= 10 && rollingWr < breakevenWr) || !aboveMa)
    health = "warn";
  if (curDd >= 8 || (n >= 15 && rollingWr < breakevenWr - 4)) health = "bad";

  return {
    ...bot, category, n, wins, losses, wr, pf: pf(rs), sumR, retPct, pnlUsd, balance,
    realBalance: null, netFlows: 0, withdrawn: 0, deposited: 0, realPnl: pnlUsd, realRetPct: retPct,
    ddPct: Math.max(0, curDd), maxDdPct: maxDd, ddLimitPct: 10,
    maxLossFromInitialPct, todayPnlUsd, todayPnlPct,
    breakevenWr, rollingWr, aboveMa, health,
    expectancyUsd, expectancyR, avgWinUsd, avgLossUsd, avgWinR, avgLossR, rrr,
    streak, streakWin, bestUsd, worstUsd, avgDurationMin, wrLondon, wrNy, wrLong, wrShort,
    equity, recent: ts.slice(-80).reverse(), daily,
    todayN: todayTs.length, todayWins: todayTs.filter((t) => t.pnl_usd > 0).length,
  };
}

export type Alert = { botId: string; botName: string; level: "info" | "warn" | "bad"; msg: string };
export type Totals = {
  nBots: number; capital: number; balance: number; pnlUsd: number; retPct: number;
  nTrades: number; wins: number; losses: number; wr: number;
  healthy: number; warn: number; bad: number;
};
export type PortPoint = { i: number; equity: number; ma: number | null };
export type Dashboard = {
  bots: BotHealth[]; totals: Totals; alerts: Alert[]; portfolio: PortPoint[];
  portfolioDaily: DayPnl[]; updatedAt: string; lastCollected: string; error?: string;
};

function alertsFor(b: BotHealth): Alert[] {
  const out: Alert[] = [];
  const A = (level: Alert["level"], msg: string) => out.push({ botId: b.id, botName: b.name, level, msg });
  if (b.ddPct >= b.ddLimitPct * 0.7)
    A(b.ddPct >= b.ddLimitPct * 0.85 ? "bad" : "warn", `Drawdown ${b.ddPct.toFixed(1)}% — cerca del límite ${b.ddLimitPct}%`);
  if (b.n >= 10 && b.rollingWr < b.breakevenWr)
    A(b.rollingWr < b.breakevenWr - 4 ? "bad" : "warn", `WR reciente ${b.rollingWr.toFixed(0)}% bajo el breakeven ${b.breakevenWr.toFixed(0)}%`);
  if (b.n >= 20 && b.wr < b.breakevenWr)
    A(b.wr < b.breakevenWr - 4 ? "bad" : "warn", `WR global ${b.wr.toFixed(0)}% bajo el breakeven ${b.breakevenWr.toFixed(0)}% — no rentable`);
  if (!b.aboveMa && b.n >= 10)
    A("warn", "Equity bajo su media — posible cambio de régimen");
  if (b.retPct <= -5)
    A(b.retPct <= -8 ? "bad" : "warn", `Cuenta en pérdida ${b.retPct.toFixed(1)}% del balance`);
  if (b.todayPnlPct <= -3)
    A("warn", `Pérdida hoy ${b.todayPnlPct.toFixed(1)}% — límite diario 5%`);
  if (!b.streakWin && b.streak >= 6)
    A("warn", `Racha de ${b.streak} pérdidas seguidas`);
  if (b.category === "ftmo" && b.retPct >= 8 && b.retPct < 10)
    A("info", `Cerca del pase FTMO (+${b.retPct.toFixed(1)}% de +10%)`);
  return out;
}

const EMPTY: Totals = { nBots: 0, capital: 0, balance: 0, pnlUsd: 0, retPct: 0, nTrades: 0, wins: 0, losses: 0, wr: 0, healthy: 0, warn: 0, bad: 0 };

export type Opts = { since?: string; until?: string; category?: "ftmo" | "darwinex" | "demo" };
export const MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"];
export function periodRange(key?: string): { since?: string; until?: string; label: string } {
  const now = new Date();
  const iso = (d: Date) => d.toISOString();
  const D = 864e5;
  if (key === "7d") return { since: iso(new Date(now.getTime() - 7 * D)), label: "Últimos 7 días" };
  if (key === "30d") return { since: iso(new Date(now.getTime() - 30 * D)), label: "Últimos 30 días" };
  if (key && /^\d{4}-\d{2}$/.test(key)) {
    const [y, m] = key.split("-").map(Number);
    return { since: iso(new Date(y, m - 1, 1)), until: iso(new Date(y, m, 1)), label: `${MESES[m - 1]} ${y}` };
  }
  return { label: "Todo" };
}

export type Candle = { t: number; o: number; h: number; l: number; c: number };
export async function getTradeCandles(tickets: number[]): Promise<Record<number, Candle[]>> {
  if (!tickets.length || !process.env.SUPABASE_URL || !process.env.SUPABASE_SERVICE_KEY) return {};
  try {
    const { data } = await sb().from("trade_candles").select("ticket,candles").in("ticket", tickets);
    const out: Record<number, Candle[]> = {};
    for (const r of (data ?? []) as { ticket: number; candles: Candle[] }[]) out[r.ticket] = r.candles;
    return out;
  } catch {
    return {};
  }
}

export type SessionZone = { type: "bullish" | "bearish"; high: number; low: number; at: number };
export type SessionView = { symbol: string; session: string; candles: Candle[]; zones: SessionZone[]; updatedAt: string };
export async function getSessionViews(symbols: string[]): Promise<Record<string, SessionView>> {
  if (!symbols.length || !process.env.SUPABASE_URL || !process.env.SUPABASE_SERVICE_KEY) return {};
  try {
    const { data } = await sb().from("session_view").select("*").in("symbol", symbols);
    const out: Record<string, SessionView> = {};
    for (const r of (data ?? []) as any[])
      out[r.symbol] = { symbol: r.symbol, session: r.session, candles: r.candles ?? [], zones: r.zones ?? [], updatedAt: r.updated_at };
    return out;
  } catch {
    return {};
  }
}

export async function getDashboard(opts: Opts = {}): Promise<Dashboard> {
  const now0 = new Date().toISOString();
  const base = { bots: [], totals: EMPTY, alerts: [], portfolio: [], portfolioDaily: [], updatedAt: now0, lastCollected: now0 };
  if (!process.env.SUPABASE_URL || !process.env.SUPABASE_SERVICE_KEY)
    return { ...base, error: "Falta configurar SUPABASE_URL / SUPABASE_SERVICE_KEY en .env.local" };
  try {
    const client = sb();
    const [{ data: botsRaw }, { data: tradesRaw }, { data: snapsRaw }, { data: bopsRaw }] = await Promise.all([
      client.from("bots").select("*").eq("active", true),
      client.from("trades").select("*").order("exit_time", { ascending: true }).limit(5000),
      client.from("account_snapshots").select("account,balance,ts").order("ts", { ascending: false }).limit(1000),
      client.from("balance_ops").select("bot_id,amount").limit(2000),
    ]);
    let botsList = (botsRaw ?? []) as Bot[];
    if (opts.category) botsList = botsList.filter((b) => catOf(b.id) === opts.category);
    // Vista general (sin categoría) EXCLUYE demo/lab: son experimentos, no ensucian el portafolio real.
    else botsList = botsList.filter((b) => catOf(b.id) !== "demo");
    const botIds = new Set(botsList.map((b) => b.id));
    const trades = ((tradesRaw ?? []) as Trade[]).filter(
      (t) => botIds.has(t.bot_id) && (!opts.since || t.exit_time >= opts.since) && (!opts.until || t.exit_time < opts.until)
    );
    const health = botsList.map((b) => compute(b, trades));
    const rank = { bad: 0, warn: 1, good: 2 };
    health.sort((a, b) => rank[a.health] - rank[b.health]);
    // balance REAL del broker (refleja retiros/depósitos)
    const latestBal = new Map<number, number>();
    for (const s of (snapsRaw ?? []) as { account: number; balance: number }[])
      if (!latestBal.has(s.account)) latestBal.set(s.account, s.balance);
    // retiros/depósitos acumulados por bot (sobrevive rotaciones de cuenta)
    const wByBot = new Map<string, { w: number; d: number }>();
    for (const o of (bopsRaw ?? []) as { bot_id: string; amount: number }[]) {
      const e = wByBot.get(o.bot_id) ?? { w: 0, d: 0 };
      if (o.amount < 0) e.w += -o.amount; else e.d += o.amount;
      wByBot.set(o.bot_id, e);
    }
    for (const b of health) {
      const rb = b.account != null ? latestBal.get(b.account) : undefined;
      b.realBalance = rb ?? null;
      b.netFlows = rb != null ? rb - (b.initial_balance + b.pnlUsd) : 0;
      const w = wByBot.get(b.id);
      b.withdrawn = w?.w ?? 0; // BRUTO retirado de la cuenta (sin repartición); entra al retorno junto al colchón
      b.deposited = w?.d ?? 0; // incluye el fondeo inicial (~initial) + depósitos extra (colchón traído de otra cuenta)
      // Depósitos EXTRA = todo lo depositado por encima del fondeo inicial (el colchón que llevas a la cuenta nueva).
      // NO son ganancia de la estrategia → hay que restarlos o se cuenta doble (están en el balance actual).
      const extraDep = b.deposited >= b.initial_balance ? b.deposited - b.initial_balance : b.deposited;
      // retorno REAL = lo que generó la estrategia = (balance − inicial) + retirado − depósitos extra
      const rb2 = b.realBalance ?? b.balance;
      b.realPnl = rb2 + b.withdrawn - b.initial_balance - extraDep;
      b.realRetPct = b.initial_balance ? (b.realPnl / b.initial_balance) * 100 : 0;
    }

    const sum = (f: (b: BotHealth) => number) => health.reduce((a, b) => a + f(b), 0);
    const capital = sum((b) => b.initial_balance);
    const pnlUsd = sum((b) => b.realPnl);
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
    const rankLvl = { bad: 0, warn: 1, info: 2 };
    const alerts = health.flatMap(alertsFor);
    if (totals.retPct <= -5)
      alerts.unshift({ botId: "__portfolio__", botName: "Portafolio", level: totals.retPct <= -8 ? "bad" : "warn", msg: `Portafolio en pérdida ${totals.retPct.toFixed(1)}% del capital total` });
    alerts.sort((a, b) => rankLvl[a.level] - rankLvl[b.level]);

    // equity del portafolio: todos los trades ordenados por salida
    const sorted = [...trades].sort((a, b) => +new Date(a.exit_time) - +new Date(b.exit_time));
    let cum = capital;
    const portfolio: PortPoint[] = sorted.map((t, i) => { cum += t.pnl_usd; return { i, equity: cum, ma: null }; });
    portfolio.forEach((p, i) => {
      const from = Math.max(0, i - MA_WINDOW + 1);
      const win = portfolio.slice(from, i + 1).map((x) => x.equity);
      p.ma = win.reduce((a, b) => a + b, 0) / win.length;
    });

    const pdmap = new Map<string, { pnl: number; n: number; wins: number }>();
    for (const t of trades) {
      const d = chDate(t.exit_time);
      const e = pdmap.get(d) ?? { pnl: 0, n: 0, wins: 0 };
      e.pnl += t.pnl_usd; e.n++; if (t.pnl_usd > 0) e.wins++;
      pdmap.set(d, e);
    }
    const portfolioDaily: DayPnl[] = Array.from(pdmap.entries()).map(([date, v]) => ({ date, ...v })).sort((a, b) => a.date.localeCompare(b.date));

    const lastCollected = ((snapsRaw?.[0] as { ts?: string } | undefined)?.ts) ?? new Date().toISOString();
    return { bots: health, totals, alerts, portfolio, portfolioDaily, updatedAt: new Date().toISOString(), lastCollected };
  } catch (e) {
    return { ...base, error: String(e) };
  }
}
