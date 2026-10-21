# -*- coding: utf-8 -*-
r"""
Diagnostico SOLO LECTURA para correr en el VPS (no toca bots ni pone ordenes; lee el historial
de ordenes de MT5, igual que el colector).

Para cada trade que el motor tomo y el live NO (2-sep a 21-oct 2026), busca en el historial de ordenes
del bot (magic 345680) si el bot llego a poner la orden STOP:
  SIN ORDEN  -> el bot nunca vio la senal (problema de cuando mira las velas / las zonas)
  CANCELADA  -> la puso y se cancelo (zona destruida/vencida en el live, o ventana de noticia)
  LLENADA    -> se lleno (entonces el emparejado fallo, no es una diferencia real)

Uso en el VPS (desde cualquier carpeta):
    cd C:\Users\Administrator\trading-ia; python research/ob_racha/diag_ordenes_vps.py
"""
from datetime import datetime, timedelta, timezone

import MetaTrader5 as mt5

TERMINALES = {
    "10k (511393879)": r"C:\Program Files\MT5_BTCUSD\terminal64.exe",
    "100k (541459159)": r"C:\Program Files\MT5_US30\terminal64.exe",
}
MAGIC = 345680
SOLO_MOTOR = [  # (hora servidor de la entrada del motor, lado, precio de entrada, R que dio)
    ("2026-09-02 10:28", "long", 52799.96, -1.02), ("2026-09-16 10:52", "long", 52150.56, -1.02),
    ("2026-09-16 15:21", "long", 52213.75, -1.02), ("2026-09-16 16:34", "long", 52100.25, -1.03),
    ("2026-09-18 12:29", "long", 51872.46, -1.01), ("2026-09-21 16:32", "long", 51909.45, -1.02),
    ("2026-09-22 10:39", "long", 52012.96, -1.02), ("2026-09-22 10:48", "long", 51979.46, -1.03),
    ("2026-09-22 14:10", "long", 52173.46, 2.35), ("2026-09-25 10:16", "long", 51432.95, 2.38),
    ("2026-09-25 16:24", "long", 51463.36, -1.02), ("2026-09-28 12:07", "long", 51603.96, -1.02),
    ("2026-09-30 12:07", "long", 51495.76, -1.02), ("2026-10-02 16:58", "long", 51142.66, -1.02),
    ("2026-10-05 10:23", "long", 51103.66, 2.35), ("2026-10-07 16:33", "short", 51118.96, 2.37),
    ("2026-10-08 15:57", "long", 50835.86, 2.42), ("2026-10-09 12:39", "long", 51320.26, -1.02),
    ("2026-10-09 14:30", "short", 51300.85, -1.02), ("2026-10-12 16:35", "short", 51842.46, 2.35),
    ("2026-10-13 13:35", "long", 51987.26, -1.02), ("2026-10-19 12:45", "short", 52010.26, -1.02),
    ("2026-10-20 10:38", "short", 52080.16, -1.02), ("2026-10-20 15:43", "long", 52005.66, 2.44),
]
ESTADO = {mt5.ORDER_STATE_FILLED: "LLENADA", mt5.ORDER_STATE_CANCELED: "CANCELADA",
          mt5.ORDER_STATE_EXPIRED: "EXPIRADA", mt5.ORDER_STATE_REJECTED: "RECHAZADA"}


def hora(ts):
    return datetime.fromtimestamp(ts, timezone.utc).replace(tzinfo=None)   # MT5: hora servidor como epoch


for nombre, ruta in TERMINALES.items():
    if not mt5.initialize(path=ruta):
        print(f"\n### {nombre}: no se pudo conectar ({mt5.last_error()})"); continue
    acc = mt5.account_info()
    ords = mt5.history_orders_get(datetime(2026, 8, 25), datetime(2026, 10, 20)) or []
    ords = [o for o in ords if o.magic == MAGIC and o.type in (mt5.ORDER_TYPE_BUY_STOP, mt5.ORDER_TYPE_SELL_STOP)]
    print(f"\n### {nombre} - cuenta {acc.login if acc else '?'} - {len(ords)} ordenes STOP del bot en el historial")
    if ords:
        print(f"    primera orden: {hora(min(o.time_setup for o in ords))}")
    resumen = {}
    for t_txt, lado, px, r in SOLO_MOTOR:
        t = datetime.strptime(t_txt, "%Y-%m-%d %H:%M")
        tipo = mt5.ORDER_TYPE_BUY_STOP if lado == "long" else mt5.ORDER_TYPE_SELL_STOP
        c = [o for o in ords if o.type == tipo and abs(o.price_open - px) <= 3.0
             and t - timedelta(hours=3) <= hora(o.time_setup) <= t + timedelta(minutes=5)]
        if ords and t < hora(min(o.time_setup for o in ords)):
            est = "fuera del historial de esta cuenta"
        elif not c:
            est = "SIN ORDEN"
        else:
            o = min(c, key=lambda o: abs((hora(o.time_setup) - t).total_seconds()))
            est = f"{ESTADO.get(o.state, o.state)} (puesta {hora(o.time_setup):%H:%M:%S}, fin {hora(o.time_done):%H:%M:%S}, precio {o.price_open:.2f})"
        clave = est.split(" (")[0]
        resumen[clave] = resumen.get(clave, 0) + 1
        print(f"  {t_txt} {lado:5s} {px:9.2f} R={r:+.2f} -> {est}")
    print("  RESUMEN:", resumen)
    mt5.shutdown()
