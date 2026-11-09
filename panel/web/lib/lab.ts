import type { BotHealth, Trade } from "./data";

// Laboratorio en papel (papel/runner.py en el VPS). Cada estrategia lleva su referencia del backtest para
// juzgar el papel contra lo esperado, no contra un mes suelto.
export type LabRef = {
  destino: "Darwinex" | "FTMO";
  feed: string;
  reglas: string;
  // año "normal" del backtest: lo que deberia verse a la larga (por trade y por mes)
  esperado: { ePorTrade: number; tradesMes: number; wr: number; sdR: number; nota: string };
  backtest: { periodo: string; trades: number; R: number; wr: number; pf: number; ddR: number }[];
};

export const LAB: Record<string, LabRef> = {
  lab_sr_pivot_h1: {
    destino: "Darwinex",
    feed: "WS30 · terminal Darwinex",
    reglas: "Pivotes H1 15/15 · 5 niveles vivos · LIMIT 20 pts antes del nivel · SL 130 al otro lado · TP 2.5R · 24 h lun-vie · cierre viernes 19:00 UTC · 0.5 % por trade",
    esperado: { ePorTrade: 0.09, tradesMes: 16, wr: 32, sdR: 1.65, nota: "año normal ≈ 2025; 2026 fue excepcional para esta estrategia" },
    backtest: [
      { periodo: "2025", trades: 192, R: 16.6, wr: 32.3, pf: 1.13, ddR: 15.7 },
      { periodo: "2026 (ene-oct)", trades: 163, R: 61.6, wr: 41.7, pf: 1.66, ddR: 8.1 },
      { periodo: "2020-2024 (informativo)", trades: 889, R: 50.7, wr: 0, pf: 0, ddR: 21 },
    ],
  },
};

export const SUF_BT = "__bt";

// Latido del motor de papel: sube un snapshot cada 5 min.
export function latido(b: BotHealth): { ok: boolean; txt: string } {
  if (!b.lastSnapTs) return { ok: false, txt: "sin latido" };
  const min = (Date.now() - +new Date(b.lastSnapTs)) / 60000;
  if (min < 15) return { ok: true, txt: "en línea" };
  return { ok: false, txt: min < 120 ? `sin latido hace ${Math.round(min)} min` : `sin latido hace ${(min / 60).toFixed(0)} h` };
}

export function diasDesde(iso?: string | null): number | null {
  if (!iso) return null;
  return Math.max(0, Math.floor((Date.now() - +new Date(iso)) / 864e5));
}

// ¿Lo real está dentro de lo esperado? Banda de 95 % para la media de n trades (sd por trade del backtest).
export function vsEsperado(b: BotHealth, ref?: LabRef) {
  if (!ref || b.n === 0) return null;
  const banda = (1.96 * ref.esperado.sdR) / Math.sqrt(b.n);
  const dif = b.expectancyR - ref.esperado.ePorTrade;
  return { banda, dif, dentro: Math.abs(dif) <= banda, tradesParaJuzgar: Math.ceil(((1.96 * ref.esperado.sdR) / Math.max(0.05, ref.esperado.ePorTrade)) ** 2) };
}

// Papel vs backtest del mismo periodo: misma dirección y entrada en el mismo minuto (±1).
export function compararConBacktest(papel: Trade[], bt: Trade[]) {
  const usados = new Set<number>();
  let coinciden = 0;
  for (const p of papel) {
    const tp = +new Date(p.entry_time);
    const j = bt.findIndex((x, k) => !usados.has(k) && x.direction === p.direction && Math.abs(+new Date(x.entry_time) - tp) <= 120000);
    if (j >= 0) { usados.add(j); coinciden++; }
  }
  const sumR = (ts: Trade[]) => ts.reduce((a, t) => a + (t.pnl_r ?? 0), 0);
  return { papel: papel.length, backtest: bt.length, coinciden, rPapel: sumR(papel), rBt: sumR(bt) };
}

// Simulación de challenge FTMO sobre los trades en papel: +10 % pasa, −10 % del inicial o −5 % en un día quema.
export function simChallenge(trades: Trade[], inicial: number, objetivo = 10, maxPerd = 10, diaria = 5) {
  const ts = [...trades].sort((a, b) => +new Date(a.exit_time) - +new Date(b.exit_time));
  let bal = inicial, dia = "", ini = inicial, min = inicial, peorDia = 0;
  for (const t of ts) {
    const d = t.exit_time.slice(0, 10);   // día del servidor
    if (d !== dia) { dia = d; ini = bal; }
    bal += t.pnl_usd;
    min = Math.min(min, bal);
    peorDia = Math.min(peorDia, ((bal - ini) / inicial) * 100);
    if (bal <= inicial * (1 - maxPerd / 100)) return { estado: "quemaría" as const, fecha: t.exit_time, retPct: ((bal - inicial) / inicial) * 100, peorDia, minPct: ((min - inicial) / inicial) * 100 };
    if (bal - ini <= -inicial * (diaria / 100)) return { estado: "quemaría" as const, fecha: t.exit_time, retPct: ((bal - inicial) / inicial) * 100, peorDia, minPct: ((min - inicial) / inicial) * 100 };
    if (bal >= inicial * (1 + objetivo / 100)) return { estado: "pasaría" as const, fecha: t.exit_time, retPct: ((bal - inicial) / inicial) * 100, peorDia, minPct: ((min - inicial) / inicial) * 100 };
  }
  return { estado: "en curso" as const, fecha: null, retPct: ((bal - inicial) / inicial) * 100, peorDia, minPct: ((min - inicial) / inicial) * 100 };
}
