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
  { href: "/vivo", label: "En vivo" },
  { href: "/ftmo", label: "FTMO" },
  { href: "/darwinex", label: "Darwinex" },
  { href: "/trades", label: "Trades" },
  { href: "/demo", label: "Lab · Demo" },
  { href: "/alertas", label: "Alertas" },
];

export function Sidebar({ nBots, nAlerts, lastCollected }: { nBots: number; nAlerts: number; lastCollected: string }) {
  const path = usePathname();
  const [open, setOpen] = useState(false);
  useEffect(() => { setOpen(false); }, [path]); // cerrar el menú al navegar
  const dt = new Date(lastCollected);
  const opts = { timeZone: "America/Santiago", hour: "2-digit", minute: "2-digit", second: "2-digit" } as const;
  const fecha = dt.toLocaleDateString("es-CL", { timeZone: "America/Santiago", day: "2-digit", month: "2-digit", year: "numeric" });
  const hora = dt.toLocaleTimeString("es-CL", opts);

  const navLinks = (
    <>
      {NAV.map((n) => {
        const active = path === n.href;
        return (
          <Link key={n.href} href={n.href} className={`px-3 py-2.5 rounded-lg transition ${active ? "bg-panel2 text-white font-medium" : "text-dim hover:bg-panel2 hover:text-white"}`}>
            {n.label}
            {n.href === "/alertas" && nAlerts > 0 && <span className="ml-1 text-loss">({nAlerts})</span>}
          </Link>
        );
      })}
    </>
  );
  const footer = (
    <div className="text-[11px] font-mono text-dim leading-relaxed border-t border-border pt-3">
      <div>{nBots} bots activos</div>
      <div className={nAlerts ? "text-loss" : "text-win"}>{nAlerts ? `${nAlerts} en alerta` : "todo sano"}</div>
      <div className="mt-1.5 text-[10px]">Recolección cada 1 min</div>
      <div className="text-[#c5cfdb]" suppressHydrationWarning>últ. {fecha} · {hora}</div>
      <div><Countdown from={lastCollected} /></div>
    </div>
  );

  return (
    <>
      {/* Sidebar escritorio */}
      <aside className="hidden lg:flex flex-col w-56 shrink-0 border-r border-border bg-panel/40 px-4 py-6 sticky top-0 h-screen">
        <div className="mb-8">
          <div className="text-lg font-bold tracking-tight">Kovatia <span className="text-accent">Invest</span></div>
          <div className="text-[11px] text-dim">Panel de trading</div>
        </div>
        <nav className="flex flex-col gap-1 text-sm">{navLinks}</nav>
        <div className="mt-auto">{footer}</div>
      </aside>

      {/* Barra superior móvil */}
      <header className="lg:hidden fixed top-0 left-0 right-0 z-30 flex items-center justify-between border-b border-border bg-panel/95 backdrop-blur px-4 h-14">
        <div className="text-base font-bold tracking-tight">Kovatia <span className="text-accent">Invest</span></div>
        <button onClick={() => setOpen((o) => !o)} aria-label="Menú" className="p-2 -mr-2 text-dim hover:text-white">
          {open ? (
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M6 6l12 12M18 6L6 18" /></svg>
          ) : (
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M4 7h16M4 12h16M4 17h16" /></svg>
          )}
        </button>
      </header>

      {/* Drawer móvil */}
      {open && (
        <div className="lg:hidden fixed inset-0 z-40" onClick={() => setOpen(false)}>
          <div className="absolute inset-0 bg-black/60" />
          <nav className="absolute top-0 right-0 w-64 max-w-[80vw] h-full bg-panel border-l border-border px-4 py-5 flex flex-col gap-1 text-sm overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            <div className="text-base font-bold mb-4">Kovatia <span className="text-accent">Invest</span></div>
            {navLinks}
            <div className="mt-auto">{footer}</div>
          </nav>
        </div>
      )}
    </>
  );
}
