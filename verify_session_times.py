# -*- coding: utf-8 -*-
"""
Verifica si las operaciones ganadoras del archivo winning_trades.pine
están realmente dentro de la sesión configurada (13:30-19:30 UTC).
"""
import sys
import codecs
if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

from datetime import datetime, timezone, timedelta

# Zona horaria Santiago (UTC-3)
SANTIAGO_OFFSET = timedelta(hours=-3)

# Sesión configurada en TradingView y bot live
SESSION_START_UTC = "13:30"
SESSION_END_UTC = "19:30"

# 15 operaciones ganadoras más recientes (en UTC según el archivo .pine)
trades = [
    {"id": 92, "entry_utc": "2026-03-24 10:56", "dir": "SHORT"},
    {"id": 90, "entry_utc": "2026-03-23 12:42", "dir": "SHORT"},
    {"id": 87, "entry_utc": "2026-03-20 14:06", "dir": "SHORT"},
    {"id": 84, "entry_utc": "2026-03-19 10:45", "dir": "SHORT"},
    {"id": 82, "entry_utc": "2026-03-16 12:54", "dir": "LONG"},
    {"id": 79, "entry_utc": "2026-03-11 15:04", "dir": "SHORT"},
    {"id": 78, "entry_utc": "2026-03-09 15:35", "dir": "LONG"},
    {"id": 75, "entry_utc": "2026-03-05 15:41", "dir": "LONG"},
    {"id": 70, "entry_utc": "2026-02-27 15:17", "dir": "SHORT"},
    {"id": 67, "entry_utc": "2026-02-25 15:18", "dir": "LONG"},
    {"id": 66, "entry_utc": "2026-02-25 13:40", "dir": "SHORT"},
    {"id": 65, "entry_utc": "2026-02-25 11:31", "dir": "LONG"},
    {"id": 59, "entry_utc": "2026-02-17 12:52", "dir": "SHORT"},
    {"id": 58, "entry_utc": "2026-02-17 12:51", "dir": "SHORT"},
    {"id": 57, "entry_utc": "2026-02-16 10:45", "dir": "LONG"},
]

print("\n" + "="*80)
print("  VERIFICACIÓN DE HORARIOS - OPERACIONES GANADORAS OB")
print("="*80)
print(f"\nSesión configurada: {SESSION_START_UTC} - {SESSION_END_UTC} UTC")
print(f"                    (10:30 - 16:30 Santiago)\n")

inside_session = 0
outside_session = 0

print(f"{'#':<4} {'Entrada UTC':<17} {'Entrada Santiago':<17} {'¿En sesión?':<15} {'Dir':<6}")
print("-" * 80)

for trade in trades:
    dt_utc = datetime.strptime(trade["entry_utc"], "%Y-%m-%d %H:%M")
    dt_utc = dt_utc.replace(tzinfo=timezone.utc)
    
    # Convertir a Santiago
    dt_santiago = dt_utc + SANTIAGO_OFFSET
    
    # Verificar si está en sesión
    hour_utc = dt_utc.hour
    minute_utc = dt_utc.minute
    time_utc = hour_utc * 60 + minute_utc
    
    session_start = 13 * 60 + 30  # 13:30
    session_end = 19 * 60 + 30    # 19:30
    
    in_session = session_start <= time_utc < session_end
    
    if in_session:
        inside_session += 1
        status = "✅ SÍ"
    else:
        outside_session += 1
        status = "❌ NO"
    
    print(f"#{trade['id']:<3} {trade['entry_utc']:<17} {dt_santiago.strftime('%Y-%m-%d %H:%M'):<17} "
          f"{status:<15} {trade['dir']:<6}")

print("-" * 80)
print(f"\n📊 RESUMEN:")
print(f"  Dentro de sesión (13:30-19:30 UTC):  {inside_session} trades ({inside_session/len(trades)*100:.1f}%)")
print(f"  Fuera de sesión:                      {outside_session} trades ({outside_session/len(trades)*100:.1f}%)")

if outside_session > 0:
    print(f"\n⚠️  PROBLEMA DETECTADO:")
    print(f"  {outside_session} operaciones están FUERA de la sesión configurada!")
    print(f"  Esto sugiere que:")
    print(f"    1. El filtro de sesión NO se está aplicando correctamente")
    print(f"    2. O el archivo winning_trades.pine fue generado con otra configuración")
    print(f"    3. O hay un bug en el filtro horario")
else:
    print(f"\n✅ CORRECTO: Todas las operaciones están dentro de la sesión configurada")

print("\n" + "="*80)
