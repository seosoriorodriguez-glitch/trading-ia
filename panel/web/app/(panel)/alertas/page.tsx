import { getDashboard, getVolRegime, type Alert } from "@/lib/data";
import { AlertList } from "@/components/alerts";

export const dynamic = "force-dynamic";

const VOL_SYMBOLS = ["US30.cash"];   // solo US30: los umbrales se validaron ahí

const REGLAS = [
  { lvl: "bad", cond: "Pérdida desde el inicial ≥ 8.5% / ≥ 7%", que: "Límite duro de la prop (FTMO 10%) — incluye flotante" },
  { lvl: "warn", cond: "Devolución desde el pico ≥ 7%", que: "Deterioro, NO es el límite de la prop" },
  { lvl: "warn", cond: "WR reciente (últ. 30) < breakeven", que: "Las zonas dejan de respetarse" },
  { lvl: "warn", cond: "WR global < breakeven (≥20 ops)", que: "Cuenta no rentable en su historia" },
  { lvl: "warn", cond: "Equity bajo su media móvil (30)", que: "Posible cambio de régimen" },
  { lvl: "bad", cond: "Cuenta en pérdida ≥ -8% / ≥ -5%", que: "Sangrado fuerte de la cuenta" },
  { lvl: "bad", cond: "Portafolio en pérdida ≥ -5%", que: "Nivel global de todo el capital" },
  { lvl: "bad", cond: "Pérdida del día ≥ -3.5% / ≥ -3%", que: "Equity + flotante · el bot se apaga solo en -4%" },
  { lvl: "warn", cond: "Racha de 6+ pérdidas seguidas", que: "Mala racha sostenida" },
  { lvl: "warn", cond: "Ratio de volatilidad ≥ 2.0 (rojo) / ≥ 1.6 (atención)", que: "El SL fijo se desalineó del mercado" },
  { lvl: "info", cond: "Retorno ≥ +10% / ≥ +8% (solo challenge)", que: "Pase alcanzado → parar manual · o cerca del pase 🟢" },
];
const DOT = { bad: "bg-loss", warn: "bg-yellow-400", info: "bg-win" };
const COL = { verde: "text-win", amarillo: "text-yellow-400", rojo: "text-loss" };
const ICO = { verde: "✅", amarillo: "⚠️", rojo: "🔴" };

const hora = (iso: string) =>
  new Date(iso).toLocaleString("es-CL", {
    timeZone: "America/Santiago", day: "2-digit", month: "2-digit",
    hour: "2-digit", minute: "2-digit",
  });

