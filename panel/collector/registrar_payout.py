# -*- coding: utf-8 -*-
"""
Registra a mano una recompensa de prop firm en la tabla `payouts`.

POR QUE A MANO: cuando FTMO paga, CIERRA la cuenta y emite otra. En cuanto cambias
el terminal a la cuenta nueva, el colector deja de consultar la vieja, asi que el
retiro de cierre NUNCA queda en balance_ops. Cualquier intento de rastrear payouts
desde MT5 subestima siempre. Esta tabla es la fuente de verdad del efectivo cobrado.

Los datos salen de: FTMO -> Recompensas -> Historial de Recompensas.

Uso:
    # ver lo registrado
    python panel/collector/registrar_payout.py --listar

    # registrar una recompensa
    python panel/collector/registrar_payout.py \
        --bot us30_live_10k --cuenta 531415693 --fecha 2026-09-01 \
        --beneficio 922.89 --recompensa 750.87 \
        --retiro 525.61 --reinversion 225.26 --estado esperando

    # marcarla como pagada cuando FTMO apruebe (misma fecha = actualiza)
    python panel/collector/registrar_payout.py --bot us30_live_10k --fecha 2026-09-01 \
        --retiro 525.61 --reinversion 225.26 --estado pagado

Env:  SUPABASE_URL, SUPABASE_SERVICE_KEY
"""
import argparse, os, sys
from supabase import create_client

ap = argparse.ArgumentParser(description="Registrar recompensa de prop firm")
ap.add_argument("--listar", action="store_true", help="lista las recompensas ya registradas y sale")
ap.add_argument("--bot", help="bot_id (us30_live_10k, us30_challenge_100k, ...)")
ap.add_argument("--cuenta", type=int, default=None, help="numero de cuenta de la que salio")
ap.add_argument("--fecha", help="fecha de la factura, YYYY-MM-DD")
ap.add_argument("--beneficio", type=float, default=None, help="beneficio total de la cuenta, antes del split")
ap.add_argument("--recompensa", type=float, default=None, help="tu parte tras el split 80:20")
ap.add_argument("--retiro", type=float, default=0.0, help="cobrado en efectivo")
ap.add_argument("--reinversion", type=float, default=0.0, help="rollover que quedo en la cuenta siguiente")
ap.add_argument("--reembolso", type=float, default=0.0, help="devolucion del fee del challenge")
ap.add_argument("--estado", default="esperando", choices=["esperando", "pagado"])
ap.add_argument("--nota", default=None)
a = ap.parse_args()

try:
    SB = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])
except KeyError as e:
    sys.exit(f"Falta la variable de entorno {e}. Necesitas SUPABASE_URL y SUPABASE_SERVICE_KEY.")

if a.listar:
    rows = SB.table("payouts").select("*").order("fecha", desc=True).execute().data or []
    if not rows:
        print("Sin recompensas registradas todavia.")
        sys.exit(0)
    print(f"{'fecha':<12}{'bot':<24}{'retiro':>10}{'reinv':>10}{'reemb':>10}  estado")
    print("-" * 78)
    tot_r = tot_i = 0.0
    for r in rows:
        tot_r += r.get("retiro") or 0.0
        tot_i += r.get("reinversion") or 0.0
        print(f"{str(r['fecha']):<12}{r['bot_id']:<24}"
              f"{r.get('retiro') or 0:>10.2f}{r.get('reinversion') or 0:>10.2f}"
              f"{r.get('reembolso') or 0:>10.2f}  {r.get('estado')}")
    print("-" * 78)
    print(f"{'TOTAL':<36}{tot_r:>10.2f}{tot_i:>10.2f}")
    print(f"\nEfectivo cobrado acumulado: ${tot_r:,.2f}   Rollover acumulado: ${tot_i:,.2f}")
    sys.exit(0)

if not a.bot or not a.fecha:
    sys.exit("Faltan --bot y --fecha (o usa --listar). Ver --help.")

fila = {
    "bot_id": a.bot, "account": a.cuenta, "fecha": a.fecha,
    "beneficio": a.beneficio, "recompensa": a.recompensa,
    "retiro": a.retiro, "reinversion": a.reinversion, "reembolso": a.reembolso,
    "estado": a.estado, "nota": a.nota,
}
fila = {k: v for k, v in fila.items() if v is not None}
SB.table("payouts").upsert(fila, on_conflict="bot_id,fecha").execute()
print(f"OK  {a.bot}  {a.fecha}  retiro ${a.retiro:,.2f}  reinversion ${a.reinversion:,.2f}  [{a.estado}]")
