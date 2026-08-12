import { getDashboard, periodRange } from "@/lib/data";
import { BotCard, AggKPI } from "@/components/cards";
import { PeriodSelector } from "@/components/selectors";

export const dynamic = "force-dynamic";
export const runtime = "edge";
const money = (n: number) => `$${Math.round(n).toLocaleString()}`;

export default async function Darwinex({ searchParams }: { searchParams: { period?: string } }) {
  const pr = periodRange(searchParams.period);
  const { bots: dx } = await getDashboard({ since: pr.since, until: pr.until, category: "darwinex" });
  const capital = dx.reduce((a, b) => a + b.initial_balance, 0);
  const pnl = dx.reduce((a, b) => a + b.realPnl, 0);
  const withdrawn = dx.reduce((a, b) => a + b.withdrawn, 0);
  return (
    <div>
      <div className="flex flex-wrap items-end justify-between gap-3 mb-6">
        <div>
          <h1 className="text-2xl font-bold mb-1">Darwinex</h1>
          <p className="text-sm text-dim">Asignación de capital · foco en track record y consistencia · <span className="text-[#c5cfdb]">{pr.label}</span></p>
        </div>
        <PeriodSelector />
      </div>
      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-5 gap-3 mb-6">
        <AggKPI label="Cuentas" value={`${dx.length}`} />
        <AggKPI label="Capital" value={money(capital)} />
        <AggKPI label="PnL generado" value={`${pnl >= 0 ? "+" : "-"}${money(Math.abs(pnl))}`} sub={`${capital ? ((pnl / capital) * 100).toFixed(1) : 0}%`} tone={pnl >= 0 ? "win" : "loss"} />
        <AggKPI label="Retirado total" value={money(withdrawn)} sub={withdrawn > 0 ? "cobrado" : "aún nada"} tone={withdrawn > 0 ? "win" : undefined} />
        <AggKPI label="En alerta" value={`${dx.filter((b) => b.health !== "good").length}`} tone={dx.some((b) => b.health !== "good") ? "loss" : "win"} />
      </div>
      {dx.length === 0 ? (
        <div className="text-dim py-16">Sin cuentas Darwinex aún.</div>
      ) : (
        <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
          {dx.map((b) => <BotCard key={b.id} b={b} href={`/bot/${b.id}`} />)}
        </div>
      )}
    </div>
  );
}
