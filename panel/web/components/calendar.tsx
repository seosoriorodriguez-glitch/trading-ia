"use client";
import { useState } from "react";
import type { DayPnl } from "@/lib/data";

const WD = ["DOM", "LUN", "MAR", "MIÉ", "JUE", "VIE", "SÁB"];
const MONTHS = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"];

export function Calendar({ days }: { days: DayPnl[] }) {
  const map = new Map(days.map((d) => [d.date, d]));
  const last = days.length ? days[days.length - 1].date : new Date().toISOString().slice(0, 10);
  const [ym, setYm] = useState(() => { const [y, m] = last.split("-").map(Number); return { y, m: m - 1 }; });

  const startDow = new Date(ym.y, ym.m, 1).getDay();
  const daysInMonth = new Date(ym.y, ym.m + 1, 0).getDate();
  const cells: (number | null)[] = [];
  for (let i = 0; i < startDow; i++) cells.push(null);
  for (let d = 1; d <= daysInMonth; d++) cells.push(d);

  const mk = (d: number) => `${ym.y}-${String(ym.m + 1).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
  const prefix = `${ym.y}-${String(ym.m + 1).padStart(2, "0")}`;
  const inMonth = days.filter((x) => x.date.startsWith(prefix));
  const monthTotal = inMonth.reduce((a, b) => a + b.pnl, 0);

  const prev = () => setYm((s) => { const d = new Date(s.y, s.m - 1, 1); return { y: d.getFullYear(), m: d.getMonth() }; });
  const next = () => setYm((s) => { const d = new Date(s.y, s.m + 1, 1); return { y: d.getFullYear(), m: d.getMonth() }; });

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <button onClick={prev} className="w-7 h-7 rounded bg-panel2 hover:bg-border text-dim">‹</button>
          <span className="font-medium min-w-[130px] text-center">{MONTHS[ym.m]} {ym.y}</span>
          <button onClick={next} className="w-7 h-7 rounded bg-panel2 hover:bg-border text-dim">›</button>
        </div>
        <div className="font-mono text-sm">
          <span className={monthTotal >= 0 ? "text-win" : "text-loss"}>{monthTotal >= 0 ? "+" : ""}${Math.round(monthTotal).toLocaleString()}</span>
          <span className="text-dim text-xs ml-2">· {inMonth.length} días op.</span>
        </div>
      </div>
      <div className="grid grid-cols-7 gap-1 text-center text-[10px] text-dim mb-1">
        {WD.map((w) => <div key={w}>{w}</div>)}
      </div>
      <div className="grid grid-cols-7 gap-1">
        {cells.map((d, i) => {
          if (d === null) return <div key={i} />;
          const info = map.get(mk(d));
          const win = info && info.pnl > 0;
          const loss = info && info.pnl < 0;
          return (
            <div key={i} className={`min-h-[54px] rounded-md border p-1 flex flex-col ${win ? "bg-win/12 border-win/30" : loss ? "bg-loss/12 border-loss/30" : "border-border/50"}`}>
              <div className="text-[10px] text-dim">{d}</div>
              {info && (
                <div className="mt-auto font-mono leading-tight">
                  <div className={`text-[11px] ${win ? "text-win" : "text-loss"}`}>{info.pnl >= 0 ? "+" : ""}{Math.round(info.pnl)}</div>
                  <div className="text-[8px] text-dim">{info.n} op</div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
