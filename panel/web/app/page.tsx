import { getDashboard, type BotHealth } from "@/lib/data";
import { EquityChart } from "@/components/charts";

export const dynamic = "force-dynamic";

const HEALTH = {
  good: { label: "SANO", cls: "bg-win/15 text-win border-win/40" },
  warn: { label: "ATENCIÓN", cls: "bg-yellow-500/15 text-yellow-400 border-yellow-500/40" },
  bad: { label: "ALERTA", cls: "bg-loss/15 text-loss border-loss/40" },
};

function KPI({ label, value, sub, tone }: { label: string; value: string; sub?: string; tone?: "win" | "loss" | "dim" }) {
  const color = tone === "win" ? "text-win" : tone === "loss" ? "text-loss" : "text-[#e6edf3]";
  return (
    <div className="bg-panel2 rounded-lg px-3 py-2">
      <div className="text-[10px] uppercase tracking-wider text-dim">{label}</div>
      <div className={`font-mono text-lg font-semibold ${color}`}>{value}</div>
      {sub && <div className="text-[10px] text-dim font-mono">{sub}</div>}
    </div>
  );
}

function BotCard({ b }: { b: BotHealth }) {
  const h = HEALTH[b.health];
  const ddNear = b.ddPct >= b.ddLimitPct * 0.7;
  return (
    <div className="bg-panel border border-border rounded-2xl p-5 flex flex-col gap-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="font-semibold text-[15px]">{b.name}</div>
          <div className="text-xs text-dim font-mono">{b.symbol} · #{b.account ?? "—"} · {b.session}</div>
        </div>
        <span className={`text-[10px] font-semibold px-2 py-1 rounded-md border ${h.cls}`}>{h.label}</span>
      </div>

      <div className="grid grid-cols-3 gap-2">
        <KPI label="Win Rate" value={`${b.wr.toFixed(0)}%`} sub={`breakeven ${b.breakevenWr.toFixed(0)}%`}
          tone={b.wr >= b.breakevenWr ? "win" : "loss"} />
        <KPI label="WR reciente" value={`${b.rollingWr.toFixed(0)}%`} sub="últ. 30"
          tone={b.rollingWr >= b.breakevenWr ? "win" : "loss"} />
        <KPI label="Profit Factor" value={b.pf.toFixed(2)} tone={b.pf >= 1 ? "win" : "loss"} />
        <KPI label="Retorno" value={`${b.retPct >= 0 ? "+" : ""}${b.retPct.toFixed(1)}%`}
          sub={`$${Math.round(b.pnlUsd).toLocaleString()}`} tone={b.retPct >= 0 ? "win" : "loss"} />
        <KPI label="Balance" value={`$${Math.round(b.balance).toLocaleString()}`} sub={`de $${b.initial_balance.toLocaleString()}`} />
        <KPI label="Drawdown" value={`${b.ddPct.toFixed(1)}%`} sub={`límite ${b.ddLimitPct}%`}
          tone={ddNear ? "loss" : "dim"} />
      </div>

      <div>
        <div className="flex items-center justify-between mb-1">
          <span className="text-[10px] uppercase tracking-wider text-dim">Equity vs media (régimen)</span>
          <span className={`text-[10px] font-mono ${b.aboveMa ? "text-win" : "text-loss"}`}>
            {b.aboveMa ? "▲ sobre media" : "▼ bajo media"}
          </span>
        </div>
        <EquityChart data={b.equity} initial={b.initial_balance} />
      </div>

      <div className="flex items-center justify-between text-xs text-dim font-mono">
        <span>{b.n} ops · {b.wins}G/{b.losses}P</span>
        <span>hoy: {b.todayN} ops ({b.todayWins}G)</span>
      </div>

      {b.recent.length > 0 && (
        <div className="border-t border-border pt-2">
          <div className="text-[10px] uppercase tracking-wider text-dim mb-1">Últimas operaciones</div>
          <div className="flex flex-col gap-0.5 font-mono text-[11px]">
            {b.recent.slice(0, 6).map((t) => (
              <div key={t.ticket} className="flex items-center justify-between">
                <span className="text-dim">{t.exit_time.slice(5, 16).replace("T", " ")}</span>
                <span className={t.direction === "long" ? "text-win" : "text-loss"}>
                  {t.direction === "long" ? "▲" : "▼"} {t.direction}
                </span>
                <span className={t.pnl_usd > 0 ? "text-win" : "text-loss"}>
                  {t.pnl_r != null ? `${t.pnl_r > 0 ? "+" : ""}${t.pnl_r.toFixed(2)}R` : ""}
                </span>
                <span className={t.pnl_usd > 0 ? "text-win" : "text-loss"}>
                  {t.pnl_usd > 0 ? "+" : ""}${t.pnl_usd.toFixed(0)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function AggKPI({ label, value, sub, tone }: { label: string; value: string; sub?: string; tone?: "win" | "loss" }) {
  const color = tone === "win" ? "text-win" : tone === "loss" ? "text-loss" : "text-[#e6edf3]";
  return (
    <div className="bg-panel border border-border rounded-xl px-4 py-3">
      <div className="text-[10px] uppercase tracking-wider text-dim">{label}</div>
      <div className={`font-mono text-2xl font-semibold ${color}`}>{value}</div>
      {sub && <div className="text-[11px] text-dim font-mono">{sub}</div>}
    </div>
  );
}

export default async function Dashboard() {
  const { bots, totals, alerts, portfolio, updatedAt, error } = await getDashboard();
  const money = (n: number) => `$${Math.round(n).toLocaleString()}`;
  return (
    <div className="flex min-h-screen">
      <meta httpEquiv="refresh" content="30" />
      <aside className="hidden lg:flex flex-col w-56 shrink-0 border-r border-border bg-panel/40 px-4 py-6 sticky top-0 h-screen">
        <div className="mb-8">
          <div className="text-lg font-semibold">Panel de Trading</div>
          <div className="text-[11px] text-dim">Salud de los bots</div>
        </div>
        <nav className="flex flex-col gap-1 text-sm">
          <a href="#overview" className="px-3 py-2 rounded-lg hover:bg-panel2 text-dim hover:text-white transition">Vista general</a>
          <a href="#alerts" className="px-3 py-2 rounded-lg hover:bg-panel2 text-dim hover:text-white transition">
            Alertas {alerts.length > 0 && <span className="text-loss">({alerts.length})</span>}
          </a>
          <a href="#bots" className="px-3 py-2 rounded-lg hover:bg-panel2 text-dim hover:text-white transition">Bots ({totals.nBots})</a>
        </nav>
        <div className="mt-auto text-[11px] font-mono text-dim leading-relaxed">
          <div>{totals.nBots} bots activos</div>
          <div className={alerts.length ? "text-loss" : "text-win"}>{alerts.length ? `${alerts.length} en alerta` : "todo sano"}</div>
          <div>act. {new Date(updatedAt).toLocaleTimeString("es-CL")}</div>
        </div>
      </aside>

      <main className="flex-1 px-5 lg:px-8 py-8 max-w-6xl">
        {error ? (
          <div className="text-dim text-sm py-20">Sin datos: <span className="text-loss font-mono">{error}</span></div>
        ) : totals.nBots === 0 ? (
          <div className="text-dim text-sm py-20">Sin datos aún. Corre el colector en el VPS para poblar el panel.</div>
        ) : (
          <>
            <section id="overview" className="mb-10 scroll-mt-4">
              <h2 className="text-xl font-semibold mb-4">Vista general</h2>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5">
                <AggKPI label="Capital desplegado" value={money(totals.capital)} />
                <AggKPI label="PnL total" value={`${totals.pnlUsd >= 0 ? "+" : "-"}${money(Math.abs(totals.pnlUsd))}`}
                  sub={`${totals.retPct >= 0 ? "+" : ""}${totals.retPct.toFixed(1)}%`} tone={totals.pnlUsd >= 0 ? "win" : "loss"} />
                <AggKPI label="WR combinado" value={`${totals.wr.toFixed(0)}%`} sub={`${totals.nTrades} ops · ${totals.wins}G/${totals.losses}P`} />
                <AggKPI label="Estado" value={`${totals.healthy}/${totals.nBots}`}
                  sub={totals.bad ? `${totals.bad} en alerta` : totals.warn ? `${totals.warn} en atención` : "todos sanos"}
                  tone={totals.bad ? "loss" : totals.warn ? undefined : "win"} />
              </div>
              <div className="bg-panel border border-border rounded-2xl p-5">
                <div className="text-[10px] uppercase tracking-wider text-dim mb-2">Equity del portafolio (todos los bots)</div>
                <EquityChart data={portfolio} initial={totals.capital} height={200} />
              </div>
            </section>

            <section id="alerts" className="mb-10 scroll-mt-4">
              <h2 className="text-xl font-semibold mb-4">
                Alertas {alerts.length > 0 && <span className="text-loss text-base">({alerts.length})</span>}
              </h2>
              {alerts.length === 0 ? (
                <div className="bg-panel border border-border rounded-xl px-4 py-4 text-sm text-win">✓ Todo sano — ninguna alerta activa.</div>
              ) : (
                <div className="flex flex-col gap-2">
                  {alerts.map((a, i) => (
                    <div key={i} className={`flex flex-wrap items-center gap-x-3 gap-y-1 rounded-xl px-4 py-3 border ${a.level === "bad" ? "bg-loss/10 border-loss/40" : "bg-yellow-500/10 border-yellow-500/40"}`}>
                      <span className={`text-[10px] font-semibold ${a.level === "bad" ? "text-loss" : "text-yellow-400"}`}>{a.level === "bad" ? "ALERTA" : "ATENCIÓN"}</span>
                      <span className="text-sm font-medium">{a.botName}</span>
                      <span className="text-sm text-dim">— {a.msg}</span>
                    </div>
                  ))}
                </div>
              )}
            </section>

            <section id="bots" className="scroll-mt-4">
              <h2 className="text-xl font-semibold mb-4">Bots ({totals.nBots})</h2>
              <div className="grid gap-5 md:grid-cols-2 2xl:grid-cols-3">
                {bots.map((b) => <BotCard key={b.id} b={b} />)}
              </div>
            </section>
          </>
        )}
      </main>
    </div>
  );
}
