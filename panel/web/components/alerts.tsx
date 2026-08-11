import type { Alert } from "@/lib/data";

const STY = {
  bad: { box: "bg-loss/10 border-loss/40", tag: "text-loss", label: "ALERTA" },
  warn: { box: "bg-yellow-500/10 border-yellow-500/40", tag: "text-yellow-400", label: "ATENCIÓN" },
  info: { box: "bg-win/10 border-win/40", tag: "text-win", label: "INFO" },
};

export function AlertList({ alerts }: { alerts: Alert[] }) {
  if (!alerts.length)
    return <div className="bg-panel border border-border rounded-xl px-4 py-5 text-sm text-win">✓ Todo sano — ninguna alerta activa.</div>;
  return (
    <div className="flex flex-col gap-2">
      {alerts.map((a, i) => {
        const s = STY[a.level];
        return (
          <div key={i} className={`flex flex-wrap items-center gap-x-3 gap-y-1 rounded-xl px-4 py-3 border ${s.box}`}>
            <span className={`text-[10px] font-semibold ${s.tag}`}>{s.label}</span>
            <span className="text-sm font-medium">{a.botName}</span>
            <span className="text-sm text-dim">— {a.msg}</span>
          </div>
        );
      })}
    </div>
  );
}
