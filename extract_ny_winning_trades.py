# -*- coding: utf-8 -*-
"""
Extrae solo las operaciones ganadoras de NY del archivo winning_trades.pine
"""
import sys
import codecs
if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

from datetime import datetime, timezone, timedelta

# Zona horaria Santiago (UTC-3)
SANTIAGO_OFFSET = timedelta(hours=-3)

# Sesión NY en UTC
NY_START = "13:30"
NY_END = "20:00"

# Todas las operaciones ganadoras del archivo winning_trades.pine
all_trades = [
    {"id": 4, "entry_utc": "2025-12-18 12:07", "dir": "LONG", "entry": 47956.81, "sl": 47929.13, "tp": 48026.01, "pnl": 1201},
    {"id": 5, "entry_utc": "2025-12-18 13:23", "dir": "LONG", "entry": 48128.81, "sl": 48075.81, "tp": 48261.31, "pnl": 1226},
    {"id": 6, "entry_utc": "2025-12-22 11:45", "dir": "LONG", "entry": 48150.03, "sl": 48119.03, "tp": 48227.53, "pnl": 1228},
    {"id": 9, "entry_utc": "2025-12-30 11:10", "dir": "SHORT", "entry": 48481.70, "sl": 48509.70, "tp": 48411.70, "pnl": 1238},
    {"id": 11, "entry_utc": "2025-12-31 12:08", "dir": "LONG", "entry": 48333.80, "sl": 48311.30, "tp": 48390.05, "pnl": 1238},
    {"id": 13, "entry_utc": "2026-01-02 11:15", "dir": "SHORT", "entry": 48269.81, "sl": 48299.00, "tp": 48196.83, "pnl": 1257},
    {"id": 16, "entry_utc": "2026-01-06 13:24", "dir": "LONG", "entry": 48910.01, "sl": 48874.20, "tp": 48999.54, "pnl": 1265},
    {"id": 20, "entry_utc": "2026-01-09 11:11", "dir": "LONG", "entry": 49262.30, "sl": 49239.30, "tp": 49319.80, "pnl": 1263},
    {"id": 25, "entry_utc": "2026-01-12 13:41", "dir": "SHORT", "entry": 49291.70, "sl": 49312.71, "tp": 49239.17, "pnl": 1240},
    {"id": 29, "entry_utc": "2026-01-14 16:15", "dir": "LONG", "entry": 48917.95, "sl": 48854.45, "tp": 49077.45, "pnl": 1272},
    {"id": 57, "entry_utc": "2026-02-16 10:45", "dir": "LONG", "entry": 49595.93, "sl": 49568.18, "tp": 49653.43, "pnl": 1360},
    {"id": 58, "entry_utc": "2026-02-17 12:51", "dir": "SHORT", "entry": 49501.81, "sl": 49530.41, "tp": 49430.31, "pnl": 1368},
    {"id": 59, "entry_utc": "2026-02-17 12:52", "dir": "SHORT", "entry": 49496.81, "sl": 49512.31, "tp": 49458.06, "pnl": 1335},
    {"id": 65, "entry_utc": "2026-02-25 11:31", "dir": "LONG", "entry": 49314.65, "sl": 49291.41, "tp": 49372.75, "pnl": 1356},
    {"id": 66, "entry_utc": "2026-02-25 13:40", "dir": "SHORT", "entry": 49402.60, "sl": 49425.91, "tp": 49344.32, "pnl": 1372},
    {"id": 67, "entry_utc": "2026-02-25 15:18", "dir": "LONG", "entry": 49280.65, "sl": 49229.15, "tp": 49409.40, "pnl": 1416},
    {"id": 70, "entry_utc": "2026-02-27 15:17", "dir": "SHORT", "entry": 48983.85, "sl": 49106.90, "tp": 48676.22, "pnl": 1432},
    {"id": 75, "entry_utc": "2026-03-05 15:41", "dir": "LONG", "entry": 47923.50, "sl": 47875.10, "tp": 48044.50, "pnl": 1405},
    {"id": 78, "entry_utc": "2026-03-09 15:35", "dir": "LONG", "entry": 47055.10, "sl": 46994.60, "tp": 47206.35, "pnl": 1413},
    {"id": 79, "entry_utc": "2026-03-11 15:04", "dir": "SHORT", "entry": 47511.50, "sl": 47607.50, "tp": 47271.50, "pnl": 1437},
    {"id": 82, "entry_utc": "2026-03-16 12:54", "dir": "LONG", "entry": 46905.81, "sl": 46846.81, "tp": 47053.31, "pnl": 1432},
    {"id": 84, "entry_utc": "2026-03-19 10:45", "dir": "SHORT", "entry": 46159.21, "sl": 46257.71, "tp": 45912.96, "pnl": 1450},
    {"id": 87, "entry_utc": "2026-03-20 14:06", "dir": "SHORT", "entry": 45868.90, "sl": 46027.90, "tp": 45471.40, "pnl": 1457},
    {"id": 90, "entry_utc": "2026-03-23 12:42", "dir": "SHORT", "entry": 46536.81, "sl": 46829.31, "tp": 45805.56, "pnl": 1464},
    {"id": 92, "entry_utc": "2026-03-24 10:56", "dir": "SHORT", "entry": 46158.91, "sl": 46227.41, "tp": 45987.66, "pnl": 1443},
]

