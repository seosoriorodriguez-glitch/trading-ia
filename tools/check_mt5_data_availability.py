# -*- coding: utf-8 -*-
import sys
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

import MetaTrader5 as mt5
from datetime import datetime

print("🔍 Verificando disponibilidad de datos M5 en MT5...\n")

if not mt5.initialize():
    print(f"❌ Error inicializando MT5: {mt5.last_error()}")
    sys.exit(1)

print("✅ MT5 conectado\n")

symbol = "US30.cash"

# Verificar M5 - intentar con diferentes tamaños
print("📊 Timeframe M5:")

# Intentar con 100k velas primero
test_sizes = [100000, 50000, 20000, 10000]
rates_m5 = None

for size in test_sizes:
    rates_m5 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M5, 0, size)
    if rates_m5 is not None and len(rates_m5) > 0:
        print(f"   ✅ Descargado {len(rates_m5):,} velas (límite testeado: {size:,})")
        break

if rates_m5 is None or len(rates_m5) == 0:
    print(f"   ❌ No se pudieron obtener datos M5: {mt5.last_error()}")
else:
    start_time = datetime.fromtimestamp(rates_m5[0]['time'])
    end_time = datetime.fromtimestamp(rates_m5[-1]['time'])
    days = (end_time - start_time).days
    
    print(f"   Total velas:  {len(rates_m5):,}")
    print(f"   Desde:        {start_time}")
    print(f"   Hasta:        {end_time}")
    print(f"   Días:         {days}")
    print(f"   Meses:        {days/30:.1f}")

# Verificar M15
print("\n📊 Timeframe M15:")

rates_m15 = None
for size in test_sizes:
    rates_m15 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, size)
    if rates_m15 is not None and len(rates_m15) > 0:
        print(f"   ✅ Descargado {len(rates_m15):,} velas (límite testeado: {size:,})")
        break

if rates_m15 is None or len(rates_m15) == 0:
    print(f"   ❌ No se pudieron obtener datos M15: {mt5.last_error()}")
else:
    start_time = datetime.fromtimestamp(rates_m15[0]['time'])
    end_time = datetime.fromtimestamp(rates_m15[-1]['time'])
    days = (end_time - start_time).days
    
    print(f"   Total velas:  {len(rates_m15):,}")
    print(f"   Desde:        {start_time}")
    print(f"   Hasta:        {end_time}")
    print(f"   Días:         {days}")
    print(f"   Meses:        {days/30:.1f}")

mt5.shutdown()

print("\n" + "="*80)
print("RECOMENDACIÓN")
print("="*80)

if rates_m5 is not None and len(rates_m5) > 0:
    days_available = (datetime.fromtimestamp(rates_m5[-1]['time']) - 
                     datetime.fromtimestamp(rates_m5[0]['time'])).days
    
    if days_available >= 365:
        print(f"\n✅ Hay {days_available} días disponibles. Descargar 365 días (1 año).")
    else:
        print(f"\n⚠️  Solo hay {days_available} días disponibles.")
        print(f"   Descargar el máximo: {days_available} días.")
