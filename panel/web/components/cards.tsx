import { EquityChart } from "@/components/charts";
import type { BotHealth } from "@/lib/data";
import { chDateTime } from "@/lib/tz";

export const HEALTH = {
  good: { label: "SANO", cls: "bg-win/15 text-win border-win/40" },
  warn: { label: "ATENCIÓN", cls: "bg-yellow-500/15 text-yellow-400 border-yellow-500/40" },
  bad: { label: "ALERTA", cls: "bg-loss/15 text-loss border-loss/40" },
};

export function KPI({ label, value, sub, tone }: { label: string; value: string; sub?: string; tone?: "win" | "loss" | "dim" }) {
  const color = tone === "win" ? "text-win" : tone === "loss" ? "text-loss" : "text-[#e6edf3]";
  return (
    <div className="bg-panel2 rounded-lg px-3 py-2">
      <div className="text-[10px] uppercase tracking-wider text-dim">{label}</div>
      <div className={`font-mono text-lg font-semibold ${color}`}>{value}</div>
      {sub && <div className="text-[10px] text-dim font-mono">{sub}</div>}
    </div>
  );
}

export function AggKPI({ label, value, sub, tone }: { label: string; value: string; sub?: string; tone?: "win" | "loss" }) {
  const color = tone === "win" ? "text-win" : tone === "loss" ? "text-loss" : "text-[#e6edf3]";
  return (
    <div className="bg-panel border border-border rounded-xl px-4 py-3">
      <div className="text-[10px] uppercase tracking-wider text-dim">{label}</div>
      <div className={`font-mono text-2xl font-semibold ${color}`}>{value}</div>
      {sub && <div className="text-[11px] text-dim font-mono">{sub}</div>}
    </div>
  );
}

function Bar({ label, valueTxt, pct, tone }: { label: string; valueTxt: string; pct: number; tone: "win" | "loss" }) {
  return (
    <div>
      <div className="flex justify-between text-[10px] mb-0.5">
        <span className="text-dim uppercase tracking-wide">{label}</span>
        <span className={`font-mono ${tone === "win" ? "text-win" : "text-loss"}`}>{valueTxt}</span>
      </div>
      <div className="h-1.5 rounded-full bg-panel2 overflow-hidden">
        <div className={`h-full ${tone === "win" ? "bg-win" : "bg-loss"}`} style={{ width: `${Math.min(100, Math.max(0, pct))}%` }} />
      </div>
    </div>
  );
}