export default async function Alertas() {
  const [{ alerts, bots }, vol] = await Promise.all([
    getDashboard(),
    getVolRegime(VOL_SYMBOLS),
  ]);

  // ¿las operaciones reales recientes están en negativo? (2ª condición del protocolo)
  const rReciente = bots
    .filter((b) => VOL_SYMBOLS.includes(b.symbol))
    .flatMap((b) => b.recent.slice(0, 30))
    .reduce((s, t: any) => s + (Number(t.pnl_r) || 0), 0);
  const enNegativo = rReciente < 0;

  // alertas sintéticas del régimen (no tocan las reglas existentes)
  const volAlerts: Alert[] = vol
    .filter((v) => v.estado !== "verde")
    .map((v) => ({
      botId: `__vol_${v.symbol}`,
      botName: `Volatilidad · ${v.symbol}`,
      level: v.estado === "rojo" && enNegativo ? "bad" : "warn",
      msg:
        `ratio ${v.ratio.toFixed(2)} — buffer ${v.bufferActual} vs sugerido ${v.bufferSug}` +
        (v.estado === "rojo"
          ? enNegativo
            ? " · resultados recientes en negativo → CORRER EL CONTRAFACTUAL"
            : " · resultados aún positivos, solo vigilar"
          : " · vigilar mensualmente"),
    }));

  const todas = [...volAlerts, ...alerts];

  return (
    <div className="max-w-4xl">
      <h1 className="text-2xl font-bold mb-1">Alertas {todas.length > 0 && <span className="text-loss">({todas.length})</span>}</h1>
      <p className="text-sm text-dim mb-6">Cada alerta indica la cuenta afectada. Se recalculan en cada recolección.</p>

      <h2 className="text-sm font-semibold text-dim uppercase tracking-wider mb-3">Activas ahora</h2>
      <AlertList alerts={todas} />

      {/* ---------------------------- régimen de volatilidad ---------------------------- */}
      <div className="flex items-center justify-between mt-10 mb-3">
        <h2 className="text-sm font-semibold text-dim uppercase tracking-wider">Régimen de volatilidad</h2>
        <span className="text-[11px] text-dim">actualizado en cada recolección</span>
      </div>

      {vol.length === 0 ? (
        <div className="bg-panel border border-border rounded-xl px-4 py-5 text-sm text-dim">
          Aún sin datos — el colector necesita 20 sesiones de London cerradas para el primer cálculo.
        </div>
      ) : (
        <div className="bg-panel border border-border rounded-xl divide-y divide-border">
          {vol.map((v) => (
            <div key={v.symbol} className="px-4 py-4">
              <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
                <span className="font-semibold">{v.symbol}</span>
                <span className={`font-mono text-lg font-bold ${COL[v.estado]}`}>
                  {ICO[v.estado]} ratio {v.ratio.toFixed(2)}
                </span>
                <span className={`text-xs uppercase font-semibold ${COL[v.estado]}`}>{v.estado}</span>
              </div>
              <div className="mt-2 grid grid-cols-2 sm:grid-cols-4 gap-y-2 gap-x-4 text-xs font-mono">
                <div><div className="text-dim">vela M5 mediana</div><div>{v.medianaM5.toFixed(1)} pts</div></div>
                <div><div className="text-dim">buffer del bot</div><div>{v.bufferActual} pts (fijo)</div></div>
                <div><div className="text-dim">buffer sugerido</div><div>{v.bufferSug} pts</div></div>
                <div><div className="text-dim">últ. sesión medida</div><div>{v.fecha}</div></div>
              </div>
              <div className="mt-2 text-[11px] text-dim">
                mediana móvil de {v.nSesiones} sesiones de London (10:00–17:00) · {hora(v.updatedAt)}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* ------------------------------- el explicador -------------------------------- */}
      <details className="group mt-3 bg-panel border border-border rounded-xl">
        <summary className="cursor-pointer list-none px-4 py-3 text-sm flex items-center gap-2 hover:bg-panel2 rounded-xl">
          <span className="inline-flex items-center justify-center w-5 h-5 rounded-full border border-border text-xs font-bold">?</span>
          <span className="font-medium">Qué es esto y qué hacer cuando salta</span>
          <span className="ml-auto text-dim text-xs group-open:hidden">abrir</span>
          <span className="ml-auto text-dim text-xs hidden group-open:inline">cerrar</span>
        </summary>

        <div className="px-4 pb-5 pt-1 text-sm leading-relaxed border-t border-border space-y-4">
          <div>
            <div className="font-semibold mb-1">El problema que vigila</div>
            <p className="text-dim">
              El SL del bot es un buffer <span className="text-[#c5cfdb]">fijo de 35 puntos</span> más allá del borde de la zona.
              Como el RR está fijo en 2.5, ese buffer no solo define el stop: define el objetivo.
            </p>
            <pre className="mt-2 text-xs font-mono bg-panel2 rounded-lg p-3 overflow-x-auto">{`riesgo = altura_zona + buffer
TP     = entrada + riesgo × 2.5`}</pre>
            <p className="text-dim mt-2">
              Si la volatilidad se comprime, 35 puntos pasan a ser enormes en velas — y el TP se aleja
              hasta volverse inalcanzable. El bot no se entera: sigue poniendo 35.
            </p>
          </div>

          <div>
            <div className="font-semibold mb-1">El ratio</div>
            <pre className="text-xs font-mono bg-panel2 rounded-lg p-3 overflow-x-auto">{`ratio = 35 ÷ mediana(rango M5, últimas 20 sesiones de London)`}</pre>
            <p className="text-dim mt-2">
              Es tu stop medido en <span className="text-[#c5cfdb]">velas típicas</span>. En 2024 la vela M5 mediana
              era 14.6 pts → ratio 2.40 → el TP quedaba a ~9 velas. Hoy la vela es ~26 pts → ratio ~1.35 → TP a ~5 velas.
            </p>
          </div>

          <div>
            <div className="font-semibold mb-2">Los umbrales</div>
            <div className="space-y-2 text-xs">
              <div className="flex gap-3"><span className="text-win font-mono shrink-0">&lt; 1.6 verde</span>
                <span className="text-dim">Buffer alineado. Nada que hacer. Años 2020, 2022 y el actual.</span></div>
              <div className="flex gap-3"><span className="text-yellow-400 font-mono shrink-0">1.6–2.0 amarillo</span>
                <span className="text-dim">Zona de 2025 (+64%, sano pero al límite). Revisar una vez al mes.</span></div>
              <div className="flex gap-3"><span className="text-loss font-mono shrink-0">&gt; 2.0 rojo</span>
                <span className="text-dim">2021, 2023 y 2024. Un buffer adaptativo habría rendido <span className="text-[#c5cfdb]">+15 a +35 pp más al año</span>.</span></div>
            </div>
            <p className="text-dim text-xs mt-3">
              ⚠️ <span className="text-[#c5cfdb]">Rojo no significa que estés perdiendo.</span> En 2021 el ratio fue 2.15
              y el buffer fijo igual hizo +30.4%. El rojo dice que estás dejando dinero sobre la mesa, no que vayas a perder.
              Los umbrales salen de 6 años de backtest — son guías, no gatillos.
            </p>
          </div>

          <div>
            <div className="font-semibold mb-2">Protocolo cuando salta</div>
            <ol className="list-decimal ml-5 space-y-2 text-dim text-xs">
              <li>
                <span className="text-[#c5cfdb]">Confirmar.</span> El ratio solo no basta. Hacen falta las
                <span className="text-[#c5cfdb]"> dos condiciones</span>: ratio ≥ 2.0 <em>y</em> resultados reales en negativo.
                Si estás ganando, no toques nada.
              </li>
              <li>
                <span className="text-[#c5cfdb]">Diagnosticar.</span> Correr el contrafactual sobre las operaciones del mes:
                <code className="mx-1 px-1 py-0.5 rounded bg-panel2 font-mono text-[11px]">python tools/contrafactual_sl.py</code>
                Recalcula cada trade real con el buffer adaptativo y te dice si el resultado habría cambiado.
                Si el delta sigue en ≈0, <span className="text-[#c5cfdb]">el problema no es el SL</span>.
              </li>
              <li>
                <span className="text-[#c5cfdb]">Verificar el mecanismo.</span> Mirar las perdedoras: ¿se acercaron al TP
                antes de girarse? Si llegaron al 70–80% del camino, el objetivo es el problema. Si murieron temprano,
                el buffer no lo arregla y hay que buscar en otro lado.
              </li>
              <li>
                <span className="text-[#c5cfdb]">Recién ahí, corregir.</span> Dos formas de acercar el TP: bajar el buffer
                a <code className="px-1 rounded bg-panel2 font-mono text-[11px]">1.35 × mediana</code> (probado: +24 a +35 pp
                en años malos), o bajar el RR de 2.5 a 2.0 manteniendo el stop ancho (<span className="text-[#c5cfdb]">sin probar</span>).
              </li>
            </ol>
          </div>

          <div>
            <div className="font-semibold mb-1">Lo que este indicador NO hace</div>
            <p className="text-dim text-xs">
              No ajusta el SL, no manda órdenes y no toca el bot. Es un termómetro. Tampoco predice el mes:
              a escala mensual manda el ruido — agosto 2026 estuvo en amarillo por mediana propia y fue el mejor mes del año.
              Mide una sola cosa: <span className="text-[#c5cfdb]">si el buffer sigue proporcionado al mercado</span>.
            </p>
          </div>
        </div>
      </details>

      {/* --------------------------------- reglas --------------------------------- */}
      <h2 className="text-sm font-semibold text-dim uppercase tracking-wider mt-10 mb-3">Reglas configuradas (qué se vigila)</h2>
      <div className="bg-panel border border-border rounded-xl divide-y divide-border">
        {REGLAS.map((r, i) => (
          <div key={i} className="flex items-start gap-3 px-4 py-3">
            <span className={`mt-1.5 w-2 h-2 rounded-full shrink-0 ${DOT[r.lvl as keyof typeof DOT]}`} />
            <div className="min-w-0">
              <div className="text-sm font-mono">{r.cond}</div>
              <div className="text-xs text-dim">{r.que}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