print("\n" + "="*100)
print("  OPERACIONES GANADORAS - FILTRADAS POR SESIÓN NY")
print("  Sesión NY: 13:30-20:00 UTC (10:30-17:00 Santiago)")
print("="*100)

ny_trades = []
london_trades = []

for trade in all_trades:
    dt_utc = datetime.strptime(trade["entry_utc"], "%Y-%m-%d %H:%M")
    dt_utc = dt_utc.replace(tzinfo=timezone.utc)
    
    # Convertir a Santiago
    dt_santiago = dt_utc + SANTIAGO_OFFSET
    
    # Verificar si está en sesión NY
    hour_utc = dt_utc.hour
    minute_utc = dt_utc.minute
    time_utc = hour_utc * 60 + minute_utc
    
    ny_start = 13 * 60 + 30  # 13:30
    ny_end = 20 * 60          # 20:00
    
    in_ny = ny_start <= time_utc < ny_end
    
    trade_info = {
        **trade,
        "dt_santiago": dt_santiago.strftime('%Y-%m-%d %H:%M'),
        "in_ny": in_ny
    }
    
    if in_ny:
        ny_trades.append(trade_info)
    else:
        london_trades.append(trade_info)

print(f"\n📊 RESUMEN:")
print(f"  Total operaciones ganadoras: {len(all_trades)}")
print(f"  Operaciones NY:              {len(ny_trades)} ({len(ny_trades)/len(all_trades)*100:.1f}%)")
print(f"  Operaciones Londres:         {len(london_trades)} ({len(london_trades)/len(all_trades)*100:.1f}%)")

print("\n" + "="*100)
print("  OPERACIONES GANADORAS DE NY (13:30-20:00 UTC)")
print("="*100)

print(f"\n{'#':<4} {'Fecha UTC':<17} {'Hora Santiago':<17} {'Dir':<6} {'Entry':<10} {'SL':<10} {'TP':<10} {'PnL':<8}")
print("-" * 100)

for trade in ny_trades:
    print(f"#{trade['id']:<3} {trade['entry_utc']:<17} {trade['dt_santiago']:<17} {trade['dir']:<6} "
          f"{trade['entry']:<10.2f} {trade['sl']:<10.2f} {trade['tp']:<10.2f} ${trade['pnl']:<7}")

print("\n" + "="*100)
print("  ESTADÍSTICAS NY")
print("="*100)

if ny_trades:
    longs_ny = [t for t in ny_trades if t['dir'] == 'LONG']
    shorts_ny = [t for t in ny_trades if t['dir'] == 'SHORT']
    
    total_pnl = sum(t['pnl'] for t in ny_trades)
    avg_pnl = total_pnl / len(ny_trades)
    
    print(f"\n  Total trades NY:     {len(ny_trades)}")
    print(f"  LONG:                {len(longs_ny)} ({len(longs_ny)/len(ny_trades)*100:.1f}%)")
    print(f"  SHORT:               {len(shorts_ny)} ({len(shorts_ny)/len(ny_trades)*100:.1f}%)")
    print(f"  PnL total:           ${total_pnl:,.0f}")
    print(f"  PnL promedio:        ${avg_pnl:,.2f}")

print("\n" + "="*100)
print("  OPERACIONES DE LONDRES (FUERA DE NY)")
print("="*100)

print(f"\n{'#':<4} {'Fecha UTC':<17} {'Hora Santiago':<17} {'Dir':<6} {'Entry':<10} {'SL':<10} {'TP':<10} {'PnL':<8}")
print("-" * 100)

for trade in london_trades:
    print(f"#{trade['id']:<3} {trade['entry_utc']:<17} {trade['dt_santiago']:<17} {trade['dir']:<6} "
          f"{trade['entry']:<10.2f} {trade['sl']:<10.2f} {trade['tp']:<10.2f} ${trade['pnl']:<7}")

if london_trades:
    longs_lon = [t for t in london_trades if t['dir'] == 'LONG']
    shorts_lon = [t for t in london_trades if t['dir'] == 'SHORT']
    
    total_pnl_lon = sum(t['pnl'] for t in london_trades)
    avg_pnl_lon = total_pnl_lon / len(london_trades)
    
    print("\n" + "="*100)
    print("  ESTADÍSTICAS LONDRES")
    print("="*100)
    
    print(f"\n  Total trades Londres: {len(london_trades)}")
    print(f"  LONG:                 {len(longs_lon)} ({len(longs_lon)/len(london_trades)*100:.1f}%)")
    print(f"  SHORT:                {len(shorts_lon)} ({len(shorts_lon)/len(london_trades)*100:.1f}%)")
    print(f"  PnL total:            ${total_pnl_lon:,.0f}")
    print(f"  PnL promedio:         ${avg_pnl_lon:,.2f}")

print("\n" + "="*100)
