import { EquityChart } from "@/components/charts";
import { DiaCard, KPI } from "@/components/cards";
import type { BotHealth, Trade } from "@/lib/data";
import { LAB, latido, diasDesde, vsEsperado, compararConBacktest, simChallenge } from "@/lib/lab";
import { chDateTime, ftmoDayStart } from "@/lib/tz";

const money = (n: number) => `${n < 0 ? "-" : ""}$${Math.abs(Math.round(n)).toLocaleString()}`;

// "El día por estrategia" del laboratorio: las mismas tarjetas que las cuentas reales (día desde las 00:00 Praga,
// saldo, operación abierta) + operaciones del día, retorno desde que entró al papel y latido. Si todas tienen el mismo
// tamaño, una tarjeta más con la suma: cómo se vería tenerlas juntas en UNA cuenta (cada una con su riesgo).
export function LabDia({ bots }: { bots: BotHealth[] }) {
  const desde = +ftmoDayStart();
  const orden = [...bots].sort((a, b) => a.name.localeCompare(b.name));
  const saldo = (b: BotHealth) => b.realBalance ?? b.balance;
  const opsHoy = (b: BotHealth) => b.recent.filter((t) => +new Date(t.exit_time) >= desde).length;
  const sg = (v: number) => `${v >= 0 ? "+" : "-"}${Math.abs(v).toFixed(2)}%`;
  const base = orden[0]?.initial_balance ?? 0;
  const juntas = orden.length >= 2 && base > 0 && orden.every((b) => b.initial_balance === base);
  const suma = (f: (b: BotHealth) => number) => orden.reduce((a, b) => a + f(b), 0);
  const jDia = suma((b) => b.dayPnlBal);
  const jSaldo = base + suma((b) => saldo(b) - b.initial_balance);
  const enLinea = orden.filter((b) => latido(b).ok).length;
  return (
    <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-5 gap-3">
      {orden.map((b) => {
        const l = latido(b);
        const tot = b.initial_balance ? ((saldo(b) - b.initial_balance) / b.initial_balance) * 100 : 0;
        return (
          <DiaCard key={b.id} name={b.name} href={`/bot/${b.id}`} dia={b.dayPnlBal} diaPct={b.dayPnlBalPct}
            saldo={saldo(b)} flotante={b.floating}
            extra={<>{opsHoy(b)} ops hoy · total {sg(tot)} · <span className={l.ok ? "text-win" : "text-loss"}>{l.ok ? "●" : "○"} {l.txt}</span></>} />
        );
      })}
      {juntas && (
        <DiaCard name={`Las ${orden.length} juntas · 1 cuenta de ${money(base)}`} dia={jDia} diaPct={(jDia / base) * 100}
          saldo={jSaldo} flotante={suma((b) => b.floating)}
          extra={<>{suma(opsHoy)} ops hoy · total {sg(((jSaldo - base) / base) * 100)} · {enLinea}/{orden.length} en línea</>} />
      )}
    </div>
  );
}

