"use client";
import { useRef, useEffect } from "react";

type Serie = { name: string; color: string; points: number[] };

export function PctLines({ series, dates, height = 240 }: { series: Serie[]; dates: string[]; height?: number }) {
  const ref = useRef<HTMLCanvasElement>(null);
  const vScale = useRef(1);
  const view = useRef({ W: 0, PR: 48 });
  const drag = useRef(false);

  useEffect(() => {
    const cv = ref.current;
    if (!cv || !series.length || !dates.length) return;
    const clamp = (v: number, a: number, b: number) => Math.max(a, Math.min(b, v));

    const draw = () => {
      const ctx = cv.getContext("2d");
      if (!ctx) return;
      const dpr = Math.min(devicePixelRatio || 1, 2);
      const W = cv.clientWidth, H = height;
      cv.width = W * dpr; cv.height = H * dpr; cv.style.height = H + "px"; ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      const PL = 6, PR = 48, PT = 8, PB = 20, plotH = H - PT - PB, plotW = W - PL - PR;
      const N = dates.length;
      view.current = { W, PR };
      const allY = series.flatMap((s) => s.points);
      let lo0 = Math.min(0, ...allY), hi0 = Math.max(0, ...allY);
      const pad = (hi0 - lo0) * 0.08 || 1; lo0 -= pad; hi0 += pad;
      const mid = (lo0 + hi0) / 2, half = ((hi0 - lo0) / 2) / vScale.current;
      const lo = mid - half, hi = mid + half;
      const X = (i: number) => PL + (N <= 1 ? plotW / 2 : (i / (N - 1)) * plotW);
      const Y = (p: number) => PT + ((hi - p) / (hi - lo)) * plotH;
      ctx.clearRect(0, 0, W, H);

      // grid + ejes %
      ctx.font = "10px ui-monospace,monospace"; ctx.textBaseline = "middle"; ctx.textAlign = "left";
      for (let s = 0; s <= 4; s++) {
        const p = lo + ((hi - lo) * s) / 4, y = Y(p);
        ctx.strokeStyle = "rgba(255,255,255,.05)"; ctx.beginPath(); ctx.moveTo(PL, y); ctx.lineTo(W - PR, y); ctx.stroke();
        ctx.fillStyle = "#8a97a8"; ctx.fillText(`${p >= 0 ? "+" : ""}${p.toFixed(1)}%`, W - PR + 4, y);
      }
      // baseline 0%
      ctx.strokeStyle = "rgba(255,255,255,.2)"; ctx.setLineDash([4, 4]); ctx.lineWidth = 1;
      ctx.beginPath(); ctx.moveTo(PL, Y(0)); ctx.lineTo(W - PR, Y(0)); ctx.stroke(); ctx.setLineDash([]);
      // fechas (sparse)
      ctx.textAlign = "center"; ctx.textBaseline = "alphabetic"; ctx.fillStyle = "#6b7684"; ctx.font = "9px ui-monospace,monospace";
      const step = Math.max(1, Math.floor(N / 6));
      for (let i = 0; i < N; i += step) ctx.fillText(dates[i].slice(5), X(i), H - 6);
      // líneas
      ctx.lineWidth = 1.8; ctx.lineJoin = "round";
      series.forEach((s) => {
        ctx.strokeStyle = s.color; ctx.beginPath();
        s.points.forEach((p, i) => { const x = X(i), y = Y(p); i ? ctx.lineTo(x, y) : ctx.moveTo(x, y); });
        ctx.stroke();
        const li = s.points.length - 1;
        ctx.fillStyle = s.color; ctx.beginPath(); ctx.arc(X(li), Y(s.points[li]), 2.6, 0, Math.PI * 2); ctx.fill();
      });
    };

    // interacción: escala vertical (arrastrar / rueda), doble clic resetea
    const onDown = (e: PointerEvent) => { drag.current = true; cv.setPointerCapture(e.pointerId); cv.style.cursor = "ns-resize"; };
    const onMove = (e: PointerEvent) => {
      if (!drag.current) { cv.style.cursor = "ns-resize"; return; }
      vScale.current = clamp(vScale.current * Math.exp(-e.movementY * 0.008), 0.2, 30); draw();
    };
    const onUp = (e: PointerEvent) => { drag.current = false; try { cv.releasePointerCapture(e.pointerId); } catch {} };
    const onWheel = (e: WheelEvent) => { e.preventDefault(); vScale.current = clamp(vScale.current * (e.deltaY < 0 ? 1.12 : 0.89), 0.2, 30); draw(); };
    const onDbl = () => { vScale.current = 1; draw(); };

    draw();
    cv.addEventListener("pointerdown", onDown);
    cv.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onUp);
    cv.addEventListener("wheel", onWheel, { passive: false });
    cv.addEventListener("dblclick", onDbl);
    window.addEventListener("resize", draw);
    return () => {
      cv.removeEventListener("pointerdown", onDown);
      cv.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", onUp);
      cv.removeEventListener("wheel", onWheel);
      cv.removeEventListener("dblclick", onDbl);
      window.removeEventListener("resize", draw);
    };
  }, [series, dates, height]);

  if (!series.length) return <div className="text-dim text-xs flex items-center justify-center" style={{ height }}>Sin datos aún.</div>;
  return <canvas ref={ref} style={{ width: "100%", display: "block", touchAction: "none" }} />;
}
