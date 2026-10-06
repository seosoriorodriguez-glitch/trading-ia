import { getDashboard, periodRange, type BotHealth } from "@/lib/data";
import { chToday } from "@/lib/tz";
import { AggKPI } from "@/components/cards";
import { PctLines } from "@/components/pctlines";
import { Calendar } from "@/components/calendar";
import { AlertList } from "@/components/alerts";
import { PeriodSelector, TypeSelector } from "@/components/selectors";

export const dynamic = "force-dynamic";
const money = (n: number) => `$${Math.round(n).toLocaleString()}`;
const ESTRATEGIA_ACTUAL_DESDE = "2026-06-01";
const REF_MENSUAL = "us30_live_10k";   // cuenta de referencia para la rentabilidad por mes
const MESES_CORTOS = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"];

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
  // series de retorno % acumulado por cuenta (alineadas por fecha), cada una con su color
  const pctPalette = ["#26a69a", "#3b82f6", "#f59e0b", "#ef5350", "#a855f7", "#e879f9"];
  // Con el periodo "Todo" la curva arranca el 01-jun-2026: desde ahi opera la estrategia
  // actual (corte de sesion London a las 17:00). Lo anterior era otra config y ensucia la
  // comparacion. Si se elige un periodo, se respeta el periodo.
  const curvaDesde = pr.since ? "" : ESTRATEGIA_ACTUAL_DESDE;
  const allDates = Array.from(new Set(bots.flatMap((b) => b.daily.map((d) => d.date))))
    .filter((d) => d >= curvaDesde).sort();
  const shortSize = (n: number) => (n >= 1000 ? `${Math.round(n / 1000)}k` : `${n}`);
  const pctSeries = bots.map((b, i) => {
    const dm = new Map(b.daily.map((d) => [d.date, d.pnl]));
    let cum = 0;
    const points = allDates.map((date) => { cum += dm.get(date) ?? 0; return b.initial_balance ? (cum / b.initial_balance) * 100 : 0; });
    const tag = b.category === "ftmo" ? (b.kind === "live" ? " Live" : " Chall") : "";
    const label = `${b.name.split("—")[0].trim()} ${shortSize(b.initial_balance)}${tag}`;
    return { name: label, color: pctPalette[i % pctPalette.length], points };
  });
  // Cuenta de referencia (10k live): tarjetas de estrategia + rentabilidad por mes. Siempre
  // con su historial COMPLETO desde 01-jun, sin importar el periodo o el tipo elegido.
  const ref = (pr.since || category)
    ? (await getDashboard({})).bots.find((b) => b.id === REF_MENSUAL)
    : bots.find((b) => b.id === REF_MENSUAL);
  // % del mes = PnL del mes / tamano de la cuenta: mismo criterio que la curva (no compuesto).
  const mensual = new Map<string, number[]>();   // año -> 12 meses (NaN = sin operar)
  if (ref?.initial_balance) {
    for (const d of ref.daily) {
      if (d.date < ESTRATEGIA_ACTUAL_DESDE) continue;
      const [y, m] = d.date.split("-");
      if (!mensual.has(y)) mensual.set(y, Array(12).fill(NaN));
      const arr = mensual.get(y)!;
      const i = Number(m) - 1;
      arr[i] = (Number.isNaN(arr[i]) ? 0 : arr[i]) + (d.pnl / ref.initial_balance) * 100;
    }
  }
  const anios = Array.from(mensual.keys()).sort();
  const sumaAnio = (a: number[]) => a.reduce((s, v) => s + (Number.isNaN(v) ? 0 : v), 0);
  const totalMensual = anios.reduce((s, y) => s + sumaAnio(mensual.get(y)!), 0);
  const pct = (v: number) => `${v >= 0 ? "" : "-"}${Math.abs(v).toFixed(2)}%`;

  // --- Tarjetas de la estrategia (cuenta de referencia), en % y en R (1R = riesgo por trade)
  const unidadR = ref ? ref.initial_balance * (ref.risk_pct || 0.005) : 0;
  const diasRef = (ref?.daily ?? []).filter((d) => d.date >= ESTRATEGIA_ACTUAL_DESDE);
  const mesActual = chToday().slice(0, 7);
  const delMes = diasRef.filter((d) => d.date.startsWith(mesActual));
  const mesPnl = delMes.reduce((a, d) => a + d.pnl, 0);
  const mesN = delMes.reduce((a, d) => a + d.n, 0);
  const totPnl = diasRef.reduce((a, d) => a + d.pnl, 0);
  const totN = diasRef.reduce((a, d) => a + d.n, 0);
  const aR = (usd: number) => (unidadR ? usd / unidadR : 0);
  const aPct = (usd: number) => (ref?.initial_balance ? (usd / ref.initial_balance) * 100 : 0);
  // Drawdown en R sobre el cierre de cada dia (no ve el intradia). Umbrales = las reglas
  // acordadas: peor visto en vivo ~17R; preocuparse si pasa de ~20R.
  let cumR = 0, picoR = 0, ddMaxR = 0;
  for (const d of diasRef) { cumR += aR(d.pnl); picoR = Math.max(picoR, cumR); ddMaxR = Math.max(ddMaxR, picoR - cumR); }
  const ddNowR = picoR - cumR;
  const sgn = (v: number, dec = 1) => `${v >= 0 ? "+" : "-"}${Math.abs(v).toFixed(dec)}`;
  // --- Margen FTMO: la cuenta FTMO mas cerca del limite de perdida maxima (10% desde el
  // balance inicial, con flotante) y su perdida del dia (limite 5%). Mismo calculo que las alertas.
  const margenes = bots.filter((b) => b.category === "ftmo" && b.initial_balance).map((b) => {
    const eqNow = (b.realBalance ?? b.balance) + b.floating;
    const lossIni = Math.max(0, ((b.initial_balance - eqNow) / b.initial_balance) * 100);
    const dia = b.dayPnlBalPct + (b.floating / b.initial_balance) * 100;
    return { b, lossIni, dia };
  }).sort((x, y) => y.lossIni - x.lossIni || x.dia - y.dia);
  const peor = margenes[0];
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

      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3 mb-5">
        <AggKPI label="Retirado · ganado" value={money(totalWithdrawn)} sub={totalWithdrawn > 0 ? "efectivo cobrado" : "aún nada"} tone={totalWithdrawn > 0 ? "win" : undefined} />
        <AggKPI label="Estrategia · este mes" value={ref ? `${sgn(aPct(mesPnl), 2)}%` : "—"} sub={ref ? `${sgn(aR(mesPnl))}R · ${mesN} ops · ref. 10k` : "sin cuenta de referencia"} tone={!ref ? undefined : mesPnl >= 0 ? "win" : "loss"} />
        <AggKPI label="Estrategia · desde 01-jun" value={ref ? `${sgn(aPct(totPnl))}%` : "—"} sub={ref ? `${sgn(aR(totPnl))}R · ${totN} ops · ref. 10k` : ""} tone={!ref ? undefined : totPnl >= 0 ? "win" : "loss"} />
        <AggKPI label="Drawdown actual" value={ref ? `${ddNowR > 0.05 ? "-" : ""}${ddNowR.toFixed(1)}R` : "—"} sub={ref ? `peor visto ${ddMaxR.toFixed(1)}R · alerta > 20R` : ""} tone={!ref ? undefined : ddNowR >= 20 ? "loss" : ddNowR < 10 ? "win" : undefined} />
        <AggKPI label="Margen FTMO · más ajustado" value={peor ? `${peor.lossIni.toFixed(1)}% / 10%` : "—"} sub={peor ? `${peor.b.name.split("—").pop()?.trim()} · día ${sgn(peor.dia)}% / -5%` : "sin cuentas FTMO"} tone={!peor ? undefined : peor.lossIni >= 7 || peor.dia <= -3.5 ? "loss" : peor.lossIni < 5 && peor.dia > -2.5 ? "win" : undefined} />
        <AggKPI label="Estado" value={`${totals.healthy}/${totals.nBots}`} sub={totals.bad ? `${totals.bad} en alerta` : totals.warn ? `${totals.warn} en atención` : "todos sanos"} tone={totals.bad ? "loss" : totals.warn ? undefined : "win"} />
      </div>

      {bots.length > 0 && (
        <div className="mb-8">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold">El día por cuenta</h2>
            <span className="text-[10px] text-dim font-mono">reinicia 18:00 CL · 00:00 CEST (regla diaria FTMO)</span>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-5 gap-3">
            {bots.map((b) => {
              const pos = b.dayPnlBal >= 0;
              return (
                <a key={b.id} href={`/bot/${b.id}`} className="bg-panel border border-border rounded-xl px-4 py-3 hover:border-accent/50 transition block">
                  <div className="flex items-center justify-between gap-2 mb-0.5">
                    <span className="text-[11px] text-dim truncate">{b.name}</span>
                    {Math.abs(b.floating) >= 0.01 && (
                      <span className={`text-[9px] font-mono px-1.5 py-0.5 rounded shrink-0 ${b.floating >= 0 ? "bg-win/15 text-win" : "bg-loss/15 text-loss"}`}>
                        ● abierta {b.floating >= 0 ? "+" : "-"}{money(Math.abs(b.floating))}
                      </span>
                    )}
                  </div>
                  <div className={`font-mono text-lg sm:text-xl font-semibold tabular-nums truncate ${pos ? "text-win" : "text-loss"}`}>{pos ? "+" : "-"}{money(Math.abs(b.dayPnlBal))}</div>
                  <div className="text-[11px] font-mono text-dim truncate">
                    <span className={pos ? "text-win" : "text-loss"}>{pos ? "+" : ""}{b.dayPnlBalPct.toFixed(2)}%</span> · saldo {money(b.realBalance ?? b.balance)}
                    {Math.abs(b.floating) >= 0.01 && <span className="text-dim"> · c/flot. {money((b.realBalance ?? b.balance) + b.floating)}</span>}
                  </div>
                </a>
              );
            })}
          </div>
        </div>
      )}


      <div className="grid lg:grid-cols-2 gap-5 mb-8 items-start">
        <div className="bg-panel border border-border rounded-2xl p-5">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[10px] uppercase tracking-wider text-dim">Retorno % por cuenta <span className="text-[#6b7684] normal-case">· {curvaDesde ? "desde 01-jun (estrategia actual) · " : ""}relativo a su tamaño · arrastra/rueda para escalar</span></span>
          </div>
          <PctLines series={pctSeries} dates={allDates} height={300} />
          <div className="flex flex-wrap gap-x-4 gap-y-1 mt-3 text-[11px] font-mono">
            {pctSeries.map((s) => {
              const last = s.points[s.points.length - 1] ?? 0;
              return (
                <span key={s.name} className="flex items-center gap-1.5">
                  <span style={{ background: s.color }} className="w-2.5 h-2.5 rounded-sm inline-block shrink-0" />
                  <span className="text-dim">{s.name}</span>
                  <span style={{ color: s.color }}>{last >= 0 ? "+" : ""}{last.toFixed(1)}%</span>
                </span>
              );
            })}
          </div>
        </div>
        <div className="bg-panel border border-border rounded-2xl p-5">
          <div className="text-[10px] uppercase tracking-wider text-dim mb-3">Calendario PnL del portafolio</div>
          <Calendar days={portfolioDaily} />
        </div>
      </div>

      {anios.length > 0 && (
        <div className="bg-panel border border-border rounded-2xl p-5 mb-8">
          <div className="flex flex-wrap items-baseline justify-between gap-2 mb-4">
            <h2 className="text-lg font-semibold">Rentabilidad por mes</h2>
            <span className="text-[10px] text-dim">referencia: {ref?.name} · desde 01-jun-2026 (estrategia actual) · % sobre el tamaño de la cuenta</span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[760px] font-mono text-sm tabular-nums">
              <thead>
                <tr className="text-[11px] text-dim">
                  <th className="text-left font-normal pb-3 w-14"></th>
                  {MESES_CORTOS.map((m) => <th key={m} className="font-normal pb-3 text-right">{m}</th>)}
                  <th className="font-normal pb-3 text-right">Año</th>
                </tr>
              </thead>
              <tbody>
                {anios.map((y) => {
                  const arr = mensual.get(y)!;
                  const tot = sumaAnio(arr);
                  return (
                    <tr key={y} className="border-t border-border">
                      <td className="py-3 text-left text-[12px] font-semibold font-sans">{y}</td>
                      {arr.map((v, i) => (
                        <td key={i} className={`py-3 text-right ${Number.isNaN(v) ? "text-dim" : v >= 0 ? "text-win" : "text-loss"}`}>
                          {Number.isNaN(v) ? "—" : pct(v)}
                        </td>
                      ))}
                      <td className={`py-3 text-right font-semibold ${tot >= 0 ? "text-win" : "text-loss"}`}>{pct(tot)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <div className="mt-4 pt-3 border-t border-border flex items-end justify-end gap-3">
            <span className="text-[11px] text-dim">Rentabilidad total</span>
            <span className={`font-mono text-2xl font-bold ${totalMensual >= 0 ? "text-win" : "text-loss"}`}>{pct(totalMensual)}</span>
          </div>
        </div>
      )}

      <div className="grid md:grid-cols-2 gap-5 mb-8">
        {groups.map(({ k, g, href, desc }) => (
          <a key={k} href={href} className="bg-panel border border-border rounded-2xl p-5 hover:border-accent/50 transition block">
            <div className="flex items-center justify-between mb-3">
              <div><div className="font-semibold">{k}</div><div className="text-[11px] text-dim">{desc}</div></div>
              <span className="text-xs text-dim">{g.nBots} cuentas →</span>
            </div>
            <div className="grid grid-cols-3 gap-2 sm:gap-3 font-mono">
              <div className="min-w-0"><div className="text-[10px] uppercase text-dim truncate">Capital</div><div className="text-base sm:text-lg tabular-nums truncate">{money(g.capital)}</div></div>
              <div className="min-w-0"><div className="text-[10px] uppercase text-dim truncate">PnL</div><div className={`text-base sm:text-lg tabular-nums truncate ${g.pnl >= 0 ? "text-win" : "text-loss"}`}>{g.pnl >= 0 ? "+" : ""}{money(g.pnl)}</div></div>
              <div className="min-w-0"><div className="text-[10px] uppercase text-dim truncate">WR</div><div className="text-base sm:text-lg tabular-nums truncate">{g.wr.toFixed(0)}%</div></div>
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
