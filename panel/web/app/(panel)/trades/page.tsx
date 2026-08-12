import { getDashboard, getTradeCandles, type Trade, type Candle } from "@/lib/data";
import { BotSelector } from "@/components/selectors";
import { TradeChart } from "@/components/tradechart";
import { chDateTime } from "@/lib/tz";

export const dynamic = "force-dynamic";

function TradeCard({ t, dec, candles }: { t: Trade; dec: number; candles: Candle[] }) {
  const win = t.pnl_usd > 0;
  const fmt = (v: number) => v.toLocaleString("en-US", { minimumFractionDigits: dec, maximumFractionDigits: dec });
  return (
    <div className="bg-panel border border-border rounded-xl p-4">
      <div className="flex items-center justify-between text-xs font-mono mb-2">
        <span className="text-dim">{chDateTime(t.exit_time)}</span>
        <span className={t.direction === "long" ? "text-win" : "text-loss"}>{t.direction === "long" ? "▲ LONG" : "▼ SHORT"}</span>
        <span className={`font-semibold ${win ? "text-win" : "text-loss"}`}>{t.pnl_r != null ? `${t.pnl_r > 0 ? "+" : ""}${t.pnl_r.toFixed(2)}R` : ""} · {win ? "+" : ""}${t.pnl_usd.toFixed(0)}</span>
      </div>
      <TradeChart candles={candles} trade={t} dec={dec} />
      <div className="grid grid-cols-4 gap-2 mt-2 font-mono text-[11px] text-center">
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
  const trades = sel.recent.slice(0, 9);
  const candlesByTicket = await getTradeCandles(trades.map((t) => t.ticket));
  return (
    <div>
      <div className="flex flex-wrap items-end justify-between gap-3 mb-6">
        <div>
          <h1 className="text-2xl font-bold mb-1">Trades</h1>
          <p className="text-sm text-dim">Últimas operaciones con gráfico · {sel.name}</p>
        </div>
        <BotSelector bots={bots.map((b) => ({ id: b.id, name: b.name }))} />
      </div>
      {trades.length === 0 ? (
        <div className="text-dim py-16">Sin operaciones para esta cuenta.</div>
      ) : (
        <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-4">
          {trades.map((t) => <TradeCard key={t.ticket} t={t} dec={dec} candles={candlesByTicket[t.ticket] ?? []} />)}
        </div>
      )}
      <p className="text-xs text-dim mt-6">
        Verde = TP · Rojo = SL · Línea clara = entrada · ▲/▼ entrada · ✕ salida. Las velas se recolectan tras cada operación (colector actualizado).
      </p>
    </div>
  );
}
