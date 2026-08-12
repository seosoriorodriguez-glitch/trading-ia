import { getDashboard } from "@/lib/data";
import { AlertList } from "@/components/alerts";

export const dynamic = "force-dynamic";

const REGLAS = [
  { lvl: "bad", cond: "Drawdown ≥ 8.5% (crítico) / ≥ 7% (atención)", que: "Cerca del límite FTMO 10%" },
  { lvl: "warn", cond: "WR reciente (últ. 30) < breakeven", que: "Las zonas dejan de respetarse" },
  { lvl: "warn", cond: "WR global < breakeven (≥20 ops)", que: "Cuenta no rentable en su historia" },
  { lvl: "warn", cond: "Equity bajo su media móvil", que: "Posible cambio de régimen" },
  { lvl: "bad", cond: "Cuenta en pérdida ≥ -8% / ≥ -5%", que: "Sangrado fuerte de la cuenta" },
  { lvl: "bad", cond: "Portafolio en pérdida ≥ -5%", que: "Nivel global de todo el capital" },
  { lvl: "warn", cond: "Pérdida del día ≥ -3%", que: "Cerca del límite diario 5%" },
  { lvl: "warn", cond: "Racha de 6+ pérdidas seguidas", que: "Mala racha sostenida" },
  { lvl: "info", cond: "Retorno ≥ +8% (FTMO)", que: "Cerca del pase 🟢" },
];
const DOT = { bad: "bg-loss", warn: "bg-yellow-400", info: "bg-win" };

export default async function Alertas() {
  const { alerts } = await getDashboard();
  return (
    <div className="max-w-4xl">
      <h1 className="text-2xl font-bold mb-1">Alertas {alerts.length > 0 && <span className="text-loss">({alerts.length})</span>}</h1>
      <p className="text-sm text-dim mb-6">Cada alerta indica la cuenta afectada. Se recalculan en cada recolección.</p>

      <h2 className="text-sm font-semibold text-dim uppercase tracking-wider mb-3">Activas ahora</h2>
      <AlertList alerts={alerts} />

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
