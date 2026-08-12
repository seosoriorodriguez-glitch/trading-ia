import { getDashboard, periodRange, type BotHealth } from "@/lib/data";
import { AggKPI } from "@/components/cards";
import { EquityChart } from "@/components/charts";
import { Calendar } from "@/components/calendar";
import { AlertList } from "@/components/alerts";
import { PeriodSelector, TypeSelector } from "@/components/selectors";

export const dynamic = "force-dynamic";
const money = (n: number) => `$${Math.round(n).toLocaleString()}`;

function groupSummary(bots: BotHealth[]) {
  const capital = bots.reduce((a, b) => a + b.initial_balance, 0);
  const pnl = bots.reduce((a, b) => a + b.realPnl, 0);
  const n = bots.reduce((a, b) => a + b.n, 0);
  const wins = bots.reduce((a, b) => a + b.wins, 0);
  return { capital, pnl, retPct: capital ? (pnl / capital) * 100 : 0, n, wr: n ? (wins / n) * 100 : 0, nBots: bots.length };
}

export default async function Overview({ searchParams }: { searchParams: { period?: string; type?: string } }) {
  const pr = periodRange(searchParams.period);
  const category = searchParams.type === "ftmo" || searchParams.type === "darwinex" ? searchParams.type : undefined;
  const { bots, totals, alerts, portfolio, portfolioDaily, error } = await getDashboard({ since: pr.since, until: pr.until, category });
  if (error) return <div className="text-dim py-20">Sin datos: <span className="text-loss font-mono">{error}</span></div>;
  const groups = [
    { k: "FTMO", g: groupSummary(bots.filter((b) => b.category === "ftmo")), href: "/ftmo", desc: "Challenges y fondeo · profit split" },
    { k: "Darwinex", g: groupSummary(bots.filter((b) => b.category === "darwinex")), href: "/darwinex", desc: "Asignación de capital · track record" },
  ];
  const totalWithdrawn = bots.reduce((a, b) => a + b.withdrawn, 0);
  // retorno MEDIO por cuenta (equal-weight): cada cuenta sobre su propio tamaño, sin que la aplaste el nominal grande
  const avgRet = bots.length ? bots.reduce((a, b) => a + b.realRetPct, 0) / bots.length : 0;
  return (
    <div>
      <div className="flex flex-wrap items-end justify-between gap-3 mb-6">
        <div>
          <h1 className="text-2xl font-bold mb-1">Vista general</h1>
          <p className="text-sm text-dim">Todo tu portafolio · <span className="text-[#c5cfdb]">{pr.label}</span></p>
        </div>
        <div className="flex flex-col gap-2 items-start sm:items-end">
          <TypeSelector />
          <PeriodSelector />
        </div>
      </div>
      {!totals.nBots && <div className="text-dim py-16">Sin operaciones en este período.</div>}

      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-5 gap-3 mb-5">
        <AggKPI label="Capital desplegado" value={money(totals.capital)} />
        <AggKPI label="PnL total (trading)" value={`${totals.pnlUsd >= 0 ? "+" : "-"}${money(Math.abs(totals.pnlUsd))}`} sub={`${avgRet >= 0 ? "+" : ""}${avgRet.toFixed(1)}% medio por cuenta`} tone={totals.pnlUsd >= 0 ? "win" : "loss"} />
        <AggKPI label="Retirado (bruto)" value={money(totalWithdrawn)} sub={totalWithdrawn > 0 ? "ganancias retiradas" : "aún nada"} tone={totalWithdrawn > 0 ? "win" : undefined} />
        <AggKPI label="WR combinado" value={`${totals.wr.toFixed(0)}%`} sub={`${totals.nTrades} ops · ${totals.wins}G/${totals.losses}P`} />
        <AggKPI label="Estado" value={`${totals.healthy}/${totals.nBots}`} sub={totals.bad ? `${totals.bad} en alerta` : totals.warn ? `${totals.warn} en atención` : "todos sanos"} tone={totals.bad ? "loss" : totals.warn ? undefined : "win"} />
      </div>

      {bots.length > 0 && (() => {
        const ranked = [...bots].sort((a, b) => b.realRetPct - a.realRetPct);
        const maxAbs = Math.max(1, ...ranked.map((b) => Math.abs(b.realRetPct)));
        const totalPnl = ranked.reduce((a, b) => a + b.realPnl, 0);
        const sumRet = ranked.reduce((a, b) => a + b.realRetPct, 0);
        const avgRet2 = sumRet / ranked.length;
        return (
          <div className="bg-panel border border-border rounded-2xl p-5 mb-8">
            <div className="text-[10px] uppercase tracking-wider text-dim mb-4">Rentabilidad por cuenta <span className="text-[#6b7684] normal-case">· relativa a su propio tamaño</span></div>
            <div className="flex flex-col gap-3">
              {ranked.map((b) => {
                const pos = b.realRetPct >= 0;
                return (
                  <a key={b.id} href={`/bot/${b.id}`} className="group flex items-center gap-3 font-mono hover:opacity-90">
                    <div className="w-40 shrink-0 truncate text-sm font-sans group-hover:text-accent transition">
                      {b.name}<span className="text-dim text-[11px]"> · {money(b.initial_balance)}</span>
                    </div>
                    {/* barra divergente desde el centro */}
                    <div className="relative flex-1 h-5">
                      <div className="absolute inset-y-0 left-1/2 w-px bg-border" />
                      <div
                        className={`absolute inset-y-1 rounded ${pos ? "bg-win/70" : "bg-loss/70"}`}
                        style={{ left: pos ? "50%" : `${50 - (Math.abs(b.realRetPct) / maxAbs) * 50}%`, width: `${(Math.abs(b.realRetPct) / maxAbs) * 50}%` }}
                      />
                    </div>
                    <div className={`w-16 shrink-0 text-right font-semibold ${pos ? "text-win" : "text-loss"}`}>{pos ? "+" : ""}{b.realRetPct.toFixed(1)}%</div>
                    <div className="w-20 shrink-0 text-right text-[11px] text-dim">{b.realPnl >= 0 ? "+" : "-"}{money(Math.abs(b.realPnl))}</div>
                  </a>
                );
              })}
            </div>
            {/* total combinado de todas las cuentas */}
            <div className="mt-4 pt-3 border-t border-border flex items-center gap-3 font-mono">
              <div className="w-40 shrink-0 text-sm font-sans font-semibold">Total · {ranked.length} cuentas</div>
              <div className="flex-1 text-[11px] text-dim font-sans">suma de retornos (cada cuenta sobre su tamaño) · media {avgRet2 >= 0 ? "+" : ""}{avgRet2.toFixed(1)}%</div>
              <div className={`w-16 shrink-0 text-right text-lg font-bold ${sumRet >= 0 ? "text-win" : "text-loss"}`}>{sumRet >= 0 ? "+" : ""}{sumRet.toFixed(1)}%</div>
              <div className={`w-20 shrink-0 text-right text-[11px] ${totalPnl >= 0 ? "text-win" : "text-loss"}`}>{totalPnl >= 0 ? "+" : "-"}{money(Math.abs(totalPnl))}</div>
            </div>
          </div>
        );
      })()}

      <div className="grid lg:grid-cols-2 gap-5 mb-8">
        <div className="bg-panel border border-border rounded-2xl p-5">
          <div className="text-[10px] uppercase tracking-wider text-dim mb-2">Equity del portafolio (todos los bots)</div>
          <EquityChart data={portfolio} initial={totals.capital} height={220} />
        </div>
        <div className="bg-panel border border-border rounded-2xl p-5">
          <div className="text-[10px] uppercase tracking-wider text-dim mb-3">Calendario PnL del portafolio</div>
          <Calendar days={portfolioDaily} />
        </div>
      </div>

      <div className="grid md:grid-cols-2 gap-5 mb-8">
        {groups.map(({ k, g, href, desc }) => (
          <a key={k} href={href} className="bg-panel border border-border rounded-2xl p-5 hover:border-accent/50 transition block">
            <div className="flex items-center justify-between mb-3">
              <div><div className="font-semibold">{k}</div><div className="text-[11px] text-dim">{desc}</div></div>
              <span className="text-xs text-dim">{g.nBots} cuentas →</span>
            </div>
            <div className="grid grid-cols-3 gap-3 font-mono">
              <div><div className="text-[10px] uppercase text-dim">Capital</div><div className="text-lg">{money(g.capital)}</div></div>
              <div><div className="text-[10px] uppercase text-dim">PnL</div><div className={`text-lg ${g.pnl >= 0 ? "text-win" : "text-loss"}`}>{g.pnl >= 0 ? "+" : ""}{money(g.pnl)}</div></div>
              <div><div className="text-[10px] uppercase text-dim">WR</div><div className="text-lg">{g.wr.toFixed(0)}%</div></div>
            </div>
          </a>
        ))}
      </div>

      {alerts.length > 0 && (
        <div>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-lg font-semibold">Alertas activas ({alerts.length})</h2>
            <a href="/alertas" className="text-xs text-accent">ver todas →</a>
          </div>
          <AlertList alerts={alerts.slice(0, 4)} />
        </div>
      )}
    </div>
  );
}
