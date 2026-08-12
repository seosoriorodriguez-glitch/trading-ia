import { getDashboard } from "@/lib/data";
import { KPI, HEALTH } from "@/components/cards";
import { EquityChart, RBars } from "@/components/charts";
import { Calendar } from "@/components/calendar";
import { notFound } from "next/navigation";
import { chDateTime } from "@/lib/tz";

export const dynamic = "force-dynamic";
const money = (n: number) => `$${Math.round(n).toLocaleString()}`;

export default async function BotDetail({ params }: { params: { id: string } }) {
  const { bots } = await getDashboard();
  const b = bots.find((x) => x.id === params.id);
  if (!b) return notFound();
  const h = HEALTH[b.health];
  const rData = [...b.recent].reverse().map((t, i) => ({ i, r: t.pnl_r ?? (t.pnl_usd > 0 ? b.rr : -1) }));
  const dur = b.avgDurationMin;

  return (
    <div className="max-w-5xl">
      <a href={b.category === "darwinex" ? "/darwinex" : "/ftmo"} className="text-dim hover:text-white text-sm">← {b.category === "darwinex" ? "Darwinex" : "FTMO"}</a>
      <div className="flex items-start justify-between gap-3 mt-2 mb-6">
        <div>
          <h1 className="text-2xl font-bold">{b.name}</h1>
          <div className="text-sm text-dim font-mono">{b.symbol} · #{b.account} · {b.session} · RR {b.rr}</div>
        </div>
        <span className={`text-xs font-semibold px-2.5 py-1 rounded-md border ${h.cls}`}>{h.label}</span>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        <KPI label="Balance" value={money(b.realBalance ?? b.balance)} sub={Math.abs(b.netFlows) > 1 ? `${b.netFlows < 0 ? "retirado" : "depósito"} ${money(Math.abs(b.netFlows))}` : `de ${money(b.initial_balance)}`} />
        <KPI label="Retorno generado" value={`${b.realRetPct >= 0 ? "+" : ""}${b.realRetPct.toFixed(1)}%`} sub={`${money(b.realPnl)}${b.withdrawn > 1 ? ` · retirado ${money(b.withdrawn)}` : ""}`} tone={b.realRetPct >= 0 ? "win" : "loss"} />
        <KPI label="Win Rate" value={`${b.wr.toFixed(0)}%`} sub={`breakeven ${b.breakevenWr.toFixed(0)}%`} tone={b.wr >= b.breakevenWr ? "win" : "loss"} />
        <KPI label="Profit Factor" value={b.pf.toFixed(2)} tone={b.pf >= 1 ? "win" : "loss"} />
        <KPI label="Expectancy" value={`${b.expectancyUsd >= 0 ? "+" : ""}${money(b.expectancyUsd)}`} sub={`${b.expectancyR >= 0 ? "+" : ""}${b.expectancyR.toFixed(2)}R/op`} tone={b.expectancyUsd >= 0 ? "win" : "loss"} />
        <KPI label="RRR" value={b.rrr.toFixed(2)} sub={`avg +${money(b.avgWinUsd)}/${money(b.avgLossUsd)}`} />
        <KPI label="Drawdown" value={`${b.ddPct.toFixed(1)}%`} sub={`máx ${b.maxDdPct.toFixed(1)}% · lím 10%`} tone={b.ddPct >= 7 ? "loss" : "dim"} />
        <KPI label="Duración media" value={dur < 60 ? `${dur.toFixed(0)}m` : `${(dur / 60).toFixed(1)}h`} sub={`racha ${b.streak}${b.streakWin ? "G" : "P"}`} />
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-8 font-mono text-sm">
        {[["WR London", b.wrLondon], ["WR NY", b.wrNy], ["WR Long", b.wrLong], ["WR Short", b.wrShort]].map(([l, v]) => (
          <div key={l as string} className="bg-panel border border-border rounded-xl px-4 py-3">
            <div className="text-[10px] uppercase text-dim">{l as string}</div><div>{(v as number).toFixed(0)}%</div>
          </div>
        ))}
      </div>

      <div className="grid lg:grid-cols-2 gap-5 mb-8">
        <div className="bg-panel border border-border rounded-2xl p-5">
          <div className="flex justify-between mb-2">
            <span className="text-[10px] uppercase text-dim">Equity vs media</span>
            <span className={`text-[10px] font-mono ${b.aboveMa ? "text-win" : "text-loss"}`}>{b.aboveMa ? "▲ sobre media" : "▼ bajo media"}</span>
          </div>
          <EquityChart data={b.equity} initial={b.initial_balance} height={200} />
        </div>
        <div className="bg-panel border border-border rounded-2xl p-5">
          <div className="text-[10px] uppercase text-dim mb-2">R por operación (últimas)</div>
          <RBars data={rData} height={200} />
        </div>
      </div>

      <div className="bg-panel border border-border rounded-2xl p-5 mb-8">
        <div className="text-[10px] uppercase text-dim mb-3">Calendario PnL</div>
        <Calendar days={b.daily} />
      </div>

      <div className="bg-panel border border-border rounded-2xl p-5">
        <div className="text-[10px] uppercase text-dim mb-3">Operaciones ({b.n})</div>
        <div className="overflow-x-auto">
          <table className="w-full font-mono text-[12px] min-w-[520px]">
            <thead>
              <tr className="text-dim text-[10px] uppercase">
                <th className="text-left py-1">Salida</th><th className="text-left">Dir</th>
                <th className="text-right">Entry</th><th className="text-right">Exit</th>
                <th className="text-left pl-3">Motivo</th><th className="text-right">R</th><th className="text-right">$</th>
              </tr>
            </thead>
            <tbody>
              {b.recent.map((t) => (
                <tr key={t.ticket} className="border-t border-border/50">
                  <td className="py-1 text-dim">{chDateTime(t.exit_time)}</td>
                  <td className={t.direction === "long" ? "text-win" : "text-loss"}>{t.direction === "long" ? "▲" : "▼"} {t.direction}</td>
                  <td className="text-right">{t.entry_price}</td>
                  <td className="text-right">{t.exit_price}</td>
                  <td className="pl-3 text-dim uppercase text-[10px]">{t.exit_reason}</td>
                  <td className={`text-right ${t.pnl_usd > 0 ? "text-win" : "text-loss"}`}>{t.pnl_r != null ? `${t.pnl_r > 0 ? "+" : ""}${t.pnl_r.toFixed(2)}` : ""}</td>
                  <td className={`text-right ${t.pnl_usd > 0 ? "text-win" : "text-loss"}`}>{t.pnl_usd > 0 ? "+" : ""}${t.pnl_usd.toFixed(0)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