export function BotCard({ b, href }: { b: BotHealth; href?: string }) {
  const h = HEALTH[b.health];
  const ddNear = b.ddPct >= b.ddLimitPct * 0.7;
  return (
    <div className="bg-panel border border-border rounded-2xl p-5 flex flex-col gap-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="font-semibold text-[15px]">
            {href ? <a href={href} className="hover:text-accent transition">{b.name}</a> : b.name}
          </div>
          <div className="text-xs text-dim font-mono">{b.symbol} · #{b.account ?? "—"} · {b.session}</div>
        </div>
        <span className={`text-[10px] font-semibold px-2 py-1 rounded-md border ${h.cls}`}>{h.label}</span>
      </div>

      <div className="grid grid-cols-3 gap-2">
        <KPI label="Win Rate" value={`${b.wr.toFixed(0)}%`} sub={`breakeven ${b.breakevenWr.toFixed(0)}%`} tone={b.wr >= b.breakevenWr ? "win" : "loss"} />
        <KPI label="WR reciente" value={`${b.rollingWr.toFixed(0)}%`} sub="últ. 30" tone={b.rollingWr >= b.breakevenWr ? "win" : "loss"} />
        <KPI label="Profit Factor" value={b.pf.toFixed(2)} tone={b.pf >= 1 ? "win" : "loss"} />
        <KPI label="Retorno" value={`${b.realRetPct >= 0 ? "+" : ""}${b.realRetPct.toFixed(1)}%`} sub={`$${Math.round(b.realPnl).toLocaleString()}${b.withdrawn > 1 ? " gen." : ""}`} tone={b.realRetPct >= 0 ? "win" : "loss"} />
        <KPI label="Balance" value={`$${Math.round(b.realBalance ?? b.balance).toLocaleString()}`}
          sub={b.withdrawn > 1 ? `retirado $${Math.round(b.withdrawn).toLocaleString()}` : `de $${b.initial_balance.toLocaleString()}`} />
        <KPI label="Drawdown" value={`${b.ddPct.toFixed(1)}%`} sub={`límite ${b.ddLimitPct}%`} tone={ddNear ? "loss" : "dim"} />
      </div>

      <div>
        <div className="flex items-center justify-between mb-1">
          <span className="text-[10px] uppercase tracking-wider text-dim">Equity vs media (régimen)</span>
          <span className={`text-[10px] font-mono ${b.aboveMa ? "text-win" : "text-loss"}`}>{b.aboveMa ? "▲ sobre media" : "▼ bajo media"}</span>
        </div>
        <EquityChart data={b.equity} initial={b.initial_balance} />
      </div>

      <div className="flex items-center justify-between text-xs text-dim font-mono">
        <span>{b.n} ops · {b.wins}G/{b.losses}P</span>
        <span>hoy: {b.todayN} ops ({b.todayWins}G)</span>
      </div>

      <div className="grid grid-cols-4 gap-2 text-center border-t border-border pt-3">
        <div>
          <div className="text-[9px] uppercase tracking-wide text-dim">Expectancy</div>
          <div className={`font-mono text-sm ${b.expectancyUsd >= 0 ? "text-win" : "text-loss"}`}>{b.expectancyUsd >= 0 ? "+" : ""}${b.expectancyUsd.toFixed(0)}</div>
        </div>
        <div>
          <div className="text-[9px] uppercase tracking-wide text-dim">RRR</div>
          <div className="font-mono text-sm">{b.rrr.toFixed(2)}</div>
        </div>
        <div>
          <div className="text-[9px] uppercase tracking-wide text-dim">Racha</div>
          <div className={`font-mono text-sm ${b.streakWin ? "text-win" : "text-loss"}`}>{b.streak}{b.streakWin ? "G" : "P"}</div>
        </div>
        <div>
          <div className="text-[9px] uppercase tracking-wide text-dim">Avg W/L</div>
          <div className="font-mono text-sm">+{b.avgWinR.toFixed(1)}/{b.avgLossR.toFixed(1)}</div>
        </div>
      </div>

      {b.category === "ftmo" && (
        <div className="border-t border-border pt-3 flex flex-col gap-2">
          <div className="text-[10px] uppercase tracking-wider text-dim">{b.kind === "live" ? "Límites FTMO · fondeada" : "Objetivos FTMO · challenge"}</div>
          {b.kind === "challenge" && (
            <Bar label="Profit target (+10%)" valueTxt={`${b.retPct >= 0 ? "+" : ""}${b.retPct.toFixed(1)}% / 10%`} pct={(b.retPct / 10) * 100} tone="win" />
          )}
          <Bar label="Pérdida máx (límite 10%)" valueTxt={`${b.maxLossFromInitialPct.toFixed(1)}% / 10%`} pct={(b.maxLossFromInitialPct / 10) * 100} tone="loss" />
          <Bar label="Pérdida hoy (límite 5%)" valueTxt={`${Math.max(0, -b.dayPnlBalPct).toFixed(1)}% / 5%`} pct={(Math.max(0, -b.dayPnlBalPct) / 5) * 100} tone="loss" />
        </div>
      )}

      {b.recent.length > 0 && (
        <div className="border-t border-border pt-2">
          <div className="text-[10px] uppercase tracking-wider text-dim mb-1">Últimas operaciones</div>
          <div className="flex flex-col gap-0.5 font-mono text-[11px]">
            {b.recent.slice(0, 6).map((t) => (
              <div key={t.ticket} className="flex items-center justify-between">
                <span className="text-dim">{chDateTime(t.exit_time)}</span>
                <span className={t.direction === "long" ? "text-win" : "text-loss"}>{t.direction === "long" ? "▲" : "▼"} {t.direction}</span>
                <span className={t.pnl_usd > 0 ? "text-win" : "text-loss"}>{t.pnl_r != null ? `${t.pnl_r > 0 ? "+" : ""}${t.pnl_r.toFixed(2)}R` : ""}</span>
                <span className={t.pnl_usd > 0 ? "text-win" : "text-loss"}>{t.pnl_usd > 0 ? "+" : ""}${t.pnl_usd.toFixed(0)}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
