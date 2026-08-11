import { getDashboard } from "@/lib/data";
import { AlertList } from "@/components/alerts";

export const dynamic = "force-dynamic";

export default async function Alertas() {
  const { alerts } = await getDashboard();
  return (
    <div>
      <h1 className="text-2xl font-bold mb-1">Alertas {alerts.length > 0 && <span className="text-loss">({alerts.length})</span>}</h1>
      <p className="text-sm text-dim mb-6">DD cerca del límite · WR bajo breakeven · equity bajo media · cuenta/portafolio en pérdida · pérdida diaria · racha perdedora · cerca del pase</p>
      <AlertList alerts={alerts} />
    </div>
  );
}
