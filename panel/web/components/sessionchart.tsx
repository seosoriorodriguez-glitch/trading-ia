"use client";
import { useRef, useEffect } from "react";

type Candle = { t: number; o: number; h: number; l: number; c: number };
type Zone = { type: "bullish" | "bearish"; high: number; low: number; at: number };
type Trade = {
  entry_price: number; exit_price: number; entry_time: string; exit_time: string;
  direction: string; pnl_usd: number;
};

export function SessionChart({ candles, zones, trades = [], dec = 1, height = 320 }: {
  candles: Candle[]; zones: Zone[]; trades?: Trade[]; dec?: number; height?: number;
}) {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const cv = ref.current;
    if (!cv || !candles.length) return;
    const draw = () => {
      const ctx = cv.getContext("2d");
      if (!ctx) return;
      const dpr = Math.min(devicePixelRatio || 1, 2);
      const W = cv.clientWidth, H = height;
      cv.width = W * dpr; cv.height = H * dpr; cv.style.height = H + "px"; ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      const PL = 6, PR = 62, PT = 10, PB = 10;
      const tv = trades.flatMap((t) => [t.entry_price, t.exit_price]);
      let lo = Math.min(...candles.map((c) => c.l), ...zones.map((z) => z.low), ...tv);
      let hi = Math.max(...candles.map((c) => c.h), ...zones.map((z) => z.high), ...tv);
      const pad = (hi - lo) * 0.04 || 1; lo -= pad; hi += pad;
      const plotW = W - PL - PR;
      const X = (i: number) => PL + (i + 0.5) * (plotW / candles.length);
      const Y = (p: number) => PT + ((hi - p) / (hi - lo)) * (H - PT - PB);
      const idxAt = (unix: number) => { let b = 0; for (let i = 0; i < candles.length; i++) { if (candles[i].t <= unix) b = i; else break; } return b; };
      ctx.clearRect(0, 0, W, H);

      // grid + ejes de precio
      ctx.font = "10px ui-monospace,monospace"; ctx.textBaseline = "middle"; ctx.textAlign = "left";
      for (let s = 0; s <= 4; s++) {
        const p = lo + ((hi - lo) * s) / 4, y = Y(p);
        ctx.strokeStyle = "rgba(255,255,255,.05)"; ctx.beginPath(); ctx.moveTo(PL, y); ctx.lineTo(W - PR, y); ctx.stroke();
        ctx.fillStyle = "#8a97a8"; ctx.fillText(p.toFixed(dec), W - PR + 5, y);
      }

      // zonas OB (rectángulos desde su confirmación hasta el borde derecho)
      zones.forEach((z) => {
        const x0 = X(idxAt(z.at)) - 2;
        const x1 = W - PR;
        const yTop = Y(z.high), yBot = Y(z.low);
        const bull = z.type === "bullish";
        ctx.fillStyle = bull ? "rgba(38,166,154,.13)" : "rgba(239,83,80,.13)";
        ctx.fillRect(x0, yTop, x1 - x0, yBot - yTop);
        ctx.strokeStyle = bull ? "rgba(38,166,154,.5)" : "rgba(239,83,80,.5)";
        ctx.lineWidth = 1; ctx.strokeRect(x0, yTop, x1 - x0, yBot - yTop);
      });

      // velas
      const cw = Math.max(1.2, Math.min(7, (plotW / candles.length) * 0.62));
      candles.forEach((c, i) => {
        const up = c.c >= c.o; ctx.strokeStyle = ctx.fillStyle = up ? "#26a69a" : "#ef5350";
        const x = X(i); ctx.lineWidth = 1; ctx.beginPath(); ctx.moveTo(x, Y(c.h)); ctx.lineTo(x, Y(c.l)); ctx.stroke();
        const yo = Y(c.o), yc = Y(c.c); ctx.fillRect(x - cw / 2, Math.min(yo, yc), cw, Math.max(1, Math.abs(yc - yo)));
      });

      // operaciones de la sesión (entrada ▲/▼ + salida ✕)
      trades.forEach((t) => {
        const xi = X(idxAt(Date.parse(t.entry_time) / 1000));
        const xe = X(idxAt(Date.parse(t.exit_time) / 1000));
        const ey = Y(t.entry_price);
        ctx.fillStyle = t.direction === "short" ? "#ef5350" : "#26a69a";
        ctx.beginPath();
        if (t.direction === "short") { ctx.moveTo(xi, ey - 7); ctx.lineTo(xi - 4, ey - 14); ctx.lineTo(xi + 4, ey - 14); }
        else { ctx.moveTo(xi, ey + 7); ctx.lineTo(xi - 4, ey + 14); ctx.lineTo(xi + 4, ey + 14); }
        ctx.closePath(); ctx.fill();
        const xy = Y(t.exit_price);
        ctx.strokeStyle = t.pnl_usd >= 0 ? "#26a69a" : "#ef5350"; ctx.lineWidth = 1.6;
        ctx.beginPath(); ctx.moveTo(xe - 4, xy - 4); ctx.lineTo(xe + 4, xy + 4); ctx.moveTo(xe + 4, xy - 4); ctx.lineTo(xe - 4, xy + 4); ctx.stroke();
      });

      // último precio (línea punteada)
      const last = candles[candles.length - 1].c;
      ctx.strokeStyle = "rgba(207,216,230,.6)"; ctx.setLineDash([3, 3]); ctx.lineWidth = 1;
      ctx.beginPath(); ctx.moveTo(PL, Y(last)); ctx.lineTo(W - PR, Y(last)); ctx.stroke(); ctx.setLineDash([]);
      ctx.fillStyle = "#0b0f14"; ctx.fillRect(W - PR + 1, Y(last) - 7, PR - 1, 14);
      ctx.fillStyle = "#cfd8e6"; ctx.fillText(last.toFixed(dec), W - PR + 5, Y(last));
    };
    draw();
    window.addEventListener("resize", draw);
    return () => window.removeEventListener("resize", draw);
  }, [candles, zones, trades, dec, height]);

  if (!candles.length)
    return <div className="flex items-center justify-center text-dim text-xs text-center px-4" style={{ height }}>Aún sin datos de la sesión de hoy — se llena durante London (10:00–17:00 servidor ≈ 03:00–10:00 Chile) y luego queda congelada para revisarla.</div>;
  return <canvas ref={ref} style={{ width: "100%", display: "block" }} />;
}
