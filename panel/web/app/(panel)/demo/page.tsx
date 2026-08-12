import { getDashboard, periodRange } from "@/lib/data";
import { BotCard, AggKPI } from "@/components/cards";
import { PeriodSelector } from "@/components/selectors";

export const dynamic = "force-dynamic";
const money = (n: number) => `$${Math.round(n).toLocaleString()}`;

export default async function Demo({ searchParams }: { searchParams: { period?: string } }) {
  const pr = periodRange(searchParams.period);
  const { bots: demo } = await getDashboard({ since: pr.since, until: pr.until, category: "demo" });
  const nTrades = demo.reduce((a, b) => a + b.n, 0);
  const wins = demo.reduce((a, b) => a + b.wins, 0);
  const wr = nTrades ? (wins / nTrades) * 100 : 0;
  const avgRet = demo.length ? demo.reduce((a, b) => a + b.realRetPct, 0) / demo.length : 0;
  return (
    <div>
      <div className="flex flex-wrap items-end justify-between gap-3 mb-6">
        <div>
          <h1 className="text-2xl font-bold mb-1">Lab · Demo</h1>
          <p className="text-sm text-dim">Forward-testing en cuentas demo · sin plata real · <span className="text-[#c5cfdb]">no cuenta para el portafolio</span> · {pr.label}</p>
        </div>
        <PeriodSelector />
      </div>
      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-5 gap-3 mb-6">
        <AggKPI label="Estrategias" value={`${demo.length}`} />
        <AggKPI label="Operaciones" value={`${nTrades}`} sub={`${wins}G/${nTrades - wins}P`} />
        <AggKPI label="WR combinado" value={`${wr.toFixed(0)}%`} />
        <AggKPI label="Retorno medio" value={`${avgRet >= 0 ? "+" : ""}${avgRet.toFixed(1)}%`} sub="por estrategia" tone={avgRet >= 0 ? "win" : "loss"} />
        <AggKPI label="Prometedoras" value={`${demo.filter((b) => b.n >= 15 && b.pf >= 1.2 && b.wr >= b.breakevenWr).length}`} sub="≥15 ops · PF≥1.2" tone="win" />
      </div>
      {demo.length === 0 ? (
        <div className="text-dim py-16">
          Sin estrategias demo aún. Agrega una cuenta demo al colector con un <code className="text-accent">id</code> que contenga <code className="text-accent">demo</code> o <code className="text-accent">lab</code> (ej. <span className="font-mono">demo_us30_orb</span>) y aparecerá acá, aislada del portafolio real.
        </div>
      ) : (
        <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
          {demo.map((b) => <BotCard key={b.id} b={b} href={`/bot/${b.id}`} />)}
        </div>
      )}
    </div>
  );
}
