import { getDashboard, getFasesArchivadas, periodRange } from "@/lib/data";
import { BotCard, AggKPI } from "@/components/cards";
import { PeriodSelector } from "@/components/selectors";
import { chDate } from "@/lib/tz";

export const dynamic = "force-dynamic";
const money = (n: number) => `$${Math.round(n).toLocaleString()}`;

export default async function Ftmo({ searchParams }: { searchParams: { period?: string } }) {
  const pr = periodRange(searchParams.period);
  const [{ bots: ftmo }, { fases, error: errFases }] = await Promise.all([
    getDashboard({ since: pr.since, until: pr.until, category: "ftmo" }),
    getFasesArchivadas(),
  ]);
  const capital = ftmo.reduce((a, b) => a + b.initial_balance, 0);
  const pnl = ftmo.reduce((a, b) => a + b.realPnl, 0);
  const withdrawn = ftmo.reduce((a, b) => a + b.withdrawn, 0);
  return (
    <div>
      <div className="flex flex-wrap items-end justify-between gap-3 mb-6">
        <div>
          <h1 className="text-2xl font-bold mb-1">FTMO</h1>
          <p className="text-sm text-dim">Challenge y fondeo · límite DD 10% · profit split · <span className="text-[#c5cfdb]">{pr.label}</span></p>
        </div>
        <PeriodSelector />
      </div>
      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-5 gap-3 mb-6">
        <AggKPI label="Cuentas" value={`${ftmo.length}`} />
        <AggKPI label="Capital" value={money(capital)} />
        <AggKPI label="PnL generado" value={`${pnl >= 0 ? "+" : "-"}${money(Math.abs(pnl))}`} sub={`${capital ? ((pnl / capital) * 100).toFixed(1) : 0}%`} tone={pnl >= 0 ? "win" : "loss"} />
        <AggKPI label="Retirado (bruto)" value={money(withdrawn)} sub={withdrawn > 0 ? "ganancias retiradas" : "aún nada"} tone={withdrawn > 0 ? "win" : undefined} />
        <AggKPI label="En alerta" value={`${ftmo.filter((b) => b.health !== "good").length}`} tone={ftmo.some((b) => b.health !== "good") ? "loss" : "win"} />
      </div>
      {ftmo.length === 0 ? (
        <div className="text-dim py-16">Sin cuentas FTMO aún.</div>
      ) : (
        <div className="flex flex-col gap-8">
          {([
            { k: "live", title: "Fondeadas · Live", desc: "sin profit target · solo límites DD · profit split" },
            { k: "challenge", title: "Challenges", desc: "objetivo +10% (verificación +5%) · límite DD 10% / diario 5%" },
          ] as const).map(({ k, title, desc }) => {
            const grp = ftmo.filter((b) => b.kind === k);
            if (!grp.length) return null;
            return (
              <div key={k}>
                <div className="flex items-baseline gap-3 mb-3">
                  <h2 className="text-sm font-semibold">{title}</h2>
                  <span className="text-[11px] text-dim">{grp.length} · {desc}</span>
                </div>
                <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
                  {grp.map((b) => <BotCard key={b.id} b={b} href={`/bot/${b.id}`} />)}
                </div>
              </div>
            );
          })}
        </div>
      )}
      {errFases && <div className="mt-10 text-[11px] text-dim">Fases anteriores: {errFases}</div>}
      {fases.length > 0 && (
        <div className="mt-10">
          <div className="flex items-baseline gap-3 mb-3">
            <h2 className="text-sm font-semibold">Fases anteriores</h2>
            <span className="text-[11px] text-dim">{fases.length} · archivadas · cada fase mide lo suyo y no se suma a la cuenta actual</span>
          </div>
          <div className="bg-panel border border-border rounded-xl overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-[10px] uppercase tracking-wider text-dim">
                <tr className="border-b border-border">
                  <th className="text-left font-normal px-4 py-2">Fase</th>
                  <th className="text-left font-normal px-3 py-2">Cuenta</th>
                  <th className="text-left font-normal px-3 py-2">Fechas</th>
                  <th className="text-right font-normal px-3 py-2">Trades</th>
                  <th className="text-right font-normal px-3 py-2">WR</th>
                  <th className="text-right font-normal px-3 py-2">PnL</th>
                  <th className="text-right font-normal px-4 py-2">Retorno</th>
                </tr>
              </thead>
              <tbody className="font-mono text-xs">
                {fases.map((f) => (
                  <tr key={f.id} className="border-b border-border last:border-0">
                    <td className="px-4 py-2 font-sans">{f.name}</td>
                    <td className="px-3 py-2 text-dim">{f.account ?? "—"}</td>
                    <td className="px-3 py-2 text-dim whitespace-nowrap">{chDate(f.desde)} → {chDate(f.hasta)}</td>
                    <td className="px-3 py-2 text-right">{f.n}</td>
                    <td className="px-3 py-2 text-right">{f.wr.toFixed(0)}%</td>
                    <td className={`px-3 py-2 text-right ${f.pnlUsd >= 0 ? "text-win" : "text-loss"}`}>{f.pnlUsd >= 0 ? "+" : "-"}{money(Math.abs(f.pnlUsd))}</td>
                    <td className={`px-4 py-2 text-right ${f.retPct >= 0 ? "text-win" : "text-loss"}`}>{f.retPct >= 0 ? "+" : ""}{f.retPct.toFixed(1)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
