import { getDashboard } from "@/lib/data";
import { BotCard, AggKPI } from "@/components/cards";

export const dynamic = "force-dynamic";
const money = (n: number) => `$${Math.round(n).toLocaleString()}`;

export default async function Ftmo() {
  const { bots } = await getDashboard();
  const ftmo = bots.filter((b) => b.category === "ftmo");
  const capital = ftmo.reduce((a, b) => a + b.initial_balance, 0);
  const pnl = ftmo.reduce((a, b) => a + b.pnlUsd, 0);
  return (
    <div>
      <h1 className="text-2xl font-bold mb-1">FTMO</h1>
      <p className="text-sm text-dim mb-6">Cuentas de challenge y fondeo · límite DD 10% · profit split</p>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        <AggKPI label="Cuentas" value={`${ftmo.length}`} />
        <AggKPI label="Capital" value={money(capital)} />
        <AggKPI label="PnL total" value={`${pnl >= 0 ? "+" : "-"}${money(Math.abs(pnl))}`} sub={`${capital ? ((pnl / capital) * 100).toFixed(1) : 0}%`} tone={pnl >= 0 ? "win" : "loss"} />
        <AggKPI label="En alerta" value={`${ftmo.filter((b) => b.health !== "good").length}`} tone={ftmo.some((b) => b.health !== "good") ? "loss" : "win"} />
      </div>
      {ftmo.length === 0 ? (
        <div className="text-dim py-16">Sin cuentas FTMO aún.</div>
      ) : (
        <div className="grid gap-5 md:grid-cols-2 2xl:grid-cols-3">
          {ftmo.map((b) => <BotCard key={b.id} b={b} href={`/bot/${b.id}`} />)}
        </div>
      )}
    </div>
  );
}
