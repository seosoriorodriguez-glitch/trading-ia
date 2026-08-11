"use client";
import { useRef, useEffect } from "react";

type Candle = { t: number; o: number; h: number; l: number; c: number };
type T = {
  entry_price: number; sl: number | null; tp: number | null; exit_price: number;
  entry_time: string; exit_time: string; direction: string; exit_reason: string;
};

export function TradeChart({ candles, trade, dec = 1 }: { candles: Candle[]; trade: T; dec?: number }) {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const cv = ref.current;
    if (!cv || !candles.length) return;
    const draw = () => {
      const ctx = cv.getContext("2d");
      if (!ctx) return;
      const dpr = Math.min(devicePixelRatio || 1, 2);
      const W = cv.clientWidth, H = 180;
      cv.width = W * dpr; cv.height = H * dpr; cv.style.height = H + "px"; ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      const PL = 6, PR = 58, PT = 8, PB = 8;
      const lv = [trade.entry_price, trade.exit_price, trade.sl, trade.tp].filter((v) => v != null) as number[];
      let lo = Math.min(...candles.map((c) => c.l), ...lv);
      let hi = Math.max(...candles.map((c) => c.h), ...lv);
      const pad = (hi - lo) * 0.05 || 1; lo -= pad; hi += pad;
      const X = (i: number) => PL + (i + 0.5) * ((W - PL - PR) / candles.length);
      const Y = (p: number) => PT + ((hi - p) / (hi - lo)) * (H - PT - PB);
      ctx.clearRect(0, 0, W, H);
      ctx.font = "10px ui-monospace,monospace"; ctx.textBaseline = "middle"; ctx.textAlign = "left";
      for (let s = 0; s <= 3; s++) {
        const p = lo + ((hi - lo) * s) / 3, y = Y(p);
        ctx.strokeStyle = "rgba(255,255,255,.05)"; ctx.beginPath(); ctx.moveTo(PL, y); ctx.lineTo(W - PR, y); ctx.stroke();
        ctx.fillStyle = "#8a97a8"; ctx.fillText(p.toFixed(dec), W - PR + 5, y);
      }
      const cw = Math.max(1.2, Math.min(6, ((W - PL - PR) / candles.length) * 0.6));
      candles.forEach((c, i) => {
        const up = c.c >= c.o; ctx.strokeStyle = ctx.fillStyle = up ? "#26a69a" : "#ef5350";
        const x = X(i); ctx.lineWidth = 1; ctx.beginPath(); ctx.moveTo(x, Y(c.h)); ctx.lineTo(x, Y(c.l)); ctx.stroke();
        const yo = Y(c.o), yc = Y(c.c); ctx.fillRect(x - cw / 2, Math.min(yo, yc), cw, Math.max(1, Math.abs(yc - yo)));
      });
      const line = (p: number | null, col: string) => {
        if (p == null) return; ctx.strokeStyle = col; ctx.setLineDash([4, 3]); ctx.lineWidth = 1;
        ctx.beginPath(); ctx.moveTo(PL, Y(p)); ctx.lineTo(W - PR, Y(p)); ctx.stroke(); ctx.setLineDash([]);
      };
      line(trade.tp, "#26a69a"); line(trade.sl, "#ef5350"); line(trade.entry_price, "#cfd8e6");
      const idxAt = (unix: number) => { let b = 0; for (let i = 0; i < candles.length; i++) { if (candles[i].t <= unix) b = i; else break; } return b; };
      const xi = X(idxAt(Date.parse(trade.entry_time) / 1000));
      const xe = X(idxAt(Date.parse(trade.exit_time) / 1000));
      ctx.fillStyle = trade.direction === "short" ? "#ef5350" : "#26a69a";
      const ey = Y(trade.entry_price); ctx.beginPath();
      if (trade.direction === "short") { ctx.moveTo(xi, ey - 8); ctx.lineTo(xi - 4, ey - 15); ctx.lineTo(xi + 4, ey - 15); }
      else { ctx.moveTo(xi, ey + 8); ctx.lineTo(xi - 4, ey + 15); ctx.lineTo(xi + 4, ey + 15); }
      ctx.closePath(); ctx.fill();
      ctx.strokeStyle = "#e6edf3"; ctx.lineWidth = 1.6; const xy = Y(trade.exit_price);
      ctx.beginPath(); ctx.moveTo(xe - 4, xy - 4); ctx.lineTo(xe + 4, xy + 4); ctx.moveTo(xe + 4, xy - 4); ctx.lineTo(xe - 4, xy + 4); ctx.stroke();
    };
    draw();
    window.addEventListener("resize", draw);
    return () => window.removeEventListener("resize", draw);
  }, [candles, trade, dec]);

  if (!candles.length)
    return <div className="h-[180px] flex items-center justify-center text-dim text-xs text-center px-4">Velas aún no recolectadas — aparecen tras la próxima operación con el colector actualizado.</div>;
  return <canvas ref={ref} style={{ width: "100%", display: "block" }} />;
}
