import { getDashboard, getSessionViews } from "@/lib/data";
import { SessionChart } from "@/components/sessionchart";
import { chDateTime } from "@/lib/tz";

export const dynamic = "force-dynamic";
export const runtime = "edge";

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
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold mb-1">En vivo · Sesión</h1>
        <p className="text-sm text-dim">Sesión de London con tus zonas OB (misma detección del bot) y las operaciones del día. En vivo mientras corre (refresca 60 s); al terminar queda <span className="text-[#c5cfdb]">congelada</span> para analizarla, y se reinicia sola al abrir la próxima London.</p>
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
          const live = v?.live ?? false;   // el colector marca en vivo vs congelada
          return (
            <div key={a.symbol} className="bg-panel border border-border rounded-2xl p-5">
              <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
                <div className="font-semibold">{a.name} <span className="text-dim font-mono text-xs">· {a.symbol}</span></div>
                <div className="flex items-center gap-3 text-[11px] font-mono text-dim">
                  {candles.length > 0 ? <>
                    <span className={live ? "text-win font-semibold" : "text-[#8a97a8]"}>{live ? "● EN VIVO" : "■ cerrada"}</span>
                    <span className="text-win">▢ {bull} demanda</span>
                    <span className="text-loss">▢ {bear} oferta</span>
                    <span>{trades.length} op.</span>
                    {v?.updatedAt && <span suppressHydrationWarning>· {chDateTime(v.updatedAt)}</span>}
                  </> : <span>fuera de sesión · aún sin datos de hoy</span>}
                </div>
              </div>
              <SessionChart candles={candles} zones={zones} trades={trades} dec={a.dec} height={440} />
            </div>
          );
        })}
      </div>

      <p className="text-xs text-dim mt-5">
        Zonas verdes = demanda (bullish OB) · rojas = oferta (bearish OB), desde su vela de origen. ▲/▼ entrada · ✕ salida · SL/TP punteados. Zonas gastadas = tenues y punteadas. La banda sombreada marca la sesión de London (con ±2h de contexto antes/después).
        <br />🖱️ Arrastra el <span className="text-[#c5cfdb]">eje de precios (derecha)</span> para escalar las velas · arrastra el gráfico para moverlo · rueda para zoom · doble clic para resetear.
      </p>
    </div>
  );
}
