"use client";
import { useRouter, usePathname, useSearchParams } from "next/navigation";

function useSetParam() {
  const router = useRouter();
  const path = usePathname();
  const sp = useSearchParams();
  return (key: string, val: string) => {
    const p = new URLSearchParams(sp.toString());
    if (val) p.set(key, val); else p.delete(key);
    const qs = p.toString();
    router.push(qs ? `${path}?${qs}` : path);
  };
}

const MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"];
function monthOptions() {
  const now = new Date();
  const out: { k: string; label: string }[] = [];
  for (let i = 0; i < 14; i++) {
    const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
    out.push({ k: `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`, label: `${MESES[d.getMonth()]} ${d.getFullYear()}` });
  }
  return out;
}

export function PeriodSelector() {
  const cur = useSearchParams().get("period") ?? "";
  const set = useSetParam();
  return (
    <select value={cur} onChange={(e) => set("period", e.target.value)} suppressHydrationWarning
      className="bg-panel2 border border-border rounded-lg px-3 py-1.5 text-xs text-white outline-none focus:border-accent cursor-pointer">
      <option value="">Todo</option>
      <option value="7d">Últimos 7 días</option>
      <option value="30d">Últimos 30 días</option>
      <optgroup label="Por mes">
        {monthOptions().map((m) => <option key={m.k} value={m.k}>{m.label}</option>)}
      </optgroup>
    </select>
  );
}

const TYPES = [
  { k: "", label: "Todos" },
  { k: "ftmo", label: "FTMO" },
  { k: "darwinex", label: "Darwinex" },
];

export function BotSelector({ bots }: { bots: { id: string; name: string }[] }) {
  const cur = useSearchParams().get("bot") ?? "";
  const set = useSetParam();
  return (
    <select value={cur} onChange={(e) => set("bot", e.target.value)}
      className="bg-panel2 border border-border rounded-lg px-3 py-1.5 text-xs text-white outline-none focus:border-accent cursor-pointer">
      {bots.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
    </select>
  );
}

export function TypeSelector() {
  const cur = useSearchParams().get("type") ?? "";
  const set = useSetParam();
  return (
    <div className="flex gap-1">
      {TYPES.map((t) => (
        <button key={t.k} onClick={() => set("type", t.k)}
          className={`px-3 py-1.5 rounded-lg text-xs transition ${cur === t.k ? "bg-accent text-white" : "bg-panel2 text-dim hover:text-white"}`}>
          {t.label}
        </button>
      ))}
    </div>
  );
}
