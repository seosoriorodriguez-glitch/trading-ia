"use client";
import { usePathname } from "next/navigation";
import Link from "next/link";

const NAV = [
  { href: "/", label: "Vista general" },
  { href: "/ftmo", label: "FTMO" },
  { href: "/darwinex", label: "Darwinex" },
  { href: "/alertas", label: "Alertas" },
];

export function Sidebar({ nBots, nAlerts, updatedAt }: { nBots: number; nAlerts: number; updatedAt: string }) {
  const path = usePathname();
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
      <div className="mt-auto text-[11px] font-mono text-dim leading-relaxed">
        <div>{nBots} bots activos</div>
        <div className={nAlerts ? "text-loss" : "text-win"}>{nAlerts ? `${nAlerts} en alerta` : "todo sano"}</div>
        <div>act. {new Date(updatedAt).toLocaleTimeString("es-CL")}</div>
      </div>
    </aside>
  );
}
