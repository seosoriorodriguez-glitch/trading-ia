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

const PERIODS = [
  { k: "", label: "Todo" },
  { k: "mes", label: "Este mes" },
  { k: "mespasado", label: "Mes pasado" },
  { k: "30d", label: "30 días" },
  { k: "7d", label: "7 días" },
];

export function PeriodSelector() {
  const cur = useSearchParams().get("period") ?? "";
  const set = useSetParam();
  return (
    <div className="flex flex-wrap gap-1">
      {PERIODS.map((p) => (
        <button key={p.k} onClick={() => set("period", p.k)}
          className={`px-3 py-1.5 rounded-lg text-xs transition ${cur === p.k ? "bg-accent text-white" : "bg-panel2 text-dim hover:text-white"}`}>
          {p.label}
        </button>
      ))}
    </div>
  );
}

const TYPES = [
  { k: "", label: "Todos" },
  { k: "ftmo", label: "FTMO" },
  { k: "darwinex", label: "Darwinex" },
];

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
