import { getDashboard, type Trade } from "@/lib/data";
import { BotSelector } from "@/components/selectors";

export const dynamic = "force-dynamic";

function Marker({ pct, color, label }: { pct: number; color: string; label: string }) {
  return (
    <div className="absolute -translate-x-1/2 flex flex-col items-center" style={{ left: `${pct}%` }}>
      <div className={`w-px h-6 ${color}`} />
      <div className="text-[8px] text-dim mt-0.5">{label}</div>
    </div>
  );
}

function LevelBar({ t }: { t: Trade }) {
  const vals = [t.sl, t.tp, t.entry_price, t.exit_price].filter((v) => v != null) as number[];
  const lo = Math.min(...vals), hi = Math.max(...vals), span = hi - lo || 1;
  const pct = (v: number) => ((v - lo) / span) * 100;
  const win = t.pnl_usd > 0;
  return (
    <div className="relative h-11 mt-2">
      <div className="absolute top-3 left-0 right-0 h-px bg-border" />
      {t.sl != null && <div className="absolute top-0"><Marker pct={pct(t.sl)} color="bg-loss" label="SL" /></div>}
      {t.tp != null && <div className="absolute top-0"><Marker pct={pct(t.tp)} color="bg-win" label="TP" /></div>}
      <div className="absolute top-0"><Marker pct={pct(t.entry_price)} color="bg-[#8a97a8]" label="entry" /></div>
      <div className="absolute top-1 -translate-x-1/2" style={{ left: `${pct(t.exit_price)}%` }}>
        <div className={`w-3 h-3 rounded-full border-2 border-bg ${win ? "bg-win" : "bg-loss"}`} title="salida" />
      </div>
    </div>
  );
}

function TradeCard({ t, dec }: { t: Trade; dec: number }) {
  const win = t.pnl_usd > 0;
  const fmt = (v: number) => v.toLocaleString("en-US", { minimumFractionDigits: dec, maximumFractionDigits: dec });
  return (
    <div className="bg-panel border border-border rounded-xl p-4">
      <div className="flex items-center justify-between text-xs font-mono mb-1">
        <span className="text-dim">{t.exit_time.slice(0, 16).replace("T", " ")}</span>
        <span className={t.direction === "long" ? "text-win" : "text-loss"}>{t.direction === "long" ? "▲ LONG" : "▼ SHORT"}</span>
        <span className={`font-semibold ${win ? "text-win" : "text-loss"}`}>{t.pnl_r != null ? `${t.pnl_r > 0 ? "+" : ""}${t.pnl_r.toFixed(2)}R` : ""} · {win ? "+" : ""}${t.pnl_usd.toFixed(0)}</span>
      </div>
      <LevelBar t={t} />
      <div className="grid grid-cols-4 gap-2 mt-1 font-mono text-[11px] text-center">
        <div><span className="text-dim text-[9px] block">ENTRY</span>{fmt(t.entry_price)}</div>
        <div><span className="text-loss text-[9px] block">SL</span>{t.sl != null ? fmt(t.sl) : "—"}</div>
        <div><span className="text-win text-[9px] block">TP</span>{t.tp != null ? fmt(t.tp) : "—"}</div>
        <div><span className="text-dim text-[9px] block">SALIDA ({t.exit_reason})</span>{fmt(t.exit_price)}</div>
      </div>
    </div>
  );
}

export default async function Trades({ searchParams }: { searchParams: { bot?: string } }) {
  const { bots } = await getDashboard();
  if (!bots.length) return <div className="text-dim py-20">Sin datos aún.</div>;
  const sel = bots.find((b) => b.id === searchParams.bot) ?? bots[0];
  const dec = sel.symbol.includes("XAU") ? 2 : 1;
  const trades = sel.recent.slice(0, 8);
  return (
    <div className="max-w-4xl">
      <div className="flex flex-wrap items-end justify-between gap-3 mb-6">
        <div>
          <h1 className="text-2xl font-bold mb-1">Trades</h1>
          <p className="text-sm text-dim">Últimas operaciones · {sel.name}</p>
        </div>
        <BotSelector bots={bots.map((b) => ({ id: b.id, name: b.name }))} />
      </div>
      {trades.length === 0 ? (
        <div className="text-dim py-16">Sin operaciones para esta cuenta.</div>
      ) : (
        <div className="grid md:grid-cols-2 gap-4">
          {trades.map((t) => <TradeCard key={t.ticket} t={t} dec={dec} />)}
        </div>
      )}
      <p className="text-xs text-dim mt-6">
        📊 El gráfico de velas por operación (como los del backtest) requiere recolectar las velas M5 alrededor de cada trade — lo agrego al colector como siguiente paso.
      </p>
    </div>
  );
}
