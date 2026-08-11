import { getDashboard } from "@/lib/data";

export const dynamic = "force-dynamic";

export default async function Alertas() {
  const { alerts } = await getDashboard();
  return (
    <div>
      <h1 className="text-2xl font-bold mb-1">Alertas {alerts.length > 0 && <span className="text-loss">({alerts.length})</span>}</h1>
      <p className="text-sm text-dim mb-6">Se disparan cuando: DD cerca del límite · WR reciente bajo el breakeven · equity bajo su media (cambio de régimen)</p>
      {alerts.length === 0 ? (
        <div className="bg-panel border border-border rounded-xl px-4 py-5 text-sm text-win">✓ Todo sano — ninguna alerta activa.</div>
      ) : (
        <div className="flex flex-col gap-2">
          {alerts.map((a, i) => (
            <div key={i} className={`flex flex-wrap items-center gap-x-3 gap-y-1 rounded-xl px-4 py-3 border ${a.level === "bad" ? "bg-loss/10 border-loss/40" : "bg-yellow-500/10 border-yellow-500/40"}`}>
              <span className={`text-[10px] font-semibold ${a.level === "bad" ? "text-loss" : "text-yellow-400"}`}>{a.level === "bad" ? "ALERTA" : "ATENCIÓN"}</span>
              <span className="text-sm font-medium">{a.botName}</span>
              <span className="text-sm text-dim">— {a.msg}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
