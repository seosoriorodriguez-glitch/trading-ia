import { getDashboard, getSessionViews } from "@/lib/data";
import { SessionChart } from "@/components/sessionchart";
import { chDateTime } from "@/lib/tz";

export const dynamic = "force-dynamic";

const ASSETS = [
  { symbol: "US30.cash", name: "US30 · London", dec: 1 },
];
// Tolerancia para asociar una operacion con su zona: la orden STOP va en el borde de la
// zona (long = borde alto, short = borde bajo) y el llenado real difiere por slippage.
const TOL_ZONA_PTS = 3;

export default async function Vivo() {
  const [views, { bots }] = await Promise.all([
    getSessionViews(ASSETS.map((a) => a.symbol)),
    getDashboard(),
  ]);

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold mb-1">En vivo · Sesión</h1>
        <p className="text-sm text-dim">Sesión de London con las zonas OB que se usaron para operar y las operaciones del día. En vivo mientras corre (refresca 60 s); al terminar queda <span className="text-[#c5cfdb]">congelada</span> para analizarla, y se reinicia sola al abrir la próxima London.</p>
      </div>

      <div className="flex flex-col gap-6">
        {ASSETS.map((a) => {
          const v = views[a.symbol];
          const candles = v?.candles ?? [];
          const zonasTodas = v?.zones ?? [];
          let trades: typeof bots[number]["recent"] = [];
          if (candles.length) {
            const t0 = candles[0].t, t1 = candles[candles.length - 1].t + 600;
            // varias cuentas toman la MISMA senal: una sola marca por operacion (lado + minuto de entrada)
            const vistos = new Set<string>();
            trades = bots
              .filter((b) => b.symbol === a.symbol)
              .flatMap((b) => b.recent)
              .filter((t) => { const xe = Date.parse(t.exit_time) / 1000; return xe >= t0 && xe <= t1; })
              .sort((x, y) => Date.parse(x.entry_time) - Date.parse(y.entry_time))
              .filter((t) => {
                const k = `${t.direction}|${Math.floor(Date.parse(t.entry_time) / 60000)}`;
                if (vistos.has(k)) return false;
                vistos.add(k); return true;
              });
          }
          // solo las zonas que originaron una operacion: mismo lado, activa antes de la entrada
          // y con el borde de entrada a <= TOL_ZONA_PTS del precio llenado (la mas cercana)
          const usadas = new Set<number>();
          for (const t of trades) {
            const te = Date.parse(t.entry_time) / 1000, larga = t.direction === "long";
            let mejor = -1, dist = Infinity;
            zonasTodas.forEach((z, i) => {
              if ((z.type === "bullish") !== larga || z.at > te) return;
              const d = Math.abs((larga ? z.high : z.low) - t.entry_price);
              if (d <= TOL_ZONA_PTS && d < dist) { mejor = i; dist = d; }
            });
            if (mejor >= 0) usadas.add(mejor);
          }
          const zones = zonasTodas.filter((_, i) => usadas.has(i)).map((z) => ({ ...z, spent: false }));
          const live = v?.live ?? false;   // el colector marca en vivo vs congelada
          return (
            <div key={a.symbol} className="bg-panel border border-border rounded-2xl p-5">
              <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
                <div className="font-semibold">{a.name} <span className="text-dim font-mono text-xs">· {a.symbol}</span></div>
                <div className="flex items-center gap-3 text-[11px] font-mono text-dim">
                  {candles.length > 0 ? <>
                    <span className={live ? "text-win font-semibold" : "text-[#8a97a8]"}>{live ? "● EN VIVO" : "■ cerrada"}</span>
                    <span>{trades.length} op.</span>
                    <span>▢ {zones.length} zonas usadas <span className="text-[#6b7684]">de {zonasTodas.length} detectadas</span></span>
                    {v?.updatedAt && <span suppressHydrationWarning>· {chDateTime(v.updatedAt)}</span>}
                  </> : <span>fuera de sesión · aún sin datos de hoy</span>}
                </div>
              </div>
              <SessionChart candles={candles} zones={zones} trades={trades} dec={a.dec} height={680} />
            </div>
          );
        })}
      </div>

      <p className="text-xs text-dim mt-5">
        Solo se marcan las zonas que originaron una operación: verdes = demanda (bullish OB) · rojas = oferta (bearish OB), desde su vela de origen. ▲/▼ entrada · ✕ salida · SL/TP punteados. Cada operación aparece una vez aunque la hayan tomado varias cuentas. La banda sombreada marca la sesión de London (con ±2h de contexto antes/después).
        <br />🖱️ Arrastra el <span className="text-[#c5cfdb]">eje de precios (derecha)</span> para escalar las velas · arrastra el gráfico para moverlo · rueda para zoom · doble clic para resetear.
      </p>
    </div>
  );
}
