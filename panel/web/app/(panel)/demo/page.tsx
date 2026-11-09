import { getDashboard, periodRange } from "@/lib/data";
import { AggKPI } from "@/components/cards";
import { LabCard } from "@/components/lab";
import { PeriodSelector } from "@/components/selectors";
import { latido } from "@/lib/lab";

export const dynamic = "force-dynamic";

export default async function Demo({ searchParams }: { searchParams: { period?: string } }) {
  const pr = periodRange(searchParams.period);
  const { bots: demo } = await getDashboard({ since: pr.since, until: pr.until, category: "demo" });
  const nTrades = demo.reduce((a, b) => a + b.n, 0);
  const wins = demo.reduce((a, b) => a + b.wins, 0);
  const wr = nTrades ? (wins / nTrades) * 100 : 0;
  const avgRet = demo.length ? demo.reduce((a, b) => a + b.retPct, 0) / demo.length : 0;
  const enLinea = demo.filter((b) => latido(b).ok).length;
  return (
    <div>
      <div className="flex flex-wrap items-end justify-between gap-3 mb-6">
        <div>
          <h1 className="text-2xl font-bold mb-1">Lab · Papel</h1>
          <p className="text-sm text-dim">
            Paper trading con los precios en vivo del bróker · no envía órdenes · <span className="text-[#c5cfdb]">no cuenta para el portafolio</span> · {pr.label}
          </p>
        </div>
        <PeriodSelector />
      </div>
      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-5 gap-3 mb-6">
        <AggKPI label="Estrategias" value={`${demo.length}`} sub={`${enLinea} en línea`} />
        <AggKPI label="Operaciones" value={`${nTrades}`} sub={`${wins}G/${nTrades - wins}P`} />
        <AggKPI label="WR combinado" value={`${wr.toFixed(0)}%`} />
        <AggKPI label="Retorno medio" value={`${avgRet >= 0 ? "+" : ""}${avgRet.toFixed(1)}%`} sub="por estrategia" tone={avgRet >= 0 ? "win" : "loss"} />
        <AggKPI label="Prometedoras" value={`${demo.filter((b) => b.n >= 15 && b.pf >= 1.2 && b.wr >= b.breakevenWr).length}`} sub="≥15 ops · PF≥1.2" tone="win" />
      </div>
      {demo.length === 0 ? (
        <div className="text-dim py-16 max-w-3xl">
          Sin estrategias en papel aún. Se agregan en <code className="text-accent">papel/config.json</code> (id <code className="text-accent">lab_…</code>) y se lanzan en el VPS con{" "}
          <code className="font-mono text-[#c5cfdb]">python papel/runner.py --feed darwinex</code>: leen precios de una terminal que ya existe, no envían órdenes y aparecen acá, aisladas del portafolio real.
        </div>
      ) : (
        <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
          {demo.map((b) => <LabCard key={b.id} b={b} />)}
        </div>
      )}
      <p className="text-xs text-dim mt-6 max-w-4xl">
        Un mes en papel sirve para comprobar que la estrategia se ejecuta como en el backtest (mecánica, costos, swap), no para saber si gana:
        con pocas decenas de trades el resultado es ruido. Cada tarjeta compara contra lo esperado por el backtest y el detalle muestra la comparación trade por trade.
      </p>
    </div>
  );
}
