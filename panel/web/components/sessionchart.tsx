"use client";
import { useRef, useEffect } from "react";

type Candle = { t: number; o: number; h: number; l: number; c: number };
type Zone = { type: "bullish" | "bearish"; high: number; low: number; at: number; spent?: boolean };
type Trade = {
  entry_price: number; exit_price: number; entry_time: string; exit_time: string;
  direction: string; pnl_usd: number; sl?: number | null; tp?: number | null;
};

export function SessionChart({ candles, zones, trades = [], dec = 1, height = 320, sess = [10, 17] }: {
  candles: Candle[]; zones: Zone[]; trades?: Trade[]; dec?: number; height?: number; sess?: [number, number];
}) {
  const ref = useRef<HTMLCanvasElement>(null);
  const vScale = useRef(1);          // zoom vertical (arrastrar eje derecho / rueda)
  const vOff = useRef(0);            // desplazamiento vertical en precio (arrastrar el gráfico)
  const view = useRef({ lo: 0, hi: 1, plotH: 1, W: 0, PR: 62 });
  const drag = useRef<null | "scale" | "pan">(null);
  const cross = useRef<null | { x: number; y: number }>(null);

  useEffect(() => {
    const cv = ref.current;
    if (!cv || !candles.length) return;
    const clamp = (v: number, a: number, b: number) => Math.max(a, Math.min(b, v));

    const draw = () => {
      const ctx = cv.getContext("2d");
      if (!ctx) return;
      const dpr = Math.min(devicePixelRatio || 1, 2);
      const W = cv.clientWidth, H = height;
      cv.width = W * dpr; cv.height = H * dpr; cv.style.height = H + "px"; ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      const PL = 6, PR = 62, PT = 10, PB = 24, plotH = H - PT - PB;
      const chLabel = (t: number) => new Date((t - 3 * 3600) * 1000).toLocaleTimeString("es-CL", { timeZone: "America/Santiago", hour: "2-digit", minute: "2-digit" });
      const tv = trades.flatMap((t) => [t.entry_price, t.exit_price, t.sl, t.tp].filter((v) => v != null) as number[]);
      let lo0 = Math.min(...candles.map((c) => c.l), ...zones.map((z) => z.low), ...tv);
      let hi0 = Math.max(...candles.map((c) => c.h), ...zones.map((z) => z.high), ...tv);
      const pad = (hi0 - lo0) * 0.04 || 1; lo0 -= pad; hi0 += pad;
      // aplicar zoom/pan vertical
      const mid = (lo0 + hi0) / 2 + vOff.current, half = ((hi0 - lo0) / 2) / vScale.current;
      const lo = mid - half, hi = mid + half;
      view.current = { lo, hi, plotH, W, PR };
      const plotW = W - PL - PR;
      const X = (i: number) => PL + (i + 0.5) * (plotW / candles.length);
      const Y = (p: number) => PT + ((hi - p) / (hi - lo)) * plotH;
      const idxAt = (unix: number) => { let b = 0; for (let i = 0; i < candles.length; i++) { if (candles[i].t <= unix) b = i; else break; } return b; };
      ctx.clearRect(0, 0, W, H);

      // banda de la sesión de London (contexto ±2h alrededor)
      const shour = (i: number) => new Date(candles[i].t * 1000).getUTCHours();
      let iS = -1, iE = -1;
      for (let i = 0; i < candles.length; i++) { if (iS < 0 && shour(i) >= sess[0]) iS = i; if (shour(i) < sess[1]) iE = i; }
      if (iS >= 0 && iE >= iS) {
        const xs = X(iS) - (plotW / candles.length) / 2, xe = X(iE) + (plotW / candles.length) / 2;
        ctx.fillStyle = "rgba(255,255,255,.022)"; ctx.fillRect(xs, PT, xe - xs, plotH);
        ctx.strokeStyle = "rgba(255,255,255,.12)"; ctx.setLineDash([3, 3]); ctx.lineWidth = 1;
        ctx.beginPath(); ctx.moveTo(xs, PT); ctx.lineTo(xs, H - PB); ctx.moveTo(xe, PT); ctx.lineTo(xe, H - PB); ctx.stroke(); ctx.setLineDash([]);
      }

      // grid + ejes de precio
      ctx.font = "10px ui-monospace,monospace"; ctx.textBaseline = "middle"; ctx.textAlign = "left";
      for (let s = 0; s <= 4; s++) {
        const p = lo + ((hi - lo) * s) / 4, y = Y(p);
        ctx.strokeStyle = "rgba(255,255,255,.05)"; ctx.beginPath(); ctx.moveTo(PL, y); ctx.lineTo(W - PR, y); ctx.stroke();
        ctx.fillStyle = "#8a97a8"; ctx.fillText(p.toFixed(dec), W - PR + 5, y);
      }

      // zonas OB — activas = sólidas; gastadas = tenues + punteadas (se marcan igual).
      // Se extienden ~30 velas desde su origen (no hasta el borde) para no ensuciar.
      const ZONE_LEN = 60;
      zones.forEach((z) => {
        const i0 = idxAt(z.at);
        const x0 = X(i0) - 2, x1 = Math.min(W - PR, X(Math.min(candles.length - 1, i0 + ZONE_LEN)) + 2);
        const yTop = Y(z.high), yBot = Y(z.low), bull = z.type === "bullish";
        const rgb = bull ? "38,166,154" : "239,83,80";
        ctx.fillStyle = `rgba(${rgb},${z.spent ? ".05" : ".15"})`;
        ctx.fillRect(x0, yTop, x1 - x0, yBot - yTop);
        ctx.strokeStyle = `rgba(${rgb},${z.spent ? ".3" : ".6"})`;
        ctx.lineWidth = 1; ctx.setLineDash(z.spent ? [3, 3] : []);
        ctx.strokeRect(x0, yTop, x1 - x0, yBot - yTop); ctx.setLineDash([]);
      });

      // velas
      const cw = Math.max(1.2, Math.min(7, (plotW / candles.length) * 0.62));
      candles.forEach((c, i) => {
        const up = c.c >= c.o; ctx.strokeStyle = ctx.fillStyle = up ? "#26a69a" : "#ef5350";
        const x = X(i); ctx.lineWidth = 1; ctx.beginPath(); ctx.moveTo(x, Y(c.h)); ctx.lineTo(x, Y(c.l)); ctx.stroke();
        const yo = Y(c.o), yc = Y(c.c); ctx.fillRect(x - cw / 2, Math.min(yo, yc), cw, Math.max(1, Math.abs(yc - yo)));
      });

      // operaciones (SL/TP + entrada ▲/▼ + salida ✕)
      trades.forEach((t) => {
        const xi = X(idxAt(Date.parse(t.entry_time) / 1000)), xe = X(idxAt(Date.parse(t.exit_time) / 1000));
        const ey = Y(t.entry_price);
        const seg = (p: number | null | undefined, col: string) => {
          if (p == null) return;
          ctx.strokeStyle = col; ctx.setLineDash([4, 3]); ctx.lineWidth = 1;
          ctx.beginPath(); ctx.moveTo(Math.min(xi, xe) - 4, Y(p)); ctx.lineTo(Math.max(xi, xe) + 4, Y(p)); ctx.stroke(); ctx.setLineDash([]);
        };
        seg(t.tp, "rgba(38,166,154,.9)"); seg(t.sl, "rgba(239,83,80,.9)");
        ctx.fillStyle = t.direction === "short" ? "#ef5350" : "#26a69a"; ctx.beginPath();
        if (t.direction === "short") { ctx.moveTo(xi, ey - 7); ctx.lineTo(xi - 4, ey - 14); ctx.lineTo(xi + 4, ey - 14); }
        else { ctx.moveTo(xi, ey + 7); ctx.lineTo(xi - 4, ey + 14); ctx.lineTo(xi + 4, ey + 14); }
        ctx.closePath(); ctx.fill();
        const xy = Y(t.exit_price);
        ctx.strokeStyle = t.pnl_usd >= 0 ? "#26a69a" : "#ef5350"; ctx.lineWidth = 1.6;
        ctx.beginPath(); ctx.moveTo(xe - 4, xy - 4); ctx.lineTo(xe + 4, xy + 4); ctx.moveTo(xe + 4, xy - 4); ctx.lineTo(xe - 4, xy + 4); ctx.stroke();
      });

      // eje de tiempo (hora Chile) abajo + marcadores de inicio/fin de sesión
      ctx.textBaseline = "alphabetic"; ctx.font = "9px ui-monospace,monospace";
      const startX = iS >= 0 ? X(iS) : -99, endX = iE >= 0 ? X(iE) : -99;
      const step = Math.max(1, Math.floor(candles.length / 7));
      ctx.textAlign = "center"; ctx.fillStyle = "#6b7684";
      for (let i = 0; i < candles.length; i += step) {
        const x = X(i);
        if (Math.abs(x - startX) < 34 || Math.abs(x - endX) < 30) continue;   // no chocar con los de sesión
        ctx.fillText(chLabel(candles[i].t), x, H - 8);
      }
      ctx.fillStyle = "#8ab4f8"; ctx.font = "10px ui-monospace,monospace";
      if (iS >= 0) { ctx.textAlign = "left"; ctx.fillText("▏London " + chLabel(candles[iS].t), startX + 2, H - 8); }
      if (iE >= 0) { ctx.textAlign = "right"; ctx.fillText("cierre " + chLabel(candles[iE].t) + "▕", endX - 2, H - 8); }
      ctx.textAlign = "left"; ctx.textBaseline = "middle";

      // último precio
      const last = candles[candles.length - 1].c;
      ctx.strokeStyle = "rgba(207,216,230,.6)"; ctx.setLineDash([3, 3]); ctx.lineWidth = 1;
      ctx.beginPath(); ctx.moveTo(PL, Y(last)); ctx.lineTo(W - PR, Y(last)); ctx.stroke(); ctx.setLineDash([]);
      ctx.fillStyle = "#0b0f14"; ctx.fillRect(W - PR + 1, Y(last) - 7, PR - 1, 14);
      ctx.fillStyle = "#cfd8e6"; ctx.fillText(last.toFixed(dec), W - PR + 5, Y(last));

      // crosshair (al pasar el mouse) — precio a la derecha + hora abajo
      if (cross.current) {
        const cy = Math.max(PT, Math.min(H - PB, cross.current.y));
        const ci = Math.max(0, Math.min(candles.length - 1, Math.round((cross.current.x - PL) / (plotW / candles.length) - 0.5)));
        const cx = X(ci);
        ctx.strokeStyle = "rgba(255,255,255,.3)"; ctx.setLineDash([3, 3]); ctx.lineWidth = 1;
        ctx.beginPath(); ctx.moveTo(cx, PT); ctx.lineTo(cx, H - PB); ctx.stroke();
        ctx.beginPath(); ctx.moveTo(PL, cy); ctx.lineTo(W - PR, cy); ctx.stroke(); ctx.setLineDash([]);
        const p = hi - ((cy - PT) / plotH) * (hi - lo);
        ctx.fillStyle = "#2b3442"; ctx.fillRect(W - PR + 1, cy - 8, PR - 1, 16);
        ctx.fillStyle = "#e6edf3"; ctx.font = "10px ui-monospace,monospace"; ctx.textAlign = "left"; ctx.textBaseline = "middle";
        ctx.fillText(p.toFixed(dec), W - PR + 5, cy);
        const lbl = chLabel(candles[ci].t);
        ctx.textAlign = "center"; ctx.textBaseline = "alphabetic";
        const tw = ctx.measureText(lbl).width + 10;
        ctx.fillStyle = "#2b3442"; ctx.fillRect(cx - tw / 2, H - PB + 1, tw, 15);
        ctx.fillStyle = "#e6edf3"; ctx.fillText(lbl, cx, H - PB + 12);
        ctx.textAlign = "left"; ctx.textBaseline = "middle";
      }
    };

    // ---- interacción tipo TradingView ----
    const localX = (e: PointerEvent | WheelEvent) => e.clientX - cv.getBoundingClientRect().left;
    const onDown = (e: PointerEvent) => {
      drag.current = localX(e) > view.current.W - view.current.PR ? "scale" : "pan";
      cv.setPointerCapture(e.pointerId); cv.style.cursor = "grabbing";
    };
    const onMove = (e: PointerEvent) => {
      if (drag.current) {
        if (drag.current === "scale") vScale.current = clamp(vScale.current * Math.exp(-e.movementY * 0.008), 0.15, 40);
        else { const { lo, hi, plotH } = view.current; vOff.current += e.movementY * (hi - lo) / plotH; }
        draw(); return;
      }
      const r = cv.getBoundingClientRect();
      cross.current = { x: e.clientX - r.left, y: e.clientY - r.top };
      cv.style.cursor = (e.clientX - r.left) > view.current.W - view.current.PR ? "ns-resize" : "crosshair";
      draw();
    };
    const onLeave = () => { if (!drag.current) { cross.current = null; draw(); } };
    const onUp = (e: PointerEvent) => { drag.current = null; try { cv.releasePointerCapture(e.pointerId); } catch {} };
    const onWheel = (e: WheelEvent) => { e.preventDefault(); vScale.current = clamp(vScale.current * (e.deltaY < 0 ? 1.12 : 0.89), 0.15, 40); draw(); };
    const onDbl = () => { vScale.current = 1; vOff.current = 0; draw(); };

    draw();
    cv.addEventListener("pointerdown", onDown);
    cv.addEventListener("pointermove", onMove);
    cv.addEventListener("pointerleave", onLeave);
    window.addEventListener("pointerup", onUp);
    cv.addEventListener("wheel", onWheel, { passive: false });
    cv.addEventListener("dblclick", onDbl);
    window.addEventListener("resize", draw);
    return () => {
      cv.removeEventListener("pointerdown", onDown);
      cv.removeEventListener("pointermove", onMove);
      cv.removeEventListener("pointerleave", onLeave);
      window.removeEventListener("pointerup", onUp);
      cv.removeEventListener("wheel", onWheel);
      cv.removeEventListener("dblclick", onDbl);
      window.removeEventListener("resize", draw);
    };
  }, [candles, zones, trades, dec, height, sess]);

  if (!candles.length)
    return <div className="flex items-center justify-center text-dim text-xs text-center px-4" style={{ height }}>Aún sin datos de la sesión de hoy — se llena durante London (10:00–17:00 servidor ≈ 03:00–10:00 Chile) y luego queda congelada para revisarla.</div>;
  return <canvas ref={ref} style={{ width: "100%", display: "block", touchAction: "none" }} />;
}
