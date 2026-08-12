import { getDashboard, periodRange } from "@/lib/data";
import { BotCard, AggKPI } from "@/components/cards";
import { PeriodSelector } from "@/components/selectors";

export const dynamic = "force-dynamic";
const money = (n: number) => `$${Math.round(n).toLocaleString()}`;

export default async function Ftmo({ searchParams }: { searchParams: { period?: string } }) {
  const pr = periodRange(searchParams.period);
  const { bots: ftmo } = await getDashboard({ since: pr.since, until: pr.until, category: "ftmo" });
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
            { k: "challenge", title: "Challenges", desc: "objetivo +10% · límite DD 10% / diario 5%" },
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
    </div>
  );
}
