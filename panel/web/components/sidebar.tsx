"use client";
import { usePathname } from "next/navigation";
import { useState, useEffect } from "react";
import Link from "next/link";

function Countdown({ from, seconds = 60 }: { from: string; seconds?: number }) {
  const [rem, setRem] = useState<number | null>(null);
  useEffect(() => {
    const next = new Date(from).getTime() + seconds * 1000;
    const tick = () => setRem(Math.max(0, Math.ceil((next - Date.now()) / 1000)));
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [from, seconds]);
  if (rem === null) return <span suppressHydrationWarning>…</span>;
  return <span suppressHydrationWarning className={rem <= 5 ? "text-accent" : ""}>{rem > 0 ? `próxima en ${rem}s` : "recolectando…"}</span>;
}

const NAV = [
  { href: "/", label: "Vista general" },
  { href: "/ftmo", label: "FTMO" },
  { href: "/darwinex", label: "Darwinex" },
  { href: "/demo", label: "Lab · Demo" },
  { href: "/trades", label: "Trades" },
  { href: "/alertas", label: "Alertas" },
];

export function Sidebar({ nBots, nAlerts, lastCollected }: { nBots: number; nAlerts: number; lastCollected: string }) {
  const path = usePathname();
  const dt = new Date(lastCollected);
  const opts = { timeZone: "America/Santiago", hour: "2-digit", minute: "2-digit", second: "2-digit" } as const;
  const fecha = dt.toLocaleDateString("es-CL", { timeZone: "America/Santiago", day: "2-digit", month: "2-digit", year: "numeric" });
  const hora = dt.toLocaleTimeString("es-CL", opts);
  return (
    <aside className="hidden lg:flex flex-col w-56 shrink-0 border-r border-border bg-panel/40 px-4 py-6 sticky top-0 h-screen">
      <div className="mb-8">
        <div className="text-lg font-bold tracking-tight">Kovatia <span className="text-accent">Invest</span></div>
        <div className="text-[11px] text-dim">Panel de trading</div>
      </div>
      <nav className="flex flex-col gap-1 text-sm">
        {NAV.map((n) => {
          const active = path === n.href;
          return (
            <Link key={n.href} href={n.href} className={`px-3 py-2 rounded-lg transition ${active ? "bg-panel2 text-white font-medium" : "text-dim hover:bg-panel2 hover:text-white"}`}>
              {n.label}
              {n.href === "/alertas" && nAlerts > 0 && <span className="ml-1 text-loss">({nAlerts})</span>}
            </Link>
          );
        })}
      </nav>
      <div className="mt-auto text-[11px] font-mono text-dim leading-relaxed border-t border-border pt-3">
        <div>{nBots} bots activos</div>
        <div className={nAlerts ? "text-loss" : "text-win"}>{nAlerts ? `${nAlerts} en alerta` : "todo sano"}</div>
        <div className="mt-1.5 text-[10px]">Recolección cada 1 min</div>
        <div className="text-[#c5cfdb]" suppressHydrationWarning>últ. {fecha} · {hora}</div>
        <div><Countdown from={lastCollected} /></div>
      </div>
    </aside>
  );
}
