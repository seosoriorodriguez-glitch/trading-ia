import { createClient } from "@supabase/supabase-js";
import { chDateTime } from "@/lib/tz";

export const dynamic = "force-dynamic";
export const runtime = "edge";

// Exporta el histórico de trades a CSV (se abre en Excel). ?bot=<id> filtra por cuenta; sin él, todo.
export async function GET(req: Request) {
  const U = process.env.SUPABASE_URL, K = process.env.SUPABASE_SERVICE_KEY;
  if (!U || !K) return new Response("Falta configurar Supabase", { status: 500 });
  const bot = new URL(req.url).searchParams.get("bot");
  const sb = createClient(U, K, { global: { fetch: (u, o) => fetch(u as any, { ...o, cache: "no-store" }) } });

  let q = sb.from("trades")
    .select("bot_id,account,ticket,symbol,direction,entry_time,exit_time,entry_price,sl,tp,exit_price,exit_reason,risk_points,volume,pnl_usd,pnl_r,session")
    .order("exit_time", { ascending: true }).limit(50000);
  if (bot) q = q.eq("bot_id", bot);
  const { data, error } = await q;
  if (error) return new Response("Error: " + error.message, { status: 500 });

  const cols = [
    "bot_id", "cuenta", "ticket", "symbol", "direccion",
    "entrada_cl", "cierre_cl", "entry_time_utc", "exit_time_utc",
    "entry", "sl", "tp", "exit", "motivo", "risk_points", "volumen",
    "pnl_usd", "pnl_r", "sesion",
  ];
  const esc = (v: unknown) => {
    const s = v == null ? "" : String(v);
    return /[";\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  const sep = ";"; // Excel en español separa por ; por defecto
  const rows = (data ?? []).map((r: any) => [
    r.bot_id, r.account, r.ticket, r.symbol, r.direction,
    chDateTime(r.entry_time), chDateTime(r.exit_time), r.entry_time, r.exit_time,
    r.entry_price, r.sl, r.tp, r.exit_price, r.exit_reason, r.risk_points, r.volume,
    r.pnl_usd, r.pnl_r, r.session,
  ].map(esc).join(sep));
  const csv = "﻿" + [cols.join(sep), ...rows].join("\r\n"); // BOM para acentos en Excel

  const fname = `trades_${bot ?? "todos"}_${new Date().toISOString().slice(0, 10)}.csv`;
  return new Response(csv, {
    headers: {
      "Content-Type": "text/csv; charset=utf-8",
      "Content-Disposition": `attachment; filename="${fname}"`,
    },
  });
}