export function DestinoBadge({ destino }: { destino?: string }) {
  if (!destino) return null;
  const cls = destino === "Darwinex" ? "bg-accent/15 text-accent border-accent/40" : "bg-yellow-500/15 text-yellow-400 border-yellow-500/40";
  return <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-md border ${cls}`}>→ {destino}</span>;
}

export function LatidoBadge({ b }: { b: BotHealth }) {
  const l = latido(b);
  return (
    <span className={`text-[10px] font-mono px-2 py-0.5 rounded-md border ${l.ok ? "bg-win/10 text-win border-win/40" : "bg-loss/10 text-loss border-loss/40"}`}>
      {l.ok ? "●" : "○"} {l.txt}
    </span>
  );
}

export function LabCard({ b }: { b: BotHealth }) {
  const ref = LAB[b.id];
  const dias = diasDesde(b.created_at);
  const vs = vsEsperado(b, ref);
  return (
    <div className="bg-panel border border-border rounded-2xl p-5 flex flex-col gap-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <a href={`/bot/${b.id}`} className="font-semibold text-[15px] hover:text-accent transition">{b.name}</a>
          <div className="text-xs text-dim font-mono">{b.symbol} · papel{dias != null ? ` · ${dias} d` : ""}{ref ? ` · ${ref.feed}` : ""}</div>
        </div>
        <div className="flex flex-col items-end gap-1 shrink-0">
          <DestinoBadge destino={ref?.destino} />
          <LatidoBadge b={b} />
        </div>
      </div>

      <div className="grid grid-cols-3 gap-2">
        <KPI label="Trades" value={`${b.n}`} sub={ref ? `esperado ~${ref.esperado.tradesMes}/mes` : `${b.wins}G/${b.losses}P`} />
        <KPI label="Retorno" value={`${b.retPct >= 0 ? "+" : ""}${b.retPct.toFixed(1)}%`} sub={money(b.pnlUsd)} tone={b.retPct >= 0 ? "win" : "loss"} />
        <KPI label="Profit Factor" value={b.n ? b.pf.toFixed(2) : "—"} tone={b.pf >= 1 ? "win" : "loss"} />
        <KPI label="Win Rate" value={`${b.wr.toFixed(0)}%`} sub={`breakeven ${b.breakevenWr.toFixed(0)}%`} tone={b.wr >= b.breakevenWr ? "win" : "loss"} />
        <KPI label="R total" value={`${b.sumR >= 0 ? "+" : ""}${b.sumR.toFixed(1)}R`} sub={`${b.expectancyR >= 0 ? "+" : ""}${b.expectancyR.toFixed(2)}R/trade`} tone={b.sumR >= 0 ? "win" : "loss"} />
        <KPI label="Peor caída" value={`${b.maxDdPct.toFixed(1)}%`} sub={`actual ${b.ddPct.toFixed(1)}%`} tone={b.maxDdPct >= 7 ? "loss" : "dim"} />
      </div>

      <EquityChart data={b.equity} initial={b.initial_balance} />

      {ref && (
        <div className="border-t border-border pt-3 text-[11px] font-mono flex flex-col gap-1">
          <div className="flex justify-between"><span className="text-dim">Esperado (backtest)</span><span>{ref.esperado.ePorTrade >= 0 ? "+" : ""}{ref.esperado.ePorTrade.toFixed(2)}R/trade · WR {ref.esperado.wr}%</span></div>
          <div className="flex justify-between">
            <span className="text-dim">Real vs esperado</span>
            {vs ? (
              <span className={vs.dentro ? "text-win" : "text-loss"}>{vs.dentro ? "dentro de lo normal" : vs.dif < 0 ? "por debajo de lo normal" : "por encima de lo normal"} (±{vs.banda.toFixed(2)}R)</span>
            ) : <span className="text-dim">sin trades aún</span>}
          </div>
          {vs && b.n < vs.tradesParaJuzgar && (
            <div className="text-[10px] text-dim">Con {b.n} trades todavía es ruido: hacen falta ~{vs.tradesParaJuzgar} para juzgar la ventaja. Lo que sí se juzga ya: que coincida con el backtest.</div>
          )}
        </div>
      )}

      {b.recent.length > 0 && (
        <div className="border-t border-border pt-2">
          <div className="text-[10px] uppercase tracking-wider text-dim mb-1">Últimas operaciones</div>
          <div className="flex flex-col gap-0.5 font-mono text-[11px]">
            {b.recent.slice(0, 5).map((t) => (
              <div key={t.ticket} className="flex items-center justify-between">
                <span className="text-dim">{chDateTime(t.exit_time)}</span>
                <span className={t.direction === "long" ? "text-win" : "text-loss"}>{t.direction === "long" ? "▲" : "▼"} {t.direction}</span>
                <span className="text-dim uppercase text-[10px]">{t.exit_reason}</span>
                <span className={t.pnl_usd > 0 ? "text-win" : "text-loss"}>{t.pnl_r != null ? `${t.pnl_r > 0 ? "+" : ""}${t.pnl_r.toFixed(2)}R` : ""}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// Detalle de una estrategia en papel: qué es, si el motor está vivo, lo esperado vs lo real, papel vs backtest del
// mismo período y qué habría pasado en un challenge FTMO.
export function LabDetalle({ b, papel, bt }: { b: BotHealth; papel: Trade[]; bt: Trade[] }) {
  const ref = LAB[b.id];
  const vs = vsEsperado(b, ref);
  const cmp = compararConBacktest(papel, bt);
  const ch = simChallenge(papel, b.initial_balance);
  const dias = diasDesde(b.created_at);
  const fila = "flex justify-between gap-3 py-1 border-b border-border/40 last:border-0";
  return (
    <div className="grid lg:grid-cols-2 gap-5 mb-8">
      <div className="bg-panel border border-border rounded-2xl p-5 text-sm">
        <div className="flex items-center justify-between mb-3">
          <span className="text-[10px] uppercase tracking-wider text-dim">Laboratorio en papel</span>
          <div className="flex gap-2"><DestinoBadge destino={ref?.destino} /><LatidoBadge b={b} /></div>
        </div>
        {ref && <p className="text-[12px] text-[#c5cfdb] mb-3">{ref.reglas}</p>}
        <div className="font-mono text-[12px]">
          <div className={fila}><span className="text-dim">Precios</span><span>{ref?.feed ?? b.symbol} · sin órdenes reales</span></div>
          <div className={fila}><span className="text-dim">En papel desde</span><span>{b.created_at ? `${b.created_at.slice(0, 10)} (${dias} d)` : "—"}</span></div>
          <div className={fila}><span className="text-dim">Cuenta virtual</span><span>${b.initial_balance.toLocaleString()} · {(b.risk_pct * 100).toFixed(1)}% por trade</span></div>
          {ref && <div className={fila}><span className="text-dim">Esperado (backtest)</span><span>{ref.esperado.ePorTrade >= 0 ? "+" : ""}{ref.esperado.ePorTrade.toFixed(2)}R/trade · ~{ref.esperado.tradesMes} trades/mes · WR {ref.esperado.wr}%</span></div>}
          <div className={fila}><span className="text-dim">Real en papel</span><span>{b.expectancyR >= 0 ? "+" : ""}{b.expectancyR.toFixed(2)}R/trade · {b.n} trades · WR {b.wr.toFixed(0)}%</span></div>
          {vs && (
            <div className={fila}>
              <span className="text-dim">¿Dentro de lo normal?</span>
              <span className={vs.dentro ? "text-win" : "text-loss"}>{vs.dentro ? "sí" : "no"} (banda ±{vs.banda.toFixed(2)}R con {b.n} trades)</span>
            </div>
          )}
        </div>
        {vs && b.n < vs.tradesParaJuzgar && (
          <p className="text-[11px] text-dim mt-3">
            Para saber si la ventaja es real hacen falta ~{vs.tradesParaJuzgar} trades (años). El papel sirve para comprobar que la
            ejecución coincide con el backtest: eso es lo que mira el cuadro de la derecha.
          </p>
        )}
        {ref && (
          <div className="mt-4">
            <div className="text-[10px] uppercase tracking-wider text-dim mb-1">Backtest de referencia</div>
            <table className="w-full font-mono text-[11px]">
              <thead><tr className="text-dim text-[10px]"><th className="text-left font-normal">Período</th><th className="text-right font-normal">Trades</th><th className="text-right font-normal">R</th><th className="text-right font-normal">WR</th><th className="text-right font-normal">PF</th><th className="text-right font-normal">Peor caída</th></tr></thead>
              <tbody>
                {ref.backtest.map((x) => (
                  <tr key={x.periodo} className="border-t border-border/40">
                    <td className="py-1">{x.periodo}</td><td className="text-right">{x.trades}</td>
                    <td className={`text-right ${x.R >= 0 ? "text-win" : "text-loss"}`}>{x.R >= 0 ? "+" : ""}{x.R.toFixed(1)}</td>
                    <td className="text-right">{x.wr ? `${x.wr.toFixed(0)}%` : "—"}</td><td className="text-right">{x.pf ? x.pf.toFixed(2) : "—"}</td>
                    <td className="text-right">{x.ddR.toFixed(0)}R</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="bg-panel border border-border rounded-2xl p-5 text-sm flex flex-col gap-5">
        <div>
          <div className="text-[10px] uppercase tracking-wider text-dim mb-2">Papel vs backtest del mismo período</div>
          {cmp.backtest === 0 && cmp.papel === 0 ? (
            <p className="text-[12px] text-dim">Todavía sin trades. La comparación se recalcula cada día pasada la 01:00 del servidor.</p>
          ) : (
            <>
              <div className="grid grid-cols-3 gap-2">
                <KPI label="Papel" value={`${cmp.papel}`} sub={`${cmp.rPapel >= 0 ? "+" : ""}${cmp.rPapel.toFixed(1)}R`} tone={cmp.rPapel >= 0 ? "win" : "loss"} />
                <KPI label="Backtest" value={`${cmp.backtest}`} sub={`${cmp.rBt >= 0 ? "+" : ""}${cmp.rBt.toFixed(1)}R`} tone={cmp.rBt >= 0 ? "win" : "loss"} />
                <KPI label="Coinciden" value={`${cmp.coinciden}`} sub={`de ${Math.max(cmp.papel, cmp.backtest)}`} tone={cmp.coinciden >= Math.max(cmp.papel, cmp.backtest) * 0.9 ? "win" : "loss"} />
              </div>
              <p className="text-[11px] text-dim mt-2">
                Coincide = misma dirección y entrada en el mismo minuto. El backtest corre sobre las velas de este mismo bróker; el papel llena con cada tick real,
                así que el R de cada trade puede diferir un poco (deslizamiento del SL). Si dejan de coincidir los trades, algo se ejecuta distinto: revisar antes de pasar a real.
              </p>
            </>
          )}
        </div>
        <div>
          <div className="text-[10px] uppercase tracking-wider text-dim mb-2">Si hubiera sido un challenge FTMO (+10 % · −10 % · −5 % diario)</div>
          <div className="font-mono text-[12px]">
            <div className={fila}>
              <span className="text-dim">Resultado</span>
              <span className={ch.estado === "pasaría" ? "text-win" : ch.estado === "quemaría" ? "text-loss" : ""}>
                {ch.estado}{ch.fecha ? ` (${chDateTime(ch.fecha)})` : ""}
              </span>
            </div>
            <div className={fila}><span className="text-dim">Retorno</span><span>{ch.retPct >= 0 ? "+" : ""}{ch.retPct.toFixed(1)}%</span></div>
            <div className={fila}><span className="text-dim">Lo más abajo</span><span>{ch.minPct.toFixed(1)}%</span></div>
            <div className={fila}><span className="text-dim">Peor día</span><span>{ch.peorDia.toFixed(1)}%</span></div>
          </div>
        </div>
      </div>
    </div>
  );
}
