import { getDashboard, getSessionViews } from "@/lib/data";
import { SessionChart } from "@/components/sessionchart";
import { chDateTime } from "@/lib/tz";

export const dynamic = "force-dynamic";

const ASSETS = [
  { symbol: "US30.cash", name: "US30 · London", dec: 1 },
  { symbol: "GER40.cash", name: "DAX (GER40) · London", dec: 1 },
];

export default async function Vivo() {
  const [views, { bots }] = await Promise.all([
    getSessionViews(ASSETS.map((a) => a.symbol)),
    getDashboard(),
  ]);

  return (
    <div className="max-w-5xl">
      <div className="mb-6">
        <h1 className="text-2xl font-bold mb-1">En vivo · Sesión</h1>
        <p className="text-sm text-dim">Sesión actual de London con tus zonas OB (misma detección del bot) y las operaciones del día. Se refresca cada 60 s y se limpia fuera de sesión.</p>
      </div>

      <div className="flex flex-col gap-6">
        {ASSETS.map((a) => {
          const v = views[a.symbol];
          const candles = v?.candles ?? [];
          const zones = v?.zones ?? [];
          let trades: typeof bots[number]["recent"] = [];
          if (candles.length) {
            const t0 = candles[0].t, t1 = candles[candles.length - 1].t + 600;
            trades = bots
              .filter((b) => b.symbol === a.symbol)
              .flatMap((b) => b.recent)
              .filter((t) => { const xe = Date.parse(t.exit_time) / 1000; return xe >= t0 && xe <= t1; });
          }
          const bull = zones.filter((z) => z.type === "bullish").length;
          const bear = zones.filter((z) => z.type === "bearish").length;
          return (
            <div key={a.symbol} className="bg-panel border border-border rounded-2xl p-5">
              <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
                <div className="font-semibold">{a.name} <span className="text-dim font-mono text-xs">· {a.symbol}</span></div>
                <div className="flex items-center gap-3 text-[11px] font-mono text-dim">
                  {candles.length > 0 && <>
                    <span className="text-win">▢ {bull} demanda</span>
                    <span className="text-loss">▢ {bear} oferta</span>
                    <span>{trades.length} op.</span>
                    {v?.updatedAt && <span suppressHydrationWarning>· {chDateTime(v.updatedAt)}</span>}
                  </>}
                  {candles.length === 0 && <span>fuera de sesión</span>}
                </div>
              </div>
              <SessionChart candles={candles} zones={zones} trades={trades} dec={a.dec} />
            </div>
          );
        })}
      </div>

      <p className="text-xs text-dim mt-5">
        Zonas verdes = demanda (bullish OB) · rojas = oferta (bearish OB), desde su confirmación hasta el precio actual. ▲/▼ entrada · ✕ salida (verde/rojo por resultado). Las zonas destruidas se ocultan.
      </p>
    </div>
  );
}
